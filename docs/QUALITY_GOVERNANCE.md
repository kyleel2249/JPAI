# JPAI Quality Governance — Continuous Improvement & Root-Cause Resolution

## Mandatory operating standard

Every meaningful development or maintenance change follows:

**Build → Reassess → Improve → Test → Verify**

1. **Build:** implement a bounded change against an explicit objective and acceptance criteria.
2. **Reassess:** inspect the complete affected workflow and relevant surrounding systems after the change.
3. **Improve:** address weaknesses discovered during reassessment before expanding scope.
4. **Test:** run targeted tests, regression tests, security checks and relevant production builds.
5. **Verify:** inspect actual results, confirm acceptance criteria and record evidence. A queued or running CI job is not a pass.

The cycle is continuous. A verified result becomes the next baseline, not a reason to stop reassessing.

## Mandatory issue-resolution procedure

When a defect, security finding, regression, operational failure or quality gap is found, use this ordered process:

1. **Assess:** reproduce or validate the observation; record affected components, impact, severity, scope and evidence.
2. **Identify:** state the precise issue and distinguish symptoms from confirmed facts.
3. **Determine root cause:** trace the causal chain using logs, tests, dependency paths, configuration and code inspection. Do not guess.
4. **Fix:** implement a corrective action that addresses the cause, not merely the symptom. Preserve unrelated working behavior.
5. **Test:** add or update regression coverage and execute the relevant checks.
6. **Verify:** confirm the original failure is no longer reproducible, review collateral effects, inspect CI and record the verification evidence.

If the root cause is not established, the issue must remain in assessment or investigation; it must not be marked fixed or verified. If a fix cannot be tested, it must not be marked verified.

## JPAI implementation

The local SQLite-backed Quality Governance API and dashboard are available at:

- `GET /api/v1/quality/principles`
- `POST /api/v1/quality/cycles`
- `GET /api/v1/quality/cycles`
- `POST /api/v1/quality/cycles/{cycle_id}/advance`
- `POST /api/v1/quality/issues`
- `GET /api/v1/quality/issues`
- `POST /api/v1/quality/issues/{issue_id}/advance`
- `GET /api/v1/quality/events`

Cycle transitions are evidence-gated and sequential: `build → reassess → improve → test → verify`.

Issue transitions are evidence-gated and sequential: `reported → assessed → cause_identified → fix_implemented → tested → verified`.

Each transition and its audit event are written within one SQLite transaction. Conditional state updates prevent duplicate or out-of-order transitions. The store shares the configured local JPAI database path and creates additive tables; existing memory and agent records are preserved.

## Important governance rules

- A new issue starts as `reported`; it cannot jump directly to a fix.
- A fix cannot be recorded until assessment and root-cause identification are recorded.
- A verified issue and completed cycle cannot be advanced again.
- Evidence is required for every stage.
- Quality records are local operational records, not an external certification or proof of a deployment.
- Evidence text is supplied by the operator or an integrated workflow; JPAI does not fabricate test results or automatically attest that a test ran.
- The current API does not yet provide user/role identity or multi-user approvals. It is designed for the local-first single-operator deployment model.

## CI and dependency security

The frontend CI now emits a structured npm audit summary with affected package names, severity, vulnerable ranges and fix availability. Remediation must be based on the actual audit report and compatibility tests. Do not use `npm audit fix --force` as a blanket response: npm documents that force may install versions outside declared ranges, including SemVer-major changes. See [npm audit documentation](https://docs.npmjs.com/cli/audit/) and [npm dependency audit guidance](https://docs.npmjs.com/auditing-package-dependencies-for-security-vulnerabilities/).

The repository currently has no committed frontend package lockfile. This is a reproducibility gap: `npm install` resolves compatible versions at install time, so the dependency tree can change between runs. The next dependency hardening task is to generate and commit a reviewed lockfile, then use `npm ci` in CI. Do not claim the reported vulnerabilities are remediated until the new audit report confirms it.
