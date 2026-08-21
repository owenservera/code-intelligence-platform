"""cip v1.0 — command line interface for the Code Intelligence Protocol."""
import argparse, json, os, shutil, time

from . import gapfill
from . import summarize
from .hooks import install_agent_hooks, run_hook_command
from .session import session_start, session_end, get_active_session
from .verify import verify
from . import learning

HOOKS = ("post-commit", "post-merge", "post-checkout")
MARK = "# >>> cip >>>"

def _out(obj):
    print(json.dumps(obj, indent=2, default=str))

def _desc(msg):
    print("  -> %s" % msg, flush=True)

def _server_describe(root, entity=None):
    from .server import describe
    return describe(root, entity)

def _install_hooks(root):
    git = os.path.join(root, ".git")
    if not os.path.isdir(git):
        print("note: not a git repo -- hooks skipped (use `cip daemon` or `cip watch`)")
        return
    gdir = os.path.join(git, "hooks")
    os.makedirs(gdir, exist_ok=True)
    block = (MARK + "\n"
             "sh -c 'command -v cip >/dev/null && cip sync || .cip/bin/cip sync' 2>/dev/null || true\n"
             "# <<< cip <<<\n")
    for h in HOOKS:
        p = os.path.join(gdir, h)
        existing = open(p).read() if os.path.exists(p) else "#!/bin/sh\n"
        if MARK in existing:
            continue
        with open(p, "w") as f:
            f.write(existing.rstrip("\n") + "\n\n" + block)
        os.chmod(p, 0o755)
    print("installed git hooks: %s" % ", ".join(HOOKS))

def _ensure_gitignore(root):
    gi = os.path.join(root, ".gitignore")
    if not os.path.exists(gi):
        return
    text = open(gi).read()
    if ".cip/data" not in text:
        with open(gi, "a") as f:
            f.write("\n# CIP index data\n.cip/data/\n")

def _progress(phase, cur, total):
    bar_len = 30
    filled = int(bar_len * cur / total) if total else 0
    bar = "=" * filled + "-" * (bar_len - filled)
    if phase == "scan":
        print("\r  scan  [%s] %d/%d" % (bar, cur, total), end="", flush=True)
        if cur == total:
            print(" done", flush=True)
    elif phase == "embed":
        pct = int(100 * cur / total) if total else 0
        print("\r  embed [%s] %d/%d (%d%%)" % (bar, cur, total, pct),
              end="", flush=True)
        if cur == total:
            print(" done", flush=True)
    elif phase == "link":
        print("  linking edges...", flush=True)

def _check_daemon(root):
    """Return (port, health_dict) if daemon is warm, else (None, None)."""
    from .embed import find_daemon_port
    return find_daemon_port(root)

def handle_analyze_command(root, args):
    from . import analysis
    _out(analysis.repo_health_report(root))

def handle_rebuild_command(root, args):
    from .maintain import rebuild
    _out(rebuild(root, progress=_progress))

def handle_verify_index_command(root, args):
    from .maintain import verify
    _out(verify(root, repair=args.repair))

def handle_vacuum_command(root, args):
    from .maintain import vacuum
    _out(vacuum(root, days=args.days))

def handle_embed_command(root, args):
    from . import indexer
    from .store import connect
    from .base import load_config
    _out(indexer.embed_pending(connect(root), load_config(root), batch=args.batch, progress=_progress))

def handle_hook_command(root, args):
    """Handle agent integration hook commands."""
    hook_args = [args.hook_type] + args.args
    result = run_hook_command(hook_args)
    _out(result)

def handle_audit_command(root, args):
    """Handle audit command with file/diff scoping."""
    from .stack import audit as stack_audit
    if hasattr(args, 'file') and args.file:
        result = stack_audit.audit_file(root, args.file)
    elif hasattr(args, 'diff') and args.diff:
        result = stack_audit.audit_diff(root)
    else:
        result = stack_audit.audit(root, refresh=True)
    _out(result)

def handle_findings_command(root, args):
    """Handle findings command with structured output option."""
    from .stack import audit as stack_audit
    if hasattr(args, 'structured') and args.structured:
        result = stack_audit.findings_structured(
            root, getattr(args, 'severity', None), getattr(args, 'rule', None), 
            getattr(args, 'path', None), getattr(args, 'limit', 100))
    else:
        result = stack_audit.findings(
            root, getattr(args, 'severity', None), getattr(args, 'rule', None), 
            getattr(args, 'path', None), getattr(args, 'limit', 100))
    _out(result)

def handle_impact_command(root, args):
    """Handle impact command with structured output option."""
    from .stack import impact as stack_impact
    if hasattr(args, 'structured') and args.structured:
        result = stack_impact.impact_structured(
            root, getattr(args, 'target', ''), getattr(args, 'depth', 2))
    elif hasattr(args, 'ref') and args.ref:
        result = stack_impact.impact_diff(root, args.ref)
    else:
        result = stack_impact.impact(root, getattr(args, 'target', ''), getattr(args, 'depth', 2))
    _out(result)

# Add simple pass-through handlers for other commands as needed
def handle_init_command(root, args):
    cmd_init(root)

def handle_upgrade_command(root, args):
    cmd_upgrade(root)

def handle_detect_command(root, args):
    from . import detect
    from .base import load_config
    cfg = load_config(root)
    _out(detect.detect(root, cfg))

def handle_index_command(root, args):
    from . import indexer
    _out(indexer.sync(root, full=getattr(args, 'full', False), do_embed=getattr(args, 'reembed', False), progress=_progress))

def handle_sync_command(root, args):
    cmd_sync(root)

def handle_watch_command(root, args):
    from .watch import watch
    watch(root, interval=getattr(args, 'interval', 1.0))

def handle_daemon_command(root, args):
    if getattr(args, 'daemon_cmd', None) == "status":
        cmd_daemon_status(root)
    elif getattr(args, 'daemon_cmd', None) == "stop":
        cmd_daemon_stop(root)
    else:
        cmd_daemon_start(root, getattr(args, 'port', 8787), getattr(args, 'interval', 1.0))

def handle_search_command(root, args):
    from . import retrieve
    _out({"results": retrieve.search(root, getattr(args, 'query', ''), k=getattr(args, 'k', 10))})

def handle_symbol_command(root, args):
    from . import retrieve
    _out({"symbols": retrieve.find_symbol(root, getattr(args, 'name', ''))})

def handle_graph_command(root, args):
    from . import retrieve
    _out(retrieve.graph(root, getattr(args, 'id', ''), getattr(args, 'direction', 'both'), getattr(args, 'depth', 1)))

def handle_context_command(root, args):
    from . import retrieve
    _out(retrieve.context(root, getattr(args, 'query', None), getattr(args, 'symbol', None), getattr(args, 'budget', None)))

def handle_suggest_context_command(root, args):
    """Handle 'cip suggest-context' — suggest relevant context for editing a file."""
    from . import predict
    result = predict.suggest_context_for_edit(root, getattr(args, "file", None))
    _out(result)

def handle_summary_command(root, args):
    from . import summarize
    _out(summarize.summary(root, getattr(args, 'path', None)))

def handle_broken_command(root, args):
    from .runtime_adapters import broken
    _out(broken(root))

def handle_hotspots_command(root, args):
    from . import gitindex
    _out({"hotspots": gitindex.hotspots(root)})

def handle_history_command(root, args):
    from . import retrieve
    _out(retrieve.history(root, getattr(args, 'path', '')))

def handle_route_command(root, args):
    from . import router
    if getattr(args, 'agent', False):
        _out(router.route_for_agent(getattr(args, 'query', '')))
    else:
        _out(router.route(getattr(args, 'query', '')))

def handle_git_index_command(root, args):
    from . import gitindex
    _out(gitindex.git_index(root, depth=getattr(args, 'depth', None)))

def handle_ingest_command(root, args):
    from .runtime_adapters import ingest
    _out(ingest(root, getattr(args, 'kind', ''), getattr(args, 'file', '-')))

def handle_export_command(root, args):
    from .export import export
    _out(export(root, getattr(args, 'format', 'json'), getattr(args, 'out', None)))

def handle_doctor_command(root, args):
    """S5: first-class self-diagnostic command.

    `cip doctor` (no flag) = full system report (Doctor `core cmd` + info
    table). `cip doctor --static/--config/--runtime` = one scope only.
    """
    from . import doctor as doctor_mod
    if getattr(args, "static", False):
        scope = "static"
    elif getattr(args, "config", False):
        scope = "config"
    elif getattr(args, "runtime", False):
        scope = "runtime"
    else:
        scope = None
    _out(doctor_mod.doctor(root, scope))
    if scope is None:
        cmd_doctor(root)

def handle_serve_command(root, args):
    from .server import serve
    serve(root, getattr(args, 'port', None))

def handle_mdm_scan_command(root, args):
    """Run full Master Data Model (L0-LA) multi-layer extraction and synthesis."""
    from .mdm_engine import run_mdm_extraction
    from .mdm_synthesis import synthesize_la_findings
    from .store import connect
    con = connect(root)
    ext_res = run_mdm_extraction(root)
    la_res = synthesize_la_findings(con, root)
    _out({"extraction": ext_res, "synthesized_findings_count": len(la_res)})

def handle_mdm_report_command(root, args):
    """Generate and display complete Master Data Model executive report."""
    from .mdm_synthesis import generate_full_mdm_report, format_report_markdown
    report = generate_full_mdm_report(root)
    if getattr(args, "markdown", False):
        print(format_report_markdown(report))
    else:
        _out(report)

def handle_mdm_trace_command(root, args):
    """Display step-by-step explainability trace for a specific finding."""
    from .mdm_schema import get_explainability_trace
    from .store import connect
    con = connect(root)
    fid = getattr(args, "finding_id", "")
    trace = get_explainability_trace(con, fid)
    _out({"finding_id": fid, "trace_steps": trace})

def handle_mdm_gaps_command(root, args):
    """Scan and list all detected L4 wiring gaps (IPC, events, routes)."""
    from .mdm_engine import scan_l4_flow_and_wiring
    from .store import connect
    con = connect(root)
    gaps = scan_l4_flow_and_wiring(con, root)
    _out(gaps)

def handle_dashboard_web_command(root, args):
    """Handle 'cip dashboard-web' command (legacy)."""
    from .web_server import start_web_server
    port = getattr(args, 'port', 8090)
    host = getattr(args, 'host', 'localhost')
    start_web_server(root, port, host)

def handle_web_command(root, args):
    """Handle 'cip web' — new FastAPI Web Console."""
    # GAP-04: --root / --project preselect a project before the bridge imports,
    # so the bridge's CIP_WEB_ROOT bootstrap (:59-62) selects + registers it.
    cli_root = getattr(args, 'root', None)
    cli_project = getattr(args, 'project', None)
    if cli_project:
        from .project_registry import get_registry, ProjectRegistry
        entry = get_registry().get(ProjectRegistry.project_id(cli_project))
        if entry is None:
            print(f"error: unknown project in registry: {cli_project}")
            print("  list projects with: cip projects (see docs/dev/upgrade-plan/)")
            return 1
        cli_root = entry["root"]
    if cli_root:
        cli_root = os.path.abspath(os.path.normcase(cli_root))
        if not os.path.isdir(cli_root):
            print(f"error: selected folder does not exist: {cli_root}")
            return 1
        os.environ["CIP_WEB_ROOT"] = cli_root
        print(f"  -> preselected project: {cli_root}")

    from .web_bridge import app as web_app
    import uvicorn
    port = getattr(args, 'port', None) or 8090
    host = getattr(args, 'host', 'localhost') or "localhost"
    open_browser = getattr(args, 'open_browser', True)
    if open_browser:
        import threading, time as _t, webbrowser
        def _open():
            _t.sleep(1.5)
            webbrowser.open(f"http://{host}:{port}")
        threading.Thread(target=_open, daemon=True).start()
    print(f"🌐 CIP Console: http://{host}:{port}")
    print(f"   Press Ctrl+C to stop")
    uvicorn.run(web_app, host=host, port=port, log_level="info")

def handle_mcp_command(root, args):
    from .server import mcp_stdio
    mcp_stdio(root)

def handle_tools_command(root, args):
    from .server import TOOLS
    if getattr(args, 'schema', False):
        _out({"tools": TOOLS})
    else:
        for t in TOOLS:
            print(f"{t['name']}: {t['description']}")

def handle_selftest_command(root, args):
    from .selftest import run_selftest
    _out({"exit_code": run_selftest()})

def handle_session_command(root, args):
    """Handle session management commands."""
    if args.session_cmd == "start":
        result = session_start(root)
    elif args.session_cmd == "end":
        result = session_end(root)
    elif args.session_cmd == "status":
        result = get_active_session(root) or {"error": "No active session"}
    else:
        result = {"error": f"Unknown session command: {args.session_cmd}"}
    _out(result)

def handle_verify_command(root, args):
    """Handle verification gate command."""
    result = verify(
        root, 
        typecheck=getattr(args, 'typecheck', False),
        lint=getattr(args, 'lint', False),
        audit_check=not getattr(args, 'no_audit', False)
    )
    
    if getattr(args, 'blocking', False) and not result["can_proceed"]:
        _out(result)
        return 1
    
    _out(result)

def handle_learning_command(root, args):
    """Handle learning loop commands."""
    if args.learning_cmd == "analyze":
        result = learning.analyze_sessions(root)
    elif args.learning_cmd == "update":
        result = learning.update_prediction_confidence(root)
    elif args.learning_cmd == "report":
        result = learning.generate_learning_report(root)
    elif args.learning_cmd == "patterns":
        result = learning.detect_agent_patterns(root)
    else:
        result = {"error": f"Unknown learning command: {args.learning_cmd}"}
    _out(result)

# ── gapfill / audit pass-through handlers ────────────────────────────────────
# Wire registry cards + dispatch to the REAL lib callables (CORE-5 / F-35).
# Each real function lives in gapfill / predict / stack.audit; these handlers
# only translate the (root, args) shape and print via _out.

def handle_coverage_command(root, args):
    from . import gapfill
    _out(gapfill.coverage(root))

def handle_dead_command(root, args):
    from . import gapfill
    _out(gapfill.dead(root, limit=getattr(args, 'limit', 50)))

def handle_circular_command(root, args):
    from . import gapfill
    _out(gapfill.circular(root))

def handle_blame_command(root, args):
    from . import gapfill
    _out(gapfill.blame(root, path=getattr(args, 'path', None), line=getattr(args, 'line', None)))

def handle_migrations_command(root, args):
    from . import gapfill
    _out(gapfill.migrations(root))

def handle_env_command(root, args):
    from . import gapfill
    _out(gapfill.env(root, limit=getattr(args, 'limit', 60)))

def handle_logs_command(root, args):
    from . import gapfill
    _out(gapfill.logs(root))

def handle_metrics_command(root, args):
    from . import gapfill
    _out(gapfill.metrics(root))

def handle_features_command(root, args):
    from . import gapfill
    _out(gapfill.features(root))

def handle_deps_command(root, args):
    from . import gapfill
    _out(gapfill.deps(root))

def handle_api_command(root, args):
    from . import gapfill
    _out(gapfill.api(root))

def handle_refactors_command(root, args):
    from .stack import audit as stack_audit
    _out(stack_audit.quick_wins(root, limit=getattr(args, 'limit', 10)))

def handle_gate_command(root, args):
    from .stack import audit as stack_audit
    _out(stack_audit.gate(root))

def handle_predict_command(root, args):
    from . import predict
    _out(predict.predict_next_context(
        root, getattr(args, 'operation', ''), getattr(args, 'symbol', None),
        getattr(args, 'query', None)))

def handle_routes_command(root, args):
    from .stack import nextjs
    _out(nextjs.list_routes(root))

def handle_models_command(root, args):
    from .stack import prisma
    _out(prisma.models_report(root))

def handle_admission_command(root, args):
    from . import gatekeeper
    rel = getattr(args, 'path', None)
    _out(gatekeeper.explain(root, rel) if rel else gatekeeper.admission_report(root))

def handle_score_command(root, args):
    from . import gapfill
    _out(gapfill.score(root))

def handle_embedder_command(root, args):
    cmd_embedder(root)

def handle_embed_ping_command(root, args):
    cmd_embed_ping(root, getattr(args, 'count', 5))

# ── commands ─────────────────────────────────────────────────────────────────

def cmd_init(root):
    # PLAN-04 / SPEC-19 §6.3: the web console and CLI share this exact init path.
    from .init_flow import init_project
    return init_project(root)

def cmd_doctor(root):
    from .base import load_config, data_dir
    from . import indexer
    from .server import index_status
    from .store import connect, get_meta
    _desc("Checking system health...")
    load_config(root)
    con = connect(root)
    st = index_status(root)
    stats = indexer.compute_stats(con)
    cov = (stats["vectors"] / stats["chunks"] * 100) if stats["chunks"] else 0.0
    hook = os.path.join(root, ".git", "hooks", "post-commit")
    hooks_ok = os.path.exists(hook) and MARK in open(hook).read()
    from .daemon import daemon_status
    ds = daemon_status(root)
    daemon_str = "running (pid %d)" % ds["pid"] if ds["alive"] else "stopped"
    if ds["warm"]:
        daemon_str += " [warm]"
    rows = [
        ("schema_version", get_meta(con, "schema_version")),
        ("files", stats["files"]), ("symbols", stats["symbols"]),
        ("chunks", stats["chunks"]), ("edges", stats["edges"]),
        ("vector coverage", "%.1f%%" % cov),
        ("daemon", daemon_str),
        ("fts5", st["fts"]),
        ("commits indexed", st["commits"]), ("signals", st["signals"]),
        ("summaries", st["summaries"]),
        ("fresh", st["fresh"]), ("lag_s", st["lag_s"]),
        ("git hooks", "installed" if hooks_ok else "missing"),
        ("AGENTS.md", "present" if os.path.exists(
            os.path.join(root, "AGENTS.md")) else "missing"),
    ]
    try:
        sc: dict = gapfill.score(root)
        health_str = "%d/100 (%s)" % (sc.get("score", 0), sc.get("grade", "?"))
    except Exception as e:
        health_str = "n/a (%s)" % e
    dbp = os.path.join(data_dir(root), "index.db")
    db_mb = ("%.2f MB" % (os.path.getsize(dbp) / 1e6)) if os.path.exists(dbp) else "n/a"
    dims = con.execute("SELECT length(vec)/4 v FROM vectors LIMIT 1").fetchone()
    dims_str = str(dims["v"]) if dims and dims["v"] else "?"
    rows += [
        ("health score", health_str),
        ("db size", db_mb),
        ("vector dims", dims_str),
    ]
    print("cip doctor (v1.0)")
    for k, v in rows:
        print("  %-18s %s" % (k + ":", v))

def cmd_upgrade(root):
    from .base import load_config
    from .store import connect, get_meta
    from . import indexer
    _desc("Upgrading: migrating schema + full reindex + git history")
    con = connect(root)
    print("schema_version: %s" % get_meta(con, "schema_version"))
    _desc("Rebuilding entire index from scratch (full rescan)")
    _out(indexer.sync(root, full=True, progress=_progress))
    try:
        from . import gitindex
        depth = int(load_config(root)["git"]["depth"])
        _out(gitindex.git_index(root, depth=depth))
    except Exception as e:
        print("git-index skipped: %s" % e)
    print("upgrade complete. Run `cip doctor` to verify.")

def cmd_sync(root):
    """Sync: scan + link, then embed using whichever embedder is ready."""
    from . import indexer
    _desc("Updating index: scan + link + embed")
    port, health = _check_daemon(root)
    if port:
        _desc("Daemon warm on :%d, embeddings via service" % port)
    else:
        _desc("No daemon running, embeddings via local model")
    _out(indexer.sync(root, progress=_progress))

def cmd_daemon_start(root, port, interval):
    from .daemon import daemon
    daemon(root, port=port, interval=interval)

def cmd_daemon_status(root):
    from .daemon import daemon_status, _paths
    _desc("Checking daemon status...")
    info = daemon_status(root)
    p = _paths(root)
    if info["alive"]:
        print("daemon:  RUNNING (pid %d)" % info["pid"])
        print("port:    %s" % info["port"])
        print("log:     %s" % p["log"])
        if info["health"]:
            h = info["health"]
            print("model:   %s" % h.get("model", "?"))
            print("warm:    %s" % h.get("warm", "?"))
            print("uptime:  %ss" % h.get("uptime_s", "?"))
        else:
            print("warm:    false (model not loaded)")
    else:
        print("daemon:  STOPPED")
        if info["pid"]:
            print("note:    lockfile exists (pid %d) but process dead" % info["pid"])
            print("fix:     cip daemon stop  (to clean up)")

def cmd_daemon_stop(root):
    from .daemon import daemon_stop
    daemon_stop(root)

def cmd_embed_ping(root, count):
    from .embed import RemoteEmbedder
    port, health = _check_daemon(root)
    health = health or {}
    if not port:
        print("daemon: not running.  Start with: cip daemon")
        return 1
    _desc("Pinging daemon on :%d (%d requests)" % (port, count))
    emb = RemoteEmbedder(port, name=health.get("model"), dim=int(health.get("dim") or 384))
    times = []
    for i in range(count):
        t0 = time.time()
        v = emb.embed(["ping test sentence %d" % (i + 1)])
        ms = int((time.time() - t0) * 1000)
        times.append(ms)
        print("  ping %d/%d  %dms  dim=%d" % (i + 1, count, ms, len(v[0])))
    avg = sum(times) // len(times)
    mn, mx = min(times), max(times)
    print("  ---")
    print("  avg=%dms  min=%dms  max=%dms  (warm, no model reload)" % (avg, mn, mx))

def cmd_embedder(root):
    from .embed import get_embedder_with_feedback, service_health, service_port
    from .base import load_config
    _desc("Embedding engine status")
    cfg = load_config(root)
    port = service_port(cfg)
    h = service_health(port)
    if h:
        print("daemon :%d  ->  WARM  model=%s  uptime=%ss" % (
            port, h.get("model"), h.get("uptime_s")))
    else:
        print("daemon :%d  ->  not running" % port)
    print("engine:")
    t0 = time.time()
    emb = get_embedder_with_feedback(cfg, root)
    print("  resolved in %dms" % int((time.time() - t0) * 1000))
    t0 = time.time()
    v = emb.embed(["benchmark: token refresh pipeline"])
    print("  single embed %dms  dim=%d" % (int((time.time() - t0) * 1000), len(v[0])))

# ── argument parser setup ───────────────────────────────────────────────────

def setup_argument_parser():
    """Setup and return the argument parser with all subcommands."""
    p = argparse.ArgumentParser(
        prog="cip",
        description="CIP v1.0 -- repo-agnostic, self-updating code intelligence for AI agents")
    sub = p.add_subparsers(dest="cmd")

    # core
    sub.add_parser("init")
    sub.add_parser("upgrade", help="migrate schema + full reindex + git index")
    sub.add_parser("detect")
    ip = sub.add_parser("index")
    ip.add_argument("--full", action="store_true")
    ip.add_argument("--reembed", action="store_true")
    ep = sub.add_parser("embed", help="embed chunks for semantic search")
    ep.add_argument("--batch", type=int, default=64)
    sub.add_parser("sync", help="scan + link + embed (full update)")
    wp = sub.add_parser("watch")
    wp.add_argument("--interval", type=float, default=1.0)

    # daemon lifecycle
    dp = sub.add_parser("daemon", help="background watcher + HTTP server")
    dp.add_argument("--port", type=int, default=8787)
    dp.add_argument("--interval", type=float, default=1.0)
    daemon_sub = dp.add_subparsers(dest="daemon_cmd")
    daemon_sub.add_parser("start", help="start daemon (default)")
    daemon_sub.add_parser("status", help="check if daemon is running")
    daemon_sub.add_parser("stop", help="stop the daemon")

    # search / query
    sp = sub.add_parser("search")
    sp.add_argument("query")
    sp.add_argument("-k", type=int, default=10)
    yp = sub.add_parser("symbol")
    yp.add_argument("name")
    gp = sub.add_parser("graph")
    gp.add_argument("id")
    gp.add_argument("--direction", default="both")
    gp.add_argument("--depth", type=int, default=1)
    cp = sub.add_parser("context")
    cp.add_argument("query", nargs="?")
    cp.add_argument("--symbol")
    cp.add_argument("--budget", type=int)
    mp = sub.add_parser("summary")
    mp.add_argument("path", nargs="?")
    sub.add_parser("map")
    ep2 = sub.add_parser("describe")
    ep2.add_argument("entity", nargs="?")
    sub.add_parser("broken")
    sub.add_parser("hotspots")
    hp = sub.add_parser("history")
    hp.add_argument("path")
    rp = sub.add_parser("route")
    rp.add_argument("query")
    rp.add_argument("--agent", action="store_true", help="agent-aware routing with confidence scores")
    gip = sub.add_parser("git-index")
    gip.add_argument("--depth", type=int)
    ig = sub.add_parser("ingest")
    ig.add_argument("--kind", required=True,
        choices=["vitest", "jest", "pytest", "tsc", "generic", "eslint"])
    ig.add_argument("--file", default="-")
    ex = sub.add_parser("export")
    ex.add_argument("--format", default="json", choices=["json", "lsif", "markdown"])
    ex.add_argument("--out")
    doc = sub.add_parser("doctor", help="system health + self-consistency checks")
    doc.add_argument("--static", action="store_true", help="CODE-* static scans (S1 swallow + S2 lint)")
    doc.add_argument("--config", action="store_true", help="CONFIG-* self-consistency skeleton")
    doc.add_argument("--runtime", action="store_true", help="runtime / API-contract probes")
    vp = sub.add_parser("serve")
    vp.add_argument("--port", type=int)
    sub.add_parser("mcp")
    tp = sub.add_parser("tools")
    tp.add_argument("--schema", action="store_true")
    sub.add_parser("selftest")

    # v1.1 stack pack
    ap = sub.add_parser("audit")
    ap.add_argument("--file", help="scope audit to single file")
    ap.add_argument("--diff", action="store_true", help="scope audit to git diff")
    fp = sub.add_parser("findings")
    fp.add_argument("--severity")
    fp.add_argument("--rule")
    fp.add_argument("--path")
    fp.add_argument("--limit", type=int, default=100)
    fp.add_argument("--structured", action="store_true", help="return machine-actionable format")
    sub.add_parser("refactors", help="top quick-win refactors")
    mp2 = sub.add_parser("impact")
    mp2.add_argument("target", nargs="?")
    mp2.add_argument("--ref")
    mp2.add_argument("--depth", type=int, default=2)
    mp2.add_argument("--structured", action="store_true", help="return structured format for todo integration")
    sub.add_parser("routes")
    sub.add_parser("models")
    sub.add_parser("gate", help="quality gate: exit 1 on critical findings")
    dp2 = sub.add_parser("dashboard", help="local visualization")
    dp2.add_argument("--port", type=int, default=8790)

    dw = sub.add_parser("dashboard-web", help="interactive web dashboard with WebSocket (legacy)")
    dw.add_argument("--port", type=int, default=8090)
    dw.add_argument("--host", type=str, default="localhost")

    wb = sub.add_parser("web", help="Web Console (FastAPI + React SPA)")
    wb.add_argument("--port", type=int, default=8090)
    wb.add_argument("--host", type=str, default="localhost")
    wb.add_argument("--no-browser", dest="open_browser", action="store_false", default=True)
    # GAP-04: preselect the active project at boot (works from a non-CIP cwd).
    wb.add_argument("--project", help="registry project id (normalized root) to select")
    wb.add_argument("--root", help="folder to register + select (auto-registers)")

    # v1.3 gatekeeper
    ad = sub.add_parser("admission", help="audit what is indexed and why")
    ad.add_argument("--path", help="explain one specific file")

    # v1.4 embedder
    sub.add_parser("embedder", help="embedding engine status + benchmark")
    pp = sub.add_parser("embed-ping", help="test daemon embedding latency")
    pp.add_argument("count", nargs="?", type=int, default=5)

    # v2 gap-fillers — close pressure-test scenarios 63/70/71/72/78/100/106/107…
    sub.add_parser("coverage", help="test-coverage signals (scenario 63/228/229)")
    sub.add_parser("dead", help="dead-code / unused-symbol detection (71)")
    sub.add_parser("circular", help="circular-dependency detection (72)")
    bl = sub.add_parser("blame", help="git blame for a file [+line] (78)")
    bl.add_argument("path"); bl.add_argument("line", nargs="?")
    sub.add_parser("score", help="overall health score 0-100 (70/100/106/107)")
    sub.add_parser("migrations", help="DB migration inventory (137/251-258)")
    sub.add_parser("env", help="env-var inventory (20/195)")
    sub.add_parser("logs", help="logging-pattern analysis (29/198/266)")
    sub.add_parser("metrics", help="metrics/observability status (269/271)")
    sub.add_parser("features", help="feature-flag inventory (281/282/285)")
    sub.add_parser("deps", help="dependency graph + audit (34/43/91/102)")
    sub.add_parser("api", help="API contract inventory (146-160/310)")

    # v1.6 agent-friendly features
    pr = sub.add_parser("predict", help="predict next context based on current operation")
    pr.add_argument("--operation", required=True)
    pr.add_argument("--symbol")
    pr.add_argument("--query")
    sc = sub.add_parser("suggest-context", help="suggest context for file editing")
    sc.add_argument("path")
    sc.add_argument("--line", type=int)

    # v1.8 intelligent repo analysis
    sub.add_parser("analyze", help="comprehensive repository analysis with actionable insights")

    # agent integration hooks
    hp = sub.add_parser("hook", help="agent integration hooks (post-edit, pre-edit)")
    hp.add_argument("hook_type", choices=["post-edit", "pre-edit"])
    hp.add_argument("args", nargs="+", help="hook-specific arguments")

    # session management
    sp = sub.add_parser("session", help="agent session management")
    session_sub = sp.add_subparsers(dest="session_cmd")
    session_sub.add_parser("start", help="start session with repo context")
    session_sub.add_parser("end", help="end session and collect learning data")
    session_sub.add_parser("status", help="show active session status")

    # verification gate
    vp = sub.add_parser("verify", help="verification gate: broken tests + typecheck + lint + audit")
    vp.add_argument("--typecheck", action="store_true", help="run typecheck as part of verification")
    vp.add_argument("--lint", action="store_true", help="run lint as part of verification")
    vp.add_argument("--no-audit", action="store_true", help="skip audit check")
    vp.add_argument("--blocking", action="store_true", help="exit 1 if verification fails")

    # learning loop
    lp = sub.add_parser("learning", help="learning loop: analyze sessions and update predictions")
    learning_sub = lp.add_subparsers(dest="learning_cmd")
    learning_sub.add_parser("analyze", help="analyze recent sessions for patterns")
    learning_sub.add_parser("update", help="update prediction confidence based on learning data")
    learning_sub.add_parser("report", help="generate comprehensive learning report")
    learning_sub.add_parser("patterns", help="detect agent-specific patterns")

    # v1.2 durability
    sub.add_parser("rebuild", help="wipe and fully reindex")
    vf = sub.add_parser("verify-index", help="check index vs disk drift"); vf.add_argument("--repair", action="store_true")
    vc = sub.add_parser("vacuum", help="compact DB, prune old events"); vc.add_argument("--days", type=int)

    # Master Data Model (L0-LA) CLI surface
    sub.add_parser("mdm-scan", help="run complete L0-LA extraction and synthesis")
    mr = sub.add_parser("mdm-report", help="generate comprehensive MDM executive report")
    mr.add_argument("--markdown", "-m", action="store_true", help="output report in markdown format")
    mt = sub.add_parser("mdm-trace", help="display explainability trace for a finding")
    mt.add_argument("finding_id", help="the finding ID to trace (e.g. LA-GAP-...)")
    sub.add_parser("mdm-gaps", help="list detected L4 silent wiring gaps and traps")

    return p

def dispatch_command(root, args):
    """Dispatch command to appropriate handler."""
    handlers = {
        "init": handle_init_command,
        "upgrade": handle_upgrade_command,
        "detect": handle_detect_command,
        "index": handle_index_command,
        "sync": handle_sync_command,
        "watch": handle_watch_command,
        "daemon": handle_daemon_command,
        "search": handle_search_command,
        "symbol": handle_symbol_command,
        "graph": handle_graph_command,
        "context": handle_context_command,
        "summary": handle_summary_command,
        "map": lambda r, a: _out(summarize.map_(r)),
        "describe": lambda r, a: _out(_server_describe(r, getattr(a, 'entity', None))),
        "broken": handle_broken_command,
        "hotspots": handle_hotspots_command,
        "history": handle_history_command,
        "route": handle_route_command,
        "git-index": handle_git_index_command,
        "ingest": handle_ingest_command,
        "export": handle_export_command,
        "doctor": handle_doctor_command,
        "serve": handle_serve_command,
        "mcp": handle_mcp_command,
        "tools": handle_tools_command,
        "hook": handle_hook_command,
        "audit": handle_audit_command,
        "findings": handle_findings_command,
        "impact": handle_impact_command,
        "session": handle_session_command,
        "verify": handle_verify_command,
        "learning": handle_learning_command,
        "selftest": handle_selftest_command,
        "suggest-context": handle_suggest_context_command,
        "analyze": handle_analyze_command,
        "rebuild": handle_rebuild_command,
        "verify-index": handle_verify_index_command,
        "vacuum": handle_vacuum_command,
        "embed": handle_embed_command,
        "dashboard-web": handle_dashboard_web_command,
        "web": handle_web_command,
        # v2 gap-fillers (F-16: registered but were never dispatched)
        "coverage": handle_coverage_command,
        "dead": handle_dead_command,
        "circular": handle_circular_command,
        "blame": handle_blame_command,
        "score": handle_score_command,
        "migrations": handle_migrations_command,
        "env": handle_env_command,
        "logs": handle_logs_command,
        "metrics": handle_metrics_command,
        "features": handle_features_command,
        "deps": handle_deps_command,
        "api": handle_api_command,
        "predict": handle_predict_command,
        "refactors": handle_refactors_command,
        "gate": handle_gate_command,
        "routes": handle_routes_command,
        "models": handle_models_command,
        "admission": handle_admission_command,
        "embedder": handle_embedder_command,
        "embed-ping": handle_embed_ping_command,
        # Master Data Model (L0-LA) commands
        "mdm-scan": handle_mdm_scan_command,
        "mdm-report": handle_mdm_report_command,
        "mdm-trace": handle_mdm_trace_command,
        "mdm-gaps": handle_mdm_gaps_command,
    }
    
    handler = handlers.get(args.cmd)
    if handler:
        return handler(root, args)
    else:
        print("unknown command: %s" % args.cmd)
        return 1

# ── main ─────────────────────────────────────────────────────────────────────

def main(argv=None):
    p = setup_argument_parser()

    a = p.parse_args(argv)
    if not a.cmd:
        p.print_help()
        return 0

    from .base import repo_root
    root = os.getcwd() if a.cmd == "init" else repo_root()

    return dispatch_command(root, a)


# Allow `python -m cipkg.cli <cmd>` to behave like `cip <cmd>` instead of being
# a silent no-op (module import without a `__main__` guard used to exit 0 doing
# nothing — AGENTS.md documents the `-m` form).
if __name__ == "__main__":
    import sys
    sys.exit(main())
