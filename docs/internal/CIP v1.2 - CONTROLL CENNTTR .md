# CIP Mission Control — the professional-grade dashboard

Everything you've built (structure, history, tests, signals, audit, impact, local embeddings) now gets **one screen**. Design constraints honored: your Ryzen 3700U gets a **zero-dependency** dashboard — stdlib HTTP server + a single self-contained HTML file with hand-rolled SVG charts. No build step, no CDN, no Node, works offline. It's just another CIP binding (like MCP/CLI/HTTP), read-only, safe to run alongside the daemon.

---

## 1. `lib/cipkg/dashboard.py` (NEW — save to `~/.cip-global/lib/cipkg/`)

```python
"""CIP Mission Control — local, zero-dependency repo visualization.
Aggregates every CIP layer (structure, history, tests, signals, audit, impact)
into one screen. Read-only; safe alongside the daemon."""
import json, os, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from .base import repo_root
from .store import connect, get_meta
from . import indexer, retrieve, gitindex, runtime_adapters
from .stack import audit as stack_audit, nextjs as stack_nextjs, prisma as stack_prisma
from .stack import impact as stack_impact
from .stack.common import ensure as stack_ensure

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "static", "dashboard.html")

def _q(con, sql, args=()):
    return [dict(r) for r in con.execute(sql, args)]

def quadrant(con, cutoff):
    return _q(con, """
      SELECT f.path, f.lines,
        (SELECT COUNT(*) FROM commit_files cf JOIN commits c ON c.sha=cf.sha
           WHERE cf.path=f.path AND c.ts>=?) churn,
        (SELECT COUNT(*) FROM findings fd WHERE fd.path=f.path AND fd.status='open') openf,
        (SELECT COUNT(*) FROM symbols s WHERE s.path=f.path) syms
      FROM files f
      WHERE f.language IN ('typescript','javascript','python','rust','go')
      ORDER BY churn DESC, f.lines DESC LIMIT 300""", (cutoff,))

def velocity(con, weeks=12):
    out = [0] * weeks; now = time.time()
    for r in con.execute("SELECT ts FROM commits"):
        w = int((now - r["ts"]) / (7 * 86400))
        if 0 <= w < weeks: out[weeks - 1 - w] += 1
    return out

def briefing(root, con):
    """Auto-generated staff-engineer notes: derived risk/opportunity signals."""
    notes = []
    quad = quadrant(con, time.time() - 90 * 86400)
    hot_big = [r for r in quad if r["churn"] >= 3 and r["lines"] > 400]
    if hot_big:
        names = ", ".join(os.path.basename(r["path"]) for r in hot_big[:3])
        notes.append(("refactor", f"{len(hot_big)} files are HOT + LARGE (≥3 changes/90d, >400 lines): {names}. Split these before adding features."))
    unt = _q(con, "SELECT path,title FROM findings WHERE rule='QA-UNTESTED-HOT' AND status='open' LIMIT 1")
    if unt:
        notes.append(("risk", f"Load-bearing code without tests: {unt[0]['title']}. Add one test before touching it."))
    crit = _q(con, "SELECT path,title FROM findings WHERE severity='critical' AND status='open' LIMIT 1")
    if crit:
        notes.append(("blocker", f"Critical: {crit[0]['title']} ({crit[0]['path']}). Fix before any feature work."))
    hidden = _q(con, "SELECT COUNT(*) c FROM findings WHERE status='open' AND rule LIKE 'HIDDEN-%'")
    if hidden and hidden[0]["c"]:
        notes.append(("opportunity", f"{hidden[0]['c']} hidden assets (orphan routes/models/exports): buried features to revive or delete deliberately."))
    brk = runtime_adapters.broken(root)
    if brk.get("signals"):
        notes.append(("health", f"{len(brk['signals'])} failing test/type signals in 14 days — stabilize before refactoring."))
    co = _q(con, "SELECT src,dst FROM edges WHERE kind='co_change' LIMIT 1")
    if co:
        notes.append(("pattern", f"Files that always change together: {co[0]['src']} ↔ {co[0]['dst']}. Co-locate or extract a shared module."))
    if not notes:
        notes.append(("ok", "No dominant risks detected — good window for proactive refactoring or docs."))
    return [{"tag": t, "text": x} for t, x in notes]

def overview(root):
    con = connect(root); stack_ensure(con)
    stats = indexer.compute_stats(con)
    last = float(get_meta(con, "last_sync", 0) or 0)
    lag = time.time() - last if last else None
    sev = stack_audit.summarize(con)
    brk = runtime_adapters.broken(root)
    return {
        "repo": os.path.basename(os.path.abspath(root)),
        "stats": stats,
        "fresh": bool(lag is not None and lag < 300),
        "lag_s": round(lag, 1) if lag is not None else None,
        "embedder": get_meta(con, "embedder_name"),
        "severity": sev,
        "broken": {"signals": len(brk.get("signals", [])), "files": len(brk.get("files", []))},
        "velocity": velocity(con),
        "hotspots": gitindex.hotspots(root, k=8),
        "dirs": _q(con, """SELECT CASE WHEN instr(path,'/')>0 THEN substr(path,1,instr(path,'/')-1)
                           ELSE '(root)' END d, COUNT(*) files FROM files GROUP BY d
                           ORDER BY files DESC LIMIT 12"""),
        "quad": quadrant(con, time.time() - 90 * 86400)[:120],
        "briefing": briefing(root, con),
        "gate": {"ok": sev.get("critical", 0) == 0 and len(brk.get("signals", [])) == 0},
    }

def serve_dashboard(root=None, port=8790):
    root = root or repo_root()
    class H(BaseHTTPRequestHandler):
        def _send(self, obj=None, code=200, raw=None, ctype="application/json"):
            body = raw if raw is not None else json.dumps(obj, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            u = urlparse(self.path); p, qs = u.path, parse_qs(u.query)
            try:
                if p == "/":
                    with open(HTML, "rb") as f: return self._send(raw=f.read(), ctype="text/html")
                if p == "/api/overview":  return self._send(overview(root))
                if p == "/api/findings":  return self._send(stack_audit.findings(
                    root, severity=qs.get("severity", [None])[0],
                    rule=qs.get("rule", [None])[0], limit=200))
                if p == "/api/quickwins": return self._send(stack_audit.quick_wins(root, limit=12))
                if p == "/api/routes":    return self._send(stack_nextjs.list_routes(root))
                if p == "/api/models":    return self._send(stack_prisma.models_report(root))
                if p == "/api/search":    return self._send(retrieve.search(root, qs.get("q", [""])[0], k=8))
                if p == "/api/graph":     return self._send(retrieve.graph(root, qs.get("id", [""])[0]))
                if p == "/api/impact":    return self._send(stack_impact.impact(root, qs.get("target", [""])[0]))
                return self._send({"error": "not found"}, 404)
            except Exception as e:
                return self._send({"error": str(e)}, 500)
        def log_message(self, *a): pass
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"cip dashboard → http://127.0.0.1:{port}  (ctrl-c to stop)")
    srv.serve_forever()
```

---

## 2. `lib/cipkg/static/dashboard.html` (NEW — save to `~/.cip-global/lib/cipkg/static/`)

```html
<!doctype html><html><head><meta charset="utf-8">
<title>CIP Mission Control</title>
<style>
:root{--bg:#0b0f14;--card:#11161d;--line:#1f2630;--tx:#d7dde5;--mut:#7d8590;
--ok:#3fb950;--warn:#d29922;--hi:#f0883e;--crit:#f85149;--acc:#58a6ff;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);
font:13px/1.45 system-ui,Segoe UI,sans-serif}
header{display:flex;gap:10px;align-items:center;padding:10px 14px;
border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5}
header b{font:600 14px var(--mono)}
.badge{padding:3px 8px;border-radius:4px;font:600 11px var(--mono)}
.b-ok{background:#12261a;color:var(--ok)}.b-warn{background:#2a2110;color:var(--warn)}
.b-crit{background:#2d1416;color:var(--crit)}.b-acc{background:#10202f;color:var(--acc)}
#q{margin-left:auto;background:var(--card);border:1px solid var(--line);color:var(--tx);
padding:6px 10px;border-radius:6px;width:320px;font:12px var(--mono)}
#results{position:absolute;right:14px;top:44px;width:320px;background:var(--card);
border:1px solid var(--line);border-radius:6px;display:none;max-height:300px;overflow:auto}
#results div{padding:6px 10px;cursor:pointer;font:11px var(--mono)}
#results div:hover{background:var(--line)}
main{display:grid;grid-template-columns:repeat(12,1fr);gap:12px;padding:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;grid-column:span 4}
.card h2{margin:0 0 10px;font:600 11px var(--mono);letter-spacing:.08em;color:var(--mut);text-transform:uppercase}
.s6{grid-column:span 6}.s12{grid-column:span 12}
.kpis{display:flex;gap:14px;flex-wrap:wrap}
.kpi b{display:block;font:600 20px var(--mono)}.kpi span{color:var(--mut);font-size:11px}
.row{display:flex;gap:8px;align-items:baseline;padding:4px 0;border-top:1px solid var(--line);font-size:12px}
.row .mut{margin-left:auto;font:10px var(--mono);color:var(--mut);text-align:right}
.tag{padding:1px 6px;border-radius:3px;font:600 10px var(--mono);white-space:nowrap}
.t-crit{background:#2d1416;color:var(--crit)}.t-hi{background:#2a1a10;color:var(--hi)}
.t-warn{background:#2a2110;color:var(--warn)}.t-acc{background:#10202f;color:var(--acc)}
.t-ok{background:#12261a;color:var(--ok)}.t-mut{background:#1a2028;color:var(--mut)}
.mut{color:var(--mut)}pre{font:11px var(--mono);overflow:auto;max-height:180px}
.wsvg{width:100%}.dsvg{width:110px;float:left;margin-right:10px}
.big{font:700 20px var(--mono);fill:var(--tx)}.mutl{font:9px var(--mono);fill:var(--mut)}
.ql{stroke:var(--line);stroke-dasharray:3 3}.pt{fill:var(--acc);opacity:.75;cursor:pointer}
.pt-hot{fill:var(--crit);cursor:pointer}.spark{fill:none;stroke:var(--ok);stroke-width:2}
.gl{stroke:var(--line)}.gt{font:9px var(--mono);fill:var(--mut)}
.lg{display:inline-block;margin:2px 8px 2px 0;font:11px var(--mono)}
.lg i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:4px}
.tm{display:flex;height:64px;border-radius:6px;overflow:hidden;gap:2px}
.tmb{background:#1a2530;padding:6px;overflow:hidden;font:10px var(--mono);color:var(--mut);min-width:0}
.tmb b{display:block;color:var(--tx)}
.bar{height:8px;background:var(--line);border-radius:4px;margin:3px 0 8px}
.bar i{display:block;height:8px;border-radius:4px;background:var(--hi)}
#modal{display:none;position:fixed;inset:0;background:#0009;align-items:center;justify-content:center;z-index:9}
.mcard{background:var(--card);border:1px solid var(--line);border-radius:10px;
width:640px;max-height:80vh;overflow:auto;padding:16px}
.mhead{display:flex;gap:10px;align-items:center;margin-bottom:8px}
.mhead button{margin-left:auto;background:none;border:0;color:var(--mut);font-size:16px;cursor:pointer}
h4{margin:10px 0 4px;font:600 11px var(--mono);color:var(--mut)}
</style></head><body>
<header>
  <b id="repo">CIP</b>
  <span class="badge" id="gate"></span>
  <span class="badge" id="fresh"></span>
  <input id="q" placeholder="⌘K — search symbol/file, Enter = blast radius">
  <div id="results"></div>
</header>
<main>
  <section class="card s6"><h2>Ship-readiness</h2><div class="kpis" id="health"></div></section>
  <section class="card s6"><h2>Staff briefing</h2><div id="briefing"></div></section>
  <section class="card"><h2>Findings</h2><div id="donut"></div></section>
  <section class="card"><h2>Quick wins (fix first)</h2><div id="quickwins"></div></section>
  <section class="card"><h2>Hotspots (90d)</h2><div id="hotspots"></div></section>
  <section class="card s6"><h2>Risk quadrant — churn × size</h2><div id="quad"></div></section>
  <section class="card s6"><h2>Architecture</h2><div id="treemap"></div>
    <h4 style="margin-top:14px">Commit velocity (12 weeks)</h4><div id="velocity"></div></section>
  <section class="card"><h2>Test health</h2><div id="tests"></div></section>
  <section class="card"><h2>Hidden capacity</h2><div id="hidden"></div></section>
  <section class="card"><h2>Routes / Models</h2><div id="routes"></div></section>
  <section class="card s12"><h2>Dependency explorer — click nodes to walk the graph</h2>
    <div id="graph" class="mut">Search above or click any quadrant point to explore.</div>
    <div id="graphmeta" class="mut" style="font:10px var(--mono)"></div></section>
</main>
<div id="modal"></div>
<script>
const $=s=>document.querySelector(s), api=p=>fetch(p).then(r=>r.json());
const COL={critical:'var(--crit)',high:'var(--hi)',medium:'var(--warn)',low:'var(--mut)',info:'var(--acc)'};
let OV,FIND,QW,RT,MD;
const short=s=>{s=String(s).split('/').pop();return s.length>24?s.slice(0,22)+'…':s};
async function load(){
  OV=await api('/api/overview'); FIND=api('/api/findings'); QW=api('/api/quickwins');
  RT=api('/api/routes'); MD=api('/api/models');
  header(); health(); brief(); donut(); quickwins(); hotspots(); quad(); treemap(); velocity();
  tests(); hidden(); routes();
}
function header(){
  $('#repo').textContent='CIP // '+OV.repo;
  $('#gate').className='badge '+(OV.gate.ok?'b-ok':'b-crit');
  $('#gate').textContent=OV.gate.ok?'GATE PASS':'GATE FAIL';
  $('#fresh').className='badge '+(OV.fresh?'b-ok':'b-warn');
  $('#fresh').textContent=(OV.fresh?'fresh ':'stale ')+OV.lag_s+'s';
}
function health(){
  $('#health').innerHTML=[
    [OV.broken.signals,'failing signals',OV.broken.signals?'t-crit':'t-ok'],
    [OV.severity.critical,'criticals',OV.severity.critical?'t-crit':'t-ok'],
    [OV.stats.symbols,'symbols','t-acc'],[OV.stats.edges,'edges','t-acc'],
    [OV.stats.vectors,'vectors','t-acc'],
    [(OV.embedder||'none').replace('local:',''),'embedder','t-mut']]
   .map(k=>`<div class=kpi><b>${k[0]}</b><span class="tag ${k[2]}">${k[1]}</span></div>`).join('');
}
function brief(){
  const T={blocker:'t-crit',risk:'t-hi',refactor:'t-warn',health:'t-hi',opportunity:'t-acc',pattern:'t-acc',ok:'t-ok'};
  $('#briefing').innerHTML=OV.briefing.map(n=>
    `<div class=row><span class="tag ${T[n.tag]||'t-mut'}">${n.tag}</span><span>${n.text}</span></div>`).join('');
}
function donut(){
  const s=OV.severity.by_severity, ord=['critical','high','medium','low','info'];
  const tot=ord.reduce((a,k)=>a+(s[k]||0),0)||1, C=2*Math.PI*40; let a=0,seg='';
  ord.forEach(k=>{const v=s[k]||0; if(!v)return; const len=v/tot*C;
    seg+=`<circle r=40 cx=55 cy=55 fill=none stroke=${COL[k]} stroke-width=14
      stroke-dasharray="${len} ${C-len}" stroke-dashoffset="${-a}" transform="rotate(-90 55 55)"/>`; a+=len;});
  $('#donut').innerHTML=`<svg viewBox="0 0 110 110" class=dsvg>${seg}
    <text x=55 y=52 class=big text-anchor=middle>${OV.severity.open}</text>
    <text x=55 y=66 class=mutl text-anchor=middle>open</text></svg>`+
    ord.map(k=>`<span class=lg><i style=background:${COL[k]}></i>${k} ${s[k]||0}</span>`).join('');
}
async function quickwins(){
  const w=await QW;
  $('#quickwins').innerHTML=w.length?w.slice(0,7).map(f=>
    `<div class=row><span class="tag t-${f.effort=='trivial'?'ok':'warn'}">${f.effort}</span>
     <span>${f.title}</span><span class=mut>${f.rule} · ${short(f.path)}</span></div>`).join('')
   :'<p class=mut>no quick wins open — debt is under control</p>';
}
function hotspots(){
  const h=OV.hotspots; if(!h.length)return $('#hotspots').innerHTML='<p class=mut>run: cip git-index</p>';
  const m=Math.max(...h.map(x=>x.score),1);
  $('#hotspots').innerHTML=h.map(x=>`${short(x.path)}
    <div class=bar><i style="width:${x.score/m*100}%"></i></div>`).join('');
}
function quad(){
  const d=OV.quad; if(!d.length)return $('#quad').innerHTML='<p class=mut>no git history — run: cip git-index</p>';
  const W=560,H=300,P=34, xmax=Math.max(...d.map(r=>r.lines),1), ymax=Math.max(...d.map(r=>r.churn),1);
  const gx=P+(.5)*(W-2*P), gy=H-P-(Math.max(2,ymax/2)/ymax)*(H-2*P);
  const pts=d.map(r=>{const x=P+(r.lines/xmax)*(W-2*P), y=H-P-(r.churn/ymax)*(H-2*P);
    const hot=r.churn>=3&&r.lines>400;
    return `<circle cx=${x.toFixed(1)} cy=${y.toFixed(1)} r=${hot?5.5:3.5}
      class="${hot?'pt-hot':'pt'}" data-p="${r.path}"><title>${r.path}\n${r.lines}L · ${r.churn} changes · ${r.openf} findings</title></circle>`;}).join('');
  $('#quad').innerHTML=`<svg viewBox="0 0 ${W} ${H}" class=wsvg>
    <line x1=${gx} y1=${P} x2=${gx} y2=${H-P} class=ql/><line x1=${P} y1=${gy} x2=${W-P} y2=${gy} class=ql/>
    <text x=${W-P} y=${gy-6} class=mutl text-anchor=end>hot+small → safe refactor</text>
    <text x=${W-P} y=${H-10} class=mutl text-anchor=end style="fill:var(--crit)">hot+large → SPLIT FIRST</text>
    <text x=${P} y=${gy-6} class=mutl>stable+small</text>
    <text x=${P} y=${H-10} class=mutl>stable+large → modularize</text>${pts}</svg>`;
  $('#quad').querySelectorAll('circle').forEach(c=>c.onclick=()=>openTarget(c.dataset.p));
}
function treemap(){
  const d=OV.dirs;
  $('#treemap').innerHTML=`<div class=tm>${d.map(r=>
    `<div class=tmb style="flex:${r.files}" title="${r.d}: ${r.files} files"><span>${r.d}</span><b>${r.files}</b></div>`).join('')}</div>`;
}
function velocity(){
  const v=OV.velocity,W=260,H=56,m=Math.max(...v,1);
  const pts=v.map((n,i)=>`${(i/(v.length-1))*W},${H-6-(n/m)*(H-12)}`).join(' ');
  $('#velocity').innerHTML=`<svg viewBox="0 0 ${W} ${H}" class=wsvg style=max-width:280px>
    <polyline points="${pts}" class=spark/></svg>
    <span class=mut>${v.slice(-4).reduce((a,b)=>a+b,0)} commits / 4w · trend ${v.slice(-4).reduce((a,b)=>a+b,0)>=v.slice(0,4).reduce((a,b)=>a+b,0)?'↑':'↓'}</span>`;
}
async function tests(){
  const F=await FIND, unt=F.filter(f=>f.rule==='QA-UNTESTED-HOT');
  $('#tests').innerHTML=`<p class=mut>${OV.broken.signals} failing signals · ${unt.length} hot untested symbols</p>`+
    unt.slice(0,6).map(f=>`<div class=row><span class="tag t-warn">untested</span><span>${f.title}</span><span class=mut>${short(f.path)}</span></div>`).join('');
}
async function hidden(){
  const F=await FIND, h=F.filter(f=>f.rule.startsWith('HIDDEN'));
  const by={}; h.forEach(f=>by[f.rule]=(by[f.rule]||0)+1);
  $('#hidden').innerHTML=h.length?Object.entries(by).map(([k,v])=>
    `<div class=row><span class="tag t-acc">${k}</span><b>${v}</b><span class=mut>buried assets</span></div>`).join('')+
    h.slice(0,4).map(f=>`<div class=row><span>${f.title}</span><span class=mut>${short(f.path)}</span></div>`).join('')
   :'<p class=mut>nothing buried — clean surface area</p>';
}
async function routes(){
  const [rt,md]=await Promise.all([RT,MD]);
  const orph=rt.filter(r=>!r.referenced), om=(md.models||[]).filter(m=>m.orphan);
  $('#routes').innerHTML=`<p class=mut>${rt.length} routes (${orph.length} unreferenced) · ${(md.models||[]).length} models (${om.length} orphan)</p>`+
    orph.slice(0,4).map(r=>`<div class=row><span class="tag t-acc">route</span><span>${r.path}</span><span class=mut>${short(r.file)}</span></div>`).join('')+
    om.slice(0,4).map(m=>`<div class=row><span class="tag t-acc">model</span><span>${m.model}</span><span class=mut>0 usage</span></div>`).join('');
}
async function openTarget(t){
  impact(t); graph(t);
}
async function impact(t){
  const r=await api('/api/impact?target='+encodeURIComponent(t));
  if(r.error)return;
  $('#modal').innerHTML=`<div class=mcard><div class=mhead><b style="font:600 13px var(--mono)">${t}</b>
    <span class="badge ${r.risk=='high'?'b-crit':r.risk=='medium'?'b-warn':'b-ok'}">risk ${r.risk}</span>
    <button onclick="document.getElementById('modal').style.display='none'">✕</button></div>
    <p>${r.affected_count} files in blast radius · ${(r.routes_affected||[]).length} routes · ${(r.tests_to_run||[]).length} test files · ${r.open_findings_in_area} open findings in area</p>
    <ul>${(r.advice||[]).map(a=>`<li>${a}</li>`).join('')}</ul>
    <h4>Tests to run</h4><pre>${(r.tests_to_run||[]).join('\n')||'none — add one first'}</pre>
    <h4>Top affected files</h4><pre>${(r.affected_files||[]).slice(0,12).join('\n')}</pre></div>`;
  $('#modal').style.display='flex';
}
async function graph(id){
  const g=await api('/api/graph?id='+encodeURIComponent(id));
  if(!g||g.error||!g.nodes)return;
  const others=g.nodes.filter(n=>n!==g.root).slice(0,14);
  const W=900,H=260,cx=W/2,cy=H/2,R=100;
  let el=`<circle cx=${cx} cy=${cy} r=7 class=pt-hot/><text x=${cx} y=${cy-12} class=gt text-anchor=middle>${short(g.root)}</text>`;
  others.forEach((n,i)=>{const a=i/others.length*2*Math.PI,x=cx+R*2.2*Math.cos(a),y=cy+R*Math.sin(a);
    el+=`<line x1=${cx} y1=${cy} x2=${x} y2=${y} class=gl/>
      <circle cx=${x} cy=${y} r=5 class=pt data-id="${n}"><title>${n}</title></circle>
      <text x=${x+8} y=${y+3} class=gt>${short(n)}</text>`;});
  $('#graph').innerHTML=`<svg viewBox="0 0 ${W} ${H}" class=wsvg>${el}</svg>`;
  $('#graphmeta').textContent='root: '+g.root;
  $('#graph').querySelectorAll('[data-id]').forEach(c=>c.onclick=()=>openTarget(c.dataset.id));
}
const q=$('#q');
q.addEventListener('input',async()=>{
  if(q.value.length<2)return $('#results').style.display='none';
  const r=await api('/api/search?q='+encodeURIComponent(q.value));
  $('#results').innerHTML=r.map(x=>`<div data-t="${x.symbol||x.path}">${short(x.path)} <span class=mut>${x.lines[0]}–${x.lines[1]}</span></div>`).join('');
  $('#results').style.display='block';
  $('#results').querySelectorAll('div').forEach(d=>d.onclick=()=>{$('#results').style.display='none';openTarget(d.dataset.t);});
});
q.addEventListener('keydown',e=>{
  if(e.key==='Enter'){const f=$('#results div');if(f)f.click();}
  if(e.key==='Escape')$('#results').style.display='none';
});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();q.focus();}});
load(); setInterval(load,30000);
</script></body></html>
```

---

## 3. CLI wiring (two small patches to `~/.cip-global/lib/cipkg/cli.py`)

**Patch 1** — after the `gate` parser line, add:

```python
    dp = sub.add_parser("dashboard", help="professional-grade local visualization")
    dp.add_argument("--port", type=int, default=8790)
```

**Patch 2** — after the `gate` dispatch block, add:

```python
    elif a.cmd == "dashboard":
        from .dashboard import serve_dashboard
        serve_dashboard(root, port=a.port)
```

---

## 4. Run it

```powershell
cd C:\path\to\any\repo
cip dashboard
# → open http://127.0.0.1:8790
```

Works on **every** repo you've `cip init`-ed. Auto-refreshes every 30s. Ctrl+K to search; click any quadrant point or graph node to get its **blast radius** instantly.

---

## 5. How to read it like a top engineer

| Panel | The question a staff engineer asks | The move it triggers |
|---|---|---|
| **Gate / Ship-readiness** | "Can anything ship today?" | Red = stop feature work, stabilize |
| **Staff briefing** | "What would I flag in an architecture review?" | Auto-derived heuristics (hot+large, untested load-bearers, co-change) |
| **Risk quadrant** | "Where is change concentrating *and* complexity?" | Bottom-right = split before adding features |
| **Quick wins** | "What's the highest-leverage 30 minutes?" | Trivial-effort criticals first |
| **Hotspots + velocity** | "Is churn trending into stable code?" | ↑ trend into hotspots = incoming breakage |
| **Test health** | "What load-bearing code would fail silently?" | One test per hot untested symbol |
| **Hidden capacity** | "What are we carrying that nobody uses?" | Revive deliberately or delete |
| **Dependency explorer** | "If I touch this, what breaks?" | Blast radius before the edit, not after |

That's the full loop: **see risk → confirm blast radius → fix the highest-leverage thing → gate stays green.**