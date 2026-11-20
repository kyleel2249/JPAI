from fastapi.testclient import TestClient

from jpai_api.main import app
from jpai_api.routes import quality as quality_routes
from jpai_api.quality.store import QualityStore

client = TestClient(app)


def setup_quality(monkeypatch, tmp_path):
    quality_routes.get_store.cache_clear()
    monkeypatch.setenv("JPAI_DATABASE_PATH", str(tmp_path / "quality.sqlite3"))
    return quality_routes.get_store()


def test_cycle_requires_sequential_evidence_gated_stages(monkeypatch, tmp_path):
    setup_quality(monkeypatch, tmp_path)
    created = client.post("/api/v1/quality/cycles", json={
        "title": "JPAI reliability improvement",
        "scope": "Review backend reliability, frontend dependencies and dashboard workflows.",
        "baseline": "Baseline captured: dependency advisories, API behavior and current CI results.",
    })
    assert created.status_code == 200
    cycle_id = created.json()["id"]
    skipped = client.post(f"/api/v1/quality/cycles/{cycle_id}/advance", json={
        "stage": "improve", "evidence": "A proposed improvement was made after the initial build.",
    })
    assert skipped.status_code == 409
    for stage in ("reassess", "improve", "test", "verify"):
        result = client.post(f"/api/v1/quality/cycles/{cycle_id}/advance", json={
            "stage": stage, "evidence": f"Evidence for the {stage} stage has been recorded and reviewed.",
        })
        assert result.status_code == 200
    assert result.json()["status"] == "completed"
    duplicate = client.post(f"/api/v1/quality/cycles/{cycle_id}/advance", json={
        "stage": "verify", "evidence": "Attempt to verify a completed cycle again.",
    })
    assert duplicate.status_code == 404
    assert len(client.get("/api/v1/quality/events?record_type=cycle&record_id=1").json()["items"]) == 5


def test_issue_resolution_requires_assessment_and_root_cause_before_fix(monkeypatch, tmp_path):
    setup_quality(monkeypatch, tmp_path)
    created = client.post("/api/v1/quality/issues", json={
        "title": "Frontend dependency security alerts",
        "description": "The CI install reported multiple package vulnerabilities requiring investigation.",
        "component": "frontend-dependencies",
        "severity": "critical",
    })
    assert created.status_code == 200
    issue_id = created.json()["id"]
    skipped = client.post(f"/api/v1/quality/issues/{issue_id}/advance", json={
        "stage": "fix_implemented", "evidence": "Dependencies were updated without root-cause analysis.",
    })
    assert skipped.status_code == 409
    for stage in ("assessed", "cause_identified", "fix_implemented", "tested", "verified"):
        result = client.post(f"/api/v1/quality/issues/{issue_id}/advance", json={
            "stage": stage, "evidence": f"Documented evidence supporting {stage} for the issue.",
        })
        assert result.status_code == 200
    assert result.json()["status"] == "verified"
    assert result.json()["root_cause"] is not None
    assert result.json()["corrective_action"] is not None
    assert result.json()["test_result"] is not None
    assert result.json()["verification_result"] is not None


def test_quality_store_uses_existing_local_database_and_preserves_records(tmp_path):
    path = str(tmp_path / "shared.db")
    first = QualityStore(path)
    first.create_issue("A local issue", "A detailed description of the issue.", "core", "low")
    second = QualityStore(path)
    assert len(second.list_issues()) == 1
