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
