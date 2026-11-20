"""API routes for eight governed JPAI directorates."""
from functools import lru_cache
from fastapi import APIRouter,HTTPException,Query
from pydantic import BaseModel,Field
from jpai_api.directorates import CONFIG,DirectorateError,DirectorateStore
router=APIRouter(prefix="/directorates",tags=["directorates"])
@lru_cache(maxsize=1)
def get_store():return DirectorateStore()
class Create(BaseModel):
 kind:str=Field(min_length=3,max_length=40);title:str=Field(min_length=3,max_length=200);brief:str=Field(min_length=10,max_length=8000)
class Update(BaseModel):fields:dict=Field(min_length=1)
class Transition(BaseModel):target:str=Field(min_length=2,max_length=40)
def call(fn,*args):
 try:return fn(*args)
 except DirectorateError as e:
  m=str(e);raise HTTPException(status_code=404 if "not found" in m else 409,detail=m) from e
@router.get("/catalog")
def catalog():return {"count":len(CONFIG),"items":[{"kind":k,"phase":v[0],"name":v[1],"stages":v[2],"fields":sorted(v[3].split())} for k,v in CONFIG.items()]}
@router.post("/projects",status_code=201)
def create(req:Create):return call(get_store().create,req.kind,req.title,req.brief)
@router.get("/projects")
def listing(kind:str|None=Query(default=None),limit:int=Query(default=100,ge=1,le=200)):
 if kind is not None and kind not in CONFIG:raise HTTPException(status_code=422,detail="Unsupported directorate kind.")
 items=get_store().list(kind,limit);return {"count":len(items),"items":items}
@router.get("/projects/{pid}")
def get(pid:int):
 p=get_store().get(pid)
 if not p:raise HTTPException(status_code=404,detail="directorate_project_not_found")
 return p
@router.patch("/projects/{pid}")
def update(pid:int,req:Update):return call(get_store().update,pid,req.fields)
@router.post("/projects/{pid}/transition")
def transition(pid:int,req:Transition):return call(get_store().transition,pid,req.target)
@router.get("/projects/{pid}/events")
def events(pid:int):
 e=get_store().events(pid)
 if e is None:raise HTTPException(status_code=404,detail="directorate_project_not_found")
 return {"count":len(e),"items":e}
