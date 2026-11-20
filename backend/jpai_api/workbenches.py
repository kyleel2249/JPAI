"""Governed engineering and editorial workbenches with durable audit history."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

KINDS = {"engineering", "editorial"}
ENGINEERING_STAGES = ["intake", "requirements", "design", "implementation", "verification", "release_ready"]
EDITORIAL_STAGES = ["brief", "outline", "draft", "fact_check", "editorial_review", "ready_to_publish"]


class WorkbenchError(ValueError):
    """A workbench operation violates its lifecycle or evidence requirements."""


class WorkbenchStore:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("JPAI_DATABASE_PATH", "data/jpai.sqlite3")).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS workbench_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('engineering','editorial')),
                title TEXT NOT NULL,
                brief TEXT NOT NULL,
                stage TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_workbench_kind_updated
                ON workbench_projects(kind, updated_at DESC);
            CREATE TABLE IF NOT EXISTS workbench_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                event TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES workbench_projects(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_workbench_events_project
                ON workbench_events(project_id, id);
            """)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _public(row):
        if row is None:
            return None
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        return item

    def create(self, kind, title, brief):
        if kind not in KINDS:
            raise WorkbenchError("Unsupported workbench kind")
        now = datetime.now(UTC).isoformat()
        stage = "intake" if kind == "engineering" else "brief"
        with self._connect() as db:
            cursor = db.execute(
                """INSERT INTO workbench_projects
                   (kind,title,brief,stage,payload,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (kind, title.strip(), brief.strip(), stage, "{}", now, now),
            )
            project_id = cursor.lastrowid
            self._event(db, project_id, kind, "created", {"stage": stage})
            row = db.execute("SELECT * FROM workbench_projects WHERE id=?", (project_id,)).fetchone()
        return self._public(row)

    @staticmethod
    def _event(db, project_id, kind, event, details):
        db.execute(
            "INSERT INTO workbench_events(project_id,kind,event,details,created_at) VALUES(?,?,?,?,?)",
            (project_id, kind, event, json.dumps(details, ensure_ascii=False),
             datetime.now(UTC).isoformat()),
        )

    def update(self, project_id, fields):
        allowed = {"requirements", "architecture_decisions", "deliverables", "test_evidence",
                   "risk_review", "outline", "draft", "sources", "fact_check_status",
                   "editorial_notes", "publication_approved", "tags", "owner"}
        unknown = set(fields) - allowed
        if unknown:
            raise WorkbenchError("Unsupported fields: " + ", ".join(sorted(unknown)))
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM workbench_projects WHERE id=?", (project_id,)).fetchone()
            if not row:
                raise WorkbenchError("Workbench project was not found")
            payload = json.loads(row["payload"])
            payload.update(fields)
            now = datetime.now(UTC).isoformat()
            db.execute("UPDATE workbench_projects SET payload=?,updated_at=? WHERE id=?",
                       (json.dumps(payload, ensure_ascii=False), now, project_id))
            self._event(db, project_id, row["kind"], "updated", {"fields": sorted(fields)})
            updated = db.execute("SELECT * FROM workbench_projects WHERE id=?", (project_id,)).fetchone()
        return self._public(updated)

    @staticmethod
    def _gate(kind, next_stage, payload):
        if kind == "engineering":
            requirements = {
                "requirements": ("requirements", "Requirements must be recorded before design."),
                "design": ("architecture_decisions", "Architecture/design decisions are required."),
                "implementation": ("deliverables", "Implementation deliverables are required."),
                "verification": ("test_evidence", "Test evidence is required before verification."),
                "release_ready": ("risk_review", "A risk review is required before release readiness."),
            }
            if next_stage in requirements:
                key, message = requirements[next_stage]
                value = payload.get(key)
                if key == "risk_review":
                    if not isinstance(value, dict) or value.get("status") not in {"accepted", "accepted_with_conditions"}:
                        raise WorkbenchError("Risk review must be accepted or accepted_with_conditions.")
                elif not isinstance(value, list) or not value:
                    raise WorkbenchError(message)
                if key == "test_evidence" and any(
                    not isinstance(item, dict) or not item.get("result") or not item.get("artifact")
                    for item in value
                ):
                    raise WorkbenchError("Each test evidence item needs a result and an artifact reference.")
        else:
            requirements = {
                "outline": ("outline", "An outline is required before drafting."),
                "draft": ("draft", "A draft is required before fact-checking."),
                "fact_check": ("sources", "Source records are required before fact-checking."),
                "editorial_review": ("editorial_notes", "Editorial review notes are required."),
                "ready_to_publish": ("publication_approved", "Explicit publication approval is required."),
            }
            if next_stage in requirements:
                key, message = requirements[next_stage]
                value = payload.get(key)
                if key == "publication_approved":
                    if value is not True:
                        raise WorkbenchError(message)
                    if payload.get("fact_check_status") not in {"verified", "qualified"}:
                        raise WorkbenchError("Fact-check status must be verified or qualified.")
                elif key == "sources":
                    if not isinstance(value, list) or not value:
                        raise WorkbenchError(message)
                    if any(not isinstance(item, dict) or not item.get("locator") or not item.get("excerpt")
                           for item in value):
                        raise WorkbenchError("Each source record needs a locator and excerpt.")
                elif not value:
                    raise WorkbenchError(message)

    def transition(self, project_id, target):
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM workbench_projects WHERE id=?", (project_id,)).fetchone()
            if not row:
                raise WorkbenchError("Workbench project was not found")
            stages = ENGINEERING_STAGES if row["kind"] == "engineering" else EDITORIAL_STAGES
            current_index = stages.index(row["stage"])
            if current_index + 1 >= len(stages) or stages[current_index + 1] != target:
                raise WorkbenchError("Only the next sequential lifecycle stage is permitted.")
            payload = json.loads(row["payload"])
            self._gate(row["kind"], target, payload)
            now = datetime.now(UTC).isoformat()
            db.execute("UPDATE workbench_projects SET stage=?,updated_at=? WHERE id=?",
                       (target, now, project_id))
            self._event(db, project_id, row["kind"], "stage_transition",
                        {"from": row["stage"], "to": target})
            updated = db.execute("SELECT * FROM workbench_projects WHERE id=?", (project_id,)).fetchone()
        return self._public(updated)

    def get(self, project_id):
        with self._connect() as db:
            return self._public(db.execute(
                "SELECT * FROM workbench_projects WHERE id=?", (project_id,)
            ).fetchone())

    def list(self, kind=None, limit=50):
        with self._connect() as db:
            if kind:
                rows = db.execute(
                    "SELECT * FROM workbench_projects WHERE kind=? ORDER BY updated_at DESC LIMIT ?",
                    (kind, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM workbench_projects ORDER BY updated_at DESC LIMIT ?", (limit,)
                ).fetchall()
            return [self._public(row) for row in rows]

    def events(self, project_id):
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM workbench_projects WHERE id=?", (project_id,)).fetchone():
                return None
            rows = db.execute(
                "SELECT * FROM workbench_events WHERE project_id=? ORDER BY id", (project_id,)
            ).fetchall()
            items = [dict(row) for row in rows]
            for item in items:
                item["details"] = json.loads(item["details"])
            return items
