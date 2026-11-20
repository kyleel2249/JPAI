# JPAI Web Intelligence & Research Engine

## Scope
Local-first persistent same-site crawler and HTML extraction pipeline integrated with FastAPI and the configured SQLite database.

## Capabilities
- Same-origin discovery from a user-supplied HTTP(S) seed.
- HTML title, visible text, headings, links, meta and Open Graph descriptions.
- Persistent jobs and page records with SHA-256 content fingerprints and fetch timestamps.
- Local keyword search with title-weighted relevance.
- Job status, page inventory and collection metrics.

## Safety limits
- HTTP(S) only; URL credentials rejected.
- Hostnames are resolved and every returned IP must be globally routable. Private, loopback, link-local and reserved destinations are blocked.
- Redirects are not followed; crawling is restricted to the seed host and port.
- Seed robots.txt Disallow rules for wildcard/JPAI-ResearchBot are honored.
- Minimum one-second request delay; maximum 50 pages, depth two, 1.5 MB response and 15-second timeout.
- HTML only. No JavaScript execution, login sessions, paywall/CAPTCHA bypass or anti-bot evasion.
- Users remain responsible for site terms, copyright, privacy and lawful collection.

## API
- GET /api/v1/web-intelligence/status
- POST /api/v1/web-intelligence/jobs (202; background crawl)
- GET /api/v1/web-intelligence/jobs
- GET /api/v1/web-intelligence/jobs/{job_id}
- GET /api/v1/web-intelligence/pages
- GET /api/v1/web-intelligence/search?q=...

## Limitations
Search is lexical, not semantic. JavaScript-rendered pages, images, PDFs, schema.org extraction and full-text indexing are future enhancements. Completed means the bounded crawl finished, not that claims are verified. URL, fetch timestamp and content hash provide source provenance for downstream corroboration.
