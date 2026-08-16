from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_landscape_service
from app.core.config import AppEnvironment, Settings
from app.domain.landscape import ResearchLandscape
from app.main import create_app
from app.services.landscape_service import (
    InsufficientLandscapeDataError,
    LandscapeSynthesisUnavailableError,
)


class FakeLandscapeService:
    def __init__(self, result: ResearchLandscape | Exception) -> None:
        self.result = result

    async def build(self, search_id: UUID) -> ResearchLandscape:
        return self._resolve()

    async def get(self, search_id: UUID) -> ResearchLandscape:
        return self._resolve()

    def _resolve(self) -> ResearchLandscape:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_test_app(service: FakeLandscapeService) -> FastAPI:
    app = create_app(Settings(app_env=AppEnvironment.TEST))
    app.dependency_overrides[get_landscape_service] = lambda: service
    return app


@pytest.mark.anyio
async def test_landscape_endpoints_build_and_read_persisted_result() -> None:
    search_id = uuid4()
    landscape = ResearchLandscape.model_validate(_landscape_payload(search_id))
    app = make_test_app(FakeLandscapeService(landscape))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(f"/api/v1/searches/{search_id}/landscape")
        loaded = await client.get(f"/api/v1/searches/{search_id}/landscape")

    assert created.status_code == 200
    assert loaded.status_code == 200
    assert created.json() == loaded.json()
    assert created.json()["search_id"] == str(search_id)


@pytest.mark.anyio
async def test_landscape_build_reports_missing_extractions_and_configuration() -> None:
    cases = [
        (InsufficientLandscapeDataError("at least two papers required"), 409),
        (LandscapeSynthesisUnavailableError("OPENAI_API_KEY is required"), 503),
    ]
    for error, expected_status in cases:
        app = make_test_app(FakeLandscapeService(error))
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(f"/api/v1/searches/{uuid4()}/landscape")
        assert response.status_code == expected_status


def _landscape_payload(search_id: UUID) -> dict[str, Any]:
    first, second = uuid4(), uuid4()
    return {
        "search_id": search_id,
        "clustered": {
            "clusters": [
                {"cluster_id": 0, "label": "retrieval", "paper_ids": [first, second]}
            ],
            "positions": [
                {"paper_id": first, "cluster_id": 0, "membership_score": 0.9, "x": -1, "y": 0},
                {"paper_id": second, "cluster_id": 0, "membership_score": 0.8, "x": 1, "y": 0},
            ],
            "similarity_edges": [
                {"source_paper_id": first, "target_paper_id": second, "similarity": 0.7}
            ],
            "silhouette_score": None,
        },
        "synthesis_run": {
            "synthesis": {
                "overview": "The landscape studies adaptive retrieval and evaluation methods.",
                "clusters": [
                    {
                        "cluster_id": 0,
                        "name": "Adaptive retrieval",
                        "summary": "This theme studies when systems should retrieve evidence.",
                        "evidence_paper_ids": [first, second],
                    }
                ],
                "relationships": [],
                "tensions": [],
                "open_questions": [
                    {
                        "question": "How should retrieval quality and cost be balanced?",
                        "rationale": "The papers explore related routing and evaluation choices.",
                        "evidence_paper_ids": [first, second],
                    }
                ],
            },
            "model": "test-model",
            "prompt_version": "test-v1",
            "provider_response_id": "response-1",
            "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            "elapsed_ms": 20,
        },
    }
