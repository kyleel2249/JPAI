"""Unified provenance-aware evidence index for web pages and uploaded documents."""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

VALID_SOURCE_TYPES = {"web", "document"}
VALID_STANCES = {"supports", "contradicts", "context"}


class EvidenceError(ValueError):
    """Evidence operation rejected because its source or citation is invalid."""


class EvidenceStore:
    """Unifies existing local source tables without duplicating source content."""

    def __init__(self, path=None):
        self.path = Path(path or os.getenv("JPAI_DATABASE_PATH", "data/jpai.sqlite3")).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Bootstrap the two source catalogues before any evidence search can run.
        from jpai_api.research.crawler import CrawlerStore
        from jpai_api.research.documents import DocumentStore

        CrawlerStore(str(self.path))
        DocumentStore(str(self.path))
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS evidence_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                statement TEXT NOT NULL,
                context TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                source_type TEXT NOT NULL CHECK(source_type IN ('web','document')),
                source_id INTEGER NOT NULL,
                stance TEXT NOT NULL CHECK(stance IN ('supports','contradicts','context')),
                excerpt TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(claim_id,source_type,source_id,stance),
                FOREIGN KEY(claim_id) REFERENCES evidence_claims(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_evidence_links_claim
                ON evidence_links(claim_id,created_at DESC);
            """)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _source(db, source_type, source_id):
        if source_type == "web":
            row = db.execute(
                """SELECT id,url AS locator,domain,title,description,content,
                   content_hash AS source_hash,fetched_at AS observed_at
                   FROM crawled_pages WHERE id=?""", (source_id,)
            ).fetchone()
            if not row:
                return None
            item = dict(row)
            item.update(source_type="web", trust="unverified_external_source",
                        origin_key="web:" + item["domain"])
            return item
        if source_type == "document":
            row = db.execute(
                """SELECT id,filename AS locator,file_type,content,content_hash AS source_hash,
                   uploaded_at AS observed_at FROM research_documents WHERE id=?""",
                (source_id,),
            ).fetchone()
            if not row:
                return None
            item = dict(row)
            item.update(title=item["locator"], description="", domain="",
                        source_type="document", trust="unverified_user_supplied_document",
                        origin_key="document:" + item["source_hash"])
            return item
        return None

    @staticmethod
    def _snippet(content, terms, limit=420):
        lower = content.lower()
        positions = [lower.find(term) for term in terms if lower.find(term) >= 0]
        start = max(0, min(positions) - 120) if positions else 0
        excerpt = content[start:start + limit].strip()
        return ("…" if start else "") + excerpt + ("…" if start + limit < len(content) else "")

    def search_sources(self, query="", limit=30):
        terms = [term.lower() for term in re.findall(r"[\w-]{2,}", query)][:12]
        with self._connect() as db:
            rows = []
            for source_type, sql in (
                ("web", """SELECT id,url AS locator,domain,title,description,content,
                    content_hash AS source_hash,fetched_at AS observed_at
                    FROM crawled_pages ORDER BY fetched_at DESC LIMIT 1000"""),
                ("document", """SELECT id,filename AS locator,'' AS domain,filename AS title,
                    '' AS description,content,content_hash AS source_hash,
                    uploaded_at AS observed_at FROM research_documents
                    ORDER BY uploaded_at DESC LIMIT 1000"""),
            ):
                for row in db.execute(sql).fetchall():
                    item = dict(row)
                    haystack = " ".join((item["title"], item["description"], item["content"])).lower()
                    score = sum(haystack.count(term) + item["title"].lower().count(term) * 3
                                for term in terms)
                    if not terms or score:
                        item.update(
                            source_type=source_type,
                            trust=("unverified_external_source" if source_type == "web"
                                   else "unverified_user_supplied_document"),
                            relevance=score,
                            excerpt=self._snippet(item["content"], terms),
                        )
                        item.pop("content")
                        rows.append(item)
        return sorted(rows, key=lambda x: (x["relevance"], x["observed_at"]), reverse=True)[:limit]

    def create_claim(self, statement, context=""):
        now = datetime.now(UTC).isoformat()
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO evidence_claims(statement,context,created_at,updated_at) VALUES(?,?,?,?)",
                (statement.strip(), context.strip(), now, now),
            )
            claim_id = cursor.lastrowid
        return self.get_claim(claim_id)

    def add_evidence(self, claim_id, source_type, source_id, stance, excerpt):
        if source_type not in VALID_SOURCE_TYPES or stance not in VALID_STANCES:
            raise EvidenceError("Unsupported source type or evidence stance")
        quote = excerpt.strip()
        if len(quote) < 20 or len(quote) > 1200:
            raise EvidenceError("Evidence excerpt must contain 20 to 1,200 characters")
        now = datetime.now(UTC).isoformat()
        with self._connect() as db:
            claim = db.execute("SELECT id FROM evidence_claims WHERE id=?", (claim_id,)).fetchone()
            if not claim:
                raise EvidenceError("Research claim was not found")
            source = self._source(db, source_type, source_id)
            if not source:
                raise EvidenceError("Evidence source was not found")
            if quote.casefold() not in source["content"].casefold():
                raise EvidenceError("Evidence excerpt must exactly match text in the selected source")
            db.execute(
                """INSERT OR IGNORE INTO evidence_links
                   (claim_id,source_type,source_id,stance,excerpt,source_hash,created_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (claim_id, source_type, source_id, stance, quote, source["source_hash"], now),
            )
            db.execute("UPDATE evidence_claims SET updated_at=? WHERE id=?", (now, claim_id))
        return self.get_claim(claim_id)

    def _claim_public(self, db, claim):
        item = dict(claim)
        links = db.execute(
            "SELECT * FROM evidence_links WHERE claim_id=? ORDER BY created_at,id",
            (item["id"],),
        ).fetchall()
        evidence = []
        origins = set()
        for link in links:
            source = self._source(db, link["source_type"], link["source_id"])
            record = dict(link)
            if source:
                origins.add(source["origin_key"])
                record.update(
                    source_title=source["title"], source_locator=source["locator"],
                    source_domain=source["domain"], source_trust=source["trust"],
                    source_observed_at=source["observed_at"],
                )
            evidence.append(record)
        support = sum(x["stance"] == "supports" for x in evidence)
        contradict = sum(x["stance"] == "contradicts" for x in evidence)
        context = sum(x["stance"] == "context" for x in evidence)
        item.update(
            evidence=evidence, support_count=support, contradiction_count=contradict,
            context_count=context, source_origins=len(origins),
            evidence_balance=(
                "contested" if support and contradict else
                "supported_by_multiple_origins" if support and len(origins) > 1 else
                "single_supporting_source" if support else
                "contradictory_evidence_only" if contradict else "no_linked_evidence"
            ),
            verification_status="not_verified",
        )
        return item

    def get_claim(self, claim_id):
        with self._connect() as db:
            row = db.execute("SELECT * FROM evidence_claims WHERE id=?", (claim_id,)).fetchone()
            return self._claim_public(db, row) if row else None

    def list_claims(self, limit=50):
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM evidence_claims ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._claim_public(db, row) for row in rows]

    def stats(self):
        with self._connect() as db:
            return {
                "claims_recorded": db.execute("SELECT COUNT(*) FROM evidence_claims").fetchone()[0],
                "evidence_links_recorded": db.execute("SELECT COUNT(*) FROM evidence_links").fetchone()[0],
            }
