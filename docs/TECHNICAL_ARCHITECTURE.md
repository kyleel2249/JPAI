# Technical Architecture

## Initial stack
- Backend: Python 3.11+, FastAPI, Pydantic Settings.
- Frontend: React 18, TypeScript, Vite.
- Backend tests: pytest, FastAPI TestClient/httpx.
- Frontend tests: Vitest and Testing Library.
- Linting: Ruff and TypeScript strict mode.

These are initial implementation choices, not permanent coupling points. Keep domain services behind interfaces so runtimes and libraries can be replaced.

## Backend boundaries
- `jpai_api.main`: application composition and middleware.
- `jpai_api.config`: typed configuration and safe defaults.
- `jpai_api.routes`: transport-level HTTP routes.
- Future `domain`, `services`, `adapters` and `infrastructure` packages will separate business rules from external systems.

## Frontend boundaries
- `src/App.tsx`: initial application shell and backend connectivity status.
- `src/style.css`: responsive visual foundation.
- Future feature areas should be split into route-level modules and typed API clients.

## Runtime and networking
Development services bind to loopback by default. CORS is limited to local Vite origins. Before any network exposure, add explicit origin configuration, authentication, authorization, rate limiting, secure transport and threat-model review.

## Configuration
Environment variables use the `JPAI_` prefix on the backend. Never commit populated .env files. The frontend API base URL is a non-secret configuration value.

## Persistence strategy
Phase 1 deliberately has no database dependency. Introduce persistence behind repository interfaces in the memory/knowledge phase. SQLite is the initial local default candidate; evaluate PostgreSQL for multi-user or server deployments.

## API evolution
All public endpoints are versioned under `/api/v1`. Validate request/response schemas and document breaking changes. Add idempotency keys for future mutating operations.

## Security baseline
No arbitrary shell execution, filesystem access, trading or publishing endpoints are exposed in Phase 1. Credential storage, agent permissions, audit trails and sandboxing must be implemented before tool execution is enabled.
