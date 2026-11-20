import asyncio
import json

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


def _run_middleware(middleware, content_length=None, requests=1):
    sent = []

    async def downstream(_scope, _receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "headers": [(b"content-length", str(content_length).encode())] if content_length else [],
        "client": ("127.0.0.1", 12345),
    }
    middleware.app = downstream

    async def run():
        for _ in range(requests):
            await middleware(scope, receive, send)

    asyncio.run(run())
    starts = [message for message in sent if message["type"] == "http.response.start"]
    bodies = [message for message in sent if message["type"] == "http.response.body"]
    start = starts[-1]
    body = bodies[-1]
    return start["status"], dict(start["headers"]), json.loads(body["body"])


def test_gateway_rejects_oversized_declared_content_length():
    middleware = GatewayMiddleware(app=None, requests_per_minute=10, max_request_bytes=1024)
    status, _headers, body = _run_middleware(middleware, content_length=2048)
    assert status == 413
    assert body["detail"] == "request_too_large"


def test_gateway_enforces_sliding_window_rate_limit():
    middleware = GatewayMiddleware(app=None, requests_per_minute=1, max_request_bytes=2048)
    status, _headers, _body = _run_middleware(middleware, requests=2)
    assert status == 429


def test_gateway_rejects_malformed_content_length():
    middleware = GatewayMiddleware(app=None, requests_per_minute=10, max_request_bytes=2048)
    middleware.app = None
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    async def run():
        await middleware(
            {"type": "http", "headers": [(b"content-length", b"not-a-number")], "client": ("127.0.0.1", 1)},
            receive,
            send,
        )

    asyncio.run(run())
    assert sent[0]["status"] == 400
