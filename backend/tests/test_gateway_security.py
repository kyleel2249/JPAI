import asyncio

from jpai_api.middleware.gateway import GatewayMiddleware


def run_middleware(middleware, scope, messages):
    sent = []
    iterator = iter(messages)

    async def receive():
        try:
            return next(iterator)
        except StopIteration:
            return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    async def downstream(_scope, _receive, downstream_send):
        await downstream_send({"type": "http.response.start", "status": 200, "headers": []})
        await downstream_send({"type": "http.response.body", "body": b"ok"})

    middleware.app = downstream

    async def execute():
        await middleware(scope, receive, send)

    asyncio.run(execute())
    return sent


def test_api_key_protects_private_api_routes():
    middleware = GatewayMiddleware(app=None, api_key="test-secret")
    sent = run_middleware(
        middleware,
        {"type": "http", "method": "GET", "path": "/api/v1/memory", "headers": [], "client": ("127.0.0.1", 1)},
        [{"type": "http.request", "body": b"", "more_body": False}],
    )
    assert sent[0]["status"] == 401


def test_valid_api_key_allows_private_api_routes():
    middleware = GatewayMiddleware(app=None, api_key="test-secret")
    sent = run_middleware(
        middleware,
        {"type": "http", "method": "GET", "path": "/api/v1/memory",
         "headers": [(b"x-jpai-api-key", b"test-secret")], "client": ("127.0.0.1", 1)},
        [{"type": "http.request", "body": b"", "more_body": False}],
    )
    assert sent[0]["status"] == 200


def test_streamed_body_limit_rejects_chunked_oversize_without_content_length():
    middleware = GatewayMiddleware(app=None, max_request_bytes=1024)
    sent = run_middleware(
        middleware,
        {"type": "http", "method": "POST", "path": "/api/v1/agents/tasks", "headers": [],
         "client": ("127.0.0.1", 1)},
        [
            {"type": "http.request", "body": b"x" * 700, "more_body": True},
            {"type": "http.request", "body": b"y" * 400, "more_body": False},
        ],
    )
    assert sent[0]["status"] == 413


def test_cors_preflight_is_not_blocked_by_api_key():
    middleware = GatewayMiddleware(app=None, api_key="test-secret")
    sent = run_middleware(
        middleware,
        {"type": "http", "method": "OPTIONS", "path": "/api/v1/agents", "headers": [],
         "client": ("127.0.0.1", 1)},
        [{"type": "http.request", "body": b"", "more_body": False}],
    )
    assert sent[0]["status"] == 200
