"""Local intelligence API routes."""
import asyncio
import statistics
from functools import lru_cache
from fastapi import APIRouter, HTTPException
from jpai_api.config import get_settings
from jpai_api.intelligence.runtime import LocalIntelligenceService, ModelNotFound, OllamaRuntime, RuntimeUnavailable
from jpai_api.intelligence.schemas import (AutoInferenceRequest, BenchmarkRequest, InferenceRequest,
    InferenceResponse, ModelComparisonRequest, ModelSelectionRequest)

router = APIRouter(prefix="/intelligence", tags=["local-intelligence"])


@lru_cache(maxsize=1)
def get_service() -> LocalIntelligenceService:
    """Return the process-wide service so the model catalogue and lock are shared across requests."""
    settings = get_settings()
    return LocalIntelligenceService(OllamaRuntime(settings.ollama_base_url, settings.model_timeout_seconds))


@router.get("/runtime")
async def runtime_health():
    return await get_service().runtime.health()


@router.post("/models/discover")
async def discover_models():
    try:
        models = await get_service().discover()
        return {"count": len(models), "models": [m.model_dump() for m in models]}
    except RuntimeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/models")
async def list_models():
    try:
        models = await get_service().discover()
        return {"count": len(models), "models": [m.model_dump() for m in models]}
    except RuntimeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/models/select")
async def select_model(request: ModelSelectionRequest):
    service = get_service()
    try:
        await service.discover()
        selected = await service.select(request.capability, request.preferred_provider, request.minimum_context)
        if selected is None:
            raise HTTPException(status_code=404, detail="No discovered local model satisfies the requested capability")
        return {"selected": selected.model_dump(), "selection_reason": "deterministic eligible capability match"}
    except RuntimeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/infer", response_model=InferenceResponse)
async def infer(request: InferenceRequest):
    service = get_service()
    try:
        await service.discover()
        return InferenceResponse(**await service.infer(request.model, request.prompt, request.system, request.temperature))
    except ModelNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/benchmark")
async def benchmark(request: BenchmarkRequest):
    service = get_service()
    try:
        await service.discover()
        runs = []
        for _ in range(request.iterations):
            result = await service.infer(request.model, request.prompt, None, 0)
            runs.append(result["duration_ms"])
        return {"model": request.model, "iterations": len(runs), "latency_ms": {
            "min": min(runs), "median": statistics.median(runs), "max": max(runs),
            "mean": round(statistics.mean(runs), 2)}}
    except ModelNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/infer/auto", response_model=InferenceResponse)
async def infer_auto(request: AutoInferenceRequest):
    service = get_service()
    try:
        await service.discover()
        selected = await service.select(request.capability, request.preferred_provider, request.minimum_context)
        if selected is None:
            raise HTTPException(status_code=404, detail="No local model satisfies the requested capability")
        return InferenceResponse(**await service.infer(selected.id, request.prompt, request.system, request.temperature))
    except ModelNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/models/compare")
async def compare_models(request: ModelComparisonRequest):
    if len(set(request.models)) != len(request.models):
        raise HTTPException(status_code=422, detail="Model list must not contain duplicates")
    service = get_service()
    try:
        await service.discover()
        semaphore = asyncio.Semaphore(2)

        async def bounded_inference(model: str):
            async with semaphore:
                return await service.infer(model, request.prompt, request.system, request.temperature)

        tasks = [bounded_inference(model) for model in request.models]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        results = []
        for model, outcome in zip(request.models, outcomes):
            if isinstance(outcome, ModelNotFound):
                results.append({"model": model, "status": "unavailable", "error": "model_not_discovered"})
            elif isinstance(outcome, RuntimeUnavailable):
                results.append({"model": model, "status": "failed", "error": "runtime_unavailable"})
            elif isinstance(outcome, Exception):
                results.append({"model": model, "status": "failed", "error": "inference_failed"})
            else:
                results.append({"model": model, "status": "completed", **outcome})
        return {"comparison_count": len(results), "results": results}
    except RuntimeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
