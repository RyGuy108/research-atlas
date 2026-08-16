import asyncio
from typing import Protocol
from uuid import UUID

from app.domain.landscape import LandscapePaper, ResearchLandscape
from app.services.landscape_clusterer import LandscapeClusterer
from app.synthesizers.base import LandscapeSynthesizer


class LandscapeStore(Protocol):
    async def list_landscape_papers(self, search_id: UUID) -> list[LandscapePaper]: ...

    async def save_landscape(self, landscape: ResearchLandscape) -> None: ...

    async def get_landscape(self, search_id: UUID) -> ResearchLandscape | None: ...


class InsufficientLandscapeDataError(LookupError):
    """Raised when fewer than two extracted papers are available for synthesis."""


class LandscapeSynthesisUnavailableError(RuntimeError):
    """Raised when building a landscape is requested without an LLM provider."""


class LandscapeService:
    def __init__(
        self,
        *,
        store: LandscapeStore,
        clusterer: LandscapeClusterer,
        synthesizer: LandscapeSynthesizer | None,
    ) -> None:
        self._store = store
        self._clusterer = clusterer
        self._synthesizer = synthesizer

    async def build(self, search_id: UUID) -> ResearchLandscape:
        if self._synthesizer is None:
            raise LandscapeSynthesisUnavailableError(
                "OPENAI_API_KEY is required for landscape synthesis"
            )
        papers = await self._store.list_landscape_papers(search_id)
        if len(papers) < 2:
            raise InsufficientLandscapeDataError(
                "at least two successfully extracted papers are required"
            )

        clustered = await asyncio.to_thread(self._clusterer.cluster, papers)
        synthesis_run = await self._synthesizer.synthesize(papers, clustered)
        landscape = ResearchLandscape(
            search_id=search_id,
            clustered=clustered,
            synthesis_run=synthesis_run,
        )
        await self._store.save_landscape(landscape)
        return landscape

    async def get(self, search_id: UUID) -> ResearchLandscape:
        landscape = await self._store.get_landscape(search_id)
        if landscape is None:
            raise InsufficientLandscapeDataError("research landscape not found")
        return landscape
