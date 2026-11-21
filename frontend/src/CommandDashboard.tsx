type Model = { id:string; provider:string; display_name:string; capabilities:string[]; metrics?:{samples?:number;successes?:number;avg_latency_ms?:number} };
type Agent = { id:string; name:string; domain:string; status:string };
type Task = { id:number; title:string; status:string; agent_id:string };
type Event = { id:number; event_type:string; created_at:string; task_id:number|null; agent_id:string|null };
type Props = {
  health:{status:string;service:string;environment:string;mode:string}|null;
  runtime:{available:boolean;version?:string}|null;
  models:Model[]; agents:Agent[]; tasks:Task[]; events:Event[]; memoryCount:number;
  averageLatency:number|null; notice:string; onNavigate:(page:string)=>void;
  onRefresh:()=>void; onDiscover:()=>void; onCouncil:()=>void;
};
const profiles = [
  {name:"JPAI-6.2 Ultra",role:"Flagship intelligence",tone:"ultra",symbol:"✧",summary:"Advanced reasoning · Architecture · Research · Synthesis"},
  {name:"JPAI-6.2 Pro",role:"Professional intelligence",tone:"pro",symbol:"⌘",summary:"Engineering · Analysis · Verification · Specialist work"},
  {name:"JPAI-6 Mantra",role:"Efficient intelligence",tone:"mantra",symbol:"◈",summary:"Classification · Extraction · Transformation · High-volume tasks"}
];
function statusTime(value:string){const d=new Date(value);return Number.isNaN(d.getTime())?value:d.toLocaleString([], {month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});}
function label(value:string){return value.replace(/[._]/g," ").replace(/\b\w/g,c=>c.toUpperCase());}
export default function CommandDashboard(p:Props){
 const activeAgents=p.agents.filter(a=>a.status==="active").length;
 const running=p.tasks.filter(t=>["running","in_progress","processing"].includes(t.status.toLowerCase())).length;
 const queued=p.tasks.filter(t=>t.status.toLowerCase()==="queued").length;
 const completed=p.tasks.filter(t=>t.status.toLowerCase()==="completed").length;
 const failed=p.tasks.filter(t=>t.status.toLowerCase()==="failed").length;
 const coreOk=!!p.health && ["ok","healthy","operational"].includes(p.health.status.toLowerCase());
 const runtimeOk=!!p.runtime?.available;
 const latest=p.events.slice(0,7);
 const discovered=p.models.length;
 const go=(name:string)=>p.onNavigate(name);
 const serviceStatus=coreOk&&runtimeOk?"SYSTEM PARTIALLY READY":"SYSTEM NEEDS ATTENTION";
 return <div className="command-dashboard">
  <section className="command-hero">
   <div className="hero-copy"><div className="command-kicker"><span className="kicker-pulse"/> JPAI · UNIFIED INTELLIGENCE PLATFORM</div><h1>Command <em>Centre</em></h1><p>One intelligence workspace. A coordinated specialist workforce. A shared knowledge core.</p><div className="hero-actions"><button className="command-primary" onClick={()=>go("Agents")}>Open AI workforce <span>↗</span></button><button className="command-secondary" onClick={p.onRefresh}>Refresh live systems <span>↻</span></button></div></div>
   <div className="hero-core" aria-label="JPAI intelligence core"><div className="core-orbit orbit-one"/><div className="core-orbit orbit-two"/><div className="core-orbit orbit-three"/><div className="core-brain"><span>✧</span><small>JPAI</small></div><div className="core-caption">INTELLIGENCE CORE</div></div>
   <div className="hero-foot"><span className={coreOk?"status-indicator good":"status-indicator warn"}><i/>{coreOk?"API CORE HEALTHY":"API CORE UNVERIFIED"}</span><span className={runtimeOk?"status-indicator good":"status-indicator warn"}><i/>{runtimeOk?"LOCAL INFERENCE CONNECTED":"LOCAL INFERENCE UNAVAILABLE"}</span><span className="hero-mode">LOCAL-FIRST · GOVERNED</span></div>
  </section>
  <section className="command-metrics" aria-label="Live system metrics">
   <article className="command-metric"><span className="metric-icon">◈</span><small>LOCAL MODELS</small><strong>{discovered}</strong><span>{discovered?"Discovered on this device":"No models discovered"}</span></article>
   <article className="command-metric"><span className="metric-icon">◎</span><small>ACTIVE SPECIALISTS</small><strong>{activeAgents}<sup>/{p.agents.length}</sup></strong><span>Registered agent workforce</span></article>
   <article className="command-metric"><span className="metric-icon">▤</span><small>SHARED MEMORY</small><strong>{p.memoryCount.toLocaleString()}</strong><span>Persisted local records</span></article>
   <article className="command-metric"><span className="metric-icon">⇄</span><small>RUNNING TASKS</small><strong>{running}</strong><span>{queued} queued · {completed} completed</span></article>
   <article className="command-metric"><span className="metric-icon">⌁</span><small>AVG MODEL LATENCY</small><strong>{p.averageLatency===null?"—":p.averageLatency}<sup>{p.averageLatency===null?"":"ms"}</sup></strong><span>Observed inference telemetry</span></article>
  </section>
  <section className="command-model-section">
   <div className="command-section-heading"><div><small>UNIFIED MODEL FABRIC</small><h2>Three intelligence identities. One coordinated system.</h2></div><button className="command-text-link" onClick={()=>go("Model Fabric")}>Explore model fabric ↗</button></div>
   <div className="command-model-grid">{profiles.map((m,i)=><article className={"command-model-card "+m.tone} key={m.name}><div className="model-card-top"><div className="model-emblem">{m.symbol}</div><span className="model-identity">JPAI MODEL IDENTITY</span></div><small>{m.role}</small><h3>{m.name}</h3><p>{m.summary}</p><div className="model-card-bottom"><span>{discovered} local model{discovered===1?"":"s"} discovered</span><button onClick={()=>go("Model Fabric")}>Capability profile <b>→</b></button></div></article>)}</div>
  </section>
  <section className="command-main-grid">
   <article className="command-panel execution-panel"><div className="command-panel-head"><div><small>PARALLEL ORCHESTRATION</small><h3>Specialist execution</h3></div><span className={running?"command-live-tag":"command-idle-tag"}><i/>{running?running+" RUNNING":"NO ACTIVE RUNS"}</span></div><div className="execution-flow">{["Specialist analysis","Independent peer review","Ultra synthesis","Pro verification"].map((x,i)=><div className="execution-step" key={x}><span>{String(i+1).padStart(2,"0")}</span><div><b>{x}</b><small>{["Capability-matched agents","Separate review contributions","Consolidated intelligence","Verification pass"][i]}</small></div>{i<3&&<i className="step-connector"/>}</div>)}</div><div className="execution-footer"><span><b>{activeAgents}</b> active agents</span><span><b>{running}</b> running</span><span><b>{failed}</b> failed</span></div><div className="command-actions"><button className="command-primary" onClick={()=>go("Agents")}>Manage workforce ↗</button><button className="command-secondary" onClick={p.onCouncil}>Open council workspace</button></div></article>
   <article className="command-panel activity-panel"><div className="command-panel-head"><div><small>OPERATIONAL EVENT STREAM</small><h3>Recent agent activity</h3></div><span className="event-count">{p.events.length} events</span></div>{latest.length?<div className="activity-feed">{latest.map(e=><div className="activity-line" key={e.id}><span className="activity-node"/><div><b>{label(e.event_type)}</b><small>{statusTime(e.created_at)}{e.task_id!==null?" · Task #"+e.task_id:""}</small></div></div>)}</div>:<div className="command-empty"><span>◌</span><b>No activity recorded yet</b><small>Agent events will appear here as the workforce performs tasks.</small></div>}<button className="command-text-link" onClick={()=>go("Agents")}>View workforce and task log ↗</button></article>
   <article className="command-panel memory-panel"><div className="command-panel-head"><div><small>SHARED KNOWLEDGE CORE</small><h3>Persistent memory</h3></div><span className="panel-symbol">▤</span></div><div className="memory-orbit"><div><strong>{p.memoryCount.toLocaleString()}</strong><small>MEMORY RECORDS</small></div></div><p>Specialists can retrieve relevant local context from JPAI's shared SQLite memory service.</p><div className="memory-facts"><span>Storage <b>Local SQLite</b></span><span>Retrieval <b>Lexical relevance</b></span></div><button className="command-text-link" onClick={()=>go("Memory")}>Explore memory & knowledge ↗</button></article>
  </section>
  <section className="command-lower-grid">
   <article className="command-panel performance-panel"><div className="command-panel-head"><div><small>OBSERVED TELEMETRY</small><h3>System performance</h3></div><span className="telemetry-label">LIVE COUNTS</span></div><div className="telemetry-grid"><div><b>{p.averageLatency===null?"—":p.averageLatency+" ms"}</b><small>Average model latency</small></div><div><b>{discovered}</b><small>Discovered local models</small></div><div><b>{p.agents.length}</b><small>Registered specialists</small></div><div><b>{p.runtime?.available?"CONNECTED":"UNAVAILABLE"}</b><small>Local inference runtime</small></div></div><p className="telemetry-note">Accuracy and reliability scores appear only when validated evaluation samples are available. No synthetic performance figures are displayed.</p><button className="command-text-link" onClick={()=>go("Intelligence")}>Inspect model telemetry ↗</button></article>
   <article className="command-panel system-panel"><div className="command-panel-head"><div><small>INFRASTRUCTURE STATUS</small><h3>System overview</h3></div><span className="panel-symbol">⌬</span></div>{[["JPAI API",p.health?.status??"Checking"],["Local runtime",runtimeOk?"Connected":"Unavailable"],["Agent workforce",activeAgents+" active / "+p.agents.length],["Memory service",p.memoryCount+" records"]].map(([k,v])=><div className="system-row" key={k}><span>{k}</span><b>{v}</b></div>)}<div className="system-health-note"><i/>{serviceStatus}</div><button className="command-text-link" onClick={p.onRefresh}>Refresh infrastructure ↻</button></article>
  </section>
  <section className="command-panel quick-panel"><div className="command-panel-head"><div><small>COMMAND SHORTCUTS</small><h3>Launch a workspace</h3></div><span className="muted-command">DIRECT ACCESS</span></div><div className="quick-grid">{[["✧","Intelligence","Intelligence"],["◎","AI agents","Agents"],["◈","Model fabric","Model Fabric"],["⌕","Web research","Web Intelligence"],["▤","Shared memory","Memory"],["✓","Quality control","Quality & Improvement"],["◉","Reality Studio","Reality Studio"],["⌘","Directorates","Directorates"]].map(([icon,label,target])=><button key={target} onClick={()=>go(target)}><i>{icon}</i><span>{label}</span><b>↗</b></button>)}</div></section>
  {p.notice&&<div className="command-notice" role="status">{p.notice}</div>}
  <footer className="command-footer"><span>JPAI · INTELLIGENCE COMMAND CENTRE</span><span>LOCAL-FIRST · GOVERNED · AUDITABLE</span></footer>
 </div>;
}
