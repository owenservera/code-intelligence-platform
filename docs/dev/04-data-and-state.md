# Data Layer & Statefulness (for a stateful, live web index)

**Status:** Draft — source review
**Date:** 2026-08-15
**Purpose:** Understand what "state" exists, where it lives, and how to push it to a
reactive web UI (durable store, ephemeral state, live events).

---

## 1. Where state lives today

| State | Location | Durable? | Lifespan |
|---|---|---|---|
| Code model | `.cip/data/*.db` (SQLite, schema in `store.py`) | Yes | repo lifetime |
| Agent memory facts | `.cip/memory.db` (TemporalKnowledgeGraph) | Yes | repo lifetime |
| Episodes | `.cip/episodes.db` (EpisodicMemory) | Yes | repo lifetime |
| Audit findings | `findings` table (in store) | Yes | until re-audit |
| Events timeline | `events(ts, kind, payload)` | Yes | pruned by vacuum |
| Dashboard reactive state | `dashboard_state.py` `DashboardState` | No | process lifetime |
| Embedder model | in-memory (sentence-transformers) or service | No | process/service |
| Daemon state | `.cip/*.pid`, health file | Partial | process |

## 2. SQLite store schema (`store.py`)

Tables: `meta(key,value)`, `files`, `symbols`, `chunks`, `file_imports`,
`edges(src,dst,kind,src_path)`, `vectors(id,model,vec)`, `events(ts,kind,payload)`,
`summaries`, `commits`, `commit_files`, `signals(kind,path,symbol_id,name,payload,ts)`,
`symbol_calls`. Indexes on symbol name/path, chunk path, edges src_path/dst, commit_files
path, signals path/kind.

Helpers: `connect(root)`, `get_meta`, `set_meta` (keys like `last_sync`,
`embedder_name`).

## 3. Index lifecycle (`indexer.sync`)

```
sync(root, full=False, do_embed=True, progress=None)
  → _sync_body: scan files → parse → _bulk_write → link_imports
  → resolve_symbol_edges → build_tested_by → embed_pending(progress=…)
  → returns stats {files, symbols, chunks, edges, embedded, ms}
```

- `progress` callback exists (phase, cur, total) — perfect hook for WS progress streaming.
- `compute_stats(con)` → aggregated counts for dashboards.
- `meta.last_sync` drives "freshness" everywhere.

## 4. Embedding (heavy, must not block the web request loop)

`embed.py` + `vecstore.py` + `lancedb_store.py`; config `[embed]`:
- `backend = auto | local | service | hashing`
- `model = BAAI/bge-small-en-v1.5`, `dim=384`, `batch_size=32`
- daemon port range 8765–8775, service port 8787
- `embed_pending(con, cfg, batch, progress)` streams progress already.

**Design requirement:** embedding runs in a background worker/daemon; the web console
subscribes to progress via WS, not by blocking HTTP.

## 5. Memory system

- `TemporalKnowledgeGraph(memory.db)`: `add_fact`, `query_facts(subject, predicate,
  at_time)`; facts have `valid_from`, `confidence`.
- `EpisodicMemory(episodes.db)`: `record_episode`, `query_episodes(limit)`; episodes have
  `type`, `context`, `outcome`.
- `MemoryConsolidator`: promotes short→long-term; `run_consolidation_daemon(db, interval)`.
- `AgentMemory`: `remember(key, value, source)`.
- Config `[memory]`: enable_temporal/episodic/procedural, consolidation_interval (24h),
  lookback 7d, max_episodes.

## 6. Signals & events (the "telemetry" backbone)

- `events` table: append-only timeline of every action (ingest, sync, memory ops…) —
  **the data source for activity feeds and trends**.
- `signals` table: test failures + type errors (kind `test_fail`, `type_error`) via
  `runtime_adapters.broken(root, window_days=14)`.
- `commits`/`commit_files`: churn, co-change, hotspots, velocity (12-week chart in
  `dashboard.py:velocity`).

## 7. Analysis/audit data for dashboards

- `analysis.repo_health_report` → `{overall_score, critical_issues, high_priority,
  test_coverage, technical_debt, hotspots, recommendations}`.
- `stack_audit.summarize(con)` → severity counts by category.
- `stack_audit.findings` / `findings_structured` → per-file findings.
- `stack_audit.quick_wins` → ranked refactor opportunities.
- `gapfill.score(root)` → health score 0–100 (used by dashboard_state updater).
- `dashboard.py:briefing` → derived staff-engineer notes (refactor/risk/blocker/
  opportunity/health/pattern/ok) — a nice, low-cost addition to the new console.

## 8. Ephemeral dashboard state — generalization needed

Current `DashboardState` props: health_score, index_fresh, git_branch, uncommitted_files,
last_sync; `StateUpdater` polls every 30s.

**For the new console** we want a richer, event-driven state model:
- Index state machine: `idle → indexing → linking → embedding → done/error` with counts.
- Job registry for long-running commands (job_id, command, status, progress, logs, result).
- Live stats cache (stats computed once per change, invalidated by sync events).
- Git status (branch, dirty count) — polled cheaply (30s) or on demand.
- Daemon status (running, uptime, cache stats) — via `daemon.daemon_status`.
- Embedder status (backend, model, warm, queue depth) — via `embed_ping`/status.

## 9. Concurrency constraints for FastAPI design

- SQLite: single-writer. Long sync/embed must not hold a write transaction across
  requests. Use the existing `indexer` batching; run heavy jobs in a background
  worker; expose read-only connections to the UI.
- `indexer.sync` already uses `ThreadPoolExecutor`/workers internally (config `perf.workers`).
- WS broadcasts must be lightweight snapshots/deltas, not full re-fetch payloads.
- Memory DBs are separate files — safe to read concurrently with the main store.

## 10. Recommended "stateful index" contract for the UI (v0 sketch)

Backend owns:
- `IndexSnapshot`: {phase, files, symbols, chunks, edges, embedded, last_sync, freshness}.
- `Job`: {id, command, status, progress, logs[], started, finished, result?}.
- `MemorySnapshot`: {facts count, episodes count, last_consolidation}.
- `DaemonSnapshot`: {running, port, uptime, pid}.
- `HealthSnapshot`: {score, gate, severity, broken}.

Frontend holds it in a Zustand store; backend pushes `snapshot.*` and `job.*` events over
WS; REST endpoints do initial hydration + on-demand reads.
