# CIP Deep-Intel — Learned from `cip-inntel.md` + Live `.cip` Inspection

**Status:** Consolidation snapshot (anti-compaction) — write as learned; **v2: full log read**
**Source:** `cip-inntel.md` (prior deep-inspection session log, **entire 7179 lines now read**)
+ live queries against `.cip/data/index.db` in this repo
**Date:** 2026-08-15

> Purpose: preserve hard-won intel before context compaction. Used to update
> `05-requirements.md` and drive `07-api-design.md` / `08-migration-plan.md`.

---

## 1. Confirmed Real Bugs (from the deep-inspection log)

### P1 — NameError crashes (dead paths)
| File:Line | Bug | Impact |
|---|---|---|
| `lancedb_store.py:55` | `json` used but never imported | `NameError` whenever `add_embeddings()` runs |
| `retrieval_bridge.py:240,253,263,266` | `con` undefined in `get_symbol_context()`; `graph_data` fetched but never used | `NameError` on symbol-context requests |
| `retrieval_bridge.py` | `tested_by` edge query treats test-file **path** as a symbol `id` (`SELECT path FROM symbols WHERE id=?`) | wrong rows / misses |

### P2/P3 — correctness & robustness
- `retrieve.py:context()` — **caller/callee labels are swapped** ("called by" shows callees, "caller of" shows callers). Real labeling bug.
- `embed.py:get_embedder` — fallback to hashing only catches `ImportError`; with `HF_HUB_OFFLINE=1` and uncached model, `LocalEmbedder` raises non-ImportError → **crashes** instead of hashing fallback. Affects `sync`/`search`.
- `embed.py` auto-start path can block **up to 120 s** inside `search()` via `_ensure_embedded` → `embed_pending` → `get_embedder`. Responsiveness hazard.
- **`analysis.py:50,91,136` — `sn.list_findings(con)` calls a function that does NOT exist on `nextjs`** (grep-verified: only `analysis.py` references it). Every call → `AttributeError` → swallowed by `except Exception`. **Net effect: health-score "quality" component is always 80 and the "security" critical-issues bucket is ALWAYS empty.** Big functional dead path.
- `analysis.py:20` — `test_coverage = gapfill.coverage()` passes **no root** → computes coverage for `cwd` repo, not the `root` arg of `repo_health_report(root=...)`. Inconsistent-repo bug when cwd ≠ root.
- **`stack/audit.py:audit()` — auto-`UPDATE findings SET status='fixed' WHERE id NOT IN (seen)`.** `seen` only holds *current stack-rule* findings. Any other persisted findings (e.g. ESLINT: from `ingest_eslint`, Tauri findings) get **silently marked fixed on the next rules audit** — data-loss bug.
- `stack/custom_rules.py` — **executes arbitrary Python from `.cip/rules.py`** via `importlib`. By design, but a security consideration: running `cip audit` against a malicious repo can execute its code. Flag in docs; do NOT auto-run in the web console without a warning.
- `lancedb_store._init_table` hardcodes `pa.list_(pa.float32(), 384)`; dimension mismatch fails at insert.
- `lancedb_store.delete_by_path` interpolates path into SQL (`path = '{path}'`) — injection/quote risk.
- `ast_chunker.py` — **fully dead code** (grep-verified: `chunk_by_ast`/`chunk_file_ast_aware` never referenced outside the module). Reads `start_line/end_line/parent` keys that parse output never emits (`start`/`end`, no `parent`).
- `stack/prisma.py` — **`_resolve_store_contract` and `index_stack_with_store_contracts` are dead code** (grep-verified, never called). Duplicates `index_stack` logic.
- `build_tested_by` — `O(test_files × symbols)` DB queries (per-test-file chunk SELECT per symbol). Slow on big repos.
- `link_imports(dirty=None)` — per-path DELETE+SELECT loop over all paths; `build_heritage` inserts edges one-by-one (not bulk). Perf debt.
- `lex_search` — FTS5 quoted tokens become **phrase AND** queries; can over-restrict results.
- `_external_search` — `except (TimeoutExpired, json.JSONDecodeError, Exception)` — redundant `Exception` swallows everything.
- `vecstore._knn_sqlite_vec` — `load_extension("vec0")` needs DLL on path (Windows); silently falls back.
- `base._parse_toml_naive` — dead on Python 3.11+ (tomllib always present; this env is 3.14).
- `stack/impact.py` — `ph = ",".join("?" * len(dep))`; safe only because `_dependents` always returns ≥ seed; still an `IN ()` SQLite syntax trap if ever fed empty set.

### Pyflakes hygiene (unused/undefined)
- `lancedb_store.py:8` unused `os`; `learning.py:5-6` unused imports; `predict.py` redefines `retrieve` (6→76→107); `intelligent_executor.py` unused `Callable/datetime/threading` + 4 unused `e`; `interactive_ui.py` 4 unused imports; f-strings missing placeholders in `learning_system.py:536,579,589` and `suggestion_engine.py:417`.

---

## 2. Architecture Deep-Dive (how the systems work)

### 2.1 Indexing pipeline (`indexer.py`, 409 lines)
```
sync(root, full, do_embed, progress)          # wrapped in WriteLock(root)
  └ _sync_body
     1.  scan   — iter_files_smart → mtime fast-path → sha content check → jobs
     1.5 parse  — ProcessPoolExecutor(_parse_worker) [Windows spawn-safe:
                  worker gets (path, lang, source, tier) only, NO db conn]
                  fallback to serial on pool error
     2.  prepare_file → pure dict of rows (worker-safe) → _bulk_write
     3.  deleted → remove_file (vectors/symbol_calls/symbols/chunks/edges/
                  file_imports by path)
     4.  link   — link_imports (file→file "imports")
                  resolve_symbol_edges (symbol→symbol "calls"/"references",
                  import-scope precision gate, 200-cap)
                  build_heritage ("extends"/"implements")
     5.  embed  — embed_pending(con, cfg, batch=64, progress)
     stats = compute_stats + {dirty, deleted, embedded, ms}
     set_meta last_sync; INSERT events(sync, str(stats)); commit
```
- `progress(phase, cur, total)` phases: `scan`, `link`, `embed` → **direct WS fuel for the new UI**.
- `_bulk_write` order: delete (vectors by chunk-id, symbol_calls by sym-id, symbols/chunks/edges/src_path/file_imports by path) → bulk `INSERT OR REPLACE`.
- Edge kinds in use: `contains`, `exports`, `imports`, `calls`, `references`, `tested_by`, `extends`, `implements`.
- `resolve_symbol_edges`: global `name_map` (skips `STOP_NAMES` / name len<4); allowed set = `{file} ∪ imports(file)`.

### 2.2 Storage layer (`store.py`, 229 lines)
- `connect()`: WAL, `synchronous=NORMAL`, `busy_timeout=30000`, `cache_size=-65536` (64MB), `mmap_size=128MB`, `temp_store=MEMORY`, `wal_autocheckpoint=2000`, `foreign_keys=OFF`. Runs `CORE_SCHEMA` (CREATE IF NOT EXISTS → in-place upgrade), FTS probe → `fts` meta, tier-column migration, `_ensure_tokenizer` (tokens column + `chunks_fts2`).
- **Vectors:** BLOB = little-endian `<384f` (1536 bytes for bge-small-en-v1.5). `from_blob`/`to_blob`/`cosine` in `embed.py`.
- `vector_matrix(con, model)` → `(ids, numpy matrix)` cached per-DB keyed by `(model, count, max rowid)` — cross-process safe invalidation. `invalidate_vectors()` on embed.
- `vecstore.knn` = dot product on normalized matrix (or pure-python cosine fallback); `sqlite-vec` path optional.

### 2.3 Config system (`base.py`)
- Merge order (highest→lowest): `.cip/config.toml` → **repo profile** (detectors.detect_repo_type + load_repo_profile; flattens `profile.<name>` nesting, include/exclude→index) → TOML defaults (`config.default.toml` + `config.v2.default.toml`) → hardcoded `DEFAULT_CONFIG`.
- Repo root discovery: walk up until `.cip/` exists; else `SystemExit`.
- `tokenize`: `[^0-9A-Za-z_$]+` split → underscore→space → camelCase split → lower → keep len>1.
- `iter_files` (used by detect) vs `iter_files_smart` (gatekeeper, used by indexer) — indexer uses the smart one.

### 2.4 Gatekeeper (file admission) (`gatekeeper.py`)
- Truth priority: `git ls-files` > parse `.gitignore` > heuristics.
- `classify(rel)` → tier: `skip` (assets/lockfiles), `doc` (md/rst/txt/adoc/readme), `config` (json/yaml/toml/ini/dockerfile/properties + named), `code` (known ext), `pathonly` (unknown).
- `_decide`: explicit include/exclude → git-tracking → binary → classify → oversize>max_file_kb→pathonly → generated → minified → pathonly.
- `iter_files_smart` yields `(rel, tier, why)`; `admission_report()` + `explain(rel)` power the `admission` command (trust/transparency).
- `chunk_markdown`: markdown chunked at `#`-headings, cap 50 chunks, 8000-char trunc.

### 2.5 Parsing (`parse.py` → `tree_parser.py`)
- `parse_file` prefers **tree-sitter** (TS/TSX/JS/Python w/ real call edges), falls back to **regex** RULES per language + GENERIC.
- `tree_parser`: lazy `_LANGS` cache built from `tree_sitter_typescript` (TS + TSX), `tree_sitter_javascript`, `tree_sitter_python`; all optional try/except → `available(lang)` gates; `Parser.set_language` fallback for older API.
  - `DEF_NODES`: class_declaration→class, function_declaration→function, method_definition→method, interface_declaration→interface, type_alias_declaration→type, enum_declaration→class, python class_definition/function_definition.
  - `emit()` slices bytes via `start_point/end_point` (0-indexed +1 → 1-based), byte-slicing `src_bytes[...]` for Unicode safety; `exported(node)` walks parents for `export_statement`.
  - `capture_call()` records `(func_qual, callee)` pairs from `call_expression` nodes — **`calls` list only produced by tree-sitter; regex fallback has no call edges**. These become `symbol_calls` / `calls` edges downstream.
  - Variable decls (`lexical_declaration`/`variable_declaration`) become functions when value is arrow/function-expression.
- **Regex fallback** (`parse.py`, 145 lines): per-lang `RULES` (python: class/def; typescript/js: class/interface/type/enum/function/arrow-const/method; rust: struct/enum/trait/fn; go: type/struct/interface/func; java/csharp: class/method); `GENERIC` for unknown; `STOPWORDS`; `_end_indent` (python) / `_end_braces` (brace count, ignores strings/comments) block end detection.
  - `IMPORT_PATS` per lang → `extract_imports` (python from/import, ts from/import()/require, go quoted, rust mod).
  - Methods nested in classes get `Class.method` qualname + kind→method.
- Symbol id grammar: `<lang>://<path>#<Qualified.name>` (e.g. `python://lib/cipkg/analysis.py#repo_health_report`); chunks: `<path>#L<start>-L<end>`.
- Chunks: one per symbol; if no symbols, file header (first ≤60 lines); `signature` = first line [:240]; `exported` from `export`/`pub ` prefix (regex) or AST parent walk (tree-sitter).

### 2.7 Analysis (`analysis.py`, 290 lines)
- `repo_health_report(root)` → `{overall_score, critical_issues, high_priority, test_coverage, technical_debt, hotspots, recommendations}`.
- `_calculate_health_score`: weighted `coverage 0.3 + quality 0.3 + freshness 0.2 + complexity 0.2`. Freshness via `maintain.verify`. **Quality bucket broken (see §1 `list_findings`).**
- `_list_critical_issues`: untested_hot (kind function/method/class, no tested_by edge, dependents > 5, top 5) + security findings (dead path).
- `_list_high_priority`: complexity (function/method > 100 lines, top 5) + duplication findings (dead path).
- `_inventory_technical_debt`: test_debt (untested, dependents > 2, top 10) + complexity_debt (> 50 lines, top 10).
- `_identify_hotspots`: dense (top-10 files by symbol count) + load_bearing (top-10 symbols by dependents).
- `_generate_recommendations`: mapped from critical/high-priority/debt with priority + impact + effort tags.

### 2.8 Gapfill (`gapfill.py`, 501 lines) — the "mining the index" layer
All commands answer pressure-test scenarios by mining stored chunks/FTS/edges/git — **no re-parse required**.
| fn | What it returns |
|---|---|
| `coverage` | coverage_files (paths w/ coverage/istanbul/nyc/lcov), framework_signals (jest/vitest/pytest/.test./describe…), actual_coverage via tested_by edges (total/tested/pct), untested_load_bearing (deps>3; critical if >10) |
| `dead` | symbols with zero inbound edges, confidence high/low (filtered: exported / test paths / entry names main/init/setup/configure/run) |
| `circular` | Tarjan SCC over calls/imports/references edges → cycles + count |
| `blame` | `git blame --line-porcelain` → top_authors, commits_touched, raw_lines |
| `score` | heuristic 0–100: freshness (<300s lag, −15), vector coverage <80% (−≤20), dead-symbol ratio (−≤15), critical findings (−≤30) |
| `migrations` | migration/seed file inventory + schema_signals (CREATE/ALTER/DROP/prisma…) + per-file version/rollback/breaking/tables |
| `env` | `process.env.X` / `import.meta.env.X` / `os.environ['X']` variable inventory by count |
| `logs` | logging pattern counts (console.*, logger., winston, pino, morgan, "level":) + distinct log files |
| `metrics` | observability signals (counter/gauge/histogram/prometheus/datadog/otel/sentry/trace/span) |
| `features` | feature-flag signals (featureFlag/isEnabled/toggle/launchDarkly/unleash/experiment/killSwitch) + sample locations |
| `deps` | manifest presence (package.json/pyproject/requirements/go.mod/Cargo/composer/Gemfile) + import_edge_count + most_imported top-20 |
| `api` | routes via `nextjs.list_routes` + contract_signals + per-handler endpoints (methods detected from app.get/post/put/delete/patch) + handlers |
- Helpers: `_con`, `_pattern_count` (LIKE over chunks), `_pattern_paths`, `_pattern_count_in_file`, `_search` → `retrieve.search`.

### 2.9 Stack pack (`stack/` — per-stack analyzers, tables auto-ensured)
- `common.ensure(con)`: lazily creates **findings / routes / models / model_usage / tauri_commands / tauri_capabilities** — no core `store.py` edits. Any consumer (analysis, audit, impact) must `ensure()`.
- **impact.py**: blast radius — seed by file path or symbol id/name; BFS `_dependents` (depth capped 1–3) over `imports/calls/references` edges (dst may be file path or symbol id; `_to_file` maps `://` ids); tests = tested_by dsts whose src path ∈ dep; routes_hit from `routes WHERE file IN (dep)`; findings count; hotspot heat via `gitindex.hotspots`; risk low/medium/high + advice. `impact_structured` = todo-friendly format. `impact_diff(ref=HEAD)` = union over `git diff --name-only` files (cap 20).
- **nextjs.py**: `index_routes` (route.ts/js→api, page.*→page, layout.*→layout, `/pages/api/`→api; methods regex `export (async) (function|const) (GET|POST|…)`; client boundary `"use client"`; App-Router path = dir minus `app/` + route-groups `(x)`; Pages path from `pages/`). `list_routes` lazy-indexes if table empty, adds `referenced` heuristic (string probe in chunks).
- **prisma.py**: `parse_schema` (models, fields w/ @id/@unique, @@index blocks); `index_stack` (models + `model_usage` from `prisma.X.op(` call sites resolved to enclosing symbol); `where_fields` (keys inside `where:` blocks − AND/OR/NOT); `models_report` (per-model ops breakdown, files_using, `orphan` flag). **`_resolve_store_contract` + `index_stack_with_store_contracts` = dead code.**
- **audit.py**: `_fid` = sha1(`rule:path:line:title`)[:16] stable IDs; `audit(root, refresh=True)` → nextjs.index_routes + prisma.index_stack (on refresh) → `rules.run_rules` → upsert findings → **`status='fixed'` for open findings not in seen (data-loss bug, §1)** → summarize `{open, by_severity, critical, high}`. `findings` query w/ severity-order; `findings_structured` machine-actionable `{file,line,rule_id,message,suggested_pattern,severity,effort}`; `quick_wins` (open, suggestion present, severity high+, effort trivial/small); `ingest_eslint` (JSON via stdin/file → `ESLINT:<ruleId>` findings); `report_markdown`; `gate` (sync → audit → `runtime_adapters.broken()` count; exit non-zero on criticals/broken).
- **custom_rules.py**: loads `.cip/rules.py` exporting `CUSTOM_RULES = [(id, fn)]`, merged via `get_all_rules` → `RULES + custom`. **Executes repo code (§1 security note).**
- **tauri.py**: `#![tauri::command]` fn inventory + capabilities `"allow":[{... "cmd":...}]`; `index_stack` persists to tauri_commands/tauri_capabilities; `commands_report` = commands + gated/ungated counts.

### 2.6 Retrieval (`retrieve.py`, 400 lines)
- `search()`: optional external tool defer (`_external_search` subprocess) → `_ensure_embedded` (auto-embed) → `lex_search` (chunks_fts2 tokens → chunks_fts → LIKE fallback) + `vec_search` (knn) → `rrf` fusion (k=60) → `rerank` → top-k.
- Result dict: `{chunk, path, lines:[s,e], symbol, score, matched:[fts|vec], snippet(≤360), tier}`.
- `graph(sid, direction, depth≤3)` cap 200 nodes / 400 edges. `find_symbol` = exact NOCASE → LIKE. `context()` builds budgeted sections (search hits / symbol source / summaries / signals / tests / callers-callees / siblings / header).
- `vecstore.knn` (37 lines): `backend="sqlite-vec"` attempt → numpy dot on normalized `vector_matrix` (cosine = dot) → pure-python cosine fallback; sqlite-vec score = `1/(1+distance)`.

### 2.10 Misc verified behaviors
- `base.load_config` merge confirmed line-by-line (see §2.3); `iter_files` (detect/deps use) vs `iter_files_smart` (indexer/analysis use) — both `os.scandir`-based, cached dir-entry sizes.
- `gatekeeper` decision order (`_decide`): explicit include → explicit exclude → git-tracked truth (untracked admitted only if `_looks_new_source` = valid-lang + not generated) → gitignore fallback → binary → classify → oversize (>max_file_kb → pathonly) → generated code → minified → index. `admission_report` returns `{mode, index_tiers, skipped, examples}`.
- `detect(root, cfg)` → `{languages, primary, stacks, multi_roots}`; multi-root = top-level dirs with own package.json/Cargo.toml/go.mod.

---

## 3. Live `.cip` Output Structure (this repo = indexed repo)

### 3.1 `.cip/` layout
```
.cip/
  data/index.db          16 MB, WAL mode
  data/daemon.{lock,port,log}   (when daemon running)
  data/context/  data/learning_data/{actions,models,patterns,profiles}/
  data/workflow_states/  data/write.lock
  memory.db   episodes.db
```
- **No** `.cip/config.toml` / `.cip/ontology.json` here — repo config lives at repo root.

### 3.2 Live index DB — tables & counts
| Table | Rows | Purpose |
|---|---|---|
| meta | 5 | schema_version=4, fts=1, tok_built=1, embedder_name=`local:BAAI/bge-small-en-v1.5`, last_sync |
| files | 225 | path, language, size, lines, hash, mtime, indexed_at, **tier** (code/doc/config/pathonly) |
| symbols | 1436 | id, name, kind, path, start/end_line, signature, body_hash, body |
| chunks | 2566 | id, path, symbol_id, start/end_line, text, text_hash, **tokens** |
| edges | 4312 | src, dst, kind, src_path (kinds: contains/exports/imports/calls/…) |
| vectors | 2566 | id, model, vec(1536B blob = 384 floats) |
| file_imports | — | path, spec |
| events | 1 | ts, kind, payload (last sync JSON) |
| summaries/commits/commit_files/signals/symbol_calls | 0 | empty until used |

- Last sync event payload: `{files:225, symbols:1436, chunks:2566, edges:4312, vectors:2566, dirty:225, deleted:0, embedded:2566, ms:1077484}` — full index + embed took **~18 min** on this repo.
- **Implication for web console:** full sync is a *long* job; MUST run in background worker with progress streaming + job state. Never in-request.

### 3.3 Schema delta vs `store.py`
Live DB matches `CORE_SCHEMA` + `FTS_SCHEMA` + `FTS2_SCHEMA` + tier column + tokens column (all migrations applied). `tokens` column + `chunks_fts2` confirmed present.

---

## 4. Daemon, Embedding, CLI, Server

### 4.1 Daemon (`daemon.py`, 152 lines)
- Files: `.cip/data/daemon.lock` (pid), `daemon.port`, `daemon.log`; `daemon_status` → `{pid, port, alive, warm, health}` via `GET /embed/health`.
- `daemon(port=8787)` → watcher thread (`watch`) + `serve()`; Windows stop = `taskkill /F /T`.

### 4.2 Embedding engine (`embed.py`, 245 lines)
- Resolution: warm daemon `RemoteEmbedder` (HTTP, `service:` prefix) → auto-start daemon (120 s wait) → `HashingEmbedder` (offline) → `LocalEmbedder` (sentence-transformers, `local:` prefix). Never auto-starts by default in `get_embedder`; `get_embedder_with_feedback` prints path taken.
- Server endpoints: `GET /embed/health` → `{warm, model, dim, pid, uptime_s}`; `POST /embed` → `{vectors, model, dim, n}`.

### 4.3 HTTP/JSON-RPC server (`server.py`, 254 lines)
- 20 `TOOLS`; `call_tool(root, cfg, name, args)` → direct lib dispatch, envelope `{ok, tool, result, next_ops, index_stats}`; `_next_ops` suggests follow-ups (agent-native chaining).
- `index_status(root)` → stats + freshness + embedder + schema_version.
- `serve()` pre-warms model resident; endpoints: `GET /health /tools /ontology.json /embed/health`, `POST /embed`, `POST /rpc` (`tools.list`, `index.status`, else `call_tool`). MCP stdio shares the same tool set.

### 4.4 CLI (`cli.py`, 652 lines)
- `build_parser` (~70 subcommands) catalogued in `03-cli-and-registry.md`; **54 registered commands** (registry) across 11 categories; `dispatch_command` handles only a subset — gapfill/refactors/routes/models/gate/admission/embedder/embed-ping/watch hit "unknown command" → **web layer must call lib directly** (like `call_tool`), never subprocess `cip`.

---

## 5. Key Files Referenced
- `cip-inntel.md` — prior deep-inspection transcript (bugs, file-by-file analysis; fully read to line 7179)
- `lib/cipkg/{indexer,store,retrieve,embed,parse,parsers,tree_parser,ast_chunker,gatekeeper,detect,analysis,gapfill,base,vecstore,lancedb_store,retrieval_bridge,daemon,server,maintain}.py`
- `lib/cipkg/stack/{common,impact,nextjs,prisma,audit,custom_rules,tauri}.py`
- `docs/dev/{00-goals-and-decisions,01-repo-overview,02-web-layer-current,03-cli-and-registry,04-data-and-state,05-requirements,06-system-log}.md`

## 6. Confidence / Verification Notes
- `list_findings` grep: **only** `analysis.py:50,91,136` reference it; `nextjs.py` defines `index_routes/route_referenced/list_routes` only → confirmed AttributeError dead path.
- `ast_chunker` / `_resolve_store_contract` / `index_stack_with_store_contracts` grep: referenced only within their own modules → confirmed dead code.
- `lancedb_store` grep: only `dependency_checker.py` (optional dep) + its own `migrate_sqlite_to_lancedb` → opt-in path, not default.
- `retrieval_bridge` exposes `search_and_format` / `get_impact_context` / `get_symbol_context` (the `con` NameError lives in the latter).
