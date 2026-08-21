# CIP System Log — Features, Configs, Outputs, Command Layer, API

**Status:** Complete system log (deep-dive #2, per owner request)
**Date:** 2026-08-15
**Context:** Owner asked for deeper understanding of *what the project does* — its
features, configurations, outputs, command layer, and API — before proceeding. This is
the authoritative reference doc; `01-repo-overview.md` covers module inventory.

---

## 1. What CIP Is

**CIP (Code Intelligence Protocol)** is a continuously-updated model of a codebase:
structure, history, tests, runtime health, and semantic audit. It exists to give AI
agents and developers fast, correct navigation of complex repos. It is repo-agnostic,
self-installing, and self-updating.

**Core loop:** scan → parse (AST) → link → embed → retrieve. Plus git history, audit
rules, memory, and agent surfaces layered on top.

**Three ways to drive it:** CLI (`cip`), agent tools (MCP/JSON-RPC), and the web
console (being redesigned now).

---

## 2. Features (from README + source)

### 2.1 Core intelligence
- **Semantic code search** — hybrid lexical + vector + graph with RRF fusion and
  cross-encoder reranking (`retrieve.hybrid_search`).
- **Symbol navigation** — find definitions, relationship counts, click-through.
- **Impact analysis** — blast radius for a file/symbol or a git diff
  (`stack/impact.py`: `impact`, `impact_structured`, `impact_diff`).
- **Quality auditing** — ~26 rules (`stack/rules.py`): hidden exports/routes/models,
  DB N+1, missing indexes, missing await, destructive migrations, schema drift,
  secrets, raw SQL, env leaks, layer violations, god modules, untested-hot, circular
  deps, QA rules (console, ts-ignore, dup), orphan files, Tauri command gating.
- **Gap detection** — missing docs/tests/type hints (`gapfill.GapFiller`).

### 2.2 Agent memory
- **Temporal Knowledge Graph** — facts with validity windows + confidence.
- **Episodic Memory** — learn from past interactions/errors/outcomes.
- **Procedural memory** — remember successful workflows (AgentMemory key/value).
- **Consolidation** — background promotion of short→long-term patterns.

### 2.3 Advanced indexing
- **AST-aware chunking** — semantic boundaries instead of line cuts.
- **SCIP integration** — precise cross-file symbol resolution.
- **Repository maps** — token-efficient architecture overviews (`summarize.map_`).
- **Hybrid search** — lexical + semantic + graph traversal with intent routing.

### 2.4 Stack-aware analysis
- **TypeScript/Next.js** — route inventory, orphan/used detection.
- **Prisma** — schema parse, model report, store-contract analysis.
- **SQLite/DB** — N+1, missing index, await checks.
- **Custom rules** — user-defined via `repo-settings`/config.
- **Tauri** — command/capability inventory.

### 2.5 Agent integration
- MCP stdio server (`cip mcp`) + JSON-RPC over HTTP (`cip serve`).
- Agent hook installation (claude-code, opencode) + git hooks (post-commit/merge/checkout).

### 2.6 Verification & tooling
- `verify` gate (broken tests + typecheck + lint + audit), `gate` (CI exit-code gate),
  `selftest`, `doctor`, `admission` (index admission audit).

---

## 3. Configurations

### 3.1 File layout
- `config.default.toml` / `config.v2.default.toml` — shipped defaults.
- `.cip/config.toml` + `.cip/ontology.json` — per-repo overrides (created by `cip init`).
- `repo-settings/detectors.py` — repo-type detection used at init.
- Load order: `base._load_default_toml()` merges both shipped defaults; `load_config`
  overlays the repo `.cip/config.toml`; hardcoded `DEFAULT_CONFIG` is the floor.

### 3.2 Key sections (what they control)

| Section | Controls |
|---|---|
| `[meta]` | version, schema_version (currently 11) |
| `[index]` | exclude_patterns, max_file_size (1MB), chunk_size (1000), overlap (200), ast_aware_chunking, languages, test_globs |
| `[embed]` | backend (auto/local/service/hashing), model (bge-small-en-v1.5, 384d), batch_size, daemon port range 8765–8775, service_port 8787 |
| `[retrieval]` | hybrid_weight (0.7), max_results, rerank model, graph depth, HyDE toggle, lexical_k/vector_k (30/30), context_budget_tokens (6000) |
| `[memory]` | enable temporal/episodic/procedural, consolidation_interval (24h), memory_db/episodes_db paths, max_episodes, lookback 7d |
| `[mcp]` | host, port 8080, autostart, allowed_origins, max_request_size (10MB) |
| `[daemon]` | host, port 8765, enable_watcher, watcher_interval, cache_size/ttl |
| `[analysis]` | health_weights (coverage .3/quality .3/recency .2/complexity .2), audit_refresh_interval, max_findings |
| `[logging]` | level, log file `.cip/logs/cip.log`, max_size, backup_count, debug flag |
| `[performance]` | db_batch_size, worker_threads, parallel_indexing, max_parallel_workers |
| `[ui]` | dashboard refresh/theme, animations, max_list_items |
| `[summary]` | backend (structural/llm), llm_model, max_llm_per_sync |
| `[git]` | depth 500, co_change_min 2 |
| `[rerank]` | enabled |
| `[vector]` | backend (sqlite / sqlite-vec) |
| `[perf]` | workers (0=auto, 1=serial, N=explicit) |
| `[maintain]` | event_days (30) |
| `[audit]` | ignore_rules |
| `[v2: interactive/context/command_adaptation/error_handling/workflows/ui]` | v2 TUI/interactive/adaptation/error-recovery/UI config (used by terminal_dashboard, command_adapter, error_system) |

> **Design note for the web console:** config is currently read in several places with
> different helpers (`load_config`, `_parse_toml_naive`). The new API should expose one
> canonical `/api/config` that returns the *effective* merged config (defaults →
> shipped → repo override) and marks source per key.

---

## 4. Outputs (everything the system writes)

### 4.1 Index artifacts (under `<repo>/.cip/`)
| Artifact | Location | Written by |
|---|---|---|
| Main index DB | `.cip/data/index.db` | `store.connect` (SQLite, 13 tables + FTS5) |
| Temporal fact DB | `.cip/memory.db` | `memory/temporal_graph.py` |
| Episodic DB | `.cip/episodes.db` | `memory/episodic.py` |
| Daemon lock/port/log | `.cip/data/daemon.{lock,port,log}` | `daemon.py` |
| App log | `.cip/logs/cip.log` | logging config |
| Per-repo config/ontology | `.cip/config.toml`, `.cip/ontology.json` | `cip init` |

### 4.2 Index DB tables (output schema)
`meta`, `files`, `symbols`, `chunks`, `chunks_fts` (virtual), `file_imports`, `edges`,
`vectors`, `events`, `summaries`, `commits`, `commit_files`, `signals`,
`symbol_calls`.

### 4.3 Export outputs (`cip export`)
- `json` — full DB dump (`_json_dump`).
- `lsif` — LSIF-format symbol dump (`_lsif`).
- `markdown` — repo tree + symbols markdown (`_markdown`).

### 4.4 Reports / derived data
- `analysis.repo_health_report` — health report JSON.
- `stack_audit.report_markdown` — audit report markdown.
- `summarize.summary/map_` — hash-cached summaries stored in `summaries` table.
- `dashboard.py:briefing` — derived staff-engineer notes.
- `selftest` / `doctor` — diagnostics printed to stdout.
- `gapfill.*` — 12 analysis outputs (coverage, dead, circular, blame, score, migrations,
  env, logs, metrics, features, deps, api).

### 4.5 What the daemon serves
`GET /health`, `GET /tools`, `GET /ontology.json`, `GET /embed/health`
(`{warm, model, dim, pid, uptime_s}`), `POST /embed` (`{texts}` → vectors), `POST /rpc`.

---

## 5. Command Layer (CLI — authoritative surface)

> Full argparse surface catalogued in `03-cli-and-registry.md`. Here: behavior notes.

### 5.1 Lifecycle
`init` → `detect` → `index [--full|--reembed]` → `sync` (scan+link+embed) → `watch` →
`daemon start/status/stop` → `doctor`.

### 5.2 Query
`search <q> [-k]`, `symbol <name>`, `graph <id> [--direction --depth]`,
`context [q] [--symbol --budget]`, `summary [path]`, `map`, `describe [entity]`,
`history <path>`, `route <q> [--agent]`.

### 5.3 Quality
`audit [--file|--diff]`, `findings [--severity --rule --path --limit --structured]`,
`refactors`, `impact [target] [--ref --depth --structured]`, `routes`, `models`,
`gate`, `verify [--typecheck --lint --no-audit --blocking]`.

### 5.4 Maintenance
`upgrade`, `rebuild`, `verify-index [--repair]`, `vacuum [--days]`,
`git-index [--depth]`, `broken`, `hotspots`.

### 5.5 Gapfill (12) — *under owner scrutiny*
`coverage`, `dead`, `circular`, `blame <path> [line]`, `score`, `migrations`, `env`,
`logs`, `metrics`, `features`, `deps`, `api`.

### 5.6 Agent / integration
`ingest --kind <vitest|jest|pytest|tsc|generic|eslint> --file`, `export`,
`hook <post-edit|pre-edit> args…`, `session start/end/status`,
`learning analyze/update/report/patterns`, `predict --operation`,
`suggest-context <path> [--line]`, `admission [--path]`.

### 5.7 Servers
`serve [--port]` (JSON-RPC + embed), `mcp` (stdio), `dashboard [--port 8790]`
(mission control), `dashboard-web [--port 8090]` (interactive — being replaced),
`embedder`, `embed-ping [count]`, `tools [--schema]`, `selftest`.

### 5.8 Dispatch gap (critical for web bridge)
`dispatch_command` maps only ~40 of ~70 argparse subcommands; several registered
commands (`refactors`, `routes`, `models`, `gate`, `admission`, `embedder`,
`embed-ping`, and the 12 gapfill cmds, `watch`, etc.) are **not** in the handler dict —
they hit `unknown command`. The web layer MUST call lib functions directly (as
`server.py:call_tool` does), never shell out to `cip`.

---

## 6. API Layer (existing surfaces to unify)

### 6.1 `server.py` — JSON-RPC + MCP (agent surface)
- `TOOLS` (20): search, symbol, graph, context, summary, map, describe, broken,
  hotspots, history, route, route_for_agent, git_index, index_status, audit, findings,
  refactors, impact, routes, models.
- `call_tool(root, cfg, name, args)` → direct lib dispatch, envelope
  `{ok, tool, result, next_ops, index_stats}`. `_next_ops` suggests follow-up tool
  calls (agent-native chaining).
- `index_status(root)` → stats + commits/signals/summaries counts, freshness, embedder,
  FTS flag, schema_version.
- HTTP server (`serve`) pre-warms model resident; endpoints listed in §4.5.
- MCP stdio (`mcp_stdio`) — same tools over JSON-RPC 2.0 stdio protocol
  (initialize / tools/list / tools/call).

### 6.2 `web_server.py` — interactive dashboard (being replaced)
- GET: `/api/ping|health|search|symbols|impact|gaps|memory|graph|stats|config`.
- POST: `/api/sync|analyze|audit|memory/store|memory/recall`.
- WS on port+1 (8081) via `websocket_handler.py`.
- **Bugs found:** `/api/sync` calls `indexer.sync(con, cfg)` (wrong signature);
  `/api/memory/consolidate` + `/api/memory/clear` called by frontend but not implemented;
  frontend action buttons have no handlers; single-threaded HTTP blocks on heavy ops.

### 6.3 `dashboard.py` — mission control (read-only)
- GET `/api/overview|findings|quickwins|routes|models|search|graph|impact`.
- Serves the SAME `dashboard.html` that web_server serves → endpoint mismatch bug.

### 6.4 Embedding service (daemon-resident)
- `GET /embed/health`, `POST /embed`. Client `RemoteEmbedder` (HTTP) used when daemon
  warm; local `LocalEmbedder` fallback; `HashEmbedder` degenerate fallback.

---

## 7. Key contracts the new FastAPI layer must honor

1. **Root threading**: every lib function takes `root=` with `repo_root()` default.
   The web server must pin a single root (server-scoped) and pass it explicitly.
2. **Progress hooks**: `indexer.sync(root, full, do_embed, progress)` where
   `progress(phase, cur, total)` with phases `scan/link/embed` — direct WS fuel.
3. **Write lock**: `sync()` wraps in `WriteLock(root)` — long jobs must run in a
   background worker, never inside an HTTP request handler.
4. **Envelope convention**: reuse `{ok, tool, result, next_ops}` style from server.py
   for job results so the UI can show "suggested next actions".
5. **Freshness**: `meta.last_sync` + `lag_s` + `fresh (<300s)` is the canonical health
   pulse everywhere (doctor, index_status, overview, gapfill.score).
6. **Snapshot gap**: no history table exists — trends require adding `snapshots`.

## 8. Confirmed facts for the requirements doc

- Full command count in registry: **54**; argparse subcommands: **~70**; RPC tools: **20**.
- The "stateful index" contract is feasible: `sync` already reports phases/progress and
  writes `events`; we extend with `snapshots` + a `Job` registry in-process.
- gapfill validation is actionable now: run `gapfill.coverage()` / `.dead()` /
  `.circular()` etc. against this repo and judge output quality (planned as an early
  spike before full UI wiring).
