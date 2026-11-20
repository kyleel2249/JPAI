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
type EvidenceSource = {
  id: number; source_type: "web" | "document"; title: string; locator: string;
  domain: string; source_hash: string; observed_at: string; trust: string;
  relevance: number; excerpt: string;
};
type EvidenceLink = {
  id: number; stance: "supports" | "contradicts" | "context"; excerpt: string;
  source_title?: string; source_locator?: string; source_domain?: string;
  source_trust?: string; source_hash: string;
};
type EvidenceClaim = {
  id: number; statement: string; context: string; created_at: string;
  evidence: EvidenceLink[]; support_count: number; contradiction_count: number;
  context_count: number; source_origins: number; evidence_balance: string;
  verification_status: string;
};
type ResearchDocument = {
  id: number; filename: string; file_type: string; content_hash: string;
  extracted_chars: number; page_count?: number | null; uploaded_at: string;
  memory_id?: number | null; relevance?: number; excerpt?: string;
};

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
  const [documents, setDocuments] = useState<ResearchDocument[]>([]);
  const [documentQuery, setDocumentQuery] = useState("");
  const [documentResults, setDocumentResults] = useState<ResearchDocument[]>([]);
  const [evidenceQuery, setEvidenceQuery] = useState("");
  const [evidenceSources, setEvidenceSources] = useState<EvidenceSource[]>([]);
  const [evidenceClaims, setEvidenceClaims] = useState<EvidenceClaim[]>([]);
  const [claimStatement, setClaimStatement] = useState("");
  const [claimContext, setClaimContext] = useState("");
  const [selectedSource, setSelectedSource] = useState<EvidenceSource | null>(null);
  const [selectedClaimId, setSelectedClaimId] = useState<number | null>(null);
  const [evidenceStance, setEvidenceStance] = useState<"supports" | "contradicts" | "context">("supports");
  const [evidenceExcerpt, setEvidenceExcerpt] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [query, setQuery] = useState("");
  const [stats, setStats] = useState({
    pages_stored: 0, domains_indexed: 0, jobs_total: 0,
    schedules_total: 0, changes_detected: 0, versions_stored: 0,
    pages_with_structured_data: 0, documents_stored: 0, document_chars_indexed: 0,
  });
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      const [status, jobData, pageData, scheduleData, changeData, documentData, claimData] = await Promise.all([
        request("/api/v1/web-intelligence/status"),
        request("/api/v1/web-intelligence/jobs"),
        request("/api/v1/web-intelligence/pages"),
        request("/api/v1/web-intelligence/schedules"),
        request("/api/v1/web-intelligence/changes?limit=30"),
        request("/api/v1/web-intelligence/documents"),
        request("/api/v1/web-intelligence/evidence/claims"),
      ]);
      setStats(status);
      setJobs(jobData.items ?? []);
      setPages(pageData.items ?? []);
      setSchedules(scheduleData.items ?? []);
      setChanges(changeData.items ?? []);
      setDocuments(documentData.items ?? []);
      setEvidenceClaims(claimData.items ?? []);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to load web intelligence");
    }
  }

  useEffect(() => {
    void refresh();
    const poll = window.setInterval(() => { void refresh(); }, 30000);
    return () => window.clearInterval(poll);
  }, []);

  async function uploadDocument(file?: File) {
    if (!file) return;
    setBusy(true);
    setNotice("");
    try {
      const form = new FormData();
      form.append("file", file);
      const data = await request("/api/v1/web-intelligence/documents", {
        method: "POST", body: form,
      });
      setNotice("Document indexed: " + data.document.filename + " · " + data.document.extracted_chars + " extracted characters.");
      await refresh();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Document extraction failed");
    } finally {
      setBusy(false);
    }
  }

  async function searchEvidenceSources() {
    setBusy(true);
    try {
      const data = await request("/api/v1/web-intelligence/evidence/sources?q=" + encodeURIComponent(evidenceQuery));
      setEvidenceSources(data.items ?? []);
      setNotice(data.count + " evidence source(s) found · " + data.method);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Evidence source search failed");
    } finally {
      setBusy(false);
    }
  }

  async function createClaim() {
    if (claimStatement.trim().length < 10) return;
    setBusy(true);
    try {
      const data = await request("/api/v1/web-intelligence/evidence/claims", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ statement: claimStatement, context: claimContext }),
      });
      setClaimStatement("");
      setClaimContext("");
      setSelectedClaimId(data.id);
      setNotice("Research claim recorded. Attach source excerpts before drawing conclusions.");
      await refresh();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Claim could not be recorded");
    } finally {
      setBusy(false);
    }
  }

  async function linkEvidence() {
    if (!selectedSource || !selectedClaimId || evidenceExcerpt.trim().length < 20) return;
    setBusy(true);
    try {
      await request("/api/v1/web-intelligence/evidence/claims/" + selectedClaimId + "/evidence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_type: selectedSource.source_type, source_id: selectedSource.id,
          stance: evidenceStance, excerpt: evidenceExcerpt,
        }),
      });
      setNotice("Verbatim source excerpt linked to the claim with provenance.");
      setEvidenceExcerpt("");
      await refresh();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Evidence link was rejected");
    } finally {
      setBusy(false);
    }
  }

  async function searchDocuments() {
    if (documentQuery.trim().length < 2) return;
    setBusy(true);
    try {
      const data = await request("/api/v1/web-intelligence/documents/search?q=" + encodeURIComponent(documentQuery));
      setDocumentResults(data.items ?? []);
      setNotice(data.count + " matching document(s) · " + data.method);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Document search failed");
    } finally {
      setBusy(false);
    }
  }

  async function rememberDocument(documentId: number) {
    setBusy(true);
    try {
      const data = await request("/api/v1/web-intelligence/documents/" + documentId + "/remember", {
        method: "POST",
      });
      setNotice(data.status === "already_in_memory"
        ? "Document is already in JPAI memory."
        : "Document added to JPAI memory with provenance.");
      await refresh();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Document memory ingestion failed");
    } finally {
      setBusy(false);
    }
  }

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
      <article className="metric"><span>DOCUMENTS INDEXED</span><strong>{stats.documents_stored ?? 0}</strong><small>{(stats.document_chars_indexed ?? 0).toLocaleString()} extracted characters</small></article>
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

    <div className="section-title"><div><span className="eyebrow">DOCUMENT INTELLIGENCE</span><h2>Research files & knowledge extraction</h2></div>
      <span className="muted">{documents.length} indexed documents</span></div>
    <div className="overview-grid">
      <article className="panel">
        <h3>Import research documents</h3>
        <p>Upload PDF, DOCX, TXT, Markdown or CSV files. JPAI extracts text locally, stores a SHA-256 fingerprint and indexes the content for research.</p>
        <div className="field"><label>Choose document · maximum 20 MB</label>
          <input type="file" accept=".pdf,.docx,.txt,.md,.csv,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown,text/csv"
            disabled={busy} onChange={(event) => {
              const file = event.target.files?.[0];
              void uploadDocument(file);
              event.target.value = "";
            }}/></div>
        <p className="muted">PDF extraction is text-based; scanned image-only PDFs require OCR, which is not yet enabled. Encrypted documents are rejected.</p>
      </article>
      <article className="panel">
        <h3>Search document knowledge</h3>
        <p>Search extracted document text with local weighted keyword relevance.</p>
        <div className="search-row">
          <input value={documentQuery} onChange={(event) => setDocumentQuery(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Enter") void searchDocuments(); }}
            placeholder="Search PDFs, reports and documents…"/>
          <button className="outline-btn" disabled={busy || documentQuery.trim().length < 2} onClick={() => void searchDocuments()}>Search</button>
        </div>
        {documentResults.map((item) => <article className="memory-item" key={item.id}>
          <div><span className="eyebrow">{item.file_type.toUpperCase()} · RELEVANCE {item.relevance}</span>
            <h4>{item.filename}</h4><p>{item.excerpt}</p>
            <small>SHA-256 · {item.content_hash.slice(0, 24)}…</small>
            <button className="text-btn" disabled={busy || !!item.memory_id} onClick={() => void rememberDocument(item.id)}>
              {item.memory_id ? "✓ Added to JPAI memory" : "Add to JPAI memory"}</button>
          </div></article>)}
      </article>
    </div>
    <div className="panel task-list">{documents.length ? documents.map((document) =>
      <article className="task-row" key={document.id}><div className="task-main">
        <b>{document.filename}</b><small>{document.file_type.toUpperCase()} · {document.extracted_chars.toLocaleString()} characters
          {document.page_count ? " · " + document.page_count + " pages" : ""}</small>
        <small>Imported {new Date(document.uploaded_at).toLocaleString()}</small>
        <small>SHA-256 · {document.content_hash}</small>
        <span className="task-state">{document.memory_id ? "IN JPAI MEMORY" : "INDEXED LOCALLY"}</span>
      </div><button className="outline-btn" disabled={busy || !!document.memory_id}
        onClick={() => void rememberDocument(document.id)}>
        {document.memory_id ? "Added to memory" : "Add to memory"}</button></article>
    ) : <p className="muted">Uploaded research documents will appear here with extraction details and source fingerprints.</p>}</div>

    <div className="section-title"><div><span className="eyebrow">EVIDENCE & KNOWLEDGE INTELLIGENCE</span><h2>Cross-source evidence workspace</h2></div>
      <span className="muted">{evidenceClaims.length} research claims</span></div>
    <div className="overview-grid">
      <article className="panel">
        <h3>Record a research claim</h3>
        <p>Claims are researcher-authored. Record a precise statement, then attach exact excerpts from indexed web pages or uploaded documents.</p>
        <div className="field"><label>Claim / proposition</label>
          <textarea rows={3} value={claimStatement} onChange={(event) => setClaimStatement(event.target.value)}
            placeholder="State one testable proposition…"/></div>
        <div className="field"><label>Context and scope (optional)</label>
          <textarea rows={2} value={claimContext} onChange={(event) => setClaimContext(event.target.value)}
            placeholder="Time period, geography, definitions or caveats…"/></div>
        <button className="gold-btn" disabled={busy || claimStatement.trim().length < 10}
          onClick={() => void createClaim()}>Record research claim</button>
        <div className="divider-line"/>
        <h3>Find source evidence</h3>
        <div className="search-row">
          <input value={evidenceQuery} onChange={(event) => setEvidenceQuery(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Enter") void searchEvidenceSources(); }}
            placeholder="Search all crawled pages and documents…"/>
          <button className="outline-btn" disabled={busy} onClick={() => void searchEvidenceSources()}>Search</button>
        </div>
        {evidenceSources.map((source) => <article className="memory-item" key={source.source_type + ":" + source.id}>
          <div><span className="eyebrow">{source.source_type.toUpperCase()} · {source.domain || "UPLOADED DOCUMENT"}</span>
            <h4>{source.title || source.locator}</h4><p>{source.excerpt}</p>
            <small>{source.trust} · SHA-256 {source.source_hash.slice(0, 18)}…</small>
            <button className="text-btn" disabled={busy} onClick={() => {
              setSelectedSource(source);
              setEvidenceExcerpt(source.excerpt.replace(/^…|…$/g, "").trim());
            }}>Select source & use excerpt</button>
          </div></article>)}
      </article>
      <article className="panel">
        <h3>Attach selected evidence</h3>
        <p className="muted">{selectedSource ? selectedSource.title : "Select a source from the search results."}</p>
        <div className="field"><label>Research claim</label>
          <select value={selectedClaimId ?? ""} onChange={(event) => setSelectedClaimId(event.target.value ? Number(event.target.value) : null)}>
            <option value="">Choose a recorded claim</option>
            {evidenceClaims.map((claim) => <option key={claim.id} value={claim.id}>#{claim.id} · {claim.statement.slice(0, 90)}</option>)}
          </select></div>
        <div className="field"><label>Evidence relationship</label>
          <select value={evidenceStance} onChange={(event) => setEvidenceStance(event.target.value as "supports" | "contradicts" | "context")}>
            <option value="supports">Supports the claim</option>
            <option value="contradicts">Contradicts the claim</option>
            <option value="context">Provides context</option>
          </select></div>
        <div className="field"><label>Exact source excerpt (20–1,200 characters)</label>
          <textarea rows={5} value={evidenceExcerpt} onChange={(event) => setEvidenceExcerpt(event.target.value)}
            placeholder="Select a source to populate an excerpt, then edit only if the text remains verbatim…"/></div>
        <button className="gold-btn" disabled={busy || !selectedSource || !selectedClaimId || evidenceExcerpt.trim().length < 20}
          onClick={() => void linkEvidence()}>Link source evidence</button>
        <p className="muted">JPAI validates that the excerpt occurs in the selected source. A citation match validates provenance, not the truth of the claim.</p>
      </article>
    </div>
    <div className="panel task-list">{evidenceClaims.length ? evidenceClaims.map((claim) =>
      <article className="task-row" key={claim.id}><div className="task-main">
        <b>CLAIM #{claim.id} · {claim.statement}</b>
        {claim.context && <small>{claim.context}</small>}
        <span className="task-state">{claim.evidence_balance.replace(/_/g, " ").toUpperCase()} · NOT VERIFIED</span>
        <small>{claim.support_count} supporting · {claim.contradiction_count} contradicting · {claim.context_count} contextual · {claim.source_origins} source origins</small>
        {claim.evidence.map((item) => <div className="council-contribution" key={item.id}>
          <b>{item.stance.toUpperCase()} · {item.source_title || item.source_locator}</b>
          <small>{item.source_domain || item.source_trust} · SHA-256 {item.source_hash.slice(0, 16)}…</small>
          <p>“{item.excerpt}”</p>
          {item.source_locator?.startsWith("http") && <a href={item.source_locator} target="_blank" rel="noreferrer">{item.source_locator}</a>}
        </div>)}
      </div><button className="outline-btn" onClick={() => setSelectedClaimId(claim.id)}>Select claim</button></article>
    ) : <p className="muted">No research claims recorded yet. Create a claim and attach source excerpts to begin a traceable evidence file.</p>}</div>

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
