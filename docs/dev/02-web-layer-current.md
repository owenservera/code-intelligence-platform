# Current Web Layer Analysis

**Status:** Draft — source review of the existing web surface
**Date:** 2026-08-15
**Context:** This is the layer we are rebuilding (FastAPI + React). Documenting what exists so nothing is lost.

---

## 1. Three overlapping web surfaces

| Surface | Entry | Port | Base | Purpose |
|---|---|---|---|---|
| Dashboard (web) | `web_server.py:start_web_server()` | 8090 (HTTP) + 8081 (WS) | `http.server.HTTPServer` + `SimpleHTTPRequestHandler` | Interactive dashboard (v2.0, vanilla JS) |
| Mission Control | `dashboard.py:serve_dashboard()` | 8790 | `ThreadingHTTPServer` | Read-only overview (compact, no WS) |
| JSON-RPC/MCP | `server.py:serve()` | 8080 (config) | custom `BaseHTTPRequestHandler` | Agent tool surface |

## 2. `web_server.py` (current interactive dashboard)

### 2.1 Handler architecture
- `DashboardAPIHandler(SimpleHTTPRequestHandler)` with class-level `root` + `ws_manager`.
- GET `/` and `/dashboard` serve `static/dashboard.html`; other paths → static files.
- All `/api/*` → JSON responses with `Access-Control-Allow-Origin: *`.

### 2.2 Existing API surface (GET)
| Endpoint | Returns |
|---|---|
| `/api/ping` | `{status, timestamp}` |
| `/api/health` | `analysis.repo_health_report(root)` — full report (score, critical, debt, hotspots, recs) |
| `/api/search?q=&limit=` | `retrieve.hybrid_search(root, q, limit)` |
| `/api/symbols` | first 1000 symbols (id, name, kind, path, start_line, end_line) |
| `/api/impact?symbol=` | `ImpactAnalyzer(con).analyze_impact(symbol_id)` |
| `/api/gaps` | `GapFiller(con).find_gaps()` — typed gap objects |
| `/api/memory` | temporal facts + recent episodes (from memory.db / episodes.db) |
| `/api/graph` | first 500 symbols + 1000 edges |
| `/api/stats` | file/symbol/chunk/edge counts + last_sync |
| `/api/config` | index/embed/retrieval/memory sections of config |

### 2.3 Existing API surface (POST)
| Endpoint | Action |
|---|---|
| `/api/sync` | `indexer.sync(con, cfg)` + broadcast WS `sync_complete` |
| `/api/analyze` | `analysis.repo_health_report(root)` |
| `/api/audit` | `stack_audit.audit(root, refresh=True)` |
| `/api/memory/store` | `AgentMemory(root).remember(key, value, source)` |
| `/api/memory/recall` | `TemporalKnowledgeGraph.query_facts(...)` |

### 2.4 Notes / bugs
- `indexer.sync(con, cfg)` — signature mismatch: `sync()` in indexer is
  `sync(root=None, full=False, do_embed=True, progress=None)` (no `con`/`cfg`). So
  `/api/sync` likely raises → 500. Verify.
- `_api_analyze` returns the report but does not broadcast; `_api_audit` no broadcast.
- HTTP base is single-threaded `HTTPServer` (blocking sync runs freeze the UI). WS runs
  on separate port+1 via `websocket_handler.py`.
- `memory.py` frontend (JS) calls `/api/memory/consolidate` and `/api/memory/clear` (POST)
  but **no such routes exist** in web_server — dead buttons.

## 3. `websocket_handler.py` (current WS server)

- `DashboardWebSocketServer` (websockets lib, port 8081): connections, subscriptions,
  `subscribe/unsubscribe`, broadcast to topics.
- `DashboardEventEmitter`: `emit_index_update`, `emit_health_update`, `emit_search_result`,
  `emit_memory_update`.
- Frontend `websocket.js`: reconnect logic, `subscribe(topic, handler)`, topics wired:
  `index`, `health`, `sync`, `memory`. Frontend subscribes to `connected`/`disconnected`.

## 4. `dashboard.py` (Mission Control — read-only)

Rich compact overview. Reuses core lib directly (no subprocess). Data payloads:

- `/api/overview` → stats, freshness (lag<300s), embedder name, severity summary, broken
  signals, 12-week commit velocity, hotspots (k=8), top dirs by file count, quadrant
  (churn vs size top-120), auto-generated **briefing notes** (staff-engineer style),
  gate pass/fail.
- `/api/findings?severity=&rule=` (limit 200), `/api/quickwins` (12),
  `/api/routes`, `/api/models`, `/api/search?q=` (k=8), `/api/graph?id=`,
  `/api/impact?target=`.
- Serves `static/dashboard.html` — NOTE: dashboard.py serves the SAME HTML file that
  web_server.py serves, but its API paths differ (`/api/overview` etc.). This is a
  **functional mismatch**: the HTML/JS expects web_server's endpoints
  (`/api/stats`, `/api/health`, `/api/graph`, `/api/gaps`, `/api/memory`, `/api/config`),
  not dashboard.py's. So `cip dashboard` renders a partially broken page.

## 5. `dashboard_state.py` (reactive state)

- `DashboardState`: thread-safe props with listeners: health_score, index_fresh,
  git_branch, uncommitted_files, last_sync. `to_dict()`.
- `StateUpdater`: background thread polling every 30s → updates health (via
  `gapfill.score`), index freshness (meta `last_sync` < 1h), git branch,
  `git diff --name-only` count.
- This is the seed of the "stateful" backend we need to generalize (currently only 4 props).

## 6. Current static frontend (to be replaced)

Vanilla JS, 8 modules, no build step:
- `store.js` — Redux-like store (state/history/undo/redo).
- `app.js` — tab nav, theme toggle, WS subscriptions, map controls, and data loaders for
  `/api/stats|health|graph|gaps|memory|config`. **Action buttons (sync/analyze/audit/
  gapfill/consolidate/export) exist in HTML but have NO handlers wired.**
- `search.js`, `impact.js`, `memory.js`, `components.js`, `graph.js` — per-tab logic.
- `websocket.js` — WS client.
- libs: `chart.min.js`, `d3.v7.min.js`, `marked.min.js` (vendored, no package.json).

## 7. Summary of problems the redesign must solve

1. **No full CLI capability** — only 6 read paths; zero command execution surface.
2. **Dead UI** — action buttons and `/api/memory/consolidate`/`clear` are unbacked.
3. **Blocking sync** — single-threaded HTTP; heavy ops freeze UI; no progress streaming.
4. **Split-brain dashboards** — two servers serving one HTML with incompatible API paths.
5. **Inert state layer** — `dashboard_state.py` has only 4 props, polled, not event-driven.
6. **No stats visualization beyond one gauge** — no trends, no per-rule/per-file breakdowns,
   no embed metrics, no memory visualizations.
7. **No WS protocol contract** — topics are ad-hoc; events don't carry payload schemas.
8. **Auth**: none (fine for local tool, but must be a decision).
