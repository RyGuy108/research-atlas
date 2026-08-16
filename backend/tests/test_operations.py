import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from app.core.config import AppEnvironment, Settings
from app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_requests_receive_trace_ids_and_emit_prometheus_metrics() -> None:
    app = create_app(Settings(app_env=AppEnvironment.TEST))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/api/v1/health", headers={"X-Request-ID": "trace-123"})
        metrics = await client.get("/api/v1/metrics")

    assert health.headers["x-request-id"] == "trace-123"
    assert "research_atlas_http_requests_total" in metrics.text
    assert 'path="/api/v1/health"' in metrics.text


@pytest.mark.anyio
async def test_optional_write_key_protects_mutating_endpoints() -> None:
    app = create_app(Settings(app_env=AppEnvironment.TEST, write_api_key=SecretStr("correct-key")))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rejected = await client.post(
            "/api/v1/pipeline-jobs",
            json={"search": {"topic": "adaptive retrieval"}},
        )
        accepted = await client.post(
            "/api/v1/pipeline-jobs",
            json={"search": {"topic": "adaptive retrieval"}},
            headers={"X-API-Key": "correct-key"},
        )

    assert rejected.status_code == 401
    assert accepted.status_code == 202
    await app.state.pipeline_job_manager.close()


def test_blank_deployment_secrets_are_treated_as_unset() -> None:
    settings = Settings(openai_api_key="", openalex_api_key="  ", write_api_key="")

    assert settings.openai_api_key is None
    assert settings.openalex_api_key is None
    assert settings.write_api_key is None
