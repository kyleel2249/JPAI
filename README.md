# JPAI

Local-first personal, professional and enterprise intelligence platform.

## Current implementation

- FastAPI backend and React/TypeScript command-centre dashboard.
- Local Ollama model discovery and private inference.
- Capability-aware model routing using observed reliability, latency, provider preference and context constraints.
- Parallel model comparison and latency benchmarking.
- Governed API gateway with capability allowlisting, optional API-key enforcement, request IDs, early rate limiting and bounded request bodies.
- SQLite persistence for typed memories, model telemetry, agent tasks, scorecards and audit events.
- Four-class persistent memory (working, episodic, semantic, procedural), importance-aware lexical retrieval, memory archiving and a local knowledge graph.
- Specialist task inference can retrieve relevant local memories as untrusted reference context.
- Professional specialisation taxonomy with 11 categories and 16 seeded specialist agents.
- Persistent agent registry, task queue, human approvals, multi-agent council and task performance scorecards.
- Capability-aware specialist recommendations with explicit skill filters, task relevance, observed outcomes and explainable ranking reasons.
- Dashboard surfaces specialist recommendations, workforce scorecards and governance events.
- Dashboard workspaces for intelligence, memory, agents, quality governance, research, creative, engineering, business, finance, automation, security and system monitoring.
- Evidence-gated continuous improvement cycles and sequential issue resolution with root-cause, corrective-action, test and verification records.
- Quality audit trail persisted in the same local SQLite database as JPAI's other operational records.
- Governed Web Intelligence crawler with same-origin discovery, robots.txt handling, bounded HTML extraction, SHA-256 source fingerprints, persistent crawl jobs and local search.
- Explicit research-to-memory ingestion so selected crawled pages become provenance-labelled, unverified reference memories available to specialist retrieval.
- Persistent recurring source-monitoring schedules with a local lifecycle-managed scheduler, pause/resume and atomic due-job claiming.
- Normalized page-version history, SHA-256 content fingerprints and detected content-change events, surfaced in the Web Intelligence dashboard.
- DNS-pinned public-IP socket connections to reduce DNS-rebinding/SSRF risk while retaining HTTPS hostname verification.

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

Web Intelligence currently collects public HTML only. It uses same-origin scope, robots.txt checks, DNS-pinned public-IP connections, and bounded page/depth/size/time limits; it does not execute JavaScript. Persistent schedules run only while the local API process is active. Page versions and content-change events are stored locally. Crawled content is external and unverified; explicit ingestion preserves source URL, timestamp and content hash. Memory and web-page search currently use weighted lexical relevance, not embeddings. Knowledge-graph entities and relations are locally persisted in SQLite. Model and specialist routing use explainable operational heuristics, not a claimed measure of intelligence or guaranteed success.

## Documentation

- [Master architecture](docs/MASTER_ARCHITECTURE.md)
- [30-phase roadmap](docs/ROADMAP_30_PHASES.md)
- [Phase 3 — governed API gateway](docs/PHASE_3_GOVERNED_API_GATEWAY.md)
- [Phase 4 — multi-agent orchestration](docs/PHASE_4_MULTI_AGENT_ORCHESTRATION.md)
- [Phase 5 — memory and knowledge infrastructure](docs/PHASE_5_MEMORY_KNOWLEDGE_INFRASTRUCTURE.md)
- [Phase 6 — professional intelligence registry](docs/PHASE_6_PROFESSIONAL_INTELLIGENCE_REGISTRY.md)
- [Phase 7 — quality governance](docs/PHASE_7_QUALITY_GOVERNANCE.md)
- [Phase 7 acceptance](docs/PHASE_7_ACCEPTANCE.md)
- [Quality governance and continuous improvement](docs/QUALITY_GOVERNANCE.md)
- [Quality governance acceptance](docs/QUALITY_GOVERNANCE_ACCEPTANCE.md)
- [Web Intelligence & Research Engine](docs/WEB_INTELLIGENCE.md)
- [Professional specialisation catalogue](docs/PROFESSIONAL_SPECIALISATIONS.md)

## API gateway configuration

Optional local API protection:
```env
JPAI_GATEWAY_API_KEY=replace_with_a_long_random_secret
JPAI_GATEWAY_REQUESTS_PER_MINUTE=60
JPAI_GATEWAY_MAX_REQUEST_BYTES=1048576
VITE_JPAI_API_KEY=replace_with_the_same_local_secret
```
Do not commit real secrets. A Vite-exposed key is only appropriate for a trusted local development setup.

## Multi-agent safety boundaries

Agent task execution currently performs local-model analysis only. High-risk quantitative-finance and cybersecurity tasks require explicit human approval. Recommendations do not create tasks or approve execution. No trading, deployment, payment, shell or external account actions are enabled.
