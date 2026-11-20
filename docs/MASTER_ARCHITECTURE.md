# JPAI Master Architecture

## Mission
JPAI is a local-first platform that coordinates personal, professional and enterprise intelligence through specialist agents, knowledge services and governed tools.

## Architectural principles
1. Local core first; online providers are optional capability extensions.
2. Modular domains with versioned contracts and explicit ownership.
3. Provider, model, tool and professional role are distinct concepts.
4. Least privilege and human approval for consequential operations.
5. Deterministic code governs permissions, limits and critical calculations.
6. Every capability has observable health, tests and recovery behaviour.
7. Data is portable; avoid unnecessary vendor lock-in.

## Logical layers
- Experience: desktop, Android and local web clients.
- Orchestration: task intake, planning, scheduling and agent coordination.
- Workforce: professional registry, departments, agents and supervision.
- Capability: research, engineering, enterprise, finance, trading and creative domains.
- Integration: tools, local services and universal API gateway.
- Intelligence infrastructure: memory, knowledge, files and project context.
- Foundation: runtime, storage, security, audit, backup and diagnostics.

## Delivery architecture
Begin as a modular monolith with explicit internal interfaces. Extract services only when independent scaling, isolation or deployment justifies the operational cost. Domain modules must not reach into one another's persistence internals.

## Core project boundaries
ETI, T-Bots, JPTI, ELSIM Engineering and X-STUDIOS remain distinct domains/products. Integrate them through versioned adapters and scoped permissions; do not merge their business logic or data ownership into a shared unbounded module.

## Phase 1 delivered boundary
This phase supplies the API shell, UI shell, configuration, health endpoint, test scaffolding and architecture baseline. It does not imply completion of orchestration, persistence, workforce or integrations.
