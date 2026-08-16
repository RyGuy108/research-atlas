import asyncio
from datetime import date
from uuid import UUID, uuid4

import pytest

from app.domain.extraction import (
    EvidenceClaim,
    EvidenceQuote,
    EvidenceSection,
    ExtractionRun,
    ExtractionTarget,
    ExtractionUsage,
    PaperExtraction,
)
from app.domain.paper import Author, Paper, PaperProvider, PaperSource
from app.services.extraction_service import ExtractionService, NoExtractionTargetsError


class FakeExtractor:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0

    async def extract(self, paper: Paper) -> ExtractionRun:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0)
        self.active -= 1
        if paper.title == "Broken paper":
            raise RuntimeError("provider refused extraction")
        return _run(paper)


class FakeStore:
    def __init__(self, targets: list[ExtractionTarget]) -> None:
        self.targets = targets
        self.saved: list[tuple[UUID, UUID, ExtractionRun]] = []

    async def list_extraction_targets(
        self,
        search_id: UUID,
        *,
        limit: int,
    ) -> list[ExtractionTarget]:
        return self.targets[:limit]

    async def save_extraction(
        self,
        search_id: UUID,
        paper_id: UUID,
        run: ExtractionRun,
    ) -> None:
        self.saved.append((search_id, paper_id, run))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_batch_extraction_limits_concurrency_persists_successes_and_tracks_failures() -> None:
    targets = [
        _target(1, "First paper"),
        _target(2, "Broken paper"),
        _target(3, "Third paper"),
    ]
    extractor = FakeExtractor()
    store = FakeStore(targets)
    search_id = uuid4()
    service = ExtractionService(extractor=extractor, store=store, max_concurrency=2)

    batch = await service.extract_search(search_id, limit=3)

    assert batch.requested_count == 3
    assert [item.rank for item in batch.completed] == [1, 3]
    assert batch.failures[0].title == "Broken paper"
    assert batch.failures[0].error == "provider refused extraction"
    assert batch.usage.total_tokens == 60
    assert extractor.max_active == 2
    assert [item[1] for item in store.saved] == [targets[0].paper_id, targets[2].paper_id]


@pytest.mark.anyio
async def test_batch_extraction_rejects_search_without_ranked_papers() -> None:
    service = ExtractionService(extractor=FakeExtractor(), store=FakeStore([]))

    with pytest.raises(NoExtractionTargetsError, match="no ranked papers"):
        await service.extract_search(uuid4(), limit=5)


def _target(rank: int, title: str) -> ExtractionTarget:
    return ExtractionTarget(paper_id=uuid4(), rank=rank, paper=_paper(title))


def _paper(title: str) -> Paper:
    return Paper(
        sources=(PaperSource(provider=PaperProvider.ARXIV, identifier=title),),
        title=title,
        abstract="We introduce a retrieval policy.",
        authors=(Author(name="Ada Researcher"),),
        published_on=date(2026, 8, 1),
        landing_page_url="https://example.org/paper",
    )


def _run(paper: Paper) -> ExtractionRun:
    evidence = EvidenceQuote(
        quote="We introduce a retrieval policy.",
        section=EvidenceSection.ABSTRACT,
    )
    claim = EvidenceClaim(summary="A supported claim.", evidence=(evidence,))
    return ExtractionRun(
        extraction=PaperExtraction(
            problem=claim,
            method=claim,
            results=(claim,),
            contributions=(claim,),
            limitations=(),
            keywords=("retrieval", "routing", "evaluation"),
        ),
        model="test-model",
        prompt_version="test-v1",
        provider_response_id=f"response-{paper.title}",
        usage=ExtractionUsage(input_tokens=10, output_tokens=20, total_tokens=30),
        elapsed_ms=5,
    )
