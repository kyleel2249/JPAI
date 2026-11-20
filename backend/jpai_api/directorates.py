"""Governed local project workflows for JPAI directorates 13–20."""
import json, os, sqlite3
from datetime import UTC, datetime
from pathlib import Path
CONFIG={
"graphic_design":(13,"Graphic Design & Visual Intelligence",["brief","concept","design_spec","asset_production","review","approved"],"creative_brief design_direction design_spec asset_manifest review_checklist approval brand_tokens accessibility_notes"),
"video_audio_animation":(14,"Video, Audio & Animation Studio",["concept","script","storyboard","production_plan","post_production","approved"],"creative_brief script storyboard production_plan production_evidence final_review rights_clearance delivery_specs audio_notes"),
"digital_experience":(15,"Creative Development & Digital Experiences",["discovery","requirements","ux_design","implementation","quality_assurance","launch_ready"],"research_findings requirements ux_spec architecture implementation_artifacts qa_evidence security_review launch_review"),
"business_marketing":(16,"Business, Marketing & Customer Intelligence",["discovery","strategy","campaign_design","activation","measurement","optimization"],"customer_research business_model marketing_strategy campaign_assets activation_approval performance_metrics improvement_actions budget_controls consent_review"),
"financial_intelligence":(17,"Financial Intelligence & ETI Integration",["intake","data_mapping","analysis","risk_review","reporting","approved"],"data_sources data_mapping analysis_notes assumptions risk_review financial_report reconciliation_evidence human_approval"),
"trading_intelligence":(18,"T-Bots Universal Trading Intelligence",["market_scope","data_validation","strategy_research","backtest_review","paper_trading","deployment_eligible"],"market_universe data_quality_report strategy_spec backtest_evidence paper_trade_evidence risk_controls deployment_review human_approval exchange_adapters"),
"enterprise_automation":(19,"Business & Enterprise Automation",["process_mapping","workflow_design","permissions_review","simulation","approval","enabled"],"process_map workflow_spec permissions_review simulation_evidence owner_approval allowlisted_action_catalog rollback_plan service_slo"),
"media_journalism":(20,"Media & Journalism Intelligence",["assignment","research","draft","fact_check","editorial_review","publication_approved"],"assignment_brief sources draft fact_check_status editorial_notes publication_approval corrections_log rights_review")}
FIELDS={k:set(v[3].split()) for k,v in CONFIG.items()}
GATES={
"graphic_design":{"concept":"creative_brief","design_spec":"design_direction","asset_production":"design_spec","review":"asset_manifest","approved":"review_checklist"},
"video_audio_animation":{"script":"creative_brief","storyboard":"script","production_plan":"storyboard","post_production":"production_evidence","approved":"final_review"},
"digital_experience":{"requirements":"research_findings","ux_design":"requirements","implementation":"ux_spec","quality_assurance":"implementation_artifacts","launch_ready":"qa_evidence"},
"business_marketing":{"strategy":"customer_research","campaign_design":"marketing_strategy","activation":"campaign_assets","measurement":"performance_metrics","optimization":"improvement_actions"},
"financial_intelligence":{"data_mapping":"data_sources","analysis":"data_mapping","risk_review":"analysis_notes","reporting":"risk_review","approved":"financial_report"},
"trading_intelligence":{"data_validation":"market_universe","strategy_research":"data_quality_report","backtest_review":"strategy_spec","paper_trading":"backtest_evidence","deployment_eligible":"paper_trade_evidence"},
"enterprise_automation":{"workflow_design":"process_map","permissions_review":"workflow_spec","simulation":"permissions_review","approval":"simulation_evidence","enabled":"owner_approval"},
"media_journalism":{"research":"assignment_brief","draft":"sources","fact_check":"draft","editorial_review":"fact_check_status","publication_approved":"editorial_notes"}}
class DirectorateError(ValueError):pass
class DirectorateStore:
 def __init__(self,path=None):
  self.path=Path(path or os.getenv("JPAI_DATABASE_PATH","data/jpai.sqlite3")).expanduser();self.path.parent.mkdir(parents=True,exist_ok=True)
  with self.db() as d:d.executescript("""CREATE TABLE IF NOT EXISTS directorate_projects(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,title TEXT NOT NULL,brief TEXT NOT NULL,stage TEXT NOT NULL,payload TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE INDEX IF NOT EXISTS idx_directorate_kind ON directorate_projects(kind,updated_at DESC);CREATE TABLE IF NOT EXISTS directorate_events(id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL,kind TEXT NOT NULL,event TEXT NOT NULL,details TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES directorate_projects(id) ON DELETE CASCADE);CREATE INDEX IF NOT EXISTS idx_directorate_events ON directorate_events(project_id,id);""")
 def db(self):
  d=sqlite3.connect(self.path,timeout=20);d.row_factory=sqlite3.Row;d.execute("PRAGMA foreign_keys=ON");return d
 @staticmethod
 def public(r):
  if r is None:return None
  x=dict(r);x["payload"]=json.loads(x["payload"]);c=CONFIG[x["kind"]];x.update(phase=c[0],directorate=c[1],stages=c[2]);return x
 @staticmethod
 def event(d,pid,k,e,detail):
  d.execute("INSERT INTO directorate_events(project_id,kind,event,details,created_at) VALUES(?,?,?,?,?)",(pid,k,e,json.dumps(detail),datetime.now(UTC).isoformat()))
 def create(self,kind,title,brief):
  if kind not in CONFIG:raise DirectorateError("Unsupported directorate.")
  if not isinstance(title,str) or not title.strip() or not isinstance(brief,str) or not brief.strip():raise DirectorateError("Title and brief are required.")
  now=datetime.now(UTC).isoformat();stage=CONFIG[kind][2][0]
  with self.db() as d:
   cur=d.execute("INSERT INTO directorate_projects(kind,title,brief,stage,payload,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(kind,title.strip(),brief.strip(),stage,"{}",now,now));pid=cur.lastrowid
   self.event(d,pid,kind,"created",{"phase":CONFIG[kind][0],"stage":stage});r=d.execute("SELECT * FROM directorate_projects WHERE id=?",(pid,)).fetchone()
  return self.public(r)
 def update(self,pid,fields):
  if not isinstance(fields,dict) or not fields:raise DirectorateError("Provide at least one payload field.")
  with self.db() as d:
   d.execute("BEGIN IMMEDIATE");r=d.execute("SELECT * FROM directorate_projects WHERE id=?",(pid,)).fetchone()
   if not r:raise DirectorateError("Directorate project not found.")
   unknown=set(fields)-FIELDS[r["kind"]]
   if unknown:raise DirectorateError("Unsupported fields: "+", ".join(sorted(unknown)))
   p=json.loads(r["payload"]);p.update(fields)
   try:encoded=json.dumps(p,ensure_ascii=False,allow_nan=False)
   except (TypeError,ValueError) as e:raise DirectorateError("Payload must contain finite JSON values.") from e
   if len(encoded.encode())>100000:raise DirectorateError("Project payload exceeds 100 KB.")
   d.execute("UPDATE directorate_projects SET payload=?,updated_at=? WHERE id=?",(encoded,datetime.now(UTC).isoformat(),pid));self.event(d,pid,r["kind"],"updated",{"fields":sorted(fields)})
   out=d.execute("SELECT * FROM directorate_projects WHERE id=?",(pid,)).fetchone()
  return self.public(out)
 @staticmethod
 def present(p,k):
  v=p.get(k)
  if isinstance(v,str):return bool(v.strip())
  if isinstance(v,(dict,list)):return bool(v)
  return v is not None and v is not False
 def gate(self,k,target,p):
  field=GATES[k][target]
  if not self.present(p,field):raise DirectorateError("Required evidence missing: "+field)
  if k=="graphic_design" and target=="approved" and (not isinstance(p.get("approval"),dict) or p["approval"].get("status") not in {"accepted","accepted_with_conditions"}):raise DirectorateError("Design approval must be accepted.")
  if k=="video_audio_animation" and target=="approved" and (not isinstance(p.get("final_review"),dict) or p["final_review"].get("status") not in {"accepted","accepted_with_conditions"}):raise DirectorateError("Final production review must be accepted.")
  if k=="digital_experience" and target=="launch_ready" and (not isinstance(p.get("launch_review"),dict) or p["launch_review"].get("status") not in {"approved","approved_with_conditions"}):raise DirectorateError("Launch review must be approved.")
  if k=="business_marketing" and target=="activation" and (not isinstance(p.get("activation_approval"),dict) or p["activation_approval"].get("status")!="approved"):raise DirectorateError("Campaign activation requires explicit approval.")
  if k=="financial_intelligence":
   if target=="reporting" and (not isinstance(p.get("risk_review"),dict) or p["risk_review"].get("status") not in {"accepted","qualified"}):raise DirectorateError("Financial risk review must be accepted or qualified.")
   if target=="approved" and p.get("human_approval") is not True:raise DirectorateError("Explicit human approval is required.")
  if k=="trading_intelligence" and target=="deployment_eligible":
   c=p.get("risk_controls");r=p.get("deployment_review")
   if not isinstance(c,dict) or not c.get("max_position_size") or not c.get("max_daily_loss"):raise DirectorateError("Define maximum position size and maximum daily loss.")
   if not isinstance(r,dict) or r.get("status")!="approved" or p.get("human_approval") is not True:raise DirectorateError("Approved deployment review and explicit human approval are required.")
  if k=="enterprise_automation" and target=="simulation" and (not isinstance(p.get("permissions_review"),dict) or p["permissions_review"].get("status")!="approved"):raise DirectorateError("Automation permissions review must be approved before simulation.")
  if k=="enterprise_automation" and target=="enabled":
   a=p.get("owner_approval");actions=p.get("allowlisted_action_catalog")
   if not isinstance(a,dict) or a.get("status")!="approved":raise DirectorateError("Process-owner approval is required.")
   if not isinstance(actions,list) or not actions or any(not isinstance(x,dict) or not x.get("action_id") or not x.get("scope") for x in actions):raise DirectorateError("Each action needs an explicit action_id and scope.")
  if k=="media_journalism" and target=="publication_approved":
   src=p.get("sources")
   if p.get("fact_check_status") not in {"verified","qualified"} or p.get("publication_approval") is not True:raise DirectorateError("Qualified/verified fact-check and explicit publication approval are required.")
   if not isinstance(src,list) or not src or any(not isinstance(x,dict) or not x.get("locator") or not x.get("excerpt") for x in src):raise DirectorateError("Each journalism source needs a locator and excerpt.")
 def transition(self,pid,target):
  with self.db() as d:
   d.execute("BEGIN IMMEDIATE");r=d.execute("SELECT * FROM directorate_projects WHERE id=?",(pid,)).fetchone()
   if not r:raise DirectorateError("Directorate project not found.")
   stages=CONFIG[r["kind"]][2];i=stages.index(r["stage"])
   if i+1>=len(stages) or stages[i+1]!=target:raise DirectorateError("Only the next sequential lifecycle stage is permitted.")
   self.gate(r["kind"],target,json.loads(r["payload"]));d.execute("UPDATE directorate_projects SET stage=?,updated_at=? WHERE id=?",(target,datetime.now(UTC).isoformat(),pid))
   self.event(d,pid,r["kind"],"stage_transition",{"from":r["stage"],"to":target});out=d.execute("SELECT * FROM directorate_projects WHERE id=?",(pid,)).fetchone()
  return self.public(out)
 def get(self,pid):
  with self.db() as d:return self.public(d.execute("SELECT * FROM directorate_projects WHERE id=?",(pid,)).fetchone())
 def list(self,kind=None,limit=100):
  with self.db() as d:
   rows=d.execute("SELECT * FROM directorate_projects WHERE kind=? ORDER BY updated_at DESC LIMIT ?",(kind,limit)).fetchall() if kind else d.execute("SELECT * FROM directorate_projects ORDER BY updated_at DESC LIMIT ?",(limit,)).fetchall()
   return [self.public(r) for r in rows]
 def events(self,pid):
  with self.db() as d:
   if not d.execute("SELECT 1 FROM directorate_projects WHERE id=?",(pid,)).fetchone():return None
   out=[dict(r) for r in d.execute("SELECT * FROM directorate_events WHERE project_id=? ORDER BY id",(pid,)).fetchall()]
   for x in out:x["details"]=json.loads(x["details"])
   return out
