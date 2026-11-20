"""Reality Studio media intake and production planning API."""
from functools import lru_cache

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from jpai_api.intelligence.media_studio import MediaStudioError, MediaStudioStore, engine_status

router = APIRouter(prefix="/media-studio", tags=["media-studio"])


@lru_cache(maxsize=1)
def get_store():
    return MediaStudioStore()


class JobCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    mode: str = Field(pattern="^(extract|reconstruct|enhance|transcode|audio_restore|image_rebuild)$")
    source_asset_id: str = Field(min_length=16, max_length=64)
    request: dict = Field(default_factory=dict)


def _call(operation, *args):
    try:
        return operation(*args)
    except MediaStudioError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/capabilities")
def capabilities():
    return {"studio": "JPAI Reality Studio", "output_profiles": {
        "video": {"width": 3840, "height": 2160, "label": "4K UHD", "fps": [24, 25, 30, 50, 60]},
        "image": {"width": 3840, "height": 2160, "label": "4K UHD", "format": "PNG"},
        "audio": {"sample_rates_hz": [48000, 96000], "format": "WAV", "bit_depth": 24},
    }, "engines": engine_status()} 


@router.post("/assets", status_code=201)
async def upload_asset(file: UploadFile = File(...), media_type: str = Query(..., pattern="^(video|audio|image)$")):
    content = await file.read()
    if len(content) > 500 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Media upload exceeds 500 MB.")
    return _call(get_store().add_asset, file.filename or "", content, media_type)


@router.get("/assets")
def list_assets(limit: int = Query(default=50, ge=1, le=100)):
    items = get_store().list_assets(limit)
    return {"count": len(items), "items": items}


@router.post("/jobs", status_code=201)
def create_job(request: JobCreate):
    return _call(get_store().create_job, request.title, request.mode, request.source_asset_id, request.request)


@router.get("/jobs")
def list_jobs(limit: int = Query(default=50, ge=1, le=100)):
    items = get_store().list_jobs(limit)
    return {"count": len(items), "items": items}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    item = get_store().get_job(job_id)
    if not item:
        raise HTTPException(status_code=404, detail="media_job_not_found")
    return item
