from collections.abc import Awaitable, Callable
from uuid import UUID

import httpx
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.repository import ResearchRepository
from app.db.session import session_factory
from app.domain.extraction import ExtractionBatch
from app.domain.job import (
    PipelineArtifacts,
    PipelineJobRequest,
    PipelineJobStage,
    PipelineProgress,
)
from app.domain.landscape import ResearchLandscape
from app.domain.search_result import SearchOutcome
from app.extractors.openai import OpenAIPaperExtractor
from app.providers.arxiv import ArxivProvider
from app.providers.base import PaperSearchProvider
from app.providers.openalex import OpenAlexProvider
from app.rankers.cross_encoder import CrossEncoderRanker
from app.rankers.tfidf import TfidfRanker
from app.services.extraction_service import ExtractionService
from app.services.landscape_clusterer import LandscapeClusterer
from app.services.landscape_service import LandscapeService
from app.services.search_service import SearchService
from app.synthesizers.openai import OpenAILandscapeSynthesizer

ProgressReporter = Callable[[PipelineProgress], Awaitable[None]]


class AtlasPipelineRunner:
    def __init__(
        self,
        settings: Settings,
        *,
        sessions: async_sessionmaker[AsyncSession] = session_factory,
    ) -> None:
        self._settings = settings
        self._sessions = sessions
        self._semantic_ranker = (
            CrossEncoderRanker(
                model_name=settings.cross_encoder_model,
                device=settings.cross_encoder_device,
                batch_size=settings.cross_encoder_batch_size,
            )
            if settings.cross_encoder_enabled
            else None
        )

    async def run(
        self,
        request: PipelineJobRequest,
        report: ProgressReporter,
    ) -> PipelineArtifacts:
        search = await self._search(request)
        search_artifacts = PipelineArtifacts(search=search)
        await report(
            PipelineProgress(
                stage=PipelineJobStage.RERANK,
                percent=38,
                message=f"Ranked {len(search.results)} papers",
                artifacts=search_artifacts,
            )
        )
        await report(
            PipelineProgress(
                stage=PipelineJobStage.EXTRACT,
                percent=48,
                message=f"Reading the top {request.extraction_limit} papers",
                artifacts=search_artifacts,
            )
        )

        api_key = (
            self._settings.openai_api_key.get_secret_value()
            if self._settings.openai_api_key
            else None
        )
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the end-to-end pipeline")

        client = AsyncOpenAI(
            api_key=api_key,
            timeout=self._settings.llm_timeout_seconds,
            max_retries=self._settings.openai_max_retries,
        )
        try:
            extractions = await self._extract(
                search.search_id,
                request.extraction_limit,
                client,
            )
            extraction_artifacts = PipelineArtifacts(
                search=search,
                extractions=extractions,
            )
            await report(
                PipelineProgress(
                    stage=PipelineJobStage.MAP,
                    percent=78,
                    message=f"Mapping {len(extractions.completed)} evidence-backed papers",
                    artifacts=extraction_artifacts,
                )
            )
            landscape = await self._map(search.search_id, client)
        finally:
            await client.close()

        return PipelineArtifacts(
            search=search,
            extractions=extractions,
            landscape=landscape,
        )

    async def _search(self, request: PipelineJobRequest) -> SearchOutcome:
        timeout = httpx.Timeout(self._settings.provider_timeout_seconds)
        async with (
            httpx.AsyncClient(
                base_url=self._settings.arxiv_base_url,
                timeout=timeout,
            ) as arxiv_client,
            httpx.AsyncClient(
                base_url=self._settings.openalex_base_url,
                timeout=timeout,
            ) as openalex_client,
            self._sessions() as session,
            session.begin(),
        ):
            providers: list[PaperSearchProvider] = [ArxivProvider(arxiv_client)]
            openalex_key = (
                self._settings.openalex_api_key.get_secret_value()
                if self._settings.openalex_api_key
                else None
            )
            if openalex_key:
                providers.append(OpenAlexProvider(openalex_client, api_key=openalex_key))

            service = SearchService(
                providers=providers,
                store=ResearchRepository(session),
                baseline_ranker=TfidfRanker(),
                semantic_ranker=self._semantic_ranker,
                shortlist_limit=self._settings.cross_encoder_candidate_limit,
                result_limit=self._settings.ranking_result_limit,
            )
            return await service.search(request.search)

    async def _extract(
        self,
        search_id: UUID,
        limit: int,
        client: AsyncOpenAI,
    ) -> ExtractionBatch:
        async with self._sessions() as session, session.begin():
            service = ExtractionService(
                extractor=OpenAIPaperExtractor(
                    client,
                    model=self._settings.openai_model,
                    max_output_tokens=self._settings.extraction_max_output_tokens,
                ),
                store=ResearchRepository(session),
                max_concurrency=self._settings.extraction_concurrency,
            )
            return await service.extract_search(search_id, limit=limit)

    async def _map(self, search_id: UUID, client: AsyncOpenAI) -> ResearchLandscape:
        async with self._sessions() as session, session.begin():
            service = LandscapeService(
                store=ResearchRepository(session),
                clusterer=LandscapeClusterer(
                    max_clusters=self._settings.landscape_max_clusters,
                    similarity_threshold=self._settings.landscape_similarity_threshold,
                ),
                synthesizer=OpenAILandscapeSynthesizer(
                    client,
                    model=self._settings.openai_model,
                    max_output_tokens=self._settings.landscape_max_output_tokens,
                ),
            )
            return await service.build(search_id)
