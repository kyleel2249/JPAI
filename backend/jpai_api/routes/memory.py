"""Persistent local memory and knowledge-graph endpoints."""
from functools import lru_cache
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from jpai_api.intelligence.persistence import IntelligenceStore
router=APIRouter(prefix="/memory",tags=["persistent-memory","knowledge-graph"])
@lru_cache(maxsize=1)
def get_store():return IntelligenceStore()
class MemoryCreate(BaseModel):
    namespace:str=Field(default="general",min_length=1,max_length=80)
    title:str=Field(min_length=1,max_length=240)
    content:str=Field(min_length=1,max_length=30000)
    tags:list[str]=Field(default_factory=list,max_length=20)
    source:str=Field(default="user",max_length=80)
    memory_type:str=Field(default="semantic",pattern="^(working|episodic|semantic|procedural)$")
    importance:float=Field(default=0.5,ge=0,le=1)
    metadata:dict=Field(default_factory=dict)
class MemorySearch(BaseModel):
    query:str=Field(min_length=2,max_length=500)
    namespace:str|None=Field(default=None,max_length=80)
    memory_type:str|None=Field(default=None,pattern="^(working|episodic|semantic|procedural)$")
    limit:int=Field(default=10,ge=1,le=50)
class MemoryUpdate(BaseModel):
    title:str|None=Field(default=None,min_length=1,max_length=240)
    content:str|None=Field(default=None,min_length=1,max_length=30000)
    importance:float|None=Field(default=None,ge=0,le=1)
    tags:list[str]|None=Field(default=None,max_length=20)
class EntityCreate(BaseModel):
    name:str=Field(min_length=1,max_length=160)
    entity_type:str=Field(min_length=1,max_length=80)
    description:str=Field(default="",max_length=2000)
    metadata:dict=Field(default_factory=dict)
class RelationCreate(BaseModel):
    source_id:int=Field(gt=0);target_id:int=Field(gt=0)
    relation_type:str=Field(min_length=1,max_length=100)
    confidence:float=Field(default=0.8,ge=0,le=1)
    source_memory_id:int|None=Field(default=None,gt=0)
@router.get("")
def list_memories(namespace:str|None=None,memory_type:str|None=None,limit:int=50):
    if limit<1 or limit>100:raise HTTPException(status_code=422,detail="limit_must_be_between_1_and_100")
    if memory_type and memory_type not in {"working","episodic","semantic","procedural"}:raise HTTPException(status_code=422,detail="invalid_memory_type")
    items=get_store().list_memories(namespace,limit,memory_type);return {"count":len(items),"items":items}
@router.post("")
def create_memory(request:MemoryCreate):
    tags=list(dict.fromkeys(t.strip()[:48] for t in request.tags if t.strip()))
    return get_store().create_memory(request.namespace.strip(),request.title.strip(),request.content.strip(),tags,request.source.strip(),request.memory_type,request.importance,request.metadata)
@router.post("/search")
def search_memory(request:MemorySearch):
    items=get_store().search_memories(request.query,request.namespace,request.limit,request.memory_type)
    return {"count":len(items),"items":items,"method":"weighted_local_keyword_relevance"}
@router.patch("/{memory_id}")
def update_memory(memory_id:int,request:MemoryUpdate):
    payload=request.model_dump(exclude_unset=True)
    if payload.get("tags") is not None:payload["tags"]=list(dict.fromkeys(t.strip()[:48] for t in payload["tags"] if t.strip()))
    item=get_store().update_memory(memory_id,**payload)
    if not item:raise HTTPException(status_code=404,detail="active_memory_not_found")
    return item
@router.delete("/{memory_id}")
def archive_memory(memory_id:int):
    if not get_store().archive_memory(memory_id):raise HTTPException(status_code=404,detail="active_memory_not_found")
    return {"id":memory_id,"status":"archived"}
@router.post("/entities")
def upsert_entity(request:EntityCreate):return get_store().upsert_entity(request.name,request.entity_type,request.description,request.metadata)
@router.post("/relations")
def create_relation(request:RelationCreate):
    item=get_store().create_relation(request.source_id,request.target_id,request.relation_type,request.confidence,request.source_memory_id)
    if not item:raise HTTPException(status_code=404,detail="knowledge_entity_not_found")
    return item
@router.get("/graph")
def get_knowledge_graph(limit:int=200):
    if limit<1 or limit>500:raise HTTPException(status_code=422,detail="limit_must_be_between_1_and_500")
    graph=get_store().knowledge_graph(limit);return {**graph,"entity_count":len(graph["entities"]),"relation_count":len(graph["relations"])}
