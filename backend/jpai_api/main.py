"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jpai_api.config import get_settings
from jpai_api.routes.agents import router as agents_router
from jpai_api.middleware.gateway import GatewayMiddleware
from jpai_api.routes.gateway import router as gateway_router
from jpai_api.routes.health import router as health_router
from jpai_api.routes.intelligence import router as intelligence_router
from jpai_api.routes.memory import router as memory_router
from jpai_api.routes.routing import router as routing_router

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    description="Local-first personal, professional and enterprise intelligence platform",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-JPAI-API-Key", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)
app.add_middleware(
    GatewayMiddleware,
    requests_per_minute=settings.gateway_requests_per_minute,
    max_request_bytes=settings.gateway_max_request_bytes,
    api_key=settings.gateway_api_key,
)
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(intelligence_router, prefix=settings.api_prefix)
app.include_router(memory_router, prefix=settings.api_prefix)
app.include_router(routing_router, prefix=settings.api_prefix)
app.include_router(gateway_router, prefix=settings.api_prefix)
app.include_router(agents_router, prefix=settings.api_prefix)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "running", "docs": "/docs"}
