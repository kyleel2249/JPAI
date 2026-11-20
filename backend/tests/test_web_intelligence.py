"""Regression tests for governed web collection and source monitoring."""
import socket
from datetime import UTC, datetime, timedelta

import pytest

from jpai_api.research.crawler import (
    CrawlPolicyError,
    CrawlerStore,
    PageExtractor,
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


def test_credentials_and_non_http_rejected():
    with pytest.raises(CrawlPolicyError):
        validate_public_url("file:///etc/passwd")
    with pytest.raises(CrawlPolicyError):
        validate_public_url("https://user:pass@example.com")


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
