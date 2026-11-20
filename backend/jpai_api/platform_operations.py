"""Governed operational kernel for JPAI roadmap phases 21–30.

This module records plans, evidence and approvals. It deliberately does not
execute trades, mutate models, run shell commands, pair devices or invoke tools.
"""
from __future__ import annotations
import json, os, sqlite3
from datetime import UTC, datetime
from pathlib import Path

PHASES = {
 "personal_intelligence": (21,"Personal Intelligence & JPTI Integration",["profile","integration_design","privacy_review","approval","ready"],"personal_profile preferences integration_scope privacy_review human_approval"),
 "decision_intelligence": (22,"Advanced Reasoning & Decision Intelligence",["question","evidence","alternatives","risk_review","decision"],"decision_question evidence_set alternatives risk_assessment decision_review"),
 "project_execution": (23,"Autonomous Project Execution",["plan","decomposition","simulation","execution_review","completed"],"project_plan task_graph simulation_evidence acceptance_results release_approval"),
 "adaptive_learning": (24,"Adaptive Learning & Agent Evolution",["signals","evaluation","proposal","governance","approved"],"feedback_records evaluation_dataset evaluation_report change_proposal human_approval"),
 "tool_intelligence": (25,"Advanced Automation & Tool Intelligence",["inventory","scoping","security_review","simulation","approved"],"tool_manifest permission_scope threat_review simulation_evidence owner_approval"),
 "software_development": (26,"Autonomous Software Development",["requirements","design","implementation","verification","release_ready"],"requirements design implementation_refs test_evidence security_review release_approval"),
 "command_centre": (27,"World-Class JPAI Command Centre",["configuration","telemetry","alerting","operator_review","operational"],"dashboard_config service_metrics alert_rules operator_review"),
 "device_ecosystem": (28,"Desktop & Android Ecosystem",["inventory","sync_design","security_review","pairing_review","paired"],"device_registry sync_policy encryption_review pairing_approval"),
 "security_governance": (29,"Enterprise Security & Governance",["threat_model","access_review","policy_review","incident_readiness","compliant"],"threat_model access_review policy_set incident_plan security_approval"),
 "reliability_engineering": (30,"Performance & Reliability Engineering",["objectives","load_testing","recovery_testing","operations_review","certified"],"slo_targets load_test_evidence backup_restore_evidence recovery_drill ops_approval"),
}
MAX_BYTES=100_000
# Evidence is collected incrementally, one gate per transition.
GATES = {
 "personal_intelligence":[["personal_profile"],["preferences","integration_scope"],["privacy_review"],["human_approval"]],
 "decision_intelligence":[["decision_question"],["evidence_set","alternatives"],["risk_assessment"],["decision_review"]],
 "project_execution":[["project_plan"],["task_graph"],["simulation_evidence"],["acceptance_results","release_approval"]],
 "adaptive_learning":[["feedback_records"],["evaluation_dataset","evaluation_report"],["change_proposal"],["human_approval"]],
 "tool_intelligence":[["tool_manifest"],["permission_scope","threat_review"],["simulation_evidence"],["owner_approval"]],
 "software_development":[["requirements"],["design"],["implementation_refs"],["test_evidence","security_review","release_approval"]],
 "command_centre":[["dashboard_config"],["service_metrics"],["alert_rules"],["operator_review"]],
 "device_ecosystem":[["device_registry"],["sync_policy"],["encryption_review"],["pairing_approval"]],
 "security_governance":[["threat_model"],["access_review"],["policy_set"],["incident_plan","security_approval"]],
 "reliability_engineering":[["slo_targets"],["load_test_evidence"],["backup_restore_evidence"],["recovery_drill","ops_approval"]],
}

class OperationsError(ValueError): pass

class OperationsStore:
 def __init__(self,path=None):
  self.path=Path(path or os.getenv("JPAI_DATABASE_PATH","data/jpai.sqlite3")).expanduser()
  self.path.parent.mkdir(parents=True,exist_ok=True)
  with self._db() as db:
   db.executescript("""
   CREATE TABLE IF NOT EXISTS platform_operations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,title TEXT NOT NULL,
    brief TEXT NOT NULL,stage TEXT NOT NULL,payload TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
   CREATE INDEX IF NOT EXISTS idx_platform_operations_kind ON platform_operations(kind,updated_at DESC);
   CREATE TABLE IF NOT EXISTS platform_operation_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,project_id INTEGER NOT NULL,event TEXT NOT NULL,
    details TEXT NOT NULL,created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES platform_operations(id) ON DELETE CASCADE);
   CREATE INDEX IF NOT EXISTS idx_platform_operation_events_project ON platform_operation_events(project_id,id);
   """)
 def _db(self):
  db=sqlite3.connect(self.path,timeout=20);db.row_factory=sqlite3.Row
  db.execute("PRAGMA foreign_keys=ON");return db
 @staticmethod
 def _public(row):
  if row is None:return None
  x=dict(row);x["payload"]=json.loads(x["payload"])
  phase,name,stages,_=PHASES[x["kind"]]
  x.update(phase=phase,directorate=name,stages=stages);return x
 def catalog(self):
  return [{"kind":k,"phase":v[0],"name":v[1],"stages":v[2],"fields":v[3].split()} for k,v in PHASES.items()]
 def create(self,kind,title,brief):
  if kind not in PHASES:raise OperationsError("Unsupported phase or operation kind.")
  if len(title.strip())<3 or len(brief.strip())<10:raise OperationsError("Title or brief is too short.")
  now=datetime.now(UTC).isoformat()
  with self._db() as db:
   cur=db.execute("INSERT INTO platform_operations(kind,title,brief,stage,payload,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(kind,title.strip(),brief.strip(),PHASES[kind][2][0],"{}",now,now))
   i=cur.lastrowid;self._event(db,i,"created",{"kind":kind,"phase":PHASES[kind][0]})
   return self._public(db.execute("SELECT * FROM platform_operations WHERE id=?",(i,)).fetchone())
 def get(self,i):
  with self._db() as db:return self._public(db.execute("SELECT * FROM platform_operations WHERE id=?",(i,)).fetchone())
 def list(self,kind=None,limit=100):
  if kind is not None and kind not in PHASES:raise OperationsError("Unsupported phase or operation kind.")
  with self._db() as db:
   rows=db.execute("SELECT * FROM platform_operations"+(" WHERE kind=?" if kind else "")+" ORDER BY updated_at DESC,id DESC LIMIT ?",((kind,limit) if kind else (limit,))).fetchall()
   return [self._public(r) for r in rows]
 @staticmethod
 def _event(db,i,event,details):
  db.execute("INSERT INTO platform_operation_events(project_id,event,details,created_at) VALUES(?,?,?,?)",(i,event,json.dumps(details,sort_keys=True),datetime.now(UTC).isoformat()))
 def update(self,i,fields):
  with self._db() as db:
   row=db.execute("SELECT * FROM platform_operations WHERE id=?",(i,)).fetchone()
   if row is None:raise OperationsError("Operation not found.")
   allowed=set(PHASES[row["kind"]][3].split())
   if not fields or set(fields)-allowed:raise OperationsError("Empty or unsupported evidence fields.")
   payload=json.loads(row["payload"]);payload.update(fields)
   encoded=json.dumps(payload,separators=(",",":"),ensure_ascii=False)
   if len(encoded.encode())>MAX_BYTES:raise OperationsError("Evidence payload exceeds 100 KB.")
   now=datetime.now(UTC).isoformat()
   db.execute("UPDATE platform_operations SET payload=?,updated_at=? WHERE id=?",(encoded,now,i))
   self._event(db,i,"evidence_updated",{"fields":sorted(fields)})
   return self._public(db.execute("SELECT * FROM platform_operations WHERE id=?",(i,)).fetchone())
 def transition(self,i,target):
  with self._db() as db:
   row=db.execute("SELECT * FROM platform_operations WHERE id=?",(i,)).fetchone()
   if row is None:raise OperationsError("Operation not found.")
   phase,_,stages,_=PHASES[row["kind"]]
   current=stages.index(row["stage"])
   if current>=len(stages)-1 or target!=stages[current+1]:raise OperationsError("Only the next sequential lifecycle stage is permitted.")
   payload=json.loads(row["payload"])
   required=GATES[row["kind"]][current]
   missing=[f for f in required if f not in payload or payload[f] is None or payload[f] is False or payload[f]=="" or payload[f]==[] or payload[f]=={}]
   if missing:raise OperationsError("Evidence gate not satisfied; missing: "+", ".join(missing))
   # Consequential transitions must be explicitly approved; no transition invokes external actions.
   approval_keys={"personal_intelligence":"human_approval","decision_intelligence":"decision_review","project_execution":"release_approval","adaptive_learning":"human_approval","tool_intelligence":"owner_approval","software_development":"release_approval","device_ecosystem":"pairing_approval","security_governance":"security_approval","reliability_engineering":"ops_approval"}
   key=approval_keys.get(row["kind"])
   if current==len(stages)-2 and key:
    value=payload.get(key)
    if value is not True and not (isinstance(value,dict) and value.get("status")=="approved"):
     raise OperationsError("Final stage requires explicit approval: "+key)
   now=datetime.now(UTC).isoformat()
   db.execute("UPDATE platform_operations SET stage=?,updated_at=? WHERE id=?",(target,now,i))
   self._event(db,i,"stage_transition",{"from":row["stage"],"to":target,"phase":phase})
   return self._public(db.execute("SELECT * FROM platform_operations WHERE id=?",(i,)).fetchone())
 def events(self,i):
  with self._db() as db:
   if db.execute("SELECT 1 FROM platform_operations WHERE id=?",(i,)).fetchone() is None:return None
   rows=db.execute("SELECT * FROM platform_operation_events WHERE project_id=? ORDER BY id",(i,)).fetchall()
   return [{**dict(r),"details":json.loads(r["details"])} for r in rows]
 def dashboard(self):
  items=self.list(limit=200);counts={k:0 for k in PHASES};stages={}
  for x in items:counts[x["kind"]]+=1;stages[x["kind"]]=x["stage"]
  return {"phase_range":[21,30],"phase_count":10,"project_count":len(items),"projects_by_phase":counts,"latest_stage_by_phase":stages,"governance":"evidence_gated_sequential","execution_mode":"record_and_review_only","external_actions_enabled":False}
