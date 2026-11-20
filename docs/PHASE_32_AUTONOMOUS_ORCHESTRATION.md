# Phase 32 — Autonomous Intelligence and Parallel Orchestration

## Objective
Operate JPAI-6.2 Ultra, JPAI-6.2 Pro, JPAI-6 Mantra and specialist agents as a coordinated intelligence workforce with concurrent analysis, persistent shared memory, independent peer review, durable run records and bounded recovery.

## Implemented
- Bounded concurrent specialist inference using asynchronous fan-out and a shared concurrency semaphore.
- Shared local SQLite workspace memory. Each completed specialist contribution is committed with run, agent, model and response provenance.
- A second concurrent peer-review stage in which reviewers examine the combined first-pass workspace and identify disagreement, unsupported claims, missing evidence and risk.
- JPAI-6.2 Ultra synthesis that retains attribution and disagreement.
- Independent JPAI-6.2 Pro verification of the synthesis against the specialist and peer-review findings.
- Durable orchestration run ledger and ordered checkpoints for initialization, memory loading, specialist contributions, peer review, synthesis and verification.
- Run history and run-detail APIs: `GET /api/v1/model-fabric/council/runs` and `GET /api/v1/model-fabric/council/runs/{run_id}`.
- Partial-failure isolation: one specialist failure does not discard successful contributions.
- Bounded retries for transient provider rate-limit, server and transport failures.
- Dashboard display of run ID, memory writes and individual peer-review results.

## Execution sequence
1. Validate active agents and provider readiness.
2. Create a durable run record and checkpoint.
3. Retrieve relevant shared memories and provide them as explicitly untrusted reference context.
4. Fan out independent specialist analyses concurrently.
5. Persist each successful contribution immediately to the shared workspace.
6. Fan out independent peer reviews concurrently over the combined findings.
7. Synthesize with Ultra and independently verify with Pro.
8. Persist synthesis, verification and final run result.

## Accuracy and performance controls
- Independent first-pass analyses reduce anchoring on a single model answer.
- Cross-review explicitly searches for contradictions and missing evidence.
- Synthesis must preserve dissent and separate facts from assumptions.
- Pro verification provides a distinct audit pass.
- Concurrency is bounded by `JPAI_MODEL_FABRIC_MAX_CONCURRENCY`; each provider call is also bounded by the provider adapter semaphore.
- Transient provider failures receive at most two retries after the initial attempt, with bounded backoff and `Retry-After` support.
- Failed agents are reported separately; successful work remains available.
- SQLite WAL, busy timeout and short-lived transactions support concurrent memory writes.
- Every imported or model-generated memory item is provenance-labelled and remains unverified until separately validated.

## APIs
- `POST /api/v1/model-fabric/council` — execute a multi-agent council.
- `GET /api/v1/model-fabric/council/runs` — list recent durable runs.
- `GET /api/v1/model-fabric/council/runs/{run_id}` — inspect run status, result and checkpoints.
- `GET /api/v1/model-fabric/status` — inspect model-fabric configuration and parallel limit.

## Boundaries and next work
- The current council endpoint runs synchronously within the request while persisting run records and checkpoints. A process interruption can leave a run marked `running`; automatic worker lease recovery, queued background execution and true resume-from-checkpoint are future work.
- Shared memory is persistent and shared across agents, but first-pass agents receive a common memory snapshot; the peer-review stage is where they exchange and assess each other’s newly produced findings.
- Provider-enforced context/output limits, rate limits, availability and billing still apply to remote inference. Long tasks must be chunked and checkpointed; this phase does not claim unlimited single-call context.
- Model function-call proposals are not executed automatically. Shell, patch, computer-use and external actions remain separately governed and disabled unless an explicit executor is implemented.
- No live provider inference benchmark is claimed without configured credentials and a deliberate smoke test.

## Acceptance checklist
- [x] Parallel specialist fan-out
- [x] Shared persistent SQLite workspace
- [x] Per-contribution provenance
- [x] Parallel independent peer review
- [x] Ultra synthesis
- [x] Pro verification
- [x] Durable run ledger and checkpoints
- [x] Partial-failure isolation
- [x] Bounded transient retries
- [x] Run history API and dashboard visibility
- [ ] Background worker queue and process-independent task execution
- [ ] Resume/replay from last completed checkpoint
- [ ] Automated evaluation datasets and calibrated quality scoring
- [ ] Provider live latency/quality benchmarking
- [ ] Independent local model hosting for provider-limit independence