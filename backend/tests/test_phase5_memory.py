from fastapi.testclient import TestClient
from jpai_api.intelligence.persistence import IntelligenceStore
from jpai_api.main import app
from jpai_api.routes import memory as memory_routes
client=TestClient(app)
def test_typed_weighted_memory_and_archive(tmp_path):
 s=IntelligenceStore(str(tmp_path/"m.db"));important=s.create_memory("project","JPAI architecture","Knowledge graph episodic retrieval",["architecture"],"test","procedural",0.95)
 s.create_memory("project","Old note","Knowledge graph reference",[],"test","working",0.1)
 found=s.search_memories("knowledge graph");assert found[0]["id"]==important["id"] and found[0]["memory_type"]=="procedural"
 assert s.archive_memory(important["id"]);assert all(x["id"]!=important["id"] for x in s.search_memories("knowledge graph"))
def test_graph_entities_and_relations(tmp_path):
 s=IntelligenceStore(str(tmp_path/"g.db"));x=s.upsert_entity("JPAI","platform");y=s.upsert_entity("Memory Engine","component")
 rel=s.create_relation(x["id"],y["id"],"contains",0.97);graph=s.knowledge_graph()
 assert rel["source_name"]=="JPAI" and len(graph["entities"])==2 and len(graph["relations"])==1
def test_memory_api_types_and_archive(monkeypatch,tmp_path):
 monkeypatch.setattr(memory_routes,"get_store",lambda:IntelligenceStore(str(tmp_path/"api.db")))
 r=client.post("/api/v1/memory",json={"title":"Runbook","content":"Restart local model safely","memory_type":"procedural","importance":0.9})
 assert r.status_code==200;mid=r.json()["id"]
 assert client.get("/api/v1/memory?memory_type=procedural").json()["count"]==1
 assert client.delete(f"/api/v1/memory/{mid}").json()["status"]=="archived"
 assert client.get("/api/v1/memory").json()["count"]==0
 assert client.get("/api/v1/memory/graph").status_code==200
def test_additive_migration_preserves_legacy_rows(tmp_path):
 import sqlite3
 path=str(tmp_path/"legacy.db");db=sqlite3.connect(path)
 db.execute("CREATE TABLE memories (id INTEGER PRIMARY KEY AUTOINCREMENT,namespace TEXT NOT NULL DEFAULT 'general',title TEXT NOT NULL,content TEXT NOT NULL,tags_json TEXT NOT NULL DEFAULT '[]',source TEXT NOT NULL DEFAULT 'user',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
 db.execute("INSERT INTO memories(title,content) VALUES('legacy','keep this')");db.commit();db.close()
 item=IntelligenceStore(path).list_memories()[0];assert item["content"]=="keep this" and item["memory_type"]=="semantic"
