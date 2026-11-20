"""Governed APIs for JPAI phases 21–30."""
from functools import lru_cache
from fastapi import APIRouter,HTTPException,Query
from pydantic import BaseModel,Field
from jpai_api.platform_operations import OperationsError,OperationsStore
router=APIRouter(prefix="/platform-operations",tags=["platform-operations"])
@lru_cache(maxsize=1)
def get_store():return OperationsStore()
class Create(BaseModel):
 kind:str=Field(min_length=3,max_length=40)
 title:str=Field(min_length=3,max_length=200)
 brief:str=Field(min_length=10,max_length=8000)
class Update(BaseModel):fields:dict=Field(min_length=1)
class Transition(BaseModel):target:str=Field(min_length=2,max_length=40)
def call(fn,*args):
 try:return fn(*args)
 except OperationsError as e:
  m=str(e);raise HTTPException(status_code=404 if "not found" in m else 409,detail=m) from e
@router.get("/catalog")
def catalog():return {"count":10,"items":get_store().catalog()}
@router.get("/dashboard")
def dashboard():return get_store().dashboard()
@router.post("/projects",status_code=201)
def create(req:Create):return call(get_store().create,req.kind,req.title,req.brief)
@router.get("/projects")
def listing(kind:str|None=Query(default=None),limit:int=Query(default=100,ge=1,le=200)):
 return call(get_store().list,kind,limit)
@router.get("/projects/{pid}")
def get(pid:int):
 p=get_store().get(pid)
 if not p:raise HTTPException(status_code=404,detail="operation_not_found")
 return p
@router.patch("/projects/{pid}")
def update(pid:int,req:Update):return call(get_store().update,pid,req.fields)
@router.post("/projects/{pid}/transition")
def transition(pid:int,req:Transition):return call(get_store().transition,pid,req.target)
@router.get("/projects/{pid}/events")
def events(pid:int):
 e=get_store().events(pid)
 if e is None:raise HTTPException(status_code=404,detail="operation_not_found")
 return {"count":len(e),"items":e}
