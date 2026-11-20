"""Durable local SQLite storage for JPAI memory and model-routing telemetry."""
from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path

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
            columns = {row[1] for row in db.execute("PRAGMA table_info(memories)").fetchall()}
            migrations = {
                "memory_type": "ALTER TABLE memories ADD COLUMN memory_type TEXT NOT NULL DEFAULT 'semantic'",
                "importance": "ALTER TABLE memories ADD COLUMN importance REAL NOT NULL DEFAULT 0.5",
                "metadata_json": "ALTER TABLE memories ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'",
                "archived": "ALTER TABLE memories ADD COLUMN archived INTEGER NOT NULL DEFAULT 0",
            }
            for name, statement in migrations.items():
                if name not in columns: db.execute(statement)
            db.executescript("""
            CREATE INDEX IF NOT EXISTS idx_memories_type_importance ON memories(memory_type, importance DESC);
            CREATE TABLE IF NOT EXISTS knowledge_entities (
              id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, entity_type TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '', metadata_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(name, entity_type));
            CREATE TABLE IF NOT EXISTS knowledge_relations (
              id INTEGER PRIMARY KEY AUTOINCREMENT, source_entity_id INTEGER NOT NULL,
              target_entity_id INTEGER NOT NULL, relation_type TEXT NOT NULL, confidence REAL NOT NULL DEFAULT 0.8,
              source_memory_id INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(source_entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
              FOREIGN KEY(target_entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
              FOREIGN KEY(source_memory_id) REFERENCES memories(id) ON DELETE SET NULL,
              UNIQUE(source_entity_id,target_entity_id,relation_type,source_memory_id));
            CREATE INDEX IF NOT EXISTS idx_knowledge_relations_source ON knowledge_relations(source_entity_id);
            CREATE INDEX IF NOT EXISTS idx_knowledge_relations_target ON knowledge_relations(target_entity_id);
            """)

    @staticmethod
    def _memory(row):
        item = dict(row)
        item["tags"] = json.loads(item.pop("tags_json"))
        item["metadata"] = json.loads(item.pop("metadata_json", "{}"))
        item["archived"] = bool(item.get("archived", 0))
        return item

    def create_memory(self, namespace, title, content, tags, source, memory_type="semantic", importance=0.5, metadata=None):
        with self._connect() as db:
            cur=db.execute("INSERT INTO memories(namespace,title,content,tags_json,source,memory_type,importance,metadata_json) VALUES(?,?,?,?,?,?,?,?)",
                (namespace,title,content,json.dumps(tags),source,memory_type,max(0.0,min(1.0,float(importance))),json.dumps(metadata or {})))
            row=db.execute("SELECT * FROM memories WHERE id=?",(cur.lastrowid,)).fetchone()
            db.execute("INSERT INTO audit_events(event_type,subject,detail_json) VALUES(?,?,?)",
                ("memory.created",str(cur.lastrowid),json.dumps({"namespace":namespace,"memory_type":memory_type})))
            return self._memory(row)

    def list_memories(self, namespace=None, limit=50, memory_type=None, include_archived=False):
        clauses=[]; args=[]
        if namespace: clauses.append("namespace=?"); args.append(namespace)
        if memory_type: clauses.append("memory_type=?"); args.append(memory_type)
        if not include_archived: clauses.append("archived=0")
        query="SELECT * FROM memories"+(" WHERE "+" AND ".join(clauses) if clauses else "")+" ORDER BY importance DESC,created_at DESC LIMIT ?"
        args.append(limit)
        with self._connect() as db:return [self._memory(r) for r in db.execute(query,args).fetchall()]

    def search_memories(self, query, namespace=None, limit=10, memory_type=None):
        terms=[t.lower() for t in query.split() if len(t)>1]
        if not terms:return []
        clauses=["archived=0"];args=[]
        if namespace:clauses.append("namespace=?");args.append(namespace)
        if memory_type:clauses.append("memory_type=?");args.append(memory_type)
        with self._connect() as db:rows=db.execute("SELECT * FROM memories WHERE "+" AND ".join(clauses),args).fetchall()
        found=[]
        for row in rows:
            title,content=row["title"].lower(),row["content"].lower();tags=row["tags_json"].lower();ns=row["namespace"].lower()
            score=sum(title.count(t)*3+content.count(t)+tags.count(t)*2+ns.count(t) for t in terms)
            if score:
                item=self._memory(row);item["relevance"]=round((score/len(terms))*(0.75+item["importance"]*0.5),3);found.append(item)
        return sorted(found,key=lambda x:(x["relevance"],x["created_at"]),reverse=True)[:limit]

    def archive_memory(self,memory_id):
        with self._connect() as db:
            cur=db.execute("UPDATE memories SET archived=1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND archived=0",(memory_id,))
            if cur.rowcount:db.execute("INSERT INTO audit_events(event_type,subject,detail_json) VALUES(?,?,?)",("memory.archived",str(memory_id),"{}"))
            return cur.rowcount==1

    def update_memory(self,memory_id,title=None,content=None,importance=None,tags=None):
        fields=[];values=[]
        for key,value in (("title",title),("content",content),("importance",importance),("tags_json",json.dumps(tags) if tags is not None else None)):
            if value is not None:fields.append(f"{key}=?");values.append(max(0.0,min(1.0,float(value))) if key=="importance" else value)
        if not fields:return None
        fields.append("updated_at=CURRENT_TIMESTAMP");values.append(memory_id)
        with self._connect() as db:
            db.execute(f"UPDATE memories SET {','.join(fields)} WHERE id=? AND archived=0",values)
            row=db.execute("SELECT * FROM memories WHERE id=? AND archived=0",(memory_id,)).fetchone()
            return self._memory(row) if row else None

    def upsert_entity(self,name,entity_type,description="",metadata=None):
        with self._connect() as db:
            db.execute("""INSERT INTO knowledge_entities(name,entity_type,description,metadata_json) VALUES(?,?,?,?)
                ON CONFLICT(name,entity_type) DO UPDATE SET description=CASE WHEN excluded.description='' THEN knowledge_entities.description ELSE excluded.description END,
                metadata_json=excluded.metadata_json,updated_at=CURRENT_TIMESTAMP""",(name.strip(),entity_type.strip(),description.strip(),json.dumps(metadata or {})))
            row=db.execute("SELECT * FROM knowledge_entities WHERE name=? AND entity_type=?",(name.strip(),entity_type.strip())).fetchone()
            return {**dict(row),"metadata":json.loads(row["metadata_json"])}

    def create_relation(self,source_id,target_id,relation_type,confidence=0.8,source_memory_id=None):
        with self._connect() as db:
            for entity_id in (source_id,target_id):
                if not db.execute("SELECT 1 FROM knowledge_entities WHERE id=?",(entity_id,)).fetchone():return None
            db.execute("INSERT OR IGNORE INTO knowledge_relations(source_entity_id,target_entity_id,relation_type,confidence,source_memory_id) VALUES(?,?,?,?,?)",
                (source_id,target_id,relation_type.strip(),max(0.0,min(1.0,float(confidence))),source_memory_id))
            row=db.execute("""SELECT r.*,s.name AS source_name,t.name AS target_name FROM knowledge_relations r
                JOIN knowledge_entities s ON s.id=r.source_entity_id JOIN knowledge_entities t ON t.id=r.target_entity_id
                WHERE r.source_entity_id=? AND r.target_entity_id=? AND r.relation_type=? AND r.source_memory_id IS ? ORDER BY r.id DESC LIMIT 1""",
                (source_id,target_id,relation_type.strip(),source_memory_id)).fetchone()
            return dict(row) if row else None

    def knowledge_graph(self,limit=200):
        with self._connect() as db:
            entities=db.execute("SELECT * FROM knowledge_entities ORDER BY updated_at DESC LIMIT ?",(limit,)).fetchall()
            relations=db.execute("""SELECT r.*,s.name AS source_name,t.name AS target_name FROM knowledge_relations r
                JOIN knowledge_entities s ON s.id=r.source_entity_id JOIN knowledge_entities t ON t.id=r.target_entity_id
                ORDER BY r.created_at DESC LIMIT ?""",(limit,)).fetchall()
        return {"entities":[{**dict(r),"metadata":json.loads(r["metadata_json"])} for r in entities],"relations":[dict(r) for r in relations]}

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
