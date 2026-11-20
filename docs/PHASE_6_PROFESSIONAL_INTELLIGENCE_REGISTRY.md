# Phase 6 — Professional Intelligence Registry

## Objective

Turn the Phase 4 specialist catalogue into an operational, explainable registry that can recommend an active specialist using explicit capability fit, task-language relevance and recorded execution outcomes.

## Implemented

- Added `POST /api/v1/agents/recommend`.
- Accepts a task prompt, optional required capability names and a bounded result limit.
- Hard-filters candidates that do not possess every explicitly required capability.
- Ranks remaining active specialists using a transparent deterministic score:
  - 55% required capability fit (neutral 0.5 when no explicit capabilities are supplied).
  - 25% task/profile lexical relevance.
  - 15% observed task success rate (neutral 0.5 when there is no execution history).
  - 5% active availability.
- Returns the score components, matched capabilities and human-readable reasons.
- Dashboard can request recommendations, select the suggested specialist, and inspect workforce scorecards and recent governance events.
- Existing specialist creation remains available for adding custom specialist profiles; finance and cybersecurity domain risk-tier enforcement remains in place.

## Reassessment and improvements to prior phases

### Phase 3 — Governed API Gateway
- Moved rate-limit admission control ahead of request-body buffering. Rejected requests no longer force the gateway to read and buffer their bodies.
- Computes the remaining quota while holding the limiter lock, avoiding a racy post-lock count.
- Added regression coverage for early rejection and quota headers.
- The limiter remains process-local; multi-worker deployments still require shared atomic storage.

### Phase 4 — Multi-Agent Orchestration
- Made human approval a conditional database transition and writes the approval event in the same SQLite transaction.
- Made task claiming and the task-started audit event atomic.
- Duplicate approvals are rejected and cannot create duplicate approval events.
- Added regression coverage for approval idempotency and task-start audit consistency.
- Execution remains synchronous local-model analysis. No external tools, trades, deployments, payments or account actions are enabled.

### Phase 5 — Memory & Knowledge Infrastructure
- Reviewed typed memory, namespace filters, archive behavior, graph persistence and specialist retrieval boundaries.
- This phase does not introduce embeddings, automatic extraction, contradiction resolution, secure erasure or fine-grained per-user access controls. Those remain explicit future work rather than implied capabilities.

## Recommendation contract

The recommender is a decision-support feature, not an autonomous authority. A score is a relative ranking within the currently active registry, not a calibrated probability of success or a guarantee of expertise. Missing performance history receives neutral weighting. Explicit required capabilities are strict filters; if no active specialist declares all required capabilities, the endpoint returns an empty list rather than silently relaxing requirements.

## Safety and operational boundaries

- Recommendations do not create tasks or approve execution.
- Task creation and high-risk approval requirements remain unchanged.
- Only active specialists are considered.
- Capability strings are registry metadata and should be curated; they are not independently verified credentials.
- Recommendation results are deterministic for the same registry, metrics and request.

## Verification

- Backend tests cover exact capability filtering and empty-match behavior.
- CI remains the authoritative verification for backend tests, Ruff, frontend TypeScript build and frontend tests.
