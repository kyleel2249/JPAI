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
  {name:"JPAI-6.2 Ultra",role:"Flagship intelligence",tone:"ultra",summary:"Advanced reasoning · Architecture · Research · Synthesis"},
  {name:"JPAI-6.2 Pro",role:"Professional intelligence",tone:"pro",summary:"Engineering · Analysis · Verification · Execution"},
  {name:"JPAI-6 Mantra",role:"Efficient intelligence",tone:"mantra",summary:"Classification · Extraction · Automation · Transformation"}
];
function statusTime(value:string){const d=new Date(value);return Number.isNaN(d.getTime())?value:d.toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"});}
export default function CommandDashboard(p:Props){
 const activeAgents=p.agents.filter(a=>a.status==="active").length;
 const running=p.tasks.filter(t=>["running","in_progress","processing"].includes(t.status.toLowerCase())).length;
 const completed=p.tasks.filter(t=>t.status.toLowerCase()==="completed").length;
 const coreOk=!!p.health && ["ok","healthy","operational"].includes(p.health.status.toLowerCase());
 const runtimeOk=!!p.runtime?.available;
 const latest=p.events.slice(0,6);
 const quick:[string,string,string][]=[
  ["＋","New project","Directorates"],["◎","Select agents","Agents"],["▶","Run council","Agents"],
  ["⌕","Research web","Web Intelligence"],["▤","Open memory","Memory"],["▥","View analytics","Quality & Improvement"]
 ];
 const go=(name:string)=>p.onNavigate(name);
 return <div className="command-dashboard">
  <div className="command-head"><div><span className="command-kicker">JPAI · UNIFIED INTELLIGENCE</span><h2>Command Centre</h2><p>Plan · Analyse · Execute · Verify · Deliver</p></div><div className={coreOk?"command-status":"command-status warning"}><i/>{coreOk?"Core services operational":"Core status requires attention"}</div></div>
  <section className="model-trio">{profiles.map((m,i)=><article className={"ai-model-card "+m.tone} key={m.name}><div className="ai-orb"><span>{i===0?"✧":i===1?"⌘":"◈"}</span></div><div className="ai-model-copy"><small>{m.role}</small><h3>{m.name}</h3><p>{m.summary}</p><span className="model-readiness">{p.models.length?"Local model inventory detected":"Provider readiness not yet verified"}</span></div><button onClick={()=>go("Intelligence")}>View capability profile <b>→</b></button></article>)}</section>
  <section className="command-main-grid">
   <article className="command-panel execution-panel"><div className="command-panel-head"><div><small>ORCHESTRATION ENGINE</small><h3>Parallel execution</h3></div><span className="live-tag">{running?running+" RUNNING":"READY"}</span></div><div className="execution-stages">{["Specialist analysis","Peer review","Ultra synthesis","Pro verification"].map((x,i)=><div className="execution-stage" key={x}><span className="stage-node">{i+1}</span><b>{x}</b><small>{i===0?activeAgents+" active specialists":i===1?"Independent review":i===2?"Synthesis stage":"Verification stage"}</small></div>)}</div><div className="execution-stats"><span><b>{activeAgents}</b> active agents</span><span><b>{running}</b> running tasks</span><span><b>{completed}</b> completed tasks</span></div><div className="command-actions"><button className="primary-command-btn" onClick={()=>go("Agents")}>Open workforce →</button><button className="secondary-command-btn" onClick={p.onCouncil}>Run agent council</button></div></article>
   <article className="command-panel activity-panel"><div className="command-panel-head"><div><small>LIVE OPERATIONS</small><h3>Recent activity</h3></div><span className="live-dot">● LIVE DATA</span></div>{latest.length?latest.map(e=><div className="activity-line" key={e.id}><i/><time>{statusTime(e.created_at)}</time><span>{e.event_type.replace(/[._]/g," ")}</span></div>):<div className="empty-activity">No agent events have been recorded yet.</div>}<button className="panel-link" onClick={()=>go("Agents")}>View activity log →</button></article>
   <article className="command-panel memory-panel"><div className="command-panel-head"><div><small>KNOWLEDGE CORE</small><h3>Shared memory</h3></div><span className="memory-glyph">▤</span></div><strong className="memory-total">{p.memoryCount.toLocaleString()}</strong><small className="memory-caption">Persisted local memory records</small><div className="memory-meter"><i style={{width:p.memoryCount?"100%":"0%"}}/></div><p>Shared context is retrieved from the local memory service.</p><button className="panel-link" onClick={()=>go("Memory")}>Explore knowledge base →</button></article>
  </section>
  <section className="command-lower-grid">
   <article className="command-panel workspace-panel"><div className="command-panel-head"><div><small>WORKSPACE ACCESS</small><h3>Intelligence domains</h3></div><button className="panel-link" onClick={()=>go("Directorates")}>All domains →</button></div><div className="domain-list">{[["◈","Intelligence","Models and inference"],["◎","Specialist agents","Workforce and scorecards"],["⌕","Research engine","Web intelligence"],["⌘","Engineering","Build and delivery"]].map(([icon,name,desc])=><button key={name} onClick={()=>go(name==="Intelligence"?"Intelligence":name==="Specialist agents"?"Agents":name==="Research engine"?"Web Intelligence":"Directorates")}><i>{icon}</i><span><b>{name}</b><small>{desc}</small></span><strong>→</strong></button>)}</div></article>
   <article className="command-panel performance-panel"><div className="command-panel-head"><div><small>OBSERVED TELEMETRY</small><h3>Performance metrics</h3></div><span className="telemetry-label">LIVE COUNTS</span></div><div className="telemetry-grid"><div><b>{p.averageLatency===null?"—":p.averageLatency+"ms"}</b><small>Average model latency</small></div><div><b>{p.models.length}</b><small>Discovered local models</small></div><div><b>{p.agents.length}</b><small>Registered specialists</small></div><div><b>{p.runtime?.available?"ONLINE":"OFFLINE"}</b><small>Local inference runtime</small></div></div><p className="telemetry-note">Accuracy and reliability scores will appear here when validated evaluation samples are available. No synthetic performance figures are displayed.</p></article>
   <article className="command-panel system-panel"><div className="command-panel-head"><div><small>INFRASTRUCTURE</small><h3>System overview</h3></div><span className="system-icon">⌬</span></div>{[["JPAI API",p.health?.status??"Checking"],["Local runtime",runtimeOk?"Connected":"Unavailable"],["Agent workforce",activeAgents+" active"],["Memory service",p.memoryCount+" records"]].map(([k,v])=><div className="system-row" key={k}><span>{k}</span><b>{v}</b></div>)}<button className="panel-link" onClick={p.onRefresh}>Refresh system status ↻</button></article>
  </section>
  <section className="command-panel quick-panel"><div className="command-panel-head"><div><small>COMMAND SHORTCUTS</small><h3>Quick actions</h3></div></div><div className="quick-grid">{quick.map(([icon,label,target])=><button key={label} onClick={()=>go(target)}><i>{icon}</i><span>{label}</span></button>)}</div></section>
  {p.notice&&<div className="command-notice" role="status">{p.notice}</div>}
  <footer className="command-footer"><span>JPAI · COMMAND CENTRE</span><span>LOCAL-FIRST · GOVERNED · AUDITABLE</span></footer>
 </div>;
}
