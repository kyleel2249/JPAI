# Phase 4 — Professional Intelligence & Multi-Agent Orchestration

## Professional identity and role taxonomy
JPAI now includes a structured professional taxonomy covering:
- Core professional identities and software engineering.
- AI, machine learning, intelligent automation and agentic systems.
- Quantitative finance, algorithmic trading, FinTech and risk.
- Data science, analytics and business intelligence.
- Cybersecurity and infrastructure assurance.
- Entrepreneurship, business development and digital transformation.
- Web engineering, CMS, SEO and digital commerce.
- Content, technical writing, education and media.
- Product engineering, platform development and ecosystem architecture.
- Technology strategy and systems building.

The catalogue is data-driven and searchable through `GET /api/v1/agents/catalog`. It contains the role labels supplied for JPAI's professional specialisation profile. These labels describe knowledge domains and system configurations; they do not claim that any person holds every listed job, licence or certification.

## Specialist workforce
The seeded registry provides specialist profiles for:
1. Chief Systems Architect
2. Full-Stack Engineering Specialist
3. Platform & DevOps Specialist
4. Automation & Integration Specialist
5. AI & Agentic Systems Architect
6. Machine Learning & Applied Research Specialist
7. Quantitative Research & Trading Systems Specialist
8. Financial Risk & Portfolio Specialist
9. Data & Business Intelligence Specialist
10. Cybersecurity & Application Assurance Specialist
11. Product & Technology Strategy Specialist
12. Web, CMS & Digital Commerce Specialist
13. Content, Media & Technical Communications Specialist
14. Enterprise Platform & Ecosystem Strategist
15. Business Operations & Entrepreneurship Specialist
16. Quality, Reliability & Technical Review Specialist

Custom agents can be registered with explicit roles, capabilities, risk tiers and operating instructions. Agents can be paused or disabled.

## Orchestration API
- `GET /api/v1/agents/identity` — primary professional identity and positioning note.
- `GET /api/v1/agents/catalog` — role taxonomy and specialist blueprints.
- `GET /api/v1/agents` — registry, with optional domain/status filters.
- `POST /api/v1/agents` — create a specialist profile.
- `PATCH /api/v1/agents/{agent_id}/status` — activate, pause or disable.
- `POST /api/v1/agents/tasks` — enqueue a specialist task.
- `GET /api/v1/agents/tasks` and `GET /api/v1/agents/tasks/{task_id}` — inspect work.
- `POST /api/v1/agents/tasks/{task_id}/approve` — explicit human approval.
- `POST /api/v1/agents/tasks/{task_id}/run` — execute local-model analysis.
- `POST /api/v1/agents/council` — parallel independent specialist perspectives (2–4 agents).
- `GET /api/v1/agents/scorecards` — assignment, completion, failure and latency metrics.
- `GET /api/v1/agents/events` — audit events.

## Governance and safety
- Agent profiles are bounded by declared roles, capabilities, risk tier and system instructions.
- High-risk quantitative-finance and cybersecurity agents require explicit approval before task execution.
- Task execution is currently local-model analysis only. No agent is granted shell, filesystem, browser, network, trading, payment, deployment or account-control tools.
- Council contributions are independent analysis outputs; JPAI does not represent them as verified facts or a substitute for professional judgement.
- Task events, approvals and outcomes are persisted in the local SQLite database.
- Agent execution is synchronous in this phase; durable background workers, retry policies, dependency graphs and distributed coordination are later hardening work.

## Local persistence
Agent registry, task queue, events and scorecards use the configured `JPAI_DATABASE_PATH` SQLite database (default `data/jpai.sqlite3`), alongside existing JPAI memory and routing telemetry.
