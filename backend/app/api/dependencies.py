from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, Request, status
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repository import ResearchRepository
from app.db.session import get_session
from app.extractors.openai import OpenAIPaperExtractor
from app.providers.arxiv import ArxivProvider
from app.providers.base import PaperSearchProvider
from app.providers.openalex import OpenAlexProvider
from app.rankers.cross_encoder import CrossEncoderRanker
from app.rankers.tfidf import TfidfRanker
from app.services.evaluation_service import EvaluationService
from app.services.extraction_service import ExtractionService
from app.services.landscape_clusterer import LandscapeClusterer
from app.services.landscape_service import LandscapeService
from app.services.search_service import SearchService
from app.synthesizers.openai import OpenAILandscapeSynthesizer


async def get_evaluation_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncIterator[EvaluationService]:
    async with session.begin():
        yield EvaluationService(ResearchRepository(session))


async def get_search_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncIterator[SearchService]:
    settings: Settings = request.app.state.settings
    timeout = httpx.Timeout(settings.provider_timeout_seconds)
    async with (
        httpx.AsyncClient(base_url=settings.arxiv_base_url, timeout=timeout) as arxiv_client,
        httpx.AsyncClient(base_url=settings.openalex_base_url, timeout=timeout) as openalex_client,
        session.begin(),
    ):
        providers: list[PaperSearchProvider] = [ArxivProvider(arxiv_client)]
        openalex_key = (
            settings.openalex_api_key.get_secret_value() if settings.openalex_api_key else None
        )
        if openalex_key:
            providers.append(OpenAlexProvider(openalex_client, api_key=openalex_key))

        semantic_ranker = _semantic_ranker(request, settings)
        yield SearchService(
            providers=providers,
            store=ResearchRepository(session),
            baseline_ranker=TfidfRanker(),
            semantic_ranker=semantic_ranker,
            shortlist_limit=settings.cross_encoder_candidate_limit,
            result_limit=settings.ranking_result_limit,
        )


def _semantic_ranker(request: Request, settings: Settings) -> CrossEncoderRanker | None:
    if not settings.cross_encoder_enabled:
        return None
    ranker: CrossEncoderRanker | None = getattr(request.app.state, "cross_encoder_ranker", None)
    if ranker is None:
        ranker = CrossEncoderRanker(
            model_name=settings.cross_encoder_model,
            device=settings.cross_encoder_device,
            batch_size=settings.cross_encoder_batch_size,
        )
        request.app.state.cross_encoder_ranker = ranker
    return ranker


async def get_extraction_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncIterator[ExtractionService]:
    settings: Settings = request.app.state.settings
    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is required for paper extraction",
        )

    client = AsyncOpenAI(
        api_key=api_key,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.openai_max_retries,
    )
    try:
        async with session.begin():
            yield ExtractionService(
                extractor=OpenAIPaperExtractor(
                    client,
                    model=settings.openai_model,
                    max_output_tokens=settings.extraction_max_output_tokens,
                ),
                store=ResearchRepository(session),
                max_concurrency=settings.extraction_concurrency,
            )
    finally:
        await client.close()


async def get_landscape_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncIterator[LandscapeService]:
    settings: Settings = request.app.state.settings
    api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
    client = (
        AsyncOpenAI(
            api_key=api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )
        if api_key
        else None
    )
    synthesizer = (
        OpenAILandscapeSynthesizer(
            client,
            model=settings.openai_model,
            max_output_tokens=settings.landscape_max_output_tokens,
        )
        if client
        else None
    )
    try:
        async with session.begin():
            yield LandscapeService(
                store=ResearchRepository(session),
                clusterer=LandscapeClusterer(
                    max_clusters=settings.landscape_max_clusters,
                    similarity_threshold=settings.landscape_similarity_threshold,
                ),
                synthesizer=synthesizer,
            )
    finally:
        if client:
            await client.close()
