"""Evidence-gated continuous improvement and issue-resolution APIs."""
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jpai_api.quality.store import QualityStore

router = APIRouter(prefix="/quality", tags=["quality-and-continuous-improvement"])


@lru_cache(maxsize=1)
def get_store() -> QualityStore:
    return QualityStore()


class CycleCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    scope: str = Field(min_length=3, max_length=2000)
    baseline: str = Field(min_length=10, max_length=4000)


class CycleAdvance(BaseModel):
    stage: str = Field(pattern="^(reassess|improve|test|verify)$")
    evidence: str = Field(min_length=10, max_length=5000)


class IssueCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=10, max_length=4000)
    component: str = Field(min_length=2, max_length=100)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


class IssueAdvance(BaseModel):
    stage: str = Field(pattern="^(assessed|cause_identified|fix_implemented|tested|verified)$")
    evidence: str = Field(min_length=10, max_length=5000)


@router.get("/principles")
def quality_principles():
    return {
        "development_cycle": ["build", "reassess", "improve", "test", "verify"],
        "issue_resolution": [
            "reported", "assessed", "cause_identified", "fix_implemented", "tested", "verified"
        ],
        "governance": "sequential_evidence_required",
        "persistence": "local_sqlite",
    }


@router.post("/cycles")
def create_cycle(request: CycleCreate):
    return get_store().create_cycle(
        request.title.strip(), request.scope.strip(), request.baseline.strip()
    )


@router.get("/cycles")
def list_cycles(limit: int = 50):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit_must_be_between_1_and_100")
    items = get_store().list_cycles(limit)
    return {"count": len(items), "items": items}


@router.post("/cycles/{cycle_id}/advance")
def advance_cycle(cycle_id: int, request: CycleAdvance):
    item, error = get_store().advance_cycle(cycle_id, request.stage, request.evidence.strip())
    if error == "cycle_not_active":
        raise HTTPException(status_code=404, detail=error)
    if error:
        raise HTTPException(status_code=409, detail=error)
    return item


@router.post("/issues")
def create_issue(request: IssueCreate):
    return get_store().create_issue(
        request.title.strip(), request.description.strip(),
        request.component.strip(), request.severity,
    )


@router.get("/issues")
def list_issues(status: str | None = None, limit: int = 50):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit_must_be_between_1_and_100")
    if status and status not in {"reported", "assessed", "cause_identified", "fix_implemented", "tested", "verified"}:
        raise HTTPException(status_code=422, detail="invalid_issue_status")
    items = get_store().list_issues(status, limit)
    return {"count": len(items), "items": items}


@router.post("/issues/{issue_id}/advance")
def advance_issue(issue_id: int, request: IssueAdvance):
    item, error = get_store().advance_issue(issue_id, request.stage, request.evidence.strip())
    if error == "issue_not_active":
        raise HTTPException(status_code=404, detail=error)
    if error:
        raise HTTPException(status_code=409, detail=error)
    return item


@router.get("/events")
def quality_events(record_type: str | None = None, record_id: int | None = None, limit: int = 100):
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail="limit_must_be_between_1_and_200")
    if record_type and record_type not in {"cycle", "issue"}:
        raise HTTPException(status_code=422, detail="invalid_record_type")
    return {"items": get_store().events(record_type, record_id, limit)}
