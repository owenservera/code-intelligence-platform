# CIP Repo Overview (for Web Console redesign)

**Status:** Draft — derived from sequential source review
**Date:** 2026-08-15
**Scope:** Full module inventory and responsibilities, to ground the new web console design.

---

## 1. Repository Layout

```
C:\0-BlackBoxProject-0\index
├── bin/cip(.py)            # Universal wrapper; local lib first, then ~/.cip-global
├── lib/cipkg/              # The entire product (76 .py files)
│   ├── cli.py              # CLI entry: argparse + dispatch (52 handlers surface)
│   ├── command_registry.py # CommandCard metadata for UI rendering (11 categories)
│   ├── command_adapter.py  # Context-aware command adaptation (experimental)
│   ├── intelligent_executor.py  # Execution engine with progress/status
│   ├── web_server.py       # stdlib http.server + hand-rolled WS (to be replaced)
│   ├── dashboard.py        # "Mission Control" read-only HTTP dashboard
│   ├── websocket_handler.py# websockets-based WS server (port 8081)
│   ├── dashboard_state.py  # Reactive state + background StateUpdater thread
│   ├── server.py           # JSON-RPC over HTTP + MCP stdio tool surface
│   ├── stack/              # Framework-specific analyzers (audit, rules, impact, nextjs, prisma, tauri)
│   ├── memory/             # temporal_graph, episodic, consolidation
│   └── static/             # current vanilla-JS dashboard (to be replaced)
├── repo-settings/          # detectors.py (repo-type detection)
├── sync_global/            # global-install sync machinery
├── templates/              # AGENTS.md, config.toml, ontology.json scaffolds
├── tests/                  # pytest suites (terminal_dashboard/, sync-system/)
├── docs/                   # design docs (dev/ = this new series)
├── config.default.toml     # all tunables (index, embed, retrieval, memory, mcp, daemon…)
└── config.v2.default.toml  # v2 interactive/context/adaptation/error-handling/UI config
```

## 2. Runtime Entry Points

| Entry | What it starts |
|---|---|
| `bin/cip` → `cli.main()` | argparse parse → `dispatch_command` → handler |
| `cip serve` | `server.py:serve()` — JSON-RPC over HTTP (POST /rpc, GET /tools) |
| `cip mcp` | `server.py:mcp_stdio()` — MCP stdio protocol |
| `cip daemon start` | `daemon.py:daemon()` — watcher + HTTP, PID/health files |
| `cip dashboard` | `dashboard.py:serve_dashboard()` — read-only mission control (8790) |
| `cip dashboard-web` | `web_server.py:start_web_server()` — interactive WS dashboard (8090) |

## 3. Module Inventory (by responsibility)

### 3.1 Core intelligence
| Module | Role |
|---|---|
| `indexer.py` | scan → parse → link imports → symbol edges → embed pending. `sync()` orchestrator with `progress` callback. |
| `store.py` | SQLite schema + `connect()`, `get/set_meta`. Tables: meta, files, symbols, chunks, file_imports, edges, vectors, events, summaries, commits, commit_files, signals, symbol_calls. |
| `parse.py`, `parsers.py`, `tree_parser.py`, `ast_chunker.py`, `scip_indexer.py` | parsing layers (AST-aware chunking, SCIP). |
| `retrieve.py` | `hybrid_search` (lexical+vector+graph + RRF + rerank), `search`, `find_symbol`, `graph`, `context`, `history`. |
| `embed.py`, `vecstore.py`, `lancedb_store.py`, `rerank.py` | embedding backends + vector stores + reranking. |
| `summarize.py` | repo/dir/file summaries (hash-cached), `map_`, `describe`. |
| `repo_map.py` | hierarchical repo map for token-efficient context. |

### 3.2 Analysis & quality
| Module | Role |
|---|---|
| `analysis.py` | `repo_health_report()` — score, critical issues, debt, hotspots, recommendations. |
| `gapfill.py` | 12 sub-commands: coverage, dead, circular, blame, score, migrations, env, logs, metrics, features, deps, api (+GapFiller class used by `/api/gaps`). |
| `stack/audit.py` | audit rules engine: `audit`, `findings`, `findings_structured`, `quick_wins`, `gate`, `audit_file`, `audit_diff`, `report_markdown`. |
| `stack/rules.py` | ~26 rules (hidden exports/routes/models, DB N+1/missing-index/await/destructive-migration, secrets, env, layer violations, god module, untested-hot, circular, QA rules, Tauri). |
| `stack/impact.py` | `impact`, `impact_structured`, `impact_diff` (blast radius + diff). |
| `stack/nextjs.py` | route inventory (`list_routes`, `index_routes`). |
| `stack/prisma.py` | schema parse, `models_report`, store-contract indexing. |
| `stack/tauri.py` | Tauri command/capability inventory. |
| `stack/common.py` | `ensure(con)` — audit table bootstrap. |
| `stack/custom_rules.py` | custom rule loading from repo config. |
| `verify.py`, `gatekeeper.py`, `error_system.py`, `dependency_checker.py` | verification gate, admission audit, error handling, `deps`. |

### 3.3 Memory & learning
| Module | Role |
|---|---|
| `memory/temporal_graph.py` | `TemporalKnowledgeGraph`, `AgentMemory` (fact DB). |
| `memory/episodic.py` | `EpisodicMemory`, `AgentExperienceLogger`. |
| `memory/consolidation.py` | `MemoryConsolidator` + background daemon. |
| `learning_system.py`, `learning.py`, `suggestion_engine.py`, `predict.py` | pattern learning, suggestions, next-context prediction. |

### 3.4 Tooling / infra
| Module | Role |
|---|---|
| `context_manager.py` | 6 context providers + `ContextBuilder`/`ContextManager`. |
| `router.py` | `route`, `route_for_agent` — intent routing. |
| `gitindex.py` | commit/co-change/hotspots. |
| `runtime_adapters.py` | broken, ingest (vitest/jest/pytest/tsc/generic). |
| `maintain.py` | rebuild. |
| `watcher.py`, `watch.py`, `hooks.py`, `lock.py` | file watching, git hooks, lock. |
| `selftest.py`, `test_embed.py`, `test_gapfill.py` | self-tests. |
| `detect.py`, `init_detector.py` | repo init / type detect. |
| `session.py`, `export.py`, `tsconfig.py`, `interactive*.py`, `async_input.py`, `help_system.py` | sessions, export, TS config, interactive mode. |
| `workflow_engine.py` | workflow execution. |
| `terminal_dashboard.py` | Textual TUI. |
| `base.py` | config load, repo discovery, data dir, hashing. |

## 4. Key Data Facts for the Web Console

- **Durable state** lives in SQLite under `.cip/data/` (schema in `store.py`), plus
  `.cip/memory.db` and `.cip/episodes.db`.
- **Ephemeral state** exists in `dashboard_state.py` (`DashboardState` + `StateUpdater`
  thread polling every 30s: health score, index freshness, git branch, uncommitted count).
- **Embedding** is heavy (torch + sentence-transformers, model `BAAI/bge-small-en-v1.5`,
  384-dim). Config supports backends: `auto | local | service | hashing`. Embedding should
  NOT block HTTP requests; needs progress streaming + background execution.
- **Events** table records every ingestion/action (timeline source for stats viz).
- **Audit findings** persist per-file with severity/rule/status (rich for dashboards).

## 5. Version / Config Anchors

- `lib/cipkg/__init__.py`: `__version__ = "1.0.0"` (README claims v2.0; docs split).
- Config sections that matter for the UI: `index`, `embed`, `retrieval`, `memory`, `mcp`,
  `daemon`, `analysis`, `summary`, `git`, `rerank`, `vector`, `perf`, `maintain`, `audit`,
  `ui`, `interactive`, `context`, `command_adaptation`, `error_handling`, `workflows`, `sync`.

## 6. Gaps / Inconsistencies Found (relevant to design)

- **Fixed (Ph1, 2026-08-16):** `verify-index` now routes to `handle_verify_index_command`
  (runs `maintain.verify(repair=)`). All 20 product subcommands are wired in
  `dispatch_command`; only `dashboard` (legacy TUI) remains pending as a deletion
  target for the new frontend.
- Some CLI handlers are trivial passthroughs (`handle_*`) — the real logic lives in the
  lib modules; the web layer should call the **lib functions directly**, not subprocess `cip`.
- `gapfill.coverage()` is called without args in `analysis.py` (uses cwd root default) —
  cross-check root threading in the API layer.
- No auth anywhere (internal tool).
- Old static frontend: action buttons exist in HTML (`data-action="sync|analyze|audit|gapfill|consolidate|export"`)
  but **no JS handlers wire them** — dashboard buttons are inert.
