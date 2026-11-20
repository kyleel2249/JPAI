"""Stable contracts for local model discovery, routing and inference."""
from pydantic import BaseModel, Field

class ModelProfile(BaseModel):
    id:str
    provider:str
    display_name:str
    family:str|None=None
    parameter_size:str|None=None
    quantization:str|None=None
    capabilities:list[str]=Field(default_factory=list)
    context_length:int|None=None
    available:bool=True

class ModelSelectionRequest(BaseModel):
    capability:str="chat"
    preferred_provider:str|None=None
    minimum_context:int|None=Field(default=None,ge=1)
    max_latency_ms:float|None=Field(default=None,gt=0)
    minimum_reliability:float=Field(default=0.0,ge=0,le=1)

class InferenceRequest(BaseModel):
    model:str
    prompt:str=Field(min_length=1,max_length=100_000)
    system:str|None=Field(default=None,max_length=20_000)
    temperature:float=Field(default=0.2,ge=0,le=2)

class InferenceResponse(BaseModel):
    model:str
    provider:str
    response:str
    duration_ms:float
    prompt_tokens:int|None=None
    completion_tokens:int|None=None

class BenchmarkRequest(BaseModel):
    model:str
    prompt:str=Field(default="Reply with the single word READY.",min_length=1,max_length=2000)
    iterations:int=Field(default=3,ge=1,le=10)

class AutoInferenceRequest(BaseModel):
    capability:str="chat"
    prompt:str=Field(min_length=1,max_length=100_000)
    system:str|None=Field(default=None,max_length=20_000)
    temperature:float=Field(default=0.2,ge=0,le=2)
    preferred_provider:str|None=None
    minimum_context:int|None=Field(default=None,ge=1)
    max_latency_ms:float|None=Field(default=None,gt=0)
    minimum_reliability:float=Field(default=0.0,ge=0,le=1)

class ModelComparisonRequest(BaseModel):
    models:list[str]=Field(min_length=2,max_length=5)
    prompt:str=Field(min_length=1,max_length=20_000)
    system:str|None=Field(default=None,max_length=5_000)
    temperature:float=Field(default=0.2,ge=0,le=2)
