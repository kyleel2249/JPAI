"""Explainable model-routing diagnostics."""
from fastapi import APIRouter
from jpai_api.intelligence.persistence import IntelligenceStore
from jpai_api.routes.intelligence import get_service

router=APIRouter(prefix="/routing",tags=["model-routing"])
store=IntelligenceStore()

@router.get("/profiles")
async def routing_profiles():
    models=await get_service().discover()
    metrics=store.get_model_metrics()
    return {"strategy":"weighted_capability_latency_reliability",
            "weights":{"capability":0.40,"reliability":0.25,"latency":0.20,
                       "provider_preference":0.10,"context":0.05},
            "models":[{**m.model_dump(),"metrics":metrics.get(m.id,{})} for m in models]}

@router.get("/metrics")
def routing_metrics():
    return {"models":store.get_model_metrics()}
