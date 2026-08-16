from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_extraction_service
from app.core.config import AppEnvironment, Settings
from app.domain.extraction import ExtractionBatch, ExtractionUsage
from app.main import create_app


class FakeExtractionService:
    async def extract_search(self, search_id: UUID, *, limit: int) -> ExtractionBatch:
        return ExtractionBatch(
            search_id=search_id,
            requested_count=limit,
            completed=(),
            failures=(),
            usage=ExtractionUsage(input_tokens=0, output_tokens=0, total_tokens=0),
        )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_test_app() -> FastAPI:
    app = create_app(Settings(app_env=AppEnvironment.TEST))
    app.dependency_overrides[get_extraction_service] = lambda: FakeExtractionService()
    return app


@pytest.mark.anyio
async def test_extract_search_papers_accepts_a_bounded_batch_size() -> None:
    search_id = uuid4()
    async with AsyncClient(
        transport=ASGITransport(app=make_test_app()), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/searches/{search_id}/extractions",
            json={"limit": 3},
        )

    assert response.status_code == 200
    assert response.json() == {
        "search_id": str(search_id),
        "requested_count": 3,
        "completed": [],
        "failures": [],
        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    }


@pytest.mark.anyio
async def test_extract_search_papers_rejects_oversized_batches() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_test_app()), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/searches/{uuid4()}/extractions",
            json={"limit": 26},
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_extract_search_papers_requires_an_openai_key() -> None:
    app = create_app(Settings(app_env=AppEnvironment.TEST, openai_api_key=None))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/searches/{uuid4()}/extractions",
            json={"limit": 1},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "OPENAI_API_KEY is required for paper extraction"
