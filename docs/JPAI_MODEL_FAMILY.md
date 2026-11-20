# JPAI Unified Model Family

## Official identities

| JPAI identity | Capability lineage | Primary routing profile |
|---|---|---|
| JPAI-6.2 Ultra (`jpai-6.2-ultra`) | GPT-6.2 Astra | Deep reasoning, architecture, complex research, advanced engineering and synthesis |
| JPAI-6.2 Pro (`jpai-6.2-pro`) | GPT-6.2 Sol | Professional reasoning, coding, implementation and multi-step execution |
| JPAI-6 Mantra (`jpai-6-mantra`) | GPT-6 Luna | Efficient reasoning, extraction, classification, monitoring and high-volume processing |

These are JPAI product identities and routing profiles. The current remote adapter maps them to the configured provider model IDs. Renaming a model does not change provider weights or grant capabilities that the provider does not expose.

## Capability inheritance policy

All three identities are first-class JPAI models. Their role profiles are routing defaults, not permission boundaries. The model catalogue exposes each model's capability profile, documented tool surface, and the subset of hosted tools currently enabled by JPAI. Unsupported or unenabled tools are not represented as operational.

Legacy provider model IDs are accepted as compatibility aliases during migration. Catalogues and UI surfaces expose only JPAI identities.

## Shared platform capabilities

- JPAI-native model catalogue and stable public IDs.
- Provider adapter indirection, allowing provider IDs to change without changing the JPAI UI/API contract.
- Explainable routing by task type, complexity, risk, latency and cost preference.
- Parallel specialist council with shared local SQLite memory.
- Provenance-labelled, explicitly unverified agent contributions.
- Ultra synthesis and optional independent Pro verification.
- Per-model reasoning controls, image URL input, structured JSON Schema output and governed hosted tools.
- Bounded concurrency, usage and estimated-cost telemetry, partial-result reporting and fail-closed provider errors.
- Legacy ID compatibility during migration.

## Limits and independence

JPAI does not impose role-based intelligence restrictions. Long-running workflows should be implemented with resumable tasks, checkpoints, retrieval and durable memory rather than relying on one enormous prompt.

The current remote provider still enforces its context window, maximum output, rate limits, service availability, tool availability and billing. JPAI cannot override those external controls. The catalogue exposes provider limits so the UI does not misrepresent them as unlimited.

True provider independence requires a separately hosted model runtime or independently trained/hosted JPAI weights. This repository's local Ollama runtime remains available for supported local models, but it does not currently reproduce the capability or quality of the three remote reference models automatically.

## API

- `GET /api/v1/model-fabric/catalog`
- `GET /api/v1/model-fabric/capabilities`
- `GET /api/v1/model-fabric/status`
- `POST /api/v1/model-fabric/route`
- `POST /api/v1/model-fabric/infer`
- `POST /api/v1/model-fabric/council`

Set `JPAI_OPENAI_API_KEY` only in the backend environment. Never put provider credentials in frontend variables or commit them. Hosted function calls remain review-only; computer use, shell, patching, MCP and external account actions are not enabled by this change.

## Verification

Offline CI verifies public identities, alias migration, cost accounting, fail-closed missing credentials, tool allowlisting, capability discovery and explainable routing. Live provider quality, latency, account access and billing require a deliberate smoke test with a configured credential.
