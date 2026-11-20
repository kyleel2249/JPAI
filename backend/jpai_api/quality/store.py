"""Persistent, evidence-gated quality cycles and root-cause issue resolution."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path


CYCLE_STAGES = ("build", "reassess", "improve", "test", "verify")
ISSUE_STAGES = ("reported", "assessed", "cause_identified", "fix_implemented", "tested", "verified")


class QualityStore:
    def __init__(self, database_path: str | None = None):
        self.path = Path(database_path or os.getenv("JPAI_DATABASE_PATH", "data/jpai.sqlite3")).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _initialise(self):
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS quality_cycles (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL, scope TEXT NOT NULL, baseline TEXT NOT NULL,
              current_stage TEXT NOT NULL DEFAULT 'build',
              status TEXT NOT NULL DEFAULT 'in_progress',
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS quality_issues (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL, description TEXT NOT NULL, component TEXT NOT NULL,
              severity TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'reported',
              assessment TEXT, root_cause TEXT, corrective_action TEXT,
              test_result TEXT, verification_result TEXT,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS quality_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              record_type TEXT NOT NULL, record_id INTEGER NOT NULL,
              stage TEXT NOT NULL, evidence TEXT NOT NULL,
              actor TEXT NOT NULL DEFAULT 'local_operator',
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_quality_cycles_status ON quality_cycles(status, id DESC);
            CREATE INDEX IF NOT EXISTS idx_quality_issues_status ON quality_issues(status, severity, id DESC);
            CREATE INDEX IF NOT EXISTS idx_quality_events_record ON quality_events(record_type, record_id, id);
            """)

    @staticmethod
    def _dict(row):
        return dict(row) if row else None

    def create_cycle(self, title, scope, baseline):
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO quality_cycles(title,scope,baseline) VALUES(?,?,?)",
                (title, scope, baseline),
            )
            cycle_id = cur.lastrowid
            db.execute(
                "INSERT INTO quality_events(record_type,record_id,stage,evidence) VALUES('cycle',?,'build',?)",
                (cycle_id, baseline),
            )
            return self._dict(db.execute("SELECT * FROM quality_cycles WHERE id=?", (cycle_id,)).fetchone())

    def advance_cycle(self, cycle_id, stage, evidence):
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM quality_cycles WHERE id=?", (cycle_id,)).fetchone()
            if row is None or row["status"] != "in_progress":
                return None, "cycle_not_active"
            expected_index = CYCLE_STAGES.index(row["current_stage"]) + 1
            if expected_index >= len(CYCLE_STAGES) or CYCLE_STAGES[expected_index] != stage:
                return None, "cycle_stage_out_of_order"
            status = "completed" if stage == "verify" else "in_progress"
            cur = db.execute(
                """UPDATE quality_cycles SET current_stage=?,status=?,updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND current_stage=? AND status='in_progress'""",
                (stage, status, cycle_id, row["current_stage"]),
            )
            if cur.rowcount != 1:
                return None, "cycle_stage_out_of_order"
            db.execute(
                "INSERT INTO quality_events(record_type,record_id,stage,evidence) VALUES('cycle',?,?,?)",
                (cycle_id, stage, evidence),
            )
            return self._dict(db.execute("SELECT * FROM quality_cycles WHERE id=?", (cycle_id,)).fetchone()), None

    def create_issue(self, title, description, component, severity):
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO quality_issues(title,description,component,severity) VALUES(?,?,?,?)",
                (title, description, component, severity),
            )
            issue_id = cur.lastrowid
            db.execute(
                "INSERT INTO quality_events(record_type,record_id,stage,evidence) VALUES('issue',?,'reported',?)",
                (issue_id, description),
            )
            return self._dict(db.execute("SELECT * FROM quality_issues WHERE id=?", (issue_id,)).fetchone())

    def advance_issue(self, issue_id, stage, evidence):
        field_by_stage = {
            "assessed": "assessment",
            "cause_identified": "root_cause",
            "fix_implemented": "corrective_action",
            "tested": "test_result",
            "verified": "verification_result",
        }
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM quality_issues WHERE id=?", (issue_id,)).fetchone()
            if row is None or row["status"] == "verified":
                return None, "issue_not_active"
            expected_index = ISSUE_STAGES.index(row["status"]) + 1
            if expected_index >= len(ISSUE_STAGES) or ISSUE_STAGES[expected_index] != stage:
                return None, "issue_stage_out_of_order"
            field = field_by_stage[stage]
            cur = db.execute(
                f"""UPDATE quality_issues SET {field}=?,status=?,updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND status=?""",
                (evidence, stage, issue_id, row["status"]),
            )
            if cur.rowcount != 1:
                return None, "issue_stage_out_of_order"
            db.execute(
                "INSERT INTO quality_events(record_type,record_id,stage,evidence) VALUES('issue',?,?,?)",
                (issue_id, stage, evidence),
            )
            return self._dict(db.execute("SELECT * FROM quality_issues WHERE id=?", (issue_id,)).fetchone()), None

    def list_cycles(self, limit=50):
        with self._connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT * FROM quality_cycles ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()]

    def list_issues(self, status=None, limit=50):
        with self._connect() as db:
            if status:
                rows = db.execute(
                    "SELECT * FROM quality_issues WHERE status=? ORDER BY id DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = db.execute("SELECT * FROM quality_issues ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def events(self, record_type=None, record_id=None, limit=100):
        query = "SELECT * FROM quality_events WHERE 1=1"
        args = []
        if record_type:
            query += " AND record_type=?"
            args.append(record_type)
        if record_id is not None:
            query += " AND record_id=?"
            args.append(record_id)
        query += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with self._connect() as db:
            return [dict(r) for r in db.execute(query, args).fetchall()]
