# Phase 5 — Memory & Knowledge Infrastructure

## Delivered capabilities
- Four typed memory classes: working, episodic, semantic and procedural.
- Additive SQLite migrations preserve existing local memory records.
- Importance-aware local retrieval weights title, content, tags and namespace.
- Memory update and archive operations; archived records are excluded from default retrieval.
- Local knowledge graph with typed entities and confidence-scored, provenance-capable relations.
- Specialist task inference retrieves up to four relevant local memories as reference context requiring verification.
- Persistence remains SQLite/WAL; no hosted database or external vector service is introduced.

## API
- GET /api/v1/memory?namespace=general&memory_type=semantic&limit=50
- POST /api/v1/memory — create typed memory with importance and metadata.
- POST /api/v1/memory/search — weighted local keyword retrieval.
- PATCH /api/v1/memory/{memory_id} — update title, content, importance or tags.
- DELETE /api/v1/memory/{memory_id} — soft archive, not destructive deletion.
- POST /api/v1/memory/entities — create or update a graph entity.
- POST /api/v1/memory/relations — create a confidence-scored relation.
- GET /api/v1/memory/graph?limit=200 — retrieve graph nodes and edges.

## Governance and limitations
Memory remains local. Retrieval is weighted lexical matching, not embedding-based semantic retrieval. Archiving is a soft archive, not secure erasure. Retrieved memory is untrusted reference data and cannot override system policy, safety rules or human approvals. Graph population is API-driven; automatic extraction and contradiction resolution are future work. Back up data/jpai.sqlite3 before production upgrades.

Regression tests cover migration, retrieval, archive, graph relations and API endpoints. Tests are committed but were not executed in this hosted editing session.
