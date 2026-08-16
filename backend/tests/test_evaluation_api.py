from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_evaluation_service
from app.core.config import AppEnvironment, Settings
from app.domain.evaluation import RankingEvaluationRequest, RankingEvaluationRun
from app.main import create_app
from app.services.ranking_metrics import RankingMetrics


class FakeEvaluationService:
    async def evaluate(
        self,
        search_id: UUID,
        request: RankingEvaluationRequest,
    ) -> RankingEvaluationRun:
        return RankingEvaluationRun(
            search_id=search_id,
            judgments=request.judgments,
            metrics=RankingMetrics(k=request.k, recall=0.5, reciprocal_rank=1, ndcg=0.8),
        )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_test_app() -> FastAPI:
    app = create_app(Settings(app_env=AppEnvironment.TEST))
    app.dependency_overrides[get_evaluation_service] = lambda: FakeEvaluationService()
    return app


@pytest.mark.anyio
async def test_evaluation_api_returns_reproducible_metrics() -> None:
    search_id, paper_id = uuid4(), uuid4()
    async with AsyncClient(
        transport=ASGITransport(app=make_test_app()), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/searches/{search_id}/evaluations",
            json={"judgments": [{"paper_id": str(paper_id), "relevance": 2}], "k": 5},
        )

    assert response.status_code == 201
    assert response.json()["metrics"] == {
        "k": 5,
        "recall": 0.5,
        "reciprocal_rank": 1.0,
        "ndcg": 0.8,
    }
