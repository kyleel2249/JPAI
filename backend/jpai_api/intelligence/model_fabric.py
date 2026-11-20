"""JPAI-native model identities over governed provider inference adapters."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

MODEL_SPECS: dict[str, dict[str, Any]] = {
    "jpai-6.2-ultra": {
        "name": "JPAI-6.2 Ultra", "tier": "flagship", "provider_model": "gpt-6.2-astra",
        "reference_model": "GPT-6.2 Astra", "purpose": "frontier reasoning, complex engineering, architecture, research and synthesis",
        "context_window": 1_050_000, "max_input_tokens": 922_000, "max_output_tokens": 128_000,
        "reasoning_efforts": ["low", "medium", "high", "xhigh", "max"],
        "modalities": ["text_input", "image_input", "text_output"],
        "capabilities": ["deep_reasoning", "advanced_coding", "architecture", "research", "mathematics",
                         "image_understanding", "computer_use_target", "tool_use", "structured_output",
                         "multi_step_execution", "strategic_analysis", "peer_review"],
        "documented_tools": ["function_calling", "web_search", "file_search", "image_generation",
                             "code_interpreter", "hosted_shell", "apply_patch", "skills",
                             "computer_use", "mcp", "tool_search"],
        "enabled_hosted_tools": ["web_search_preview", "code_interpreter", "image_generation"],
        "input_usd_per_million": 8.0, "cached_input_usd_per_million": 0.4, "output_usd_per_million": 40.0,
    },
    "jpai-6.2-pro": {
        "name": "JPAI-6.2 Pro", "tier": "professional", "provider_model": "gpt-6.2-sol",
        "reference_model": "GPT-6.2 Sol", "purpose": "professional reasoning, coding, multi-step workflows and agent execution",
        "context_window": 1_050_000, "max_input_tokens": 922_000, "max_output_tokens": 128_000,
        "reasoning_efforts": ["low", "medium", "high", "xhigh", "max"],
        "modalities": ["text_input", "image_input", "text_output"],
        "capabilities": ["reasoning", "coding", "software_implementation", "research", "workflow_execution",
                         "tool_use", "image_understanding", "structured_output", "multi_step_execution",
                         "automation", "peer_review"],
        "documented_tools": ["function_calling", "web_search", "file_search", "computer_use"],
        "enabled_hosted_tools": ["web_search_preview"],
        "input_usd_per_million": 2.0, "cached_input_usd_per_million": 0.1, "output_usd_per_million": 10.0,
    },
    "jpai-6-mantra": {
        "name": "JPAI-6 Mantra", "tier": "efficient", "provider_model": "gpt-6-luna",
        "reference_model": "GPT-6 Luna", "purpose": "focused reasoning, high-volume processing, extraction and automation",
        "context_window": 1_050_000, "max_input_tokens": 922_000, "max_output_tokens": 128_000,
        "reasoning_efforts": ["none", "low", "medium", "high", "xhigh"],
        "modalities": ["text_input", "image_input", "text_output"],
        "capabilities": ["reasoning", "classification", "extraction", "summarization", "data_transformation",
                         "coding", "automation", "monitoring", "image_understanding", "tool_use",
                         "structured_output", "multi_step_execution"],
        "documented_tools": ["function_calling", "web_search", "file_search", "image_generation",
                             "code_interpreter", "hosted_shell", "apply_patch", "skills",
                             "computer_use", "mcp", "tool_search"],
        "enabled_hosted_tools": ["web_search_preview", "code_interpreter", "image_generation"],
        "input_usd_per_million": 0.1, "cached_input_usd_per_million": 0.01, "output_usd_per_million": 0.5,
    },
}

# Accept old internal identifiers during migration, but never expose them as JPAI product names.
MODEL_ALIASES = {
    "gpt-6.2-astra": "jpai-6.2-ultra",
    "gpt-6.2-sol": "jpai-6.2-pro",
    "gpt-6-luna": "jpai-6-mantra",
}
SAFE_TOOLS = {"web_search_preview", "code_interpreter", "image_generation"}


def canonical_model_id(model: str) -> str:
    return MODEL_ALIASES.get(model, model)


class ModelFabricError(RuntimeError):
    """A governed model-fabric request failed validation or provider execution."""


class ProviderNotConfigured(ModelFabricError):
    """The optional remote inference provider has no backend credential."""


class OpenAIResponsesRuntime:
    """Provider adapter; JPAI model names remain stable even if provider IDs change."""

    def __init__(self, api_key: str | None, base_url: str = "https://api.openai.com/v1",
                 timeout_seconds: float = 180, max_concurrency: int = 8):
        self.api_key = api_key.strip() if api_key else ""
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.semaphore = asyncio.Semaphore(max(1, min(max_concurrency, 32)))

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def catalog(self) -> list[dict[str, Any]]:
        return [{
            "id": model_id, **spec, "provider": "openai",
            "configured": self.configured,
            "availability": "credentials_configured" if self.configured else "awaiting_api_key",
            "provider_model_id": spec["provider_model"],
            "provider_limits_apply": True,
        } for model_id, spec in MODEL_SPECS.items()]

    @staticmethod
    def cost(model: str, usage: dict[str, Any]) -> float:
        model_id = canonical_model_id(model)
        if model_id not in MODEL_SPECS:
            raise ModelFabricError("Unknown JPAI model.")
        spec = MODEL_SPECS[model_id]
        total = int(usage.get("input_tokens") or 0)
        output = int(usage.get("output_tokens") or 0)
        cached = min(total, int((usage.get("input_tokens_details") or {}).get("cached_tokens") or 0))
        return round(((total - cached) * spec["input_usd_per_million"]
                      + cached * spec["cached_input_usd_per_million"]
                      + output * spec["output_usd_per_million"]) / 1_000_000, 8)

    @staticmethod
    def output_text(data: dict[str, Any]) -> str:
        if isinstance(data.get("output_text"), str):
            return data["output_text"]
        return "\n".join(
            chunk["text"] for item in data.get("output", []) if isinstance(item, dict)
            for chunk in item.get("content", [])
            if isinstance(chunk, dict) and chunk.get("type") in {"output_text", "text"}
            and isinstance(chunk.get("text"), str)
        )

    async def infer(self, model: str, prompt: str, system: str | None = None,
                    reasoning_effort: str = "medium", max_output_tokens: int = 4096,
                    image_urls: list[str] | None = None, json_schema: dict[str, Any] | None = None,
                    tools: list[str] | None = None,
                    function_tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if not self.configured:
            raise ProviderNotConfigured("Set JPAI_OPENAI_API_KEY in the backend environment.")
        model_id = canonical_model_id(model)
        if model_id not in MODEL_SPECS:
            raise ModelFabricError("Model is not in the approved JPAI model catalogue.")
        spec = MODEL_SPECS[model_id]
        if reasoning_effort not in spec["reasoning_efforts"]:
            raise ModelFabricError("Unsupported reasoning effort for this JPAI model.")
        if not 1 <= max_output_tokens <= spec["max_output_tokens"]:
            raise ModelFabricError("Output request exceeds the selected provider model's supported bounds.")

        content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
        for url in image_urls or []:
            if not url.startswith("https://"):
                raise ModelFabricError("Image inputs must be HTTPS URLs.")
            content.append({"type": "input_image", "image_url": url})
        items = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": content}
        ]
        payload: dict[str, Any] = {
            "model": spec["provider_model"], "input": items,
            "max_output_tokens": max_output_tokens,
            "reasoning": {"effort": reasoning_effort},
        }
        selected_tools = tools or []
        if set(selected_tools) - SAFE_TOOLS:
            raise ModelFabricError("Tool is not enabled by JPAI's safe hosted-tool policy.")
        if set(selected_tools) - set(spec["enabled_hosted_tools"]):
            raise ModelFabricError("Requested hosted tool is not enabled for this JPAI model.")
        if selected_tools:
            payload["tools"] = [{"type": item} for item in selected_tools]
        if function_tools:
            if len(function_tools) > 12:
                raise ModelFabricError("At most 12 function declarations are allowed.")
            for item in function_tools:
                if not isinstance(item, dict) or not item.get("name") or not isinstance(item.get("parameters"), dict):
                    raise ModelFabricError("Function tools require name and JSON-schema parameters.")
            payload.setdefault("tools", []).extend({
                "type": "function", "name": item["name"],
                "description": item.get("description", ""), "parameters": item["parameters"],
                "strict": bool(item.get("strict", True)),
            } for item in function_tools)
        if json_schema:
            payload["text"] = {"format": {
                "type": "json_schema", "name": "jpai_structured_output",
                "schema": json_schema, "strict": True,
            }}

        started = time.perf_counter()
        async with self.semaphore:
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        self.base_url + "/responses", json=payload,
                        headers={"Authorization": "Bearer " + self.api_key,
                                 "Content-Type": "application/json"},
                    )
                    response.raise_for_status()
                    data = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise ModelFabricError("Provider inference failed; inspect provider status and telemetry.") from exc

        usage = data.get("usage") or {}
        output = data.get("output") or []
        calls = [{
            "name": item.get("name"), "call_id": item.get("call_id"),
            "arguments": item.get("arguments"),
        } for item in output if isinstance(item, dict) and item.get("type") == "function_call"]
        return {
            "model": model_id, "name": spec["name"], "provider": "openai",
            "provider_model_id": spec["provider_model"],
            "response": self.output_text(data),
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "usage": usage, "estimated_cost_usd": self.cost(model_id, usage),
            "tool_calls_pending_governance": calls, "response_id": data.get("id"),
            "status": data.get("status", "completed"),
        }
