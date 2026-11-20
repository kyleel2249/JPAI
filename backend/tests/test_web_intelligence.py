"""Regression tests for governed web collection and source monitoring."""
import socket
from datetime import UTC, datetime, timedelta

import pytest

from jpai_api.research.crawler import (
    CrawlPolicyError,
    CrawlerStore,
    PageExtractor,
    parse_robots_rules,
    robots_path_allowed,
    validate_public_url,
)


def _parser(title, text):
    parser = PageExtractor()
    parser.feed(f"<title>{title}</title><p>{text}</p>")
    return parser


def test_private_destination_rejected(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 0))],
    )
    with pytest.raises(CrawlPolicyError):
        validate_public_url("http://example.test")


def test_mixed_public_and_private_dns_is_rejected(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (None, None, None, None, ("93.184.216.34", 0)),
            (None, None, None, None, ("10.0.0.4", 0)),
        ],
    )
    with pytest.raises(CrawlPolicyError):
        validate_public_url("https://example.test")


def test_public_url_normalized(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 0))],
    )
    assert validate_public_url("https://example.com/path#section") == "https://example.com/path"


def test_credentials_non_http_and_invalid_port_rejected():
    with pytest.raises(CrawlPolicyError):
        validate_public_url("file:///etc/passwd")
    with pytest.raises(CrawlPolicyError):
        validate_public_url("https://user:pass@example.com")
    with pytest.raises(CrawlPolicyError):
        validate_public_url("https://example.com:99999")


def test_html_extraction():
    parser = PageExtractor()
    parser.feed(
        '<title>Example</title><meta name="description" content="A test">'
        '<h1>Welcome</h1><p>Useful content</p><a href="/next">Next</a>'
        "<script>secret()</script>"
    )
    assert "Example" in parser.title_parts
    assert "Useful content" in parser.text_parts
    assert "/next" in parser.links
    assert parser.meta["description"] == "A test"
    assert "secret()" not in parser.text_parts


def test_jsonld_structured_data_is_extracted_without_leaking_script_text():
    parser = PageExtractor()
    parser.feed(
        '<title>Research</title>'
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Article",'
        '"headline":"Market outlook","author":{"@type":"Person","name":"A. Analyst"}}'
        '</script><p>Visible article text</p>'
        '<script>secret_token()</script>'
    )
    assert len(parser.structured_data) == 1
    assert parser.structured_data[0]["@type"] == "Article"
    assert "secret_token" not in parser.text_parts


def test_invalid_and_oversized_jsonld_are_ignored():
    parser = PageExtractor()
    parser.feed(
        '<script type="application/ld+json">{invalid}</script>'
        '<script type="application/ld+json">' + ('x' * 50001) + '</script>'
    )
    assert parser.structured_data == []


def test_jsonld_structured_data_persists_and_legacy_rows_default_empty(tmp_path):
    store = CrawlerStore(str(tmp_path / "structured.sqlite3"))
    job = store.create_job("https://example.com", 2)
    parser = PageExtractor()
    parser.feed(
        '<script type="application/ld+json">'
        '{"@type":"NewsArticle","headline":"A headline"}'
        '</script><p>Body text</p>'
    )
    result = store.save_page(
        job["id"], "https://example.com/article", "example.com",
        parser, 200, "text/html", "raw-hash",
    )
    page = store.get_page(result["page_id"])
    assert page["structured_data"] == [{"@type": "NewsArticle", "headline": "A headline"}]
    assert store.stats()["pages_with_structured_data"] == 1


def test_persistence_and_search(tmp_path):
    store = CrawlerStore(str(tmp_path / "web.sqlite3"))
    job = store.create_job("https://example.com", 5)
    store.save_page(
        job["id"], "https://example.com/report", "example.com",
        _parser("Market research", "Economic intelligence report"),
        200, "text/html", "raw-hash",
    )
    store.update_job(job["id"], "completed", 1)
    assert store.get_job(job["id"])["pages_crawled"] == 1
    assert store.search_pages("economic report")[0]["title"] == "Market research"
    assert store.stats()["pages_stored"] == 1


def test_page_versions_and_content_change_detection(tmp_path):
    store = CrawlerStore(str(tmp_path / "versions.sqlite3"))
    first_job = store.create_job("https://example.com", 5)
    first = store.save_page(
        first_job["id"], "https://example.com/report", "example.com",
        _parser("Market report", "Revenue increased by 5 percent"),
        200, "text/html", "raw-1",
    )
    second_job = store.create_job("https://example.com", 5, schedule_id=7)
    second = store.save_page(
        second_job["id"], "https://example.com/report", "example.com",
        _parser("Market report", "Revenue increased by 8 percent"),
        200, "text/html", "raw-2", schedule_id=7,
    )
    assert first["page_id"] == second["page_id"]
    assert first["changed"] is False
    assert second["changed"] is True
    versions = store.list_versions(first["page_id"])
    assert len(versions) == 2
    changes = store.list_changes()
    assert len(changes) == 1
    assert changes[0]["schedule_id"] == 7
    assert changes[0]["change_type"] == "content_changed"
    assert changes[0]["previous_hash"] != changes[0]["current_hash"]


def test_identical_content_does_not_create_false_change_event(tmp_path):
    store = CrawlerStore(str(tmp_path / "stable.sqlite3"))
    job = store.create_job("https://example.com", 5)
    parser = _parser("Stable", "Same extracted content")
    store.save_page(job["id"], "https://example.com/page", "example.com", parser, 200, "text/html", "raw-a")
    store.save_page(job["id"], "https://example.com/page", "example.com", parser, 200, "text/html", "raw-b")
    assert len(store.list_versions(1)) == 1
    assert store.list_changes() == []


def test_schedule_claim_is_persistent_and_single_claim(tmp_path):
    store = CrawlerStore(str(tmp_path / "schedules.sqlite3"))
    schedule = store.create_schedule("https://example.com", 60, 5)
    due_time = datetime.now(UTC) + timedelta(seconds=2)
    claimed = store.claim_due_schedules(now=due_time)
    assert [item["id"] for item in claimed] == [schedule["id"]]
    assert store.claim_due_schedules(now=due_time) == []
    paused = store.set_schedule_enabled(schedule["id"], False)
    assert paused["enabled"] == 0
    assert store.get_schedule(schedule["id"])["enabled"] == 0


def test_legacy_page_table_is_migrated_without_data_loss(tmp_path):
    import sqlite3

    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE crawl_jobs(
              id TEXT PRIMARY KEY, seed_url TEXT NOT NULL, status TEXT NOT NULL,
              max_pages INTEGER NOT NULL, pages_crawled INTEGER NOT NULL DEFAULT 0,
              error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE crawled_pages(
              id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, url TEXT NOT NULL UNIQUE,
              canonical_url TEXT, domain TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
              description TEXT NOT NULL DEFAULT '', content TEXT NOT NULL DEFAULT '',
              headings_json TEXT NOT NULL DEFAULT '[]', metadata_json TEXT NOT NULL DEFAULT '{}',
              status_code INTEGER NOT NULL, content_type TEXT NOT NULL, content_hash TEXT NOT NULL,
              fetched_at TEXT NOT NULL);
            INSERT INTO crawl_jobs VALUES('old','https://example.com','completed',1,1,NULL,'2026-01-01','2026-01-01');
            INSERT INTO crawled_pages(job_id,url,domain,status_code,content_type,content_hash,fetched_at)
              VALUES('old','https://example.com','example.com',200,'text/html','hash','2026-01-01');
            """
        )
    store = CrawlerStore(str(path))
    assert store.get_page(1)["url"] == "https://example.com"
    assert "schedule_id" in store.get_job("old")
    assert "memory_id" in store.get_page(1)



def test_scheduler_creates_and_executes_due_job(tmp_path, monkeypatch):
    from jpai_api.research.crawler import WebCrawler

    store = CrawlerStore(str(tmp_path / "scheduler.sqlite3"))
    schedule = store.create_schedule("https://example.com", 60, 4)
    crawler = WebCrawler(store)
    calls = []

    def fake_run(job_id):
        calls.append(job_id)
        store.update_job(job_id, "completed", 0)

    monkeypatch.setattr(crawler, "run", fake_run)
    result = crawler.run_due_schedules()
    assert len(result) == 1
    assert calls == [result[0]["job_id"]]
    job = store.get_job(result[0]["job_id"])
    assert job["schedule_id"] == schedule["id"]
    assert job["status"] == "completed"
    assert store.get_schedule(schedule["id"])["last_job_id"] == job["id"]



def test_http_connection_uses_the_pinned_public_ip(monkeypatch):
    from jpai_api.research.crawler import _PinnedHTTPConnection

    calls = []

    class FakeSocket:
        def close(self):
            return None

    def fake_create_connection(address, timeout):
        calls.append((address, timeout))
        return FakeSocket()

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    connection = _PinnedHTTPConnection("example.com", 80, "93.184.216.34", 15)
    connection.connect()
    connection.close()
    assert calls == [(("93.184.216.34", 80), 15)]



def test_robots_txt_fails_closed_on_server_errors():
    with pytest.raises(CrawlPolicyError):
        parse_robots_rules("", 503)
    assert parse_robots_rules("", 404) == []


def test_robots_allow_rule_overrides_less_specific_disallow():
    rules = parse_robots_rules(
        "User-agent: *\nDisallow: /private\nAllow: /private/public\n",
        200,
    )
    assert robots_path_allowed("/public", rules)
    assert not robots_path_allowed("/private/account", rules)
    assert robots_path_allowed("/private/public/report", rules)


def _make_docx(text):
    import io
    import zipfile

    buffer = io.BytesIO()
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>'
    )
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", xml)
    return buffer.getvalue()


def test_document_text_extraction_and_sha256():
    from jpai_api.research.documents import extract_document

    result = extract_document("market-report.txt", b"Revenue outlook for next quarter")
    assert result["file_type"] == "txt"
    assert result["text"] == "Revenue outlook for next quarter"
    assert len(result["content_hash"]) == 64
    assert result["extracted_chars"] == len(result["text"])


def test_docx_extraction_reads_paragraph_text():
    from jpai_api.research.documents import extract_document

    result = extract_document("briefing.docx", _make_docx("Regional infrastructure outlook"))
    assert result["text"] == "Regional infrastructure outlook"


def test_document_extraction_rejects_unsupported_and_mismatched_files():
    from jpai_api.research.documents import DocumentExtractionError, extract_document

    with pytest.raises(DocumentExtractionError):
        extract_document("payload.exe", b"not a document")
    with pytest.raises(DocumentExtractionError):
        extract_document("report.pdf", b"not a PDF")
    with pytest.raises(DocumentExtractionError):
        extract_document("report.docx", b"not a zip archive")


def test_document_extraction_enforces_upload_size_and_utf8():
    from jpai_api.research.documents import (
        MAX_DOCUMENT_BYTES,
        DocumentExtractionError,
        extract_document,
    )

    with pytest.raises(DocumentExtractionError):
        extract_document("large.txt", b"x" * (MAX_DOCUMENT_BYTES + 1))
    with pytest.raises(DocumentExtractionError):
        extract_document("invalid.txt", b"\xff\xfe")


def test_document_store_persistence_deduplication_and_search(tmp_path):
    from jpai_api.research.documents import DocumentStore, extract_document

    store = DocumentStore(str(tmp_path / "documents.sqlite3"))
    payload = b"Central bank policy and inflation research"
    document = extract_document("policy.txt", payload)
    first = store.save(document)
    duplicate = store.save(document)
    assert first["id"] == duplicate["id"]
    assert store.stats()["documents_stored"] == 1
    assert store.get(first["id"], include_content=True)["content"] == document["text"]
    results = store.search("inflation policy")
    assert results[0]["id"] == first["id"]
    assert "content" not in results[0]


def test_document_upload_and_search_api(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from jpai_api.main import app
    from jpai_api.routes import web_intelligence
    from jpai_api.research.documents import DocumentStore

    store = DocumentStore(str(tmp_path / "api-documents.sqlite3"))
    monkeypatch.setattr(web_intelligence, "get_document_store", lambda: store)
    client = TestClient(app)
    uploaded = client.post(
        "/api/v1/web-intelligence/documents",
        files={"file": ("briefing.txt", b"Energy transition and infrastructure investment", "text/plain")},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["document"]["id"]
    assert uploaded.json()["trust"] == "unverified_user_supplied_document"
    searched = client.get(
        "/api/v1/web-intelligence/documents/search",
        params={"q": "infrastructure investment"},
    )
    assert searched.status_code == 200
    assert searched.json()["items"][0]["id"] == document_id
    detail = client.get(f"/api/v1/web-intelligence/documents/{document_id}")
    assert detail.status_code == 200
    assert "Energy transition" in detail.json()["content"]


def test_document_upload_api_rejects_unsupported_format(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from jpai_api.main import app
    from jpai_api.routes import web_intelligence
    from jpai_api.research.documents import DocumentStore

    monkeypatch.setattr(
        web_intelligence, "get_document_store",
        lambda: DocumentStore(str(tmp_path / "reject.sqlite3")),
    )
    response = TestClient(app).post(
        "/api/v1/web-intelligence/documents",
        files={"file": ("payload.exe", b"not allowed", "application/octet-stream")},
    )
    assert response.status_code == 400



def test_evidence_index_unifies_web_and_document_sources_and_preserves_provenance(tmp_path):
    from jpai_api.research.documents import DocumentStore, extract_document
    from jpai_api.research.evidence import EvidenceStore

    path = str(tmp_path / "evidence.sqlite3")
    web = CrawlerStore(path)
    documents = DocumentStore(path)
    job = web.create_job("https://example.com", 2)
    web.save_page(
        job["id"], "https://example.com/report", "example.com",
        _parser("Energy outlook", "Renewable energy investment increased during the reporting period."),
        200, "text/html", "raw-hash",
    )
    document = documents.save(extract_document(
        "energy-brief.txt", b"Renewable energy investment increased during the reporting period."
    ))
    evidence = EvidenceStore(path)
    results = evidence.search_sources("renewable energy")
    assert {item["source_type"] for item in results} == {"web", "document"}
    assert all("source_hash" in item and "trust" in item for item in results)
    assert evidence.stats() == {"claims_recorded": 0, "evidence_links_recorded": 0}


def test_evidence_claim_requires_verbatim_source_excerpt_and_reports_conflicts(tmp_path):
    from jpai_api.research.evidence import EvidenceError, EvidenceStore

    path = str(tmp_path / "claims.sqlite3")
    web = CrawlerStore(path)
    first_job = web.create_job("https://alpha.example", 2)
    first = web.save_page(
        first_job["id"], "https://alpha.example/a", "alpha.example",
        _parser("Report A", "The project budget increased by 12 percent in the latest review."),
        200, "text/html", "a",
    )
    second_job = web.create_job("https://beta.example", 2)
    second = web.save_page(
        second_job["id"], "https://beta.example/b", "beta.example",
        _parser("Report B", "The project budget decreased by 4 percent in the latest review."),
        200, "text/html", "b",
    )
    store = EvidenceStore(path)
    claim = store.create_claim("The project budget increased in the latest review.")
    with pytest.raises(EvidenceError):
        store.add_evidence(claim["id"], "web", first["page_id"], "supports",
                           "A fabricated quotation that is not present in the source.")
    updated = store.add_evidence(
        claim["id"], "web", first["page_id"], "supports",
        "The project budget increased by 12 percent in the latest review.",
    )
    updated = store.add_evidence(
        claim["id"], "web", second["page_id"], "contradicts",
        "The project budget decreased by 4 percent in the latest review.",
    )
    assert updated["support_count"] == 1
    assert updated["contradiction_count"] == 1
    assert updated["source_origins"] == 2
    assert updated["evidence_balance"] == "contested"
    assert updated["verification_status"] == "not_verified"
    assert len(updated["evidence"]) == 2


def test_evidence_link_rejects_missing_claim_or_source_and_invalid_excerpt(tmp_path):
    from jpai_api.research.evidence import EvidenceError, EvidenceStore

    store = EvidenceStore(str(tmp_path / "missing.sqlite3"))
    with pytest.raises(EvidenceError, match="claim"):
        store.add_evidence(99, "web", 1, "supports", "A sufficiently long quotation.")
    claim = store.create_claim("A statement that requires evidence.")
    with pytest.raises(EvidenceError, match="source"):
        store.add_evidence(claim["id"], "document", 99, "supports",
                           "A sufficiently long quotation from a missing file.")


def test_evidence_api_claim_lifecycle_and_verbatim_quote_validation(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from jpai_api.main import app
    from jpai_api.routes import web_intelligence
    from jpai_api.research.documents import DocumentStore
    from jpai_api.research.evidence import EvidenceStore

    path = str(tmp_path / "evidence-api.sqlite3")
    crawler = CrawlerStore(path)
    job = crawler.create_job("https://example.com", 1)
    page = crawler.save_page(
        job["id"], "https://example.com/evidence", "example.com",
        _parser("Evidence report", "Independent testing confirmed the system passed all checks."),
        200, "text/html", "api-hash",
    )
    monkeypatch.setattr(web_intelligence, "get_store", lambda: crawler)
    monkeypatch.setattr(web_intelligence, "get_document_store", lambda: DocumentStore(path))
    monkeypatch.setattr(web_intelligence, "get_evidence_store", lambda: EvidenceStore(path))
    client = TestClient(app)
    sources = client.get("/api/v1/web-intelligence/evidence/sources?q=independent")
    assert sources.status_code == 200
    assert sources.json()["items"][0]["source_type"] == "web"
    claim = client.post("/api/v1/web-intelligence/evidence/claims",
                        json={"statement": "The system passed independent testing."})
    assert claim.status_code == 201
    invalid = client.post(
        f"/api/v1/web-intelligence/evidence/claims/{claim.json()['id']}/evidence",
        json={"source_type": "web", "source_id": page["page_id"], "stance": "supports",
              "excerpt": "This is a fabricated quote with enough characters."},
    )
    assert invalid.status_code == 400
    linked = client.post(
        f"/api/v1/web-intelligence/evidence/claims/{claim.json()['id']}/evidence",
        json={"source_type": "web", "source_id": page["page_id"], "stance": "supports",
              "excerpt": "Independent testing confirmed the system passed all checks."},
    )
    assert linked.status_code == 200
    assert linked.json()["support_count"] == 1
    assert linked.json()["verification_status"] == "not_verified"
    assert web_intelligence.get_evidence_store().list_claims()[0]["id"] == claim.json()["id"]


def test_evidence_store_bootstraps_source_catalogues_on_first_use(tmp_path):
    from jpai_api.research.evidence import EvidenceStore

    store = EvidenceStore(str(tmp_path / "first-use.sqlite3"))
    assert store.search_sources() == []
    assert store.stats() == {"claims_recorded": 0, "evidence_links_recorded": 0}
