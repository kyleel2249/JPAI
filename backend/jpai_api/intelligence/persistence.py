"""Durable local SQLite storage for JPAI memory and model-routing telemetry."""
from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

class IntelligenceStore:
    def __init__(self, database_path: str | None = None) -> None:
        self.path = Path(database_path or os.getenv("JPAI_DATABASE_PATH", "data/jpai.sqlite3")).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _initialise(self):
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
              id INTEGER PRIMARY KEY AUTOINCREMENT, namespace TEXT NOT NULL DEFAULT 'general',
              title TEXT NOT NULL, content TEXT NOT NULL, tags_json TEXT NOT NULL DEFAULT '[]',
              source TEXT NOT NULL DEFAULT 'user', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE INDEX IF NOT EXISTS idx_memories_namespace_created ON memories(namespace, created_at DESC);
            CREATE TABLE IF NOT EXISTS model_metrics (
              model_id TEXT PRIMARY KEY, provider TEXT NOT NULL, samples INTEGER NOT NULL DEFAULT 0,
              successes INTEGER NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0,
              avg_latency_ms REAL, quality_score REAL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS audit_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, subject TEXT NOT NULL,
              detail_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            """)

    @staticmethod
    def _memory(row):
        return {**dict(row), "tags": json.loads(row["tags_json"])}

    def create_memory(self, namespace, title, content, tags, source):
        with self._connect() as db:
            cur = db.execute("INSERT INTO memories(namespace,title,content,tags_json,source) VALUES(?,?,?,?,?)",
                             (namespace,title,content,json.dumps(tags),source))
            row = db.execute("SELECT * FROM memories WHERE id=?", (cur.lastrowid,)).fetchone()
            db.execute("INSERT INTO audit_events(event_type,subject,detail_json) VALUES(?,?,?)",
                       ("memory.created",str(cur.lastrowid),json.dumps({"namespace":namespace})))
            return self._memory(row)

    def list_memories(self, namespace=None, limit=50):
        with self._connect() as db:
            if namespace:
                rows=db.execute("SELECT * FROM memories WHERE namespace=? ORDER BY created_at DESC LIMIT ?",
                                (namespace,limit)).fetchall()
            else:
                rows=db.execute("SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall()
            return [self._memory(row) for row in rows]

    def search_memories(self, query, namespace=None, limit=10):
        terms=[term.lower() for term in query.split() if len(term)>1]
        if not terms: return []
        with self._connect() as db:
            rows=db.execute("SELECT * FROM memories"+(" WHERE namespace=?" if namespace else ""),
                            (namespace,) if namespace else ()).fetchall()
        found=[]
        for row in rows:
            text=" ".join([row["title"],row["content"],row["namespace"],row["tags_json"]]).lower()
            score=sum(text.count(term) for term in terms)
            if score:
                item=self._memory(row); item["relevance"]=round(score/len(terms),3); found.append(item)
        return sorted(found,key=lambda x:(x["relevance"],x["created_at"]),reverse=True)[:limit]

    def record_model_result(self, model_id, provider, latency_ms, success):
        with self._connect() as db:
            old=db.execute("SELECT * FROM model_metrics WHERE model_id=?",(model_id,)).fetchone()
            if old:
                n=old["samples"]+1
                avg=((old["avg_latency_ms"] or latency_ms)*old["samples"]+latency_ms)/n
                db.execute("""UPDATE model_metrics SET provider=?,samples=?,successes=?,failures=?,
                    avg_latency_ms=?,updated_at=CURRENT_TIMESTAMP WHERE model_id=?""",
                    (provider,n,old["successes"]+int(success),old["failures"]+int(not success),avg,model_id))
            else:
                db.execute("""INSERT INTO model_metrics(model_id,provider,samples,successes,failures,avg_latency_ms)
                    VALUES(?,?,?,?,?,?)""",(model_id,provider,1,int(success),int(not success),latency_ms))

    def get_model_metrics(self):
        with self._connect() as db:
            return {r["model_id"]:dict(r) for r in db.execute("SELECT * FROM model_metrics").fetchall()}
