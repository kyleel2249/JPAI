"""Local API gateway protections: request IDs, bounded bodies, auth and rate limits."""
from __future__ import annotations

import asyncio
import hmac
import json
import math
import time
import uuid
from collections import defaultdict, deque
from typing import Callable


class GatewayMiddleware:
    """Single-process sliding-window limiter and request guard for local deployments.

    The body is bounded and replayed to downstream ASGI apps. Multi-worker deployments
    must use shared rate-limit storage; a reverse proxy should still terminate TLS.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        max_request_bytes: int = 1_048_576,
        api_key: str | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.app = app
        self.limit = max(1, requests_per_minute)
        self.max_request_bytes = max(1024, max_request_bytes)
        self.api_key = api_key
        self.clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def _json_error(self, send, status: int, detail: str, request_id: str, headers=None):
        body = json.dumps({"detail": detail, "request_id": request_id}).encode()
        response_headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"x-request-id", request_id.encode()),
            (b"cache-control", b"no-store"),
            (b"x-content-type-options", b"nosniff"),
        ]
        response_headers.extend(headers or [])
        await send({"type": "http.response.start", "status": status, "headers": response_headers})
        await send({"type": "http.response.body", "body": body})

    async def _read_bounded_body(self, receive):
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return None
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_request_bytes:
                return False
            chunks.append(chunk)
            if not message.get("more_body", False):
                return b"".join(chunks)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_id = headers.get(b"x-request-id", b"").decode("ascii", "ignore")[:64]
        request_id = raw_id if raw_id and all(c.isalnum() or c in "-_." for c in raw_id) else uuid.uuid4().hex
        path = scope.get("path", "")
        protected = path.startswith("/api/v1/") and path not in {
            "/api/v1/health", "/api/v1/gateway/status",
        }

        if protected and self.api_key:
            supplied = headers.get(b"x-jpai-api-key", b"").decode("utf-8", "ignore")
            if not hmac.compare_digest(supplied, self.api_key):
                await self._json_error(send, 401, "api_authentication_required", request_id)
                return

        declared_length = headers.get(b"content-length")
        if declared_length:
            try:
                if int(declared_length) > self.max_request_bytes:
                    await self._json_error(send, 413, "request_too_large", request_id)
                    return
            except ValueError:
                await self._json_error(send, 400, "invalid_content_length", request_id)
                return

        body = await self._read_bounded_body(receive)
        if body is False:
            await self._json_error(send, 413, "request_too_large", request_id)
            return
        if body is None:
            return
        replayed = False

        async def replay_receive():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        client = scope.get("client")
        client_key = client[0] if client else "unknown"
        now = self.clock()
        limited = False
        retry_after = 60

        async with self._lock:
            hits = self._hits[client_key]
            while hits and now - hits[0] >= 60:
                hits.popleft()
            if len(hits) >= self.limit:
                limited = True
                retry_after = max(1, math.ceil(60 - (now - hits[0])))
            else:
                hits.append(now)
            if len(self._hits) > 10_000:
                stale = [key for key, values in self._hits.items() if not values or now - values[-1] >= 60]
                for key in stale:
                    self._hits.pop(key, None)

        if limited:
            await self._json_error(
                send, 429, "rate_limit_exceeded", request_id,
                [(b"retry-after", str(retry_after).encode()),
                 (b"x-ratelimit-limit", str(self.limit).encode()),
                 (b"x-ratelimit-remaining", b"0")],
            )
            return

        remaining = max(0, self.limit - len(self._hits[client_key]))

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.extend([
                    (b"x-request-id", request_id.encode()),
                    (b"x-ratelimit-limit", str(self.limit).encode()),
                    (b"x-ratelimit-remaining", str(remaining).encode()),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"cache-control", b"no-store"),
                ])
                message = {**message, "headers": response_headers}
            await send(message)

        await self.app(scope, replay_receive, send_with_headers)
