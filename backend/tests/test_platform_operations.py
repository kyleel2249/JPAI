import pytest
from jpai_api.platform_operations import PHASES,OperationsError,OperationsStore

@pytest.fixture
def store(tmp_path):return OperationsStore(tmp_path/"ops.sqlite3")

@pytest.mark.parametrize("kind,cfg",list(PHASES.items()))
def test_all_ten_phase_workflows_persist_and_audit(store,kind,cfg):
 p=store.create(kind,"Phase project","A sufficiently detailed project brief.")
 assert p["phase"]==cfg[0] and p["stage"]==cfg[2][0]
 assert store.get(p["id"])["title"]==p["title"]
 assert store.events(p["id"])[0]["event"]=="created"
 assert store.dashboard()["phase_count"]==10

@pytest.mark.parametrize("kind,cfg",list(PHASES.items()))
def test_all_phase_workflows_fail_closed_without_evidence(store,kind,cfg):
 p=store.create(kind,"Gate project","A sufficiently detailed project brief.")
 with pytest.raises(OperationsError):store.transition(p["id"],cfg[2][1])

@pytest.mark.parametrize("kind,cfg",list(PHASES.items()))
def test_all_phase_fields_are_allowlisted(store,kind,cfg):
 p=store.create(kind,"Allowlist project","A sufficiently detailed project brief.")
 with pytest.raises(OperationsError):store.update(p["id"],{"shell_command":"whoami"})

def test_personal_intelligence_sequential_gates_and_approval(store):
 p=store.create("personal_intelligence","Personal profile","Define a local personal intelligence profile.")
 i=p["id"]
 with pytest.raises(OperationsError):store.transition(i,"integration_design")
 store.update(i,{"personal_profile":{"goals":["organise"]}})
 store.transition(i,"integration_design")
 store.update(i,{"preferences":{"local_first":True},"integration_scope":{"system":"JPTI","mode":"read_only"}})
 store.transition(i,"privacy_review")
 store.update(i,{"privacy_review":{"status":"approved"}})
 store.transition(i,"approval")
 with pytest.raises(OperationsError):store.transition(i,"ready")
 store.update(i,{"human_approval":True})
 assert store.transition(i,"ready")["stage"]=="ready"

def test_decision_requires_full_evidence_and_review(store):
 p=store.create("decision_intelligence","Decision","Evaluate alternatives with evidence.")
 i=p["id"]
 store.update(i,{"decision_question":"Which option?","evidence_set":[{"source":"local://1"}],"alternatives":["A","B"],"risk_assessment":{"risks":["cost"]},"decision_review":{"status":"approved"}})
 for target in ["evidence","alternatives","risk_review","decision"]:store.transition(i,target)
 assert store.get(i)["stage"]=="decision"

def test_payload_limit_unknown_project_and_event_history(store):
 p=store.create("command_centre","Telemetry","Monitor platform telemetry and operations.")
 with pytest.raises(OperationsError):store.update(p["id"],{"dashboard_config":"x"*100_001})
 assert store.events(p["id"])[-1]["event"]=="created"
 assert store.get(99999) is None and store.events(99999) is None

def test_dashboard_is_transparent_about_non_execution(store):
 d=store.dashboard()
 assert d["execution_mode"]=="record_and_review_only"
 assert d["external_actions_enabled"] is False

def test_api_routes_and_denial(tmp_path,monkeypatch):
 from fastapi import HTTPException
 from jpai_api.routes import platform_operations as api
 monkeypatch.setattr(api,"get_store",lambda:OperationsStore(tmp_path/"api.sqlite3"))
 assert api.catalog()["count"]==10
 p=api.create(api.Create(kind="software_development",title="API project",brief="A sufficiently detailed software project brief."))
 with pytest.raises(HTTPException) as exc:api.transition(p["id"],api.Transition(target="verification"))
 assert exc.value.status_code==409
