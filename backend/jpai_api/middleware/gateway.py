"""Local API gateway protections: request IDs, bounded payloads and rate limits."""
from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict, deque
from typing import Callable


class GatewayMiddleware:
    """Small single-process limiter suitable for the local-first development gateway.

    Deployments with multiple workers must replace the in-memory limiter with a shared
    store before relying on globally consistent quotas.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        max_request_bytes: int = 1_048_576,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.app = app
        self.limit = max(1, requests_per_minute)
        self.max_request_bytes = max(1024, max_request_bytes)
        self.clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def _json_error(self, send, status: int, detail: str, request_id: str, headers=None):
        body = ('{"detail":"' + detail + '","request_id":"' + request_id + '"}').encode()
        response_headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"x-request-id", request_id.encode()),
            (b"cache-control", b"no-store"),
        ]
        response_headers.extend(headers or [])
        await send({"type": "http.response.start", "status": status, "headers": response_headers})
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        supplied_id = headers.get(b"x-request-id", b"").decode("ascii", "ignore")[:64]
        request_id = supplied_id if supplied_id and all(c.isalnum() or c in "-_." for c in supplied_id) else uuid.uuid4().hex
        client = scope.get("client")
        client_key = client[0] if client else "unknown"
        now = self.clock()

        async with self._lock:
            hits = self._hits[client_key]
            while hits and now - hits[0] >= 60:
                hits.popleft()
            remaining = max(0, self.limit - len(hits))
            if len(hits) >= self.limit:
                await self._json_error(
                    send, 429, "rate_limit_exceeded", request_id,
                    [(b"retry-after", b"60"), (b"x-ratelimit-limit", str(self.limit).encode()),
                     (b"x-ratelimit-remaining", b"0")],
                )
                return
            hits.append(now)
            remaining = max(0, self.limit - len(hits))

        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_request_bytes:
                    await self._json_error(send, 413, "request_too_large", request_id)
                    return
            except ValueError:
                await self._json_error(send, 400, "invalid_content_length", request_id)
                return

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

        await self.app(scope, receive, send_with_headers)
