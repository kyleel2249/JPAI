"""FastAPI application entry point."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jpai_api.config import get_settings
from jpai_api.routes.agents import router as agents_router
from jpai_api.routes.directorates import router as directorates_router
from jpai_api.middleware.gateway import GatewayMiddleware
from jpai_api.routes.gateway import router as gateway_router
from jpai_api.routes.health import router as health_router
from jpai_api.routes.intelligence import router as intelligence_router
from jpai_api.routes.memory import router as memory_router
from jpai_api.routes.quality import router as quality_router
from jpai_api.routes.routing import router as routing_router
from jpai_api.routes.web_intelligence import get_crawler, router as web_intelligence_router
from jpai_api.routes.workbenches import router as workbenches_router

logger = logging.getLogger(__name__)


async def _web_intelligence_scheduler():
    while True:
        try:
            await asyncio.to_thread(get_crawler().run_due_schedules, 3)
        except Exception:
            logger.exception("JPAI web-intelligence scheduler iteration failed")
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(_app):
    enabled = os.getenv("JPAI_WEB_INTELLIGENCE_SCHEDULER_ENABLED", "true").lower() not in {"0", "false", "no"}
    task = asyncio.create_task(_web_intelligence_scheduler()) if enabled else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

settings = get_settings()
app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version="0.6.0",
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
app.include_router(quality_router, prefix=settings.api_prefix)
app.include_router(routing_router, prefix=settings.api_prefix)
app.include_router(gateway_router, prefix=settings.api_prefix)
app.include_router(agents_router, prefix=settings.api_prefix)
app.include_router(web_intelligence_router, prefix=settings.api_prefix)
app.include_router(workbenches_router, prefix=settings.api_prefix)
app.include_router(directorates_router, prefix=settings.api_prefix)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "running", "docs": "/docs"}
