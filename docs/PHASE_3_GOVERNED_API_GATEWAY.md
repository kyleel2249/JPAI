# Phase 3 — Governed API Gateway hardening

## Implemented
- Unified local inference gateway: `POST /api/v1/gateway/infer`.
- Gateway diagnostics: `GET /api/v1/gateway/status`.
- Capability allowlisting; only capabilities implemented by the local runtime are accepted.
- Automatic model selection through the capability-aware ranker.
- Optional API-key enforcement across protected `/api/v1/*` routes using `X-JPAI-API-Key`.
- Public liveness and gateway-status exceptions; CORS preflight requests bypass API-key enforcement.
- Constant-time API-key comparison.
- Bounded request-body buffering and replay, including chunked bodies without Content-Length.
- Sliding-window per-client request limiting, request IDs, retry hints and security response headers.
- Regression tests for authentication, streamed body limits, CORS preflight, rate limiting and gateway behaviour.

## Local configuration
```env
JPAI_GATEWAY_REQUESTS_PER_MINUTE=60
JPAI_GATEWAY_MAX_REQUEST_BYTES=1048576
JPAI_GATEWAY_API_KEY=replace_with_a_long_random_secret
VITE_JPAI_API_KEY=replace_with_the_same_local_secret
```

Set the Vite variable only for a trusted local development build. A browser-delivered key is visible to users of that browser bundle and is not a production secret-management solution. Do not commit real secrets.

## Remaining deployment hardening
- The rate limiter is process-local. Multi-worker or multi-device deployments need a shared atomic store.
- Production network exposure requires TLS termination, managed identity, secret rotation, network segmentation and operational monitoring.
- The request body is buffered up to the configured cap before downstream processing; this is deliberately bounded and is not a large-file streaming service.
- The gateway does not proxy arbitrary remote providers, run shell commands, access files, deploy software, place trades or execute financial transactions.

## Verification
Repository CI is configured to run backend pytest and Ruff checks plus frontend TypeScript/Vite build and Vitest. A source commit is not proof that the workflow has passed; inspect the actual Actions run before marking the phase certified.
