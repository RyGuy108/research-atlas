from datetime import date
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_search_service
from app.core.config import AppEnvironment, Settings
from app.domain.paper import Author, Paper, PaperProvider, PaperSource
from app.domain.ranking import RankedPaper
from app.domain.search import RankingStrategy, SearchRequest
from app.domain.search_result import SearchDiagnostics, SearchOutcome
from app.main import create_app


class FakeSearchService:
    async def search(self, request: SearchRequest) -> SearchOutcome:
        paper = Paper(
            sources=(PaperSource(provider=PaperProvider.ARXIV, identifier="2608.00001"),),
            title="Adaptive retrieval",
            abstract="A routing policy for retrieval.",
            authors=(Author(name="Ada Researcher"),),
            published_on=date(2026, 8, 1),
            landing_page_url="https://arxiv.org/abs/2608.00001",
        )
        return SearchOutcome(
            search_id=uuid4(),
            topic=request.topic,
            ranking_strategy=RankingStrategy.KEYWORD,
            results=(
                RankedPaper(
                    paper=paper,
                    rank=1,
                    score=0.91,
                    strategy=RankingStrategy.KEYWORD,
                ),
            ),
            diagnostics=SearchDiagnostics(
                provider_candidates={"arxiv": 1},
                candidate_count=1,
                deduplicated_count=1,
                returned_count=1,
                elapsed_ms=12.5,
            ),
        )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_test_app() -> FastAPI:
    app = create_app(Settings(app_env=AppEnvironment.TEST))
    app.dependency_overrides[get_search_service] = lambda: FakeSearchService()
    return app


@pytest.mark.anyio
async def test_create_search_returns_ranked_papers_and_diagnostics() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_test_app()), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/searches",
            json={"topic": "  adaptive   retrieval  ", "strategies": ["keyword"]},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["topic"] == "adaptive retrieval"
    assert payload["ranking_strategy"] == "keyword"
    assert payload["results"][0]["paper"]["title"] == "Adaptive retrieval"
    assert payload["diagnostics"]["provider_candidates"] == {"arxiv": 1}
