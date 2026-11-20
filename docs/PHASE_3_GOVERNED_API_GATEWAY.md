# Phase 3 — Governed API Gateway

## Delivered scope
- Unified local inference ingress at `POST /api/v1/gateway/infer`.
- Capability allowlisting: only `chat` is enabled until additional adapters and their safety contracts exist.
- Reuses the existing model eligibility and ranking service; returns the selected model, score, rationale and bounded alternatives.
- Optional API-key enforcement through `JPAI_GATEWAY_API_KEY`; comparisons use constant-time secret comparison.
- Request IDs, rate-limit response headers, bounded declared request sizes and baseline browser security headers.
- Gateway configuration/status endpoint at `GET /api/v1/gateway/status`.

## Configuration
- `JPAI_GATEWAY_REQUESTS_PER_MINUTE=60`
- `JPAI_GATEWAY_MAX_REQUEST_BYTES=1048576`
- `JPAI_GATEWAY_API_KEY` (unset for loopback local development; set before exposing the API to trusted clients)

## Safety and limitations
- The gateway does not enable tools, filesystem access, shell execution, remote providers or autonomous actions.
- Unsupported capabilities fail closed with HTTP 403.
- The in-memory rate limiter is per process. Multi-worker or multi-device deployments require a shared limiter.
- The request-size guard validates declared Content-Length; reverse proxies or a streaming body limiter are required for hostile clients that omit it.
- This is a local-first development gateway, not a substitute for production identity, TLS termination, secrets management or network segmentation.
