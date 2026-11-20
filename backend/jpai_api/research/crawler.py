"""Governed same-site web crawler and structured content extractor."""
from __future__ import annotations
import hashlib, ipaddress, json, re, socket, sqlite3, time, uuid
from collections import deque
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse
import httpx

MAX_PAGE_BYTES = 1_500_000
USER_AGENT = "JPAI-ResearchBot/1.0 (+local research; respects robots.txt)"

class CrawlPolicyError(ValueError):
    """A URL or crawl request violates the safe collection policy."""

def validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CrawlPolicyError("Only absolute HTTP(S) URLs are supported")
    if parsed.username or parsed.password:
        raise CrawlPolicyError("URLs containing credentials are not allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise CrawlPolicyError("Local and private network destinations are not allowed")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise CrawlPolicyError("Hostname could not be resolved") from exc
    if not addresses:
        raise CrawlPolicyError("Hostname has no resolved addresses")
    for address in addresses:
        if not ipaddress.ip_address(address.split("%", 1)[0]).is_global:
            raise CrawlPolicyError("Private, loopback, link-local and reserved destinations are blocked")
    return urlunparse(parsed._replace(fragment=""))

class PageExtractor(HTMLParser):
    """Dependency-free HTML text and metadata extractor."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts=[]; self.text_parts=[]; self.links=[]; self.meta={}; self.headings=[]
        self._title=False; self._heading=None; self._skip=0
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag in {"script","style","noscript","svg","template"}: self._skip+=1
        if tag=="title": self._title=True
        if tag in {"h1","h2","h3"}: self._heading={"level":tag,"text":""}
        if tag=="a" and attrs.get("href"): self.links.append(attrs["href"])
        if tag=="meta":
            key=attrs.get("name") or attrs.get("property")
            if key and attrs.get("content"): self.meta[key.lower()]=attrs["content"][:1000]
    def handle_endtag(self, tag):
        if tag in {"script","style","noscript","svg","template"} and self._skip: self._skip-=1
        if tag=="title": self._title=False
        if self._heading and tag==self._heading["level"]:
            self.headings.append(self._heading); self._heading=None
    def handle_data(self, data):
        value=re.sub(r"\s+"," ",data).strip()
        if not value or self._skip: return
        if self._title: self.title_parts.append(value)
        else: self.text_parts.append(value)
        if self._heading: self._heading["text"] += (" " if self._heading["text"] else "")+value

class CrawlerStore:
    def __init__(self,path=None):
        import os
        self.path=Path(path or os.getenv("JPAI_DATABASE_PATH","data/jpai.sqlite3")).expanduser()
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS crawl_jobs(id TEXT PRIMARY KEY,seed_url TEXT NOT NULL,status TEXT NOT NULL,
              max_pages INTEGER NOT NULL,pages_crawled INTEGER NOT NULL DEFAULT 0,error TEXT,
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS crawled_pages(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT NOT NULL,
              url TEXT NOT NULL UNIQUE,canonical_url TEXT,domain TEXT NOT NULL,title TEXT NOT NULL DEFAULT '',
              description TEXT NOT NULL DEFAULT '',content TEXT NOT NULL DEFAULT '',headings_json TEXT NOT NULL DEFAULT '[]',
              metadata_json TEXT NOT NULL DEFAULT '{}',status_code INTEGER NOT NULL,content_type TEXT NOT NULL,
              content_hash TEXT NOT NULL,fetched_at TEXT NOT NULL,
              FOREIGN KEY(job_id) REFERENCES crawl_jobs(id) ON DELETE CASCADE);
            CREATE INDEX IF NOT EXISTS idx_crawled_pages_domain ON crawled_pages(domain);
            CREATE INDEX IF NOT EXISTS idx_crawled_pages_job ON crawled_pages(job_id);
            CREATE INDEX IF NOT EXISTS idx_crawled_pages_fetched ON crawled_pages(fetched_at DESC);
            """)
            columns={row[1] for row in db.execute("PRAGMA table_info(crawled_pages)").fetchall()}
            if "memory_id" not in columns:
                db.execute("ALTER TABLE crawled_pages ADD COLUMN memory_id INTEGER")
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=15); db.row_factory=sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA foreign_keys=ON"); return db
    def create_job(self,seed_url,max_pages):
        job_id=uuid.uuid4().hex; now=datetime.now(UTC).isoformat()
        with self._connect() as db:
            db.execute("INSERT INTO crawl_jobs(id,seed_url,status,max_pages,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                       (job_id,seed_url,"queued",max_pages,now,now))
        return self.get_job(job_id)
    def update_job(self,job_id,status,pages=None,error=None):
        now=datetime.now(UTC).isoformat()
        with self._connect() as db:
            if pages is None: db.execute("UPDATE crawl_jobs SET status=?,error=?,updated_at=? WHERE id=?",(status,error,now,job_id))
            else: db.execute("UPDATE crawl_jobs SET status=?,pages_crawled=?,error=?,updated_at=? WHERE id=?",(status,pages,error,now,job_id))
    def get_job(self,job_id):
        with self._connect() as db: row=db.execute("SELECT * FROM crawl_jobs WHERE id=?",(job_id,)).fetchone()
        return dict(row) if row else None
    def list_jobs(self,limit=30):
        with self._connect() as db: return [dict(r) for r in db.execute("SELECT * FROM crawl_jobs ORDER BY created_at DESC LIMIT ?",(limit,))]
    def save_page(self,job_id,url,domain,parsed,status_code,content_type,content_hash):
        now=datetime.now(UTC).isoformat()
        title=" ".join(parsed.title_parts)[:500]
        content=re.sub(r"\s+"," "," ".join(parsed.text_parts)).strip()[:200000]
        description=parsed.meta.get("description",parsed.meta.get("og:description",""))[:2000]
        with self._connect() as db:
            db.execute("""INSERT INTO crawled_pages(job_id,url,domain,title,description,content,headings_json,
              metadata_json,status_code,content_type,content_hash,fetched_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(url) DO UPDATE SET job_id=excluded.job_id,title=excluded.title,description=excluded.description,
              content=excluded.content,headings_json=excluded.headings_json,metadata_json=excluded.metadata_json,
              status_code=excluded.status_code,content_type=excluded.content_type,content_hash=excluded.content_hash,
              fetched_at=excluded.fetched_at""",
              (job_id,url,domain,title,description,content,json.dumps(parsed.headings[:80]),json.dumps(parsed.meta),
               status_code,content_type,content_hash,now))
    def list_pages(self,job_id=None,limit=50):
        with self._connect() as db:
            if job_id: rows=db.execute("SELECT id,job_id,url,domain,title,description,status_code,content_type,content_hash,fetched_at,memory_id FROM crawled_pages WHERE job_id=? ORDER BY fetched_at DESC LIMIT ?",(job_id,limit))
            else: rows=db.execute("SELECT id,job_id,url,domain,title,description,status_code,content_type,content_hash,fetched_at,memory_id FROM crawled_pages ORDER BY fetched_at DESC LIMIT ?",(limit,))
            return [dict(r) for r in rows]
    def search_pages(self,query,limit=20):
        terms=[t.lower() for t in re.findall(r"[\w-]{2,}",query)][:12]
        if not terms:return []
        with self._connect() as db: rows=db.execute("SELECT id,job_id,url,domain,title,description,content,fetched_at FROM crawled_pages ORDER BY fetched_at DESC LIMIT 1000").fetchall()
        ranked=[]
        for row in rows:
            item=dict(row); title=item["title"].lower(); content=item["content"].lower()
            score=sum(title.count(t)*4+content.count(t) for t in terms)
            if score:
                item["relevance"]=score; item["excerpt"]=item["content"][:420]; item.pop("content"); ranked.append(item)
        return sorted(ranked,key=lambda x:(x["relevance"],x["fetched_at"]),reverse=True)[:limit]
    def get_page(self,page_id):
        with self._connect() as db:
            row=db.execute("SELECT * FROM crawled_pages WHERE id=?",(page_id,)).fetchone()
        return dict(row) if row else None
    def mark_page_memory(self,page_id,memory_id):
        with self._connect() as db:
            db.execute("UPDATE crawled_pages SET memory_id=? WHERE id=?",(memory_id,page_id))
    def stats(self):
        with self._connect() as db:
            return {"pages_stored":db.execute("SELECT COUNT(*) FROM crawled_pages").fetchone()[0],
                    "domains_indexed":db.execute("SELECT COUNT(DISTINCT domain) FROM crawled_pages").fetchone()[0],
                    "jobs_total":db.execute("SELECT COUNT(*) FROM crawl_jobs").fetchone()[0]}

class WebCrawler:
    def __init__(self,store=None,delay_seconds=1.0):
        self.store=store or CrawlerStore(); self.delay_seconds=max(1.0,min(delay_seconds,10.0))
    def _get(self,client,url):
        safe=validate_public_url(url)
        response=client.get(safe,headers={"User-Agent":USER_AGENT,"Accept":"text/html,application/xhtml+xml"})
        if len(response.content)>MAX_PAGE_BYTES: raise CrawlPolicyError("Page exceeded response-size limit")
        return response
    def run(self,job_id):
        job=self.store.get_job(job_id)
        if not job:return
        self.store.update_job(job_id,"running",0)
        pages=0
        try:
            seed=validate_public_url(job["seed_url"]); parts=urlparse(seed)
            origin=(parts.scheme,parts.hostname,parts.port)
            queue=deque([(seed,0)]); seen=set()
            with httpx.Client(timeout=httpx.Timeout(15.0,connect=5.0),follow_redirects=False,max_redirects=0) as client:
                robots_url=urlunparse((parts.scheme,parts.netloc,"/robots.txt","","",""))
                robots=self._get(client,robots_url)
                disallowed=[]; active=False
                for line in (robots.text[:100000] if robots.status_code==200 else "").splitlines():
                    line=line.split("#",1)[0].strip()
                    if ":" not in line: continue
                    key,value=[x.strip() for x in line.split(":",1)]
                    if key.lower()=="user-agent": active=value=="*" or "JPAI-ResearchBot" in value
                    elif active and key.lower()=="disallow" and value: disallowed.append(value)
                while queue and pages<job["max_pages"]:
                    url,depth=queue.popleft(); url=validate_public_url(url); p=urlparse(url)
                    if (p.scheme,p.hostname,p.port)!=origin or url in seen: continue
                    seen.add(url)
                    if any(p.path.startswith(rule) for rule in disallowed): continue
                    time.sleep(self.delay_seconds)
                    response=self._get(client,url)
                    if response.status_code in {301,302,303,307,308} or response.status_code!=200: continue
                    content_type=response.headers.get("content-type","").lower()
                    if "text/html" not in content_type and "application/xhtml+xml" not in content_type: continue
                    digest=hashlib.sha256(response.content).hexdigest()
                    parser=PageExtractor(); parser.feed(response.text)
                    self.store.save_page(job_id,url,p.hostname or "",parser,200,content_type,digest)
                    pages+=1; self.store.update_job(job_id,"running",pages)
                    if depth<2:
                        for href in parser.links:
                            if href.startswith(("mailto:","javascript:","tel:","data:")): continue
                            candidate=urldefrag(urljoin(url,href))[0]; target=urlparse(candidate)
                            if target.hostname==origin[1] and target.scheme in {"http","https"}: queue.append((candidate,depth+1))
            self.store.update_job(job_id,"completed",pages)
        except (CrawlPolicyError,httpx.HTTPError,OSError,ValueError) as exc:
            self.store.update_job(job_id,"failed",pages,str(exc)[:500])
