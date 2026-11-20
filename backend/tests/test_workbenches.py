"""Regression tests for the Phase 11 engineering workbench."""
import pytest

from jpai_api.workbenches import WorkbenchError, WorkbenchStore


def test_engineering_workflow_is_sequential_and_evidence_gated(tmp_path):
    store = WorkbenchStore(tmp_path / "workbenches.sqlite3")
    project = store.create("engineering", "Engineering platform", "Deliver a resilient local platform.")
    project_id = project["id"]
    with pytest.raises(WorkbenchError, match="sequential"):
        store.transition(project_id, "design")
    store.update(project_id, {"requirements": ["API contract", "security boundaries"]})
    assert store.transition(project_id, "requirements")["stage"] == "requirements"
    with pytest.raises(WorkbenchError, match="Architecture"):
        store.transition(project_id, "design")
    store.update(project_id, {"architecture_decisions": ["SQLite persistence", "local-first API"]})
    store.transition(project_id, "design")
    store.update(project_id, {"deliverables": ["API implementation"]})
    store.transition(project_id, "implementation")
    store.update(project_id, {"test_evidence": [{"result": "passed", "artifact": "CI run #42"}]})
    store.transition(project_id, "verification")
    with pytest.raises(WorkbenchError, match="Risk review"):
        store.transition(project_id, "release_ready")
    store.update(project_id, {"risk_review": {"status": "accepted_with_conditions", "notes": "Monitor load"}})
    assert store.transition(project_id, "release_ready")["stage"] == "release_ready"


def test_engineering_audit_events_are_durable_and_ordered(tmp_path):
    store = WorkbenchStore(tmp_path / "audit.sqlite3")
    project = store.create("engineering", "Audit test", "Test durable event history.")
    store.update(project["id"], {"owner": "Engineering lead"})
    events = store.events(project["id"])
    assert [event["event"] for event in events] == ["created", "updated"]
    assert store.get(project["id"])["payload"]["owner"] == "Engineering lead"


def test_engineering_rejects_unknown_fields_and_bad_test_evidence(tmp_path):
    store = WorkbenchStore(tmp_path / "validation.sqlite3")
    project = store.create("engineering", "Validation", "Validate field boundaries.")
    with pytest.raises(WorkbenchError, match="Unsupported fields"):
        store.update(project["id"], {"arbitrary_command": "run"})
    store.update(project["id"], {"requirements": ["A"]})
    store.transition(project["id"], "requirements")
    store.update(project["id"], {"architecture_decisions": ["Decision"]})
    store.transition(project["id"], "design")
    store.update(project["id"], {"deliverables": ["Build"]})
    store.transition(project["id"], "implementation")
    store.update(project["id"], {"test_evidence": [{"result": "passed"}]})
    with pytest.raises(WorkbenchError, match="artifact reference"):
        store.transition(project["id"], "verification")


def test_editorial_workflow_requires_sources_review_and_explicit_approval(tmp_path):
    store = WorkbenchStore(tmp_path / "editorial.sqlite3")
    project = store.create("editorial", "Energy policy explainer", "Explain energy policy changes.")
    project_id = project["id"]
    store.update(project_id, {"outline": ["Background", "Policy", "Implications"]})
    store.transition(project_id, "outline")
    store.update(project_id, {"draft": "A carefully qualified editorial draft."})
    store.transition(project_id, "draft")
    with pytest.raises(WorkbenchError, match="Source records"):
        store.transition(project_id, "fact_check")
    store.update(project_id, {
        "sources": [{"locator": "https://example.org/report", "excerpt": "Source excerpt; unverified"}],
        "fact_check_status": "qualified",
    })
    store.transition(project_id, "fact_check")
    store.update(project_id, {"editorial_notes": ["Clarify date range", "Qualify causal language"]})
    store.transition(project_id, "editorial_review")
    with pytest.raises(WorkbenchError, match="approval"):
        store.transition(project_id, "ready_to_publish")
    store.update(project_id, {"publication_approved": True})
    assert store.transition(project_id, "ready_to_publish")["stage"] == "ready_to_publish"


def test_editorial_source_records_require_locator_and_excerpt(tmp_path):
    store = WorkbenchStore(tmp_path / "editorial-sources.sqlite3")
    project = store.create("editorial", "Source validation", "Validate source records.")
    store.update(project["id"], {"outline": ["A"]})
    store.transition(project["id"], "outline")
    store.update(project["id"], {"draft": "Draft text"})
    store.transition(project["id"], "draft")
    store.update(project["id"], {"sources": [{"locator": "https://example.org"}]})
    with pytest.raises(WorkbenchError, match="locator and excerpt"):
        store.transition(project["id"], "fact_check")
