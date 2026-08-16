from collections.abc import Awaitable
from pathlib import Path

import httpx
import pytest

from app.domain.paper import PaperProvider
from app.domain.search import SearchFilters, SearchRequest
from app.providers.arxiv import ArxivProvider, build_arxiv_query, parse_arxiv_feed
from app.providers.base import ProviderResponseError

FIXTURE = Path(__file__).parent / "fixtures" / "arxiv_feed.xml"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_parse_arxiv_feed_maps_atom_metadata() -> None:
    paper = parse_arxiv_feed(FIXTURE.read_text())[0]

    assert paper.provider == PaperProvider.ARXIV
    assert paper.provider_id == "2608.00001"
    assert paper.title == "Adaptive Retrieval for Small Language Models"
    assert [author.name for author in paper.authors] == ["Ada Researcher", "Grace Scientist"]
    assert paper.categories == ("cs.CL", "cs.IR")
    assert paper.doi == "10.1000/example.1"
    assert str(paper.pdf_url) == "https://arxiv.org/pdf/2608.00001v2"


def test_build_arxiv_query_includes_date_range() -> None:
    request = SearchRequest(
        topic="adaptive retrieval",
        filters=SearchFilters(year_from=2024, year_to=2026),
    )

    assert build_arxiv_query(request) == (
        'all:"adaptive" AND all:"retrieval" AND submittedDate:[202401010000 TO 202612312359]'
    )


@pytest.mark.anyio
async def test_search_pages_until_candidate_budget_is_met() -> None:
    calls: list[httpx.Request] = []
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, text=FIXTURE.read_text())

    def record_delay(delay: float) -> Awaitable[None]:
        async def complete() -> None:
            delays.append(delay)

        return complete()

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://export.arxiv.org"
    ) as client:
        provider = ArxivProvider(client, page_size=1, sleep=record_delay)
        papers = await provider.search(
            SearchRequest(topic="adaptive retrieval", filters=SearchFilters(max_candidates=10))
        )

    assert len(papers) == 10
    assert len(calls) == 10
    assert delays == [3.0] * 9
    assert calls[1].url.params["start"] == "1"


@pytest.mark.anyio
async def test_search_retries_temporary_provider_errors() -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        status = 503 if attempts < 3 else 200
        return httpx.Response(status, text=FIXTURE.read_text(), request=request)

    async def record_delay(delay: float) -> None:
        delays.append(delay)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://export.arxiv.org"
    ) as client:
        provider = ArxivProvider(client, page_size=10, sleep=record_delay)
        papers = await provider.search(SearchRequest(topic="retrieval evaluation"))

    assert len(papers) == 1
    assert attempts == 3
    assert delays == [1.0, 2.0]


def test_parse_arxiv_feed_rejects_invalid_xml() -> None:
    with pytest.raises(ProviderResponseError, match="invalid Atom XML"):
        parse_arxiv_feed("not xml")

