from jpai_api.intelligence.persistence import IntelligenceStore

def test_memory_persists_and_searches(tmp_path):
    path=str(tmp_path/"jpai-test.sqlite3")
    first=IntelligenceStore(path)
    item=first.create_memory("project","JPAI roadmap","Build persistent intelligence memory",
                             ["roadmap","memory"],"test")
    second=IntelligenceStore(path)
    assert second.list_memories("project")[0]["id"]==item["id"]
    assert second.search_memories("persistent intelligence")[0]["id"]==item["id"]

def test_model_metrics_accumulate(tmp_path):
    store=IntelligenceStore(str(tmp_path/"metrics.sqlite3"))
    store.record_model_result("local-model","ollama",100,True)
    store.record_model_result("local-model","ollama",300,False)
    metric=store.get_model_metrics()["local-model"]
    assert metric["samples"]==2 and metric["successes"]==1 and metric["failures"]==1
    assert metric["avg_latency_ms"]==200
