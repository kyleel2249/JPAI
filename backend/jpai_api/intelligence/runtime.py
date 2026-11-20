"""Provider-neutral local inference runtime and Ollama adapter."""
from __future__ import annotations
import asyncio
import ipaddress
import time
from urllib.parse import urlparse
import httpx
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
            if not name:
                continue
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
        data = await self._request("POST", "/api/generate", json=payload)
        return data


class LocalIntelligenceService:
    def __init__(self, runtime: OllamaRuntime):
        self.runtime = runtime
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

    async def select(self, capability: str, preferred_provider: str | None = None,
                     minimum_context: int | None = None) -> ModelProfile | None:
        candidates = await self.models()
        candidates = [p for p in candidates if p.available and capability in p.capabilities]
        if minimum_context is not None:
            candidates = [p for p in candidates if p.context_length is not None and p.context_length >= minimum_context]
        if preferred_provider:
            preferred = [p for p in candidates if p.provider == preferred_provider]
            if preferred:
                candidates = preferred
        return sorted(candidates, key=lambda p: (p.provider, p.id))[0] if candidates else None

    async def infer(self, model: str, prompt: str, system: str | None, temperature: float) -> dict:
        known = {p.id for p in await self.models()}
        if model not in known:
            raise ModelNotFound("Model is not in the discovered local catalogue; discover models first")
        started = time.perf_counter()
        result = await self.runtime.generate(model, prompt, system, temperature)
        return {"model": model, "provider": "ollama", "response": result.get("response", ""),
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "prompt_tokens": result.get("prompt_eval_count"),
                "completion_tokens": result.get("eval_count")}
