"""Governed OpenAI Responses API adapter for the GPT-6 model family."""
from __future__ import annotations
import asyncio, time
from typing import Any
import httpx

MODEL_SPECS: dict[str, dict[str, Any]] = {
 "gpt-6.2-astra":{"name":"GPT-6.2 Astra","tier":"frontier","purpose":"complex reasoning, coding, architecture and synthesis","context_window":1050000,"max_input_tokens":922000,"max_output_tokens":128000,"reasoning_efforts":["low","medium","high","xhigh","max"],"modalities":["text_input","image_input","text_output"],"tools":["function_calling","web_search","file_search","image_generation","code_interpreter","hosted_shell","apply_patch","skills","computer_use","mcp","tool_search"],"input_usd_per_million":8.0,"cached_input_usd_per_million":0.4,"output_usd_per_million":40.0},
 "gpt-6.2-sol":{"name":"GPT-6.2 Sol","tier":"balanced","purpose":"multi-step workflows, coding and agent-scale work","context_window":1050000,"max_input_tokens":922000,"max_output_tokens":128000,"reasoning_efforts":["low","medium","high","xhigh","max"],"modalities":["text_input","image_input","text_output"],"tools":["function_calling","web_search","file_search","computer_use"],"input_usd_per_million":2.0,"cached_input_usd_per_million":0.1,"output_usd_per_million":10.0},
 "gpt-6-luna":{"name":"GPT-6 Luna","tier":"efficient","purpose":"focused, repeatable and high-volume tasks","context_window":1050000,"max_input_tokens":922000,"max_output_tokens":128000,"reasoning_efforts":["none","low","medium","high","xhigh","max"],"modalities":["text_input","image_input","text_output"],"tools":["function_calling","web_search","file_search","image_generation","code_interpreter","hosted_shell","apply_patch","skills","computer_use","mcp","tool_search"],"input_usd_per_million":0.1,"cached_input_usd_per_million":0.01,"output_usd_per_million":0.5},
}
SAFE_TOOLS={"web_search_preview","code_interpreter","image_generation"}

class ModelFabricError(RuntimeError): pass
class ProviderNotConfigured(ModelFabricError): pass

class OpenAIResponsesRuntime:
 def __init__(self,api_key:str|None,base_url:str="https://api.openai.com/v1",timeout_seconds:float=180,max_concurrency:int=8):
  self.api_key=api_key.strip() if api_key else "";self.base_url=base_url.rstrip("/");self.timeout_seconds=timeout_seconds
  self.semaphore=asyncio.Semaphore(max(1,min(max_concurrency,32)))
 @property
 def configured(self): return bool(self.api_key)
 def catalog(self):
  return [{"id":k,**v,"provider":"openai","configured":self.configured,"availability":"credentials_configured" if self.configured else "awaiting_api_key"} for k,v in MODEL_SPECS.items()]
 @staticmethod
 def cost(model,usage):
  spec=MODEL_SPECS[model];total=int(usage.get("input_tokens") or 0);out=int(usage.get("output_tokens") or 0)
  cached=min(total,int((usage.get("input_tokens_details") or {}).get("cached_tokens") or 0))
  return round(((total-cached)*spec["input_usd_per_million"]+cached*spec["cached_input_usd_per_million"]+out*spec["output_usd_per_million"])/1_000_000,8)
 @staticmethod
 def output_text(data):
  if isinstance(data.get("output_text"),str):return data["output_text"]
  return "\n".join(c["text"] for item in data.get("output",[]) if isinstance(item,dict) for c in item.get("content",[]) if isinstance(c,dict) and c.get("type") in {"output_text","text"} and isinstance(c.get("text"),str))
 async def infer(self,model,prompt,system=None,reasoning_effort="medium",max_output_tokens=4096,image_urls=None,json_schema=None,tools=None,function_tools=None):
  if not self.configured: raise ProviderNotConfigured("Set JPAI_OPENAI_API_KEY in the backend environment.")
  if model not in MODEL_SPECS: raise ModelFabricError("Model is not in the approved GPT-6 catalogue.")
  spec=MODEL_SPECS[model]
  if reasoning_effort not in spec["reasoning_efforts"]: raise ModelFabricError("Unsupported reasoning effort for this model.")
  if not 1<=max_output_tokens<=spec["max_output_tokens"]: raise ModelFabricError("Output token limit is outside model bounds.")
  content=[{"type":"input_text","text":prompt}]
  for url in image_urls or []:
   if not url.startswith("https://"): raise ModelFabricError("Image inputs must be HTTPS URLs.")
   content.append({"type":"input_image","image_url":url})
  items=([{"role":"system","content":system}] if system else [])+[{"role":"user","content":content}]
  payload={"model":model,"input":items,"max_output_tokens":max_output_tokens,"reasoning":{"effort":reasoning_effort}}
  selected=tools or []
  if set(selected)-SAFE_TOOLS: raise ModelFabricError("Tool is not enabled by JPAI's safe hosted-tool policy.")
  if selected:payload["tools"]=[{"type":x} for x in selected]
  if function_tools:
   if len(function_tools)>12:raise ModelFabricError("At most 12 function declarations are allowed.")
   for f in function_tools:
    if not isinstance(f,dict) or not f.get("name") or not isinstance(f.get("parameters"),dict):raise ModelFabricError("Function tools require name and JSON-schema parameters.")
   payload.setdefault("tools",[]).extend({"type":"function","name":f["name"],"description":f.get("description",""),"parameters":f["parameters"],"strict":bool(f.get("strict",True))} for f in function_tools)
  if json_schema:payload["text"]={"format":{"type":"json_schema","name":"jpai_structured_output","schema":json_schema,"strict":True}}
  started=time.perf_counter()
  async with self.semaphore:
   try:
    async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
     response=await client.post(self.base_url+"/responses",json=payload,headers={"Authorization":"Bearer "+self.api_key,"Content-Type":"application/json"})
     response.raise_for_status();data=response.json()
   except (httpx.HTTPError,ValueError) as exc:raise ModelFabricError("OpenAI Responses API request failed; inspect provider status and telemetry.") from exc
  usage=data.get("usage") or {};output=data.get("output") or []
  calls=[{"name":x.get("name"),"call_id":x.get("call_id"),"arguments":x.get("arguments")} for x in output if isinstance(x,dict) and x.get("type")=="function_call"]
  return {"model":model,"provider":"openai","response":self.output_text(data),"duration_ms":round((time.perf_counter()-started)*1000,2),"usage":usage,"estimated_cost_usd":self.cost(model,usage),"tool_calls_pending_governance":calls,"response_id":data.get("id"),"status":data.get("status","completed")}
