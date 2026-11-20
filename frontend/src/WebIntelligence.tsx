import { useEffect, useState } from "react";

type Job = {
  id: string; seed_url: string; status: string; max_pages: number;
  pages_crawled: number; error?: string | null; created_at: string;
};
type Page = {
  id: number; job_id: string; url: string; domain: string; title: string;
  description: string; status_code: number; content_hash: string;
  fetched_at: string; memory_id?: number | null;
};
type SearchResult = Page & { relevance: number; excerpt: string };
type Schedule = {
  id: number; seed_url: string; interval_minutes: number; max_pages: number;
  enabled: number; next_run_at: string; last_run_at?: string | null; last_job_id?: string | null;
};
type Change = {
  id: number; url: string; domain: string; title: string; summary: string;
  change_type: string; detected_at: string; previous_hash: string; current_hash: string;
};
type Version = {
  id: number; title: string; content_hash: string; fetched_at: string; job_id: string;
};
type StructuredRecord = Record<string, unknown>;
type StructuredData = { count: number; items: StructuredRecord[]; trust: string };

const api = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const key = import.meta.env.VITE_JPAI_API_KEY ?? "";

async function request(path: string, init: RequestInit = {}) {
  const response = await fetch(api + path, {
    ...init,
    headers: {
      ...(init.headers as Record<string, string> | undefined),
      ...(key ? { "X-JPAI-API-Key": key } : {}),
    },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail ?? "Web intelligence request failed");
  return data;
}

export default function WebIntelligence() {
  const [url, setUrl] = useState("");
  const [maxPages, setMaxPages] = useState(10);
  const [intervalMinutes, setIntervalMinutes] = useState(60);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [pages, setPages] = useState<Page[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [changes, setChanges] = useState<Change[]>([]);
  const [versions, setVersions] = useState<Record<number, Version[]>>({});
  const [structuredData, setStructuredData] = useState<Record<number, StructuredData>>({});
  const [results, setResults] = useState<SearchResult[]>([]);
  const [query, setQuery] = useState("");
  const [stats, setStats] = useState({
    pages_stored: 0, domains_indexed: 0, jobs_total: 0,
    schedules_total: 0, changes_detected: 0, versions_stored: 0,
    pages_with_structured_data: 0,
  });
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      const [status, jobData, pageData, scheduleData, changeData] = await Promise.all([
        request("/api/v1/web-intelligence/status"),
        request("/api/v1/web-intelligence/jobs"),
        request("/api/v1/web-intelligence/pages"),
        request("/api/v1/web-intelligence/schedules"),
        request("/api/v1/web-intelligence/changes?limit=30"),
      ]);
      setStats(status);
      setJobs(jobData.items ?? []);
      setPages(pageData.items ?? []);
      setSchedules(scheduleData.items ?? []);
      setChanges(changeData.items ?? []);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to load web intelligence");
    }
  }

  useEffect(() => {
    void refresh();
    const poll = window.setInterval(() => { void refresh(); }, 30000);
    return () => window.clearInterval(poll);
  }, []);

  async function start() {
    if (!url.trim()) return;
    setBusy(true);
    setNotice("");
    try {
      const data = await request("/api/v1/web-intelligence/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seed_url: url, max_pages: maxPages }),
      });
      setNotice(data.message);
      setUrl("");
      await refresh();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Crawl could not start");
    } finally {
      setBusy(false);
    }
  }

  async function createSchedule() {
    if (!url.trim()) return;
    setBusy(true);
    setNotice("");
    try {
      const data = await request("/api/v1/web-intelligence/schedules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          seed_url: url, interval_minutes: intervalMinutes, max_pages: maxPages,
        }),
      });
      setNotice(data.message);
      setUrl("");
      await refresh();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Monitoring schedule could not be created");
    } finally {
      setBusy(false);
    }
  }

  async function toggleSchedule(schedule: Schedule) {
    setBusy(true);
    try {
      await request("/api/v1/web-intelligence/schedules/" + schedule.id, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !schedule.enabled }),
      });
      setNotice(schedule.enabled ? "Monitoring paused." : "Monitoring resumed.");
      await refresh();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Schedule update failed");
    } finally {
      setBusy(false);
    }
  }

  async function loadVersions(pageId: number) {
    try {
      const data = await request("/api/v1/web-intelligence/pages/" + pageId + "/versions");
      setVersions((current) => ({ ...current, [pageId]: data.items ?? [] }));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to load page history");
    }
  }

  async function loadStructuredData(pageId: number) {
    try {
      const data = await request("/api/v1/web-intelligence/pages/" + pageId + "/structured-data");
      setStructuredData((current) => ({ ...current, [pageId]: data }));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to load structured metadata");
    }
  }

  async function remember(pageId: number) {
    setBusy(true);
    try {
      const data = await request("/api/v1/web-intelligence/pages/" + pageId + "/remember", {
        method: "POST",
      });
      setNotice(data.status === "already_in_memory"
        ? "Source is already in JPAI memory."
        : "Source added to JPAI memory for specialist retrieval.");
      await refresh();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Memory ingestion failed");
    } finally {
      setBusy(false);
    }
  }

  async function search() {
    if (query.trim().length < 2) return;
    setBusy(true);
    try {
      const data = await request("/api/v1/web-intelligence/search?q=" + encodeURIComponent(query));
      setResults(data.items ?? []);
      setNotice(data.count + " matching stored page(s) · " + data.method);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }

  return <>
    <div className="section-title">
      <div><span className="eyebrow">RESEARCH DIRECTORATE · WEB INTELLIGENCE</span>
        <h2>Discovery, crawling & extraction</h2></div>
      <button className="outline-btn" onClick={() => void refresh()}>↻ Refresh</button>
    </div>
    <div className="metrics">
      <article className="metric"><span>STORED PAGES</span><strong>{stats.pages_stored}</strong><small>Extracted HTML documents</small></article>
      <article className="metric"><span>DOMAINS INDEXED</span><strong>{stats.domains_indexed}</strong><small>Source domains</small></article>
      <article className="metric"><span>MONITORING PLANS</span><strong>{stats.schedules_total}</strong><small>Persistent schedules</small></article>
      <article className="metric"><span>CHANGES DETECTED</span><strong>{stats.changes_detected}</strong><small>Content-change events</small></article>
      <article className="metric"><span>STRUCTURED SOURCES</span><strong>{stats.pages_with_structured_data}</strong><small>Pages with JSON-LD metadata</small></article>
    </div>
    <div className="overview-grid">
      <article className="panel">
        <h3>Launch a governed crawl</h3>
        <p>Enter a public website URL. JPAI discovers same-site links, checks robots.txt and extracts page text and metadata.</p>
        <div className="field"><label>Seed website URL</label>
          <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/research"/></div>
        <div className="field"><label>Maximum pages (1–50)</label>
          <input type="number" min={1} max={50} value={maxPages}
            onChange={(event) => setMaxPages(Math.max(1, Math.min(50, Number(event.target.value) || 1)))}/></div>
        <button className="gold-btn" disabled={busy || !url.trim()} onClick={() => void start()}>
          {busy ? "Working…" : "Start one-time crawl →"}</button>
        <div className="divider-line"/>
        <h3>Continuous source monitoring</h3>
        <p>Save a recurring schedule. The local JPAI service checks for updates while its API process is running.</p>
        <div className="field"><label>Repeat interval (15 minutes to 30 days)</label>
          <input type="number" min={15} max={43200} value={intervalMinutes}
            onChange={(event) => setIntervalMinutes(Math.max(15, Math.min(43200, Number(event.target.value) || 15)))}/></div>
        <button className="outline-btn" disabled={busy || !url.trim()} onClick={() => void createSchedule()}>
          Create monitoring schedule</button>
        <p className="muted">DNS-pinned public destinations, same-origin scope, no redirects, robots.txt rules, one-second minimum request delay, depth two and bounded response size.</p>
        {notice && <p className="notice" role="status">{notice}</p>}
      </article>
      <article className="panel">
        <h3>Search collected intelligence</h3>
        <p>Search locally stored page titles, descriptions and extracted text. Source URL and content fingerprint are retained.</p>
        <div className="search-row">
          <input value={query} onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Enter") void search(); }}
            placeholder="Search extracted research…"/>
          <button className="outline-btn" disabled={busy || query.trim().length < 2} onClick={() => void search()}>Search</button>
        </div>
        {results.map((item) => <article className="memory-item" key={item.id}><div>
          <span className="eyebrow">{item.domain} · RELEVANCE {item.relevance}</span>
          <h4>{item.title || "Untitled page"}</h4><p>{item.description || item.excerpt}</p>
          <a href={item.url} target="_blank" rel="noreferrer">{item.url}</a>
        </div></article>)}
      </article>
    </div>

    <div className="section-title"><div><span className="eyebrow">AUTOMATED COLLECTION</span><h2>Monitoring schedules</h2></div>
      <span className="muted">{schedules.length} saved plans</span></div>
    <div className="panel task-list">{schedules.length ? schedules.map((schedule) =>
      <article className="task-row" key={schedule.id}><div className="task-main">
        <b>{schedule.seed_url}</b>
        <small>Every {schedule.interval_minutes} minutes · up to {schedule.max_pages} pages</small>
        <small>Next run: {new Date(schedule.next_run_at).toLocaleString()}</small>
        <small>{schedule.last_run_at ? "Last run: " + new Date(schedule.last_run_at).toLocaleString() : "Awaiting first run"}</small>
        <span className="task-state">{schedule.enabled ? "ACTIVE" : "PAUSED"}</span>
      </div><button className="outline-btn" disabled={busy} onClick={() => void toggleSchedule(schedule)}>
        {schedule.enabled ? "Pause" : "Resume"}</button></article>
    ) : <p className="muted">No recurring monitoring plans have been configured.</p>}</div>

    <div className="section-title"><div><span className="eyebrow">INTELLIGENCE WATCH</span><h2>Detected source changes</h2></div>
      <span className="muted">{changes.length} recent events</span></div>
    <div className="panel task-list">{changes.length ? changes.map((change) =>
      <article className="task-row" key={change.id}><div className="task-main">
        <b>{change.title || change.url}</b><small>{change.domain} · {new Date(change.detected_at).toLocaleString()}</small>
        <p>{change.summary}</p><small>Previous: {change.previous_hash.slice(0, 16)}…</small>
        <small>Current: {change.current_hash.slice(0, 16)}…</small>
        <a href={change.url} target="_blank" rel="noreferrer">{change.url}</a>
      </div></article>
    ) : <p className="muted">No content changes detected yet. Changes appear after a monitored page differs from its previous extracted version.</p>}</div>

    <div className="section-title"><div><span className="eyebrow">COLLECTION CONTROL</span><h2>Crawl jobs</h2></div>
      <span className="muted">{jobs.length} recent jobs</span></div>
    <div className="panel task-list">{jobs.length ? jobs.map((job) =>
      <article className="task-row" key={job.id}><div className="task-main">
        <b>{job.seed_url}</b><small>{job.id} · {job.pages_crawled}/{job.max_pages} pages · {new Date(job.created_at).toLocaleString()}</small>
        <span className="task-state">{job.status.toUpperCase()}</span>{job.error && <p>{job.error}</p>}
      </div><button className="outline-btn" onClick={() => void refresh()}>Refresh status</button></article>
    ) : <p className="muted">No crawl jobs yet.</p>}</div>

    <div className="section-title"><div><span className="eyebrow">SOURCE INVENTORY</span><h2>Recently extracted pages</h2></div>
      <span className="muted">{pages.length} shown · {stats.versions_stored} versions</span></div>
    <div className="panel task-list">{pages.length ? pages.map((page) =>
      <article className="task-row" key={page.id}><div className="task-main">
        <b>{page.title || "Untitled page"}</b><small>{page.domain} · {new Date(page.fetched_at).toLocaleString()}</small>
        <p>{page.description}</p><small>SHA-256 · {page.content_hash}</small>
        <a href={page.url} target="_blank" rel="noreferrer">{page.url}</a>
        <div className="task-actions">
          <button className="text-btn" onClick={() => void loadVersions(page.id)}>View version history</button>
          <button className="text-btn" onClick={() => void loadStructuredData(page.id)}>View structured data</button>
          <button className="text-btn" disabled={busy || !!page.memory_id} onClick={() => void remember(page.id)}>
            {page.memory_id ? "✓ Added to JPAI memory" : "Add source to JPAI memory"}</button>
        </div>
        {structuredData[page.id] && <div className="memory-list">
          <b>Structured metadata ({structuredData[page.id].count})</b>
          <small>Schema.org JSON-LD · unverified external metadata</small>
          {structuredData[page.id].items.map((record, index) => {
            const types = record["@type"];
            const typeLabel = Array.isArray(types) ? types.join(", ") : String(types ?? "Structured object");
            const headline = String(record["headline"] ?? record["name"] ?? record["description"] ?? "No display summary");
            return <p key={index}><b>{typeLabel}</b> · {headline.slice(0, 240)}</p>;
          })}
        </div>}
                {versions[page.id] && <div className="memory-list"><b>Version history ({versions[page.id].length})</b>
          {versions[page.id].map((version) => <p key={version.id}>
            {new Date(version.fetched_at).toLocaleString()} · {version.title || "Untitled"} · {version.content_hash.slice(0, 20)}…
          </p>)}</div>}
      </div></article>
    ) : <p className="muted">Collected pages will appear here with source provenance.</p>}</div>
  </>;
}
