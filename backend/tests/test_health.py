from fastapi.testclient import TestClient
from jpai_api.main import app

client = TestClient(app)


def test_root_returns_service_identity() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "JPAI"


def test_health_is_available_without_external_services() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["mode"] == "local-first"
