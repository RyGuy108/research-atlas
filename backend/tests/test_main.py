from fastapi.testclient import TestClient

from app.main import app


def test_root_describes_the_api() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.json() == {"name": "Research Atlas API", "docs": "/docs"}

