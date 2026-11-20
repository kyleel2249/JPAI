# Phase 2 Acceptance Criteria

## Scope
Provide a provider-neutral local intelligence layer, first local runtime adapter, model discovery, capability selection, bounded inference and benchmarking, plus dashboard controls.

## Implemented
- [x] Local runtime abstraction and Ollama adapter.
- [x] Loopback-only runtime URL validation.
- [x] Local runtime health check.
- [x] Model discovery and typed capability profiles.
- [x] Capability-aware model selection with optional provider/context constraints.
- [x] Inference endpoint with bounded prompt/system inputs and temperature.
- [x] Bounded latency benchmark endpoint.
- [x] Explicit unknown-model and runtime-unavailable errors.
- [x] Dashboard model discovery, selection and inference controls.
- [x] Backend tests for selection, loopback validation, unknown models and API contracts.

## Verification still required
- [ ] Install dependencies and run pytest.
- [ ] Run Ruff and resolve all findings.
- [ ] Install frontend dependencies and run production build/tests.
- [ ] Verify with a running local Ollama runtime and a locally installed model.
- [ ] Exercise runtime-offline behaviour and verify no external network dependency.
- [ ] Review latency and memory behaviour under representative local models.

## Safety and limitations
- No automatic model download, shell execution or remote runtime access.
- Capability metadata is conservative; only chat is currently advertised for discovered Ollama models.
- The model catalogue is refreshed from Ollama and remains process-local; persistent model assignments and multi-agent orchestration are future work.
- Benchmark reports latency statistics, not model quality or fabricated throughput.
- Local inference quality, speed and memory use depend on the chosen runtime/model and host environment.

Phase 2 must not be certified complete until the verification checklist is executed and reviewed.
