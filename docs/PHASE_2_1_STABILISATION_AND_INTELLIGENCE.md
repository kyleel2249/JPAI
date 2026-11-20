# Phase 2.1 — Stabilisation, Persistent Intelligence and Command Centre

## Scope
- Responsive institutional command centre with Dashboard, Intelligence, Memory, Agents and System workspaces.
- SQLite persistence for memory records, model performance telemetry and audit events.
- Namespace-scoped memory capture, listing and transparent local keyword relevance retrieval.
- Model routing using capability eligibility, observed reliability, observed latency, provider preference and known context metadata.
- Routing diagnostics and model telemetry endpoints.
- Preserved loopback-only Ollama access and fail-closed capability/context constraints.

## Limitations
- Memory retrieval is lexical keyword relevance, not embeddings or semantic vector search.
- Model scores are deterministic operational heuristics, not independent reasoning-quality measurements.
- Ollama-discovered models advertise chat only; context length remains unknown unless supplied by a provider.
- SQLite is local persistence; encryption-at-rest, multi-process coordination and cross-device sync require further hardening.
- This phase does not implement external provider credentials, remote integrations, autonomous agents or production authentication.

Default database: data/jpai.sqlite3. Override with JPAI_DATABASE_PATH.
