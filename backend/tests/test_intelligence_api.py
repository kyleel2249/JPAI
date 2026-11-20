from fastapi.testclient import TestClient
from jpai_api.main import app
from jpai_api.routes import intelligence as routes
from jpai_api.intelligence.schemas import ModelProfile

client = TestClient(app)


class FakeRuntime:
    async def health(self):
        return {"available": True, "runtime": "fake", "version": "test"}


class FakeService:
    runtime = FakeRuntime()

    async def discover(self):
        return [ModelProfile(id="local-chat", provider="fake", display_name="Local Chat", capabilities=["chat"])]

    async def rank(self, capability, preferred_provider=None, minimum_context=None, max_latency_ms=None, minimum_reliability=0.0):
        selected = await self.select(capability, preferred_provider, minimum_context)
        return [{"model": selected, "score": 0.9, "reason": "test capability match"}] if selected else []

    async def select(self, capability, preferred_provider=None, minimum_context=None, max_latency_ms=None, minimum_reliability=0.0):
        if capability == "chat":
            return (await self.discover())[0]
        return None

    async def infer(self, model, prompt, system, temperature):
        if model != "local-chat":
            from jpai_api.intelligence.runtime import ModelNotFound
            raise ModelNotFound("not discovered")
        return {"model": model, "provider": "fake", "response": "READY", "duration_ms": 1.0,
                "prompt_tokens": 2, "completion_tokens": 1}


def test_local_runtime_health_endpoint(monkeypatch):
    monkeypatch.setattr(routes, "get_service", lambda: FakeService())
    response = client.get("/api/v1/intelligence/runtime")
    assert response.status_code == 200
    assert response.json()["available"] is True


def test_capability_selection_endpoint(monkeypatch):
    monkeypatch.setattr(routes, "get_service", lambda: FakeService())
    response = client.post("/api/v1/intelligence/models/select", json={"capability": "chat"})
    assert response.status_code == 200
    assert response.json()["selected"]["id"] == "local-chat"


def test_unknown_capability_fails_closed(monkeypatch):
    monkeypatch.setattr(routes, "get_service", lambda: FakeService())
    response = client.post("/api/v1/intelligence/models/select", json={"capability": "vision"})
    assert response.status_code == 404


def test_inference_endpoint_returns_model_metadata(monkeypatch):
    monkeypatch.setattr(routes, "get_service", lambda: FakeService())
    response = client.post("/api/v1/intelligence/infer", json={"model": "local-chat", "prompt": "hello"})
    assert response.status_code == 200
    assert response.json()["response"] == "READY"
    assert response.json()["provider"] == "fake"


def test_auto_inference_selects_capable_model(monkeypatch):
    monkeypatch.setattr(routes, "get_service", lambda: FakeService())
    response = client.post("/api/v1/intelligence/infer/auto", json={"capability": "chat", "prompt": "hello"})
    assert response.status_code == 200
    assert response.json()["model"] == "local-chat"


def test_parallel_model_comparison_reports_each_result(monkeypatch):
    monkeypatch.setattr(routes, "get_service", lambda: FakeService())
    response = client.post("/api/v1/intelligence/models/compare", json={
        "models": ["local-chat", "not-discovered"], "prompt": "Compare this prompt"
    })
    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "completed"
    assert response.json()["results"][1]["status"] == "unavailable"


def test_model_comparison_rejects_duplicate_models(monkeypatch):
    monkeypatch.setattr(routes, "get_service", lambda: FakeService())
    response = client.post("/api/v1/intelligence/models/compare", json={
        "models": ["local-chat", "local-chat"], "prompt": "hello"
    })
    assert response.status_code == 422
