# JPAI

**Local-first Personal, Professional and Enterprise Intelligence Platform**

JPAI is a modular intelligence platform designed to coordinate specialist AI agents, local tools, knowledge, projects and optional external providers through a governed runtime.

## Principles
- Local-first core; external API keys are optional.
- Provider-neutral adapters and modular domain boundaries.
- Roles, agents, models and tools are distinct entities.
- Least privilege, explicit approvals and auditable execution.
- Evidence-based phase completion; no unverified completion claims.

## Current delivery
- **Phase 1:** repository and application foundation, FastAPI health API, React/TypeScript shell, configuration and architecture baseline.
- **Phase 2:** local intelligence adapter, Ollama loopback runtime integration, model discovery, capability selection, inference and benchmark API, plus dashboard controls. Runtime verification remains pending.

## Planned architecture
Backend: Python/FastAPI. Frontend: React/TypeScript/Vite. Local model runtime: provider-neutral adapter with Ollama as the first implementation. Persistence and knowledge services will be added behind repository interfaces. Desktop and Android packaging are later roadmap phases.

## Repository map
```text
backend/       FastAPI application and local intelligence services
frontend/      React + TypeScript user interface
docs/          Architecture, governance and phase specifications
scripts/       Developer utilities
```

## Backend setup
Requires Python 3.11+.
```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn jpai_api.main:app --reload --app-dir backend
```
API docs: http://127.0.0.1:8000/docs
Health: http://127.0.0.1:8000/api/v1/health

## Frontend setup
Requires Node.js 20+.
```bash
cd frontend
npm install
npm run dev
```
Configure `VITE_API_BASE_URL` using `frontend/.env.example`.

## Local model runtime
Install and start Ollama separately, then pull a model using Ollama's own trusted installer/CLI. JPAI connects only to a loopback runtime by default:
```text
JPAI_OLLAMA_BASE_URL=http://127.0.0.1:11434
JPAI_MODEL_TIMEOUT_SECONDS=90
```
JPAI does not download models automatically. No model or Ollama installation is bundled with this repository.

## Security
Never commit credentials, tokens, private keys, local databases or personal data. Development binds to loopback. Do not expose shell, filesystem, trading or publishing tools to agents without policy enforcement, sandboxing and approval controls.
