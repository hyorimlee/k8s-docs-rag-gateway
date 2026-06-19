from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_includes_service_metadata() -> None:
    response = client.get("/health")

    body = response.json()
    assert "service" in body
    assert "environment" in body
    assert "version" in body
