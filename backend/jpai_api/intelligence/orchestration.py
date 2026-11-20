"""Durable checkpoints and run ledger for parallel JPAI council orchestration."""
from __future__ import annotations
import json, os, sqlite3, uuid
from pathlib import Path
from typing import Any

class OrchestrationStore:
    """Transactional run ledger sharing JPAI local SQLite database."""
    def __init__(self, database_path: str | None = None) -> None:
        self.path = Path(database_path or os.getenv("JPAI_DATABASE_PATH", "data/jpai.sqlite3")).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS orchestration_runs (
              id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
              prompt TEXT NOT NULL, agent_ids_json TEXT NOT NULL,
              completed_agents INTEGER NOT NULL DEFAULT 0, total_agents INTEGER NOT NULL DEFAULT 0,
              result_json TEXT, error_code TEXT,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE INDEX IF NOT EXISTS idx_orchestration_runs_status ON orchestration_runs(status, updated_at DESC);
            CREATE TABLE IF NOT EXISTS orchestration_checkpoints (
              id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, phase TEXT NOT NULL,
              status TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT "{}",
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(run_id) REFERENCES orchestration_runs(id) ON DELETE CASCADE);
            CREATE INDEX IF NOT EXISTS idx_orchestration_checkpoints_run ON orchestration_checkpoints(run_id, id);
            """)
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=20000")
        return db
    @staticmethod
    def _run(row):
        if row is None: return None
        item = dict(row)
        item["agent_ids"] = json.loads(item.pop("agent_ids_json"))
        item["result"] = json.loads(item.pop("result_json")) if item.get("result_json") else None
        return item
    def create_run(self, prompt: str, agent_ids: list[str]) -> str:
        run_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("INSERT INTO orchestration_runs(id,kind,status,prompt,agent_ids_json,total_agents) VALUES(?,?,?,?,?,?)",
                       (run_id, "parallel_council", "running", prompt, json.dumps(agent_ids), len(agent_ids)))
            db.execute("INSERT INTO orchestration_checkpoints(run_id,phase,status,payload_json) VALUES(?,?,?,?)",
                       (run_id, "initialised", "completed", json.dumps({"agent_ids": agent_ids})))
        return run_id
    def checkpoint(self, run_id: str, phase: str, status: str, payload: dict[str, Any] | None = None):
        with self._connect() as db:
            db.execute("INSERT INTO orchestration_checkpoints(run_id,phase,status,payload_json) VALUES(?,?,?,?)",
                       (run_id, phase, status, json.dumps(payload or {}, default=str)))
            if phase == "specialist_contributions":
                db.execute("UPDATE orchestration_runs SET completed_agents=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                           (int((payload or {}).get("completed_count", 0)), run_id))
    def finish(self, run_id: str, status: str, result: dict[str, Any] | None = None, error_code: str | None = None):
        with self._connect() as db:
            db.execute("UPDATE orchestration_runs SET status=?,result_json=?,error_code=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                       (status, json.dumps(result, default=str) if result is not None else None, error_code, run_id))
    def get_run(self, run_id: str):
        with self._connect() as db:
            row = db.execute("SELECT * FROM orchestration_runs WHERE id=?", (run_id,)).fetchone()
            if row is None: return None
            result = self._run(row)
            result["checkpoints"] = [{**dict(x), "payload": json.loads(x["payload_json"])} for x in db.execute(
                "SELECT * FROM orchestration_checkpoints WHERE run_id=? ORDER BY id", (run_id,)).fetchall()]
            return result
    def list_runs(self, limit: int = 20):
        with self._connect() as db:
            rows = db.execute("SELECT * FROM orchestration_runs ORDER BY created_at DESC LIMIT ?",
                              (max(1, min(limit, 100)),)).fetchall()
            return [self._run(row) for row in rows]