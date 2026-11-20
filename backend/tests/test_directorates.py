"""Regression coverage for phases 13–20."""
import pytest
from jpai_api.directorates import CONFIG,DirectorateError,DirectorateStore
@pytest.fixture
def s(tmp_path):return DirectorateStore(tmp_path/"d.sqlite3")
@pytest.mark.parametrize("kind,cfg",list(CONFIG.items()))
def test_all_eight_create_persist_and_audit(s,kind,cfg):
 p=s.create(kind,"Project title","A sufficiently detailed project brief.")
 assert p["phase"]==cfg[0] and p["stage"]==cfg[2][0] and s.get(p["id"])["title"]==p["title"]
 assert s.events(p["id"])[0]["event"]=="created"
def test_graphic_design_gates(s):
 p=s.create("graphic_design","Identity","Create an identity.");i=p["id"]
 with pytest.raises(DirectorateError):s.transition(i,"concept")
 for f,v,t in [("creative_brief","Brief","concept"),("design_direction","Minimal","design_spec"),("design_spec",{"palette":["navy"]},"asset_production"),("asset_manifest",[{"asset_type":"logo","locator":"local://logo.svg"}],"review")]:
  s.update(i,{f:v});s.transition(i,t)
 s.update(i,{"review_checklist":["contrast"],"approval":{"status":"accepted"}});assert s.transition(i,"approved")["stage"]=="approved"
def test_video_evidence_and_review_gates(s):
 p=s.create("video_audio_animation","Film","Produce launch film.");i=p["id"]
 for f,v,t in [("creative_brief","Brief","script"),("script","Script","storyboard"),("storyboard",["scene"],"production_plan")]:
  s.update(i,{f:v});s.transition(i,t)
 with pytest.raises(DirectorateError):s.transition(i,"post_production")
 s.update(i,{"production_evidence":[{"artifact":"render://1"}]});s.transition(i,"post_production")
 with pytest.raises(DirectorateError):s.transition(i,"approved")
 s.update(i,{"final_review":{"status":"accepted"}});assert s.transition(i,"approved")["stage"]=="approved"
def test_digital_experience_requires_qa_and_launch_approval(s):
 p=s.create("digital_experience","Portal","Build a secure portal.");i=p["id"]
 for f,v,t in [("research_findings",["interviews"],"requirements"),("requirements",["login"],"ux_design"),("ux_spec",{"flows":["login"]},"implementation"),("implementation_artifacts",["commit:abc"],"quality_assurance")]:
  s.update(i,{f:v});s.transition(i,t)
 s.update(i,{"qa_evidence":[{"result":"passed","artifact":"ci://1"}],"launch_review":{"status":"approved"}})
 assert s.transition(i,"launch_ready")["stage"]=="launch_ready"
def test_business_marketing_activation_requires_approval(s):
 p=s.create("business_marketing","Campaign","Acquire customers.");i=p["id"]
 for f,v,t in [("customer_research",["interviews"],"strategy"),("marketing_strategy",{"goal":"leads"},"campaign_design"),("campaign_assets",[{"channel":"email"}],"activation")]:
  s.update(i,{f:v})
  if t=="activation":
   with pytest.raises(DirectorateError):s.transition(i,t)
   s.update(i,{"activation_approval":{"status":"approved"}})
  s.transition(i,t)
 with pytest.raises(DirectorateError):s.transition(i,"measurement")
def test_financial_analysis_requires_risk_and_human_approval(s):
 p=s.create("financial_intelligence","Portfolio","Analyze dataset.");i=p["id"]
 for f,v,t in [("data_sources",[{"source":"CSV"}],"data_mapping"),("data_mapping",{"currency":"USD"},"analysis")]:
  s.update(i,{f:v});s.transition(i,t)
 s.update(i,{"analysis_notes":"Descriptive analysis","risk_review":{"status":"qualified"}});s.transition(i,"risk_review");s.transition(i,"reporting")
 s.update(i,{"financial_report":"Report"})
 with pytest.raises(DirectorateError):s.transition(i,"approved")
 s.update(i,{"human_approval":True});assert s.transition(i,"approved")["stage"]=="approved"
def test_trading_needs_backtest_paper_risk_limits_and_human(s):
 p=s.create("trading_intelligence","Strategy","Research universal strategy.");i=p["id"]
 for f,v,t in [("market_universe",["BTC/USDT"],"data_validation"),("data_quality_report",{"missing":0},"strategy_research"),("strategy_spec",{"version":"1"},"backtest_review"),("backtest_evidence",[{"artifact":"backtest://1"}],"paper_trading")]:
  s.update(i,{f:v});s.transition(i,t)
 s.update(i,{"paper_trade_evidence":[{"artifact":"paper://1"}],"risk_controls":{"max_position_size":100,"max_daily_loss":10},"deployment_review":{"status":"approved"}})
 with pytest.raises(DirectorateError):s.transition(i,"deployment_eligible")
 s.update(i,{"human_approval":True});assert s.transition(i,"deployment_eligible")["stage"]=="deployment_eligible"
def test_automation_requires_owner_and_scoped_allowlist(s):
 p=s.create("enterprise_automation","Invoices","Route invoices.");i=p["id"]
 for f,v,t in [("process_map",["intake","review"],"workflow_design"),("workflow_spec",{"scope":"finance"},"permissions_review"),("permissions_review",{"status":"approved"},"simulation"),("simulation_evidence",[{"result":"passed","artifact":"sim://1"}],"approval")]:
  s.update(i,{f:v});s.transition(i,t)
 s.update(i,{"owner_approval":{"status":"approved"},"allowlisted_action_catalog":[{"action_id":"route_invoice","scope":"finance"}]})
 assert s.transition(i,"enabled")["stage"]=="enabled"
def test_journalism_requires_source_factcheck_and_explicit_approval(s):
 p=s.create("media_journalism","Investigation","Investigate policy change.");i=p["id"]
 for f,v,t in [("assignment_brief","Establish facts","research"),("sources",[{"locator":"https://example.org","excerpt":"Source excerpt"}],"draft"),("draft","Qualified attributed draft","fact_check"),("fact_check_status","qualified","editorial_review")]:
  s.update(i,{f:v});s.transition(i,t)
 s.update(i,{"editorial_notes":["Check dates"],"publication_approval":True})
 assert s.transition(i,"publication_approved")["stage"]=="publication_approved"
def test_unknown_fields_size_limits_and_skipped_stage_denied(s):
 p=s.create("graphic_design","Boundary","Test constraints.")
 with pytest.raises(DirectorateError):s.update(p["id"],{"shell_command":"unsafe"})
 with pytest.raises(DirectorateError):s.update(p["id"],{"creative_brief":"x"*100001})
 with pytest.raises(DirectorateError):s.transition(p["id"],"design_spec")
def test_api_catalog_and_denied_transition(tmp_path,monkeypatch):
 from jpai_api.routes import directorates as m
 from fastapi import HTTPException
 monkeypatch.setattr(m,"get_store",lambda:DirectorateStore(tmp_path/"api.sqlite3"))
 assert m.catalog()["count"]==8
 p=m.create(m.Create(kind="graphic_design",title="API project",brief="A sufficiently detailed API project brief."))
 assert p["stage"]=="brief"
 with pytest.raises(HTTPException) as exc:m.transition(p["id"],m.Transition(target="concept"))
 assert exc.value.status_code==409
