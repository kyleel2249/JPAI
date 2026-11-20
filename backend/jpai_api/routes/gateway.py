"""Governed API gateway ingress for automatic local inference."""
import secrets

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from jpai_api.config import get_settings
from jpai_api.intelligence.runtime import RuntimeUnavailable
from jpai_api.routes.intelligence import get_service

router = APIRouter(prefix="/gateway", tags=["api-gateway"])


class GatewayInferenceRequest(BaseModel):
    capability: str = Field(default="chat", min_length=1, max_length=40)
    prompt: str = Field(min_length=1, max_length=50_000)
    system: str | None = Field(default=None, max_length=10_000)
    temperature: float = Field(default=0.2, ge=0, le=2)
    preferred_provider: str | None = Field(default=None, max_length=80)
    minimum_context: int | None = Field(default=None, ge=1)
    max_latency_ms: float | None = Field(default=None, gt=0)
    minimum_reliability: float = Field(default=0.0, ge=0, le=1)


def _authorize(api_key: str | None) -> None:
    expected = get_settings().gateway_api_key
    if expected and (not api_key or not secrets.compare_digest(api_key, expected)):
        raise HTTPException(status_code=401, detail="gateway_authentication_required")


@router.get("/status")
def gateway_status():
    settings = get_settings()
    return {
        "status": "operational",
        "mode": "local-first",
        "rate_limit_per_minute": settings.gateway_requests_per_minute,
        "max_request_bytes": settings.gateway_max_request_bytes,
        "api_key_required": bool(settings.gateway_api_key),
        "authentication": "configured" if settings.gateway_api_key else "local-development",
        "inference_ingress": "/api/v1/gateway/infer",
    }


@router.post("/infer")
async def gateway_infer(
    request: GatewayInferenceRequest,
    x_jpai_api_key: str | None = Header(default=None),
):
    _authorize(x_jpai_api_key)
    # Only capabilities explicitly implemented by the current local runtime are allowed.
    if request.capability != "chat":
        raise HTTPException(status_code=403, detail="capability_not_enabled")
    service = get_service()
    try:
        await service.discover()
        ranked = await service.rank(
            request.capability,
            request.preferred_provider,
            request.minimum_context,
            request.max_latency_ms,
            request.minimum_reliability,
        )
        if not ranked:
            raise HTTPException(status_code=503, detail="no_eligible_local_model")
        selected = ranked[0]["model"]
        result = await service.infer(selected.id, request.prompt, request.system, request.temperature)
        return {
            **result,
            "gateway": {
                "selected_model": selected.id,
                "selection_score": ranked[0]["score"],
                "selection_reason": ranked[0]["reason"],
                "alternatives": [
                    {"model": item["model"].id, "score": item["score"]}
                    for item in ranked[1:4]
                ],
                "policy": "capability_allowlist_and_local_model_only",
            },
        }
    except RuntimeUnavailable as exc:
        raise HTTPException(status_code=503, detail="local_runtime_unavailable") from exc
