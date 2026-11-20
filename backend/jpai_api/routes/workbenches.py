"""Governed technology/engineering and editorial workbench APIs."""
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from jpai_api.workbenches import WorkbenchError, WorkbenchStore

router = APIRouter(prefix="/workbenches", tags=["workbenches"])


@lru_cache(maxsize=1)
def get_store():
    return WorkbenchStore()


class ProjectCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    brief: str = Field(min_length=10, max_length=8000)


class ProjectUpdate(BaseModel):
    fields: dict = Field(min_length=1)


class StageTransition(BaseModel):
    target: str = Field(min_length=2, max_length=40)


def _call(operation, *args):
    try:
        return operation(*args)
    except WorkbenchError as exc:
        message = str(exc)
        code = 404 if "not found" in message else 409
        raise HTTPException(status_code=code, detail=message) from exc


@router.post("/engineering", status_code=201)
def create_engineering_project(request: ProjectCreate):
    return get_store().create("engineering", request.title, request.brief)


@router.get("")
def list_projects(kind: str | None = Query(default=None, pattern="^(engineering|editorial)$"),
                  limit: int = Query(default=50, ge=1, le=100)):
    items = get_store().list(kind, limit)
    return {"count": len(items), "items": items}


@router.get("/{project_id}")
def get_project(project_id: int):
    item = get_store().get(project_id)
    if not item:
        raise HTTPException(status_code=404, detail="workbench_project_not_found")
    return item


@router.patch("/{project_id}")
def update_project(project_id: int, request: ProjectUpdate):
    return _call(get_store().update, project_id, request.fields)


@router.post("/{project_id}/transition")
def transition_project(project_id: int, request: StageTransition):
    return _call(get_store().transition, project_id, request.target)


@router.get("/{project_id}/events")
def project_events(project_id: int):
    items = get_store().events(project_id)
    if items is None:
        raise HTTPException(status_code=404, detail="workbench_project_not_found")
    return {"count": len(items), "items": items}
