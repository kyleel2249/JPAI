"""Provider-neutral local inference runtime and explainable model routing."""
from __future__ import annotations
import asyncio
import ipaddress
import time
from urllib.parse import urlparse

import httpx

from jpai_api.intelligence.persistence import IntelligenceStore
from jpai_api.intelligence.schemas import ModelProfile


class RuntimeUnavailable(RuntimeError):
    pass


class ModelNotFound(RuntimeError):
    pass


class OllamaRuntime:
    """Local-only Ollama adapter. Remote hosts are rejected to avoid SSRF exposure."""

    def __init__(self, base_url: str, timeout_seconds: float = 90.0) -> None:
        parsed = urlparse(base_url)
        host = parsed.hostname or ""
        try:
            is_loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_loopback = host.lower() == "localhost"
        if parsed.scheme not in {"http", "https"} or not is_loopback:
            raise ValueError("Local model runtime must use a loopback address")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def _request(self, method: str, path: str, **kwargs):
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.request(method, f"{self.base_url}{path}", **kwargs)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeUnavailable("Local model runtime is unavailable or returned an invalid response") from exc

    async def health(self) -> dict:
        try:
            data = await self._request("GET", "/api/version")
            return {"available": True, "runtime": "ollama", "version": data.get("version")}
        except RuntimeUnavailable:
            return {"available": False, "runtime": "ollama", "version": None}

    async def discover(self) -> list[ModelProfile]:
        data = await self._request("GET", "/api/tags")
        profiles = []
        for item in data.get("models", []):
            details = item.get("details") or {}
            name = item.get("name") or item.get("model")
            if name:
                profiles.append(ModelProfile(
                    id=name, provider="ollama", display_name=name,
                    family=details.get("family"), parameter_size=details.get("parameter_size"),
                    quantization=details.get("quantization_level"), capabilities=["chat"], available=True,
                ))
        return profiles

    async def generate(self, model: str, prompt: str, system: str | None, temperature: float) -> dict:
        payload = {"model": model, "prompt": prompt, "stream": False,
                   "options": {"temperature": temperature}}
        if system:
            payload["system"] = system
        return await self._request("POST", "/api/generate", json=payload)


class LocalIntelligenceService:
    def __init__(self, runtime: OllamaRuntime, store: IntelligenceStore | None = None):
        self.runtime = runtime
        self.store = store or IntelligenceStore()
        self._catalog: dict[str, ModelProfile] = {}
        self._lock = asyncio.Lock()

    async def discover(self) -> list[ModelProfile]:
        profiles = await self.runtime.discover()
        async with self._lock:
            self._catalog = {profile.id: profile for profile in profiles}
        return profiles

    async def models(self) -> list[ModelProfile]:
        async with self._lock:
            return list(self._catalog.values())

    async def rank(self, capability: str, preferred_provider: str | None = None,
                   minimum_context: int | None = None, max_latency_ms: float | None = None,
                   minimum_reliability: float = 0.0) -> list[dict]:
        candidates = [p for p in await self.models() if p.available and capability in p.capabilities]
        metrics = self.store.get_model_metrics()
        ranked = []
        for model in candidates:
            metric = metrics.get(model.id, {})
            latency = metric.get("avg_latency_ms")
            samples = metric.get("samples", 0)
            reliability = metric.get("successes", 0) / samples if samples else 1.0
            if minimum_context is not None and (model.context_length is None or model.context_length < minimum_context):
                continue
            if max_latency_ms is not None and latency is not None and latency > max_latency_ms:
                continue
            if reliability < minimum_reliability:
                continue
            latency_score = 1.0 / (1.0 + (latency or 1000.0) / 1000.0)
            provider_score = float(bool(preferred_provider and model.provider == preferred_provider))
            context_score = min((model.context_length or 0) / 128000, 1.0)
            score = 0.40 + 0.25 * reliability + 0.20 * latency_score + 0.10 * provider_score + 0.05 * context_score
            ranked.append({"model": model, "score": round(score, 4), "reliability": round(reliability, 4),
                           "avg_latency_ms": latency,
                           "reason": "capability match; weighted reliability, latency, provider preference and context"})
        return sorted(ranked, key=lambda item: (-item["score"], item["model"].provider, item["model"].id))

    async def select(self, capability: str, preferred_provider: str | None = None,
                     minimum_context: int | None = None, max_latency_ms: float | None = None,
                     minimum_reliability: float = 0.0) -> ModelProfile | None:
        ranked = await self.rank(capability, preferred_provider, minimum_context,
                                 max_latency_ms, minimum_reliability)
        return ranked[0]["model"] if ranked else None

    async def infer(self, model: str, prompt: str, system: str | None, temperature: float) -> dict:
        known = {p.id: p for p in await self.models()}
        if model not in known:
            raise ModelNotFound("Model is not in the discovered local catalogue; discover models first")
        started = time.perf_counter()
        try:
            result = await self.runtime.generate(model, prompt, system, temperature)
            duration = round((time.perf_counter() - started) * 1000, 2)
            self.store.record_model_result(model, known[model].provider, duration, True)
            return {"model": model, "provider": known[model].provider, "response": result.get("response", ""),
                    "duration_ms": duration, "prompt_tokens": result.get("prompt_eval_count"),
                    "completion_tokens": result.get("eval_count")}
        except RuntimeUnavailable:
            self.store.record_model_result(model, known[model].provider,
                                           round((time.perf_counter() - started) * 1000, 2), False)
            raise
