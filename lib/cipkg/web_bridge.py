"""
CIP Web Console backend — FastAPI app serving:
  - GET  /api/status          — live daemon/index/embedder status
  - GET  /api/config          — merged CIP config (sanitized)
  - GET  /api/commands        — command registry for palette
  - POST /api/run             — execute a command (async job)
  - POST /api/jobs/<id>/cancel — cancel a running job
  - WS   /ws                  — real-time event stream
  - GET  /*                   — SPA static files (built frontend)

MDM (Master Data Model L0–LA) Intelligence API:
  - GET  /api/mdm/scan        — run full L0–L9 extraction + LA synthesis
  - GET  /api/mdm/report      — executive dossier (json or ?format=markdown)
  - GET  /api/mdm/scorecard   — 5-dimensional health scorecard (lightweight)
  - GET  /api/mdm/gaps        — L4 IPC/event wiring gaps only
  - GET  /api/mdm/trace/<id>  — explainability trace for a specific finding

Designed per SPEC-15 §4: additive only, read-only DB on GET, no
modifications to core CIP modules.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Core CIP imports (read-only, no side effects) ─────────────────────────────
from .base import repo_root, load_config, cip_dir, DEFAULT_CONFIG
import contextvars

# ── Request-scoped root (SPEC-19 §4/§6.2) ──────────────────────────────────
_CURRENT_ROOT: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "cip_root", default=None
)

def _legacy_root() -> str | None:
    """GAP-02: console boots from ANY folder (registry-manager mode).

    repo_root() raises SystemExit (base.py:81) when no .cip exists above cwd;
    the central console must not crash - it falls back to registry-only mode
    where every endpoint requires an explicit ?repo=."""
    try:
        return repo_root()
    except SystemExit:
        return None

_LEGACY_ROOT = _legacy_root()  # fallback root; never touched by a ?repo= request

# GAP-05: auto-register launch root on console boot (idempotent)
if _LEGACY_ROOT:
    try:
        from .project_registry import get_registry
        # Honor CLI selection (GAP-04): CIP_WEB_ROOT env var overrides walk-up
        cli_root = os.environ.get("CIP_WEB_ROOT")
        if cli_root and os.path.isdir(cli_root):
            _LEGACY_ROOT = os.path.abspath(os.path.normcase(cli_root))
        get_registry().register(_LEGACY_ROOT)
    except Exception:
        # Fail silently on registry errors; console still boots in registry-only mode
        pass

def _root() -> str | None:
    return _CURRENT_ROOT.get() or _LEGACY_ROOT

def _require_root() -> str:
    """Helper for endpoints that require a root. Returns 4xx if no project selected."""
    r = _root()
    if not r:
        raise ValueError("NO_PROJECT")
    return r

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="CIP Web Console", version="2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request‑middleware: project scoping (SPEC-19 §4/§6.2) ─────────────────────
# Reads ``?repo=<id>`` or ``X-CIP-Project`` header and sets a request‑scoped root via
# the registry.  Missing/invalid repo leaves the legacy root untouched (SPEC-15 backward
# compat).  Registry‑validated keys prevent a hostile path string from injecting.
@app.middleware("http")
async def _project_scoping_middleware(request, call_next):
    from .project_registry import get_registry  # lazy import, safe: no circular dependency
    repo = request.query_params.get("repo") or request.headers.get("X-CIP-Project")
    token = None
    if repo:
        # Validate against registry before setting
        registry = get_registry()
        if registry.has(repo):
            token = _CURRENT_ROOT.set(repo)
    try:
        response = await call_next(request)
    finally:
        if token is not None:
            _CURRENT_ROOT.reset(token)
    return response


@app.exception_handler(RequestValidationError)
async def _validation_handler(request, exc):
    """Wrap FastAPI 422 validation errors in the stable _err envelope (NFR-1)."""
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(p) for p in first.get("loc", []) if p != "query")
    return JSONResponse(
        status_code=200,
        content=_err(
            "VALIDATION_ERROR",
            f"Invalid parameter {loc}: {first.get('msg', 'bad value')}",
        ),
    )


@app.exception_handler(ValueError)
async def _no_project_handler(request, exc):
    """Handle NO_PROJECT errors (GAP-02: registry-only mode)."""
    if str(exc) == "NO_PROJECT":
        return JSONResponse(
            status_code=200,
            content=_err("NO_PROJECT", "No project selected. Call with ?repo=<id>"),
        )
    raise  # re-raise other ValueErrors


# ── Helpers ────────────────────────────────────────────────────────────────────
def _ok(data: Any = None) -> dict:
    return {"ok": True, **({"data": data} if data is not None else {})}


def _err(code: str, message: str, core: str | None = None) -> dict:
    err: dict[str, Any] = {"code": code, "message": message}
    if core:
        err["core"] = core
    return {"ok": False, "error": err}


# ── Embedding safety (spec: web must never load a model or autostart daemon) ──
def _warm_daemon() -> int | None:
    """Cheap (<=0.5s) probe for an already-warm embed daemon; never starts one."""
    from .embed import service_health, service_port
    r = _root()
    if not r:
        return None
    port = service_port(load_config(r))
    h = service_health(port, timeout=0.5)
    if h and h.get("warm"):
        return port
    return None


# GAP-03 (P5 T5.4): per-project daemon bookkeeping. Keyed by project id so a
# second project with the same default daemon port never double-spawns — the
# first daemon is reused (`reused:true`) instead of binding-conflicting.
_DAEMONS: dict[str, dict] = {}


def _project_id_for_root(root: str) -> str:
    """Normalize a root to its registry project id (falls back to the path)."""
    from .project_registry import ProjectRegistry
    return ProjectRegistry.project_id(root)


def _port_in_use(port: int) -> bool:
    """True if something is already listening on ``port`` (TCP probe)."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


# ── Cheap TTL cache for heavy read-only GETs (SPEC-15 NFR-7 responsiveness) ──
_TTL_CACHE: dict[str, tuple[float, Any]] = {}
_TTL_CACHE_LOCK = threading.Lock()


def _ttl_cache(key: str, ttl: float, fn):
    """Return cached value if fresh, else compute + store under a lock.
    Keys are root-prefixed to prevent cross-project cache collisions (SPEC-19 §6.5)."""
    r = _root()
    root_prefixed_key = f"{r}|{key}" if r else key
    now = time.monotonic()
    with _TTL_CACHE_LOCK:
        hit = _TTL_CACHE.get(root_prefixed_key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    value = fn()
    with _TTL_CACHE_LOCK:
        _TTL_CACHE[root_prefixed_key] = (time.monotonic(), value)
    return value


# ── REST Endpoints ─────────────────────────────────────────────────────────────
@app.get("/api/status")
async def status():
    """Live status cluster for the four subsystems."""
    r = _root()
    if not r:
        return _err("NO_PROJECT", "No project selected. Call with ?repo=<id>")

    daemon_running = False
    daemon_pid: int | None = None
    daemon_uptime: str | None = None
    daemon_port: int | None = None
    index_fresh = False
    index_last_sync: str | None = None
    index_file_count = 0
    embed_backend = "hashing"
    embed_ready = False
    embed_warming = False

    # Daemon: probe the EFFECTIVE service port (CORE-10) — never a stale literal.
    try:
        import socket
        from .embed import service_port as _service_port
        daemon_port = _service_port(load_config(r))
        s = socket.create_connection(("localhost", daemon_port), timeout=1)
        s.close()
        daemon_running = True
        # Try to get PID from .cip/daemon.pid
        pid_file = Path(cip_dir(r)) / "daemon.pid"
        if pid_file.exists():
            daemon_pid = int(pid_file.read_text().strip())
    except (OSError, ValueError):
        pass

    # Index: check DB mtime
    db_path = Path(cip_dir(r)) / "index.db"
    if db_path.exists():
        mtime = db_path.stat().st_mtime
        age_s = time.time() - mtime
        index_fresh = age_s < 3600
        if age_s < 60:
            index_last_sync = "just now"
        elif age_s < 3600:
            index_last_sync = f"{int(age_s / 60)}m ago"
        else:
            index_last_sync = f"{int(age_s / 3600)}h ago"
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            row = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
            index_file_count = row[0] if row else 0
            conn.close()
        except Exception:
            pass

    # Embedder
    cfg = load_config(r)
    embed_backend = cfg.get("embed", {}).get("backend", "auto")
    embed_ready = embed_backend != "local"  # local needs warming

    return _ok({
        "repo_root": r,
        "daemon": {"running": daemon_running, "pid": daemon_pid, "uptime": daemon_uptime,
                   "port": daemon_port},
        "index": {"fresh": index_fresh, "last_sync": index_last_sync, "file_count": index_file_count},
        "embedder": {"backend": embed_backend, "ready": embed_ready, "warming": embed_warming},
    })


@app.get("/api/config")
async def config():
    """Return merged CIP config (sanitized — no secrets)."""
    r = _require_root()
    cfg = load_config(r)
    # Strip any keys that look like secrets
    sanitized = {k: v for k, v in cfg.items() if not any(s in k.lower() for s in ("secret", "key", "token", "password"))}
    return _ok(sanitized)


@app.get("/api/commands")
async def commands():
    """Registry catalog grouped by category, priority-sorted (SPEC-02 §4)."""
    return _ok(_catalog_bundle())


def _schema_type_to_api(prop: dict) -> str:
    """JSON-schema property type → CommandParam API type (SPEC-02 §4)."""
    return {
        "string": "string",
        "integer": "int",
        "number": "float",
        "boolean": "boolean",
        "array": "string",
    }.get(prop.get("type", "string"), "string")


def _catalog_bundle() -> dict:
    """Grouped command catalog {categories:[{name, commands}]} from the registry
    dispatch table (SPEC-02 §4). Replaces the argparse-derived flat list."""
    table = _command_table()
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for name, meta in table.items():
        cat = meta["category"]
        if cat not in groups:
            groups[cat] = []
            order.append(cat)
        groups[cat].append({
            "name": name,
            "description": meta["description"],
            "label": meta["label"],
            "category": cat,
            "priority": meta["priority"],
            "long_running": meta["long_running"],
            "requires_confirmation": meta["requires_confirmation"],
            "params": [
                {
                    "name": k,
                    "type": _schema_type_to_api(p),
                    "required": k in meta["schema"].get("required", []),
                    "default": p.get("default"),
                    "help": p.get("description", ""),
                    "choices": p.get("enum"),
                }
                for k, p in meta["schema"]["properties"].items()
            ],
        })
    prio = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for cat in order:
        groups[cat].sort(key=lambda c: (prio.get(c["priority"], 9), c["name"]))
    return {"categories": [{"name": cat, "commands": groups[cat]} for cat in order]}


def _command_registry() -> list[dict]:
    """Shared command registry (SPEC-02 dispatch table) used by /api/commands
    and /api/tools (SPEC-11 tools schema viewer)."""
    from .cli import setup_argument_parser
    parser = setup_argument_parser()
    cmds = []
    for action in parser._subparsers._actions:
        if hasattr(action, '_parser_class'):
            for name, sub in action._name_parser_map.items():
                # Extract help text from subparser
                sub_actions = [a for a in sub._actions if hasattr(a, 'option_strings')]
                params = []
                for a in sub_actions:
                    if a.option_strings:
                        pname = a.option_strings[0].lstrip('-')
                        params.append({
                            "name": pname,
                            "type": "boolean" if a.nargs == 0 else "string",
                            "required": a.required if hasattr(a, 'required') else False,
                            "default": a.default if a.default is not None else None,
                            "help": a.help or "",
                        })
                # Derive category from name
                category = _categorize(name)
                help_text = sub.description or ""
                cmds.append({
                    "name": name,
                    "description": help_text[:120],
                    "category": category,
                    "params": params,
                })
    return cmds


def _categorize(name: str) -> str:
    mapping = {
        "sync": "Index", "index": "Index", "rebuild": "Index", "verify-index": "Index", "vacuum": "Index",
        "search": "Search", "symbol": "Search", "refs": "Search",
        "analyze": "Quality", "audit": "Quality", "doctor": "Quality", "coverage": "Quality", "dead": "Quality", "circular": "Quality", "score": "Quality",
        "impact": "Analysis", "blame": "Analysis", "predict": "Analysis", "refactors": "Analysis",
        "daemon": "System", "embed": "System", "embedder": "System", "embed-ping": "System", "serve": "System", "mcp": "System", "tools": "System",
        "memory": "Memory", "learning": "Memory", "episodes": "Memory",
        "gate": "CI", "routes": "CI", "models": "CI", "admission": "CI",
        "config": "Config", "env": "Config", "features": "Config",
        "hook": "Hooks", "selftest": "Testing", "verify": "Testing",
        "init": "Setup",
    }
    return mapping.get(name, "Other")


# ── Event broadcast (thread-safe) ─────────────────────────────────────────────
_jobs: dict[str, dict] = {}
# P5 T5.1: _ws_clients is keyed by project id so broadcasts fan out to the
# connections subscribed to that project only. ``"*"`` = legacy / no-repo
# connections, which keep receiving un-scoped events (SPEC-15 backward compat).
_ws_clients: dict[str, set[WebSocket]] = {}
_loop: asyncio.AbstractEventLoop | None = None


def _repo_for_event(event: dict) -> str | None:
    """Best-effort project id carried by an event, if any (P5 T5.1)."""
    return event.get("repo") or (event.get("payload") or {}).get("repo")


async def _broadcast(event: dict, repo: str | None = None):
    """Send an event to the WS clients subscribed to one project.

    ``repo`` given → only that project's bucket plus the legacy ``"*"`` bucket
    (backward-compatible un-scoped clients). ``repo`` None → route by the
    event's own payload.repo if present, else the ``"*"`` bucket only."""
    if repo is None:
        repo = _repo_for_event(event)
    buckets = {"*"}
    if repo:
        buckets.add(repo)
    dead = set()
    for bucket in buckets:
        for ws in list(_ws_clients.get(bucket, ())):
            try:
                await ws.send_json(event)
            except Exception:
                dead.add(ws)
    if dead:
        for bucket in _ws_clients.values():
            bucket.difference_update(dead)


def _schedule_broadcast(event: dict, repo: str | None = None):
    """Schedule _broadcast from any thread (incl. worker threads)."""
    try:
        loop = _loop or asyncio.get_event_loop()
    except RuntimeError:
        return
    if loop.is_closed():
        return
    loop.call_soon_threadsafe(asyncio.create_task, _broadcast(event, repo))


def _register_job(command: str) -> str:
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {
        "id": job_id,
        "command": command,
        "status": "running",
        "started": time.time(),
        "cancelled": False,
        "logs": [],
    }
    return job_id


def _job_event(job_id: str, event_type: str, repo: str | None = None, **data):
    """Broadcast a normalized job event on the shared WS stream (thread-safe).

    GAP-01: single writer for the modern job event vocab
    (job.progress | job.log | job.done | job.error | job.cancelled).
    ``repo`` scopes the broadcast to one project (P5 T5.1); default None keeps
    legacy un-scoped behavior (the ``"*"`` bucket).
    """
    _schedule_broadcast({
        "type": event_type,
        "job_id": job_id,
        "command": _jobs.get(job_id, {}).get("command"),
        "data": data,
        "timestamp": time.time(),
        "repo": repo,
    }, repo=repo)


def _job_progress(job_id: str, pct: int, phase: str | None = None,
                  current: int = 0, total: int = 0,
                  message: str | None = None, stage: str | None = None,
                  repo: str | None = None):
    """Broadcast a job.progress event with server-derived pct (SPEC-02 §4:
    {id, phase, current, total, pct}). `phase` wins over legacy `stage`."""
    _job_event(job_id, "job.progress", repo=repo, pct=pct,
               phase=phase or stage, current=current, total=total,
               message=message)


def _job_log(job_id: str, line: str, repo: str | None = None):
    """Append a log line to the job and broadcast it (job.log)."""
    job = _jobs.get(job_id)
    if job is not None:
        job["logs"].append(line)
    _job_event(job_id, "job.log", repo=repo, line=line)


def _job_done(job_id: str, message: str | None = None, repo: str | None = None, **extra):
    """Mark a job done and broadcast job.done with a real duration_s."""
    if job_id in _jobs:
        started = _jobs[job_id].get("started") or time.time()
        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["finished"] = time.time()
        _job_event(job_id, "job.done", repo=repo, status="done",
                   duration_s=round(time.time() - started, 3), message=message, **extra)


def _job_error(job_id: str, message: str, repo: str | None = None):
    if job_id in _jobs:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = message
        _jobs[job_id]["finished"] = time.time()
        _job_event(job_id, "job.error", repo=repo, error=message)


def _job_cancelled(job_id: str, repo: str | None = None):
    if job_id in _jobs:
        _jobs[job_id]["status"] = "cancelled"
        _jobs[job_id]["finished"] = time.time()
        _job_event(job_id, "job.cancelled", repo=repo, status="cancelled")


@app.get("/api/jobs")
async def jobs_list_endpoint(limit: int = 50):
    """Job history, newest first; log bodies trimmed (use detail for full tails)."""
    jobs = sorted(_jobs.values(), key=lambda j: j.get("started", 0) or 0, reverse=True)[:limit]
    body = []
    for j in jobs:
        entry = {k: v for k, v in j.items() if k != "logs"}
        entry["log_count"] = len(j.get("logs", []))
        body.append(entry)
    return _ok({"jobs": body, "count": len(body)})


@app.get("/api/jobs/{job_id}")
async def jobs_get_endpoint(job_id: str):
    """Job detail including the last 50 log lines."""
    job = _jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content=_err("NOT_FOUND", f"Job {job_id} not found"))
    entry = dict(job)
    entry["logs"] = list(job.get("logs", []))[-50:]
    return _ok(entry)


# ── SPEC-03: Daemon & Server Management ───────────────────────────────────────
@app.get("/api/daemon")
async def daemon_status_endpoint():
    """Merged daemon status: daemon_status(root) + embed.service_health(port)."""
    from . import daemon, embed
    r = _require_root()
    info = daemon.daemon_status(r)
    # GAP-03: surface the per-project bookkeeping so the UI sees which daemon
    # actually serves this project (reuse/conflict state). Always present so the
    # API contract is stable even when no daemon has been tracked yet.
    pid_key = _project_id_for_root(r)
    tracked = _DAEMONS.get(pid_key)
    info["tracked_pid"] = tracked.get("pid") if tracked else None
    info["reused"] = bool(tracked and tracked.get("reused", False))
    health = None
    if info.get("port"):
        health = embed.service_health(info["port"])
    if health:
        info["health"] = health
        info["warm"] = health.get("warm", False)
    return _ok(info)


@app.get("/api/daemon/log")
async def daemon_log_endpoint(lines: int = 200):
    """Tail of daemon.log (append-only free text)."""
    from .daemon import read_log
    r = _require_root()
    tail = read_log(r, lines=max(1, min(lines, 5000)))
    return _ok({"lines": tail, "count": len(tail)})


class DaemonActionRequest(BaseModel):
    port: int | None = None
    interval: float = 1.0


@app.post("/api/daemon/start")
async def daemon_start_endpoint(req: DaemonActionRequest | None = None, port: int | None = None, interval: float = 1.0):
    """Start the daemon as a separate subprocess (non-blocking job).

    GAP-03 guard: if a CIP daemon already runs for this project (tracked in
    ``_DAEMONS`` or its lock file alive) → return ``{reused:true, pid}`` with no
    spawn. If the resolved port is taken by a non-CIP process → ``_err``."""
    from . import daemon
    from .embed import service_port as _service_port
    r = _require_root()
    pid_key = _project_id_for_root(r)
    req_port = req.port if req is not None else None
    req_interval = req.interval if req is not None else interval
    resolved_port = req_port or port or _service_port(load_config(r))
    job_id = _register_job("daemon start")

    # GAP-03: never double-spawn — reuse the already-running daemon.
    status = daemon.daemon_status(r)
    if status.get("alive"):
        _DAEMONS[pid_key] = {"port": status.get("port") or resolved_port,
                             "pid": status.get("pid"), "reused": True}
        return _ok({"job_id": job_id, "status": "running", "port": status.get("port"),
                    "pid": status.get("pid"), "reused": True})

    # GAP-03: port already taken by a non-CIP process → refuse, don't fight it.
    if _port_in_use(resolved_port):
        return _err("DAEMON_PORT_CONFLICT", f"Port {resolved_port} is already in use by another process")

    def _work():
        try:
            proc = daemon.start_daemon(r, port=resolved_port, interval=req_interval)
            if proc is None:
                _job_progress(job_id, 100, stage="start",
                              message="daemon already running or failed to spawn")
            else:
                _job_progress(job_id, 100, stage="start", message="daemon spawned")
            # record the per-project daemon once spawned (GAP-03 bookkeeping)
            _DAEMONS[pid_key] = {"port": resolved_port,
                                 "pid": proc.pid if proc else None,
                                 "reused": False}
            _job_done(job_id, repo=r,
                      message=f"daemon started (pid {proc.pid})" if proc else "daemon already running",
                      pid=proc.pid if proc else None)
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)

    threading.Thread(target=_work, daemon=True).start()
    return _ok({"job_id": job_id, "status": "running"})


@app.post("/api/daemon/stop")
async def daemon_stop_endpoint():
    """Stop the daemon (job)."""
    from .daemon import daemon_stop
    r = _require_root()
    pid_key = _project_id_for_root(r)
    job_id = _register_job("daemon stop")

    def _work():
        try:
            daemon_stop(r)
            _DAEMONS.pop(pid_key, None)
            _job_done(job_id, repo=r, message="daemon stopped")
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)

    threading.Thread(target=_work, daemon=True).start()
    return _ok({"job_id": job_id, "status": "running"})


@app.post("/api/daemon/restart")
async def daemon_restart_endpoint(req: DaemonActionRequest | None = None, port: int | None = None):
    """Stop then start the daemon (single job)."""
    from .daemon import daemon_stop, start_daemon
    from .embed import service_port as _service_port
    r = _require_root()
    pid_key = _project_id_for_root(r)
    req_port = req.port if req is not None else None
    resolved_port = req_port or port or _service_port(load_config(r))
    job_id = _register_job("daemon restart")

    def _work():
        try:
            _job_progress(job_id, 50, stage="stop", message="stopping daemon", repo=r)
            daemon_stop(r)
            _DAEMONS.pop(pid_key, None)
            _job_progress(job_id, 100, stage="start", message="starting daemon", repo=r)
            proc = start_daemon(r, port=resolved_port)
            _DAEMONS[pid_key] = {"port": resolved_port,
                                 "pid": proc.pid if proc else None,
                                 "reused": False}
            _job_done(job_id, repo=r,
                      message=f"daemon restarted (pid {proc.pid if proc else 'n/a'})")
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)

    threading.Thread(target=_work, daemon=True).start()
    return _ok({"job_id": job_id, "status": "running"})


@app.post("/api/daemon/auto-manage")
async def daemon_auto_manage_endpoint(enabled: bool = True):
    """Set [web].auto_manage_daemon in .cip/config.toml."""
    r = _require_root()
    cfg_path = Path(cip_dir(r)) / "config.toml"
    try:
        import tomlkit
        doc = tomlkit.parse(cfg_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        doc = tomlkit.document()
    if "web" not in doc:
        doc["web"] = tomlkit.table()
    doc["web"]["auto_manage_daemon"] = enabled
    cfg_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    return _ok({"auto_manage_daemon": enabled})


# ── SPEC-04 §6.1/6.2: Watch manager (CORE-16) ────────────────────────────────
class WatchManager:
    """Runs watch.watch in a background thread with a stop flag (CORE-16).

    watch is an infinite loop; this wrapper makes it start/stop-able from the UI
    and surfaces its `sync` phases + completions over WS as `watch.event` /
    `index.update` broadcasts (SPEC-04 addition 2). A single instance may run at
    most once — start() is a no-op while already running.

    P5 T5.2/5.3: watchers are tracked per project (``self._watchers: dict``
    keyed by project id) so multiple projects can be watched simultaneously and
    ``file.changed`` broadcasts can be emitted project-scoped. Watchers are lazy:
    only started when a project is activated, never on GET /api/projects.
    """

    def __init__(self):
        # project_id -> {"stop": Event, "thread": Thread|None, "interval": float}
        self._watchers: dict[str, dict] = {}
        self._lock = threading.Lock()

    def _key(self, repo: str | None) -> str:
        """Normalize a ?repo= value (registry id) or fall back to active/legacy root."""
        if repo:
            return _project_id_for_root(repo)
        r = _root()
        return _project_id_for_root(r) if r else "*"

    def running(self, repo: str | None = None) -> bool:
        key = self._key(repo)
        with self._lock:
            w = self._watchers.get(key)
        return bool(w and w["thread"] and w["thread"].is_alive())

    def start(self, interval: float = 1.0, repo: str | None = None) -> str:
        with self._lock:
            key = self._key(repo)
            w = self._watchers.get(key)
            if w and w["thread"] and w["thread"].is_alive():
                return "already-running"
            w = {"stop": threading.Event(), "thread": None, "interval": max(0.5, float(interval))}
            self._watchers[key] = w
            # P5 T5.2: the loop needs the project key for project-scoped broadcasts
            w["thread"] = threading.Thread(
                target=self._run, args=(key,), kwargs={"interval": w["interval"]},
                daemon=True, name="cip-watch")
            w["thread"].start()
            _schedule_broadcast({"type": "watch.event", "kind": "start"}, repo=key)
            return "started"

    def stop(self, repo: str | None = None) -> str:
        with self._lock:
            key = self._key(repo)
            w = self._watchers.get(key)
            if not w or not w["thread"] or not w["thread"].is_alive():
                return "not-running"
            w["stop"].set()
            # NOTE: keep w["thread"]; running() reports alive until the loop
            # actually exits, and _run's finally clears the flag so status()
            # returns to idle instead of showing "stopping" forever. start()
            # refuses while the thread is still alive, so no race on the flag.
            _schedule_broadcast({"type": "watch.event", "kind": "stop"}, repo=key)
            return "stopping"

    def status(self, repo: str | None = None) -> dict:
        key = self._key(repo)
        with self._lock:
            w = self._watchers.get(key)
        if not w:
            return {"running": False, "interval": 1.0, "stopping": False, "project": key}
        return {"running": bool(w["thread"] and w["thread"].is_alive()),
                "interval": w["interval"],
                "stopping": w["stop"].is_set(),
                "project": key}

    def running_projects(self) -> list[str]:
        """Ids of projects with a live watcher (P5 T5.3 lazy-activation check)."""
        with self._lock:
            return [k for k, w in self._watchers.items()
                    if w["thread"] and w["thread"].is_alive()]

    def stop_project(self, repo: str) -> str:
        """Stop the watcher for one project (T5.3 deactivation path)."""
        return self.stop(repo=repo)

    def _run(self, project_id: str, interval: float = 1.0):
        from . import watch as _watch
        # resolve the root for this project id (registry) or the legacy root
        from .project_registry import get_registry
        with self._lock:
            w = self._watchers.get(project_id)
            if not w:
                return
            stop = w["stop"]

        def progress(kind, cur, tot):
            _schedule_broadcast({"type": "watch.event", "kind": "progress",
                                 "phase": kind, "cur": cur, "tot": tot}, repo=project_id)

        def on_sync(stats):
            _schedule_broadcast({"type": "index.update", "kind": "sync",
                                 "dirty": stats.get("dirty"), "deleted": stats.get("deleted"),
                                 "embedded": stats.get("embedded"), "ms": stats.get("ms")},
                                repo=project_id)

        try:
            # wrap indexer.sync so a completed watch-sync also broadcasts;
            # watch.watch itself calls sync() without the wrapper, so intercept
            # by monkeypatching is avoided — instead we relay via progress and
            # rely on the daemon/log surfaces for raw stats. (CORE-16 scope:
            # stop flag + WS progress; full sync-stats relay is the job layer.)
            root = get_registry().get(project_id)["root"] if project_id != "*" else _root()
            if not root:
                root = _root()
            r = root
            _watch.watch(r, interval=interval, verbose=False,
                         stop_event=stop, progress=progress,
                         on_change=lambda paths: self._emit_file_changed(project_id, r, paths))
        except Exception as exc:
            _schedule_broadcast({"type": "watch.event", "kind": "error",
                                 "error": str(exc)}, repo=project_id)
        finally:
            # Clear the stop flag so status() reverts to idle (running=False,
            # stopping=False) — mirrors the "stopping" phase in the UI badge.
            stop.clear()
            _schedule_broadcast({"type": "watch.event", "kind": "exit"}, repo=project_id)

    def _emit_file_changed(self, project_id: str, root: str, rel_paths: list[str]):
        """P5 T5.2 / SPEC-18 producer: relay each changed file to `project_id`'s clients."""
        for rel in rel_paths:
            _schedule_broadcast({
                "type": "file.changed",
                "payload": {"path": rel, "repo": project_id, "root": root},
                "timestamp": time.time(),
            }, repo=project_id)


_WATCH = WatchManager()


@app.get("/api/watch/status")
async def watch_status_endpoint(repo: str | None = None):
    """Watch worker status (running/interval/stopping). ?repo= spaces it per project."""
    return _ok(_WATCH.status(repo))


@app.post("/api/watch/start")
async def watch_start_endpoint(interval: float = 1.0, repo: str | None = None):
    """Start the background watch loop (thread; never blocks a request).

    ``repo`` scopes it to one project; default keeps legacy un-scoped behavior."""
    result = _WATCH.start(interval=interval, repo=repo)
    return _ok({"result": result, **_WATCH.status(repo)})


@app.post("/api/watch/stop")
async def watch_stop_endpoint(repo: str | None = None):
    """Stop the watch loop at the next tick."""
    result = _WATCH.stop(repo)
    return _ok({"result": result, **_WATCH.status(repo)})


# P5 T5.3: activation hook — starts/stops the watcher for a project when it
# becomes/ceases to be the active console project (lazy, PLAN-06 wires it).
@app.post("/api/watch/activate")
async def watch_activate_endpoint(repo: str, active: bool = True):
    """T5.3: lazily start (active) or stop (inactive) a project's watcher."""
    from .project_registry import get_registry
    key = _project_id_for_root(repo)
    if active:
        if not get_registry().has(key):
            return _err("UNKNOWN_PROJECT", f"Project not registered: {repo}")
        result = _WATCH.start(repo=key)
    else:
        result = _WATCH.stop(repo=key)
    return _ok({"result": result, **_WATCH.status(key)})


# ── SPEC-10: Settings & Config (FR-10 write-now) ─────────────────────────────
def _config_path() -> Path:
    """Dynamic config path based on current root (request-scoped)."""
    return Path(cip_dir(_require_root())) / "config.toml"

# Type hints / descriptions for the schema. Keys mirror `config.default.toml`
# (defaults.cfg is the merged DEFAULT_CONFIG + TOML defaults).
_CONFIG_HINTS: dict[str, dict[str, dict]] = {
    "index": {
        "max_file_kb": {"type": "int", "min": 1, "desc": "Max indexable file size (KB)"},
        "exclude": {"type": "array", "desc": "Directory/pattern exclusions (hard defaults always apply)"},
        "include": {"type": "array", "desc": "Restrict indexing to these paths"},
        "test_globs": {"type": "array", "desc": "Test-file markers"},
        "exclude_patterns": {"type": "array", "desc": "[deprecated alias of exclude]"},
        "max_file_size": {"type": "int", "min": 1, "desc": "[deprecated: bytes; use max_file_kb]"},
    },
    "embed": {
        "backend": {"type": "str", "choices": ["auto", "local", "service", "hashing"], "desc": "Embedding backend"},
        "model": {"type": "str", "desc": "Local embedding model"},
        "dim": {"type": "int", "min": 1, "desc": "Embedding dimensions"},
        "autostart": {"type": "bool", "desc": "Auto-start embed daemon (web never does)"},
        "service_port": {"type": "int", "min": 1, "max": 65535, "desc": "Warm-model service port"},
    },
    "retrieval": {
        "lexical_k": {"type": "int", "min": 1, "desc": "Lexical search top-k"},
        "vector_k": {"type": "int", "min": 1, "desc": "Vector search top-k"},
        "context_budget_tokens": {"type": "int", "min": 1000, "desc": "Context budget (tokens)"},
        "hybrid_weight": {"type": "float", "min": 0.0, "max": 1.0, "desc": "Semantic weight (0..1)"},
        "max_results": {"type": "int", "min": 1, "desc": "Max results"},
    },
    "memory": {
        "enable_temporal": {"type": "bool", "desc": "Temporal knowledge graph"},
        "enable_episodic": {"type": "bool", "desc": "Episodic memory"},
        "enable_procedural": {"type": "bool", "desc": "Procedural memory"},
        "consolidation_interval": {"type": "int", "min": 1, "desc": "Seconds between consolidations"},
        "max_episodes": {"type": "int", "min": 1, "desc": "Episodes retained"},
        "consolidation_lookback_days": {"type": "int", "min": 1, "desc": "Consolidation lookback (days)"},
        "memory_db": {"type": "str", "desc": "Facts DB (relative to .cip/)"},
        "episodes_db": {"type": "str", "desc": "Episodes DB (relative to .cip/)"},
    },
    "mcp": {
        "host": {"type": "str", "desc": "MCP bind host"},
        "port": {"type": "int", "min": 1, "max": 65535, "desc": "MCP port"},
        "autostart": {"type": "bool", "desc": "Auto-start MCP server"},
    },
    "daemon": {
        "host": {"type": "str", "desc": "Daemon bind host"},
        "port": {"type": "int", "min": 1, "max": 65535, "desc": "Daemon port"},
        "enable_watcher": {"type": "bool", "desc": "File watcher"},
        "watcher_interval": {"type": "int", "min": 1, "desc": "Watcher poll (seconds)"},
    },
    "analysis": {
        "audit_refresh_interval": {"type": "int", "min": 1, "desc": "Audit refresh (seconds)"},
        "max_findings": {"type": "int", "min": 1, "desc": "Max findings surfaced"},
    },
    "logging": {
        "level": {"type": "str", "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], "desc": "Log level"},
        "debug": {"type": "bool", "desc": "Show swallowed exceptions"},
        "max_size": {"type": "int", "min": 1, "desc": "Log file max bytes"},
        "backup_count": {"type": "int", "min": 0, "desc": "Rotated log backups"},
    },
    "performance": {
        "worker_threads": {"type": "int", "min": 0, "desc": "[legacy alias of perf.workers]"},
        "parallel_indexing": {"type": "bool", "desc": "Parallel index builds"},
        "max_parallel_workers": {"type": "int", "min": 1, "desc": "Parallel worker cap"},
    },
    "perf": {"workers": {"type": "int", "min": 0, "desc": "0=auto, 1=serial, N=explicit"}},
    "git": {"depth": {"type": "int", "min": 1, "desc": "Git history depth"}, "co_change_min": {"type": "int", "min": 1, "desc": "Co-change minimum"}},
    "maintain": {"event_days": {"type": "int", "min": 1, "desc": "Event retention (days)"}},
    "summary": {"backend": {"type": "str", "choices": ["structural", "llm"], "desc": "Summary backend"}, "llm_model": {"type": "str", "desc": "LLM model"}, "max_llm_per_sync": {"type": "int", "min": 0, "desc": "LLM summaries per sync"}},
    "rerank": {"enabled": {"type": "bool", "desc": "Enable reranking"}},
    "vector": {"backend": {"type": "str", "choices": ["sqlite", "sqlite-vec"], "desc": "Vector backend"}},
    "audit": {"ignore_rules": {"type": "array", "desc": "Rules to suppress"}, "custom_rules_path": {"type": "str", "desc": "Extra rules JSON file"}},
    "stack": {
        "prisma_store_contracts": {"type": "bool", "desc": "Prisma schema & contract validation"},
        "tauri_enabled": {"type": "bool", "desc": "Tauri desktop app integration"},
    },
    "profile": {
        "name": {"type": "str", "desc": "Active repo profile name"},
    },
    "web": {"host": {"type": "str", "desc": "Web host"}, "port": {"type": "int", "min": 1, "max": 65535, "desc": "Web port (8090)"}, "open_browser": {"type": "bool", "desc": "Open browser on start"}, "auto_manage_daemon": {"type": "bool", "desc": "Auto-start daemon with web"}},
    "serve": {"port": {"type": "int", "min": 1, "max": 65535, "desc": "[legacy; prefer [web] port]"}},
}

_SCHEMA_ORDER = [
    "index", "stack", "embed", "retrieval", "memory", "mcp", "daemon", "analysis",
    "logging", "performance", "perf", "git", "maintain", "summary", "rerank",
    "vector", "audit", "web", "serve",
]


class ConfigUpdatesRequest(BaseModel):
    updates: dict[str, Any]


class ConfigResetRequest(BaseModel):
    section: str | None = None
    keys: list[str] | None = None


def _effective_meta() -> int | None:
    """Live DB schema version (CORE-40: never trust config [meta].schema_version=11)."""
    try:
        r = _require_root()
        db = Path(cip_dir(r)) / "index.db"
        if not db.exists():
            return None
        import sqlite3
        con = sqlite3.connect(str(db))
        row = con.execute(
            "SELECT value FROM meta WHERE key='schema_version'").fetchone()
        con.close()
        return int(row[0]) if row else None
    except Exception:
        return None


def _get_detected_profile(root: str) -> dict:
    """Resolve active repo profile, source files, and configuration."""
    try:
        cip_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        repo_settings_dir = os.path.join(cip_base_dir, "repo-settings")
        if repo_settings_dir not in sys.path:
            sys.path.insert(0, repo_settings_dir)
        from detectors import detect_repo_type, load_repo_profile
        repo_type = detect_repo_type(root)
        profile_cfg = load_repo_profile(repo_type)
        profiles_dir = os.path.join(repo_settings_dir, "profiles")
        folder = os.path.join(profiles_dir, repo_type)
        if os.path.isdir(folder):
            p_files = sorted([f for f in os.listdir(folder) if f.endswith('.toml')])
            p_dir = folder
        else:
            single = os.path.join(profiles_dir, f"{repo_type}.toml")
            p_files = [f"{repo_type}.toml"] if os.path.exists(single) else []
            p_dir = single if os.path.exists(single) else None
        return {
            "repo_type": repo_type,
            "profile_dir": p_dir,
            "profile_files": p_files,
            "profile_config": profile_cfg,
        }
    except Exception as exc:
        return {
            "repo_type": "generic",
            "profile_dir": None,
            "profile_files": [],
            "profile_config": {},
            "error": str(exc),
        }


def _config_sources() -> dict:
    """Per-key provenance: config.toml / profile / default."""
    import tomllib
    r = _require_root()
    cfg = load_config(r)
    file_cfg: dict = {}
    if _config_path().exists():
        try:
            with open(_config_path(), "rb") as f:
                file_cfg = tomllib.load(f)
        except Exception:
            file_cfg = {}
    sources: dict[str, dict[str, str]] = {}
    for section, kv in cfg.items():
        if not isinstance(kv, dict):
            continue
        sources[section] = {}
        for key in kv:
            if isinstance(file_cfg.get(section), dict) and key in file_cfg[section]:
                sources[section][key] = "config.toml"
            elif section in DEFAULT_CONFIG and key in DEFAULT_CONFIG[section]:
                if DEFAULT_CONFIG[section][key] != kv[key]:
                    sources[section][key] = "profile"
                else:
                    sources[section][key] = "default"
            else:
                sources[section][key] = "profile"
    return sources


def config_schema_endpoint():
    """Build per-key schema (type, default, range, source) driving the form."""
    r = _require_root()
    schema = {}
    sources = _config_sources()
    for section in _SCHEMA_ORDER:
        if section not in DEFAULT_CONFIG:
            continue
        defaults = DEFAULT_CONFIG.get(section, {})
        if not isinstance(defaults, dict):
            continue
        hints = _CONFIG_HINTS.get(section, {})
        entries = {}
        for key, default in defaults.items():
            hint = hints.get(key, {})
            typ = hint.get("type") or (
                "bool" if isinstance(default, bool)
                else "int" if isinstance(default, int)
                else "float" if isinstance(default, float)
                else "array" if isinstance(default, list)
                else "str")
            entries[key] = {
                "type": typ,
                "default": default,
                "desc": hint.get("desc", ""),
                "choices": hint.get("choices"),
                "min": hint.get("min"),
                "max": hint.get("max"),
                "source": sources.get(section, {}).get(key, "default"),
            }
        if entries:
            schema[section] = entries
    return _ok({
        "schema": schema,
        "live_schema_version": _effective_meta(),
        "declared_schema_version": (load_config(r).get("meta") or {}).get("schema_version"),
        "detected_profile": _get_detected_profile(r),
    })


def _apply_updates_to_doc(doc, updates: dict) -> tuple[list[str], list[str]]:
    """Apply {section:{key:value}} onto a tomlkit doc. Returns (written, errors)."""
    written: list[str] = []
    errors: list[str] = []
    for section, kv in (updates or {}).items():
        hints = _CONFIG_HINTS.get(section, {})
        allowed = set((DEFAULT_CONFIG.get(section) or {}).keys())
        if not isinstance(kv, dict):
            errors.append(f"{section}: value must be an object")
            continue
        if section not in doc:
            doc[section] = __import__("tomlkit").table()
        for key, value in kv.items():
            hint = hints.get(key, {})
            # Reject unknown keys (silently-ignored keys = CORE-39/42 risk)
            if allowed and key not in allowed and key not in ("include", "prisma_store_contracts", "tauri_enabled"):
                errors.append(f"{section}.{key}: unknown key (rejected, not written)")
                continue
            # Deprecated aliases map to live keys (CORE-39)
            if section == "index" and key == "exclude_patterns":
                key = "exclude"
            if section == "index" and key == "max_file_size":
                key = "max_file_kb"
            if section == "performance" and key == "worker_threads":
                section, key = "perf", "workers"
            if key.startswith("_") or key.startswith("__"):
                errors.append(f"{section}.{key}: reserved key")
                continue
            typecheck = hint.get("type")
            if typecheck == "bool" and not isinstance(value, bool):
                errors.append(f"{section}.{key}: expected bool")
                continue
            if typecheck == "int" and not isinstance(value, int):
                errors.append(f"{section}.{key}: expected int")
                continue
            if typecheck == "float" and not isinstance(value, (int, float)):
                errors.append(f"{section}.{key}: expected number")
                continue
            if typecheck == "array" and not isinstance(value, list):
                errors.append(f"{section}.{key}: expected array")
                continue
            if "min" in hint and isinstance(value, (int, float)) and value < hint["min"]:
                errors.append(f"{section}.{key}: must be >= {hint['min']}")
                continue
            if "max" in hint and isinstance(value, (int, float)) and value > hint["max"]:
                errors.append(f"{section}.{key}: must be <= {hint['max']}")
                continue
            if hint.get("choices") and value not in hint["choices"]:
                errors.append(f"{section}.{key}: must be one of {hint['choices']}")
                continue
            doc[section][key] = value
            written.append(f"{section}.{key}")
    return written, errors


def config_bundle_endpoint():
    """{effective, file, defaults, sources, detected_profile} — three-way transparency (§3)."""
    import tomllib
    r = _require_root()
    cfg = load_config(r)
    file_cfg: dict = {}
    if _config_path().exists():
        try:
            with open(_config_path(), "rb") as f:
                file_cfg = tomllib.load(f)
        except Exception:
            file_cfg = {}
    return _ok({
        "effective": cfg,
        "file": file_cfg,
        "defaults": DEFAULT_CONFIG,
        "sources": _config_sources(),
        "detected_profile": _get_detected_profile(r),
    })


@app.get("/api/config/profiles")
async def config_profiles_endpoint():
    """List available repo profile templates in repo-settings."""
    try:
        cip_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        profiles_dir = os.path.join(cip_base_dir, "repo-settings", "profiles")
        profiles = []
        if os.path.isdir(profiles_dir):
            for entry in sorted(os.listdir(profiles_dir)):
                full = os.path.join(profiles_dir, entry)
                if os.path.isdir(full):
                    toml_files = [f for f in os.listdir(full) if f.endswith('.toml')]
                    profiles.append({"id": entry, "name": entry, "is_dir": True, "files": toml_files})
                elif entry.endswith('.toml'):
                    base_name = entry[:-5]
                    profiles.append({"id": base_name, "name": base_name, "is_dir": False, "files": [entry]})
        return _ok({"profiles": profiles})
    except Exception as exc:
        return _err("PROFILES_LIST_FAILED", str(exc))


@app.get("/api/config/schema")
async def config_schema_route():
    """Per-key schema driving the settings form (server is source of truth)."""
    return config_schema_endpoint()


@app.get("/api/config/full")
async def config_full_route():
    """Three-way config bundle (effective / file / defaults / sources)."""
    return config_bundle_endpoint()


@app.post("/api/config/validate")
async def config_validate_route(req: ConfigUpdatesRequest):
    """Type + range validation only — no write (§4)."""
    import tomlkit
    doc = tomlkit.document()
    _, errors = _apply_updates_to_doc(doc, req.updates)
    if errors:
        return _ok({"ok": False, "errors": errors})
    return _ok({"ok": True, "errors": []})


@app.post("/api/config/save")
async def config_save_route(req: ConfigUpdatesRequest):
    """Write-back to .cip/config.toml (tomlkit, preserve comments, .bak backup)."""
    import tomlkit
    updates = req.updates
    # Existing doc (preserve comments/order) or fresh
    try:
        doc = tomlkit.parse(_config_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        doc = tomlkit.document()

    written, errors = _apply_updates_to_doc(doc, updates)
    if errors:
        return _ok({"ok": False, "errors": errors, "written_keys": written})

    # Atomic write + .bak backup (§4)
    r = _require_root()
    before = load_config(r)
    if _config_path().exists():
        _config_path().with_suffix(".toml.bak").write_text(
            _config_path().read_text(encoding="utf-8"), encoding="utf-8")
    tmp = _config_path().with_suffix(".toml.tmp")
    tmp.write_text(tomlkit.dumps(doc), encoding="utf-8")
    os.replace(tmp, _config_path())

    # Rebuild effective diff: which live values changed?
    after = load_config(r)
    diff = {}
    for section, kv in updates.items():
        if not isinstance(kv, dict):
            continue
        for key, value in kv.items():
            diff[f"{section}.{key}"] = {
                "from": before.get(section, {}).get(key),
                "to": after.get(section, {}).get(key),
            }
    _schedule_broadcast({
        "type": "config.update", "command": "config save",
        "data": {"written_keys": written, "diff": diff},
        "timestamp": time.time(), "repo": r}, repo=r)
    return _ok({"ok": True, "written_keys": written, "diff": diff})


@app.post("/api/config/reset")
async def config_reset_route(req: ConfigResetRequest):
    """Remove override(s): {section} or {section, keys:[...]} (§4)."""
    import tomlkit
    section = req.section
    keys = req.keys
    try:
        doc = tomlkit.parse(_config_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        doc = tomlkit.document()

    removed: list[str] = []
    if section:
        if section not in doc:
            return _ok({"ok": True, "removed": []})
        if keys:
            for key in keys:
                if key in doc[section]:
                    del doc[section][key]
                    removed.append(f"{section}.{key}")
        else:
            del doc[section]
            removed.append(section)
    tmp = _config_path().with_suffix(".toml.tmp")
    tmp.write_text(tomlkit.dumps(doc), encoding="utf-8")
    os.replace(tmp, _config_path())
    _schedule_broadcast({
        "type": "config.update", "command": "config reset",
        "data": {"removed": removed},
        "timestamp": time.time(), "repo": _project_id_for_root(_root()),
    }, repo=_project_id_for_root(_root()))
    return _ok({"ok": True, "removed": removed})


@app.post("/api/config/reload")
async def config_reload_route():
    """Job that re-runs load_config + clears caches, hot-applies safe keys (§6.3)."""
    r = _require_root()  # capture for the job thread (request contextvar is lost)
    job_id = _register_job("config reload")

    def _work():
        try:
            # Clear bridge-level caches so next reads re-derive
            global _QUALITY_CACHE, _MEM_CACHE, _VIS_CACHE
            _QUALITY_CACHE = {"ts": 0.0, "data": None}
            _MEM_CACHE = {"ts": 0.0, "data": None}
            _VIS_CACHE = {}
            # embedder cache (module-level dict)
            from . import embed
            embed._EMBEDDER_CACHE.clear()
            cfg = load_config(r)
            _job_done(job_id, repo=r, message="config reloaded",
                      sections=sorted(cfg.keys()))
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)

    threading.Thread(target=_work, daemon=True).start()
    return _ok({"job_id": job_id, "status": "running"})


@app.get("/api/env")
async def env_endpoint():
    """Sanitized environment surface — no secrets (§2 FR-15)."""
    keep = {
        "CIP_ROOT", "CIP_CONFIG", "CIP_LOG_LEVEL",
        "CIP_DAEMON_PORT", "CIP_MCP_PORT", "CIP_DEBUG",
    }
    env = {
        k: os.environ[k]
        for k in keep
        if k in os.environ and not any(
            s in k.lower() for s in ("key", "token", "secret", "password"))
    }
    r = _require_root()
    env.setdefault("CIP_ROOT", r)
    env.setdefault("CIP_CONFIG", os.environ.get("CIP_CONFIG") or f"{r}\\config.toml")
    env.setdefault("CIP_MCP_PORT", str(DEFAULT_CONFIG.get("mcp", {}).get("port", 8080)))
    from .embed import service_port as _embed_service_port
    env.setdefault("CIP_DAEMON_PORT", str(_embed_service_port(load_config(r))))
    env.setdefault("CIP_LOG_LEVEL", "INFO")
    return _ok({"env": env, "live_schema_version": _effective_meta()})


# ── SPEC-11: Export & Integration ──────────────────────────────────────────────
# Live downloads (JSON / LSIF / Markdown), MCP+daemon integration status,
# MCP tools schema viewer, runtime signal ingest, and the verification gate.

_EXPORT_KINDS = {"repo", "findings", "index", "search"}
_EXPORT_FORMATS = {"json", "markdown"}


def _export_payload(kind: str, q: str = "") -> dict:
    """Build the payload for an export kind (reuses existing builders).
    kind=repo uses export.py's full index dump; findings/index/search use the
    same builders the vis/dashboard endpoints serve, so Payload == Source."""
    from . import export as export_mod
    from .store import connect
    con = connect(_require_root())
    if kind == "repo":
        return {"source": "export._json_dump", "payload": export_mod._json_dump(con)}
    if kind == "findings":
        return {"source": "stack.audit.findings", "payload": _findings_export()}
    if kind == "index":
        return {"source": "_overview_builder", "payload": _overview_builder()}
    if kind == "search":
        from . import retrieve
        if not q.strip():
            return {"error": "search export requires ?q=", "payload": {}}
        try:
            cfg = load_config(_require_root())
            lex = retrieve.lex_search(con, q, int(cfg["retrieval"]["lexical_k"]))
            items = []
            for cid, score, srcs in retrieve.rrf([lex, []])[:50]:
                c = con.execute(
                    "SELECT c.path, c.symbol_id, c.start_line, c.end_line, "
                    "substr(c.text,1,360) snip "
                    "FROM chunks c WHERE c.id=?", (cid,)).fetchone()
                if not c:
                    continue
                items.append({"chunk": cid, "path": c["path"], "symbol": c["symbol_id"],
                              "lines": [c["start_line"], c["end_line"]],
                              "score": round(score, 5), "matched": srcs, "snippet": c["snip"]})
            return {"source": "retrieve.lex_search (+_warm_daemon)", "query": q,
                    "payload": {"results": items, "count": len(items)}}
        except Exception as exc:
            return {"source": "retrieve.lex_search", "error": str(exc), "payload": {}}
    return {"payload": {}}


def _findings_export() -> list:
    """D1-all findings for export (open only, capped at 100 by core CORE-29)."""
    from cipkg.stack import audit
    try:
        return audit.findings(_require_root(), limit=100)
    except Exception:
        return []


def _payload_to_markdown(kind: str, data: dict) -> str:
    """Render an export payload as read-only Markdown (honest columns)."""
    payload = data.get("payload", {})
    lines = [f"# CIP Export — {kind}", "",
             f"_Protocol: cip · regenerated by cip web `/api/export`_", "",
             f"Source: `{data.get('source', '?')}`"]
    if data.get("query"):
        lines.append(f"Query: `{data['query']}`")
    lines.append("")
    if kind == "repo":
        files = payload.get("files", [])
        lines.append(f"## Files ({len(files)})")
        lines += [f"- `{f['path']}` ({f.get('language') or '?'} · {f.get('lines') or 0} lines)"
                  for f in files[:200]]
        syms = payload.get("symbols", [])
        lines.append(f"\n## Symbols ({len(syms)})")
        lines += [f"- `{s['id']}` — {s.get('name')} ({s.get('kind')}) @ {s.get('path')}:{s.get('start_line')}"
                  for s in syms[:200]]
        edges = payload.get("edges", [])
        lines.append(f"\n## Edges ({len(edges)})")
        lines += [f"- `{e['src']}` -> `{e['dst']}` ({e.get('kind')})" for e in edges[:100]]
        sigs = payload.get("signals", [])
        lines.append(f"\n## Signals ({len(sigs)})")
        lines += [f"- [{s.get('kind')}] `{s.get('path')}` {s.get('name')}" for s in sigs[:100]]
        return "\n".join(lines) + "\n"
    if kind == "search":
        results = payload.get("results", [])
        lines = [f"# CIP Search Export — {len(results)} results", ""]
        for i, r in enumerate(results[:100]):
            lines += [f"### {i + 1}. `{r['path']}` (score {r.get('score')})",
                      f"_lines {r['lines']} · symbol {r.get('symbol')}_",
                      "", "```", r.get("snippet") or "", "```", ""]
        return "\n".join(lines) + "\n"
    if kind == "findings":
        rows = payload if isinstance(payload, list) else []
        lines = [f"# CIP Findings Export ({len(rows)} open findings)", ""]
        lines += ["| Severity | Rule | Path | Message |",
                  "| --- | --- | --- | --- |"]
        lines += [f"| {r.get('severity')} | {r.get('rule')} | `{r.get('path')}` | {str(r.get('message'))[:80]} |"
                  for r in rows[:200]]
        return "\n".join(lines) + "\n"
    if kind == "index":
        lines = ["# CIP Index Stats", ""]
        for k, v in sorted(payload.items()):
            if isinstance(v, (int, float, str)):
                lines.append(f"- **{k}**: {v}")
            elif isinstance(v, dict):
                lines.append(f"- **{k}**:")
                lines += [f"  - {sk}: {sv}" for sk, sv in v.items()]
        return "\n".join(lines) + "\n"
    return "\n".join(lines) + "\n"


@app.get("/api/export")
async def export_endpoint(kind: str = "repo", format: str = "json", q: str = ""):
    """Export payloads as downloads · kind ∈ repo|findings|index|search ·
    format ∈ json|markdown (JSON rendered inline; Markdown text/plain).
    SPEC-11 §4.2.2 — live exports only; deployable artifact files are NOT v1."""
    if kind not in _EXPORT_KINDS:
        return _err("BAD_EXPORT_KIND", f"kind must be one of {sorted(_EXPORT_KINDS)}")
    if format not in _EXPORT_FORMATS:
        return _err("BAD_EXPORT_FORMAT", f"format must be one of {sorted(_EXPORT_FORMATS)}")
    data = _export_payload(kind, q=q)
    if data.get("error"):
        return _err("EXPORT_FAILED", data["error"])
    filename = f"cip-{kind}-{time.strftime('%Y%m%d')}.{format}"
    if format == "json":
        text = json.dumps(data.get("payload", {}), indent=2, default=str)
        media = "application/json"
    else:
        text = _payload_to_markdown(kind, data)
        media = "text/markdown"
    return Response(content=text, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/export/status")
async def export_status_endpoint():
    """Integration status cards: MCP (8080) + embed daemon (effective port)
    reachability and index/signals presence. All low-cost probes; never spawns a server."""
    import socket
    def _reachable(port: int, timeout: float = 0.35) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=timeout):
                return True
        except Exception:
            return False
    from .store import connect
    r = _require_root()
    con = connect(r)
    try:
        files_n = con.execute("SELECT COUNT(*) c FROM files").fetchone()["c"]
        symbols_n = con.execute("SELECT COUNT(*) c FROM symbols").fetchone()["c"]
        signals_n = con.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"]
    except Exception:
        files_n = symbols_n = signals_n = 0
    mcp_port = int(DEFAULT_CONFIG.get("mcp", {}).get("port", 8080))
    from .embed import service_port as _embed_service_port
    daemon_port = _embed_service_port(load_config(r))
    return _ok({
        "mcp": {"port": mcp_port, "reachable": _reachable(mcp_port)},
        "daemon": {"port": daemon_port, "reachable": _reachable(daemon_port)},
        "index": {"files": files_n, "symbols": symbols_n, "signals": signals_n,
                  "ready": files_n > 0},
        "export": {"kinds": sorted(_EXPORT_KINDS),
                   "formats": sorted(_EXPORT_FORMATS)},
    })


@app.get("/api/export/tools")
async def export_tools_endpoint():
    """MCP tools schema viewer (SPEC-11 §3): the bridge's command registry
    reshaped as tool definitions with return type + category (SPEC-02 table)."""
    from .cli import setup_argument_parser
    parser = setup_argument_parser()
    tools = []
    for action in parser._subparsers._actions:
        if not hasattr(action, '_parser_class'):
            continue
        for name, sub in action._name_parser_map.items():
            params = []
            for a in sub._actions:
                if not a.option_strings:
                    continue
                pname = a.option_strings[0].lstrip('-')
                params.append({
                    "name": pname, "type": "boolean" if a.nargs == 0 else "string",
                    "required": bool(getattr(a, "required", False)),
                    "default": a.default if a.default is not None else None,
                    "help": (a.help or "")[:120],
                })
            tools.append({
                "name": name, "description": (sub.description or "")[:160],
                "category": _categorize(name),
                "params": params,
                "returns": "json {ok, data|error}",  # bridge envelope (SPEC-15 §4)
                "invoke": f"POST /api/run {{command: \"{name}\", params}}  (or CLI `cip {name}`)",
            })
    return _ok({"tools": tools, "count": len(tools), "port": DEFAULT_CONFIG.get("mcp", {}).get("port", 8080)})


class IngestRequest(BaseModel):
    kind: str
    text: str


@app.post("/api/export/ingest")
async def export_ingest_endpoint(req: IngestRequest):
    """Runtime signal ingest (SPEC-11 §6): paste test/typecheck/lint output.
    kind ∈ vitest|jest|pytest|tsc|generic → normalised rows in `signals`,
    stable ids via runtime_adapters._put (`sig:<kind>:<path>::<name>`, CORE-46)."""
    import tempfile
    from .store import connect
    from . import runtime_adapters as ra
    kind = (req.kind or "").lower()
    if kind not in {"vitest", "jest", "pytest", "tsc", "generic"}:
        return _err("BAD_INGEST_KIND", f"kind must be vitest|jest|pytest|tsc|generic")
    r = _require_root()
    con = connect(r)
    try:
        if kind in ("vitest", "jest"):
            n = ra.ingest_vitest(con, json.loads(req.text))
        elif kind == "tsc":
            n = ra.ingest_tsc(con, req.text)
        elif kind == "generic":
            try:
                data = json.loads(req.text)
            except json.JSONDecodeError:
                data = {"events": [{"kind": "generic", "name": line[:120], "path": ""}
                                   for line in req.text.splitlines() if line.strip()]}
            n = ra.ingest_generic(con, data)
        else:  # pytest — JUnit XML pasted text
            with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False,
                                             encoding="utf-8") as tf:
                tf.write(req.text)
                tmp = tf.name
            try:
                n = ra.ingest_pytest(con, tmp)
            finally:
                os.unlink(tmp)
    except Exception as exc:
        return _err("INGEST_FAILED", f"parse failed: {exc}")
    con.execute("INSERT INTO events(ts,kind,payload) VALUES(?,?,?)",
                (time.time(), f"ingest:{kind}", str(n)))
    con.commit()
    _schedule_broadcast({"type": "event", "command": "signals ingest",
                         "data": {"kind": kind, "ingested": n},
                         "timestamp": time.time(), "repo": r}, repo=r)
    return _ok({"ingested": n, "kind": kind,
                "note": "signals visible at /api/vis/signals and /api/export (findings/repo)"})


class VerifyRequest(BaseModel):
    typecheck: bool = False
    lint: bool = False
    audit_check: bool = True


@app.post("/api/verify")
async def verify_gate_endpoint(req: VerifyRequest):
    """Run the verification gate (SPEC-11 §7) as an async job: broken tests +
    optional typecheck/lint + critical audit findings → can_proceed/blocked_by.
    Ran in a job thread because npx tsc/eslint may take many seconds."""
    from . import verify as verify_mod
    r = _require_root()  # capture for the job thread (request contextvar is lost)
    job_id = _register_job("verify")

    def _work():
        try:
            result = verify_mod.verify(r, typecheck=req.typecheck,
                                       lint=req.lint, audit_check=req.audit_check)
            _job_done(job_id, repo=r, message="verify complete",
                      can_proceed=result.get("can_proceed"),
                      blocked_by=result.get("blocked_by", []))
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)

    threading.Thread(target=_work, daemon=True).start()
    return _ok({"job_id": job_id, "status": "running",
                "params": {"typecheck": req.typecheck, "lint": req.lint,
                           "audit_check": req.audit_check}})


@app.get("/api/embed/status")
async def embed_status_endpoint():
    """Embedder status: config-backed, warm-probe only (SPEC-15 NFR-2/embed safety).

    NEVER instantiates an embedder and NEVER auto-starts the embed daemon (the
    user-mandated web rule). Reports the configured backend + whether an
    already-warm daemon is reachable (<=0.5s probe). No model is ever loaded
    by this endpoint.
    """
    cfg = load_config(_require_root())
    backend = cfg.get("embed", {}).get("backend", "auto")
    resolution = "offline"
    model = None
    dim = 0
    warm = False
    latency_ms = None

    port = _warm_daemon()
    if port is not None:
        from .embed import service_health
        h = service_health(port, timeout=0.5)
        if h:
            warm = bool(h.get("warm"))
            resolution = "service"
            model = h.get("model") or None
            dim = int(h.get("dim") or 0)
            latency_ms = round((h.get("latency_ms") or 0.0), 1) if h.get("latency_ms") else None

    return _ok({
        "backend": backend,
        "resolution": resolution,
        "model": model,
        "dim": dim,
        "warm": warm,
        "latency_ms": latency_ms,
        "effective_backend": backend if warm else None,
    })


# ── SPEC-04: Index Management ─────────────────────────────────────────────────
@app.get("/api/index/status")
async def index_status_endpoint():
    """Index status: index_status(root) + compute_stats + admission summary."""
    from .server import index_status
    from .gatekeeper import admission_report
    try:
        status = index_status(_require_root())
    except Exception as exc:
        return _err("INDEX_UNAVAILABLE", str(exc))
    try:
        status["admission"] = admission_report(_require_root())
    except Exception:
        status["admission"] = None
    return _ok(status)


@app.post("/api/index/sync")
async def index_sync_endpoint(full: bool = False, reembed: bool = False):
    """Run indexer.sync as a job with phase progress broadcast."""
    from .indexer import sync
    r = _require_root()  # capture for the job thread (request contextvar is lost)
    job_id = _register_job("sync" if not full else "full sync")

    def _work():
        try:
            def _prog(phase, cur, tot):
                pct = int((cur / max(tot or 1, 1)) * 100) if tot else 0
                _job_progress(job_id, pct, stage=phase, message=f"{phase} {cur}/{tot or 0}",
                              repo=r)
            stats = sync(r, full=full, do_embed=not reembed, progress=_prog)
            _job_done(job_id, repo=r, message="sync complete", stats=stats)
            _schedule_broadcast({
                "type": "index.update", "job_id": job_id, "command": "sync",
                "data": stats, "timestamp": time.time(), "repo": r}, repo=r)
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)

    threading.Thread(target=_work, daemon=True).start()
    return _ok({"job_id": job_id, "status": "running"})


@app.post("/api/index/rebuild")
async def index_rebuild_endpoint():
    """Wipe DB then full sync — destructive, job."""
    from .maintain import rebuild
    r = _require_root()  # capture for the job thread (request contextvar is lost)
    job_id = _register_job("rebuild")

    def _work():
        try:
            _job_progress(job_id, 0, stage="wipe", message="clearing index", repo=r)
            stats = rebuild(r)
            _job_done(job_id, repo=r, message="rebuild complete", stats=stats)
            _schedule_broadcast({
                "type": "index.update", "job_id": job_id, "command": "rebuild",
                "data": stats, "timestamp": time.time(), "repo": r}, repo=r)
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)

    threading.Thread(target=_work, daemon=True).start()
    return _ok({"job_id": job_id, "status": "running"})


@app.post("/api/index/verify")
async def index_verify_endpoint(repair: bool = False):
    """maintain.verify as a job."""
    from .maintain import verify
    r = _require_root()  # capture for the job thread (request contextvar is lost)
    job_id = _register_job("verify")

    def _work():
        try:
            result = verify(r, repair=repair)
            _job_done(job_id, repo=r, message="index verify complete", result=result)
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)

    threading.Thread(target=_work, daemon=True).start()
    return _ok({"job_id": job_id, "status": "running"})


@app.post("/api/index/vacuum")
async def index_vacuum_endpoint(days: int | None = None):
    """maintain.vacuum as a job."""
    from .maintain import vacuum
    r = _require_root()  # capture for the job thread (request contextvar is lost)
    job_id = _register_job("vacuum")

    def _work():
        try:
            result = vacuum(r, event_days=days)
            _job_done(job_id, repo=r, message="vacuum complete", result=result)
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)

    threading.Thread(target=_work, daemon=True).start()
    return _ok({"job_id": job_id, "status": "running"})


@app.get("/api/admission")
async def admission_endpoint():
    """Trust/transparency admission report."""
    from .gatekeeper import admission_report
    try:
        return _ok(admission_report(_require_root()))
    except Exception as exc:
        return _err("ADMISSION_UNAVAILABLE", str(exc))


@app.get("/api/admission/explain")
async def admission_explain_endpoint(path: str):
    """Explain per-file gatekeeper decision."""
    from .gatekeeper import explain
    try:
        return _ok(explain(_require_root(), path))
    except Exception as exc:
        return _err("EXPLAIN_UNAVAILABLE", str(exc))


# ── SPEC-12: Repo Activation (onboarding wizard) ──────────────────────────────
def _onboarding_state_dict(root: str | None = None) -> dict:
    """Serialized InitDetector.detect() + real index presence/freshness.

    CORE-47: freshness mirrors /api/index/status (server.index_status, last_sync
    < 300s), NOT init_detector's hardcoded 1h mtime (advisory only). index_status
    is only consulted when the index DB already exists — a GET must never create
    .cip/data/index.db on a fresh repo.
    """
    from .init_detector import InitDetector, get_init_ui_text
    from .server import index_status

    r = root or _require_root()  # optional explicit root (PLAN-06 arbitrary folder)
    detector = InitDetector(r)
    state = detector.detect()

    indexed = False
    fresh = False
    if state.index_exists:
        try:
            idx = index_status(r)
            indexed = (idx.get("files") or 0) > 0
            fresh = bool(idx.get("fresh"))
        except Exception:
            indexed = True  # DB exists; treat as present, freshness unknown

    detection = None
    if state.detection:
        detection = {
            "repo_type": state.detection.repo_type,
            "languages": state.detection.languages,
            "frameworks": state.detection.frameworks,
            "has_git": state.detection.has_git,
            "git_branch": state.detection.git_branch,
            "git_uncommitted": state.detection.git_uncommitted,
            "file_count": state.detection.file_count,
        }

    return {
        "status": state.status.value,
        "status_label": get_init_ui_text(state),
        "cip_dir_exists": state.cip_dir_exists,
        "config_exists": state.config_exists,
        "index_exists": state.index_exists,
        "detector_index_fresh": state.index_fresh,  # advisory only (CORE-47)
        "git_hooks_installed": state.git_hooks_installed,
        "agents_md_exists": state.agents_md_exists,
        "indexed": indexed,
        "fresh": fresh,
        "needs_onboarding": not indexed,
        "detection": detection,
        "recommendations": state.recommendations or [],
        "error_message": state.error_message,
    }


# ── SPEC-19: Projects Registry (multi-project console) ─────────────────────────
class RegisterRequest(BaseModel):
    root: str


@app.get("/api/projects")
async def projects_list_endpoint():
    """List all registered projects with live status (SPEC-19 §).
    
    Registry-level endpoint (no ?repo= required). Probes status cheaply:
    daemon pid, index.db freshness, .cip presence. Never blocks on slow probes."""
    from .project_registry import get_registry
    from .base import cip_dir
    import os
    try:
        registry = get_registry()
        projects = []
        for proj_id, meta in registry.list().items():
            root = meta["root"]
            name = os.path.basename(root)
            status = "unknown"
            last_onboard_ts = meta.get("last_onboard_ts")
            repo_type = None
            
            # Cheap status probes (no blocking operations)
            try:
                cip_path = cip_dir(root)
                has_cip = os.path.isdir(cip_path)
                has_daemon = os.path.isfile(os.path.join(cip_path, "daemon.pid"))
                has_index = os.path.isfile(os.path.join(cip_path, "data", "index.db"))
                
                if not has_cip:
                    status = "no_cip"
                elif not has_index:
                    status = "initialized"
                else:
                    # Check index freshness (mtime within 24h = fresh)
                    index_mtime = os.path.getmtime(os.path.join(cip_path, "data", "index.db"))
                    age_hours = (time.time() - index_mtime) / 3600
                    if age_hours < 24:
                        status = "indexed"
                    else:
                        status = "stale"
                
                # Lazy repo_type detection only when cheap (skip if stale index)
                if status == "indexed":
                    try:
                        from .init_detector import detect_init_status
                        repo_type = detect_init_status(root).get("repo_type")
                    except Exception:
                        repo_type = None
            except Exception:
                status = "error"
            
            projects.append({
                "id": proj_id,
                "root": root,
                "name": name,
                "status": status,
                "last_onboard_ts": last_onboard_ts,
                "repo_type": repo_type,
            })
        
        return _ok({"projects": projects})
    except Exception as exc:
        return _err("PROJECTS_LIST_FAILED", str(exc))


@app.post("/api/projects")
async def projects_register_endpoint(req: RegisterRequest):
    """Register a folder as a project (SPEC-19 §).
    
    Registration only (no init). Idempotent: re-registering returns same entry.
    Requires folder exists; never creates files."""
    from .project_registry import get_registry
    from pathlib import Path
    import os
    try:
        root = os.path.abspath(os.path.normcase(req.root))
        if not Path(root).is_dir():
            return _err("NOT_A_DIR", f"Folder does not exist: {req.root}")
        
        registry = get_registry()
        entry = registry.register(root)
        proj_id = entry["id"]
        
        # Probe live status for response
        from .base import cip_dir
        cip_path = cip_dir(root)
        has_cip = os.path.isdir(cip_path)
        has_index = os.path.isfile(os.path.join(cip_path, "data", "index.db"))
        status = "initialized" if has_cip and not has_index else ("indexed" if has_index else "no_cip")
        
        meta = registry.list().get(proj_id, {})
        
        return _ok({
            "id": proj_id,
            "root": root,
            "name": os.path.basename(root),
            "status": status,
            "last_onboard_ts": meta.get("last_onboard_ts"),
        })
    except Exception as exc:
        return _err("PROJECT_REGISTER_FAILED", str(exc))


@app.delete("/api/projects")
async def projects_unregister_endpoint(id: str):
    """Unregister a project by id (SPEC-19 §).
    
    Never deletes files; only removes from registry."""
    from .project_registry import get_registry
    try:
        registry = get_registry()
        if not registry.has(id):
            return _err("UNKNOWN_PROJECT", f"Project not found: {id}")
        
        registry.unregister(id)
        return _ok({"id": id, "unregistered": True})
    except Exception as exc:
        return _err("PROJECT_UNREGISTER_FAILED", str(exc))


@app.post("/api/projects/{project_id:path}/onboard")
async def project_onboard_endpoint(project_id: str):
    """Full web onboarding: run init_project as a background job (PLAN-04 / SPEC-19 §6.3).

    Resolves the registered root from the registry id (NOT the request's active root),
    then runs the same init the CLI `cip init` uses, streaming progress as a job.
    On success records ``last_onboard_ts`` and broadcasts ``project.onboarded``."""
    from .project_registry import get_registry, ProjectRegistry
    from .init_flow import init_project

    reg = get_registry()
    pid = ProjectRegistry.project_id(project_id)
    entry = reg.get(pid)
    if entry is None:
        return _err("UNKNOWN_PROJECT", f"Project not registered: {project_id}")
    root = entry["root"]
    if not os.path.isdir(root):
        return _err("ONBOARD_INVALID", f"Project folder missing: {root}")
    try:
        os.makedirs(os.path.join(root, ".cip"), exist_ok=True)
    except OSError as exc:
        return _err("ONBOARD_INVALID", f"cannot prepare .cip dir: {exc}")

    job_id = _register_job("onboard")

    def _work():
        try:
            def _prog(phase, cur, tot):
                pct = int((cur / max(tot or 1, 1)) * 100) if tot else 0
                _job_progress(job_id, pct, stage="onboard:" + str(phase),
                             message=f"{phase} {cur}/{tot or 0}", repo=pid)
            result = init_project(root, progress=_prog)
            reg.touch_onboard(pid)
            _job_done(job_id, repo=pid, message="onboard complete",
                      stats=result.get("stats"), detection=result.get("detection"),
                      warnings=result.get("warnings"))
            _schedule_broadcast({
                "type": "project.onboarded", "job_id": job_id, "project_id": pid,
                "data": {"root": root}, "timestamp": time.time(), "repo": pid},
                repo=pid)
        except Exception as exc:
            _job_error(job_id, str(exc), repo=pid)

    threading.Thread(target=_work, daemon=True).start()
    return _ok({"job_id": job_id, "status": "running", "project_id": pid})


class ProfileRequest(BaseModel):
    profile: dict = {}


@app.post("/api/projects/{project_id:path}/profile")
async def project_profile_endpoint(project_id: str, req: ProfileRequest):
    """Persist [profile] for a registered project (PLAN-04 T4.4 / SPEC-19 §7).

    Merges into ``<root>/.cip/config.toml`` via tomlkit (comments/order preserved,
    .bak backup). Scoped to the registry root, not the request's active root.
    """
    from .project_registry import get_registry, ProjectRegistry
    from .base import load_config
    import tomlkit

    reg = get_registry()
    pid = ProjectRegistry.project_id(project_id)
    entry = reg.get(pid)
    if entry is None:
        return _err("UNKNOWN_PROJECT", f"Project not registered: {project_id}")
    root = entry["root"]
    cfg_path = Path(root) / ".cip" / "config.toml"
    os.makedirs(cfg_path.parent, exist_ok=True)
    try:
        doc = (tomlkit.parse(cfg_path.read_text(encoding="utf-8"))
               if cfg_path.exists() else tomlkit.document())
    except Exception as exc:
        return _err("PROFILE_PARSE_ERROR", str(exc))
    written, errors = _apply_updates_to_doc(doc, {"profile": req.profile})
    if errors:
        return _err("PROFILE_INVALID", "; ".join(errors))
    if cfg_path.exists():
        cfg_path.with_suffix(".toml.bak").write_text(
            cfg_path.read_text(encoding="utf-8"), encoding="utf-8")
    tmp = cfg_path.with_suffix(".toml.tmp")
    tmp.write_text(tomlkit.dumps(doc), encoding="utf-8")
    os.replace(tmp, cfg_path)
    effective = load_config(root)
    return _ok({"profile_section": effective.get("profile", {}), "written_keys": written})


@app.get("/api/onboarding/status")
async def onboarding_status_endpoint(path: str = ""):
    """SPEC-12 first-run gate: real wizard when not indexed, direct attach when yes.

    ``path`` (optional) detects an arbitrary folder before it is registered — the
    PLAN-06 wizard preview step. Default = active project root.
    Cached for 5s (SPEC-15 NFR-7): InitDetector tree-walks on every call otherwise."""
    try:
        root = os.path.abspath(os.path.normcase(path)) if path else None
        if root is not None and not os.path.isdir(root):
            return _err("NOT_A_DIR", f"Folder does not exist: {path}")
        key = f"onboarding.status:{root or _root() or 'legacy'}"
        return _ok(_ttl_cache(key, 5.0, lambda: _onboarding_state_dict(root)))
    except Exception as exc:
        return _err("ONBOARDING_UNAVAILABLE", str(exc))


# ── SPEC-13: Oracle / Intelligence Surface ────────────────────────────────────
def _oracle_ready() -> bool:
    """Oracle needs the index DB; a GET must NEVER create it (read-only NFR).

    Mirrors the SPEC-12 rule: probe os.path only — no store.connect() side effect.
    """
    return os.path.isfile(os.path.join(cip_dir(_require_root()), "data", "index.db"))


def _oracle_no_index() -> dict:
    return {"ready": False, "reason": "no_index",
            "message": "Run a sync first — no index found yet."}


@app.get("/api/oracle/summary")
async def oracle_summary_endpoint(path: str = ""):
    """SPEC-13: repo/dir/file summary via summarize.summary (source: structural|llm)."""
    try:
        if not _oracle_ready():
            return _ok(_oracle_no_index())
        from . import summarize
        return _ok({"ready": True, **summarize.summary(_require_root(), path or None)})
    except Exception as exc:
        return _err("ORACLE_SUMMARY_FAILED", str(exc))


@app.get("/api/oracle/repo-summary")
async def oracle_repo_summary_endpoint():
    """SPEC-13: repo story — summarize.summary(repo) + map_ dirs + hotspots (W5 seed)."""
    try:
        if not _oracle_ready():
            return _ok(_oracle_no_index())
        from . import summarize
        r = _require_root()
        story = summarize.summary(r)
        m = summarize.map_(r)
        return _ok({"ready": True,
                    "story": story,
                    "directories": m.get("directories", []),
                    "totals": m.get("totals", {}),
                    "hotspots": m.get("hotspots", [])})
    except Exception as exc:
        return _err("ORACLE_REPO_FAILED", str(exc))


@app.get("/api/oracle/suggest-context")
async def oracle_suggest_context_endpoint(file: str = ""):
    """SPEC-13: predict.suggest_context_for_edit — symbols/deps/tests/findings for a file."""
    if not file:
        return _err("EMPTY_FILE", "File path is required")
    try:
        if not _oracle_ready():
            return _ok(_oracle_no_index())
        from . import predict
        return _ok({"ready": True, "file": file,
                    **predict.suggest_context_for_edit(_require_root(), file)})
    except Exception as exc:
        return _err("ORACLE_SUGGEST_FAILED", str(exc))


@app.get("/api/oracle/next")
async def oracle_next_endpoint(operation: str = "", symbol: str = "", query: str = ""):
    """SPEC-13: predict_next_context — predictive next-tool chips (read-only; no DB).

    Confidence is static per operation branch (CORE-53: labeled "estimated" client-side).
    """
    try:
        from . import predict
        res = predict.predict_next_context(_require_root(), operation,
                                           symbol or None, query or None)
        return _ok({"ready": True, **res})
    except Exception as exc:
        return _err("ORACLE_NEXT_FAILED", str(exc))


# ── GAP-09 (SPEC-13 §3): Oracle workflows + runnable actions ──────────────────
@app.get("/api/oracle/workflows")
async def oracle_workflows_endpoint():
    """Workflow browser (SPEC-13 §3) — list_workflows."""
    from .workflow_engine import list_workflows
    try:
        r = _require_root()
        cfg = load_config(r)
        return _ok({"workflows": list_workflows(r, cfg)})
    except Exception as exc:
        return _err("ORACLE_WORKFLOWS_FAILED", str(exc))


class WorkflowRunRequest(BaseModel):
    config: dict[str, Any] = {}


@app.post("/api/oracle/workflows/{workflow_id}/run")
async def oracle_workflow_run_endpoint(workflow_id: str, req: WorkflowRunRequest):
    """Run a workflow as a job (SPEC-13 §3)."""
    from .workflow_engine import execute_workflow
    r = _require_root()
    job_id = _register_job(f"workflow {workflow_id}")
    _schedule_broadcast(_job_start(job_id, f"workflow {workflow_id}"), repo=r)

    def _work():
        try:
            cfg = load_config(r)
            result = execute_workflow(r, workflow_id, {**cfg, **req.config})
            _job_done(job_id, repo=r)
            _jobs[job_id]["result"] = result
            _schedule_broadcast(_job_done_ev(job_id, f"workflow {workflow_id}", result), repo=r)
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)
            _schedule_broadcast(_job_error_ev(job_id, f"workflow {workflow_id}", str(exc)), repo=r)

    threading.Thread(target=_work, daemon=True).start()
    return _ok({"job_id": job_id, "status": "running"})


# ── SPEC-05: Search & Navigation ──────────────────────────────────────────────
def _decorate_graph(graph_result: dict, root: str) -> dict:
    """Decorate graph() node ids with symbol metadata (CORE-22).

    graph() returns raw id lists; the UI needs labels/kinds/paths.
    Queries the symbols table once for all node ids (N+1-safe batch).
    """
    from .base import repo_root as _rr
    from .store import connect
    nodes = graph_result.get("nodes", [])
    if not nodes:
        return graph_result
    con = connect(root)
    placeholders = ",".join("?" * len(nodes))
    rows = con.execute(
        f"SELECT id,name,kind,path,start_line,end_line,signature FROM symbols WHERE id IN ({placeholders})",
        list(nodes)).fetchall()
    meta = {r["id"]: {
        "name": r["name"], "kind": r["kind"], "path": r["path"],
        "start_line": r["start_line"], "end_line": r["end_line"], "signature": r["signature"],
    } for r in rows}
    graph_result["nodes"] = [{"id": n, **meta.get(n, {})} for n in nodes]
    return graph_result


@app.get("/api/search")
async def search_endpoint(q: str = "", k: int = 10, tier: str | None = None, kind: str | None = None):
    """Hybrid search → {results, query, took_ms, matched_fallback, warming}.

    Safety (spec): the web path NEVER loads an embedding model and NEVER
    auto-starts the embed daemon. Vector search only enriches results IF a
    daemon is already warm (cheap <=0.5s probe). Otherwise lexical-only.
    """
    from . import retrieve
    if not q.strip():
        return _err("EMPTY_QUERY", "Search query is required")
    t0 = time.time()
    from .store import connect as _connect
    r = _require_root()
    cfg = load_config(r)
    con = _connect(r)

    # Vector enrichment is strictly gated on an already-warm daemon. The rest
    # of this function never touches get_embedder / daemon spawn.
    vec_used = False
    if _warm_daemon() is not None:
        try:
            vec_cands = retrieve.vec_search(con, cfg, q, int(cfg["retrieval"]["vector_k"]))
            vec_used = bool(vec_cands)
        except Exception:
            vec_cands = []
    else:
        vec_cands = []

    try:
        lex = retrieve.lex_search(con, q, int(cfg["retrieval"]["lexical_k"]))
        items = []
        for cid, score, srcs in retrieve.rrf([lex, vec_cands])[:max(k * 3, 30)]:
            c = con.execute(
                "SELECT c.path, c.symbol_id, c.start_line, c.end_line, "
                "substr(c.text,1,360) snip, f.tier "
                "FROM chunks c LEFT JOIN files f ON f.path=c.path WHERE c.id=?",
                (cid,),
            ).fetchone()
            if not c:
                continue
            items.append({
                "chunk": cid,
                "path": c["path"],
                "lines": [c["start_line"], c["end_line"]],
                "symbol": c["symbol_id"],
                "score": round(score, 5),
                "matched": srcs,
                "snippet": c["snip"],
                "tier": c["tier"] or "code",
            })
        items = retrieve.rerank(q, items, con, cfg)[:k]
    except Exception as exc:
        return _err("SEARCH_FAILED", str(exc))
    matched_fallback = False
    if tier:
        items = [it for it in items if it.get("tier") == tier]
    if kind and items and any(it.get("symbol") for it in items):
        # bridge-side kind filter: join symbols table
        from .store import connect
        r = _require_root()
        con = _connect(r)
        sym_ids = list({it["symbol"] for it in items if it.get("symbol")})
        if sym_ids:
            ph = ",".join("?" * len(sym_ids))
            rows = con.execute(f"SELECT id FROM symbols WHERE id IN ({ph}) AND kind=?", (*sym_ids, kind)).fetchall()
            ok_ids = {r["id"] for r in rows}
            items = [it for it in items if not it.get("symbol") or it["symbol"] in ok_ids]
        matched_fallback = len(items) == 0 and sym_ids is not None
    return _ok({
        "results": items,
        "query": q,
        "count": len(items),
        "took_ms": round((time.time() - t0) * 1000, 1),
        "matched_fallback": matched_fallback,
        "warming": not vec_used,
    })


@app.get("/api/symbols")
async def symbols_endpoint(name: str = "", limit: int = 20):
    """Symbol lookup → find_symbol normalized."""
    from . import retrieve
    if not name.strip():
        return _err("EMPTY_NAME", "Symbol name is required")
    return _ok({"symbols": retrieve.find_symbol(_require_root(), name, limit=limit)})


@app.get("/api/graph")
async def graph_endpoint(id: str = "", direction: str = "both", depth: int = 1):
    """Graph traversal around a symbol, decorated with node metadata."""
    from . import retrieve
    if not id:
        return _err("EMPTY_ID", "Symbol id is required")
    try:
        r = _require_root()
        g = retrieve.graph(r, id, direction=direction, depth=depth)
    except Exception as exc:
        return _err("GRAPH_FAILED", str(exc))
    return _ok(_decorate_graph(g, r))


def _safe_context(root: str, query: str, budget: int | None = None) -> dict:
    """Lexical-only budgeted context pack (SPEC-15 NFR-2 / embed safety).

    Mirrors retrieve.context's query path but NEVER calls retrieve.search
    (which would auto-embed/_ensure_embedded + load a model). Uses only
    lex_search + rrf, gated on an already-warm daemon for vector enrichment —
    identical safety posture to /api/search.
    """
    from . import retrieve
    from .base import est_tokens
    from .store import connect as _connect
    cfg = load_config(root)
    con = _connect(root)
    budget = int(budget or cfg["retrieval"]["context_budget_tokens"])

    lex = retrieve.lex_search(con, query, int(cfg["retrieval"]["lexical_k"]))
    vec = []
    if _warm_daemon() is not None:
        try:
            vec = retrieve.vec_search(con, cfg, query, int(cfg["retrieval"]["vector_k"]))
        except Exception:
            vec = []

    sections, used = [], 0
    seed = None
    for cid, score, srcs in retrieve.rrf([lex, vec])[:8]:
        row = con.execute("SELECT text, path, symbol_id, start_line, end_line FROM chunks WHERE id=?",
                          (cid,)).fetchone()
        if not row:
            continue
        t = est_tokens(row["text"])
        if used + t > budget and sections:
            break
        sections.append({
            "why": "search hit",
            "meta": {"path": row["path"], "lines": [row["start_line"], row["end_line"]],
                     "score": round(score, 5), "matched": srcs},
            "text": row["text"],
        })
        used += t
        if not seed and row["symbol_id"]:
            seed = row["symbol_id"]

    return {
        "seed": seed, "budget_tokens": budget, "used_tokens": used,
        "tokens_remaining": budget - used,
        "budget_utilization": round(used / budget * 100, 1) if budget > 0 else 0,
        "sections": sections,
        "next_ops": [f"graph(id='{seed}', direction='both')"] if seed else [],
    }


@app.get("/api/context")
async def context_endpoint(query: str | None = None, symbol: str | None = None, budget: int | None = None):
    """Token-budgeted context pack for a query or symbol.

    SPEC-15 safety: the symbol path delegates to retrieve.context (read-only SQL);
    the query path uses _safe_context (lex + warm-gated vec, NEVER auto-embed /
    never loads a model). An empty request is rejected outright.
    """
    from . import retrieve
    from .store import connect as _connect
    r = _require_root()
    if symbol:
        con = _connect(r)
        row = con.execute("SELECT id FROM symbols WHERE id=?", (symbol,)).fetchone()
        if not row:
            hits = retrieve.find_symbol(r, symbol, limit=1)
            row = {"id": hits[0]["id"]} if hits else None
        if row:
            try:
                return _ok(retrieve.context(r, symbol=row["id"], budget=budget))
            except Exception as exc:
                return _err("CONTEXT_FAILED", str(exc))
        # unresolved symbol: degrade to lexical context on the name, never auto-embed
        try:
            return _ok(_safe_context(r, symbol, budget))
        except Exception as exc:
            return _err("CONTEXT_FAILED", str(exc))
    if not query or not query.strip():
        return _err("EMPTY_CONTEXT", "Provide a query or symbol")
    try:
        return _ok(_safe_context(r, query, budget))
    except Exception as exc:
        return _err("CONTEXT_FAILED", str(exc))


@app.get("/api/history")
async def history_endpoint(path: str = ""):
    """Git history for a path."""
    from . import retrieve
    if not path:
        return _err("EMPTY_PATH", "File path is required")
    r = _require_root()
    return _ok(retrieve.history(r, path))


# ── SPEC-06: Deep File Panel ─────────────────────────────────────────────────
def _prune_name(name: str) -> bool:
    """Reject names the indexer hard-excludes (SPEC-16 §6.1): prune anything in
    DEFAULT_EXCLUDES or under a BACKUP_DIR_PREFIXES tree. Mirrors base.py:202-204
    so the tree UI agrees with what the index contains."""
    from .base import DEFAULT_EXCLUDES, BACKUP_DIR_PREFIXES
    return name in DEFAULT_EXCLUDES or name.startswith(BACKUP_DIR_PREFIXES)


def _safe_join(root: str, path: str) -> Path:
    """Resolve a user-supplied `path` against `root` and reject escapes.

    Returns an absolute, normalized Path guaranteed to live at or below `root`.
    Raises ValueError("PATH_ESCAPE") if the resolved path escapes `root`
    (e.g. ``../../etc/passwd``). Mirrors plan-07 T7.4.
    """
    base = Path(root).resolve()
    real = (base / path).resolve()
    if real != base and base not in real.parents:
        raise ValueError("PATH_ESCAPE")
    return real


def file_bundle(path: str, root: str | None = None) -> dict:
    """Compose the base file bundle in one read pass (SPEC-06 §6.1, N+1-safe).

    Returns {path, found, text, symbols, chunks, routes, findings, vectors_n}.
    Raises FileNotFoundError if the file is not on disk or missing from index.
    """
    from .store import connect
    root = root or _require_root()
    real = _safe_join(root, path)
    if not real.is_file():
        raise FileNotFoundError(path)
    con = connect(root)
    text = real.read_text(encoding="utf-8", errors="replace")
    symbols = [dict(r) for r in con.execute(
        "SELECT id,name,kind,start_line,end_line,signature FROM symbols WHERE path=? "
        "ORDER BY start_line", (path,)).fetchall()]
    chunks = [dict(r) for r in con.execute(
        "SELECT id,start_line,end_line,symbol_id,tokens FROM chunks WHERE path=? "
        "ORDER BY start_line", (path,)).fetchall()]
    routes = [dict(r) for r in con.execute(
        "SELECT path,kind,methods,client FROM routes WHERE file=?", (path,)).fetchall()]
    findings = [dict(r) for r in con.execute(
        "SELECT id,rule,severity,line,title,status FROM findings "
        "WHERE path=? AND status='open' ORDER BY severity", (path,)).fetchall()]
    vectors_n = 0
    if chunks:
        ids = [c["id"] for c in chunks]
        ph = ",".join("?" * len(ids))
        vectors_n = con.execute(
            f"SELECT COUNT(*) c FROM vectors WHERE id IN ({ph})", ids).fetchone()["c"]
    return {
        "path": path,
        "found": True,
        "text": text,
        "symbols": symbols,
        "chunks": chunks,
        "routes": routes,
        "findings": findings,
        "vectors_n": vectors_n,
        "vectors_total": len(chunks),
    }


def file_findings(path: str, root: str | None = None) -> list:
    """Findings for a specific file."""
    from .store import connect
    from .stack import audit
    con = connect(root or _require_root())
    return [dict(r) for r in con.execute(
        "SELECT id,rule,severity,line,title,status FROM findings "
        "WHERE path=? AND status='open' ORDER BY severity", (path,)).fetchall()]


def dir_listing(root: str, rel: str = "") -> dict:
    """Lazy one-level directory listing with git decorations (SPEC-16 §4/§6).

    Returns ``{path, dirs:[{name,path}], files:[{name,path,status}]}`` where
    ``path`` is the slash-joined relative path. Non-git projects skip status.
    Raises ValueError("PATH_ESCAPE") if ``rel`` resolves above ``root``.
    """
    base = Path(root).resolve()
    real = (Path(root) / rel).resolve()
    if real != base and base not in real.parents:
        raise ValueError("PATH_ESCAPE")
    dirs, files = [], []
    try:
        with os.scandir(real) as it:
            for e in it:
                name = e.name
                if _prune_name(name):
                    continue
                try:
                    is_dir = e.is_dir()
                except OSError:
                    continue  # dangling symlink / unreadable entry
                relpath = os.path.relpath(e.path, base).replace(os.sep, "/")
                if is_dir:
                    # one-level records only; recurse happens via /api/tree?path=
                    dirs.append({"name": name, "path": relpath})
                else:
                    files.append({"name": name, "path": relpath, "status": ""})
    except OSError:
        raise FileNotFoundError(rel)

    dirs.sort(key=lambda d: (d["name"].lower(), d["name"]))
    files.sort(key=lambda f: (f["name"].lower(), f["name"]))

    # Git status per directory, one porcelain call (not per-file); map rel -> letter.
    if files:
        git_status = _git_porcelain_status(root)
        if git_status:
            for f in files:
                f["status"] = git_status.get(f["path"], "")

    return {"path": rel.replace(os.sep, "/"), "dirs": dirs, "files": files}


def _git_porcelain_status(root: str) -> dict[str, str] | None:
    """Map rel paths → porcelain status letter (M/A/D) for a root, or None if not git."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "."],
            cwd=root, capture_output=True, timeout=15, text=True,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    mapping: dict[str, str] = {}
    for line in out.stdout.splitlines():
        if len(line) < 4:
            continue
        code = line[0:2].strip()
        rest = line[3:].strip()
        status = ""
        if "?" in code:
            status = "?"
        elif code:
            status = code[0]  # M/A/D/R first letter per SPEC-16 §6
        mapping[rest] = status
    return mapping


@app.get("/api/tree")
async def tree_endpoint(path: str = ""):
    """Lazy one-level directory listing (SPEC-16 §4): {path, dirs, files}.

    ``path`` is a relative dir; default "" = root. Scoped to the active project
    via ?repo= (PLAN-02). Cached 10 s (SPEC-15 NFR-7). Read-only — never creates.
    """
    r = _require_root()
    try:
        return _ok(_ttl_cache(f"tree:{path}", 10.0, lambda: dir_listing(r, path)))
    except ValueError as ve:
        if "PATH_ESCAPE" in str(ve):
            return _err("PATH_ESCAPE", f"Path escapes project root: {path}")
        raise
    except FileNotFoundError:
        return _err("DIR_NOT_FOUND", f"Directory not found: {path}")
    except Exception as exc:
        return _err("TREE_FAILED", str(exc))


@app.get("/api/file")
async def file_endpoint(path: str = ""):
    """Base file bundle: text + symbols + chunks + routes + findings + vectors."""
    if not path:
        return _err("EMPTY_PATH", "File path is required")
    r = _require_root()
    try:
        return _ok(file_bundle(path, r))
    except FileNotFoundError:
        return _err("FILE_NOT_FOUND", f"File not found: {path}")
    except ValueError as ve:
        if "PATH_ESCAPE" in str(ve):
            return _err("PATH_ESCAPE", f"Path escapes project root: {path}")
        return _err("FILE_BUNDLE_ERROR", str(ve))
    except Exception as exc:
        return _err("FILE_BUNDLE_ERROR", str(exc))


@app.get("/api/file/summary")
async def file_summary_endpoint(path: str = ""):
    """File summary → summarize.file_summary (source badge: structural|llm)."""
    from . import summarize
    if not path:
        return _err("EMPTY_PATH", "File path is required")
    r = _require_root()
    try:
        return _ok(summarize.file_summary(r, path))
    except Exception as exc:
        return _err("SUMMARY_FAILED", str(exc))


@app.get("/api/file/impact")
async def file_impact_endpoint(path: str = "", depth: int = 2):
    """Impact/blast radius → stack.impact.impact (CORE-23: run as job when heavy)."""
    from cipkg.stack import impact as impact_mod
    if not path:
        return _err("EMPTY_PATH", "File path is required")
    r = _require_root()
    try:
        return _ok(impact_mod.impact(r, target=path, depth=depth))
    except Exception as exc:
        return _err("IMPACT_FAILED", str(exc))


@app.get("/api/file/history")
async def file_history_endpoint(path: str = "", n: int = 8):
    """Git history for the file → retrieve.history (per-file, n configurable)."""
    from . import retrieve
    if not path:
        return _err("EMPTY_PATH", "File path is required")
    r = _require_root()
    try:
        return _ok(retrieve.history(r, path, n=n))
    except Exception as exc:
        return _err("FILE_HISTORY_FAILED", str(exc))


@app.get("/api/file/coverage")
async def file_coverage_endpoint(path: str = ""):
    """Per-file coverage from gapfill.coverage (filtered bridge-side)."""
    from . import gapfill
    if not path:
        return _err("EMPTY_PATH", "File path is required")
    r = _require_root()
    try:
        cov = gapfill.coverage(r)
    except Exception as exc:
        return _err("COVERAGE_FAILED", str(exc))
    # coverage() is repo-wide; extract the file-relevant slice
    per_file = {
        "file": path,
        "coverage_pct": cov.get("actual_coverage", {}).get("coverage_pct", 0),
        "loaded": [f for f in cov.get("untested_load_bearing", []) if f.get("path") == path],
        "note": cov.get("note"),
    }
    return _ok(per_file)


@app.get("/api/file/context")
async def file_context_endpoint(path: str = "", line: int | None = None):
    """Edit-context suggestions → predict.suggest_context_for_edit (CORE-26 guarded)."""
    from cipkg import predict
    if not path:
        return _err("EMPTY_PATH", "File path is required")
    r = _require_root()
    try:
        return _ok(predict.suggest_context_for_edit(r, path, line_number=line))
    except Exception as exc:
        return _err("CONTEXT_UNAVAILABLE", str(exc))


@app.get("/api/file/graph")
async def file_graph_endpoint(path: str = "", depth: int = 1):
    """Relations mini-map for a file, seeded by its most-connected symbol."""
    from . import retrieve
    from .store import connect
    if not path:
        return _err("EMPTY_PATH", "File path is required")
    r = _require_root()
    con = connect(r)
    # seed = symbol in this file with most out-edges; fall back to any symbol
    seed = con.execute(
        "SELECT s.id FROM symbols s WHERE s.path=? ORDER BY "
        "(SELECT COUNT(*) FROM edges e WHERE e.src=s.id) DESC LIMIT 1",
        (path,)).fetchone()
    if not seed:
        return _ok({"nodes": [], "edges": [], "seeded": None})
    try:
        g = retrieve.graph(r, seed["id"], direction="both", depth=depth)
    except Exception as exc:
        return _err("FILE_GRAPH_FAILED", str(exc))
    return _ok({**_decorate_graph(g, r), "seeded": seed["id"]})


# ── SPEC-07: Quality & Audit ─────────────────────────────────────────────────
_QUALITY_CACHE: dict[str, Any] = {"ts": 0.0, "data": None}
_QUALITY_CACHE_TTL = 30.0  # audit is expensive (re-index + rules); cache 30s


def quality_bundle(root: str | None = None) -> dict:
    """Compose the Quality dashboard core (SPEC-07 §6.1).

    Fast path only: health (repo_health_report) + findings summary + quick wins.
    Heavy sections (gaps digest, coverage) are separate lazy endpoints per-tab.
    Cached 30s so an audit run or repeated visits never re-run the analysis.
    """
    import time as _t
    global _QUALITY_CACHE
    now = _t.time()
    if _QUALITY_CACHE["data"] and (now - _QUALITY_CACHE["ts"]) < _QUALITY_CACHE_TTL:
        return _QUALITY_CACHE["data"]
    from . import analysis
    from .store import connect
    root = root or _require_root()
    con = connect(root)
    health = analysis.repo_health_report(root)
    try:
        from cipkg.stack import audit
        summary = audit.summarize(con)
        quick_wins = audit.quick_wins(root, limit=10)
    except Exception:
        summary = {"open": 0, "by_severity": {}, "critical": 0, "high": 0}
        quick_wins = []
    # Trends from events (B1–B3/D2 ground source; SPEC-09 renders)
    try:
        trend_rows = con.execute(
            "SELECT ts, payload FROM events WHERE kind='quality' ORDER BY ts DESC LIMIT 30"
        ).fetchall()
        trends = []
        for r in reversed(trend_rows):
            p = json.loads(r["payload"]) if isinstance(r["payload"], str) else r["payload"]
            trends.append({"ts": r["ts"], **p})
    except Exception:
        trends = []
    bundle = {
        "health": health,
        "findings": summary,
        "quick_wins": quick_wins,
        "trends": trends,
        "breakdown": _health_breakdown(root, con, health, summary),
        "generated_ms": round((_t.time() - now) * 1000, 1),
    }
    _QUALITY_CACHE = {"ts": now, "data": bundle}
    return bundle


def _health_breakdown(root: str, con, health: dict, summary: dict) -> dict:
    """Derive the 4 score components (coverage/quality/freshness/complexity)
    bridge-side — `repo_health_report` only returns the weighted overall score,
    and its internal verify/dead runs must not be duplicated here (additive-only,
    and verify is ~6.5s). Same weights; each component derives from data already
    fetched or a cheap store query.
    """
    # coverage: report already computed actual_coverage
    cov = health.get("test_coverage", {})
    coverage_pct = 0.0
    try:
        coverage_pct = cov["actual_coverage"]["coverage_pct"] or 0.0
    except Exception:
        pass
    # quality: from findings summary (already computed)
    critical = summary.get("critical", 0) or 0
    high = summary.get("high", 0) or 0
    quality_score = max(0, 100 - (critical * 20) - (high * 10))
    # freshness: cheap proxy — how stale is the last sync vs now (verify is
    # expensive and already ran inside repo_health_report; its boolean "fresh"
    # answers the same question this simplified signal does).
    freshness_score = 50
    try:
        last = con.execute(
            "SELECT ts FROM events WHERE kind='sync' ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        if last is not None and (time.time() - float(last["ts"])) < 3600:
            freshness_score = 100
    except Exception:
        pass
    return {
        "coverage": round(coverage_pct, 1),
        "quality": round(quality_score, 1),
        "freshness": round(freshness_score, 1),
        "complexity": None,  # needs a dead-code pass (~2s); see /api/quality/gaps
    }


@app.get("/api/quality/gaps")
async def quality_gaps_endpoint():
    """Gapfill digest by category (lazy tab; stack-shape gaps report None as
    'not applicable' rather than faking 'no gaps' — CORE-23 watch).

    Cached for 30s (SPEC-15 NFR-7): runs ten analyzers (~5s) on a cold cache,
    instant on revisit/poll."""
    from . import gapfill
    def _compute() -> dict:
        out = {}
        r = _require_root()
        for name, fn in (
            ("score", gapfill.score), ("dead", gapfill.dead), ("circular", gapfill.circular),
            ("migrations", gapfill.migrations), ("env", gapfill.env),
            ("logs", gapfill.logs), ("metrics", gapfill.metrics),
            ("features", gapfill.features), ("deps", gapfill.deps), ("api", gapfill.api),
        ):
            try:
                out[name] = fn(r)
            except Exception:
                out[name] = None
        return out
    return _ok(_ttl_cache("quality.gaps", 30.0, _compute))


@app.get("/api/quality/coverage")
async def quality_coverage_endpoint():
    """Repo-wide coverage report (lazy tab; heavy ~3s, gapfill.coverage).

    Cached for 30s (SPEC-15 NFR-7)."""
    from . import gapfill
    r = _require_root()
    return _ok(_ttl_cache("quality.coverage", 30.0, lambda: gapfill.coverage(r)))


def _quality_trend(metric: str, con) -> list:
    """Filter the stored quality event series to one metric (SPEC-07 §4 trends)."""
    rows = con.execute(
        "SELECT ts, payload FROM events WHERE kind='quality' ORDER BY ts DESC LIMIT 30"
    ).fetchall()
    out = []
    for r in reversed(rows):
        p = json.loads(r["payload"]) if isinstance(r["payload"], str) else r["payload"]
        val = p.get(metric)
        if val is not None:
            out.append({"ts": r["ts"], "value": val})
    return out


@app.get("/api/quality")
async def quality_endpoint():
    """Compose the Quality dashboard bundle (cached 30s)."""
    try:
        return _ok(quality_bundle())
    except Exception as exc:
        return _err("QUALITY_FAILED", str(exc))


@app.get("/api/quality/findings")
async def quality_findings_endpoint(
    severity: str | None = None, rule: str | None = None,
    path: str | None = None, limit: int = 100, offset: int = 0,
):
    """Audit findings with filters + pagination (CORE-29: core caps limit at 100)."""
    from cipkg.stack import audit
    r = _require_root()
    try:
        rows = audit.findings(r, severity=severity, rule=rule, path=path, limit=limit + offset)
        sliced = rows[offset:offset + limit]
    except Exception as exc:
        return _err("FINDINGS_FAILED", str(exc))
    return _ok({"findings": sliced, "count": len(sliced), "offset": offset, "limit": limit})


@app.get("/api/quality/findings/structured")
async def quality_findings_structured_endpoint(
    severity: str | None = None, rule: str | None = None,
    path: str | None = None, limit: int = 100,
):
    """Machine-actionable findings (agent-edit-ready)."""
    from cipkg.stack import audit
    r = _require_root()
    try:
        rows = audit.findings_structured(r, severity=severity, rule=rule, path=path, limit=limit)
    except Exception as exc:
        return _err("FINDINGS_FAILED", str(exc))
    return _ok({"structured": rows, "count": len(rows)})


@app.get("/api/quality/trends")
async def quality_trends_endpoint(metric: str = "score"):
    """Quality trend series — snapshot-backed (SPEC-09 §5), audit snapshots
    primary, quality-event fallback (B1–B3/D2; SPEC-09 renders)."""
    from .store import connect
    r = _require_root()
    try:
        snap = _snapshot_series("audit", metric)
        if snap:
            return _ok({"metric": metric, "series": snap})
        return _ok({"metric": metric, "series": _quality_trend(metric, connect(r))})
    except Exception as exc:
        return _err("TRENDS_FAILED", str(exc))


@app.get("/api/snapshots")
async def snapshots_endpoint(job: str | None = None, limit: int = 60):
    """Durable job-snapshot history (SPEC-04 §6.1/ISSUE-107).

    Read-only; rows are written by sync/audit/consolidate completions and are
    exempt from the events vacuum (CORE-17 — snapshots retain full history).
    `job` filters to sync|audit|consolidate; `limit` caps newest kept."""
    from .store import connect, snapshot_series
    try:
        con = connect(_require_root())
        series = snapshot_series(con, job=job or None, limit=limit)
        return _ok({"job": job, "count": len(series), "snapshots": series})
    except Exception as exc:
        return _err("SNAPSHOTS_FAILED", str(exc))


@app.get("/api/quality/quickwins")
async def quality_quickwins_endpoint(limit: int = 10):
    """Quick wins (open findings with a suggestion). Read-only (SPEC-15 NFR-2)."""
    from cipkg.stack import audit
    r = _require_root()
    try:
        return _ok({"quick_wins": audit.quick_wins(r, limit=limit)})
    except Exception as exc:
        return _err("QUICKWINS_FAILED", str(exc))


class AuditRequest(BaseModel):
    refresh: bool = True
    scoped_file: str | None = None  # if set → audit_file instead of full audit


@app.post("/api/quality/audit")
async def quality_audit_endpoint(req: AuditRequest):
    """Run audit as an async job (CORE-28: never in a GET). Writes a 'quality'
    trend event on completion (snapshot stand-in while store snapshots is TODO)."""
    from cipkg.stack import audit
    r = _require_root()  # capture for the async job (request contextvar is lost)
    job_id = _register_job("audit")

    async def _phase(msg: str):
        _job_progress(job_id, 0, stage=msg, message=msg, repo=r)

    async def _run():
        global _QUALITY_CACHE
        from .store import connect
        try:
            # Clear the quality cache so the dashboard reflects fresh results.
            _QUALITY_CACHE = {"ts": 0.0, "data": None}
            if req.scoped_file:
                await _phase("scoped-audit")
                result = await asyncio.to_thread(audit.audit_file, r, req.scoped_file)
                payload = {"open": len(result), "file": req.scoped_file}
            else:
                for phase in ("routes", "stack", "rules", "upsert"):
                    await _phase(phase)
                await asyncio.to_thread(audit.audit, r, refresh=req.refresh)
                con = connect(r)
                payload = audit.summarize(con)
            # Trend event (B1–B3/D2 source) + durable snapshot (SPEC-04 §6.1).
            con = connect(r)
            payload2 = dict(payload)
            score = None
            try:
                from . import analysis
                score = analysis.repo_health_report(r)["overall_score"]
                payload2["score"] = score
                payload2["coverage_pct"] = (payload2.get("coverage_pct")
                                            or analysis.repo_health_report(r)
                                            .get("test_coverage", {}).get("actual_coverage", {})
                                            .get("coverage_pct"))
            except Exception:
                payload2["score"] = None
            con.execute("INSERT INTO events (ts, kind, payload) VALUES (?, 'quality', ?)",
                        (time.time(), json.dumps(payload2)))
            # SPEC-04 §6.1: snapshot row (health/components/counts/severity).
            from .store import write_snapshot, compute_stats as _cs
            try:
                summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
                severity = dict(summary) if isinstance(summary, dict) else {}
                write_snapshot(
                    con, "audit",
                    health=score,
                    components={"coverage_pct": payload2.get("coverage_pct"),
                                "score": payload2.get("score")},
                    counts=_cs(con),
                    severity=severity,
                    meta={"scoped_file": req.scoped_file, "open": payload.get("open")},
                )
            except Exception:
                pass  # snapshot is best-effort; the trend event still landed
            con.commit()
            _job_done(job_id, repo=r, message="audit complete", summary=payload)
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)


# ── SPEC-Forensics: Deep Intelligence, Ghost Code & AI Context Pack ──────────

GHOST_CODE_RULES = {"HIDDEN-EXPORT", "HIDDEN-ROUTE", "HIDDEN-MODEL", "ARCH-ORPHAN-FILE"}
SILENT_TRAP_RULES = {"S1", "DB-NO-AWAIT", "DB-N1", "NEXT-CLIENT-LEAK", "NEXT-ROUTE-NO-ERROR", "NEXT-ACTION-NO-VALIDATE", "SEC-SQL-RAW"}
ARCHITECTURE_RULES = {"ARCH-LAYER-VIOLATION", "QA-CIRCULAR", "QA-GOD-MODULE", "QA-DUP", "TAURI-UNGATED-COMMAND"}
RISK_RULES = {"QA-UNTESTED-HOT"}
SECRET_ENV_RULES = {"SEC-HARDCODED-SECRET", "ENV-UNDEFINED", "ENV-UNREAD", "DB-SCHEMA-DRIFT", "DB-MIGRATION-INDEX-DRIFT", "DB-DESTRUCTIVE-MIGRATION", "DB-MISSING-INDEX"}


def _categorize_finding(rule: str) -> str:
    if rule in GHOST_CODE_RULES or "HIDDEN" in rule:
        return "ghost_code"
    if rule in SILENT_TRAP_RULES or "NO-AWAIT" in rule or "LEAK" in rule:
        return "silent_traps"
    if rule in ARCHITECTURE_RULES or "ARCH-" in rule or "CIRCULAR" in rule or "GOD" in rule:
        return "architecture"
    if rule in RISK_RULES or "HOT" in rule:
        return "risk_matrix"
    if rule in SECRET_ENV_RULES or "SEC-" in rule or "ENV" in rule or "DB-" in rule:
        return "secrets_env"
    return "quality"


@app.get("/api/forensics/summary")
async def forensics_summary_endpoint():
    """Aggregates repository intelligence across the 5 core forensic dimensions:
    - ghost_code: Unreferenced exports, uncalled routes, dead models, orphan files.
    - silent_traps: Swallowed exceptions, unawaited queries, unvalidated actions.
    - architecture: Layer inversions, circular import cycles, god modules.
    - risk_matrix: Untested load-bearing hotspots and git churn correlation.
    - secrets_env: Undefined/unread env vars, hardcoded secrets, schema drift.
    """
    from .store import connect
    from . import gapfill, gitindex
    r = _require_root()
    con = connect(r)
    
    # Query all open findings
    try:
        rows = con.execute(
            "SELECT id, rule, severity, path, line, symbol_id, title, detail, suggestion, effort "
            "FROM findings WHERE status='open' ORDER BY severity"
        ).fetchall()
        findings = [dict(row) for row in rows]
    except Exception:
        findings = []

    categorized: dict[str, list] = {
        "ghost_code": [],
        "silent_traps": [],
        "architecture": [],
        "risk_matrix": [],
        "secrets_env": [],
        "quality": [],
    }

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for f in findings:
        cat = _categorize_finding(f.get("rule", ""))
        categorized[cat].append(f)
        sev = (f.get("severity") or "low").lower()
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Augment risk_matrix with git churn hotspots and untested load-bearing stats
    hotspots_data = []
    try:
        hot = gitindex.hotspots(r, k=10)
        # Check test coverage per hotspot
        for h in hot:
            path = h["path"]
            syms_n = con.execute("SELECT COUNT(*) c FROM symbols WHERE path=?", (path,)).fetchone()["c"]
            tested_n = con.execute("""
                SELECT COUNT(DISTINCT s.id) c FROM symbols s
                JOIN edges e ON e.src = s.id AND e.kind = 'tested_by'
                WHERE s.path = ?
            """, (path,)).fetchone()["c"]
            cov = round((tested_n / syms_n * 100), 1) if syms_n > 0 else 0.0
            hotspots_data.append({
                "path": path,
                "churn_score": h["score"],
                "symbols_count": syms_n,
                "tested_count": tested_n,
                "coverage_pct": cov,
                "risk_tier": "critical" if cov < 30 and h["score"] > 5 else ("high" if cov < 60 else "moderate")
            })
    except Exception:
        hotspots_data = []

    # Circular dependency loops from Tarjan SCC
    cycles_data = []
    try:
        circ = gapfill.circular(r)
        cycles_data = circ.get("cycles", [])
    except Exception:
        cycles_data = []

    # Dead symbols count
    dead_stats = {"count": 0}
    try:
        dead_res = gapfill.dead(r, limit=20)
        dead_stats = {"count": dead_res.get("count", 0), "candidates": dead_res.get("candidate_dead_symbols", [])[:10]}
    except Exception:
        pass

    return _ok({
        "total_findings": len(findings),
        "by_severity": severity_counts,
        "dimensions": {
            "ghost_code": {
                "count": len(categorized["ghost_code"]),
                "findings": categorized["ghost_code"],
                "dead_stats": dead_stats,
            },
            "silent_traps": {
                "count": len(categorized["silent_traps"]),
                "findings": categorized["silent_traps"],
            },
            "architecture": {
                "count": len(categorized["architecture"]),
                "findings": categorized["architecture"],
                "cycles": cycles_data,
            },
            "risk_matrix": {
                "count": len(categorized["risk_matrix"]),
                "findings": categorized["risk_matrix"],
                "hotspots": hotspots_data,
            },
            "secrets_env": {
                "count": len(categorized["secrets_env"]),
                "findings": categorized["secrets_env"],
            },
            "quality": {
                "count": len(categorized["quality"]),
                "findings": categorized["quality"],
            }
        }
    })


@app.get("/api/forensics/dossier")
async def forensics_dossier_endpoint(format: str = "json"):
    """Generates an executive-ready architectural and forensic intelligence dossier report."""
    from . import analysis, gapfill, gitindex
    from .store import connect
    r = _require_root()
    con = connect(r)
    health = analysis.repo_health_report(r)
    summary_resp = await forensics_summary_endpoint()
    summary_data = summary_resp.body
    try:
        summary_parsed = json.loads(summary_data).get("data", {})
    except Exception:
        summary_parsed = {}

    dims = summary_parsed.get("dimensions", {})

    dossier_json = {
        "title": f"CIP Executive Forensic Dossier — {os.path.basename(r)}",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "root": r,
        "health_score": health.get("overall_score", 0),
        "findings_by_severity": summary_parsed.get("by_severity", {}),
        "dimensions_summary": {
            "ghost_code_issues": dims.get("ghost_code", {}).get("count", 0),
            "silent_traps_issues": dims.get("silent_traps", {}).get("count", 0),
            "architectural_violations": dims.get("architecture", {}).get("count", 0),
            "high_risk_hotspots": len([h for h in dims.get("risk_matrix", {}).get("hotspots", []) if h.get("risk_tier") in ("critical", "high")]),
            "env_and_security_issues": dims.get("secrets_env", {}).get("count", 0),
        },
        "critical_issues": health.get("critical_issues", []),
        "recommendations": health.get("recommendations", []),
        "risk_hotspots": dims.get("risk_matrix", {}).get("hotspots", [])[:10],
    }

    if format == "markdown":
        md_lines = [
            f"# {dossier_json['title']}",
            f"**Generated:** {dossier_json['generated_at']} · **Health Score:** `{dossier_json['health_score']}/100`",
            "",
            "## 1. Executive Summary",
            f"- **Critical Issues:** {summary_parsed.get('by_severity', {}).get('critical', 0)}",
            f"- **High Severity Issues:** {summary_parsed.get('by_severity', {}).get('high', 0)}",
            f"- **Ghost Code / Buried Features:** {dims.get('ghost_code', {}).get('count', 0)} items",
            f"- **Silent Failure Hazards:** {dims.get('silent_traps', {}).get('count', 0)} items",
            f"- **Boundary / Layer Violations:** {dims.get('architecture', {}).get('count', 0)} items",
            "",
            "## 2. Top Risk Hotspots (Churn × Test Deficit)",
            "| File Path | Churn Score | Coverage % | Risk Tier |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for h in dossier_json["risk_hotspots"]:
            md_lines.append(f"| `{h['path']}` | {h['churn_score']} | {h['coverage_pct']}% | **{h['risk_tier'].upper()}** |")
        
        md_lines.extend([
            "",
            "## 3. High Priority Action Plan",
        ])
        for i, rec in enumerate(dossier_json["recommendations"][:8], 1):
            md_lines.append(f"{i}. **[{rec.get('priority', 'ACTION')}]** {rec.get('action')} — _{rec.get('impact', '')}_ (Effort: `{rec.get('effort', 'small')}`)")

        md_text = "\n".join(md_lines) + "\n"
        return Response(content=md_text, media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="cip-forensic-dossier-{time.strftime("%Y%m%d")}.md"'})

    return _ok(dossier_json)


class ContextPackRequest(BaseModel):
    target_path: str | None = None
    symbol_id: str | None = None
    max_tokens: int = 4096


@app.post("/api/forensics/context-pack")
async def forensics_context_pack_endpoint(req: ContextPackRequest):
    """Generates an optimal, token-budgeted AI context pack for Claude/Gemini/GPT-4
    operating under the canonical 120K token context window ceiling."""
    from . import repo_map, tokens, predict
    from .store import connect
    r = _require_root()
    con = connect(r)
    
    estimator = tokens.TokenEstimator(limit=128000)
    
    sections = []
    
    # 1. Signature-level Repository Map
    map_budget = min(req.max_tokens // 2, 2048)
    try:
        cfg = repo_map.RepoMapConfig(max_tokens=map_budget, include_signatures=True)
        rmap = repo_map.generate_repo_map(r, cfg)
        if rmap.strip():
            sections.append(f"## 1. Repository Architecture Map (Token-Optimized)\n```\n{rmap.strip()}\n```")
    except Exception:
        pass

    # 2. Target File Context & Ast Chunks
    if req.target_path:
        try:
            full_path = Path(r) / req.target_path
            if full_path.is_file():
                content = full_path.read_text(encoding="utf-8", errors="replace")
                # Truncate content to token budget
                max_chars = req.max_tokens * 3
                if len(content) > max_chars:
                    content = content[:max_chars] + f"\n\n... [Truncated: {len(content) - max_chars} characters remaining]"
                sections.append(f"## 2. Target File: `{req.target_path}`\n```\n{content}\n```")
        except Exception:
            pass

    # 3. Symbol Relationship Graph & Callers
    if req.symbol_id:
        try:
            sym = con.execute("SELECT name, kind, path, signature FROM symbols WHERE id=?", (req.symbol_id,)).fetchone()
            if sym:
                callers = con.execute("""
                    SELECT e.src, e.kind FROM edges e
                    WHERE e.dst = ? LIMIT 15
                """, (req.symbol_id,)).fetchall()
                caller_lines = [f"- `{c['src']}` ({c['kind']})" for c in callers]
                sections.append(f"## 3. Symbol Focus: `{sym['name']}` ({sym['kind']}) in `{sym['path']}`\n"
                               f"Signature: `{sym['signature']}`\n\n"
                               f"### Inbound Dependents ({len(caller_lines)}):\n" + "\n".join(caller_lines))
        except Exception:
            pass

    # 4. Predictive Next Context Recommendations
    try:
        op = "symbol" if req.symbol_id else ("file" if req.target_path else "general")
        preds = predict.predict_next_context(r, op, current_symbol=req.symbol_id)
        if preds.get("predictions"):
            p_lines = [f"- **{p['reason']}** (Tool: `{p['tool']}` · Confidence: {int(p['confidence']*100)}%)"
                       for p in preds["predictions"][:4]]
            sections.append("## 4. Intelligent Context Recommendations for Agent\n" + "\n".join(p_lines))
    except Exception:
        pass

    full_pack = "\n\n".join(sections)
    token_count = estimator.estimate(full_pack)

    return _ok({
        "context_pack": full_pack,
        "token_count": token_count,
        "token_limit": 128000,
        "target_path": req.target_path,
        "symbol_id": req.symbol_id,
        "caution_threshold": int(128000 * tokens.CAUTION_THRESHOLD),
        "emergency_threshold": int(128000 * tokens.EMERGENCY_THRESHOLD),
    })


# ── SPEC-08: Memory Lab ──────────────────────────────────────────────────────
# CORE-32 (verified on disk): `LearningSystem.memory` → `memory.db` (temporal_facts),
# `LearningSystem.episodic` → `episodes.db` (episodes) — TWO files, but
# `MemoryConsolidator` assumes ONE shared path. So the consolidation job adapter
# reads episodes from `episodes.db` and promotes into the `memory.db` graph via the
# consolidator's own `_extract_patterns`/`_promote_to_semantic`. Never call
# `MemoryConsolidator.consolidate()` directly — it queries an empty episodes table.
_MEM_CACHE: dict[str, Any] = {"ts": 0.0, "data": None}
_MEM_CACHE_TTL = 5.0  # overview is cheap; still cached per SPEC-08 §4


def _mem_dir(root: str) -> Path:
    from .base import data_dir
    d = Path(data_dir(root)) / "learning_data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def memory_overview(root: str | None = None) -> dict:
    """SPEC-08 §4 overview — counts + last consolidation + daemon flag (cheap,
    cached 5s). Empty-state honest: files may not exist yet."""
    import sqlite3
    import time as _t
    global _MEM_CACHE
    now = _t.time()
    if _MEM_CACHE["data"] and (now - _MEM_CACHE["ts"]) < _MEM_CACHE_TTL:
        return _MEM_CACHE["data"]
    root = root or _require_root()
    md = _mem_dir(root)
    mem_db, ep_db = md / "memory.db", md / "episodes.db"

    facts_n = episodes_n = 0
    last_write = None
    for p in (mem_db, ep_db):
        try:
            if p.exists():
                t = p.stat().st_mtime
                last_write = max(last_write or 0, t)
        except Exception:
            pass

    if mem_db.exists():
        try:
            with sqlite3.connect(str(mem_db)) as c:
                facts_n = c.execute("SELECT COUNT(*) FROM temporal_facts").fetchone()[0]
        except Exception:
            facts_n = 0
    if ep_db.exists():
        try:
            with sqlite3.connect(str(ep_db)) as c:
                episodes_n = c.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        except Exception:
            episodes_n = 0

    profiles_n = 0
    prof_dir = md / "profiles"
    try:
        if prof_dir.exists():
            profiles_n = len([f for f in prof_dir.iterdir() if f.suffix == ".json"])
    except Exception:
        pass

    last_consolidation = None
    try:
        from .store import connect
        con = connect(root)
        row = con.execute(
            "SELECT ts, payload FROM events WHERE kind='memory.consolidate' "
            "ORDER BY ts DESC LIMIT 1").fetchone()
        if row:
            payload = (json.loads(row["payload"])
                       if isinstance(row["payload"], str) else row["payload"])
            last_consolidation = {"ts": row["ts"], **payload}
    except Exception:
        pass

    daemon_running = False
    try:
        from . import daemon
        st = daemon.daemon_status(root)
        daemon_running = bool(st.get("alive"))
    except Exception:
        pass

    bundle = {
        "facts_n": facts_n,
        "episodes_n": episodes_n,
        "patterns_n": _count_patterns(mem_db),
        "profiles": profiles_n,
        "last_consolidation": last_consolidation,
        "daemon_running": daemon_running,
        "memory_dir": str(md).replace(str(root), ".") if root else str(md),
        "disk_bytes": sum(p.stat().st_size for p in (mem_db, ep_db) if p.exists()),
        "last_write": last_write,
        "initialized": (mem_db.exists() or ep_db.exists()),
    }
    _MEM_CACHE = {"ts": now, "data": bundle}
    return bundle


def _count_patterns(mem_db: Path) -> int:
    """Promoted patterns live in temporal_facts with subject='learned_patterns'."""
    import sqlite3
    if not mem_db.exists():
        return 0
    try:
        with sqlite3.connect(str(mem_db)) as c:
            return c.execute(
                "SELECT COUNT(*) FROM temporal_facts WHERE subject='learned_patterns'").fetchone()[0]
    except Exception:
        return 0


def _facts_rows(root: str, subject: str | None = None, predicate: str | None = None,
                at_time: float | None = None, limit: int = 100) -> list:
    """Temporal facts — direct read (need expired rows too, for validity bars)."""
    import sqlite3
    mem_db = _mem_dir(root) / "memory.db"
    if not mem_db.exists():
        return []
    with sqlite3.connect(str(mem_db)) as c:
        q = ("SELECT subject, predicate, object_value, valid_from, valid_until, "
             "confidence, source, metadata, created_at FROM temporal_facts")
        conds, params = [], []
        if subject:
            conds.append("subject = ?"); params.append(subject)
        if predicate:
            conds.append("predicate = ?"); params.append(predicate)
        if at_time:
            conds.append("valid_from <= ? AND (valid_until IS NULL OR valid_until >= ?)")
            params += [at_time, at_time]
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY valid_from DESC LIMIT ?"; params.append(limit)
        rows = c.execute(q, params).fetchall()
    out = []
    for r in rows:
        try:
            obj = json.loads(r[2])
        except Exception:
            obj = r[2]
        out.append({
            "subject": r[0], "predicate": r[1], "object_value": obj,
            "valid_from": r[3], "valid_until": r[4], "confidence": r[5],
            "source": r[6], "metadata": json.loads(r[7]) if r[7] else {},
            "created_at": r[8],
        })
    return out


def _episodes_rows(root: str, episode_type: str | None = None, limit: int = 50) -> list:
    import sqlite3
    ep_db = _mem_dir(root) / "episodes.db"
    if not ep_db.exists():
        return []
    with sqlite3.connect(str(ep_db)) as c:
        q = ("SELECT id, timestamp, episode_type, context, outcome, metadata, "
             "(embedding IS NOT NULL) AS has_embedding FROM episodes")
        conds, params = [], []
        if episode_type:
            conds.append("episode_type = ?"); params.append(episode_type)
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY timestamp DESC LIMIT ?"; params.append(limit)
        rows = c.execute(q, params).fetchall()
    out = []
    for r in rows:
        try:
            ctx = json.loads(r[3])
        except Exception:
            ctx = {}
        out.append({
            "id": r[0], "timestamp": r[1], "episode_type": r[2],
            "context": ctx, "outcome": r[4],
            "metadata": json.loads(r[5]) if r[5] else {},
            "has_embedding": bool(r[6]),
        })
    return out


@app.get("/api/memory/overview")
async def memory_overview_endpoint():
    try:
        return _ok(memory_overview())
    except Exception as exc:
        return _err("MEMORY_OVERVIEW_FAILED", str(exc))


@app.get("/api/memory/facts")
async def memory_facts_endpoint(
    subject: str | None = None, predicate: str | None = None,
    at: float | None = None, limit: int = 100,
):
    r = _require_root()
    try:
        return _ok({"facts": _facts_rows(r, subject, predicate, at, limit)})
    except Exception as exc:
        return _err("MEMORY_FACTS_FAILED", str(exc))


@app.get("/api/memory/episodes")
async def memory_episodes_endpoint(type: str | None = None, limit: int = 50):
    r = _require_root()
    try:
        out = _episodes_rows(r, type, limit)
        return _ok({"episodes": out, "count": len(out)})
    except Exception as exc:
        return _err("MEMORY_EPISODES_FAILED", str(exc))


@app.get("/api/memory/recall")
async def memory_recall_endpoint(query: str):
    """LearningSystem.recall_relevant — episodes (keyword match; embedding BLOB
    filled only by logger with embedder on) + facts by command tag (CORE-33)."""
    r = _require_root()
    try:
        from .learning_system import LearningSystem
        ls = LearningSystem(r)
        results = ls.recall_relevant(query)
        return _ok({"query": query, "results": results, "count": len(results)})
    except Exception as exc:
        return _err("MEMORY_RECALL_FAILED", str(exc))


@app.get("/api/memory/patterns")
async def memory_patterns_endpoint(user_id: str = "default"):
    """PatternAnalyzer.analyze_user_patterns + promoted learned_patterns facts."""
    out = {"analyzed": None, "learned": []}
    r = _require_root()
    try:
        from .learning_system import LearningSystem
        ls = LearningSystem(r)
        out["analyzed"] = ls.analyze_patterns(user_id)
    except Exception as exc:
        return _err("MEMORY_PATTERNS_FAILED", str(exc))
    out["learned"] = _facts_rows(r, subject="learned_patterns")
    return _ok(out)


@app.get("/api/memory/suggestions")
async def memory_suggestions_endpoint(user_id: str = "default", context: str | None = None):
    r = _require_root()
    try:
        from .learning_system import get_personalized_suggestions
        ctx = json.loads(context) if context else {}
        return _ok({"suggestions": get_personalized_suggestions(r, user_id=user_id, context=ctx)})
    except Exception as exc:
        return _err("MEMORY_SUGGESTIONS_FAILED", str(exc))


class MemoryActionRequest(BaseModel):
    action_type: str  # 'command' or 'suggestion_response' (core branches on these)
    command: str | None = None
    success: bool = True
    kwargs: dict[str, Any] = {}


@app.post("/api/memory/action")
async def memory_action_endpoint(req: MemoryActionRequest):
    """record_user_action telemetry — server-side user_id='default'. JSONL append
    per call; frontend debounces. No echo on success (SPEC-08 §4)."""
    r = _require_root()
    try:
        from .learning_system import record_user_action
        kw = dict(req.kwargs)
        if req.command:
            kw["command"] = req.command
        kw["success"] = req.success
        record_user_action(r, req.action_type, **kw)
        return _ok({})
    except Exception as exc:
        return _err("MEMORY_ACTION_FAILED", str(exc))


class ConsolidateRequest(BaseModel):
    lookback_days: int = 7


@app.post("/api/memory/consolidate")
async def memory_consolidate_endpoint(req: ConsolidateRequest):
    """Consolidation-as-job (SPEC-08 §6.2) — CORE-32 adapter: read episodes from
    episodes.db, extract patterns, promote >0.7 confidence into memory.db graph.
    Writes a memory.consolidate trend event + WS memory.updated broadcast."""
    r = _require_root()  # capture for the async job (request contextvar is lost)
    job_id = _register_job("consolidate")

    async def _phase(msg: str):
        _job_progress(job_id, 0, stage=msg, message=msg, repo=r)

    async def _run():
        global _MEM_CACHE
        from .store import connect
        from .memory.episodic import EpisodicMemory
        from .memory.consolidation import MemoryConsolidator
        try:
            await _phase("episodes")
            md = _mem_dir(r)
            ep_db, mem_db = md / "episodes.db", md / "memory.db"
            episodes = EpisodicMemory(str(ep_db)).query_episodes(
                since=time.time() - (req.lookback_days * 86400), limit=1000)
            await _phase("patterns")
            cons = MemoryConsolidator(str(mem_db))
            patterns = cons._extract_patterns(episodes) if episodes else []
            promoted = [p for p in patterns if p["confidence"] > 0.7]
            for p in promoted:
                cons._promote_to_semantic(p)
            await _phase("done")
            summary = {
                "lookback_days": req.lookback_days,
                "episodes": len(episodes),
                "patterns": len(patterns),
                "promoted": len(promoted),
            }
            con = connect(r)
            con.execute("INSERT INTO events (ts, kind, payload) VALUES (?, 'memory.consolidate', ?)",
                        (time.time(), json.dumps(summary)))
            # SPEC-04 §6.1: durable snapshot for the consolidate job (counts +
            # memory digest as meta; no health/severity — those are audit-only).
            from .store import write_snapshot, compute_stats as _cs
            try:
                write_snapshot(con, "consolidate",
                               health=None,
                               components={"episodes": len(episodes),
                                           "patterns": len(patterns),
                                           "promoted": len(promoted)},
                               counts=_cs(con),
                               severity=None,
                               meta={"lookback_days": req.lookback_days})
            except Exception:
                pass
            con.commit()
            _MEM_CACHE = {"ts": 0.0, "data": None}
            _job_done(job_id, repo=r, message="consolidation complete", summary=summary)
            _schedule_broadcast({
                "type": "memory.updated", "job_id": job_id, "command": "consolidate",
                "data": summary, "timestamp": time.time(),
                "repo": r}, repo=r)
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)

    asyncio.create_task(_run())
    return _ok({"job_id": job_id, "status": "running"})


class ClearMemoryRequest(BaseModel):
    confirm: bool = False


@app.post("/api/memory/clear")
async def memory_clear_endpoint(req: ClearMemoryRequest):
    """Wipe learning_data (memory.db, episodes.db, actions/profiles) — requires
    confirm=true (SPEC-08 §5 hygiene; CORE-34: vacuum does not prune memory)."""
    import shutil
    if not req.confirm:
        return _err("MEMORY_CLEAR_CONFIRM", "pass confirm:true to wipe memory files")
    global _MEM_CACHE
    r = _require_root()
    try:
        md = _mem_dir(r)
        for p in md.glob("*.db"):
            p.unlink(missing_ok=True)
        for sub in ("actions", "patterns", "profiles", "models"):
            d = md / sub
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
        _MEM_CACHE = {"ts": 0.0, "data": None}
        return _ok({"cleared": True})
    except Exception as exc:
        return _err("MEMORY_CLEAR_FAILED", str(exc))


# ── SPEC-09: Visualization Suite ──────────────────────────────────────────────
_VIS_CACHE: dict[str, dict] = {}

# Per-group cache TTL (spec §4: light 30–60s; heavy computed sources cached longer).
_VIS_TTL = {
    "overview": 30.0,   # A1/A3 + D5 language (buffered behind quality_bundle 30s)
    "trends": 20.0,     # A2/B1/B2/B3/D2 time series
    "git": 60.0,        # C1–C4 (commits/hotspots/co-change/feed)
    "findings": 30.0,   # D1 by-severity + by-rule
    "map": 60.0,        # G1/G2 (summarize.map_ + dirs)
    "signals": 20.0,    # F3 windowed signals
    "graph": 10.0,      # E1 graph payload (decorated, caps applied)
}


def _vis_get(key: str, builder) -> dict:
    """Per-group cached payload with event-driven invalidation.

    Every sync → 'sync' event, audit → 'quality' event and consolidate →
    'memory.consolidate' event bumps events.max(ts), so the chart source is
    always fresh without touching job closures (SPEC-09 §6.5 bookkeeping).
    """
    global _VIS_CACHE
    now = time.time()
    cached = _VIS_CACHE.get(key)
    try:
        con = connect(_require_root())
        ev = con.execute("SELECT MAX(ts) m FROM events").fetchone()
        last_ev = float(ev["m"] or 0.0)
        con.close()
    except Exception:
        last_ev = 0.0
    if cached and (now - cached["ts"]) < _VIS_TTL.get(key, 30.0) and cached["ev"] == last_ev:
        return cached["data"]
    data = builder()
    _VIS_CACHE[key] = {"ts": now, "data": data, "ev": last_ev}
    return data


def _parse_payload(raw) -> dict:
    """Robustly parse an events.payload. Core writes quality/consolidate as JSON
    but indexer writes sync stats as `str(stats)` (Python repr) — tolerate both."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    try:
        import ast
        v = ast.literal_eval(raw)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def _events_series(kind: str, metric: str, days: int | None = None) -> list:
    """Generic event time-series: rows of {ts, value} for `metric` in `kind`
    payloads, optionally windowed to the last N days (A2/B1/B2/B3/D2 source)."""
    from .store import connect
    r = _require_root()
    con = connect(r)
    q = "SELECT ts, payload FROM events WHERE kind=? ORDER BY ts ASC"
    args: list = [kind]
    if days:
        q = ("SELECT ts, payload FROM events WHERE kind=? AND ts>=? ORDER BY ts ASC")
        args.append(time.time() - days * 86400)
    out = []
    for r in con.execute(q, args).fetchall():
        p = _parse_payload(r["payload"])
        if metric in p and p.get(metric) is not None:
            out.append({"ts": r["ts"], "value": p[metric]})
    return out


# ── GAP-08 (SPEC-09 §5/§8): snapshot-backed trend series ─────────────────────
_SNAPSHOT_METRIC_KEYS = {
    "files": ("counts", "files"), "symbols": ("counts", "symbols"),
    "chunks": ("counts", "chunks"), "edges": ("counts", "edges"),
    "vectors": ("counts", "vectors"), "vector_coverage_pct": ("counts", "vector_coverage_pct"),
    "score": ("health", None), "overall_score": ("health", None),
    "coverage_pct": ("components", "coverage_pct"),
    "critical": ("severity", "critical"), "high": ("severity", "high"),
}


def _snapshot_series(kind: str | None, metric: str, days: int | None = None) -> list:
    """Snapshot-backed trend series (SPEC-09 §5). Kind maps to the snapshot job
    (sync|audit|consolidate); metric maps to a JSON field per the table above."""
    from .store import connect, snapshot_series
    r = _require_root()
    con = connect(r)
    job = kind if kind in ("sync", "audit", "consolidate") else None
    rows = snapshot_series(con, job=job, limit=500)
    spec = _SNAPSHOT_METRIC_KEYS.get(metric)
    if not spec:
        return []
    container, key = spec
    out = []
    for r in rows:
        src = r.get(container)
        if isinstance(src, str):
            try:
                src = json.loads(src)
            except Exception:
                src = None
        val = None
        if isinstance(src, dict):
            val = src.get(key) if key else src
        if isinstance(r.get("health"), (int, float)) and metric in ("score", "overall_score"):
            val = float(r["health"])
        if val is not None:
            if isinstance(val, (int, float)):
                val = float(val)
            out.append({"ts": r["ts"], "value": val})
    if days and out:
        cutoff = time.time() - days * 86400
        out = [p for p in out if p["ts"] >= cutoff]
    return out


def _events_series_snapshots_first(kind: str, metric: str, days: int | None = None) -> list:
    """Primary: snapshots (retained indefinitely, CORE-17). Fallback: events
    (freshness/`ms` only where snapshots lack the field)."""
    snap = _snapshot_series(kind, metric, days)
    if snap:
        return snap
    return _events_series(kind, metric, days)


def _events_feed(kind: str | None = None, since: float | None = None,
                 limit: int = 100) -> list[dict]:
    """Durable events rows {ts, kind, payload} — shared by GET /api/events and
    WS `subscribe {since}` replay (SPEC-14 §4/§6.2)."""
    from .store import connect
    r = _require_root()
    con = connect(r)
    q = "SELECT ts, kind, payload FROM events"
    conds, args = [], []
    if kind:
        conds.append("kind=?"); args.append(kind)
    if since is not None:
        conds.append("ts>?"); args.append(since)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY ts ASC LIMIT ?"
    args.append(int(max(1, min(limit, 500))))
    return [
        {"ts": r["ts"], "kind": r["kind"], "payload": _parse_payload(r["payload"])}
        for r in con.execute(q, args).fetchall()
    ]


@app.get("/api/events")
async def events_feed_endpoint(kind: str | None = None, since: float | None = None,
                               limit: int = 100):
    """Durable activity feed (SPEC-14 §4). Read-only; tolerates legacy str
    payloads via _parse_payload (CORE-55). `since` enables WS reconnect replay."""
    try:
        events = _events_feed(kind=kind, since=since, limit=limit)
        return _ok({"events": events, "count": len(events), "since": since})
    except Exception as exc:
        return _err("EVENTS_FAILED", str(exc))


def _lang_breakdown() -> list:
    """D5: files.language GROUP BY (unknown/empty grouped as 'other')."""
    from .store import connect
    r = _require_root()
    con = connect(r)
    rows = con.execute(
        "SELECT CASE WHEN language IS NULL OR language='' THEN 'other' "
        "ELSE language END lang, COUNT(*) c FROM files GROUP BY lang "
        "ORDER BY c DESC").fetchall()
    return [{"language": r["lang"], "count": r["c"]} for r in rows]


def _overview_builder() -> dict:
    """A1 radial score + A3 gate + buffered components + D5 language counts."""
    from .store import connect
    r = _require_root()
    q = quality_bundle()  # 30s-cached health + findings + quick_wins + trends
    con = connect(r)
    langs = _lang_breakdown()
    # A3 quality gate composite: criticals/highs + freshness-age in hours
    try:
        last_sync = con.execute(
            "SELECT ts FROM events WHERE kind='sync' ORDER BY ts DESC LIMIT 1").fetchone()
        fresh_h = round((time.time() - float(last_sync["ts"])) / 3600, 1) if last_sync else None
    except Exception:
        fresh_h = None
    s = q.get("findings", {})
    gate = {
        "ok": (s.get("critical", 0) == 0) and (fresh_h is not None and fresh_h < 24),
        "critical": s.get("critical", 0), "high": s.get("high", 0),
        "freshness_hours": fresh_h,
    }
    try:
        counts = {
            "files": con.execute("SELECT COUNT(*) c FROM files").fetchone()["c"],
            "symbols": con.execute("SELECT COUNT(*) c FROM symbols").fetchone()["c"],
            "chunks": con.execute("SELECT COUNT(*) c FROM chunks").fetchone()["c"],
            "edges": con.execute("SELECT COUNT(*) c FROM edges").fetchone()["c"],
            "vectors": con.execute("SELECT COUNT(*) c FROM vectors").fetchone()["c"],
        }
    except Exception:
        counts = {}
    # B2 vector coverage % (vectors/chunks) — honest live count; embed honours
    # the no-load rule, so there is no guarantee vectors exist.
    try:
        if counts.get("chunks"):
            counts["vector_coverage_pct"] = round(
                counts.get("vectors", 0) * 100.0 / counts["chunks"], 1)
        else:
            counts["vector_coverage_pct"] = 0.0
    except Exception:
        pass
    return {
        "health": q.get("health", {}),
        "findings": s,
        "quick_wins": q.get("quick_wins", []),
        "trends": q.get("trends", []),
        "breakdown": q.get("breakdown", {}),
        "gate": gate,
        "languages": langs,
        "counts": counts,
    }


@app.get("/api/vis/overview")
async def vis_overview_endpoint():
    try:
        return _ok(_vis_get("overview", _overview_builder))
    except Exception as exc:
        return _err("VIS_OVERVIEW_FAILED", str(exc))


@app.get("/api/vis/trends")
async def vis_trends_endpoint(kind: str = "quality", metric: str = "score", days: int | None = None):
    """Generic trend series — snapshot-backed (SPEC-09 §5) with events fallback.
    `kind` = snapshot job (sync|audit|consolidate) or event kind."""
    try:
        return _ok({"kind": kind, "metric": metric,
                    "series": _events_series_snapshots_first(kind, metric, days)})
    except Exception as exc:
        return _err("VIS_TRENDS_FAILED", str(exc))


@app.get("/api/vis/snapshots")
async def vis_snapshots_endpoint(metric: str = "files", range_days: int | None = None):
    """Snapshot-backed series for any metric, optional day window (SPEC-09 §5)."""
    try:
        return _ok({"metric": metric,
                    "series": _snapshot_series(None, metric, range_days)})
    except Exception as exc:
        return _err("VIS_SNAPSHOTS_FAILED", str(exc))


def _git_builder() -> dict:
    """C1 commit velocity (12-week), C2 hotspots + churn-vs-size, C3 co-change
    pairs, C4 activity feed — all read-only from commits/commit_files/edges."""
    import datetime as _dt
    from .store import connect
    from .gitindex import hotspots
    r = _require_root()
    con = connect(r)
    out: dict = {}

    # C1: commits per ISO week for the last 12 weeks.
    try:
        rows = con.execute("SELECT ts FROM commits").fetchall()
        weeks: dict[str, int] = {}
        now = time.time()
        for r in rows:
            age_days = (now - float(r["ts"])) / 86400.0
            if age_days > 84:  # 12 weeks
                continue
            wk = _dt.datetime.fromtimestamp(float(r["ts"]), tz=_dt.timezone.utc).strftime("%G-W%V")
            weeks[wk] = weeks.get(wk, 0) + 1
        out["velocity"] = [{"week": k, "commits": v} for k, v in sorted(weeks.items())]
    except Exception:
        out["velocity"] = []

    # C2: hotspots (score) + fuzzy churn-vs-size (lines proxy — CORE-36 honest).
    try:
        hs = hotspots(r, k=15)
        if hs:
            paths = list({h["path"] for h in hs})
            ph = ",".join("?" * len(paths))
            sizes = {r["path"]: {"lines": r["lines"], "size": r["size"]} for r in con.execute(
                f"SELECT path,lines,size FROM files WHERE path IN ({ph})", paths).fetchall()}
            out["hotspots"] = [{
                **h, "lines": sizes.get(h["path"], {}).get("lines"),
                "size": sizes.get(h["path"], {}).get("size"),
                "proxy": "size-as-churn (CORE-36)",
            } for h in hs]
        else:
            out["hotspots"] = []
    except Exception:
        out["hotspots"] = []

    # C3: co-change pairs (edges kind='co_change'), top 20 by last commit recency
    # is not available; order by commit_files count as recency proxy.
    try:
        rows = con.execute(
            "SELECT src, dst FROM edges WHERE kind='co_change' ORDER BY src LIMIT 250").fetchall()
        out["co_change_pairs"] = [{"src": r["src"], "dst": r["dst"]} for r in rows]
        out["co_change_total"] = len(rows)
    except Exception:
        out["co_change_pairs"] = []
        out["co_change_total"] = 0

    # C4: recent activity feed from events (last 25).
    try:
        feed = []
        for r in con.execute("SELECT ts, kind, payload FROM events "
                             "ORDER BY ts DESC LIMIT 25").fetchall():
            feed.append({"ts": r["ts"], "kind": r["kind"],
                         "payload": _parse_payload(r["payload"])})
        feed.reverse()
        out["activity"] = feed
    except Exception:
        out["activity"] = []
    return out


@app.get("/api/vis/git")
async def vis_git_endpoint():
    try:
        return _ok(_vis_get("git", _git_builder))
    except Exception as exc:
        return _err("VIS_GIT_FAILED", str(exc))


def _findings_builder() -> dict:
    """D1: findings by severity + by rule (open findings only)."""
    from .store import connect
    r = _require_root()
    con = connect(r)
    try:
        by_sev = [{"severity": r["severity"], "count": r["c"]} for r in con.execute(
            "SELECT severity, COUNT(*) c FROM findings WHERE status='open' "
            "GROUP BY severity ORDER BY c DESC").fetchall()]
        by_rule = [{"rule": r["rule"], "count": r["c"]} for r in con.execute(
            "SELECT rule, COUNT(*) c FROM findings WHERE status='open' "
            "GROUP BY rule ORDER BY c DESC LIMIT 20").fetchall()]
    except Exception:
        by_sev, by_rule = [], []
    return {"by_severity": by_sev, "by_rule": by_rule}


@app.get("/api/vis/findings")
async def vis_findings_endpoint():
    try:
        return _ok(_vis_get("findings", _findings_builder))
    except Exception as exc:
        return _err("VIS_FINDINGS_FAILED", str(exc))


def _map_builder() -> dict:
    """G1 tree-map dirs + G2 subsystem overview via summarize.map_."""
    from .summarize import map_
    r = _require_root()
    try:
        return map_(r)
    except Exception as exc:
        raise exc


@app.get("/api/vis/map")
async def vis_map_endpoint():
    try:
        return _ok(_vis_get("map", _map_builder))
    except Exception as exc:
        return _err("VIS_MAP_FAILED", str(exc))


def _signals_builder(days: int = 14) -> dict:
    """F3 broken-signals window (failing tests + type errors). signals table is
    populated by runtime_adapters.broken(); empty table → honest empty state."""
    from .store import connect
    r = _require_root()
    con = connect(r)
    cutoff = time.time() - days * 86400
    try:
        rows = con.execute(
            "SELECT kind, path, name, ts FROM signals WHERE ts>=? ORDER BY ts DESC LIMIT 500",
            (cutoff,)).fetchall()
        return {"window_days": days, "signals": [dict(r) for r in rows],
                "count": len(rows), "kinds": sorted({r["kind"] for r in rows})}
    except Exception as exc:
        return {"window_days": days, "signals": [], "count": 0, "kinds": [],
                "error": str(exc)}


@app.get("/api/vis/signals")
async def vis_signals_endpoint(days: int = 14):
    try:
        return _ok(_vis_get("signals", lambda: _signals_builder(days)))
    except Exception as exc:
        return _err("VIS_SIGNALS_FAILED", str(exc))


@app.get("/api/vis/graph")
async def vis_graph_endpoint(id: str = "", direction: str = "both", depth: int = 1):
    """E1/E2 decorated graph with server-side caps (CORE-38): retrieve.graph caps
    at 200/400 already; when hit, flag lod_fallback so the client offers 2D LOD."""
    from . import retrieve
    if not id:
        return _err("EMPTY_ID", "Symbol id is required")
    r = _require_root()
    try:
        g = retrieve.graph(r, id, direction=direction, depth=depth)
    except Exception as exc:
        return _err("GRAPH_FAILED", str(exc))
    nodes_n = len(g.get("nodes", []))
    edges_n = len(g.get("edges", []))
    return _ok({
        **_decorate_graph(g, r),
        "lod_fallback": nodes_n >= 200 or edges_n >= 400,
        "focus": id, "direction": direction, "depth": depth,
        "node_sources": {"graph_payload": "retrieve.graph", "caps": [200, 400]},
    })


# ── Job runner (in-memory) ────────────────────────────────────────────────────


class RunRequest(BaseModel):
    command: str
    params: dict[str, Any] = {}


# ── SPEC-02 §6: bridge-owned dispatch table (never subprocess) ───────────────
def _merged_param_schema(card) -> dict:
    """SPEC-02 addition 2: registry CommandParameter → canonical JSON Schema."""
    schema: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
    for p in card.parameters:
        tmap = {"str": "string", "int": "integer", "float": "number",
                "bool": "boolean", "list": "array"}
        prop = {"type": tmap.get(p.type, "string"), "description": p.description}
        if p.choices:
            prop["enum"] = p.choices
        if p.default is not None:
            prop["default"] = p.default
        schema["properties"][p.name] = prop
        if p.required:
            schema["required"].append(p.name)
    return schema


def _build_command_table() -> dict:
    """command → {callable, schema, category, priority, label, long_running,
    requires_confirmation}. Callable resolves at dispatch time (module import)."""
    from .command_registry import (  # deferred: registry side effects on module load
        get_command_registry,
    )

    reg = get_command_registry()
    table = {}
    for card in reg.list_all():
        table[card.command] = {
            "label": card.label,
            "description": card.description,
            "category": card.category.value,
            "priority": card.priority.value,
            "long_running": card.long_running,
            "requires_confirmation": card.requires_confirmation,
            "schema": _merged_param_schema(card),
            "callable": card.handler,  # lib-direct wrapper (not subprocess, not print)
        }
    return table


_COMMAND_TABLE: dict | None = None


def _command_table() -> dict:
    global _COMMAND_TABLE
    if _COMMAND_TABLE is None:
        _COMMAND_TABLE = _build_command_table()
    return _COMMAND_TABLE


def _validate_params(name: str, params: dict) -> dict:
    """Validate + coerce params against the merged schema (returns {error} on
    failure, else {params})."""
    card = _command_table().get(name)
    if not card:
        return {"error": f"Unknown command: {name}"}
    schema = card["schema"]
    for req in schema.get("required", []):
        if req not in params or params[req] in (None, ""):
            return {"error": f"Missing required parameter: {req}"}
    coerced = {}
    for k, v in params.items():
        prop = schema["properties"].get(k)
        if prop is None:
            continue  # drop unknown params (CORE-8: keep schema as authority)
        ptype = prop["type"]
        if ptype == "integer":
            try:
                coerced[k] = int(v)
            except (TypeError, ValueError):
                return {"error": f"Parameter {k} must be an integer"}
        elif ptype == "number":
            try:
                coerced[k] = float(v)
            except (TypeError, ValueError):
                return {"error": f"Parameter {k} must be a number"}
        elif ptype == "boolean":
            coerced[k] = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes", "on")
        else:
            coerced[k] = v if isinstance(v, list) else str(v)
    return {"params": coerced}


def _record_job_event(job_id: str, command: str, status: str, result: Any) -> None:
    """Durable job event row (kind=job) written from the worker thread — the WS
    job.done is ephemeral; this is what GET /api/events?kind=job replays."""
    from .store import connect
    try:
        con = connect(_require_root())
        started = _jobs.get(job_id, {}).get("started") or time.time()
        con.execute(
            "INSERT INTO events (ts, kind, payload) VALUES (?, 'job', ?)",
            (time.time(), json.dumps({
                "command": command, "status": status,
                "duration_s": round(time.time() - started, 3),
                "summary": result if isinstance(result, dict) else {"result": result},
            })))
        con.commit()
    except Exception:
        pass  # events are best-effort; the WS job.done already landed


@app.post("/api/run")
async def run_command(req: RunRequest):
    """Execute a command as an in-process job (SPEC-02 §6.1). Never subprocess,
    never print — the registry wrappers call lib directly (CORE-5/CORE-7 handled)."""
    card = _command_table().get(req.command)
    if not card:
        return _err("UNKNOWN_COMMAND", f"Unknown command: {req.command}")
    check = _validate_params(req.command, req.params)
    if "error" in check:
        return _err("INVALID_PARAMS", check["error"])

    job_id = _register_job(req.command)
    _jobs[job_id]["params"] = check["params"]
    r = _require_root()  # capture for the job thread (request contextvar is lost)
    _job_event(job_id, "job.start", repo=r, params=check["params"])

    async def _run():
        try:
            result = await asyncio.to_thread(card["callable"], r, check["params"])
            # registry wrappers return {'error': ...} on failure (CORE-6) — promote
            if isinstance(result, dict) and "error" in result and len(result) == 1:
                raise RuntimeError(result["error"])
            _jobs[job_id]["result"] = result
            _job_done(job_id, repo=r, message="command completed", result=result)
            _record_job_event(job_id, req.command, "done", result)
        except Exception as exc:
            _job_error(job_id, str(exc), repo=r)
            _record_job_event(job_id, req.command, "error", {"message": str(exc)})

    asyncio.create_task(_run())
    return JSONResponse(status_code=202, content=_ok({"job_id": job_id, "status": "running"}))


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content=_err("NOT_FOUND", f"Job {job_id} not found"))
    if job.get("status") not in ("running", "queued", "pending"):
        return _ok({"cancelled": False, "status": job.get("status")})
    # GAP-01: cooperative cancellation — workers poll the job's cancelled flag.
    # The running work loop notices the flag and emits the terminal job.cancelled.
    job["cancelled"] = True
    _job_cancelled(job_id)
    return _ok({"cancelled": True})


# ── Forensics & Deep Intelligence ─────────────────────────────────────────────
@app.get("/api/forensics/summary")
async def forensics_summary(repo: str | None = None):
    r = _resolve_root(repo)
    if not r:
        return JSONResponse(status_code=400, content=_err("NO_REPO", "No repository root found"))
    try:
        from .stack.audit import run_audit
        from .gitindex import hotspots as git_hotspots
        from .analysis import repo_health_report
        from .gapfill import coverage as gapfill_coverage
        from .store import connect

        # 1. Gather audit findings
        audit_res = run_audit(r)
        findings = audit_res.get("findings", [])

        # Categorize findings into 5 forensic dimensions
        ghost_rules = {"HIDDEN-EXPORT", "HIDDEN-ROUTE", "HIDDEN-MODEL", "ARCH-ORPHAN-FILE"}
        silent_rules = {"S1", "DB-NO-AWAIT", "DB-N1", "NEXT-CLIENT-LEAK", "NEXT-ROUTE-NO-ERROR", "NEXT-ACTION-NO-VALIDATE", "SEC-SQL-RAW"}
        arch_rules = {"ARCH-LAYER-VIOLATION", "QA-CIRCULAR", "QA-GOD-MODULE", "QA-DUP", "TAURI-UNGATED-COMMAND"}
        risk_rules = {"QA-UNTESTED-HOT"}
        secret_rules = {"SEC-HARDCODED-SECRET", "ENV-UNDEFINED", "ENV-UNREAD", "DB-SCHEMA-DRIFT", "DB-MIGRATION-INDEX-DRIFT", "DB-DESTRUCTIVE-MIGRATION", "DB-MISSING-INDEX"}

        dim_ghost = [f for f in findings if f.get("rule") in ghost_rules]
        dim_silent = [f for f in findings if f.get("rule") in silent_rules]
        dim_arch = [f for f in findings if f.get("rule") in arch_rules]
        dim_risk = [f for f in findings if f.get("rule") in risk_rules]
        dim_secrets = [f for f in findings if f.get("rule") in secret_rules]

        # 2. Extract dead code candidates & Tarjan cycles
        con = connect(r)
        dead_candidates = []
        cycles = []
        try:
            from .analysis import find_dead_symbols, find_circular_dependencies
            dead_symbols = find_dead_symbols(con, r)
            dead_candidates = [{"symbol": s.get("name"), "path": s.get("path"), "line": s.get("line")} for s in dead_symbols[:50]]
        except Exception:
            pass

        try:
            from .analysis import find_circular_dependencies
            raw_cycles = find_circular_dependencies(con)
            for c in raw_cycles[:20]:
                cycles.append({"symbols": c, "size": len(c)})
        except Exception:
            pass

        # 3. Hotspots correlated with test coverage
        raw_hotspots = git_hotspots(r, limit=10)
        cov_info = gapfill_coverage(r).get("actual_coverage", {})
        cov_pct = cov_info.get("coverage_pct", 0.0)

        risk_hotspots = []
        for h in raw_hotspots:
            churn = h.get("churn", 1)
            symbols_n = h.get("symbols", 0)
            tested_n = h.get("tested", 0)
            file_cov = round((tested_n / max(symbols_n, 1)) * 100, 1) if symbols_n > 0 else cov_pct
            tier = "critical" if churn >= 5 and file_cov < 30 else "high" if churn >= 3 else "medium"
            risk_hotspots.append({
                "path": h.get("path", ""),
                "churn_score": float(churn),
                "symbols_count": symbols_n,
                "tested_count": tested_n,
                "coverage_pct": file_cov,
                "risk_tier": tier,
            })

        by_sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in findings:
            sev = f.get("severity", "low").lower()
            if sev in by_sev:
                by_sev[sev] += 1

        payload = {
            "total_findings": len(findings),
            "by_severity": by_sev,
            "dimensions": {
                "ghost_code": {
                    "count": len(dim_ghost) + len(dead_candidates),
                    "findings": dim_ghost,
                    "dead_stats": {"count": len(dead_candidates), "candidates": dead_candidates},
                },
                "silent_traps": {
                    "count": len(dim_silent),
                    "findings": dim_silent,
                },
                "architecture": {
                    "count": len(dim_arch) + len(cycles),
                    "findings": dim_arch,
                    "cycles": cycles,
                },
                "risk_matrix": {
                    "count": len(dim_risk) + len(risk_hotspots),
                    "findings": dim_risk,
                    "hotspots": risk_hotspots,
                },
                "secrets_env": {
                    "count": len(dim_secrets),
                    "findings": dim_secrets,
                },
            },
        }
        return _ok(payload)
    except Exception as exc:
        return JSONResponse(status_code=500, content=_err("FORENSICS_ERROR", str(exc)))


@app.get("/api/forensics/dossier")
async def forensics_dossier(repo: str | None = None, format: str = "json"):
    r = _resolve_root(repo)
    if not r:
        return JSONResponse(status_code=400, content=_err("NO_REPO", "No repository root found"))
    try:
        from .stack.audit import run_audit
        from .analysis import repo_health_report
        audit_res = run_audit(r)
        health = repo_health_report(r)
        findings = audit_res.get("findings", [])

        if format == "markdown":
            score = health.get("overall_score", 0)
            lines = [
                "# Code Forensics & Intelligence Dossier",
                f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
                f"**Repository:** `{r}`",
                f"**Overall Health Score:** {score:.1f}/100",
                "",
                "## Executive Summary",
                f"- **Total Findings:** {len(findings)}",
                f"- **Critical Hazards:** {len([f for f in findings if f.get('severity') == 'critical'])}",
                f"- **High Priority:** {len([f for f in findings if f.get('severity') == 'high'])}",
                "",
                "## Findings Table",
                "| Severity | Rule | File | Description |",
                "| :--- | :--- | :--- | :--- |",
            ]
            for f in findings:
                lines.append(f"| {f.get('severity', '').upper()} | `{f.get('rule', '')}` | `{f.get('path', '')}:{f.get('line', 1)}` | {f.get('title', '')} |")
            
            lines.append("")
            lines.append("## Remediation Guidance")
            for f in findings[:10]:
                if f.get("suggestion"):
                    lines.append(f"- **{f.get('rule')}** in `{f.get('path')}`: {f.get('suggestion')}")

            md_content = "\n".join(lines)
            return Response(content=md_content, media_type="text/markdown")

        return _ok({"summary": health, "findings": findings})
    except Exception as exc:
        return JSONResponse(status_code=500, content=_err("DOSSIER_ERROR", str(exc)))


class ContextPackRequest(BaseModel):
    target_path: str | None = None
    symbol_id: str | None = None
    max_tokens: int = 4096

@app.post("/api/forensics/context-pack")
async def forensics_context_pack(req: ContextPackRequest, repo: str | None = None):
    r = _resolve_root(repo)
    if not r:
        return JSONResponse(status_code=400, content=_err("NO_REPO", "No repository root found"))
    try:
        from .repo_map import generate_repo_map, RepoMapConfig
        from .tokens import TokenEstimator
        from .predict import predict_next_context

        # 1. Build signature repo map within budget
        budget = min(max(req.max_tokens, 1024), 16384)
        map_budget = int(budget * 0.4)
        cfg = RepoMapConfig(max_tokens=map_budget)
        sig_map = generate_repo_map(r, cfg)

        sections = [
            "# CIP AI CONTEXT PACK (ANTI-COMPACTION ENFORCED)",
            f"Repo: {r}",
            "Target: " + (req.target_path or "Whole Repository"),
            "",
            "## Repository Signature Map",
            sig_map,
        ]

        if req.target_path:
            predicted = predict_next_context(r, "edit", req.target_path)
            if predicted:
                sections.extend([
                    "",
                    "## High-Probability Dependency Context",
                    json.dumps(predicted, indent=2),
                ])

        pack_text = "\n".join(sections)
        estimator = TokenEstimator(limit=128000)
        token_count = estimator.count(pack_text)

        return _ok({
            "context_pack": pack_text,
            "token_count": token_count,
            "token_limit": 128000,
            "budget": budget,
        })
    except Exception as exc:
        return JSONResponse(status_code=500, content=_err("CONTEXT_PACK_ERROR", str(exc)))



# ── MDM (Master Data Model L0–LA) API Routes ─────────────────────────────────

@app.get("/api/mdm/scan")
async def mdm_scan_endpoint():
    """Run full L0–L9 extraction + LA synthesis. Returns layer summaries and finding count.

    Expensive (~10-60s on large repos). Results are persisted to the MDM tables in index.db
    and can be queried cheaply via the other /api/mdm/* endpoints afterwards.

    Response keys:
      - extraction: per-layer result summary (L0–L9)
      - synthesized_findings_count: total LA Finding Records written
      - elapsed_seconds: wall-clock scan time
    """
    from .mdm_engine import run_mdm_extraction
    from .mdm_synthesis import synthesize_la_findings
    from .store import connect
    try:
        r = _require_root()
        con = connect(r)
        ext_res = run_mdm_extraction(r)
        la_findings = synthesize_la_findings(con, r)
        return _ok({
            "extraction": ext_res,
            "synthesized_findings_count": len(la_findings),
            "elapsed_seconds": ext_res.get("elapsed_seconds", 0),
        })
    except ValueError as e:
        return JSONResponse(status_code=400, content=_err("NO_PROJECT", str(e)))
    except Exception as exc:
        return JSONResponse(status_code=500, content=_err("MDM_SCAN_ERROR", str(exc)))


@app.get("/api/mdm/report")
async def mdm_report_endpoint(format: str = "json"):
    """Return the full MDM executive dossier without re-running extraction.

    Uses findings already stored from the last /api/mdm/scan run.

    Query params:
      - format: "json" (default) | "markdown"

    Response (json format):
      - scorecard: 5-dimensional health scorecard with grades (A–F)
      - total_la_findings: count of synthesized LA Finding Records
      - prioritized_findings: top 20 findings with Explainability Traces
      - wiring_gaps: subset of findings that are L4 IPC/event gaps
    """
    from .mdm_synthesis import generate_full_mdm_report, format_report_markdown
    try:
        r = _require_root()
        report = generate_full_mdm_report(r)
        if format == "markdown":
            md = format_report_markdown(report)
            return Response(content=md, media_type="text/markdown")
        return _ok(report)
    except ValueError as e:
        return JSONResponse(status_code=400, content=_err("NO_PROJECT", str(e)))
    except Exception as exc:
        return JSONResponse(status_code=500, content=_err("MDM_REPORT_ERROR", str(exc)))


@app.get("/api/mdm/trace/{finding_id:path}")
async def mdm_trace_endpoint(finding_id: str):
    """Fetch the step-by-step Explainability Trace for a specific LA Finding.

    Path param:
      - finding_id: The finding ID string (e.g. LA-GAP-non_existent_command-ui.ts)

    Response:
      - finding_id: echoed back
      - trace_steps: ordered list of {layer, entity_id, evidence_description}
    """
    from .mdm_schema import get_explainability_trace
    from .store import connect
    try:
        r = _require_root()
        con = connect(r)
        trace = get_explainability_trace(con, finding_id)
        return _ok({"finding_id": finding_id, "trace_steps": trace})
    except ValueError as e:
        return JSONResponse(status_code=400, content=_err("NO_PROJECT", str(e)))
    except Exception as exc:
        return JSONResponse(status_code=500, content=_err("MDM_TRACE_ERROR", str(exc)))


@app.get("/api/mdm/gaps")
async def mdm_gaps_endpoint():
    """Return only the L4 IPC/event wiring gaps from the last MDM scan.

    A lightweight focused view scoped to silent runtime traps:
      - IPC_UNREGISTERED_COMMAND: frontend invoke() has no backend handler
      - DEAD_EVENT_LISTENER: listen() registered but no matching emitter

    Response:
      - swallow_count: AST bare-except swallow count
      - wiring_gaps_count: total IPC+event gaps
      - wiring_gaps: list of gap objects (type, name, path, line, detail)
    """
    from .mdm_engine import scan_l4_flow_and_wiring
    from .store import connect
    try:
        r = _require_root()
        con = connect(r)
        gaps = scan_l4_flow_and_wiring(con, r)
        return _ok(gaps)
    except ValueError as e:
        return JSONResponse(status_code=400, content=_err("NO_PROJECT", str(e)))
    except Exception as exc:
        return JSONResponse(status_code=500, content=_err("MDM_GAPS_ERROR", str(exc)))


@app.get("/api/mdm/scorecard")
async def mdm_scorecard_endpoint():
    """Return the 5-dimensional health scorecard from the last MDM scan.

    Lightweight endpoint — reads from pre-computed MDM findings; no re-scan.

    Response:
      - overall_score: 0-100 composite score
      - overall_grade: A/B/C/D/F letter grade
      - dimensions: {reliability_and_flow, security_and_secrets,
                     architecture_boundaries, code_quality_smells,
                     evolution_and_churn} each with {score, grade}
      - counts: {critical, high, medium, total_findings}
    """
    from .mdm_synthesis import compute_repo_scorecard
    from .store import connect
    try:
        r = _require_root()
        con = connect(r)
        sc = compute_repo_scorecard(con)
        return _ok(sc)
    except ValueError as e:
        return JSONResponse(status_code=400, content=_err("NO_PROJECT", str(e)))
    except Exception as exc:
        return JSONResponse(status_code=500, content=_err("MDM_SCORECARD_ERROR", str(exc)))


# ── WebSocket ──────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    # P5 T5.1: subscribe the connection to a project bucket (?repo=<id>).
    # The value must be a registered project id — otherwise it joins the
    # legacy "*" bucket (un-scoped, SPEC-15 backward compat).
    repo_param = ws.query_params.get("repo")
    bucket = "*"
    if repo_param:
        from .project_registry import get_registry, ProjectRegistry
        pid = ProjectRegistry.project_id(repo_param)
        if get_registry().has(pid):
            bucket = pid
    _ws_clients.setdefault(bucket, set()).add(ws)
    # Capture the running loop so worker threads can schedule broadcasts
    global _loop
    _loop = asyncio.get_running_loop()
    try:
        while True:
            data = await ws.receive_text()
            # Client can send pings or commands
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_json({"type": "pong", "timestamp": time.time()})
                elif msg.get("type") == "subscribe":
                    # GAP-02: replay durable events since a timestamp (WS
                    # reconnect catch-up, SPEC-14 §6.2).
                    since = msg.get("since")
                    if isinstance(since, (int, float)) and since > 0:
                        events = _events_feed(since=float(since), limit=500)
                    else:
                        events = []
                    await ws.send_json({
                        "type": "events.replay",
                        "events": events,
                        "timestamp": time.time(),
                    })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        # P5 T5.1: remove from the project bucket it joined (and empty the bucket)
        bucket_clients = _ws_clients.get(bucket, set())
        bucket_clients.discard(ws)
        if not bucket_clients:
            _ws_clients.pop(bucket, None)


# ── SPA static files ───────────────────────────────────────────────────────────
DIST = Path(__file__).resolve().parent.parent.parent / "web" / "dist"

if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Catch-all: serve index.html for SPA routing."""
        file = DIST / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(DIST / "index.html")
