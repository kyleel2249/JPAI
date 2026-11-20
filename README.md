# JPAI

Local-first personal, professional and enterprise intelligence platform.

## Current implementation

- FastAPI backend and React/TypeScript command-centre dashboard.
- Local Ollama model discovery and private inference.
- Optional JPAI Unified Model Fabric with three public identities: JPAI-6.2 Ultra, JPAI-6.2 Pro and JPAI-6 Mantra. Provider adapters, image inputs, structured output, governed tool requests and usage/cost telemetry.
- Parallel specialist councils with shared local SQLite workspace memory, independent contributions, Ultra synthesis and Pro verification.
- Explainable adaptive model routing by task type, complexity, risk, latency and cost preference.
- Capability-aware model catalogue separating documented provider capabilities from JPAI-enabled tools.
- Legacy provider model IDs accepted as migration aliases; user-facing catalogue and dashboard use JPAI identities.
- Capability-aware local model routing using observed reliability, latency, provider preference and context constraints.
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
- Phases 21–30 governed operations kernel: personal intelligence/JPTI scope, decision intelligence, project-execution plans, adaptive-learning reviews, tool governance, software delivery evidence, command-centre metrics, device/sync governance, security assurance and reliability certification records.
- Persistent phase 21–30 project register with field allowlists, bounded evidence payloads, sequential fail-closed gates, explicit final approvals and durable audit history. This is a record-and-review workflow, not an external action executor.
- Evidence-gated continuous improvement cycles and sequential issue resolution with root-cause, corrective-action, test and verification records.
- Quality audit trail persisted in the same local SQLite database as JPAI's other operational records.
- Governed Web Intelligence crawler with same-origin discovery, robots.txt handling, bounded HTML extraction, SHA-256 source fingerprints, persistent crawl jobs and local search.
- Explicit research-to-memory ingestion so selected crawled pages become provenance-labelled, unverified reference memories available to specialist retrieval.
- Persistent recurring source-monitoring schedules with a local lifecycle-managed scheduler, pause/resume and atomic due-job claiming.
- Normalized page-version history, SHA-256 content fingerprints and detected content-change events, surfaced in the Web Intelligence dashboard.
- Bounded schema.org JSON-LD extraction with persistent structured metadata, a dedicated inspection API and dashboard viewer; external metadata remains unverified.
- Local PDF, DOCX, TXT, Markdown and CSV document extraction with upload bounds, SHA-256 deduplication, persistent catalogue, lexical search and explicit provenance-labelled memory ingestion.
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

Reality Studio currently supports local media intake (20 MB per upload), SHA-256 asset provenance, persistent production plans and 4K UHD/ lossless audio delivery profiles. AI reconstruction engines and render workers are not yet integrated; the studio reports engine readiness honestly and does not mark plans complete. Web Intelligence collects public HTML and supports local PDF, DOCX, TXT, Markdown and CSV document uploads. Document uploads are capped at 20 MB, PDF extraction at 200 pages, and extracted text at 500,000 characters. The gateway request-body limit defaults to 22 MB for multipart overhead. Scanned PDFs do not receive OCR; encrypted PDFs are rejected. Document text is stored locally, deduplicated by original-byte SHA-256 and searchable using lexical relevance. Uploaded material remains unverified and is only sent to JPAI memory after explicit user action. Web crawling currently collects public HTML only. It uses same-origin scope, robots.txt checks, DNS-pinned public-IP connections, and bounded page/depth/size/time limits; it does not execute JavaScript. Persistent schedules run only while the local API process is active. Page versions, content-change events and bounded schema.org JSON-LD metadata are stored locally. JSON-LD blocks are capped at 25 per page and 50 KB per block; malformed blocks are ignored. Structured metadata is separately retrievable and remains unverified. Crawled content is external and unverified; explicit ingestion preserves source URL, timestamp and content hash. Memory and web-page search currently use weighted lexical relevance, not embeddings. Knowledge-graph entities and relations are locally persisted in SQLite. Model and specialist routing use explainable operational heuristics, not a claimed measure of intelligence or guaranteed success.

- Phase 32 — Autonomous Intelligence and Parallel Orchestration: `docs/PHASE_32_AUTONOMOUS_ORCHESTRATION.md`
- Phase 33 — JPAI Reality Studio: governed media ingestion, provenance, 4K UHD output profiles and audio restoration planning: `docs/PHASE_33_REALITY_STUDIO.md`\n\n## Documentation

- [Master architecture](docs/MASTER_ARCHITECTURE.md)
- [JPAI Unified Model Family](docs/JPAI_MODEL_FAMILY.md)
- [JPAI Model Fabric](docs/MODEL_FABRIC.md)
- [30-phase roadmap](docs/ROADMAP_30_PHASES.md)
- [Phase 3 — governed API gateway](docs/PHASE_3_GOVERNED_API_GATEWAY.md)
- [Phase 4 — multi-agent orchestration](docs/PHASE_4_MULTI_AGENT_ORCHESTRATION.md)
- [Phase 5 — memory and knowledge infrastructure](docs/PHASE_5_MEMORY_KNOWLEDGE_INFRASTRUCTURE.md)
- [Phase 6 — professional intelligence registry](docs/PHASE_6_PROFESSIONAL_INTELLIGENCE_REGISTRY.md)
- [Phase 7 — quality governance](docs/PHASE_7_QUALITY_GOVERNANCE.md)
- [Quality governance and continuous improvement](docs/QUALITY_GOVERNANCE.md)
- [Web Intelligence & Research Engine](docs/WEB_INTELLIGENCE.md)
- [Professional specialisation catalogue](docs/PROFESSIONAL_SPECIALISATIONS.md)
- [Phases 21–30 advanced platform](docs/PHASE_21_30.md)
- [Phases 21–30 acceptance checklist](docs/PHASE_21_30_ACCEPTANCE.md)

## API gateway configuration

Optional local API protection:
```env
JPAI_GATEWAY_API_KEY=replace_with_a_long_random_secret
JPAI_GATEWAY_REQUESTS_PER_MINUTE=60
JPAI_GATEWAY_MAX_REQUEST_BYTES=22020096
VITE_JPAI_API_KEY=replace_with_the_same_local_secret
```
Do not commit real secrets. A Vite-exposed key is only appropriate for a trusted local development setup.

## Model provider configuration

Set `JPAI_OPENAI_API_KEY` only in the backend environment. Never expose provider credentials through Vite variables. JPAI model identities are stable aliases over provider adapters; current provider limits still apply. See [JPAI Model Family](docs/JPAI_MODEL_FAMILY.md) for capability and independence boundaries.

## Multi-agent safety boundaries

Agent task execution currently performs governed analysis only. High-risk quantitative-finance and cybersecurity tasks require explicit human approval. Recommendations do not create tasks or approve execution. No trading, deployment, payment, shell or external account actions are enabled.
