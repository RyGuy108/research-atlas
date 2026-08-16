import asyncio
from collections.abc import Sequence
from time import perf_counter
from typing import Protocol
from uuid import UUID

from app.domain.paper import Paper
from app.domain.ranking import RankedPaper
from app.domain.search import RankingStrategy, SearchRequest
from app.domain.search_result import SearchDiagnostics, SearchOutcome
from app.providers.base import PaperSearchProvider
from app.rankers.base import PaperRanker
from app.services.paper_normalizer import normalize_and_deduplicate


class SearchStore(Protocol):
    async def create_search(self, request: SearchRequest) -> UUID: ...

    async def attach_results(
        self,
        search_id: UUID,
        papers: Sequence[Paper],
        scores: Sequence[float | None] | None = None,
    ) -> None: ...


class SearchUnavailableError(RuntimeError):
    """Raised when every configured discovery provider fails."""


class SearchService:
    def __init__(
        self,
        *,
        providers: Sequence[PaperSearchProvider],
        store: SearchStore,
        baseline_ranker: PaperRanker,
        semantic_ranker: PaperRanker | None = None,
        shortlist_limit: int = 50,
        result_limit: int = 25,
    ) -> None:
        if not providers:
            raise ValueError("at least one paper provider is required")
        if shortlist_limit < 1 or result_limit < 1:
            raise ValueError("ranking limits must be positive")
        self._providers = providers
        self._store = store
        self._baseline_ranker = baseline_ranker
        self._semantic_ranker = semantic_ranker
        self._shortlist_limit = shortlist_limit
        self._result_limit = result_limit

    async def search(self, request: SearchRequest) -> SearchOutcome:
        """Discover concurrently, deduplicate, rank, and persist one reproducible search."""
        started_at = perf_counter()
        responses = await asyncio.gather(
            *(provider.search(request) for provider in self._providers),
            return_exceptions=True,
        )

        papers: list[Paper] = []
        provider_candidates: dict[str, int] = {}
        warnings: list[str] = []
        successful_providers = 0
        for provider, response in zip(self._providers, responses, strict=True):
            provider_name = provider.provider.value
            if isinstance(response, BaseException):
                warnings.append(f"{provider_name} failed: {response}")
                provider_candidates[provider_name] = 0
                continue
            successful_providers += 1
            provider_candidates[provider_name] = len(response)
            papers.extend(response)

        if successful_providers == 0:
            raise SearchUnavailableError("all paper providers failed")

        canonical_papers = normalize_and_deduplicate(papers)
        baseline = await asyncio.to_thread(
            self._baseline_ranker.rank,
            request.topic,
            canonical_papers,
            limit=self._shortlist_limit,
        )
        ranked = await self._select_ranking(request, baseline, warnings)
        search_id = await self._store.create_search(request)
        await self._store.attach_results(
            search_id,
            [result.paper for result in ranked],
            [result.score for result in ranked],
        )

        return SearchOutcome(
            search_id=search_id,
            topic=request.topic,
            ranking_strategy=ranked[0].strategy if ranked else self._baseline_ranker.strategy,
            results=tuple(ranked),
            diagnostics=SearchDiagnostics(
                provider_candidates=provider_candidates,
                candidate_count=len(papers),
                deduplicated_count=len(canonical_papers),
                returned_count=len(ranked),
                elapsed_ms=round((perf_counter() - started_at) * 1_000, 2),
                warnings=tuple(warnings),
            ),
        )

    async def _select_ranking(
        self,
        request: SearchRequest,
        baseline: Sequence[RankedPaper],
        warnings: list[str],
    ) -> list[RankedPaper]:
        wants_cross_encoder = RankingStrategy.CROSS_ENCODER in request.strategies
        if wants_cross_encoder and self._semantic_ranker is not None:
            return await asyncio.to_thread(
                self._semantic_ranker.rank,
                request.topic,
                [result.paper for result in baseline],
                limit=self._result_limit,
            )
        if wants_cross_encoder:
            warnings.append("cross_encoder unavailable; used keyword baseline")

        unsupported = set(request.strategies) - {
            RankingStrategy.KEYWORD,
            RankingStrategy.CROSS_ENCODER,
        }
        if unsupported:
            values = ", ".join(sorted(strategy.value for strategy in unsupported))
            warnings.append(f"ranking strategies not implemented: {values}")
        return [
            result.model_copy(update={"rank": rank})
            for rank, result in enumerate(baseline[: self._result_limit], start=1)
        ]
