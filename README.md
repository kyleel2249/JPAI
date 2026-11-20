# JPAI

Local-first personal, professional and enterprise intelligence platform.

## Current implementation

- FastAPI backend and React/TypeScript command-centre dashboard.
- Local Ollama model discovery and private inference.
- Capability-aware routing with observed reliability, latency, provider preference and known context constraints.
- Parallel model comparison and latency benchmarking.
- SQLite persistence for local memories, model performance telemetry and audit events.
- Namespace-scoped memory capture, listing and transparent local keyword-relevance retrieval.
- Dashboard workspaces for intelligence, memory, agents, research, creative, engineering, business, finance, automation, security and system monitoring.

## Local development

Requirements: Python 3.11+, Node.js 20+, and (for local inference) Ollama with at least one model installed.

Backend:
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn jpai_api.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

Ollama must be started separately. The default runtime endpoint is http://127.0.0.1:11434.
JPAI core and persistent memory do not require external API keys. Local memory defaults to data/jpai.sqlite3; override with JPAI_DATABASE_PATH.

Memory search currently uses transparent lexical relevance, not embeddings. Model routing uses operational heuristics, not a claimed measure of intelligence or reasoning quality.

See [Phase 2.1 engineering notes](docs/PHASE_2_1_STABILISATION_AND_INTELLIGENCE.md).
