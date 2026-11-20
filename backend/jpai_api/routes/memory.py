"""Persistent local memory endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from jpai_api.intelligence.persistence import IntelligenceStore

router=APIRouter(prefix="/memory",tags=["persistent-memory"])
store=IntelligenceStore()

class MemoryCreate(BaseModel):
    namespace:str=Field(default="general",min_length=1,max_length=80)
    title:str=Field(min_length=1,max_length=240)
    content:str=Field(min_length=1,max_length=30000)
    tags:list[str]=Field(default_factory=list,max_length=20)
    source:str=Field(default="user",max_length=80)

class MemorySearch(BaseModel):
    query:str=Field(min_length=2,max_length=500)
    namespace:str|None=Field(default=None,max_length=80)
    limit:int=Field(default=10,ge=1,le=50)

@router.get("")
def list_memories(namespace:str|None=None,limit:int=50):
    if limit<1 or limit>100: raise HTTPException(status_code=422,detail="limit must be between 1 and 100")
    items=store.list_memories(namespace,limit)
    return {"count":len(items),"items":items}

@router.post("")
def create_memory(request:MemoryCreate):
    tags=list(dict.fromkeys(t.strip()[:48] for t in request.tags if t.strip()))
    return store.create_memory(request.namespace.strip(),request.title.strip(),
                               request.content.strip(),tags,request.source.strip())

@router.post("/search")
def search_memory(request:MemorySearch):
    items=store.search_memories(request.query,request.namespace,request.limit)
    return {"count":len(items),"items":items,"method":"local_keyword_relevance"}
