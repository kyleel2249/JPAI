import { useEffect, useState } from "react";

type Health = { status: string; service: string; environment: string; mode: string };
type Model = { id: string; provider: string; display_name: string; family?: string; parameter_size?: string; capabilities: string[] };
const api = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runtime, setRuntime] = useState<{ available: boolean; version?: string } | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [selected, setSelected] = useState("");
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    fetch(`${api}/api/v1/health`).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() as Promise<Health>; }).then(setHealth).catch(e => setError(e instanceof Error ? e.message : "Connection failed"));
    fetch(`${api}/api/v1/intelligence/runtime`).then(r => r.json()).then(setRuntime).catch(() => setRuntime({ available: false }));
  }, []);

  async function discoverModels() {
    setBusy(true); setNotice("");
    try {
      const response = await fetch(`${api}/api/v1/intelligence/models/discover`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Model discovery failed");
      setModels(data.models); setSelected(data.models[0]?.id ?? ""); setNotice(`${data.count} local model(s) discovered`);
    } catch (e) { setNotice(e instanceof Error ? e.message : "Local model discovery failed"); }
    finally { setBusy(false); }
  }

  async function runInference() {
    if (!selected || !prompt.trim()) return;
    setBusy(true); setNotice(""); setAnswer("");
    try {
      const response = await fetch(`${api}/api/v1/intelligence/infer`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model: selected, prompt }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Inference failed");
      setAnswer(data.response); setNotice(`Completed in ${data.duration_ms} ms`);
    } catch (e) { setNotice(e instanceof Error ? e.message : "Inference failed"); }
    finally { setBusy(false); }
  }

  return <main className="shell">
    <header className="topbar"><div className="brand-mark">J</div><div><strong>JPAI</strong><span>INTELLIGENCE WORKSPACE</span></div><div className="topbar-tag">PHASE 02 · LOCAL INTELLIGENCE</div></header>
    <section className="hero"><p className="eyebrow">PERSONAL · PROFESSIONAL · ENTERPRISE</p><h1>Intelligence, <em>orchestrated.</em></h1><p className="intro">A local-first intelligence platform for a coordinated digital workforce — with private inference, model choice and governed execution.</p>
      <div className="status-panel"><div className={health ? "status-dot online" : "status-dot"}/><div><strong>{health ? "JPAI core connected" : error ? "Core service unavailable" : "Connecting to local core…"}</strong><span>{health ? `${health.service} · ${health.mode} · ${health.environment}` : error ?? "Checking backend health"}</span></div><span className="status-label">{health ? "OPERATIONAL" : "CORE API"}</span></div>
    </section>
    <section className="intelligence-panel"><div className="section-head"><div><p className="eyebrow">LOCAL MODEL OPERATIONS</p><h2>Intelligence runtime</h2></div><span className={runtime?.available ? "runtime-pill live" : "runtime-pill"}>{runtime?.available ? `OLLAMA ONLINE · ${runtime.version ?? "READY"}` : "RUNTIME NOT CONNECTED"}</span></div>
      <p className="panel-copy">Discover locally installed models and run private text inference. JPAI does not download models or send prompts to external providers.</p>
      <div className="controls"><button onClick={discoverModels} disabled={busy}>{busy ? "Working…" : "Discover local models"}</button><select aria-label="Select local model" value={selected} onChange={e => setSelected(e.target.value)}><option value="">Choose a discovered model</option>{models.map(model => <option key={model.id} value={model.id}>{model.display_name} · {model.provider}</option>)}</select></div>
      <textarea aria-label="Inference prompt" value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Enter a prompt for your selected local model…" rows={4}/>
      <div className="controls"><button className="secondary" onClick={runInference} disabled={busy || !selected || !prompt.trim()}>Run local inference</button><span className="notice" role="status">{notice}</span></div>
      {answer && <div className="answer"><strong>MODEL RESPONSE</strong><p>{answer}</p></div>}
      {models.length > 0 && <p className="model-count">{models.length} model(s) in the current discovery result</p>}
    </section>
    <section className="grid"><article><span className="number">01</span><h2>Local-first core</h2><p>Core services run locally without mandatory external API credentials.</p></article><article><span className="number">02</span><h2>Capability routing</h2><p>Model profiles and capability-aware selection prepare the foundation for specialist agents.</p></article><article><span className="number">03</span><h2>Governed autonomy</h2><p>Permissions, approvals and auditable actions remain foundational.</p></article></section>
    <footer><span>JPAI · LOCAL INTELLIGENCE</span><span>BUILT FOR TRUSTED EXECUTION</span></footer>
  </main>;
}
