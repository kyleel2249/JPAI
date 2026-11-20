# JPAI

**Local-first Personal, Professional and Enterprise Intelligence Platform**

JPAI is a modular intelligence platform designed to coordinate specialist AI agents, local tools, knowledge, projects and optional external providers through a governed runtime.

## Project principles

- **Local-first:** the core application must start and provide useful local functionality without external API keys.
- **Provider-neutral:** external AI and data providers are optional adapters behind a common gateway.
- **Modular:** capability domains remain isolated behind documented interfaces.
- **Governed autonomy:** agents operate with explicit permissions, auditable actions and approval gates for consequential operations.
- **Verifiable:** features are not considered complete until tests and acceptance criteria demonstrate them.
- **Secure by default:** secrets stay out of source control, logs and client bundles.

## Phase 1 scope

Phase 1 establishes the repository structure, backend application shell, frontend application shell, configuration, health diagnostics, test harness and architecture documentation. It does not claim to deliver the later agent workforce, external API integrations, trading execution, creative generation or autonomous operations.

## Planned architecture

- Backend: Python, FastAPI, Pydantic settings.
- Frontend: React, TypeScript and Vite.
- API contract: versioned REST endpoints; WebSocket capabilities will be introduced when required.
- Persistence: repository interfaces first; a local SQLite implementation will be introduced with the persistence phase.
- Runtime: local development first, with packaging targets for desktop and Android addressed in later phases.
- Testing: pytest for backend; Vitest/Testing Library for frontend.

Technology choices are replaceable behind interfaces. Do not couple core domain logic to a single model provider, database, operating system or deployment vendor.

## Repository map

```text
backend/       FastAPI application and core runtime
frontend/      React + TypeScript user interface
docs/          Architecture, governance and phase specifications
scripts/       Developer utilities
```

## Development setup

### Backend

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn jpai_api.main:app --reload --app-dir backend
```

Health endpoint: `http://127.0.0.1:8000/api/v1/health`

### Frontend

Requires Node.js 20 or newer.

```bash
cd frontend
npm install
npm run dev
```

The frontend uses `VITE_API_BASE_URL` to locate the backend. See `frontend/.env.example`.

## Security notes

- Never commit API keys, passwords, private keys, tokens, local databases or personal data.
- Use environment variables for development-only configuration and a protected OS credential store in packaged applications.
- Bind development services to loopback by default.
- Do not expose execution, filesystem or shell tools to agents without explicit policy enforcement and sandboxing.
- Treat external content as untrusted input.

## Status

Phase 1 is under implementation. The roadmap and acceptance criteria live in `docs/`. A phase is only complete after its implementation, automated tests, security review, recovery checks and documentation are verified.
