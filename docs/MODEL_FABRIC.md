# GPT-6 Model Fabric

## Models and official capabilities

| Model | JPAI assignment | Context | Max output | Standard input/output per 1M tokens |
|---|---|---:|---:|---:|
| GPT-6.2 Astra (`gpt-6.2-astra`) | Frontier reasoning, complex engineering, architecture and final synthesis | 1.05M | 128K | $8 / $40 |
| GPT-6.2 Sol (`gpt-6.2-sol`) | Balanced multi-step agent work, coding and daily workflows | 1.05M | 128K | $2 / $10 |
| GPT-6 Luna (`gpt-6-luna`) | Bounded, repeatable and high-volume tasks | 1.05M | 128K | $0.10 / $0.50 |

All accept text and image input and return text. Astra and Sol support low/medium/high/xhigh/max reasoning; Luna additionally supports none. The API model catalogue and provider documentation govern actual availability, tool support, rate limits and billing. Prices shown are published Standard token rates used for estimates and can change.

## Integrated

- OpenAI Responses API adapters using the three exact model IDs.
- Backend-only API key configuration; secrets are not exposed by status or catalog endpoints.
- Model catalogue including model purpose, context/output limits, reasoning levels, modalities, documented tool capabilities and token pricing.
- Text and HTTPS image URL inputs, reasoning controls, bounded output tokens and strict JSON Schema output.
- Explicitly requested hosted web search, code interpreter and image-generation tools.
- Function-call declarations and response parsing; proposed calls are returned for review, never auto-executed.
- Concurrent specialist council with model-tier assignment, shared local SQLite memory, provenance-labelled agent outputs and Astra synthesis.
- Bounded concurrency, latency/token/cost reporting, partial-result handling and fail-closed missing-key behaviour.
- Local Ollama remains available; cloud integration is optional.

## Safety / not enabled

Computer use, hosted shell, apply-patch, MCP, skills and tool-search are documented capabilities but are not enabled as JPAI executors. They need isolated execution, least-privilege scopes, human approval, audit and rollback. File search needs a configured vector store and is not enabled by default. Streaming and realtime audio/video are not implemented in this adapter; listed model modalities are text/image input and text output. No trade, payment, deployment or external account action is executed.

## API and configuration

- `GET /api/v1/model-fabric/catalog`
- `GET /api/v1/model-fabric/status`
- `POST /api/v1/model-fabric/infer`
- `POST /api/v1/model-fabric/council`

Set `JPAI_OPENAI_API_KEY` only in the backend environment. Optional settings: `JPAI_OPENAI_BASE_URL`, `JPAI_MODEL_FABRIC_TIMEOUT_SECONDS` (180), `JPAI_MODEL_FABRIC_MAX_CONCURRENCY` (8). Never commit a real key or place it in a Vite/frontend variable.

CI tests are offline and do not make billable API calls. Live API access, quality, latency, rate limits and account billing require a deliberate smoke test with a configured key.
