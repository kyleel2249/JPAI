from fastapi.testclient import TestClient

from jpai_api.main import app
from jpai_api.middleware.gateway import GatewayMiddleware

client = TestClient(app)


def test_gateway_status_exposes_safe_configuration():
    response = client.get("/api/v1/gateway/status")
    assert response.status_code == 200
    assert response.json()["mode"] == "local-first"
    assert response.json()["inference_ingress"] == "/api/v1/gateway/infer"


def test_gateway_rejects_unsupported_capability_before_runtime(monkeypatch):
    from jpai_api.routes import gateway

    monkeypatch.setattr(gateway, "_authorize", lambda _key: None)
    response = client.post(
        "/api/v1/gateway/infer",
        json={"capability": "vision", "prompt": "describe this image"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "capability_not_enabled"


def test_gateway_adds_request_id_and_security_headers():
    response = client.get("/", headers={"X-Request-ID": "jpai-test-123"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "jpai-test-123"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_gateway_rejects_oversized_content_length():
    middleware = GatewayMiddleware(
        app=lambda *_args: None,
        requests_per_minute=10,
        max_request_bytes=1024,
    )
    assert middleware.max_request_bytes == 1024
