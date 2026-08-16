from collections.abc import Sequence
from datetime import date
from uuid import UUID, uuid4

import pytest

from app.domain.paper import Author, Paper, PaperProvider, PaperSource
from app.domain.search import RankingStrategy, SearchRequest
from app.providers.base import PaperSearchProvider
from app.rankers.tfidf import TfidfRanker
from app.services.search_service import SearchService, SearchUnavailableError


class FakeProvider:
    def __init__(self, provider: PaperProvider, response: list[Paper] | Exception) -> None:
        self.provider = provider
        self.response = response

    async def search(self, request: SearchRequest) -> list[Paper]:
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class FakeStore:
    def __init__(self) -> None:
        self.search_id = uuid4()
        self.saved_papers: Sequence[Paper] = ()
        self.saved_scores: Sequence[float | None] = ()

    async def create_search(self, request: SearchRequest) -> UUID:
        return self.search_id

    async def attach_results(
        self,
        search_id: UUID,
        papers: Sequence[Paper],
        scores: Sequence[float | None] | None = None,
    ) -> None:
        assert search_id == self.search_id
        self.saved_papers = papers
        self.saved_scores = scores or ()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_search_combines_deduplicates_ranks_and_persists_provider_results() -> None:
    arxiv = _paper(PaperProvider.ARXIV, "2608.00001", "Adaptive retrieval", "Policy routing")
    duplicate = arxiv.model_copy(
        update={
            "sources": (PaperSource(provider=PaperProvider.OPENALEX, identifier="W1"),),
            "citation_count": 10,
        }
    )
    unrelated = _paper(PaperProvider.OPENALEX, "W2", "Vision models", "Image patches")
    store = FakeStore()
    providers: list[PaperSearchProvider] = [
        FakeProvider(PaperProvider.ARXIV, [arxiv]),
        FakeProvider(PaperProvider.OPENALEX, [duplicate, unrelated]),
    ]
    service = SearchService(
        providers=providers,
        store=store,
        baseline_ranker=TfidfRanker(),
        result_limit=2,
    )

    outcome = await service.search(
        SearchRequest(topic="adaptive retrieval", strategies=(RankingStrategy.KEYWORD,))
    )

    assert outcome.search_id == store.search_id
    assert outcome.ranking_strategy == RankingStrategy.KEYWORD
    assert outcome.diagnostics.candidate_count == 3
    assert outcome.diagnostics.deduplicated_count == 2
    assert outcome.diagnostics.provider_candidates == {"arxiv": 1, "openalex": 2}
    assert outcome.results[0].paper.title == "Adaptive retrieval"
    assert list(store.saved_papers) == [result.paper for result in outcome.results]


@pytest.mark.anyio
async def test_search_keeps_partial_results_and_reports_provider_failure() -> None:
    service = SearchService(
        providers=[
            FakeProvider(PaperProvider.ARXIV, [_paper(PaperProvider.ARXIV, "one", "RAG", "RAG")]),
            FakeProvider(PaperProvider.OPENALEX, RuntimeError("rate limited")),
        ],
        store=FakeStore(),
        baseline_ranker=TfidfRanker(),
    )

    outcome = await service.search(SearchRequest(topic="RAG evaluation"))

    assert outcome.diagnostics.returned_count == 1
    assert outcome.diagnostics.warnings == (
        "openalex failed: rate limited",
        "cross_encoder unavailable; used keyword baseline",
    )


@pytest.mark.anyio
async def test_search_fails_when_every_provider_fails() -> None:
    service = SearchService(
        providers=[FakeProvider(PaperProvider.ARXIV, RuntimeError("offline"))],
        store=FakeStore(),
        baseline_ranker=TfidfRanker(),
    )

    with pytest.raises(SearchUnavailableError, match="all paper providers"):
        await service.search(SearchRequest(topic="RAG evaluation"))


def _paper(
    provider: PaperProvider,
    identifier: str,
    title: str,
    abstract: str,
) -> Paper:
    return Paper(
        sources=(PaperSource(provider=provider, identifier=identifier),),
        title=title,
        abstract=abstract,
        authors=(Author(name="Ada Researcher"),),
        published_on=date(2026, 8, 1),
        landing_page_url=f"https://example.org/{identifier}",
    )
