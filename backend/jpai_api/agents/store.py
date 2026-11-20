"""Persistent SQLite registry, task queue, approvals and agent scorecards."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from jpai_api.agents.professional_catalog import AGENT_BLUEPRINTS


class AgentStore:
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
            CREATE TABLE IF NOT EXISTS agents (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, domain TEXT NOT NULL,
              description TEXT NOT NULL, roles_json TEXT NOT NULL, capabilities_json TEXT NOT NULL,
              risk_level TEXT NOT NULL DEFAULT 'low', status TEXT NOT NULL DEFAULT 'active',
              instructions TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS agent_tasks (
              id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, prompt TEXT NOT NULL,
              agent_id TEXT NOT NULL, priority TEXT NOT NULL DEFAULT 'normal',
              status TEXT NOT NULL DEFAULT 'queued', requires_approval INTEGER NOT NULL DEFAULT 0,
              approval_status TEXT NOT NULL DEFAULT 'not_required', result TEXT, error_code TEXT,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(agent_id) REFERENCES agents(id));
            CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks(status, priority, created_at);
            CREATE TABLE IF NOT EXISTS agent_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER, agent_id TEXT,
              event_type TEXT NOT NULL, detail_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS agent_metrics (
              agent_id TEXT PRIMARY KEY, assigned INTEGER NOT NULL DEFAULT 0,
              completed INTEGER NOT NULL DEFAULT 0, failed INTEGER NOT NULL DEFAULT 0,
              total_latency_ms REAL NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(agent_id) REFERENCES agents(id));
            """)
            for agent in AGENT_BLUEPRINTS:
                db.execute(
                    """INSERT OR IGNORE INTO agents
                    (id,name,domain,description,roles_json,capabilities_json,risk_level)
                    VALUES(?,?,?,?,?,?,?)""",
                    (agent["id"], agent["name"], agent["domain"], agent["description"],
                     json.dumps(agent["roles"]), json.dumps(agent["capabilities"]), agent["risk_level"]),
                )
                db.execute("INSERT OR IGNORE INTO agent_metrics(agent_id) VALUES(?)", (agent["id"],))

    @staticmethod
    def _agent(row):
        item = dict(row)
        item["roles"] = json.loads(item.pop("roles_json"))
        item["capabilities"] = json.loads(item.pop("capabilities_json"))
        return item

    @staticmethod
    def _task(row):
        return dict(row) if row else None

    def list_agents(self, domain=None, status=None):
        query = "SELECT * FROM agents WHERE 1=1"
        args = []
        if domain:
            query += " AND domain=?"
            args.append(domain)
        if status:
            query += " AND status=?"
            args.append(status)
        query += " ORDER BY domain,name"
        with self._connect() as db:
            return [self._agent(row) for row in db.execute(query, args).fetchall()]

    def get_agent(self, agent_id):
        with self._connect() as db:
            row = db.execute("SELECT * FROM agents WHERE id=?", (agent_id,)).fetchone()
            return self._agent(row) if row else None

    def create_agent(self, agent):
        with self._connect() as db:
            db.execute(
                """INSERT INTO agents(id,name,domain,description,roles_json,capabilities_json,risk_level,instructions)
                VALUES(?,?,?,?,?,?,?,?)""",
                (agent["id"], agent["name"], agent["domain"], agent["description"],
                 json.dumps(agent["roles"]), json.dumps(agent["capabilities"]),
                 agent["risk_level"], agent["instructions"]),
            )
            db.execute("INSERT INTO agent_metrics(agent_id) VALUES(?)", (agent["id"],))
        return self.get_agent(agent["id"])

    def update_agent_status(self, agent_id, status):
        with self._connect() as db:
            cur = db.execute(
                "UPDATE agents SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (status, agent_id),
            )
            return cur.rowcount > 0

    def create_task(self, title, prompt, agent_id, priority, requires_approval):
        with self._connect() as db:
            cur = db.execute(
                """INSERT INTO agent_tasks(title,prompt,agent_id,priority,requires_approval,approval_status)
                VALUES(?,?,?,?,?,?)""",
                (title, prompt, agent_id, priority, int(requires_approval),
                 "pending" if requires_approval else "not_required"),
            )
            task_id = cur.lastrowid
            db.execute("UPDATE agent_metrics SET assigned=assigned+1,updated_at=CURRENT_TIMESTAMP WHERE agent_id=?",
                       (agent_id,))
            db.execute("INSERT INTO agent_events(task_id,agent_id,event_type) VALUES(?,?,?)",
                       (task_id, agent_id, "task.created"))
            return self.get_task(task_id)

    def get_task(self, task_id):
        with self._connect() as db:
            return self._task(db.execute("SELECT * FROM agent_tasks WHERE id=?", (task_id,)).fetchone())

    def list_tasks(self, status=None, limit=50):
        with self._connect() as db:
            if status:
                rows = db.execute("SELECT * FROM agent_tasks WHERE status=? ORDER BY id DESC LIMIT ?",
                                  (status, limit)).fetchall()
            else:
                rows = db.execute("SELECT * FROM agent_tasks ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [self._task(row) for row in rows]

    def set_task_status(self, task_id, status, result=None, error_code=None, approval_status=None):
        with self._connect() as db:
            fields = ["status=?", "updated_at=CURRENT_TIMESTAMP"]
            values = [status]
            if result is not None:
                fields.append("result=?")
                values.append(result)
            if error_code is not None:
                fields.append("error_code=?")
                values.append(error_code)
            if approval_status is not None:
                fields.append("approval_status=?")
                values.append(approval_status)
            values.append(task_id)
            cur = db.execute(f"UPDATE agent_tasks SET {','.join(fields)} WHERE id=?", values)
            return cur.rowcount > 0

    def event(self, task_id, agent_id, event_type, detail=None):
        with self._connect() as db:
            db.execute(
                "INSERT INTO agent_events(task_id,agent_id,event_type,detail_json) VALUES(?,?,?,?)",
                (task_id, agent_id, event_type, json.dumps(detail or {})),
            )

    def record_result(self, agent_id, success, latency_ms):
        with self._connect() as db:
            column = "completed" if success else "failed"
            db.execute(
                f"UPDATE agent_metrics SET {column}={column}+1,total_latency_ms=total_latency_ms+?,updated_at=CURRENT_TIMESTAMP WHERE agent_id=?",
                (latency_ms, agent_id),
            )

    def scorecards(self):
        with self._connect() as db:
            rows = db.execute("""
              SELECT a.id,a.name,a.domain,a.status,m.assigned,m.completed,m.failed,m.total_latency_ms
              FROM agents a JOIN agent_metrics m ON m.agent_id=a.id ORDER BY a.domain,a.name
            """).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            finished = item["completed"] + item["failed"]
            item["success_rate"] = round(item["completed"] / finished, 4) if finished else None
            item["average_latency_ms"] = round(item["total_latency_ms"] / finished, 2) if finished else None
            result.append(item)
        return result

    def events(self, limit=100):
        with self._connect() as db:
            rows = db.execute("SELECT * FROM agent_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(row), "detail": json.loads(row["detail_json"])} for row in rows]
