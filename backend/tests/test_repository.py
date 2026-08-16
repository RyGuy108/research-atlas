from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.repository import ResearchRepository
from app.domain.extraction import (
    EvidenceClaim,
    EvidenceQuote,
    EvidenceSection,
    ExtractionRun,
    ExtractionUsage,
    PaperExtraction,
)
from app.domain.landscape import (
    ClusteredLandscape,
    ClusterNarrative,
    LandscapeSynthesis,
    LandscapeSynthesisRun,
    OpenResearchQuestion,
    PaperPosition,
    ResearchLandscape,
    SynthesisUsage,
    ThemeCluster,
)
from app.domain.paper import Author, Paper, PaperProvider, PaperSource
from app.domain.search import SearchRequest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_repository_persists_search_and_ranked_papers() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory.begin() as session:
        repository = ResearchRepository(session)
        search_id = await repository.create_search(SearchRequest(topic="adaptive retrieval"))
        papers = [_paper(PaperProvider.ARXIV, "2608.00001", 5)]
        await repository.attach_results(search_id, papers, scores=[0.91])

    async with factory() as session:
        stored = await ResearchRepository(session).list_search_papers(search_id)

    await engine.dispose()
    assert len(stored) == 1
    assert stored[0].title == "Adaptive Retrieval"
    assert stored[0].citation_count == 5
    assert stored[0].sources[0].identifier == "2608.00001"


@pytest.mark.anyio
async def test_repository_upserts_same_canonical_paper() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)
    async with factory.begin() as session:
        repository = ResearchRepository(session)
        first = await repository.upsert_paper(_paper(PaperProvider.ARXIV, "2608.00001", 2))
        second = await repository.upsert_paper(_paper(PaperProvider.ARXIV, "2608.00001", 12))

    await engine.dispose()
    assert first.id == second.id
    assert second.citation_count == 12


@pytest.mark.anyio
async def test_repository_lists_ranked_targets_and_upserts_extraction() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory.begin() as session:
        repository = ResearchRepository(session)
        search_id = await repository.create_search(SearchRequest(topic="adaptive retrieval"))
        await repository.attach_results(
            search_id,
            [_paper(PaperProvider.ARXIV, "2608.00001", 5)],
            scores=[0.91],
        )
        targets = await repository.list_extraction_targets(search_id, limit=5)
        await repository.save_extraction(search_id, targets[0].paper_id, _extraction_run())
        await repository.save_extraction(search_id, targets[0].paper_id, _extraction_run())
        landscape_papers = await repository.list_landscape_papers(search_id)
        landscape = _landscape(search_id, targets[0].paper_id)
        await repository.save_landscape(landscape)
        await repository.save_landscape(landscape)

    async with factory() as session:
        stored_landscape = await ResearchRepository(session).get_landscape(search_id)

    await engine.dispose()
    assert len(targets) == 1
    assert targets[0].rank == 1
    assert targets[0].paper.title == "Adaptive Retrieval"
    assert landscape_papers[0].extraction == _extraction_run().extraction
    assert stored_landscape == landscape


def _paper(provider: PaperProvider, identifier: str, citation_count: int) -> Paper:
    return Paper(
        sources=(PaperSource(provider=provider, identifier=identifier),),
        title="Adaptive Retrieval",
        abstract="A study of adaptive retrieval policies.",
        authors=(Author(name="Ada Researcher"),),
        arxiv_id="2608.00001",
        citation_count=citation_count,
        published_on=date(2026, 8, 1),
        landing_page_url="https://arxiv.org/abs/2608.00001",
    )


def _extraction_run() -> ExtractionRun:
    evidence = EvidenceQuote(
        quote="A study of adaptive retrieval policies.",
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
        provider_response_id="response-1",
        usage=ExtractionUsage(input_tokens=10, output_tokens=20, total_tokens=30),
        elapsed_ms=5,
    )


def _landscape(search_id: object, paper_id: object) -> ResearchLandscape:
    return ResearchLandscape.model_validate(
        {
            "search_id": search_id,
            "clustered": ClusteredLandscape(
                clusters=(ThemeCluster(cluster_id=0, label="retrieval", paper_ids=(paper_id,)),),
                positions=(
                    PaperPosition(
                        paper_id=paper_id,
                        cluster_id=0,
                        membership_score=1,
                        x=0,
                        y=0,
                    ),
                ),
                similarity_edges=(),
            ),
            "synthesis_run": LandscapeSynthesisRun(
                synthesis=LandscapeSynthesis(
                    overview="The landscape studies adaptive retrieval policies and evaluation.",
                    clusters=(
                        ClusterNarrative(
                            cluster_id=0,
                            name="Adaptive retrieval",
                            summary="This theme studies when systems should retrieve evidence.",
                            evidence_paper_ids=(paper_id,),
                        ),
                    ),
                    relationships=(),
                    tensions=(),
                    open_questions=(
                        OpenResearchQuestion(
                            question="How should adaptive retrieval quality and cost be balanced?",
                            rationale=(
                                "The paper motivates evaluating both behavior and efficiency."
                            ),
                            evidence_paper_ids=(paper_id,),
                        ),
                    ),
                ),
                model="test-model",
                prompt_version="test-v1",
                provider_response_id="response-landscape",
                usage=SynthesisUsage(input_tokens=100, output_tokens=50, total_tokens=150),
                elapsed_ms=20,
            ),
        }
    )
