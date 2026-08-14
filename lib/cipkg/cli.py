"""cip v1.0 — command line interface for the Code Intelligence Protocol."""
import argparse, json, os, shutil, sys

HOOKS = ("post-commit", "post-merge", "post-checkout")
MARK = "# >>> cip >>>"

def _out(obj):
    print(json.dumps(obj, indent=2, default=str))

def _install_hooks(root):
    git = os.path.join(root, ".git")
    if not os.path.isdir(git):
        print("note: not a git repo — hooks skipped (use `cip daemon` or `cip watch`)")
        return
    gdir = os.path.join(git, "hooks")
    os.makedirs(gdir, exist_ok=True)
    block = (f"{MARK}\n"
             f"sh -c 'command -v cip >/dev/null && cip sync || .cip/bin/cip sync' 2>/dev/null || true\n"
             f"# <<< cip <<<\n")
    for h in HOOKS:
        p = os.path.join(gdir, h)
        existing = open(p).read() if os.path.exists(p) else "#!/bin/sh\n"
        if MARK in existing: continue
        with open(p, "w") as f:
            f.write(existing.rstrip("\n") + "\n\n" + block)
        os.chmod(p, 0o755)
    print(f"installed git hooks: {', '.join(HOOKS)}")

def _ensure_gitignore(root):
    gi = os.path.join(root, ".gitignore")
    if not os.path.exists(gi): return
    text = open(gi).read()
    if ".cip/data" not in text:
        with open(gi, "a") as f:
            f.write("\n# CIP index data\n.cip/data/\n")

def _progress(phase, cur, total):
    """Print progress bar for long operations."""
    if phase == "scan":
        bar_len = 30
        filled = int(bar_len * cur / total) if total else 0
        bar = "=" * filled + "-" * (bar_len - filled)
        print(f"\r  scan  [{bar}] {cur}/{total}", end="", flush=True)
        if cur == total: print()
    elif phase == "embed":
        bar_len = 30
        filled = int(bar_len * cur / total) if total else 0
        bar = "=" * filled + "-" * (bar_len - filled)
        print(f"\r  embed [{bar}] {cur}/{total}", end="", flush=True)
        if cur == total: print()
    elif phase == "link":
        print("  linking edges...", end="", flush=True)

def cmd_init(root):
    from .base import load_config
    from . import detect, indexer
    from .store import connect, set_meta
    cipd = os.path.join(root, ".cip")
    os.makedirs(os.path.join(cipd, "data"), exist_ok=True)
    src, dst = os.path.join(cipd, "bootstrap", "AGENTS.md"), os.path.join(root, "AGENTS.md")
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy(src, dst)
        print(f"created {dst}")
    _install_hooks(root)
    _ensure_gitignore(root)
    cfg = load_config(root)
    det = detect.detect(root, cfg)
    con = connect(root)
    set_meta(con, "detection", json.dumps(det))
    con.commit()
    print(f"detected: primary={det['primary']} stacks={det['stacks']} langs={det['languages']}")
    print("indexing structure (fast, no embedding)...")
    stats = indexer.sync(root, full=True, do_embed=False, progress=_progress)
    print(f"indexed: {stats['files']} files, {stats['symbols']} symbols, "
          f"{stats['chunks']} chunks, {stats['edges']} edges in {stats['ms']}ms")
    try:
        from . import gitindex
        g = gitindex.git_index(root, depth=int(cfg["git"]["depth"]))
        print(f"git index: {g}")
    except Exception as e:
        print(f"git index skipped: {e}")
    print("structure ready. Run `cip embed` to enable semantic search.")

def cmd_doctor(root):
    from .base import load_config
    from . import indexer
    from .server import index_status
    from .store import connect, get_meta
    load_config(root)
    con = connect(root)
    st = index_status(root)
    stats = indexer.compute_stats(con)
    cov = (stats["vectors"] / stats["chunks"] * 100) if stats["chunks"] else 0.0
    hook = os.path.join(root, ".git", "hooks", "post-commit")
    hooks_ok = os.path.exists(hook) and MARK in open(hook).read()
    rows = [
        ("schema_version", get_meta(con, "schema_version")),
        ("files", stats["files"]), ("symbols", stats["symbols"]),
        ("chunks", stats["chunks"]), ("edges", stats["edges"]),
        ("vector coverage", f"{cov:.1f}%"),
        ("embedder", st["embedder"] or "none"), ("fts5", st["fts"]),
        ("commits indexed", st["commits"]), ("signals", st["signals"]),
        ("summaries", st["summaries"]),
        ("fresh", st["fresh"]), ("lag_s", st["lag_s"]),
        ("git hooks", "installed" if hooks_ok else "missing"),
        ("AGENTS.md", "present" if os.path.exists(os.path.join(root, "AGENTS.md")) else "missing"),
    ]
    print("cip doctor (v1.0)")
    for k, v in rows:
        print(f"  {k + ':':<18} {v}")

def cmd_upgrade(root):
    from .base import load_config
    from .store import connect, get_meta
    from . import indexer
    con = connect(root)                     # auto-migrates schema
    print(f"schema_version: {get_meta(con, 'schema_version')}")
    _out(indexer.sync(root, full=True))
    try:
        from . import gitindex
        depth = int(load_config(root)["git"]["depth"])
        _out(gitindex.git_index(root, depth=depth))
    except Exception as e:
        print(f"git-index skipped: {e}")
    print("upgrade complete. Run `cip doctor` to verify.")

def main(argv=None):
    p = argparse.ArgumentParser(prog="cip",
        description="CIP v1.0 — repo-agnostic, self-updating code intelligence for AI agents")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("init")
    sub.add_parser("upgrade", help="migrate schema + full reindex + git index")
    sub.add_parser("detect")
    ip = sub.add_parser("index"); ip.add_argument("--full", action="store_true")
    ip.add_argument("--reembed", action="store_true")
    ep = sub.add_parser("embed", help="embed chunks for semantic search (slow, CPU)")
    ep.add_argument("--batch", type=int, default=64)
    sub.add_parser("sync")
    wp = sub.add_parser("watch"); wp.add_argument("--interval", type=float, default=1.0)
    dp = sub.add_parser("daemon", help="watcher + server, single-writer lock")
    dp.add_argument("--port", type=int); dp.add_argument("--interval", type=float, default=1.0)
    sp = sub.add_parser("search"); sp.add_argument("query"); sp.add_argument("-k", type=int, default=10)
    yp = sub.add_parser("symbol"); yp.add_argument("name")
    gp = sub.add_parser("graph"); gp.add_argument("id")
    gp.add_argument("--direction", default="both"); gp.add_argument("--depth", type=int, default=1)
    cp = sub.add_parser("context"); cp.add_argument("query", nargs="?")
    cp.add_argument("--symbol"); cp.add_argument("--budget", type=int)
    mp = sub.add_parser("summary"); mp.add_argument("path", nargs="?")
    sub.add_parser("map")
    ep = sub.add_parser("describe"); ep.add_argument("entity", nargs="?")
    sub.add_parser("broken"); sub.add_parser("hotspots")
    hp = sub.add_parser("history"); hp.add_argument("path")
    rp = sub.add_parser("route"); rp.add_argument("query")
    gip = sub.add_parser("git-index"); gip.add_argument("--depth", type=int)
    ig = sub.add_parser("ingest"); ig.add_argument("--kind", required=True,
        choices=["vitest", "jest", "pytest", "tsc", "generic", "eslint"])
    ig.add_argument("--file", default="-", help="path or '-' for stdin")
    ex = sub.add_parser("export"); ex.add_argument("--format", default="json",
        choices=["json", "lsif", "markdown"]); ex.add_argument("--out")
    sub.add_parser("doctor")
    vp = sub.add_parser("serve"); vp.add_argument("--port", type=int)
    sub.add_parser("mcp")
    tp = sub.add_parser("tools"); tp.add_argument("--schema", action="store_true")
    sub.add_parser("selftest")
    # ---- v1.1 stack pack ----
    ap = sub.add_parser("audit", help="run TS/Next/Prisma audit rules")
    ap.add_argument("--md", help="write markdown report to file")
    ap.add_argument("--no-refresh", action="store_true")
    fp = sub.add_parser("findings")
    fp.add_argument("--severity"); fp.add_argument("--rule"); fp.add_argument("--path")
    fp.add_argument("--limit", type=int, default=100)
    sub.add_parser("refactors", help="top quick-win refactors")
    mp = sub.add_parser("impact"); mp.add_argument("target", nargs="?")
    mp.add_argument("--ref"); mp.add_argument("--depth", type=int, default=2)
    sub.add_parser("routes"); sub.add_parser("models")
    sub.add_parser("gate", help="quality gate: exit 1 on critical findings/broken signals")
    dp = sub.add_parser("dashboard", help="professional-grade local visualization")
    dp.add_argument("--port", type=int, default=8790)
    a = p.parse_args(argv)
    if not a.cmd:
        p.print_help(); return 0

    from .base import repo_root, load_config, cip_dir
    root = os.getcwd() if a.cmd == "init" else repo_root()

    if a.cmd == "init":       cmd_init(root)
    elif a.cmd == "upgrade":  cmd_upgrade(root)
    elif a.cmd == "detect":
        from . import detect; _out(detect.detect(root, load_config(root)))
    elif a.cmd == "index":
        from . import indexer
        from .store import connect
        if a.reembed:
            con = connect(root)
            con.execute("DELETE FROM vectors")
            con.execute("DELETE FROM meta WHERE key='embedder_name'")
            con.commit()
        _out(indexer.sync(root, full=a.full, progress=_progress))
    elif a.cmd == "embed":
        from . import indexer
        from .store import connect
        from .base import load_config
        cfg = load_config(root)
        con = connect(root)
        n = indexer.embed_pending(con, cfg, batch=a.batch, progress=_progress)
        print(f"embedded {n} chunks")
    elif a.cmd == "sync":
        from . import indexer; _out(indexer.sync(root))
    elif a.cmd == "watch":
        from .watch import watch; watch(root, interval=a.interval)
    elif a.cmd == "daemon":
        from .daemon import daemon; daemon(root, port=a.port, interval=a.interval)
    elif a.cmd == "search":
        from . import retrieve, router
        q = a.query
        _out({"route": router.route(q), "results": retrieve.search(root, q, k=a.k)})
    elif a.cmd == "symbol":
        from . import retrieve; _out({"symbols": retrieve.find_symbol(root, a.name)})
    elif a.cmd == "graph":
        from . import retrieve; _out(retrieve.graph(root, a.id, a.direction, depth=a.depth))
    elif a.cmd == "context":
        from . import retrieve; _out(retrieve.context(root, a.query, a.symbol, a.budget))
    elif a.cmd == "summary":
        from . import summarize; _out(summarize.summary(root, a.path))
    elif a.cmd == "map":
        from . import summarize; _out(summarize.map_(root))
    elif a.cmd == "describe":
        from .server import describe; _out(describe(root, a.entity))
    elif a.cmd == "broken":
        from . import runtime_adapters; _out(runtime_adapters.broken(root))
    elif a.cmd == "hotspots":
        from . import gitindex; _out({"hotspots": gitindex.hotspots(root)})
    elif a.cmd == "history":
        from . import retrieve; _out(retrieve.history(root, a.path))
    elif a.cmd == "route":
        from . import router; _out(router.route(a.query))
    elif a.cmd == "git-index":
        from . import gitindex
        depth = a.depth or int(load_config(root)["git"]["depth"])
        _out(gitindex.git_index(root, depth=depth))
    elif a.cmd == "ingest":
        if a.kind == "eslint":
            from .stack import audit as sa; _out(sa.ingest_eslint(root, a.file))
        else:
            from . import runtime_adapters; _out(runtime_adapters.ingest(root, a.kind, a.file))
    elif a.cmd == "export":
        from . import export; _out(export.export(root, a.format, a.out))
    elif a.cmd == "doctor":   cmd_doctor(root)
    elif a.cmd == "serve":
        from .server import serve; serve(root, port=a.port)
    elif a.cmd == "mcp":
        from .server import mcp_stdio; mcp_stdio(root)
    elif a.cmd == "tools":
        from .server import TOOLS
        if a.schema:
            op = os.path.join(cip_dir(root), "ontology.json")
            _out(json.load(open(op)) if os.path.exists(op) else {"tools": TOOLS})
        else:
            _out({"tools": [t["name"] for t in TOOLS]})
    elif a.cmd == "selftest":
        from .selftest import run_selftest
        rc = run_selftest()
        from .stack.selftest import run_stack_selftest
        rc2 = run_stack_selftest()
        return rc or rc2
    elif a.cmd == "audit":
        from .stack import audit as sa
        _out(sa.audit(root, refresh=not a.no_refresh))
        if a.md:
            open(a.md, "w").write(sa.report_markdown(root))
            print(f"report written: {a.md}")
    elif a.cmd == "findings":
        from .stack import audit as sa
        _out({"findings": sa.findings(root, severity=a.severity, rule=a.rule,
                                      path=a.path, limit=a.limit)})
    elif a.cmd == "refactors":
        from .stack import audit as sa; _out({"quick_wins": sa.quick_wins(root)})
    elif a.cmd == "impact":
        from .stack import impact as si
        if a.ref: _out(si.impact_diff(root, ref=a.ref))
        elif a.target: _out(si.impact(root, target=a.target, depth=a.depth))
        else: print("usage: cip impact <file|symbol>   |   cip impact --ref origin/main")
    elif a.cmd == "routes":
        from .stack import nextjs as sn; _out({"routes": sn.list_routes(root)})
    elif a.cmd == "models":
        from .stack import prisma as sp; _out(sp.models_report(root))
    elif a.cmd == "gate":
        from .stack import audit as sa
        g = sa.gate(root); _out(g)
        return 0 if g["ok"] else 1
    elif a.cmd == "dashboard":
        from .dashboard import serve_dashboard
        serve_dashboard(root, port=a.port)
    return 0
