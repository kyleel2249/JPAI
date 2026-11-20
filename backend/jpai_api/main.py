"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from jpai_api.config import get_settings
from jpai_api.routes.health import router as health_router
from jpai_api.routes.intelligence import router as intelligence_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0", description="Local-first intelligence platform API")

# Local development only. Production origins must be explicitly configured before exposure.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(intelligence_router, prefix=settings.api_prefix)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "running", "docs": "/docs"}
