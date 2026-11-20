# Phase 2 — Local Intelligence Infrastructure

## Implemented in this phase
- Provider-neutral local intelligence service boundary.
- Ollama loopback-only adapter for runtime health, model discovery and text generation.
- Typed model profiles and inference/selection/benchmark request contracts.
- Capability-aware local model selection and automatic inference routing.
- Parallel multi-model comparison with isolated per-model errors and a two-request concurrency cap.
- Local dashboard controls for runtime status, model discovery, selection and inference.
- Local model discovery, inference and latency benchmark API routes.
- Bounded request sizes, temperature and benchmark iteration validation.
- Explicit runtime-unavailable and unknown-model failure responses.
- Unit tests for loopback security, capability selection and unknown-model rejection.

## API surface
- `GET /api/v1/intelligence/runtime` — local runtime health.
- `GET /api/v1/intelligence/models` — discover and list locally installed models.
- `POST /api/v1/intelligence/models/discover` — refresh local model catalogue.
- `POST /api/v1/intelligence/models/select` — select a model by capability/provider/context constraint.
- `POST /api/v1/intelligence/infer` — local text inference.
- `POST /api/v1/intelligence/infer/auto` — discover and select a compatible model, then infer.
- `POST /api/v1/intelligence/models/compare` — compare up to five local models with at most two simultaneous inference calls.
- `POST /api/v1/intelligence/benchmark` — bounded latency benchmark.

## Configuration
- `JPAI_OLLAMA_BASE_URL` defaults to `http://127.0.0.1:11434`.
- `JPAI_MODEL_TIMEOUT_SECONDS` defaults to 90 seconds.
- The adapter rejects non-loopback hosts; this phase does not permit remote inference endpoints.

## Advanced design safeguards
- Model capability metadata is not guessed beyond supported chat capability.
- A model must be discovered before inference is permitted.
- Missing runtime/model state fails with an explicit service or not-found response.
- No automatic model download or execution of shell commands is performed.
- Benchmarks report observed latency only; they do not fabricate quality scores or throughput.
- The catalogue is currently process-local and refreshed from the runtime; persistence and agent assignments belong to later phases.

## Verification status
Tests have been authored but must be executed in a Python environment before phase certification. A running Ollama service and at least one locally pulled model are required to demonstrate live inference; neither is assumed to exist.
