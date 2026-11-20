from fastapi.testclient import TestClient

from jpai_api.main import app
from jpai_api.routes import agents as agent_routes

client = TestClient(app)


def reset_store(monkeypatch, tmp_path):
    agent_routes.get_store.cache_clear()
    monkeypatch.setenv("JPAI_DATABASE_PATH", str(tmp_path / "agents.sqlite3"))
    return agent_routes.get_store()


def test_professional_catalog_contains_all_domains_and_role_groups(monkeypatch, tmp_path):
    reset_store(monkeypatch, tmp_path)
    response = client.get("/api/v1/agents/catalog")
    assert response.status_code == 200
    payload = response.json()
    assert payload["category_count"] >= 10
    assert payload["role_count"] >= 100
    role_names = {role for category in payload["categories"] for role in category["roles"]}
    assert "Software Engineer" in role_names
    assert "Quantitative Researcher" in role_names
    assert "Cybersecurity Engineer" in role_names
    assert "Technical Writer" in role_names


def test_seeded_specialist_registry_is_persistent(monkeypatch, tmp_path):
    store = reset_store(monkeypatch, tmp_path)
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert "chief_architect" in ids
    assert "quant_research" in ids
    assert "cybersecurity" in ids
    assert store.get_agent("ai_architect") is not None


def test_high_risk_agent_task_requires_human_approval(monkeypatch, tmp_path):
    reset_store(monkeypatch, tmp_path)
    response = client.post("/api/v1/agents/tasks", json={
        "title": "Review trading strategy risk",
        "prompt": "Assess the proposed trading strategy and identify execution and portfolio risks.",
        "agent_id": "quant_research",
    })
    assert response.status_code == 200
    task = response.json()
    assert task["requires_approval"] is True
    assert task["approval_status"] == "pending"
    blocked = client.post(f"/api/v1/agents/tasks/{task['id']}/run")
    assert blocked.status_code == 403


def test_explicit_approval_unblocks_task_for_execution(monkeypatch, tmp_path):
    reset_store(monkeypatch, tmp_path)
    response = client.post("/api/v1/agents/tasks", json={
        "title": "Security architecture review",
        "prompt": "Review the proposed authentication architecture and list security risks.",
        "agent_id": "cybersecurity",
    })
    task_id = response.json()["id"]
    approved = client.post(f"/api/v1/agents/tasks/{task_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["approval_status"] == "approved"


def test_custom_agent_creation_and_duplicate_protection(monkeypatch, tmp_path):
    reset_store(monkeypatch, tmp_path)
    payload = {
        "id": "custom_product_research",
        "name": "Product Research Specialist",
        "domain": "product_strategy",
        "description": "Analyses product opportunities and user requirements.",
        "roles": ["Product Strategist"],
        "capabilities": ["product_strategy", "research"],
        "risk_level": "low",
    }
    first = client.post("/api/v1/agents", json=payload)
    assert first.status_code == 200
    duplicate = client.post("/api/v1/agents", json=payload)
    assert duplicate.status_code == 409


def test_paused_agent_cannot_receive_tasks(monkeypatch, tmp_path):
    reset_store(monkeypatch, tmp_path)
    paused = client.patch("/api/v1/agents/fullstack_engineer/status", json={"status": "paused"})
    assert paused.status_code == 200
    response = client.post("/api/v1/agents/tasks", json={
        "title": "Implement an API",
        "prompt": "Design an API endpoint and provide a detailed implementation plan.",
        "agent_id": "fullstack_engineer",
    })
    assert response.status_code == 409

class FakeModel:
    id = "test-local-model"


class FakeService:
    async def discover(self):
        return [FakeModel()]

    async def select(self, capability, preferred_provider=None):
        assert capability == "chat"
        return FakeModel()

    async def infer(self, model, prompt, system, temperature):
        return {
            "model": model,
            "provider": "test",
            "response": "Structured specialist analysis.",
            "duration_ms": 2.0,
        }


def test_low_risk_task_runs_through_local_model_and_records_result(monkeypatch, tmp_path):
    reset_store(monkeypatch, tmp_path)
    monkeypatch.setattr(agent_routes, "get_service", lambda: FakeService())
    created = client.post("/api/v1/agents/tasks", json={
        "title": "Review API design",
        "prompt": "Review this API design and propose maintainability improvements.",
        "agent_id": "fullstack_engineer",
    })
    task_id = created.json()["id"]
    completed = client.post(f"/api/v1/agents/tasks/{task_id}/run")
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["result"] == "Structured specialist analysis."
    scorecards = client.get("/api/v1/agents/scorecards").json()["items"]
    engineer = next(item for item in scorecards if item["id"] == "fullstack_engineer")
    assert engineer["completed"] == 1


def test_agent_council_returns_independent_specialist_contributions(monkeypatch, tmp_path):
    reset_store(monkeypatch, tmp_path)
    monkeypatch.setattr(agent_routes, "get_service", lambda: FakeService())
    response = client.post("/api/v1/agents/council", json={
        "prompt": "Assess the architecture and delivery risks for a local-first AI platform.",
        "agent_ids": ["chief_architect", "fullstack_engineer"],
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["contribution_count"] == 2
    assert payload["governance"] == "analysis_only_no_external_actions"
