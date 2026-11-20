import { useEffect, useState } from "react";

type Health = { status: string; service: string; environment: string; mode: string };

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const base = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
    fetch(`${base}/api/v1/health`)
      .then((response) => {
        if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`);
        return response.json() as Promise<Health>;
      })
      .then(setHealth)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Connection failed"));
  }, []);

  return (
    <main className="shell">
      <header className="topbar"><div className="brand-mark">J</div><div><strong>JPAI</strong><span>INTELLIGENCE WORKSPACE</span></div><div className="topbar-tag">PHASE 01 · FOUNDATION</div></header>
      <section className="hero">
        <p className="eyebrow">PERSONAL · PROFESSIONAL · ENTERPRISE</p>
        <h1>Intelligence, <em>orchestrated.</em></h1>
        <p className="intro">A local-first foundation for a coordinated digital workforce — built around modular intelligence, trusted execution and human-directed autonomy.</p>
        <div className="status-panel"><div className={health ? "status-dot online" : "status-dot"} /><div><strong>{health ? "Core service connected" : error ? "Core service unavailable" : "Connecting to local core…"}</strong><span>{health ? `${health.service} · ${health.mode} · ${health.environment}` : error ?? "Checking local backend health"}</span></div><span className="status-label">{health ? "OPERATIONAL" : "LOCAL API"}</span></div>
      </section>
      <section className="grid">
        <article><span className="number">01</span><h2>Local-first core</h2><p>Core services are designed to run locally without mandatory external API credentials.</p></article>
        <article><span className="number">02</span><h2>Modular intelligence</h2><p>Specialist capabilities will connect through versioned interfaces and clear domain boundaries.</p></article>
        <article><span className="number">03</span><h2>Governed autonomy</h2><p>Permissions, approvals and auditable actions are foundational — not afterthoughts.</p></article>
      </section>
      <footer><span>JPAI · CORE ARCHITECTURE</span><span>BUILDING THE FOUNDATION</span></footer>
    </main>
  );
}
