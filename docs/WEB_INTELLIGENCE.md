# JPAI Web Intelligence & Continuous Source Monitoring

## Scope
Local-first public-web collection, HTML extraction, persistent source indexing, recurring monitoring and page-change history. The subsystem shares JPAI's configured SQLite database.

## Capabilities
- Same-origin discovery from a user-supplied HTTP(S) seed.
- HTML title, visible text, headings, links, meta and Open Graph descriptions.
- Bounded schema.org JSON-LD extraction (up to 25 blocks per page; 50 KB per block) with malformed or oversized blocks ignored.
- Structured metadata is retained separately from visible page text and is labelled unverified external metadata.
- Persistent crawl jobs and page records with normalized extracted-content SHA-256 fingerprints.
- Version history for each distinct extracted page state.
- Change events when normalized title, description or extracted text changes; volatile markup-only changes do not create a new content version.
- Persistent recurring schedules, pause/resume, due-time claiming and automatic execution while the JPAI API process is running.
- Atomic SQLite schedule claims to prevent duplicate runs across multiple local API workers sharing the same database.
- Local keyword search with title-weighted relevance.
- Explicit source-to-memory ingestion, retaining URL, timestamp and content fingerprint while labelling external content unverified.

## Scheduler behaviour
The FastAPI lifespan starts a local scheduler worker by default. It checks for due schedules every 30 seconds, claims up to three schedules per iteration, and runs each bounded crawl sequentially in a worker thread. Schedules are persisted across restarts. A newly created schedule is due immediately; subsequent runs follow the configured interval. The scheduler only runs while the JPAI API process is active.

Disable the scheduler with the environment variable JPAI_WEB_INTELLIGENCE_SCHEDULER_ENABLED=false. Minimum interval is 15 minutes; maximum interval is 30 days. Each scheduled crawl is limited to 1–50 pages.

## Safety limits
- HTTP(S) only; URL credentials rejected.
- Every DNS answer must be globally routable; private, loopback, link-local and reserved destinations are rejected.
- The resolved public IP is pinned for the actual socket connection, avoiding a second hostname resolution at connect time; HTTPS retains the original hostname for SNI and certificate validation.
- Redirects are not followed; crawling is restricted to the seed origin (scheme, hostname and effective port).
- Seed robots.txt Disallow rules for wildcard/JPAI-ResearchBot are honoured.
- Minimum one-second request delay; maximum 50 pages per job, depth two, 1.5 MB response and 15-second socket timeout.
- HTML only. No JavaScript execution, login sessions, paywall/CAPTCHA bypass or anti-bot evasion.
- Users remain responsible for site terms, copyright, privacy and lawful collection.

## API
- GET /api/v1/web-intelligence/status
- POST /api/v1/web-intelligence/jobs
- GET /api/v1/web-intelligence/jobs
- GET /api/v1/web-intelligence/jobs/{job_id}
- POST /api/v1/web-intelligence/schedules
- GET /api/v1/web-intelligence/schedules
- PATCH /api/v1/web-intelligence/schedules/{schedule_id} (pause/resume)
- GET /api/v1/web-intelligence/changes
- GET /api/v1/web-intelligence/pages
- GET /api/v1/web-intelligence/pages/{page_id}/versions
- GET /api/v1/web-intelligence/pages/{page_id}/structured-data
- GET /api/v1/web-intelligence/search?q=...
- POST /api/v1/web-intelligence/pages/{page_id}/remember

## Operational notes
- Scheduled crawling is local and does not require a hosted scheduler or external queue.
- A schedule's next-run time is advanced when it is claimed. If the process stops during a run, the next attempt occurs at the following interval; the job record preserves the attempt.
- Content-change detection compares normalized extracted title, description and text. It is a change detector, not a claim-verification engine.
- External content remains unverified. Hashes establish content identity, not truth or publisher credibility.

## Limitations and next research upgrades
JavaScript-rendered pages, PDF/document extraction, semantic/vector retrieval, multi-source claim corroboration, source credibility evaluation and notifications are not yet implemented. Structured-data extraction currently supports JSON-LD script blocks; it does not yet parse microdata or RDFa. Search remains lexical. Completed means the bounded crawl finished, not that claims are verified.
