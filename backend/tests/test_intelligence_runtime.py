import pytest
from jpai_api.intelligence.runtime import LocalIntelligenceService, ModelNotFound, OllamaRuntime
from jpai_api.intelligence.schemas import ModelProfile


def test_runtime_rejects_non_loopback_host():
    with pytest.raises(ValueError):
        OllamaRuntime("https://example.com")


def test_runtime_accepts_loopback_hosts():
    assert OllamaRuntime("http://127.0.0.1:11434").base_url == "http://127.0.0.1:11434"
    assert OllamaRuntime("http://localhost:11434").base_url == "http://localhost:11434"


@pytest.mark.asyncio
async def test_model_selection_uses_capability_and_provider():
    service = LocalIntelligenceService(OllamaRuntime("http://127.0.0.1:11434"))
    service._catalog = {
        "alpha": ModelProfile(id="alpha", provider="ollama", display_name="Alpha", capabilities=["chat"]),
        "beta": ModelProfile(id="beta", provider="other", display_name="Beta", capabilities=["embedding"]),
    }
    selected = await service.select("chat")
    assert selected is not None and selected.id == "alpha"
    assert await service.select("vision") is None


@pytest.mark.asyncio
async def test_inference_requires_discovered_model():
    service = LocalIntelligenceService(OllamaRuntime("http://127.0.0.1:11434"))
    with pytest.raises(ModelNotFound):
        await service.infer("unknown", "hello", None, 0)
