import pytest
from fastapi.testclient import TestClient
from jpai_api.intelligence.model_fabric import MODEL_SPECS,ModelFabricError,OpenAIResponsesRuntime,ProviderNotConfigured
from jpai_api.main import app
from jpai_api.routes import model_fabric as routes
client=TestClient(app)
def test_catalog_models_and_limits():
 items=OpenAIResponsesRuntime(None).catalog()
 assert {x["id"] for x in items}==set(MODEL_SPECS)
 assert all(x["context_window"]==1050000 and x["max_output_tokens"]==128000 for x in items)
 assert "computer_use" in next(x for x in items if x["id"]=="gpt-6.2-astra")["tools"]
def test_status_does_not_leak_api_key():
 r=OpenAIResponsesRuntime("secret-value")
 assert r.configured and "secret-value" not in str(r.catalog())
@pytest.mark.asyncio
async def test_missing_key_fails_closed():
 with pytest.raises(ProviderNotConfigured):await OpenAIResponsesRuntime(None).infer("gpt-6.2-sol","hello")
@pytest.mark.asyncio
async def test_policy_rejects_invalid_model_effort_and_tool():
 r=OpenAIResponsesRuntime("key")
 with pytest.raises(ModelFabricError):await r.infer("invalid","hello")
 with pytest.raises(ModelFabricError):await r.infer("gpt-6.2-astra","hello",reasoning_effort="none")
 with pytest.raises(ModelFabricError):await r.infer("gpt-6.2-sol","hello",tools=["computer"])
def test_cached_token_cost_estimate():
 usage={"input_tokens":1000,"output_tokens":500,"input_tokens_details":{"cached_tokens":400}}
 assert OpenAIResponsesRuntime.cost("gpt-6.2-sol",usage)==pytest.approx((600*2+400*.1+500*10)/1000000)
def test_catalog_status_and_missing_key_routes(monkeypatch):
 monkeypatch.setattr(routes,"get_fabric",lambda:OpenAIResponsesRuntime(None))
 assert client.get("/api/v1/model-fabric/status").json()["configured"] is False
 assert client.get("/api/v1/model-fabric/catalog").json()["count"]==3
 r=client.post("/api/v1/model-fabric/infer",json={"prompt":"Explain JPAI"})
 assert r.status_code==503 and r.json()["detail"]=="openai_provider_not_configured"
