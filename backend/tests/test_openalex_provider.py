import json
from pathlib import Path

import httpx
import pytest

from app.domain.paper import PaperProvider
from app.domain.search import SearchFilters, SearchRequest
from app.providers.base import ProviderConfigurationError
from app.providers.openalex import OpenAlexProvider, _restore_abstract

FIXTURE = Path(__file__).parent / "fixtures" / "openalex_works.json"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_provider_requires_api_key() -> None:
    with pytest.raises(ProviderConfigurationError, match="OPENALEX_API_KEY"):
        OpenAlexProvider(httpx.AsyncClient(), api_key=None)


def test_restore_abstract_uses_inverted_positions() -> None:
    assert _restore_abstract({"retrieval": [2], "adaptive": [1], "Study": [0]}) == (
        "Study adaptive retrieval"
    )


@pytest.mark.anyio
async def test_search_resolves_venue_and_maps_work() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/sources":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "https://openalex.org/S111",
                            "display_name": "International Conference on Learning Representations",
                        }
                    ]
                },
            )
        return httpx.Response(200, json=json.loads(FIXTURE.read_text()))

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.openalex.org"
    ) as client:
        provider = OpenAlexProvider(client, api_key="test-key")
        papers = await provider.search(
            SearchRequest(
                topic="adaptive retrieval",
                filters=SearchFilters(
                    venues=frozenset({"International Conference on Learning Representations"}),
                    year_from=2025,
                    year_to=2026,
                ),
            )
        )

    paper = papers[0]
    assert paper.sources[0].provider == PaperProvider.OPENALEX
    assert paper.sources[0].identifier == "W123456789"
    assert paper.abstract == "We study adaptive retrieval"
    assert paper.doi == "10.1000/example.1"
    assert paper.arxiv_id == "2608.00001"
    assert paper.citation_count == 14
    assert requests[0].url.params["api_key"] == "test-key"
    assert requests[1].url.params["filter"] == (
        "has_abstract:true,from_publication_date:2025-01-01,"
        "to_publication_date:2026-12-31,primary_location.source.id:S111"
    )


@pytest.mark.anyio
async def test_search_returns_empty_when_venue_cannot_be_resolved() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []}, request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.openalex.org"
    ) as client:
        provider = OpenAlexProvider(client, api_key="test-key")
        papers = await provider.search(
            SearchRequest(
                topic="adaptive retrieval",
                filters=SearchFilters(venues=frozenset({"Unknown Conference"})),
            )
        )

    assert papers == []
