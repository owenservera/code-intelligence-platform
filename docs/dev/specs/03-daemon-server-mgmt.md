# SPEC-03 — Daemon & Server Management (FR-3)

- **Requirement source:** `05-requirements.md` §2 FR-3, §7.1(12), §7.4, ISSUE-110
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{daemon,embed,watch,server}.py`
- **Build order dependency:** SPEC-01 (shell), SPEC-02 (command center), SPEC-14 (WS contract).

---

## 1. Goal & owner intent

Full daemon + embedding-service control from the UI: status (running/pid/port/health/uptime),
start/stop/restart, auto-manage on demand (§7.4: console lazily auto-starts the embed daemon for
first embedding need, shows warm-up status, never requires manual `cip daemon`), log tail, and an
embedding-service panel (backend, model, dim, warm/loading, queue depth, latency). Realtime status
always current (§7.1-12).

## 2. Truth-grounded core surface (verified 2026-08-15)

| Need | Core call (verified) | Returns |
|---|---|---|
| Status | `daemon.daemon_status(root)` `daemon.py:40` | `{pid, port, alive, warm, health:{warm,model,dim,pid,uptime_s}}` |
| Start | `daemon.daemon(root, port=8787, interval=1.0)` `daemon.py:121` | blocking; writes `.cip/data/daemon.{lock,port,log}`; spawns `watch` thread + `serve()` HTTP |
| Stop | `daemon.daemon_stop(root)` `daemon.py:62` | Windows: `taskkill /F /T`; removes lock/port; prints "stopped" |
| Port discovery | `embed.find_daemon_port(root)` `embed.py:55` | reads `daemon.port` file + health-check |
| Embed health | `embed.service_health(port)` `embed.py:44` | `{warm, model, dim, pid, uptime_s}` or `None` (0.5 s timeout) |
| Embedder resolution | `embed.get_embedder(cfg, root)` `embed.py:160` | warm daemon → LocalEmbedder (in-process); **NEVER autostarts daemon** (docstring `embed.py:8`) |
| Watch loop | `watch.watch(root, interval)` `watch.py:14` | mtime-poll + debounce → `sync()`; logs `synced +d -d ~emb in Nms` |
| Server (daemon payload) | `server.serve(root, port)` `server.py:170` | ThreadingHTTPServer; `/embed/health`, `/embed`, `/tools`, `/ontology.json`, `/rpc` |
| Config anchors | `config.default.toml` `[daemon] port=8765, enable_watcher, watcher_interval=5` `:134-143` | **default daemon port is 8765; code default is 8787** (mismatch, see CORE-10) |

## 3. UI/UX contract

- **Daemon panel** (chip in status cluster → detail): pid, port, alive, warm, model, dim,
  uptime; actions Start / Stop / Restart; auto-manage toggle (`[web].auto_manage_daemon`);
  log tail (last N lines, auto-scroll, follow).
- **Embedding service panel:** resolution path taken (`get_embedder_with_feedback` output),
  backend (local/service/hashing), model, dim, warm/loading, queue depth, last latency (via
  `embed_ping`), effective vector backend (BUG-019: numpy vs sqlite-vec).
- **States:** starting (warm-up spinner + "loading model…"), running, stopped, error.
  Auto-manage: on first embedding need the console starts the daemon, waits on
  `/embed/health` warm, then proceeds — surfaced as a progress state, never a silent 120 s hang.
- **Restart =** stop + start (daemon APIs are blocking; run as a job per SPEC-02).

## 4. API / WS contract

REST:
- `GET /api/daemon` → `daemon_status(root)` + `embed.service_health(port)` merged.
- `POST /api/daemon/start` → `{job_id}`; runs `daemon.daemon(...)` in background worker (blocking
  loop) — status derived from lock/port/health, not the worker return.
- `POST /api/daemon/stop` → `{job_id}`; runs `daemon_stop`.
- `POST /api/daemon/restart` → stop then start (single job).
- `POST /api/daemon/auto-manage` → sets `[web].auto_manage_daemon` in `.cip/config.toml`.
- `GET /api/embed/status` → embedder resolution + `embed_ping` latency + effective backend.
- `GET /api/daemon/log?lines=N&follow=true` → log tail.

WS (`/ws`, SPEC-14):
- `status.daemon {pid,port,alive,warm,health}` pushed on change / on poll.
- `status.embed {backend,model,dim,warm,queue,latency_ms,effective_backend}` pushed on change.
- `daemon.log {line}` streamed while following.

## 5. Data contract

- All state is file/HTTP-derived: `.cip/data/daemon.{lock,port,log}` + `/embed/health`. No new tables.
- Log tail: append-only `daemon.log` — a new `daemon.read_log(root, lines)` helper (§6).
- Queue depth / latency: **does not exist in core today** (see CORE-11).

## 6. Backend additions (lib/cipkg in scope)

1. **`daemon.start_daemon(root, port, interval)`** — non-blocking wrapper that spawns
   `daemon.daemon` in a child thread (or subprocess) and returns immediately; used by the
   background job. Core `daemon()` is blocking by design.
2. **`daemon.read_log(root, lines=200)`** — read tail of `daemon.log` (new helper).
3. **Auto-manage hook in `embed.get_embedder`** — when `[web].auto_manage_daemon` and no warm
   daemon: start one (via 1) and poll `/embed/health` until warm (bounded, e.g. 60 s), *then*
   fall back to LocalEmbedder. Do NOT change default behavior (docstring `embed.py:8` keeps
   explicit-start as the default; auto-manage is a web-layer opt-in).
4. **Queue/latency telemetry** — optional: `RemoteEmbedder` records per-call latency; daemon
   `/embed/health` could add `queue_len`. Mark as enhancement (CORE-11).

## 7. Core issues / risks (flagged, grounded)

- **CORE-10 — Daemon port mismatch: config default 8765 vs code default 8787.**
  `config.default.toml:137` says `port = 8765`; `daemon.py:123` hardcodes `port or 8787`;
  registry `daemon_start` param default is 8787 (`command_registry.py:206`). Status panel would
  show a port that disagrees with the code default. → define one truth (propose `[daemon] port=8765`
  everywhere, or 8787 everywhere) and surface the effective port. *(New issue.)*
- **CORE-11 — No queue-depth or latency telemetry exists.**
  `service_health` (`embed.py:44`) returns only `{warm,model,dim,pid,uptime_s}`; no queue or
  latency fields. FR-3's "queue depth, last latency" have **no data source**. → addition 4 or
  reduce the panel to what exists (ping latency measured client-side). *(New issue.)*
- **CORE-12 — `daemon()` is blocking and `watch()` runs forever in-process.**
  `daemon.py:121` loops in `serve()`; `watch.py:14` is an infinite `while True`. Starting these
  inside the FastAPI process would block the event loop. → non-blocking wrapper (addition 1) is
  mandatory; daemon must run in its own thread/subprocess. *(New issue.)*
- **CORE-13 — `daemon_stop` on Windows uses `taskkill /F /T` (process-tree kill).**
  `daemon.py:73-78`. If the console's own process ever hosts the daemon, this kills itself.
  → the web-managed daemon must be a **separate subprocess** so stop is always safe. *(New issue.)*
- **CORE-14 — embed fallback can still block up to 120 s on first need** (BUG-009/010): with
  auto-manage, the UI must show "starting daemon / loading model" progress rather than blocking
  a request (SPEC-02 job semantics). Reconfirm with addition 3 bounded warm-wait.
- Watch: `watch.watch` logs via `print` to stdout (which is teed to `daemon.log` inside
  `daemon()`), so log tail has content but is unstructured (free text). Keep as free text; don't
  parse into events.

## 8. Acceptance checks (from §6 / §7.5)

- [ ] Daemon panel shows real {pid,port,alive,warm,model,dim,uptime}; Start/Stop/Restart work.
- [ ] Auto-manage: opening the console with embed work pending auto-starts the daemon with a
      visible warm-up state; no request blocks beyond the bounded wait.
- [ ] Log tail follows `daemon.log` live.
- [ ] Embed panel shows backend/model/dim/warm + measured ping latency; effective vector backend
      is shown (numpy vs sqlite-vec, BUG-019).
- [ ] Stop never kills the console process (daemon runs as separate subprocess).
- [ ] Effective daemon port is consistent across config/code/UI (CORE-10 resolved).
