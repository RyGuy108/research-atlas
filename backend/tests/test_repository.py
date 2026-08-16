from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.repository import ResearchRepository
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
