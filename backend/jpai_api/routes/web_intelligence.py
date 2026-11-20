"""Governed web discovery, scheduled monitoring, extraction and local search API."""
from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from jpai_api.intelligence.persistence import IntelligenceStore
from jpai_api.research.crawler import (
    CrawlPolicyError,
    CrawlerStore,
    WebCrawler,
    validate_public_url,
)

router = APIRouter(prefix="/web-intelligence", tags=["web-intelligence"])


@lru_cache(maxsize=1)
def get_store():
    return CrawlerStore()


@lru_cache(maxsize=1)
def get_crawler():
    return WebCrawler(get_store())


class CrawlRequest(BaseModel):
    seed_url: str = Field(min_length=8, max_length=2048)
    max_pages: int = Field(default=10, ge=1, le=50)


class ScheduleRequest(BaseModel):
    seed_url: str = Field(min_length=8, max_length=2048)
    interval_minutes: int = Field(default=60, ge=15, le=43200)
    max_pages: int = Field(default=10, ge=1, le=50)


class ScheduleUpdate(BaseModel):
    enabled: bool


@router.get("/status")
def status():
    return {
        "status": "available",
        "mode": "same-origin, robots-aware, DNS-pinned, bounded crawl",
        "scheduler": "persistent local scheduler; runs while the JPAI API process is active",
        "policy": {
            "max_pages_per_job": 50,
            "max_response_bytes": 1500000,
            "max_depth": 2,
            "minimum_delay_seconds": 1,
            "minimum_schedule_interval_minutes": 15,
            "max_jsonld_blocks_per_page": 25,
            "max_jsonld_block_bytes": 50000,
        },
        **get_store().stats(),
    }


@router.post("/jobs", status_code=202)
def create_job(request: CrawlRequest, background_tasks: BackgroundTasks):
    try:
        seed = validate_public_url(request.seed_url)
    except CrawlPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job = get_store().create_job(seed, request.max_pages)
    background_tasks.add_task(get_crawler().run, job["id"])
    return {
        "job": job,
        "message": "Queued. Same-origin links only; robots.txt rules are respected.",
    }


@router.get("/jobs")
def list_jobs(limit: int = Query(default=30, ge=1, le=100)):
    items = get_store().list_jobs(limit)
    return {"count": len(items), "items": items}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = get_store().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="crawl_job_not_found")
    return job


@router.post("/schedules", status_code=201)
def create_schedule(request: ScheduleRequest):
    try:
        seed = validate_public_url(request.seed_url)
    except CrawlPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    item = get_store().create_schedule(seed, request.interval_minutes, request.max_pages)
    return {
        "schedule": item,
        "message": "Monitoring schedule saved. The first crawl is due immediately.",
    }


@router.get("/schedules")
def list_schedules(limit: int = Query(default=100, ge=1, le=200)):
    items = get_store().list_schedules(limit)
    return {"count": len(items), "items": items}


@router.patch("/schedules/{schedule_id}")
def update_schedule(schedule_id: int, request: ScheduleUpdate):
    item = get_store().set_schedule_enabled(schedule_id, request.enabled)
    if not item:
        raise HTTPException(status_code=404, detail="crawl_schedule_not_found")
    return item


@router.get("/changes")
def list_changes(limit: int = Query(default=100, ge=1, le=500)):
    items = get_store().list_changes(limit)
    return {"count": len(items), "items": items}


@router.get("/pages/{page_id}/structured-data")
def get_page_structured_data(page_id: int):
    page = get_store().get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="crawled_page_not_found")
    records = page.get("structured_data", [])
    return {
        "page_id": page_id,
        "url": page["url"],
        "count": len(records),
        "items": records,
        "format": "schema.org JSON-LD",
        "trust": "unverified_external_metadata",
    }


@router.get("/pages/{page_id}/versions")
def list_page_versions(page_id: int, limit: int = Query(default=50, ge=1, le=200)):
    page = get_store().get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="crawled_page_not_found")
    items = get_store().list_versions(page_id, limit)
    return {"page_id": page_id, "count": len(items), "items": items}


@router.get("/pages")
def list_pages(job_id: str | None = None, limit: int = Query(default=50, ge=1, le=100)):
    items = get_store().list_pages(job_id, limit)
    return {"count": len(items), "items": items}


@router.get("/search")
def search_pages(
    q: str = Query(min_length=2, max_length=300),
    limit: int = Query(default=20, ge=1, le=50),
):
    items = get_store().search_pages(q, limit)
    return {"count": len(items), "items": items, "method": "local_weighted_keyword_search"}


@router.post("/pages/{page_id}/remember")
def remember_page(page_id: int):
    page = get_store().get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="crawled_page_not_found")
    if page.get("memory_id"):
        return {
            "page_id": page_id,
            "memory_id": page["memory_id"],
            "status": "already_in_memory",
        }
    content = (
        "Source URL: " + page["url"]
        + "\nFetched at: " + page["fetched_at"]
        + "\nContent SHA-256: " + page["content_hash"]
        + "\n\\n" + page["description"]
        + "\n\\n" + page["content"]
    )[:30000]
    memory = IntelligenceStore().create_memory(
        namespace="web-research",
        title=(page["title"] or page["url"])[:240],
        content=content,
        tags=["web-intelligence", page["domain"][:48]],
        source="web_crawler",
        memory_type="semantic",
        importance=0.7,
        metadata={
            "url": page["url"],
            "domain": page["domain"],
            "fetched_at": page["fetched_at"],
            "content_hash": page["content_hash"],
            "trust": "unverified_external_source",
        },
    )
    get_store().mark_page_memory(page_id, memory["id"])
    return {
        "page_id": page_id,
        "memory_id": memory["id"],
        "status": "added_to_jpai_memory",
        "warning": "External source content is unverified and must be corroborated.",
    }
