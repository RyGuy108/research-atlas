from uuid import UUID, uuid4

import pytest

from app.domain.extraction import (
    EvidenceClaim,
    EvidenceQuote,
    EvidenceSection,
    PaperExtraction,
)
from app.domain.landscape import (
    ClusteredLandscape,
    ClusterNarrative,
    LandscapePaper,
    LandscapeSynthesis,
    LandscapeSynthesisRun,
    OpenResearchQuestion,
    ResearchLandscape,
    SynthesisUsage,
)
from app.services.landscape_clusterer import LandscapeClusterer
from app.services.landscape_service import (
    InsufficientLandscapeDataError,
    LandscapeService,
    LandscapeSynthesisUnavailableError,
)


class FakeStore:
    def __init__(self, papers: list[LandscapePaper]) -> None:
        self.papers = papers
        self.saved: ResearchLandscape | None = None

    async def list_landscape_papers(self, search_id: UUID) -> list[LandscapePaper]:
        return self.papers

    async def save_landscape(self, landscape: ResearchLandscape) -> None:
        self.saved = landscape

    async def get_landscape(self, search_id: UUID) -> ResearchLandscape | None:
        return self.saved if self.saved and self.saved.search_id == search_id else None


class FakeSynthesizer:
    async def synthesize(
        self,
        papers: list[LandscapePaper],
        clustered: ClusteredLandscape,
    ) -> LandscapeSynthesisRun:
        return _synthesis_run(papers, clustered)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_landscape_service_clusters_synthesizes_persists_and_reads() -> None:
    papers = [
        _paper(1, "Adaptive retrieval", "retrieval routing evaluation"),
        _paper(2, "Query routing", "retrieval routing confidence"),
    ]
    store = FakeStore(papers)
    service = LandscapeService(
        store=store,
        clusterer=LandscapeClusterer(),
        synthesizer=FakeSynthesizer(),
    )
    search_id = uuid4()

    built = await service.build(search_id)
    loaded = await service.get(search_id)

    assert built == loaded == store.saved
    assert {item.paper_id for item in built.clustered.positions} == {
        paper.paper_id for paper in papers
    }


@pytest.mark.anyio
async def test_landscape_service_requires_two_extracted_papers() -> None:
    service = LandscapeService(
        store=FakeStore([_paper(1, "One paper", "retrieval routing evaluation")]),
        clusterer=LandscapeClusterer(),
        synthesizer=FakeSynthesizer(),
    )

    with pytest.raises(InsufficientLandscapeDataError, match="at least two"):
        await service.build(uuid4())


@pytest.mark.anyio
async def test_landscape_service_requires_key_only_when_building() -> None:
    service = LandscapeService(
        store=FakeStore([]),
        clusterer=LandscapeClusterer(),
        synthesizer=None,
    )

    with pytest.raises(LandscapeSynthesisUnavailableError, match="OPENAI_API_KEY"):
        await service.build(uuid4())
    with pytest.raises(InsufficientLandscapeDataError, match="not found"):
        await service.get(uuid4())


def _paper(rank: int, title: str, keywords: str) -> LandscapePaper:
    evidence = EvidenceQuote(quote=title, section=EvidenceSection.TITLE)
    claim = EvidenceClaim(summary=keywords, evidence=(evidence,))
    return LandscapePaper(
        paper_id=uuid4(),
        rank=rank,
        title=title,
        extraction=PaperExtraction(
            problem=claim,
            method=claim,
            results=(claim,),
            contributions=(claim,),
            limitations=(),
            keywords=tuple(keywords.split()),
        ),
    )


def _synthesis_run(
    papers: list[LandscapePaper],
    clustered: ClusteredLandscape,
) -> LandscapeSynthesisRun:
    narratives = tuple(
        ClusterNarrative(
            cluster_id=cluster.cluster_id,
            name=cluster.label,
            summary="This theme groups related approaches to retrieval and evaluation.",
            evidence_paper_ids=cluster.paper_ids,
        )
        for cluster in clustered.clusters
    )
    synthesis = LandscapeSynthesis(
        overview="The research landscape studies retrieval routing and evaluation methods.",
        clusters=narratives,
        relationships=(),
        tensions=(),
        open_questions=(
            OpenResearchQuestion(
                question="How should adaptive retrieval policies balance quality and cost?",
                rationale="The extracted papers study related routing and evaluation choices.",
                evidence_paper_ids=tuple(paper.paper_id for paper in papers),
            ),
        ),
    )
    return LandscapeSynthesisRun(
        synthesis=synthesis,
        model="test-model",
        prompt_version="test-v1",
        provider_response_id="response-1",
        usage=SynthesisUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        elapsed_ms=20,
    )
