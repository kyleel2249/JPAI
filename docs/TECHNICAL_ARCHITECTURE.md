# Technical Architecture

## Initial stack
Python 3.11+, FastAPI, Pydantic Settings and httpx; React 18, TypeScript and Vite; pytest/pytest-asyncio; Vitest/Testing Library; Ruff. Keep choices replaceable behind interfaces.

## Backend boundaries
- `jpai_api.main`: application composition and middleware.
- `jpai_api.config`: typed configuration and safe defaults.
- `jpai_api.routes`: transport-level routes.
- `jpai_api.intelligence`: provider-neutral local model contracts, runtime adapter and selection service.
- Future `domain`, `services`, `adapters` and `infrastructure` packages separate business rules from external systems.

## Local model runtime
The first adapter targets Ollama through its local HTTP API. The configured URL must resolve to a loopback host. Runtime discovery supplies model metadata; capability claims are conservative. Inference requires a model to be discovered. No model is downloaded automatically.

## Runtime and networking
Development binds to loopback. CORS is limited to local Vite origins. Before network exposure, add explicit origins, authentication, authorization, rate limits, secure transport and threat-model review.

## Persistence
No database dependency is required for the local runtime adapter. The discovered model catalogue is process-local in this phase. Durable memory, agent configuration and assignments will be introduced behind repository interfaces in later phases.

## API evolution
All public endpoints are versioned under `/api/v1`. Validate schemas and document breaking changes. Future mutating operations require idempotency and audit controls.

## Security baseline
The local runtime adapter rejects non-loopback endpoints to reduce SSRF risk. No arbitrary shell, filesystem, trading or publishing endpoints are exposed. Credential storage, agent permissions, audit and sandboxing must precede tool execution.
