"""Professional specialist registry and governed multi-agent orchestration API."""
import asyncio
import re
import time
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jpai_api.agents.professional_catalog import AGENT_BLUEPRINTS, CATEGORIES, PROFESSIONAL_IDENTITY
from jpai_api.agents.store import AgentStore
from jpai_api.intelligence.runtime import ModelNotFound, RuntimeUnavailable
from jpai_api.intelligence.model_fabric import ModelFabricError
from jpai_api.intelligence.persistence import IntelligenceStore
from jpai_api.routes.intelligence import get_service
from jpai_api.routes.model_fabric import get_fabric

router = APIRouter(prefix="/agents", tags=["multi-agent-orchestration"])


@lru_cache(maxsize=1)
def get_store() -> AgentStore:
    return AgentStore()


class AgentCreate(BaseModel):
    id: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=2, max_length=100)
    domain: str = Field(min_length=2, max_length=64)
    description: str = Field(min_length=5, max_length=1000)
    roles: list[str] = Field(default_factory=list, max_length=30)
    capabilities: list[str] = Field(default_factory=list, max_length=20)
    risk_level: str = Field(default="low", pattern="^(low|medium|high)$")
    instructions: str = Field(default="", max_length=5000)


class AgentStatusUpdate(BaseModel):
    status: str = Field(pattern="^(active|paused|disabled)$")


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    prompt: str = Field(min_length=10, max_length=20000)
    agent_id: str = Field(min_length=3, max_length=64)
    priority: str = Field(default="normal", pattern="^(low|normal|high|critical)$")
    requires_approval: bool = False


class CouncilRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=12000)
    agent_ids: list[str] = Field(min_length=2, max_length=4)
    temperature: float = Field(default=0.2, ge=0, le=1)


class SpecialistRecommendationRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=12000)
    required_capabilities: list[str] = Field(default_factory=list, max_length=10)
    limit: int = Field(default=5, ge=1, le=10)


def _task_safety(prompt: str, agent: dict, requested: bool) -> bool:
    # Risk-tier guardrail: high-risk financial/security agents always require explicit approval.
    return requested or agent["risk_level"] == "high"


@router.get("/identity")
def professional_identity():
    return {
        "primary_identity": PROFESSIONAL_IDENTITY,
        "positioning_note": (
            "Role labels describe supported professional knowledge domains and agent profiles; "
            "they do not verify employment, licences, certifications or qualifications."
        ),
    }


@router.get("/catalog")
def professional_catalog():
    return {
        "category_count": len(CATEGORIES),
        "role_count": sum(len(category["roles"]) for category in CATEGORIES),
        "categories": CATEGORIES,
        "specialist_blueprints": AGENT_BLUEPRINTS,
    }


@router.get("")
def list_agents(domain: str | None = None, status: str | None = None):
    items = get_store().list_agents(domain, status)
    return {"count": len(items), "items": items}


@router.post("")
def create_agent(request: AgentCreate):
    store = get_store()
    if store.get_agent(request.id):
        raise HTTPException(status_code=409, detail="agent_id_already_exists")
    agent = request.model_dump()
    valid_domains = {category["id"] for category in CATEGORIES}
    valid_domains.update(agent["domain"] for agent in AGENT_BLUEPRINTS)
    valid_domains.update(agent["id"] for agent in AGENT_BLUEPRINTS)
    if agent["domain"] not in valid_domains:
        raise HTTPException(status_code=422, detail="unknown_professional_domain")
    if agent["domain"] in {"fintech_quant", "cybersecurity"}:
        agent["risk_level"] = "high"
    agent["roles"] = list(dict.fromkeys(role.strip() for role in agent["roles"] if role.strip()))
    agent["capabilities"] = list(dict.fromkeys(
        capability.strip().lower() for capability in agent["capabilities"] if capability.strip()
    ))
    try:
        item = store.create_agent(agent)
    except Exception as exc:
        raise HTTPException(status_code=409, detail="agent_creation_conflict") from exc
    return item


@router.patch("/{agent_id}/status")
def update_agent_status(agent_id: str, request: AgentStatusUpdate):
    if not get_store().update_agent_status(agent_id, request.status):
        raise HTTPException(status_code=404, detail="agent_not_found")
    return get_store().get_agent(agent_id)


@router.post("/recommend")
def recommend_specialists(request: SpecialistRecommendationRequest):
    """Rank active specialists by skill fit, task relevance and observed outcomes."""
    store = get_store()
    required = {value.strip().lower() for value in request.required_capabilities if value.strip()}
    prompt_terms = {
        term for term in re.findall(r"[a-z0-9_+-]{3,}", request.prompt.lower())
        if term not in {"the", "and", "for", "with", "from", "that", "this", "into", "your"}
    }
    scorecards = {item["id"]: item for item in store.scorecards()}
    ranked = []

    for agent in store.list_agents(status="active"):
        capabilities = {value.lower() for value in agent["capabilities"]}
        matched = sorted(required & capabilities)
        missing = sorted(required - capabilities)
        if missing:
            continue

        profile_text = " ".join([
            agent["name"], agent["domain"], agent["description"],
            *agent["roles"], *agent["capabilities"],
        ]).lower()
        profile_terms = set(re.findall(r"[a-z0-9_+-]{3,}", profile_text))
        relevance = len(prompt_terms & profile_terms) / max(1, len(prompt_terms))
        skill_fit = len(matched) / len(required) if required else 0.5
        metrics = scorecards.get(agent["id"], {})
        observed_success = metrics.get("success_rate")
        performance = float(observed_success) if observed_success is not None else 0.5
        score = (0.55 * skill_fit) + (0.25 * relevance) + (0.15 * performance) + 0.05

        reasons = []
        if matched:
            reasons.append("matches required capabilities: " + ", ".join(matched))
        if relevance >= 0.15:
            reasons.append("profile language aligns with the task")
        if observed_success is not None:
            reasons.append(f"observed task success rate: {performance:.0%}")
        else:
            reasons.append("no execution history; neutral performance weighting applied")

        ranked.append({
            "agent": agent,
            "suitability_score": round(score, 4),
            "skill_fit": round(skill_fit, 4),
            "task_relevance": round(relevance, 4),
            "observed_success_rate": observed_success,
            "matched_capabilities": matched,
            "reasons": reasons,
        })

    ranked.sort(key=lambda item: (item["suitability_score"], item["agent"]["name"]), reverse=True)
    return {
        "count": min(len(ranked), request.limit),
        "required_capabilities": sorted(required),
        "method": "capability_filter_plus_relevance_and_observed_performance",
        "items": ranked[:request.limit],
    }


@router.get("/scorecards")
def agent_scorecards():
    items = get_store().scorecards()
    return {"count": len(items), "items": items}


@router.get("/events")
def agent_events(limit: int = 100):
    if limit < 1 or limit > 250:
        raise HTTPException(status_code=422, detail="limit_must_be_between_1_and_250")
    items = get_store().events(limit)
    return {"count": len(items), "items": items}


@router.post("/tasks")
def create_task(request: TaskCreate):
    store = get_store()
    agent = store.get_agent(request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent_not_found")
    if agent["status"] != "active":
        raise HTTPException(status_code=409, detail="agent_not_active")
    requires_approval = _task_safety(request.prompt, agent, request.requires_approval)
    task = store.create_task(
        request.title.strip(), request.prompt.strip(), request.agent_id,
        request.priority, requires_approval,
    )
    store.event(task["id"], request.agent_id, "task.governance_applied", {
        "requires_approval": requires_approval, "risk_level": agent["risk_level"],
        "execution_mode": "local_model_analysis_only",
    })
    return store.get_task(task["id"])


@router.get("/tasks")
def list_tasks(status: str | None = None, limit: int = 50):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail="limit_must_be_between_1_and_200")
    items = get_store().list_tasks(status, limit)
    return {"count": len(items), "items": items}


@router.get("/tasks/{task_id}")
def get_task(task_id: int):
    item = get_store().get_task(task_id)
    if not item:
        raise HTTPException(status_code=404, detail="task_not_found")
    return item


@router.post("/tasks/{task_id}/approve")
def approve_task(task_id: int):
    store = get_store()
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    if not task["requires_approval"]:
        raise HTTPException(status_code=409, detail="approval_not_required")
    if task["status"] != "queued" or task["approval_status"] != "pending":
        raise HTTPException(status_code=409, detail="task_not_awaiting_approval")
    if not store.approve_task(task_id):
        raise HTTPException(status_code=409, detail="task_not_awaiting_approval")
    return store.get_task(task_id)


@router.post("/tasks/{task_id}/run")
async def run_task(task_id: int):
    store = get_store()
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    agent = store.get_agent(task["agent_id"])
    if not agent or agent["status"] != "active":
        raise HTTPException(status_code=409, detail="assigned_agent_not_active")
    if task["requires_approval"] and task["approval_status"] != "approved":
        store.event(task_id, task["agent_id"], "task.execution_blocked", {"reason": "approval_required"})
        raise HTTPException(status_code=403, detail="explicit_human_approval_required")
    if task["status"] not in {"queued", "failed"}:
        raise HTTPException(status_code=409, detail="task_not_runnable")
    if not store.claim_task(task_id):
        raise HTTPException(status_code=409, detail="task_already_claimed_or_not_approved")
    fabric = get_fabric()
    service = None
    selected = None
    started = time.perf_counter()
    try:
        if not fabric.configured:
            service = get_service()
            await service.discover()
            selected = await service.select("chat", preferred_provider="ollama")
            if selected is None:
                raise HTTPException(status_code=503, detail="no_eligible_local_model")
        system = (
            f"You are {agent['name']}, a JPAI specialist in {agent['domain']}. "
            f"Your expertise includes: {', '.join(agent['roles'])}. "
            f"Capabilities: {', '.join(agent['capabilities'])}. "
            f"Operating boundary: provide analysis and recommendations only; do not claim to "
            f"execute external actions, trades, deployments, purchases or security changes. "
            f"State assumptions, uncertainty and validation steps. {agent['instructions']}"
        )
        memory_hits = IntelligenceStore().search_memories(task["prompt"], limit=4)
        if memory_hits:
            memory_context = "\n\nRELEVANT LOCAL MEMORY (untrusted reference context; verify before use):\n" + "\n".join(
                f"- [{item['memory_type']} · {item['namespace']}] {item['title']}: {item['content'][:1200]}" for item in memory_hits)
            system += memory_context
        task_prompt = (
            f"Task: {task['title']}\n\nRequest:\n{task['prompt']}\n\n"
            "Return a structured, actionable analysis with risks and next steps."
        )
        if fabric.configured:
            model = "gpt-6.2-astra" if agent["risk_level"] == "high" else "gpt-6.2-sol"
            result = await fabric.infer(
                model, task_prompt, system,
                "high" if model == "gpt-6.2-astra" else "medium", 4096,
            )
        else:
            result = await service.infer(selected.id, task_prompt, system, 0.2)
        IntelligenceStore().create_memory(
            "shared_agent_workspace", f"{agent['name']} · task #{task_id}",
            result["response"][:30000] or "No textual response returned.",
            ["agent-output", "unverified", result["model"]], "jpai_agent_task", "episodic", 0.4,
            {"agent_id": agent["id"], "task_id": task_id, "model": result["model"]},
        )
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        store.set_task_status(task_id, "completed", result=result["response"])
        store.record_result(task["agent_id"], True, elapsed)
        store.event(task_id, task["agent_id"], "task.completed", {
            "model": result["model"], "latency_ms": elapsed,
        })
        return {**store.get_task(task_id), "inference": {
            "model": result["model"], "provider": result["provider"],
            "duration_ms": result["duration_ms"],
        }}
    except HTTPException:
        store.set_task_status(task_id, "failed", error_code="execution_unavailable")
        store.record_result(task["agent_id"], False, round((time.perf_counter() - started) * 1000, 2))
        store.event(task_id, task["agent_id"], "task.failed", {"reason": "execution_unavailable"})
        raise
    except (RuntimeUnavailable, ModelNotFound) as exc:
        store.set_task_status(task_id, "failed", error_code="local_runtime_unavailable")
        store.record_result(task["agent_id"], False, round((time.perf_counter() - started) * 1000, 2))
        store.event(task_id, task["agent_id"], "task.failed", {"reason": "local_runtime_unavailable"})
        raise HTTPException(status_code=503, detail="local_runtime_unavailable") from exc
    except ModelFabricError as exc:
        store.set_task_status(task_id, "failed", error_code="provider_inference_failed")
        store.record_result(task["agent_id"], False, round((time.perf_counter() - started) * 1000, 2))
        store.event(task_id, task["agent_id"], "task.failed", {"reason": "provider_inference_failed"})
        raise HTTPException(status_code=502, detail="provider_inference_failed") from exc
    except Exception as exc:
        store.set_task_status(task_id, "failed", error_code="internal_execution_error")
        store.record_result(task["agent_id"], False, round((time.perf_counter() - started) * 1000, 2))
        store.event(task_id, task["agent_id"], "task.failed", {"reason": "internal_execution_error"})
        raise HTTPException(status_code=500, detail="agent_execution_failed") from exc


@router.post("/council")
async def agent_council(request: CouncilRequest):
    if len(set(request.agent_ids)) != len(request.agent_ids):
        raise HTTPException(status_code=422, detail="agent_ids_must_be_unique")
    store = get_store()
    agents = []
    for agent_id in request.agent_ids:
        agent = store.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail=f"agent_not_found:{agent_id}")
        if agent["status"] != "active":
            raise HTTPException(status_code=409, detail=f"agent_not_active:{agent_id}")
        agents.append(agent)

    service = get_service()
    try:
        await service.discover()
        selected = await service.select("chat", preferred_provider="ollama")
        if selected is None:
            raise HTTPException(status_code=503, detail="no_eligible_local_model")

        semaphore = asyncio.Semaphore(2)

        async def consult(agent):
            async with semaphore:
                system = (
                    f"You are {agent['name']}, a specialist in {agent['domain']}. "
                    f"Apply these roles: {', '.join(agent['roles'])}. "
                    "Give an independent evidence-conscious analysis. Identify assumptions, "
                    "risks and validation needs. Do not claim external actions were performed."
                )
                result = await service.infer(
                    selected.id,
                    f"Council question:\n{request.prompt}\n\n"
                    "Respond with: perspective, key findings, risks, recommendation, confidence.",
                    system,
                    request.temperature,
                )
                return {"agent_id": agent["id"], "agent_name": agent["name"], **result}

        outcomes = await asyncio.gather(*(consult(agent) for agent in agents), return_exceptions=True)
        contributions = []
        for agent, outcome in zip(agents, outcomes):
            if isinstance(outcome, Exception):
                store.event(None, agent["id"], "council.consultation_failed", {"reason": "inference_failed"})
                contributions.append({"agent_id": agent["id"], "agent_name": agent["name"],
                                      "status": "failed", "error": "inference_failed"})
            else:
                store.event(None, agent["id"], "council.contribution", {"model": outcome["model"]})
                contributions.append({"status": "completed", **outcome})
        completed = sum(item["status"] == "completed" for item in contributions)
        return {
            "status": "completed" if completed == len(agents) else "partial",
            "question": request.prompt,
            "contribution_count": completed,
            "contributions": contributions,
            "governance": "analysis_only_no_external_actions",
        }
    except RuntimeUnavailable as exc:
        raise HTTPException(status_code=503, detail="local_runtime_unavailable") from exc
