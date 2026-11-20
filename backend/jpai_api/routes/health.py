"""Health and readiness endpoints."""
from fastapi import APIRouter
from jpai_api.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "mode": "local-first",
    }
