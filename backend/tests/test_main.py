import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import AppEnvironment, Settings
from app.main import create_app


def make_test_app() -> FastAPI:
    settings = Settings(
        app_name="Test Atlas API",
        app_version="9.9.9",
        app_env=AppEnvironment.TEST,
    )
    return create_app(settings)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_root_describes_the_api() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_test_app()), base_url="http://test"
    ) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == {"name": "Research Atlas API", "docs": "/docs"}


@pytest.mark.anyio
async def test_health_reports_application_metadata() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_test_app()), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "Test Atlas API",
        "version": "9.9.9",
        "environment": "test",
    }


@pytest.mark.anyio
async def test_readiness_reports_configured_dependencies() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_test_app()), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"configuration": "configured"},
    }
