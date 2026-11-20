"""Governed, DNS-pinned web crawling, source history and scheduled monitoring."""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import sqlite3
import ssl
import time
import uuid
from collections import deque
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse


MAX_PAGE_BYTES = 1_500_000
USER_AGENT = "JPAI-ResearchBot/1.1 (+local research; respects robots.txt)"


class CrawlPolicyError(ValueError):
    """A URL or crawl request violates the safe collection policy."""


def _resolve_public_address(host: str, port: int) -> str:
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise CrawlPolicyError("Hostname could not be resolved") from exc
    addresses = {record[4][0].split("%", 1)[0] for record in records}
    if not addresses:
        raise CrawlPolicyError("Hostname has no resolved addresses")
    for address in addresses:
        if not ipaddress.ip_address(address).is_global:
            raise CrawlPolicyError("Private, loopback, link-local and reserved destinations are blocked")
    return next(iter(addresses))


def validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CrawlPolicyError("Only absolute HTTP(S) URLs are supported")
    if parsed.username or parsed.password:
        raise CrawlPolicyError("URLs containing credentials are not allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise CrawlPolicyError("Local and private network destinations are not allowed")
    _resolve_public_address(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    return urlunparse(parsed._replace(fragment=""))


class PageExtractor(HTMLParser):
    """Dependency-free HTML text and metadata extractor."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.text_parts = []
        self.links = []
        self.meta = {}
        self.headings = []
        self._title = False
        self._heading = None
        self._skip_tags = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self._skip_tags.append(tag)
        if tag == "title":
            self._title = True
        if tag in {"h1", "h2", "h3"}:
            self._heading = {"level": tag, "text": ""}
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "meta":
            key = attrs.get("name") or attrs.get("property")
            if key and attrs.get("content"):
                self.meta[key.lower()] = attrs["content"][:1000]

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip_tags.remove(tag)
        if tag == "title":
            self._title = False
        if self._heading and tag == self._heading["level"]:
            self.headings.append(self._heading)
            self._heading = None

    def handle_data(self, data):
        value = re.sub(r"\\s+", " ", data).strip()
        if not value or self._skip_tags:
            return
        if self._title:
            self.title_parts.append(value)
        else:
            self.text_parts.append(value)
        if self._heading:
            self._heading["text"] += (" " if self._heading["text"] else "") + value


class _FetchResponse:
    def __init__(self, status_code, headers, content):
        self.status_code = status_code
        self.headers = headers
        self.content = content

    @property
    def text(self):
        content_type = self.headers.get("content-type", "")
        match = re.search(r"charset=([w-]+)", content_type, re.IGNORECASE)
        encoding = match.group(1) if match else "utf-8"
        try:
            return self.content.decode(encoding, errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host, port, address, timeout):
        super().__init__(host, port, timeout=timeout)
        self._pinned_address = address

    def connect(self):
        self.sock = socket.create_connection((self._pinned_address, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, port, address, timeout):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._pinned_address = address

    def connect(self):
        raw_socket = socket.create_connection((self._pinned_address, self.port), self.timeout)
        self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)


class CrawlerStore:
    """SQLite persistence for crawl jobs, schedules, page versions and change events."""

    def __init__(self, path=None):
        self.path = Path(path or os.getenv("JPAI_DATABASE_PATH", "data/jpai.sqlite3")).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS crawl_jobs(
              id TEXT PRIMARY KEY, seed_url TEXT NOT NULL, status TEXT NOT NULL,
              max_pages INTEGER NOT NULL, pages_crawled INTEGER NOT NULL DEFAULT 0,
              error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS crawled_pages(
              id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, url TEXT NOT NULL UNIQUE,
              canonical_url TEXT, domain TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
              description TEXT NOT NULL DEFAULT '', content TEXT NOT NULL DEFAULT '',
              headings_json TEXT NOT NULL DEFAULT '[]', metadata_json TEXT NOT NULL DEFAULT '{}',
              status_code INTEGER NOT NULL, content_type TEXT NOT NULL, content_hash TEXT NOT NULL,
              fetched_at TEXT NOT NULL, memory_id INTEGER,
              FOREIGN KEY(job_id) REFERENCES crawl_jobs(id) ON DELETE CASCADE);
            CREATE INDEX IF NOT EXISTS idx_crawled_pages_domain ON crawled_pages(domain);
            CREATE INDEX IF NOT EXISTS idx_crawled_pages_job ON crawled_pages(job_id);
            CREATE INDEX IF NOT EXISTS idx_crawled_pages_fetched ON crawled_pages(fetched_at DESC);
            CREATE TABLE IF NOT EXISTS crawl_schedules(
              id INTEGER PRIMARY KEY AUTOINCREMENT, seed_url TEXT NOT NULL,
              interval_minutes INTEGER NOT NULL, max_pages INTEGER NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 1, next_run_at TEXT NOT NULL,
              last_run_at TEXT, last_job_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_crawl_schedules_due ON crawl_schedules(enabled,next_run_at);
            CREATE TABLE IF NOT EXISTS crawled_page_versions(
              id INTEGER PRIMARY KEY AUTOINCREMENT, page_id INTEGER NOT NULL, job_id TEXT NOT NULL,
              title TEXT NOT NULL, description TEXT NOT NULL, content TEXT NOT NULL,
              content_hash TEXT NOT NULL, fetched_at TEXT NOT NULL,
              UNIQUE(page_id,content_hash),
              FOREIGN KEY(page_id) REFERENCES crawled_pages(id) ON DELETE CASCADE);
            CREATE INDEX IF NOT EXISTS idx_page_versions_page ON crawled_page_versions(page_id,fetched_at DESC);
            CREATE TABLE IF NOT EXISTS crawl_change_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT, schedule_id INTEGER, page_id INTEGER NOT NULL,
              job_id TEXT NOT NULL, change_type TEXT NOT NULL, previous_hash TEXT,
              current_hash TEXT NOT NULL, summary TEXT NOT NULL, detected_at TEXT NOT NULL,
              FOREIGN KEY(page_id) REFERENCES crawled_pages(id) ON DELETE CASCADE);
            CREATE INDEX IF NOT EXISTS idx_crawl_changes_detected ON crawl_change_events(detected_at DESC);
            """)
            job_columns = {row[1] for row in db.execute("PRAGMA table_info(crawl_jobs)")}
            if "schedule_id" not in job_columns:
                db.execute("ALTER TABLE crawl_jobs ADD COLUMN schedule_id INTEGER")
            page_columns = {row[1] for row in db.execute("PRAGMA table_info(crawled_pages)")}
            if "memory_id" not in page_columns:
                db.execute("ALTER TABLE crawled_pages ADD COLUMN memory_id INTEGER")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def create_job(self, seed_url, max_pages, schedule_id=None):
        job_id = uuid.uuid4().hex
        now = datetime.now(UTC).isoformat()
        with self._connect() as db:
            db.execute(
                """INSERT INTO crawl_jobs(id,seed_url,status,max_pages,created_at,updated_at,schedule_id)
                   VALUES(?,?,?,?,?,?,?)""",
                (job_id, seed_url, "queued", max_pages, now, now, schedule_id),
            )
        return self.get_job(job_id)

    def update_job(self, job_id, status, pages=None, error=None):
        now = datetime.now(UTC).isoformat()
        with self._connect() as db:
            if pages is None:
                db.execute(
                    "UPDATE crawl_jobs SET status=?,error=?,updated_at=? WHERE id=?",
                    (status, error, now, job_id),
                )
            else:
                db.execute(
                    """UPDATE crawl_jobs SET status=?,pages_crawled=?,error=?,updated_at=?
                       WHERE id=?""",
                    (status, pages, error, now, job_id),
                )

    def get_job(self, job_id):
        with self._connect() as db:
            row = db.execute("SELECT * FROM crawl_jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def list_jobs(self, limit=30):
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM crawl_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def create_schedule(self, seed_url, interval_minutes, max_pages):
        now = datetime.now(UTC)
        timestamp = now.isoformat()
        with self._connect() as db:
            cursor = db.execute(
                """INSERT INTO crawl_schedules(seed_url,interval_minutes,max_pages,enabled,
                   next_run_at,created_at,updated_at) VALUES(?,?,?,1,?,?,?)""",
                (seed_url, interval_minutes, max_pages, timestamp, timestamp, timestamp),
            )
            schedule_id = cursor.lastrowid
            return dict(db.execute(
                "SELECT * FROM crawl_schedules WHERE id=?", (schedule_id,)
            ).fetchone())

    def get_schedule(self, schedule_id):
        with self._connect() as db:
            row = db.execute("SELECT * FROM crawl_schedules WHERE id=?", (schedule_id,)).fetchone()
        return dict(row) if row else None

    def list_schedules(self, limit=100):
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM crawl_schedules ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def set_schedule_enabled(self, schedule_id, enabled):
        now = datetime.now(UTC).isoformat()
        with self._connect() as db:
            cursor = db.execute(
                """UPDATE crawl_schedules SET enabled=?,updated_at=? WHERE id=?""",
                (int(enabled), now, schedule_id),
            )
            row = db.execute(
                "SELECT * FROM crawl_schedules WHERE id=?", (schedule_id,)
            ).fetchone()
        return dict(row) if cursor.rowcount and row else None

    def claim_due_schedules(self, now=None, limit=5):
        """Atomically claim due schedules so multiple local workers cannot duplicate a run."""
        current = (now or datetime.now(UTC)).astimezone(UTC)
        timestamp = current.isoformat()
        claimed = []
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                """SELECT * FROM crawl_schedules WHERE enabled=1 AND next_run_at<=?
                   ORDER BY next_run_at LIMIT ?""",
                (timestamp, limit),
            ).fetchall()
            for row in rows:
                next_run = (current + timedelta(minutes=row["interval_minutes"])).isoformat()
                db.execute(
                    """UPDATE crawl_schedules SET next_run_at=?,last_run_at=?,updated_at=?
                       WHERE id=? AND enabled=1 AND next_run_at<=?""",
                    (next_run, timestamp, timestamp, row["id"], timestamp),
                )
                claimed.append(dict(row))
        return claimed

    def attach_schedule_job(self, schedule_id, job_id):
        with self._connect() as db:
            db.execute(
                "UPDATE crawl_schedules SET last_job_id=?,updated_at=? WHERE id=?",
                (job_id, datetime.now(UTC).isoformat(), schedule_id),
            )

    def save_page(self, job_id, url, domain, parsed, status_code, content_type, content_hash,
                  schedule_id=None):
        now = datetime.now(UTC).isoformat()
        title = " ".join(parsed.title_parts)[:500]
        content = re.sub(r"\\s+", " ", " ".join(parsed.text_parts)).strip()[:200000]
        description = parsed.meta.get("description", parsed.meta.get("og:description", ""))[:2000]
        # Fingerprint extracted, normalized content rather than volatile HTML markup.
        normalized_hash = hashlib.sha256(
            (title + "\\n" + description + "\\n" + content).encode("utf-8")
        ).hexdigest()
        with self._connect() as db:
            old = db.execute(
                "SELECT id,content_hash,title FROM crawled_pages WHERE url=?", (url,)
            ).fetchone()
            if old:
                page_id = old["id"]
                previous_hash = old["content_hash"]
                previous_title = old["title"]
                db.execute(
                    """UPDATE crawled_pages SET job_id=?,domain=?,title=?,description=?,content=?,
                       headings_json=?,metadata_json=?,status_code=?,content_type=?,content_hash=?,
                       fetched_at=? WHERE id=?""",
                    (job_id, domain, title, description, content, json.dumps(parsed.headings[:80]),
                     json.dumps(parsed.meta), status_code, content_type, normalized_hash, now, page_id),
                )
            else:
                cursor = db.execute(
                    """INSERT INTO crawled_pages(job_id,url,domain,title,description,content,
                       headings_json,metadata_json,status_code,content_type,content_hash,fetched_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (job_id, url, domain, title, description, content, json.dumps(parsed.headings[:80]),
                     json.dumps(parsed.meta), status_code, content_type, normalized_hash, now),
                )
                page_id = cursor.lastrowid
                previous_hash = None
                previous_title = ""
            db.execute(
                """INSERT OR IGNORE INTO crawled_page_versions
                   (page_id,job_id,title,description,content,content_hash,fetched_at)
                   VALUES(?,?,?,?,?,?,?)""",
                (page_id, job_id, title, description, content, normalized_hash, now),
            )
            changed = bool(previous_hash and previous_hash != normalized_hash)
            if changed:
                summary = "Page content changed"
                if previous_title != title:
                    summary += "; page title changed"
                db.execute(
                    """INSERT INTO crawl_change_events(schedule_id,page_id,job_id,change_type,
                       previous_hash,current_hash,summary,detected_at)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (schedule_id, page_id, job_id, "content_changed", previous_hash,
                     normalized_hash, summary, now),
                )
            return {"page_id": page_id, "changed": changed, "content_hash": normalized_hash}

    def list_pages(self, job_id=None, limit=50):
        with self._connect() as db:
            if job_id:
                rows = db.execute(
                    """SELECT id,job_id,url,domain,title,description,status_code,content_type,
                       content_hash,fetched_at,memory_id FROM crawled_pages WHERE job_id=?
                       ORDER BY fetched_at DESC LIMIT ?""", (job_id, limit)
                ).fetchall()
            else:
                rows = db.execute(
                    """SELECT id,job_id,url,domain,title,description,status_code,content_type,
                       content_hash,fetched_at,memory_id FROM crawled_pages
                       ORDER BY fetched_at DESC LIMIT ?""", (limit,)
                ).fetchall()
        return [dict(row) for row in rows]

    def search_pages(self, query, limit=20):
        terms = [term.lower() for term in re.findall(r"[\\w-]{2,}", query)][:12]
        if not terms:
            return []
        with self._connect() as db:
            rows = db.execute(
                """SELECT id,job_id,url,domain,title,description,content,fetched_at,content_hash
                   FROM crawled_pages ORDER BY fetched_at DESC LIMIT 1000"""
            ).fetchall()
        ranked = []
        for row in rows:
            item = dict(row)
            title = item["title"].lower()
            content = item["content"].lower()
            score = sum(title.count(term) * 4 + content.count(term) for term in terms)
            if score:
                item["relevance"] = score
                item["excerpt"] = item["content"][:420]
                item.pop("content")
                ranked.append(item)
        return sorted(
            ranked, key=lambda item: (item["relevance"], item["fetched_at"]), reverse=True
        )[:limit]

    def get_page(self, page_id):
        with self._connect() as db:
            row = db.execute("SELECT * FROM crawled_pages WHERE id=?", (page_id,)).fetchone()
        return dict(row) if row else None

    def mark_page_memory(self, page_id, memory_id):
        with self._connect() as db:
            db.execute("UPDATE crawled_pages SET memory_id=? WHERE id=?", (memory_id, page_id))

    def list_versions(self, page_id, limit=50):
        with self._connect() as db:
            rows = db.execute(
                """SELECT id,page_id,job_id,title,description,content_hash,fetched_at
                   FROM crawled_page_versions WHERE page_id=? ORDER BY fetched_at DESC LIMIT ?""",
                (page_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_changes(self, limit=100):
        with self._connect() as db:
            rows = db.execute(
                """SELECT c.*,p.url,p.domain,p.title FROM crawl_change_events c
                   JOIN crawled_pages p ON p.id=c.page_id
                   ORDER BY c.detected_at DESC LIMIT ?""", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def stats(self):
        with self._connect() as db:
            return {
                "pages_stored": db.execute("SELECT COUNT(*) FROM crawled_pages").fetchone()[0],
                "domains_indexed": db.execute(
                    "SELECT COUNT(DISTINCT domain) FROM crawled_pages"
                ).fetchone()[0],
                "jobs_total": db.execute("SELECT COUNT(*) FROM crawl_jobs").fetchone()[0],
                "schedules_total": db.execute("SELECT COUNT(*) FROM crawl_schedules").fetchone()[0],
                "changes_detected": db.execute("SELECT COUNT(*) FROM crawl_change_events").fetchone()[0],
                "versions_stored": db.execute("SELECT COUNT(*) FROM crawled_page_versions").fetchone()[0],
            }


class WebCrawler:
    def __init__(self, store=None, delay_seconds=1.0):
        self.store = store or CrawlerStore()
        self.delay_seconds = max(1.0, min(delay_seconds, 10.0))

    def _get(self, url):
        safe = validate_public_url(url)
        parsed = urlparse(safe)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        # Resolve and validate again, then connect to this exact IP to prevent DNS rebinding.
        address = _resolve_public_address(host, port)
        connection_type = _PinnedHTTPSConnection if parsed.scheme == "https" else _PinnedHTTPConnection
        connection = connection_type(host, port, address, timeout=15)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        try:
            connection.request(
                "GET", path,
                headers={
                    "Host": parsed.netloc,
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Encoding": "identity",
                    "Connection": "close",
                },
            )
            response = connection.getresponse()
            headers = {key.lower(): value for key, value in response.getheaders()}
            length = headers.get("content-length", "")
            if length.isdigit() and int(length) > MAX_PAGE_BYTES:
                raise CrawlPolicyError("Page exceeded response-size limit")
            chunks = []
            total = 0
            while True:
                chunk = response.read(min(65536, MAX_PAGE_BYTES + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_PAGE_BYTES:
                    raise CrawlPolicyError("Page exceeded response-size limit")
                chunks.append(chunk)
            return _FetchResponse(response.status, headers, b"".join(chunks))
        finally:
            connection.close()

    def run(self, job_id):
        job = self.store.get_job(job_id)
        if not job:
            return
        self.store.update_job(job_id, "running", 0)
        pages = 0
        try:
            seed = validate_public_url(job["seed_url"])
            parts = urlparse(seed)
            origin = (parts.scheme, parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))
            queue = deque([(seed, 0)])
            seen = set()
            robots_url = urlunparse((parts.scheme, parts.netloc, "/robots.txt", "", "", ""))
            robots = self._get(robots_url)
            disallowed = []
            active = False
            for line in (robots.text[:100000] if robots.status_code == 200 else "").splitlines():
                line = line.split("#", 1)[0].strip()
                if ":" not in line:
                    continue
                key, value = [part.strip() for part in line.split(":", 1)]
                if key.lower() == "user-agent":
                    active = value == "*" or "JPAI-ResearchBot" in value
                elif active and key.lower() == "disallow" and value:
                    disallowed.append(value)
            while queue and pages < job["max_pages"]:
                url, depth = queue.popleft()
                url = validate_public_url(url)
                parsed_url = urlparse(url)
                target_port = parsed_url.port or (443 if parsed_url.scheme == "https" else 80)
                if (parsed_url.scheme, parsed_url.hostname, target_port) != origin or url in seen:
                    continue
                seen.add(url)
                if any(parsed_url.path.startswith(rule) for rule in disallowed):
                    continue
                time.sleep(self.delay_seconds)
                response = self._get(url)
                if response.status_code != 200:
                    continue
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    continue
                parser = PageExtractor()
                parser.feed(response.text)
                digest = hashlib.sha256(response.content).hexdigest()
                self.store.save_page(
                    job_id, url, parsed_url.hostname or "", parser, 200, content_type,
                    digest, schedule_id=job.get("schedule_id"),
                )
                pages += 1
                self.store.update_job(job_id, "running", pages)
                if depth < 2:
                    for href in parser.links:
                        if href.startswith(("mailto:", "javascript:", "tel:", "data:")):
                            continue
                        candidate = urldefrag(urljoin(url, href))[0]
                        target = urlparse(candidate)
                        if target.hostname == origin[1] and target.scheme in {"http", "https"}:
                            queue.append((candidate, depth + 1))
            self.store.update_job(job_id, "completed", pages)
        except (CrawlPolicyError, OSError, http.client.HTTPException, ssl.SSLError, ValueError) as exc:
            self.store.update_job(job_id, "failed", pages, str(exc)[:500])

    def run_due_schedules(self, limit=5):
        claimed = self.store.claim_due_schedules(limit=limit)
        results = []
        for schedule in claimed:
            job = self.store.create_job(
                schedule["seed_url"], schedule["max_pages"], schedule_id=schedule["id"]
            )
            self.store.attach_schedule_job(schedule["id"], job["id"])
            self.run(job["id"])
            results.append({"schedule_id": schedule["id"], "job_id": job["id"]})
        return results
