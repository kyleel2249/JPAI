# JPAI

Local-first personal, professional and enterprise intelligence platform.

## Current implementation

- Governed API gateway ingress with capability allowlisting, optional API-key enforcement, request IDs, rate limiting and payload-size guardrails.

- FastAPI backend and React/TypeScript command-centre dashboard.
- Local Ollama model discovery and private inference.
- Capability-aware routing with observed reliability, latency, provider preference and known context constraints.
- Parallel model comparison and latency benchmarking.
- SQLite persistence for local memories, model performance telemetry and audit events.
- Namespace-scoped memory capture, listing and transparent local keyword-relevance retrieval.
- Dashboard workspaces for intelligence, memory, agents, research, creative, engineering, business, finance, automation, security and system monitoring.
- Professional specialisation taxonomy with 11 domains and 16 seeded specialist agents.
- Persistent agent registry, task queue, human approvals, agent council and performance scorecards.
- Governed API gateway with optional API-key protection across private API routes and bounded request-body handling.

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

See [Phase 2.1 engineering notes](docs/PHASE_2_1_STABILISATION_AND_INTELLIGENCE.md) and [Phase 3 API Gateway notes](docs/PHASE_3_GOVERNED_API_GATEWAY.md).

## API gateway configuration

Optional local API protection:
```env
JPAI_GATEWAY_API_KEY=replace_with_a_long_random_secret
JPAI_GATEWAY_REQUESTS_PER_MINUTE=60
JPAI_GATEWAY_MAX_REQUEST_BYTES=1048576
VITE_JPAI_API_KEY=replace_with_the_same_local_secret
```
Do not commit real secrets. A Vite-exposed key is only appropriate for a trusted local development setup.

## Multi-agent orchestration

See [Phase 3 gateway hardening](docs/PHASE_3_GOVERNED_API_GATEWAY.md), [Phase 4 multi-agent orchestration](docs/PHASE_4_MULTI_AGENT_ORCHESTRATION.md), and [professional specialisation catalogue](docs/PROFESSIONAL_SPECIALISATIONS.md).

Agent task execution currently performs local-model analysis only. High-risk quantitative-finance and cybersecurity tasks require explicit human approval. No trading, deployment, payment, shell or external account actions are enabled.
