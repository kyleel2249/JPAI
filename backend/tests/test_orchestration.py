import inspect
from jpai_api.intelligence.orchestration import OrchestrationStore
from jpai_api.routes import model_fabric as routes

def test_orchestration_ledger_persists_runs_and_checkpoints(tmp_path):
    path = str(tmp_path / "orchestration.sqlite3")
    store = OrchestrationStore(path)
    run_id = store.create_run("test task", ["a", "b"])
    store.checkpoint(run_id, "parallel", "completed", {"completed_count": 2})
    store.finish(run_id, "completed", {"answer": "verified"})
    reopened = OrchestrationStore(path).get_run(run_id)
    assert reopened["status"] == "completed"
    assert reopened["result"]["answer"] == "verified"
    assert [x["phase"] for x in reopened["checkpoints"]] == ["initialised", "parallel"]

def test_orchestration_ledger_lists_runs(tmp_path):
    store = OrchestrationStore(str(tmp_path / "orchestration.sqlite3"))
    first = store.create_run("first task", ["a", "b"])
    second = store.create_run("second task", ["a", "c"])
    ids = [x["id"] for x in store.list_runs()]
    assert first in ids and second in ids

def test_council_exposes_run_history_and_peer_review():
    paths = {route.path for route in routes.router.routes}
    assert "/model-fabric/council/runs" in paths
    assert "/model-fabric/council/runs/{run_id}" in paths
    assert "peer_review_pass" in routes.CouncilRequest.model_fields

def test_council_has_parallel_specialist_and_peer_review_stages():
    source = inspect.getsource(routes.council)
    assert source.count("asyncio.gather") >= 2
    assert "shared_agent_workspace" in source
    assert "ledger.checkpoint" in source
    assert "jpai-6.2-ultra" in source and "jpai-6.2-pro" in source