# Phase 7 — Quality Governance & Continuous Improvement

## Objective

Make continuous reassessment and evidence-led issue resolution first-class JPAI capabilities. The development standards are embedded in a local API, persistent quality records, audit trail, dashboard workspace, regression tests and CI dependency-audit gate.

## Delivered capabilities

- Quality Governance API under `/api/v1/quality`.
- Local SQLite quality-cycle and issue registries.
- Build → Reassess → Improve → Test → Verify cycle with ordered, evidence-required transitions.
- Issue lifecycle: Reported → Assessed → Cause Identified → Fix Implemented → Tested → Verified.
- Root-cause and corrective-action evidence recorded separately.
- Conditional state transitions and event writes occur in the same transaction.
- Repeated, skipped and out-of-order transitions are rejected.
- Quality dashboard workspace includes cycle creation, issue registration, evidence capture, progress controls and audit timeline.
- CI emits machine-readable npm audit diagnostics and enforces zero moderate-or-higher advisories.
- Upgraded the vulnerable Vite/Vitest toolchain to Vite 8 and Vitest 4.1.12; React plugin updated to v6.

## Reassessment and cause-based improvements

### Dependency security
The previous CI report showed six findings. The detailed npm audit report identified:
- `vite` high severity and `esbuild` moderate severity from the older Vite toolchain.
- `vitest` critical severity, with affected `@vitest/mocker`, `tinypool` and `vite-node` dependency paths.
- The audit's compatible remediation recommendation required a SemVer-major toolchain migration to Vite 8 and Vitest 4.1.12. This was not a blanket `npm audit fix --force`; the direct package manifests were updated deliberately, Node 20.19 was selected to meet Vite 8's runtime requirement, and build/tests/audit are re-run in CI.
- The repository does not yet contain a committed package-lock file. CI still resolves dependencies from the manifest; lockfile generation and npm ci adoption remain a reproducibility task.

### Existing system governance
- Quality transitions use compare-and-swap state predicates, so concurrent or duplicate requests cannot silently advance the same record twice.
- Evidence and state transitions are persisted in the same transaction.
- Existing memory and agent data are preserved because the quality store adds tables to the configured local database.

## API endpoints

- `GET /api/v1/quality/principles`
- `POST /api/v1/quality/cycles`
- `GET /api/v1/quality/cycles`
- `POST /api/v1/quality/cycles/{cycle_id}/advance`
- `POST /api/v1/quality/issues`
- `GET /api/v1/quality/issues`
- `POST /api/v1/quality/issues/{issue_id}/advance`
- `GET /api/v1/quality/events`

## Safety and limitations

- JPAI requires evidence text but does not claim that an external test or verification occurred merely because an operator entered text.
- The local operator is the current audit actor; multi-user identity, approval roles and cryptographic evidence signing are future governance work.
- The system remains local-first. No hosted quality service is required.
- The npm audit gate is strict at moderate severity and above. CI is the final source of truth for the upgraded toolchain.

## Acceptance

See `docs/QUALITY_GOVERNANCE_ACCEPTANCE.md`. Completion is contingent on the final main-branch CI run being green, including npm audit, frontend build/tests, backend tests and Ruff.
