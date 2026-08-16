from fastapi.testclient import TestClient

from app.core.config import AppEnvironment, Settings
from app.main import create_app


def make_client() -> TestClient:
    settings = Settings(
        app_name="Test Atlas API",
        app_version="9.9.9",
        app_env=AppEnvironment.TEST,
    )
    return TestClient(create_app(settings))


def test_root_describes_the_api() -> None:
    response = make_client().get("/")

    assert response.status_code == 200
    assert response.json() == {"name": "Research Atlas API", "docs": "/docs"}


def test_health_reports_application_metadata() -> None:
    response = make_client().get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "Test Atlas API",
        "version": "9.9.9",
        "environment": "test",
    }


def test_readiness_reports_configured_dependencies() -> None:
    response = make_client().get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"configuration": "configured"},
    }

