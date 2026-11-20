import pytest
from fastapi.testclient import TestClient

from jpai_api.intelligence.model_fabric import (
    MODEL_ALIASES, MODEL_SPECS, ModelFabricError, OpenAIResponsesRuntime,
    ProviderNotConfigured, canonical_model_id,
)
from jpai_api.main import app
from jpai_api.middleware.gateway import GatewayMiddleware
from jpai_api.routes import model_fabric as routes

client = TestClient(app)


def test_catalog_exposes_only_jpai_public_identities():
    items = OpenAIResponsesRuntime(None).catalog()
    assert {item["id"] for item in items} == set(MODEL_SPECS)
    assert {item["name"] for item in items} == {
        "JPAI-6.2 Ultra", "JPAI-6.2 Pro", "JPAI-6 Mantra",
    }
    assert all(item["provider_limits_apply"] for item in items)
    assert all(item["context_window"] == 1_050_000 for item in items)


def test_legacy_provider_ids_resolve_to_jpai_identities():
    assert len(MODEL_ALIASES) == 3
    assert canonical_model_id("gpt-6.2-astra") == "jpai-6.2-ultra"
    assert canonical_model_id("gpt-6.2-sol") == "jpai-6.2-pro"
    assert canonical_model_id("gpt-6-luna") == "jpai-6-mantra"


def test_catalog_does_not_leak_api_key():
    runtime = OpenAIResponsesRuntime("secret-value")
    assert runtime.configured
    assert "secret-value" not in str(runtime.catalog())


@pytest.mark.asyncio
async def test_missing_key_fails_closed():
    with pytest.raises(ProviderNotConfigured):
        await OpenAIResponsesRuntime(None).infer("jpai-6.2-pro", "hello")


@pytest.mark.asyncio
async def test_policy_rejects_invalid_model_effort_and_tool():
    runtime = OpenAIResponsesRuntime("key")
    with pytest.raises(ModelFabricError):
        await runtime.infer("invalid", "hello")
    with pytest.raises(ModelFabricError):
        await runtime.infer("jpai-6.2-ultra", "hello", reasoning_effort="none")
    with pytest.raises(ModelFabricError):
        await runtime.infer("jpai-6.2-pro", "hello", tools=["computer"])


def test_cost_estimation_uses_jpai_identity_and_cached_tokens():
    usage = {"input_tokens": 1000, "output_tokens": 500,
             "input_tokens_details": {"cached_tokens": 400}}
    assert OpenAIResponsesRuntime.cost("jpai-6.2-pro", usage) == pytest.approx(
        (600 * 2 + 400 * .1 + 500 * 10) / 1_000_000
    )
    assert OpenAIResponsesRuntime.cost("gpt-6.2-sol", usage) == pytest.approx(
        OpenAIResponsesRuntime.cost("jpai-6.2-pro", usage)
    )


def _reset_gateway_rate_limit():
    layer = app.middleware_stack
    for _ in range(12):
        if isinstance(layer, GatewayMiddleware):
            layer._hits.clear()
            return
        layer = getattr(layer, "app", None)
        if layer is None:
            return


def test_catalog_status_and_missing_key_routes(monkeypatch):
    _reset_gateway_rate_limit()
    monkeypatch.setattr(routes, "get_fabric", lambda: OpenAIResponsesRuntime(None))
    assert client.get("/api/v1/model-fabric/status").json()["configured"] is False
    catalog = client.get("/api/v1/model-fabric/catalog").json()
    assert catalog["count"] == 3
    assert catalog["routing_policy"]["flagship"] == "jpai-6.2-ultra"
    response = client.post("/api/v1/model-fabric/infer", json={"prompt": "Explain JPAI"})
    assert response.status_code == 503
    assert response.json()["detail"] == "model_provider_not_configured"
    _reset_gateway_rate_limit()


def test_capabilities_endpoint_and_adaptive_routing(monkeypatch):
    _reset_gateway_rate_limit()
    monkeypatch.setattr(routes, "get_fabric", lambda: OpenAIResponsesRuntime(None))
    capabilities = client.get("/api/v1/model-fabric/capabilities").json()
    assert len(capabilities["models"]) == 3
    assert "shared-memory" in capabilities["shared_platform"]
    ultra = client.post("/api/v1/model-fabric/route", json={
        "task_type": "research", "complexity": "critical", "risk": "high",
    }).json()
    assert ultra["selected_model"] == "jpai-6.2-ultra"
    mantra = client.post("/api/v1/model-fabric/route", json={
        "task_type": "classification", "complexity": "low", "risk": "low",
    }).json()
    assert mantra["selected_model"] == "jpai-6-mantra"
    pro = client.post("/api/v1/model-fabric/route", json={
        "task_type": "implementation", "complexity": "medium", "risk": "normal",
    }).json()
    assert pro["selected_model"] == "jpai-6.2-pro"
    _reset_gateway_rate_limit()
