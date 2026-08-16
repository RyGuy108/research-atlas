import asyncio
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from app.domain.extraction import (
    CompletedExtraction,
    ExtractionBatch,
    ExtractionFailure,
    ExtractionRun,
    ExtractionTarget,
    ExtractionUsage,
)
from app.extractors.base import PaperExtractor


class ExtractionStore(Protocol):
    async def list_extraction_targets(
        self,
        search_id: UUID,
        *,
        limit: int,
    ) -> list[ExtractionTarget]: ...

    async def save_extraction(
        self,
        search_id: UUID,
        paper_id: UUID,
        run: ExtractionRun,
    ) -> None: ...


class NoExtractionTargetsError(LookupError):
    """Raised when a search has no ranked papers available for extraction."""


class ExtractionService:
    def __init__(
        self,
        *,
        extractor: PaperExtractor,
        store: ExtractionStore,
        max_concurrency: int = 3,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be positive")
        self._extractor = extractor
        self._store = store
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def extract_search(self, search_id: UUID, *, limit: int) -> ExtractionBatch:
        if limit < 1:
            raise ValueError("limit must be positive")
        targets = await self._store.list_extraction_targets(search_id, limit=limit)
        if not targets:
            raise NoExtractionTargetsError("search has no ranked papers to extract")

        outcomes = await asyncio.gather(*(self._extract_one(target) for target in targets))
        completed: list[CompletedExtraction] = []
        failures: list[ExtractionFailure] = []
        for target, outcome in zip(targets, outcomes, strict=True):
            if isinstance(outcome, Exception):
                failures.append(
                    ExtractionFailure(
                        paper_id=target.paper_id,
                        rank=target.rank,
                        title=target.paper.title,
                        error=str(outcome),
                    )
                )
                continue

            # Database writes remain sequential because one AsyncSession is not task-safe.
            await self._store.save_extraction(search_id, target.paper_id, outcome)
            completed.append(
                CompletedExtraction(
                    paper_id=target.paper_id,
                    rank=target.rank,
                    title=target.paper.title,
                    run=outcome,
                )
            )

        return ExtractionBatch(
            search_id=search_id,
            requested_count=len(targets),
            completed=tuple(completed),
            failures=tuple(failures),
            usage=_total_usage([item.run for item in completed]),
        )

    async def _extract_one(self, target: ExtractionTarget) -> ExtractionRun | Exception:
        async with self._semaphore:
            try:
                return await self._extractor.extract(target.paper)
            except Exception as error:
                return error


def _total_usage(runs: Sequence[ExtractionRun]) -> ExtractionUsage:
    return ExtractionUsage(
        input_tokens=sum(run.usage.input_tokens for run in runs),
        output_tokens=sum(run.usage.output_tokens for run in runs),
        total_tokens=sum(run.usage.total_tokens for run in runs),
    )
