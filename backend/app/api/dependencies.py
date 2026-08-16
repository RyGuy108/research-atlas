from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repository import ResearchRepository
from app.db.session import get_session
from app.providers.arxiv import ArxivProvider
from app.providers.base import PaperSearchProvider
from app.providers.openalex import OpenAlexProvider
from app.rankers.cross_encoder import CrossEncoderRanker
from app.rankers.tfidf import TfidfRanker
from app.services.search_service import SearchService


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
