# JPAI Unified Model Fabric

## Official JPAI model identities

| JPAI model | Provider adapter ID | Routing profile | Context / output (provider-enforced) |
|---|---|---|---:|
| JPAI-6.2 Ultra (`jpai-6.2-ultra`) | `gpt-6.2-astra` | Flagship reasoning, complex engineering and synthesis | 1.05M / 128K |
| JPAI-6.2 Pro (`jpai-6.2-pro`) | `gpt-6.2-sol` | Professional coding, workflows and execution | 1.05M / 128K |
| JPAI-6 Mantra (`jpai-6-mantra`) | `gpt-6-luna` | Efficient, repeatable and high-volume tasks | 1.05M / 128K |

The JPAI IDs are the public product/API identities. Provider IDs are adapter details and may change without requiring a JPAI client migration. Legacy provider IDs remain accepted as compatibility aliases; the public catalogue displays only JPAI identities.

## Implemented

- JPAI-native model identities and provider adapter indirection.
- Capability catalogue distinguishing documented provider tools from tools actually enabled by JPAI.
- Shared text/image input, reasoning controls, structured JSON Schema output and approved hosted tools.
- Explainable adaptive routing by task type, complexity, risk and user priorities.
- Parallel specialist council with shared local SQLite memory and provenance-labelled contributions.
- Ultra synthesis and independent Pro verification pass.
- Bounded concurrency, latency/token/cost telemetry, partial-result handling and fail-closed missing-key behaviour.
- Local Ollama inference remains available independently of the remote adapter.

## Safety and operational boundaries

Computer use, hosted shell, apply-patch, MCP, skills and tool-search are not enabled as JPAI executors. Function-call proposals are not automatically executed. No trade, payment, deployment or external account action is executed by this model-fabric change.

## Provider limits and long-running tasks

JPAI does not impose role-based restrictions on model capability. However, the current remote adapter cannot override provider context/output windows, rate limits, availability, tool eligibility or billing. Long-running JPAI tasks should use durable task records, retrieval, chunking, checkpoints and resumable execution rather than claiming a single model request is unlimited. Independent model hosting is required to remove dependency on the remote provider.

## API and configuration

- `GET /api/v1/model-fabric/catalog`
- `GET /api/v1/model-fabric/capabilities`
- `GET /api/v1/model-fabric/status`
- `POST /api/v1/model-fabric/route`
- `POST /api/v1/model-fabric/infer`
- `POST /api/v1/model-fabric/council`

Set `JPAI_OPENAI_API_KEY` only in the backend environment. Optional settings: `JPAI_OPENAI_BASE_URL`, `JPAI_MODEL_FABRIC_TIMEOUT_SECONDS` and `JPAI_MODEL_FABRIC_MAX_CONCURRENCY`. Never commit a real key or expose it through frontend variables.

Offline CI does not make billable provider calls. Live inference, quality, latency, availability and billing require a deliberate smoke test with a configured key.
