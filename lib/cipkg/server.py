"""CIP v1.0 server: JSON-RPC over HTTP + MCP stdio. Full tool surface."""
import json, os, sys, time
from . import retrieve, indexer, summarize, gitindex, runtime_adapters, router
from .stack import audit as stack_audit, impact as stack_impact
from .stack import nextjs as stack_nextjs, prisma as stack_prisma
from .base import repo_root, load_config, cip_dir
from .store import connect, get_meta

TOOLS = [
    {"name": "search", "description": "Hybrid search (lexical+semantic+graph), reranked, with intent routing.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer"}}, "required": ["query"]}},
    {"name": "symbol", "description": "Find symbol definitions with relationship counts.",
     "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "graph", "description": "Traverse relationships around a symbol or file.",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "direction": {"type": "string", "enum": ["in", "out", "both"]}, "depth": {"type": "integer"}}, "required": ["id"]}},
    {"name": "context", "description": "Token-budgeted context pack: code + summary + relations + tests + failures.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "symbol": {"type": "string"}, "budget": {"type": "integer"}}}},
    {"name": "summary", "description": "Repo/directory/file summary (hash-cached, self-invalidating).",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
    {"name": "map", "description": "Hierarchical repository map: subsystems, sizes, hotspots.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "describe", "description": "Self-introspection: entity/relationship ontology.",
     "inputSchema": {"type": "object", "properties": {"entity": {"type": "string"}}}},
    {"name": "broken", "description": "Current failures: failing tests + type errors (last 14 days).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "hotspots", "description": "Files with the most recent change activity.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "history", "description": "Git history for a path.",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "route", "description": "Intent analysis: best CIP operations for a request.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "route_for_agent", "description": "Agent-aware routing with capability-scoped tool names and confidence scores.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "git_index", "description": "Refresh commit index (modified_by, co_change, hotspots).",
     "inputSchema": {"type": "object", "properties": {"depth": {"type": "integer"}}}},
    {"name": "index_status", "description": "Index freshness, coverage and stats.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "audit", "description": "Run the TS/Next/Prisma/SQLite audit rules; returns finding counts.",
     "inputSchema": {"type": "object", "properties": {"refresh": {"type": "boolean"}}}},
    {"name": "findings", "description": "Query open findings by severity/rule/path.",
     "inputSchema": {"type": "object", "properties": {"severity": {"type": "string"}, "rule": {"type": "string"}, "path": {"type": "string"}, "limit": {"type": "integer"}}}},
    {"name": "refactors", "description": "Top quick-win refactors ranked by severity/effort.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "impact", "description": "Blast radius for a file/symbol, or for a git diff with `ref`.",
     "inputSchema": {"type": "object", "properties": {"target": {"type": "string"}, "ref": {"type": "string"}, "depth": {"type": "integer"}}}},
    {"name": "routes", "description": "Next.js route inventory with referenced/orphan status.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "models", "description": "Prisma model usage report incl. orphan detection.",
     "inputSchema": {"type": "object", "properties": {}}},
]

def index_status(root):
    con = connect(root)
    stats = indexer.compute_stats(con)
    last = float(get_meta(con, "last_sync", 0) or 0)
    lag = time.time() - last if last else None
    return {**stats,
            "commits": con.execute("SELECT COUNT(*) c FROM commits").fetchone()["c"],
            "signals": con.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"],
            "summaries": con.execute("SELECT COUNT(*) c FROM summaries").fetchone()["c"],
            "last_sync": last,
            "lag_s": round(lag, 1) if lag is not None else None,
            "fresh": bool(lag is not None and lag < 300),
            "embedder": get_meta(con, "embedder_name"),
            "fts": get_meta(con, "fts") == "1",
            "schema_version": get_meta(con, "schema_version")}

def describe(root, entity=None):
    p = os.path.join(cip_dir(root), "ontology.json")
    ont = json.load(open(p)) if os.path.exists(p) else {}
    if not entity: return ont
    out = {}
    if entity in ont.get("entities", {}):
        out["entity"] = ont["entities"][entity]
    rels = {k: v for k, v in ont.get("relationships", {}).items()
            if entity in (str(v.get("from", "")) + str(v.get("to", "")))}
    if rels: out["relationships"] = rels
    return out or {"error": f"unknown entity: {entity}"}

def _next_ops(name, res):
    ops = []
    ids = []
    if name == "symbol":
        ids = [s["id"] for s in res.get("symbols", [])[:3]]
    elif name == "search":
        ids = [r["symbol"] for r in res.get("results", []) if r.get("symbol")][:3]
        rt = res.get("route", {})
        if rt.get("intent") == "architecture":
            ops.append("map()")
        elif rt.get("intent") == "health":
            ops.append("broken()")
    for sid in ids:
        ops.append(f"graph(id='{sid}', direction='both')")
        ops.append(f"context(symbol='{sid}')")
    if name == "graph":
        ops += [f"context(symbol='{n}')" for n in res.get("nodes", [])[1:3]]
    if name == "broken":
        for f in res.get("files", [])[:2]:
            ops.append(f"summary(path='{f['path']}')")
    if name == "map":
        ops.append("summary(path='<subsystem>')")
    if name == "audit":
        ops += ["refactors()", "findings(severity='critical')"]
    if name == "findings":
        ops += [f"impact(target='{f['path']}')" for f in res.get("findings", [])[:2]]
    if name == "impact":
        ops += ["broken()", "context(query='<planned change>')"]
    if name == "models":
        ops += ["findings(rule='DB-MISSING-INDEX')"]
    return ops[:6]

def call_tool(root, cfg, name, args):
    args = args or {}
    try:
        if name == "search":
            q = args.get("query", "")
            res = {"results": retrieve.search(root, q, k=int(args.get("k", 10))),
                   "route": router.route(q)}
        elif name == "symbol":
            res = {"symbols": retrieve.find_symbol(root, args.get("name", ""))}
        elif name == "graph":
            res = retrieve.graph(root, args.get("id"), args.get("direction", "both"),
                                 depth=int(args.get("depth", 1)))
        elif name == "context":
            res = retrieve.context(root, args.get("query"), args.get("symbol"), args.get("budget"))
        elif name == "summary":
            res = summarize.summary(root, args.get("path"))
        elif name == "map":
            res = summarize.map_(root)
        elif name == "describe":
            res = describe(root, args.get("entity"))
        elif name == "broken":
            res = runtime_adapters.broken(root)
        elif name == "hotspots":
            res = {"hotspots": gitindex.hotspots(root)}
        elif name == "history":
            res = retrieve.history(root, args.get("path", ""))
        elif name == "route":
            res = router.route(args.get("query", ""))
        elif name == "route_for_agent":
            res = router.route_for_agent(args.get("query", ""))
        elif name == "git_index":
            res = gitindex.git_index(root, depth=int(args.get("depth", cfg["git"]["depth"])))
        elif name == "audit":
            res = stack_audit.audit(root, refresh=bool(args.get("refresh", True)))
        elif name == "findings":
            res = {"findings": stack_audit.findings(root, severity=args.get("severity"),
                   rule=args.get("rule"), path=args.get("path"),
                   limit=int(args.get("limit", 100)))}
        elif name == "refactors":
            res = {"quick_wins": stack_audit.quick_wins(root)}
        elif name == "impact":
            res = (stack_impact.impact_diff(root, ref=args["ref"]) if args.get("ref")
                   else stack_impact.impact(root, target=args.get("target", ""),
                                            depth=int(args.get("depth", 2))))
        elif name == "routes":
            res = {"routes": stack_nextjs.list_routes(root)}
        elif name == "models":
            res = stack_prisma.models_report(root)
        elif name == "index_status":
            res = index_status(root)
        else:
            return {"ok": False, "tool": name, "error": f"unknown tool '{name}'. Use tools.list."}
    except Exception as e:
        return {"ok": False, "tool": name, "error": str(e)}
    st = index_status(root)
    return {"ok": True, "tool": name, "result": res, "next_ops": _next_ops(name, res),
            "index": {"fresh": st["fresh"], "lag_s": st["lag_s"], "files": st["files"]}}

def serve(root=None, port=None):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    root = root or repo_root(); cfg = load_config(root)
    port = port or int(cfg["serve"]["port"])

    from . import embed as E
    SERVE_STATE = {}
    print("cip: pre-warming embedding model...")
    _t = time.time()
    SERVE_STATE["emb"] = E._cached(("local", cfg["embed"].get("model", E.MODEL_NAME)),
                                   lambda: E.build_local_embedder(cfg))
    SERVE_STATE["t0"] = time.time()
    print(f"cip: model WARM in {int((time.time()-_t)*1000)}ms -- holding resident")

    class H(BaseHTTPRequestHandler):
        def _send(self, obj, code=200):
            body = json.dumps(obj, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            if self.path == "/health":
                self._send({"ok": True})
            elif self.path == "/tools":
                self._send({"tools": TOOLS})
            elif self.path == "/ontology.json":
                p = os.path.join(cip_dir(root), "ontology.json")
                self._send(json.load(open(p)) if os.path.exists(p) else {})
            elif self.path == "/embed/health":
                emb = SERVE_STATE.get("emb")
                return self._send({"warm": emb is not None,
                                   "model": getattr(emb, "name", None),
                                   "dim": getattr(emb, "dim", None),
                                   "pid": os.getpid(),
                                   "uptime_s": round(time.time() - SERVE_STATE.get("t0", time.time()), 1)})
            else:
                self._send({"ok": False, "error": "not found"}, 404)
        def do_POST(self):
            if self.path == "/embed":
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
                emb = SERVE_STATE["emb"]
                vecs = emb.embed(body.get("texts", []))
                return self._send({"vectors": vecs, "model": emb.name,
                                   "dim": emb.dim, "n": len(vecs)})
            n = int(self.headers.get("Content-Length", 0))
            try:
                req = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._send({"ok": False, "error": "bad json"}, 400)
            method, params = req.get("method", ""), req.get("params", {}) or {}
            if method == "tools.list":
                res = {"tools": TOOLS}
            elif method == "index.status":
                res = index_status(root)
            else:
                res = call_tool(root, cfg, method, params)
            self._send({"jsonrpc": "2.0", "id": req.get("id"), "result": res})
        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"cip: serving http://127.0.0.1:{port}  (POST /rpc · GET /tools /ontology.json /health)")
    srv.serve_forever()

def mcp_stdio(root=None):
    root = root or repo_root(); cfg = load_config(root)
    import threading
    from .embed import get_embedder
    threading.Thread(target=lambda: get_embedder(cfg, root), daemon=True).start()
    print("cip: MCP stdio server ready", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try: msg = json.loads(line)
        except Exception: continue
        mid, method = msg.get("id"), msg.get("method", "")
        if method == "initialize":
            resp = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                    "serverInfo": {"name": "cip", "version": "1.0.0"}}
        elif method == "tools/list":
            resp = {"tools": TOOLS}
        elif method == "tools/call":
            p = msg.get("params", {})
            env = call_tool(root, cfg, p.get("name", ""), p.get("arguments", {}))
            resp = {"content": [{"type": "text", "text": json.dumps(env, default=str)}]}
        elif method.startswith("notifications/"):
            continue
        else:
            resp = {"error": {"code": -32601, "message": "unknown method"}}
        if mid is not None:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": resp}) + "\n")
            sys.stdout.flush()
