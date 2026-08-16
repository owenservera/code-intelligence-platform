# CIP Web Console — Bugs & Issues Log (living document)

**Status:** LIVE — maintained continuously during the frontend design session.
**Purpose:** Single tracked list of every bug/issue found during discovery and design.
Every entry records evidence, impact, and owner-facing consequence so decisions in
`05-requirements.md` / `07-api-design.md` reflect reality (not assumptions).
**Last updated:** 2026-08-16 (F-34..F-41 appended by Agent 2)

---

## Legend
- **ID:** sequential. **Severity:** P0 (blocks/broken) · P1 (crash/wrong data) · P2 (bug, workaround exists) · P3 (perf/robustness/hygiene) · P4 (design/UX issue).
- **Area:** index | retrieve | audit | analysis | gapfill | memory | daemon | embed | web | config | stack | learning | workflow | tests | misc.
- **Status:** open | triaged | fix-in-bridge | fixed | wontfix | deferred.
- **Affects UI:** the user-facing consequence in the new console (drives requirements).

---

## 1. Confirmed from deep inspection (`07-intel-deep-inspection.md`)

### BUG-001 — `web_server.py` sync signature mismatch → 500
- **Severity:** P1 · **Area:** web · **Status:** fix-in-bridge
- **Evidence:** `web_server._api_sync` calls `indexer.sync(con, cfg)`; real signature `sync(root=None, full=False, do_embed=True, progress=None)`.
- **Affects UI:** Any sync button wired to old `/api/sync` returns 500. The new bridge must call `indexer.sync(root, full, do_embed, progress)` — never `(con, cfg)`.

### BUG-002 — `/api/memory/consolidate` + `/api/memory/clear` not implemented
- **Severity:** P1 · **Area:** web · **Status:** fix-in-bridge
- **Evidence:** Frontend `memory.js` POSTs these; no routes in `web_server.py`. Dead buttons.
- **Affects UI:** Memory lab must map to real lib calls (`memory/consolidation.run`, `AgentMemory.clear` if exists) or drop the buttons.

### BUG-003 — Dashboard action buttons inert (sync/analyze/audit/gapfill/consolidate/export)
- **Severity:** P2 · **Area:** web · **Status:** wontfix (surface being replaced)
- **Evidence:** `data-action` attributes present in `dashboard.html`; no JS handlers.
- **Affects UI:** n/a — new console rebuilds this from scratch; requirement = "no dead buttons."

### BUG-004 — Split-brain dashboards: `web_server.py` (8090) + `dashboard.py` (8790) serve same HTML with incompatible API paths
- **Severity:** P1 · **Area:** web · **Status:** fix-in-bridge (single server)
- **Evidence:** dashboard.py `/api/overview|findings|quickwins|routes|models`; web_server `/api/stats|health|graph|gaps|memory|config`. One HTML, two contracts.
- **Affects UI:** Acceptance = remove both; one FastAPI server owns the page + API.

### BUG-005 — `lancedb_store.py:55` NameError (`json` never imported)
- **Severity:** P1 · **Area:** index · **Status:** open
- **Evidence:** `add_embeddings()` uses `json` without import.
- **Affects UI:** Only if vector backend = lancedb (not default; grep shows it's opt-in via `dependency_checker`/`migrate_sqlite_to_lancedb`). Not in v1 console path — still log it.

### BUG-006 — `retrieval_bridge.get_symbol_context` NameError (`con` undefined) + `graph_data` unused
- **Severity:** P1 · **Area:** retrieve · **Status:** open
- **Evidence:** Lines 240,253,263,266 reference `con` that is never defined; `graph_data` fetched and discarded.
- **Affects UI:** If the console reuses `retrieval_bridge` for symbol context, it crashes. Prefer `retrieve.context()` (works) or fix the bridge.

### BUG-007 — `retrieval_bridge` tested_by edge treats test-file path as symbol id
- **Severity:** P2 · **Area:** retrieve · **Status:** open
- **Evidence:** `SELECT path FROM symbols WHERE id=?` with a test-file path.
- **Affects UI:** Wrong/missing test links in deep-file panel if surfaced via bridge.

### BUG-008 — `retrieve.context()` caller/callee labels swapped
- **Severity:** P2 · **Area:** retrieve · **Status:** open
- **Evidence:** "called by" shows callees; "caller of" shows callers.
- **Affects UI:** Deep-file panel relationship labels would be inverted. Requirement: fix labeling in lib or present graph edges with correct direction at render time.

### BUG-009 — `embed.get_embedder` hashing fallback only catches ImportError
- **Severity:** P2 · **Area:** embed · **Status:** open
- **Evidence:** `HF_HUB_OFFLINE=1` + uncached model → `LocalEmbedder` raises non-ImportError → crash instead of hashing fallback. Affects `sync`/`search`.
- **Affects UI:** A sync/embed job can die with no graceful fallback. Requirement: job error state must show traceback; consider widening except.

### BUG-010 — `embed` auto-start can block up to 120s inside a request path
- **Severity:** P3 · **Area:** embed · **Status:** open
- **Evidence:** `_ensure_embedded` → `embed_pending` → `get_embedder` → daemon auto-start 120s wait.
- **Affects UI:** First search after index-add can hang 120s. Requirement: run embed in background job + surface "embedding…" status; never inline.

### BUG-011 — `ast_chunker.py` fully dead code
- **Severity:** P3 · **Area:** index · **Status:** wontfix (remove or ignore)
- **Evidence:** Grep: `chunk_by_ast`/`chunk_file_ast_aware` unreferenced; reads `start_line/end_line/parent` keys parse never emits.
- **Affects UI:** Config `index.ast_aware_chunking` is misleading — it is NOT in the active parse path. Flag in config viewer (don't let users toggle a no-op).

### BUG-012 — `stack/prisma._resolve_store_contract` + `index_stack_with_store_contracts` dead code
- **Severity:** P3 · **Area:** stack · **Status:** open
- **Evidence:** Grep: never called; duplicates `index_stack`.
- **Affects UI:** Prisma store-contract analysis promised in docs doesn't run. Decide whether to wire or document as unimplemented.

### BUG-013 — `analysis._calculate_health_score` calls nonexistent `nextjs.list_findings` → quality always 80, security bucket always empty
- **Severity:** P1 · **Area:** analysis · **Status:** open
- **Evidence:** Grep: `list_findings` referenced only in analysis.py:50,91,136; `nextjs` defines `index_routes/route_referenced/list_routes` only → AttributeError swallowed.
- **Affects UI:** **Critical for dashboards.** Health gauge quality-component is a constant 80; "security critical issues" never populate. Requirement: decide fix (real audit-severity counts) vs switch to `gapfill.score()`.

### BUG-014 — `analysis.repo_health_report` calls `gapfill.coverage()` without root → wrong-repo coverage when cwd≠root
- **Severity:** P2 · **Area:** analysis · **Status:** open
- **Evidence:** `test_coverage = gapfill.coverage()` at line 20 (no root); `gapfill.coverage(root=None)` → `repo_root()` from cwd.
- **Affects UI:** Health report can mix two repos' data. Requirement: web layer pins one root and passes it to EVERY lib call.

### BUG-015 — `stack/audit.audit()` auto-marks non-stack findings as 'fixed'
- **Severity:** P1 · **Area:** audit · **Status:** open
- **Evidence:** `UPDATE findings SET status='fixed' WHERE status='open' AND id NOT IN (seen)` — `seen` only contains current stack-rule findings; ESLINT:/tauri/custom findings get silently closed on next rules audit.
- **Affects UI:** **Findings explorer data loss.** D2 opened-vs-fixed trend and FR-7 explorer would show misleading "fixed." Requirement: fix the query (only close findings whose rule was actually run) before wiring trends.

### BUG-016 — `stack/custom_rules` executes arbitrary Python from `.cip/rules.py`
- **Severity:** P2 (security note) · **Area:** audit · **Status:** triaged
- **Evidence:** `importlib.util.spec_from_file_location` + `exec_module`.
- **Affects UI:** Localhost tool, low real risk, but a malicious repo audited from the console would execute its code. Requirement: show "custom rules active" indicator; do not auto-run audit against an untrusted path without a warning toggle.

### BUG-017 — `base._parse_toml_naive` dead on Python ≥3.11
- **Severity:** P3 · **Area:** config · **Status:** wontfix
- **Evidence:** tomllib always present on 3.11+/3.14; naive parser unreachable.
- **Affects UI:** n/a. But confirms `/api/config` should use `load_config` (tomllib path) — canonical, source-annotated effective config.

### BUG-018 — Perf: `build_tested_by` O(test_files × symbols); `build_heritage` row-by-row inserts; `link_imports(dirty=None)` per-path loop; `dead`/`score` per-symbol scalar subqueries
- **Severity:** P3 · **Area:** index/gapfill · **Status:** open
- **Evidence:** 07-intel §1 + gapfill source.
- **Affects UI:** Full sync on this repo took ~18 min (2,566 vectors). Incremental is fast; full sync must be opt-in background job with progress + ETA. Batch those queries when we touch indexer.

### BUG-019 — `vecstore._knn_sqlite_vec` `load_extension("vec0")` needs DLL on Windows path; silently falls back
- **Severity:** P3 · **Area:** retrieve · **Status:** open
- **Evidence:** vecstore.py:31-32; config `[vector] backend=sqlite-vec` only.
- **Affects UI:** If user selects sqlite-vec backend in settings, it silently uses numpy. Show effective backend in embedding panel.

### BUG-020 — `stack/impact.py` `IN ({ph})` trap when dep empty (currently safe because seed ≥1)
- **Severity:** P3 · **Area:** stack · **Status:** open
- **Evidence:** `ph = ",".join("?" * len(dep))`; SQLite `IN ()` syntax error if ever empty.
- **Affects UI:** Impact panel robustness; guard in bridge.

### BUG-021 — `lex_search` FTS5 quoted phrases → phrase-AND; may over-restrict
- **Severity:** P3 · **Area:** retrieve · **Status:** open
- **Evidence:** 07-intel §1.
- **Affects UI:** Search results quality; lower priority.

### BUG-022 — `_external_search` redundant `except (…, Exception)` swallows everything
- **Severity:** P3 · **Area:** retrieve · **Status:** open
- **Evidence:** 07-intel §1.
- **Affects UI:** n/a (optional external search path).

### BUG-023 — config `[meta] schema_version` (default says 11) vs live DB schema_version = 4
- **Severity:** P3 · **Area:** config · **Status:** open
- **Evidence:** Live `.cip/data/index.db` meta `schema_version=4`; `config.default.toml`/docs claim 11.
- **Affects UI:** `/api/config` and "doctor" displays must show the LIVE DB version, not the default; flag drift in settings view.

### BUG-024 — `index.ast_aware_chunking` config is a no-op (parse path never calls `ast_chunker`)
- **Severity:** P3 · **Area:** config · **Status:** triaged (see BUG-011)
- **Evidence:** grep: `ast_chunker` unreferenced outside itself.
- **Affects UI:** Config editor must not present this as functional. Show "currently inactive in the active parse path."

### BUG-025 — Old frontend claim: "memory.js" + 8 hand-rolled modules, no build step
- **Severity:** P4 · **Area:** web · **Status:** wontfix
- **Evidence:** 02-web-layer-current §6.
- **Affects UI:** n/a — replaced by React SPA.

---

## 2. Issues that will emerge during THIS design session (track here)

### ISSUE-101 — Health metric source of truth (BUG-013/BUG-014)
- **Open question:** single `gapfill.score()` (heuristic) vs fixed `analysis.repo_health_report()` vs both with reconciliation.
- **Decision needed from interview §A.**

### ISSUE-102 — Findings trend integrity (BUG-015)
- **Decision needed:** fix audit() close-query before D2 chart, or exclude auto-closed history.

### ISSUE-103 — Root threading discipline (BUG-014)
- **Decision:** bridge layer pins one `root`; every lib call gets explicit `root=`. Adopt as hard rule in API design.

### ISSUE-104 — Embed/long-job UX (BUG-009/010/018)
- **Decision:** background job + progress + ETA + job crash traceback + embedder-resolution indicator (local/daemon/hashing/warm).

### ISSUE-105 — Gapfill validation output quality
- **Open:** run the 12 gapfill commands against this repo, judge, gate low-value ones. (12 outputs catalogued in 07-intel §2.8.)

### ISSUE-106 — Stack tables lazy `ensure()` vs explicit prepare
- **Open:** findings/routes/models/model_usage/tauri tables created by `stack.common.ensure()`. Stats dashboards depend on them; decide auto-ensure on read vs explicit "prepare stack" job.

### ISSUE-107 — Snapshot table contract (trends)
- **Open:** what granularity (sync/audit/consolidate), retention, schema; written off the hot path.

### ISSUE-108 — 3D graph data contract
- **Open:** node/edge payload cap, expansion endpoint (`/api/graph/focus`), which edge kinds carry visual indicators, kind→icon map, severity→color map.

### ISSUE-109 — Custom-rules + ingest data loss (BUG-015/016 interplay)
- **Open:** tag external findings (ESLINT:, custom, tauri) so audit never closes them; show source badge.

### ISSUE-110 — Daemon/embed status panel data
- **Open:** `daemon_status` + `GET /embed/health` → live {pid,port,warm,model,dim,uptime_s}; log tail needs new helper (daemon.log append-only).

---

## 3. Triage workflow (how we use this doc)
1. Every new discovery during design → append entry with evidence.
2. Each interview answer → update decision fields on ISSUE-10x.
3. Before coding: all `open` P1s referenced by a requirement are either fixed-in-bridge or explicitly deferred.
4. Keep `05-requirements.md` / `07-api-design.md` consistent with this log's statuses.

---

## 4. Spec-driven finds (fresh web build — grounded in CIP core, not legacy web)

New finds from per-requirement specs in `docs/dev/specs/`. Prefix `CORE-`; each cross-references
its spec. These are core `lib/cipkg` behaviors the fresh build must design around.

### CORE-1 — `base.repo_root()` raises `SystemExit` on no-`.cip/` (SPEC-01)
- **Severity:** P2 · **Area:** config/web · **Status:** fix-in-bridge
- **Evidence:** `base.py:72` `raise SystemExit("cip: no .cip/ found here or above…")`.
- **Affects UI:** Shell must never crash on un-activated path. Need soft variant
  (`find_repo_root_or_none`) for the FR-12 onboarding/activation flow.

### CORE-2 — No `[web]` config section / port anchor (SPEC-01)
- **Severity:** P3 · **Area:** config · **Status:** open
- **Evidence:** `config.default.toml` has `[mcp] port=8080` (:122-123) and `[daemon] port=8765`
  (:134-137) only; nothing anchors the console's port 8090 (FR-1/NFR-1).
- **Affects UI:** Add `[web] host=localhost, port=8090, auto_manage_daemon` to defaults; merged
  by existing `load_config` (no loader change).

### CORE-3 — Status payload runs 5+ full-table COUNTs per call (SPEC-01)
- **Severity:** P3 · **Area:** index/web · **Status:** open
- **Evidence:** `indexer.py:286-288` `compute_stats` COUNTs files/symbols/chunks/edges/vectors;
  `server.py:52` `index_status` adds commits/signals/summaries COUNTs — uncached.
- **Affects UI:** NFR-3 (<300 ms reads) at risk on large repos. Needs snapshot-cached stats
  with invalidation on sync/embed (linkage: ISSUE-107, SPEC-14).

### CORE-4 — `base.load_config` mutates `sys.path` + imports `repo-settings` at call time (SPEC-01)
- **Severity:** P3 · **Area:** config · **Status:** open
- **Evidence:** `base.py:116-124` inserts repo-settings dir into `sys.path` and imports
  `detectors` per call.
- **Affects UI:** Process-wide side effect; safe only under single-root discipline
  (§7.3 ISSUE-103). Call once at server startup, not per request.

### CORE-5 — 14 registry handlers import nonexistent CLI functions (SPEC-02)
- **Severity:** P1 · **Area:** command center · **Status:** fix-in-bridge
- **Evidence:** Live audit of all 55 `CommandCard.handler` targets: `gate, refactors, dead,
  circular, deps, coverage, migrations, env, logs, metrics, features, api, blame, predict`
  all `from .cli import handle_*` a function that does NOT exist in `cli.py` → handler always
  returns `{'error': ...}`.
- **Affects UI:** Routing the command center through `card.handler` would make these 14
  commands permanently broken. Bridge must own dispatch (extended `call_tool` table).

### CORE-6 — Registry handlers swallow all exceptions into error dicts (SPEC-02)
- **Severity:** P2 · **Area:** command center · **Status:** fix-in-bridge
- **Evidence:** `command_registry.py:899` pattern `except Exception as e: return {'error': …}`.
- **Affects UI:** Violates NFR-5 (traceback visibility). Bridge must surface real tracebacks.

### CORE-7 — CLI handlers `_out()`-print and return `None`; structured result lost (SPEC-02)
- **Severity:** P2 · **Area:** command center · **Status:** fix-in-bridge
- **Evidence:** `cli.py:14-15` `_out(obj)` prints `json.dumps`; handlers like
  `handle_analyze_command(root)` (`cli.py:71`) return `None`.
- **Affects UI:** Command results would be lost if routed through CLI handlers. Bridge calls lib
  directly and serializes results.

### CORE-8 — `CommandParameter` metadata incomplete vs argparse (SPEC-02)
- **Severity:** P2 · **Area:** command center · **Status:** open
- **Evidence:** Cards omit flags like `--host`, `--refresh`, `--structured`; `cli.py` argparse is
  the true authority.
- **Affects UI:** Auto-forms would silently drop real parameters. Param-schema merger (registry ⊕
  argparse) is mandatory.

### CORE-9 — No 1:1 command↔lib mapping exists anywhere (SPEC-02)
- **Severity:** P2 · **Area:** command center · **Status:** open
- **Evidence:** `server.py:call_tool` covers only 20 RPC tools; the other 35 registry commands
  have no direct-lib mapping.
- **Affects UI:** "Every command executable" is unverifiable until `web_bridge.command_table`
  covers all 55 with non-stub callables.

### CORE-10 — Daemon port mismatch: config 8765 vs code 8787 (SPEC-03)
- **Severity:** P2 · **Area:** daemon/config · **Status:** open
- **Evidence:** `config.default.toml:137` `port = 8765`; `daemon.py:123` `port or 8787`;
  `command_registry.py:206` default 8787.
- **Affects UI:** Daemon panel would show a port disagreeing with code defaults. Pick one truth
  and surface the effective port.

### CORE-11 — No queue-depth or latency telemetry in embed health (SPEC-03)
- **Severity:** P2 · **Area:** embed · **Status:** open
- **Evidence:** `embed.py:44` `service_health` returns only `{warm,model,dim,pid,uptime_s}`.
- **Affects UI:** FR-3 "queue depth, last latency" have no data source; measure ping latency
  client-side or extend `/embed/health`.

### CORE-12 — `daemon()` and `watch()` are blocking/infinite loops (SPEC-03)
- **Severity:** P1 · **Area:** daemon · **Status:** fix-in-bridge
- **Evidence:** `daemon.py:121` runs `serve()` forever; `watch.py:14` is `while True`.
- **Affects UI:** In-process start would block the FastAPI event loop. Need non-blocking
  spawn wrapper; daemon in its own thread/subprocess.

### CORE-13 — `daemon_stop` Windows path uses `taskkill /F /T` (process-tree kill) (SPEC-03)
- **Severity:** P1 · **Area:** daemon · **Status:** fix-in-bridge
- **Evidence:** `daemon.py:73-78`.
- **Affects UI:** If the console ever hosts the daemon in-process, Stop kills the console.
  Web-managed daemon must be a separate subprocess.

### CORE-14 — No structured daemon log; `watch` prints free text (SPEC-03)
- **Severity:** P3 · **Area:** daemon · **Status:** open
- **Evidence:** `watch.py:29` `print(f"cip: synced +{dirty} …")` teed into `daemon.log`.
- **Affects UI:** Log tail is human-readable only; don't parse into events; add structured
  lines if activity feed needs daemon events.

### CORE-15 — `maintain.verify` rehashes every file; `rebuild` deletes DB files (SPEC-04)
- **Severity:** P2 · **Area:** index · **Status:** fix-in-bridge
- **Evidence:** `maintain.py:16-37` full read+sha per file; `maintain.py:5-14` removes `index.db*`.
- **Affects UI:** Both must be background jobs with progress + confirm; verify can be slow.

### CORE-16 — `watch.watch` is infinite, no stop, stdout-only logging (SPEC-04)
- **Severity:** P2 · **Area:** index · **Status:** fix-in-bridge
- **Evidence:** `watch.py:14-34` `while True` + `print`.
- **Affects UI:** Need WatchManager thread with stop flag + WS event emission.

### CORE-17 — `vacuum` prunes `events` by `[maintain].event_days`=30 — conflicts with full snapshot history (SPEC-04)
- **Severity:** P2 · **Area:** index · **Status:** open
- **Evidence:** `maintain.py:42-45`; ISSUE-107 requires indefinite snapshot retention (§7.1-8).
- **Affects UI:** Snapshot rows must be exempt from the events sweep or stored separately.

### CORE-18 — `embedded` stats key ambiguity (count vs total vectors) (SPEC-04)
- **Severity:** P3 · **Area:** index · **Status:** open
- **Evidence:** `indexer.py:397` `embedded=n_emb` from `embed_pending` return.
- **Affects UI:** Chart units must be labeled; confirm before rendering embed charts.

### CORE-19 — `search()` auto-embeds on first call (BUG-010) — UI hang risk (SPEC-05)
- **Severity:** P1 · **Area:** search · **Status:** fix-in-bridge
- **Evidence:** `retrieve.py:171` `_ensure_embedded(con, cfg)` before lex+vec.
- **Affects UI:** First search must run as background job + "warming" state, or pre-warm at server start.

### CORE-20 — `context()` caller/callee labels swapped (BUG-008) (SPEC-05)
- **Severity:** P2 · **Area:** search · **Status:** pending-fix
- **Evidence:** `retrieve.py:267` context sections mislabel relationships.
- **Affects UI:** Don't render raw `why` strings as relationship names; render from `edges` with correct direction.

### CORE-21 — `search()` lacks tier/kind filters (SPEC-05)
- **Severity:** P3 · **Area:** search · **Status:** fix-in-bridge
- **Evidence:** `retrieve.py:128` signature `search(root, query, k)`.
- **Affects UI:** FR-5 needs filters; add WHERE clauses in bridge or extend core.

### CORE-22 — `graph()` returns node ids only, no labels/kinds (SPEC-05)
- **Severity:** P2 · **Area:** search · **Status:** fix-in-bridge
- **Evidence:** `retrieve.py:265` returns `sorted(seen)` ids; edges have kinds.
- **Affects UI:** 3D graph needs node kind/path/severity; decorate via `graph_payload` bridge.

### CORE-23 — `impact_diff` is subprocess-heavy (git) per commit (SPEC-06)
- **Severity:** P3 · **Area:** impact · **Status:** fix-in-bridge
- **Evidence:** `stack/impact.py:116` git log/diff per target; no cap.
- **Affects UI:** PR-mode impact must run as background job or cap commits.

### CORE-24 — `impact()` sparse when file has no symbols/tests (SPEC-06)
- **Severity:** P3 · **Area:** impact · **Status:** open
- **Evidence:** `stack/impact.py:30-38` single seed; `_dependents` follows only imports/calls/references.
- **Affects UI:** Show honest "no relationships" state; offer re-sync when edges stale.

### CORE-25 — `file_summary` silently falls back to structure summary without LLM (SPEC-06)
- **Severity:** P3 · **Area:** summarize · **Status:** open
- **Evidence:** `summarize.py:38` `_llm_summary` requires LLM config; failure → structural summary.
- **Affects UI:** Source badge on summary section; don't imply AI analysis when unavailable.

### CORE-26 — `suggest_context_for_edit` deps risk under FastAPI (SPEC-06)
- **Severity:** P2 · **Area:** predict · **Status:** verify-at-integration
- **Evidence:** `predict.py:165` imports registry-heavy modules; must run standalone.
- **Affects UI:** Bridge try/except fallback to impact + symbols if it throws.

### CORE-27 — `analysis` hardcodes quality_score=80 fallback for non-Next.js (SPEC-07)
- **Severity:** P2 · **Area:** analysis · **Status:** open
- **Evidence:** `analysis.py:49-57` imports `stack.nextjs`; except → quality_score=80.
- **Affects UI:** Health score not comparable across stacks; show "fallback" note.

### CORE-28 — `audit.refresh` re-indexes routes/stack each run (subprocess/CPU heavy) (SPEC-07)
- **Severity:** P2 · **Area:** audit · **Status:** fix-in-bridge
- **Evidence:** `stack/audit.py:17-21` nextjs/prisma re-index; `R.run_rules` CPU-bound.
- **Affects UI:** Audit must be a background job with progress, not a GET.

### CORE-29 — `findings`/`quick_wins` capped (100/10), no pagination (SPEC-07)
- **Severity:** P3 · **Area:** audit · **Status:** fix-in-bridge
- **Evidence:** `stack/audit.py:48` limit=100; `quick_wins` limit=10.
- **Affects UI:** Add offset/pagination in bridge; big repos exceed caps.

### CORE-30 — empty-repo health score = 50 (neutral), indistinguishable from mediocre (SPEC-07)
- **Severity:** P3 · **Area:** analysis · **Status:** open
- **Evidence:** `analysis.py:40-41` returns 50 when 0 symbols.
- **Affects UI:** Render "no symbols indexed — run sync" instead of a 50 ring.

---

## 5. CIP core backend findings (merged from `cip-findings.md` — live backend deep inspection)

Findings from the ongoing backend inspection of `lib/cipkg` (rolling log `cip-findings.md`). Where an
entry duplicates an existing BUG-xxx / CORE-xxx above it is cross-referenced and only the delta is kept.
Severity follows §Legend (F-doc uses P0/P1/P2/P3 with the same meaning). F-ids are stable.

### F-01 — `analysis.py` calls nonexistent `nextjs.list_findings` → health quality always 80, security buckets always empty
- **Severity:** P1 · **Area:** analysis · **Status:** open
- **Evidence:** `analysis.py:49-57,89-105,133-149` do `from .stack import nextjs as sn` then `sn.list_findings(con)`; `stack/nextjs.py` has no `list_findings` (only `_read/_app_route_path/index_routes/route_referenced/list_routes`) → AttributeError swallowed → `quality_score=80` fallback, critical-issues + high-priority sections always empty.
- **Cross-ref:** dup of BUG-013 (verified again this pass).
- **Affects UI:** Health gauge quality-component constant; "security critical issues" never populate.

### F-02 — `lancedb_store.py` uses `json` without importing it
- **Severity:** P1 · **Area:** index · **Status:** open
- **Evidence:** `lancedb_store.py:55` `json.dumps(meta)`; no `import json`. Dead module (see F-04).
- **Cross-ref:** dup of BUG-005.

### F-03 — Integration tests call stale `indexer.sync(con, cfg)` signature → 10 tests fail, single test hangs >120s
- **Severity:** P1 · **Area:** tests · **Status:** open
- **Evidence:** real signature `sync(root=None, full=False, do_embed=True, progress=None)` (`indexer.py:405`); tests call `sync(con, cfg)` at `test_integration.py:41,66,84,110,130,150,170,192` and `conftest.py:91` → `con`→root, `cfg`→full, and `do_embed=True` default loads the embed model → hang/permission errors. Correct: `sync(root=temp_repo, do_embed=False)`.
- **Related:** BUG-001 (same stale-signature bug in `web_server._api_sync`).
- **Affects UI:** Test gate unverifiable until fixed; keep the web-server fix and the test fix in lockstep.

### F-04 — Three backend modules are dead code and/or broken (consolidated)
- **Severity:** P1 · **Area:** misc · **Status:** open
- **Evidence:** table — `retrieval_bridge.py` (only ref `test_integration.py:185`; `con` undefined F821; missing `sqlite3`/`connect`), `ast_chunker.py` (0 refs), `lancedb_store.py` (only string in `dependency_checker.py`). All three **untracked in git**.
- **Cross-ref:** parts of BUG-006/007 (retrieval_bridge), BUG-011/024 (ast_chunker), BUG-005 (lancedb).
- **Affects UI:** Ensure the fresh web build never routes through these; prefer `retrieve.context()`/`search()`.

### F-05 — `stack/tauri.py` capability regex never matches real Tauri v2 manifests → Tauri security analysis non-functional
- **Severity:** P2 · **Area:** stack · **Status:** open
- **Evidence:** `tauri.py:7` `CAPABILITY_RE` matches `{"allow":[{..."cmd":"..."}]}`; real Tauri v2 capabilities use `{"identifier": "shell:allow-open", "allow": [{"name": "open"}]}` (`name`, not `cmd`). `parse_capabilities` never `json.loads`; `json` imported unused; `except (OSError, json.JSONDecodeError)` is a dead except. Net: `allowed_commands` always empty → `TAURI-UNGATED-COMMAND` (rules.py:481) flags every command; `is_allowed` always False.
- **Affects UI:** Tauri findings in the findings explorer are false positives until the parser matches v2 schema.

### F-06 — `retrieve.py _external_search` exception tuple references `json` before import (NameError) + swallows everything
- **Severity:** P2 · **Area:** retrieve · **Status:** open
- **Evidence:** `retrieve.py:124` `except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception)`; `import json` is at line 105 inside the `try` — if `subprocess.run` raises TimeoutExpired, evaluating the tuple raises `NameError: name 'json' is not defined`, masking the original. Trailing `Exception` makes the specific types redundant.
- **Cross-ref:** extends BUG-022 (adds the NameError nuance).
- **Affects UI:** External-search path only; falls back to internal search either way. Low surface.

### F-07 — Two separate memory stores never share data
- **Severity:** P2 · **Area:** memory · **Status:** open
- **Evidence:** `learning_system.py:693-706` uses `<data_dir>/learning_data/memory.db` + `episodes.db`; `web_server.py:270-281,458-483` uses `<root>/.cip/memory.db` + `episodes.db`; AGENTS.md documents `.cip/...`. Same schemas, different DB files.
- **Affects UI:** Memory lab (learning + temporal/episodic) reads/writes a store the CLI learning path never touches → learned preferences never reach the web panel and vice versa.

### F-08 — `learning_system` recall + suggestion-preference analysis are near-dead logic
- **Severity:** P3 · **Area:** learning · **Status:** open
- **Evidence:** `recall_relevant` semantic branch builds predicate `f"command:{query[:50]}"` → matches only byte-identical prior commands (no fuzzy/embedding recall); `_analyze_suggestion_preferences` reads `context.get('category','general')` but `record_suggestion_response` stores only `{'suggestion_id': ...}` → every suggestion lands in `'general'`.
- **Affects UI:** "Personalization" claims are not backed by real per-category data.

### F-09 — pyflakes-flagged unused/undefined items (verified)
- **Severity:** P3 · **Area:** misc · **Status:** open
- **Evidence:** `lancedb_store.py:55` json (F-02); `retrieval_bridge.py` `con` F821; `error_system.py:97` `error_type` unused; `gatekeeper.py:225` `title` unused; `intelligent_executor.py` unused `datetime/threading/Callable`; `__init__.py:5` F401; `command_registry.py:11` `inspect` F401; `base.py`/`cli.py` E701/E702.
- **Affects UI:** None directly; hygiene gate (`cip gate`) input.

### F-10 — Test-suite state recorded
- **Severity:** P2/P3 · **Area:** tests · **Status:** open
- **Evidence:** `tests/sync-system` → **15 passed, 19.5s** ✅; full `pytest tests` → **10 failed, 90 passed, 1 skipped, 29 errors, 174s** (errors = dashboard (out of scope) + integration F-03). `tests/conftest.py:20-31` imports `cipkg.terminal_dashboard` at collection → Textual import required for ALL tests. Test files shipped inside package: `lib/cipkg/test_embed.py`, `lib/cipkg/test_gapfill.py`.
- **Affects UI:** CI baseline; root-conftest dashboard coupling should be removed so backend tests run without Textual.

### F-11 — Repo-profile system (`repo-settings/`) is dead in every runtime path — profiles & `external_search` never load
- **Severity:** P1 · **Area:** config · **Status:** open
- **Evidence:**
  - `base.py:117-122`: `cip_base_dir = dirname(dirname(__file__))` with `__file__`=`lib/cipkg/base.py` → resolves to `lib`, so `repo_settings_dir = lib/repo-settings` which **does not exist** → `from detectors import ...` ImportError → swallowed by bare `except Exception: pass` (line 144). Verified at runtime: `load_config('.')` → `profile: {}`, no `external_search`, empty `index.exclude`.
  - `context_manager.py:155` + `suggestion_engine.py:637`: `from repo_settings.detectors import ...` — the directory is literally `repo-settings` (hyphen, not a valid module name) → always ImportError → `RepositoryProvider` always uses `_fallback_provide` (repo_type=`generic`, config=`{}`). Verified: `import repo_settings.detectors` → ModuleNotFoundError.
  - Only `bin/cip.py:42-45` computes the correct path (`<root>/repo-settings`) and works — but only for a banner in `cip init`.
  - Impact: `retrieve.py:81-84` `_external_search` reads `cfg["external_search"]` → always empty → vivim-final `defer_to = "bun"` `code-index search` integration silently never runs; profile overrides (retrieval k-values, stack toggles, include/exclude) never applied; `RepositoryContext.profile_settings` always `{}`.
  - Also: AGENTS.md documents `lib/cipkg/repo-settings/` (doesn't exist); `profiles/vivim-final/custom_rules.toml` is dead config (`stack/custom_rules.py` reads only `.cip/rules.py`).
  - Positive control: adding `<root>/repo-settings` to `sys.path` → `detect_repo_type('.')` = `index`, profile loads (`profile/language/retrieval/stack`).
- **Cross-ref:** sharpens CORE-4 (which assumed this path works and only flagged the sys.path side effect).
- **Affects UI:** External search + per-repo profile settings silently off. Fix = resolve repo-settings from repo root (walk up from cwd) or install as a properly named package; align all three import sites.

### F-12 — `workflow_engine._run_pytest` parse bug → "Verify Tests" step always reports 0
- **Severity:** P2 · **Area:** workflow · **Status:** open
- **Evidence:** `workflow_engine.py:646-649` iterates `output.split()` and does `int(part.split()[0])` on the token containing "passed" — for summary `"90 passed, 1 skipped in 174.00s"` the token is `"passed,"` → `int("passed,")` raises ValueError → propagates to `_step_verify_tests` (outer `except Exception`) → returns all-zero counts. Also `total_tests=passed` conflates pass count with total (skips not counted).
- **Affects UI:** Pre-commit workflow report always shows "Tests Passed: 0" even when tests pass.

### F-13 — `workflow_engine` audit/impact steps import nonexistent modules → silent no-op
- **Severity:** P2 · **Area:** workflow · **Status:** open
- **Evidence:** `workflow_engine.py:552` `from cipkg import audit` and `:584` `from cipkg import impact` — neither top-level module exists (only `cipkg.stack.audit` / `cipkg.stack.impact`). Verified: `import cipkg.audit` → ModuleNotFoundError → caught by `except ImportError` → "Run Audit" / "Check Impact" steps always return empty fallback results.
- **Affects UI:** Diagnosis/pre-commit workflows silently skip audit + impact analysis.

### F-14 — `error_system` recovery + pattern learning are stubs
- **Severity:** P3 · **Area:** misc · **Status:** open
- **Evidence:** `RecoveryEngine._retry_operation` (error_system.py:469-490) sleeps `1×timeout_multiplier` then unconditionally returns success — never re-runs anything; `_get_error_history` (line 737-740) always returns `[]` → `ErrorPatternLearning` can never learn; `_reset_configuration` does nothing but return success. Also `ErrorPrevention` warns "Low disk space" whenever psutil is absent (defaults 0 free bytes).
- **Affects UI:** "Auto-recovery" claims success without recovery; error-personalization never activates.

### F-15 — Registry `analyze` + `rebuild` cards broken by arity mismatch (functions exist but called wrong)
- **Severity:** P2 · **Area:** command center · **Status:** open
- **Evidence:** `command_registry.py:1038-1045` (`_handle_analyze`) and `:929-936` (`_handle_rebuild`) call `handle_analyze_command(root, Namespace(**args))` / `handle_rebuild_command(root, Namespace(**args))`, but `cli.py:71` and `cli.py:75` define **`handle_analyze_command(root)`** / **`handle_rebuild_command(root)`** (single param) → TypeError on every call → both cards always return `{'error': ...}`.
- **Note:** distinct from CORE-5 (which imports functions that don't exist). Here the functions exist but arity mismatches. Combined count of permanently-broken registry cards: **CORE-5's 14 + F-15's 2 = 16**.
- Verified: `inspect.signature(cli.handle_analyze_command)` → `(root)`; `cmd_embed_ping(root, count)` and `cmd_embedder(root)` are correctly matched (controls OK).
- **Affects UI:** Any command-center run of `analyze` or `rebuild` returns an error even though CLI works.
- **CLI path also broken (severity → P1):** `cli.py` `dispatch_command` (line ~714) calls every handler as `handler(root, args)`, so `cip analyze` and `cip rebuild` crash with an **uncaught `TypeError: handle_analyze_command() takes 1 positional argument but 2 were given`** (verified at runtime). Fix is a special-case in dispatch OR align both handlers to `(root, args)`.

### F-16 — 21 CLI subcommands registered in argparse but missing from `dispatch_command` → all print "unknown command"
- **Severity:** P1 · **Area:** command center / cli · **Status:** open
- **Evidence:** `cli.py` `setup_argument_parser` registers these subparsers, but `dispatch_command`'s `handlers` dict (lines ~700-708) has no entry for them → `cip <cmd>` prints `unknown command: <cmd>` and exits 1. Verified at runtime: `coverage`, `gate`, `embedder`, `score`, `routes`, `refactors` all → `1`.
- **Affected commands (21):** `refactors`, `routes`, `models`, `gate`, `dashboard`, `admission`, `embedder`, `embed-ping`, `coverage`, `dead`, `circular`, `blame`, `score`, `migrations`, `env`, `logs`, `metrics`, `features`, `deps`, `api`, `predict`.
- **Note:** handlers exist for some of these (`cmd_embedder`, `cmd_embed_ping`, `handle_gate_command`? — `gate` has no handler at all; `score` → `gapfill.score` exists but not wired; `routes`/`models` → stack nextjs/prisma exist but not wired). These features are unreachable from both CLI **and** command registry (CORE-5 covers the registry side). `dashboard` (TUI) is reachable only via `dashboard-web`.
- **Affects UI:** AGENTS.md documents `cip gate`, `cip refactors`, `cip routes`, `cip models`, `cip score` etc. as available → all dead.

### F-17 — `verify-index` subcommand maps to the WRONG handler in `dispatch_command`
- **Severity:** P2 · **Area:** command center / cli · **Status:** open
- **Evidence:** `cli.py` `dispatch_command` maps `"verify-index"` → `handle_verify_command` (the **verification gate** logic: typecheck/lint/audit/blocking), but the correct handler `handle_verify_index_command` (runs `maintain.verify(root, repair=args.repair)`) is defined at `cli.py:79` and **never dispatched** (dead code). Verified at runtime: dispatch of `verify-index` calls `handle_verify_command`.
- **Affects UI:** `cip verify-index --repair` runs the wrong analysis (verification gate, which reads different flags) instead of repairing the index.

### F-18 — sync_global pattern expansion drops top-level files under `repo-settings/**/*`
- **Severity:** P2 · **Area:** sync_global · **Status:** open
- **Evidence:** `sync_global/core/sync_engine.py:47-65` expands `**` patterns with `fnmatch.fnmatch(rel_path, pattern)`, but `fnmatch` treats `**` as `*` (no recursive wildcard). Verified at runtime: pattern `repo-settings/**/*` matched only 12 files (all under `profiles/`); `repo-settings/detectors.py` (top-level) is **not** matched → never synced to `~/.cip-global`. Also `sync.py:32` inserts `sync_global/sync_global` (nonexistent) into `sys.path` — harmless (script dir auto-added) but dead; `sync.py` docstring says `python sync_global.py` but file is `sync.py`.
- **Affects UI:** Global install is missing `detectors.py` → even a correctly-wired global CIP would fall back to generic repo detection (compounds F-11).

### F-19 — sync_global pre/post validation always validates the EMPTY `files` list (not the expanded items)
- **Severity:** P2 · **Area:** sync_global · **Status:** open
- **Evidence:** `sync.py:171`, `:188`, `:217` all call `validator.pre_sync_validation(config['items']['files'])` / `post_sync_validation(config['items']['files'])`, but `config['items']['files']` is the empty explicit-fallback list (`sync_config.toml` uses `patterns`). The actually-synced items live in `engine.items_to_sync` and are never checked. `cip_validation()` (`validator.py:56-96`) similarly only checks that `repo-settings/` exists + `detect_repo_type`/`load_repo_profile` strings appear in `base.py` — not that synced files landed.
- **Affects UI:** Post-sync validation reports PASSED even when patterns silently failed to copy (as in F-18); auto-rollback never triggers for missing files.

### F-20 — SuggestionEngine crashes on EVERY call: `FilterEngine.rank` does not exist
- **Severity:** P1 · **Area:** suggestions / intelligent_executor / interactive · **Status:** open
- **Evidence:** `suggestion_engine.py:663` `filtered = self.filter_engine.rank(ranked)`, but `FilterEngine` (line 575) only defines `filter()` (and `_remove_duplicates`/`_limit_by_priority`). Verified at runtime: `SuggestionEngine(...).generate_suggestions()` → `AttributeError: 'FilterEngine' object has no attribute 'rank'`. Callers: `interactive.py:84`, `help_system.py:223`, `intelligent_executor.py:542` + `:641`. (The intended chain is `ranking_engine.rank(...)` then `filter_engine.filter(...)`.)
- **Affects UI:** All suggestion features (interactive UI, help suggestions, intelligent executor's suggestion step) raise instead of returning suggestions.

### F-21 — `web_server._api_search` calls nonexistent `retrieve.hybrid_search` → `/api/search` always 500
- **Severity:** P1 · **Area:** web · **Status:** open
- **Evidence:** `web_server.py:186` `results = retrieve.hybrid_search(root, query, limit=limit)`; `retrieve.py` defines only `search(:128)/find_symbol(:191)/graph(:228)/context(:267)` — no `hybrid_search`. Runtime-verified. Caught by `_send_json(...,500)`. FOUND in Gap-2 pass; legacy web is being replaced (BUG-004), but any bridge reusing this handler copy-pastes a dead call.
- **Affects UI:** Search always errors in the old console; new bridge must call `retrieve.search(root, query, k)` or `context()` — never `hybrid_search`.

### F-22 — `imports` edge resolution fails for ~99% of specs → import-dependent rules silently no-op (root-cause)
- **Severity:** P1 · **Area:** index / audit / retrieve · **Status:** open
- **Evidence:** `indexer.resolve_import` (`indexer.py:40-54`) maps module `cipkg.base` → `cipkg/base.py` (repo-root-relative), but indexed file paths are `lib/cipkg/base.py` (`files.path`). Simulated resolution over live DB: **514 specs → 2 resolved (0.4%)**. Absolute: 280 → 2 (0.7%); relative: 234 → 0 (0%). Verified concrete cases all → None: `store.py ← .base`, `indexer.py ← .parse`, `stack/rules.py ← ..base`, `cli.py ← .`. Root cause: bare-module branch (`spec.replace(".","/")`) never tries `lib/`/`src/` prefix, and the relative branch base is also `os.path.dirname(src_path)`-joined (which for `..base` from `lib/cipkg/stack/` yields `lib/cipkg/base` — exists — but `.base` from `lib/cipkg/` → `lib/cipkg/base` also exists — yet 0 matched, meaning `all_paths` passed to `link_imports` at call site `indexer.py:380` was **stale/empty** (last sync's `dirty` set), see F-23). Net: DB has 1032 `file_imports` rows but only **2** `imports` edges (both in non-backup paths).
- **Blast radius (all verified 0-findings in rules dry-run because the import graph is empty):** `QA-CIRCULAR` (needs `imports` edges), `ARCH-LAYER-VIOLATION`, `ARCH-ORPHAN-FILE` (both `kind='imports'`), `rule_hidden_export`'s `NOT EXISTS references` gate partially, and `build_tested_by` → `tested_by` edges = 0 (see F-23). Call/reference edges DO exist (2,874 `calls`) because those come from symbol-body name matching, not imports.
- **Affects UI:** Import graphs, circular-dep detection, layer-violation, orphan-file, and tested-by signals are all empty on real repos — the UI renders "no relationships / no tests" as if clean.

### F-23 — `build_tested_by` produces 0 `tested_by` edges even though 15 test files are indexed → QA-UNTESTED-HOT fires on every hot symbol
- **Severity:** P2 · **Area:** index / audit · **Status:** open
- **Evidence:** Live DB: 15 indexed files whose path contains `test`, `is_test_path('tests/…')=True` (via `cfg["index"]["test_globs"]`), yet `SELECT COUNT(*) FROM edges WHERE kind='tested_by'` = **0**. `build_tested_by` (`indexer.py:220-249`) seeds targets from `edges WHERE src_path=<testfile> AND kind IN ('imports','calls','references')` — those edge sets are empty because imports resolution fails (F-22) and calls/references are symbol-scoped (src_path is the *source* file, not the test file) → only the name-mention heuristic could help but the target set starts empty. Consequence: **QA-UNTESTED-HOT fires 30 findings (its cap) on every symbol with ≥5 dependents**, e.g. `_out` (cli.py, 30 dependents), `Suggestion` (26), `render` (21, 5 dup ids). Test coverage signals are meaningless until import/tested_by edges are real.
- **Cross-ref:** interacts with BUG-007 (tested_by edge direction) — that bug is currently masked because there are no tested_by edges at all.
- **Affects UI:** "Untested hot code" panel is pure noise (all findings are false positives given tests DO exist and cover much of this); do not render until edges fixed.

### F-24 — Rules engine dry-run: all 25 rules execute without throwing; only QA-DUP + QA-UNTESTED-HOT fire on this repo
- **Severity:** P3 · **Area:** audit · **Status:** open
- **Evidence:** In-memory backup of live DB + `stack.common.ensure` + `run_rules` (rules.py:552): every rule returned without exception. Results: QA-DUP=29 (dedup of identical symbol bodies — plausible), QA-UNTESTED-HOT=30 (spurious, see F-23), all 23 others = 0. Of the 0s, the TS/Prisma rules (`DB-*`, `NEXT-*`, `HIDDEN-*`, `SEC-*`, `TAURI-*`) are expected-empty (repo is Python-only; `.cip` indexed before TS/web existed — user-confirmed). The remaining import-dependent rules are empty because of F-22, not because the repo is clean.
- **Also verified:** `rule_db_missing_index`'s `ast.literal_eval(m["fields"])`/`ast.literal_eval(m["indexes"])` matches how `prisma.index_stack` stores them (`str([names])`/`str([combos])`, `prisma.py:70-71`) — that data path is consistent. `stack/common.ensure` (`common.py:40`) creates the findings/routes/models/model_usage/tauri tables; `audit()` (`audit.py:16`) calls `ensure` before `run_rules`, so the "missing table" failure mode doesn't occur via the audit path.
- **Affects UI:** Findings explorer on a real TS/Prisma repo will show TS findings only if `audit(refresh=True)` ran `nextjs.index_routes`+`prisma.index_stack`; if those silently fail (both wrapped in `try/except: pass`, `audit.py:17-21`), the rules query **empty** `routes`/`models` tables and report "clean" — same silent-no-op class as CORE-28.

### F-25 — Gap map vs merge-note claim: 32 backend modules were never read (merge-note "No unread backend files remain" is false)
- **Severity:** P3 (doc hygiene) · **Area:** misc · **Status:** open
- **Evidence:** The §6 merge-note (line 500-506) claims the deep-read is COMPLETE. Grep of `lib/cipkg/` shows modules with **zero report mentions and zero evidence lines**, including: `stack/rules.py` (524 lines — the audit engine, now read this pass), `command_adapter.py` (449, F-16/CORE-5 bridge), `interactive.py` (311), `interactive_ui.py` (691), `help_system.py` (236, F-20 caller), `hooks.py`, `session.py`, `router.py` (179, feeds server.py route/route_for_agent), `runtime_adapters.py` (90, `broken()` used by `gate()`), `watcher.py` (111), `websocket_handler.py` (178), `dashboard_state.py` (175), `repo_map.py` (102), `rerank.py` (35), `vecstore.py` (33), `scip_indexer.py` (159 — AGENTS.md claims SCIP integration), `parse.py`/`tree_parser.py`/`parsers.py`/`tsconfig.py`/`dependency_checker.py`/`lock.py`/`stack/common.py`/`stack/custom_rules.py`/`stack/selftest.py`. `sync_global/` sits at repo **root** (not `lib/cipkg/sync_global/` as AGENTS.md states). **Line counts corrected this pass:** `command_adapter.py` is **475** lines (not 449), `interactive.py` is **325** (not 311).
- **Affects UI:** New-web design must not assume these surfaces were vetted; SCIP/repo-map/rerank claims in AGENTS.md have no evidence of wiring.

### F-26 — `command_adapter.py` is fully dead code; its `_execute_original` placeholder fakes success without running the command
- **Severity:** P2 · **Area:** commands / interactive · **Status:** dead (do-not-wire)
- **Evidence:** Full read (475 lines). `ContextAwareCommand.execute` (`command_adapter.py:374-412`) builds adapters and calls `self._execute_original(command, adapted_args)` (`:407`), which **never invokes any real command** — it returns `{'command':…, 'args':…, 'adapted': False, 'success': True}` (`:414-423`) and only triggers on `require_confirmation`/adaptation failures. If any caller wired this in, every command would silently "succeed" without running. Caller graph: the module is imported **only** by `interactive.py:14,34` (`ContextAwareCommand`); the convenience fns `adapt_command` (`:452`) and `get_adaptation_info` (`:463`) have **zero callers** repo-wide (rg). `intelligent_executor.py:389` `_adapt_command` is a separate implementation (different signature) and does NOT use this module.
- **Cross-ref:** NOT the command-center bridge implied by §A of 10-research-guide.md — it connects to no dispatch path (`cli.py` `handlers` dict `:669-710` never references it). CORE-5 / F-16 cover the actual dispatch breakage elsewhere.
- **Affects UI:** Nothing today (unreachable). Do NOT build the console's command execution on `ContextAwareCommand`/`adapt_command`; if resurrected, it must actually invoke `cli.dispatch_command` and must never return `success=True` on a no-op.

### F-27 — `interactive.py` (InteractiveMode) is unreachable: zero importers + no `cip interactive` subcommand, yet help advertises it
- **Severity:** P2 · **Area:** interactive / cli / help · **Status:** dead (remove-or-wire)
- **Evidence:** `interactive.py` (325 lines) defines `InteractiveMode`, `start_interactive_mode`, `show_context_aware_help`, `show_suggestions`, `execute_workflow_cli`, `list_available_workflows` — **no importer exists** in `lib/cipkg/` (rg: the only hits are help-text strings). `cli.py` argparse registers **no `interactive` subcommand** (`:507-641`) and `dispatch_command` handlers (`:669-710`) has no entry. Yet `help_system.py:124,166` advertise `Run 'cip interactive' for guided workflows` / `cip interactive  Enter interactive mode` → the advertised feature does not exist (running `cip interactive` yields "unknown command"). Even if reachable, `_execute_command` (`:208-273`) calls `context_aware_command.execute` → F-26 placeholder → reports success without executing; and `_render_welcome_screen` (`:78-89`) calls `SuggestionEngine.generate_suggestions` → F-20 `AttributeError`, caught by the `except` in `_run_interactive_loop` (`:71-76`) → spams "Error: …" and resets to welcome. `_run_search`/`_render_search_screen`/`_render_workflow_screen` are "to be implemented" stubs (`:119,125,160`).
- **Cross-ref:** F-20, F-26, CORE-52.
- **Affects UI:** New console onboarding/help must NOT reference an "interactive mode" command unless it is actually wired; the console itself replaces this TUI path — do not reuse its input loop or stub screens.

### F-28 — `interactive_ui.py` (691 lines) is reachable only from dead `interactive.py`
- **Severity:** P3 · **Area:** interactive · **Status:** dead
- **Evidence:** `interactive_ui.py` imported **only** by `interactive.py:17-19` (`WelcomeScreen`, `SettingsScreen`), which is itself unreachable (F-27). No other module imports it. The entire welcome/settings screen surface is therefore dead along with the orchestrator.
- **Affects UI:** None; do not reuse its `render()` output as the new console's welcome screen — it belongs to the dead TUI path.

### F-29 — `help_system.py` is dead AND broken: `display_help` crashes (None `index_status`), `display_suggestions` hits F-20, base help is a placeholder
- **Severity:** P2 · **Area:** help / cli · **Status:** dead (do-not-wire)
- **Evidence:** Full read (247 lines — F-25 said 236, correcting). **Dead:** only importer is `interactive.py:15,33,284,290` (F-27 dead); no `help`/`workflow`/`suggest` subcommand and no `--classic`/`--classic` flag exist anywhere in `cli.py` (`add_parser` list `:507-663`, `dispatch_command` `:669-710`, `main` `:721-732`), so `display_help`/`display_suggestions`/`show_context_aware_help`/`show_suggestions` are unreachable. **Broken (runtime-verified):**
  - `display_help(root)` → `AttributeError: 'NoneType' object has no attribute 'get'` at `help_system.py:104` `context.repository.index_status.get('stale')` — `index_status` is `Optional` and legitimately `None` (`context_manager.py:35,514`) when no provider supplies it, so this crashes on the default context (not exceptional input).
  - `display_suggestions(root)` → `AttributeError: 'FilterEngine' object has no attribute 'rank'` (F-20) at `help_system.py:223`.
  - `_get_base_help` (`:149-153`) returns literal placeholder text `"This is a placeholder. The actual help system would be integrated here."` — per-command help is fake.
  - `_format_help` (`:124-125`) + `_get_classic_general_help` (`:155-175`) advertise `cip help`, `cip interactive`, `cip workflow`, `cip suggest`, and `cip --help --classic` — none of these exist (F-27 covers `interactive`; `help`/`workflow`/`suggest`/`--classic` have no parser or dispatch entries either).
- **Affects UI:** Do NOT build console help/onboarding on this module or copy its advertised command names. New console needs its own command documentation; `--help` currently falls back to argparse's auto-generated help only.

### F-30 — `post_edit_hook` reads impact keys that `stack/impact.impact()` never returns → impact metrics always empty/zero
- **Severity:** P2 · **Area:** hooks / impact · **Status:** open
- **Evidence:** `hooks.py:29-32` builds the impact summary from `impact_result.get("callers", [])`, `impact_result.get("callees", [])`, `impact_result.get("risk_score", 0)`, `impact_result.get("summary", "")`. Runtime-verified `stack/impact.py:impact(root, target='lib/cipkg/base.py', depth=2)` returns **only** `{target, risk, seed_files, affected_files, affected_count, tests_to_run, routes_affected, open_findings_in_area, hotspot_heat, advice}` — none of `callers/callees/risk_score/summary` exist. Verified live via `post_edit_hook('lib/cipkg/base.py')` → `{'impact': {'callers': 0, ' callees': 0, 'risk_score': 0, 'summary': ''}}`. Two sub-bugs: (1) the returned key is **`" callees"`** (leading space, `hooks.py:30`) so even the empty default lands under a misspelled key; (2) the whole impact block is meaningless — the hook always reports 0 callers/callees/risk and no summary regardless of actual blast radius. The `audit` half works (`findings` keys match `audit.findings()` list-of-dicts). Also **root-threading drop:** `handle_hook_command` (`cli.py:93-97`) builds `hook_args` and calls `run_hook_command(hook_args)` without passing `root`; `run_hook_command` (`hooks.py:153-173`) calls `post_edit_hook(hook_args[0])`/`pre_edit_hook(...)` with `root=None` → falls back to `repo_root()` (cwd-relative). Same class as ISSUE-103 / CORE-7 root discipline.
- **Cross-ref:** ISSUE-103 (root threading), CORE-7 (CLI handlers return None / `_out()` print — the hook CLI path also returns dict via `_out`, but the registry card `command_registry.py:1331-1333` wraps it, so that path returns the dict).
- **Affects UI:** Any agent-hook integration that consumes `post_edit_hook`'s impact summary (callers/callees/risk) gets constant zeros — the "impact analysis after edit" hook promise is unfulfilled. Fix = read the actual keys (`affected_count`, `risk`, `affected_files`) or extend `impact()` to expose callers/callees.

### F-31 — `session.py` context packet silently empty: `retrieve.runtime_adapters` doesn't exist, `map_` keys mismatch → architecture/broken_tests/test_delta always zero/error
- **Severity:** P2 · **Area:** session / agent context · **Status:** open (Agent 1)
- **Evidence:** Full read of `session.py` (199 lines — guide said 193, correcting). `session_start` (`:24-80`) is a real, wired feature (`cli.py:639-643` `session` subparser + `:699` dispatch; registry cards `command_registry.py:706-734`), so this is reachable — runtime-probed successfully via `session_start(root)`. Three silent-broken data-collection blocks:
  1. **`retrieve.runtime_adapters.broken` (`:48`) → AttributeError** — `cipkg.retrieve` has NO `runtime_adapters` attribute (only a function-local `from .runtime_adapters import broken as _broken` at `retrieve.py:321-322`). Caught by `except Exception` → `broken_tests` always `[]`. Same at `_collect_test_delta` (`:182`) → archived session `test_delta` = `{'error': 'test delta collection failed'}` (verified in archived JSON). The correct target `runtime_adapters.broken(root)` returns real data (`{'files':0,'signals':[],'window_days':7}`), so the fix is a one-line import.
  2. **`architecture` block reads keys `map_()` never returns (`:37-42`)** — reads `arch_map.get("subsystems")`, `"total_files"`, `"overview"`, but `summarize.map_(root)` returns `{directories, totals:{files,symbols}, hotspots, navigate}` (runtime-verified). So `architecture` is always `{subsystems:0, total_files:0, overview:""}` even though `totals.files`=225 exists. Docstring (`:13-17`) promises "Architecture map and subsystem overview" — never delivered.
  3. **Learning half works:** `learning.update_prediction_confidence(root)` (`:137`) is real (`learning.py:114-157`, writes `confidence_adjustments.json`); `verify(root, typecheck=False, lint=False, audit_check=True)` (`:105`) is real and ran clean. `_collect_edited_files` (`:153-165`) works via `git diff --since=`.
- **Cross-ref:** F-08 (learning recall near-dead), CORE-53 (confidence labeling — the `update_prediction_confidence` block it feeds is reachable here), CORE-7 root discipline N/A (root passed correctly by `handle_session_command`).
- **Affects UI:** The `session start` context packet is the agent-onboarding context — with architecture/broken_tests/hotspots/findings all zeros, agents get a stripped context. Fix = import `broken` directly in `session.py` and read the real `map_` keys (`totals.files`, and either derive subsystems or rename).

### F-32 — `watcher.py` (watchdog-based) is dead AND broken: zero importers, and its only re-index path calls nonexistent `indexer.mark_for_reindex`
- **Severity:** P3 · **Area:** watcher / daemon · **Status:** dead (do-not-wire) (Agent 1)
- **Evidence:** Full read of `watcher.py` (114 lines — guide said 111, correcting). **Dead:** `setup_watcher`/`AsyncFileWatcher`/`CodeChangeHandler` appear ONLY inside `watcher.py` itself (grep-verified zero external importers); no `cip` subcommand or `command_registry` card references it. **Broken if wired:** `on_file_change` (`watcher.py:104`) calls `indexer.mark_for_reindex(con, [path])` which **does not exist** — `indexer.py` has only `embed_pending` (`:250`), no `mark_for_reindex` anywhere (grep-verified). So every file change would raise AttributeError caught at `:110` and log `[Watcher] Error re-indexing`. It also depends on the `watchdog` third-party lib (`dependency_checker.py` maps it) — an extra dep for a dead module.
- **Contrast — the ACTIVE watcher:** `watch.py` (34 lines, zero-dependency mtime polling + debounce) is what `daemon.py:154` actually imports (`from .watch import watch`, run in a thread at `daemon.py:158-160`). So CORE-16/57 "watcher loop" claims are satisfied by `watch.py`, NOT `watcher.py`. `watcher.py` is an abandoned watchdog-based rewrite that should be deleted or its re-index path fixed to `indexer.embed_pending`.
- **Cross-ref:** CORE-16/57 (blocking loop claims — satisfied by `watch.py`, not this file).
- **Affects UI:** None (new web doesn't use a filesystem watcher; daemon polling is the live mechanism). Cleanup only — delete `watcher.py` or re-wire to `embed_pending` if auto re-index on edit is ever wanted.

### F-33 — `repo_map.py` + `scip_indexer.py` are dead (zero importers, no CLI); AGENTS.md SCIP/repo-map claims unsupported — while `rerank.py` + `vecstore.py` are LIVE and work
- **Severity:** P2 · **Area:** scip / repo-map / rerank · **Status:** repo_map+scip dead; rerank+vecstore verified clean (Agent 1)
- **Evidence:** Full reads of all four (repo_map 107, rerank 37, vecstore 37, scip_indexer 162). Repo-wide grep: `generate_repo_map`/`handle_map_command` (repo_map.py) and `SCIPIndexer`/`handle_scip_command` (scip_indexer.py) have **zero importers** and **no CLI subcommand** (`cip map` → `summarize.map_` at `cli.py:682`, a different impl; no `scip` parser/dispatch anywhere in cli.py or command_registry.py). AGENTS.md claims "SCIP integration for precise symbol resolution" and "Repository maps for token-efficient context" — both unsupported by wiring. scip_indexer is additionally broken-if-wired: `_run_scip_index` runs `['scip','index','--output','json']` (not a real scip CLI invocation — scip writes protobuf/index.scip, not `--output json` stdout), and the `pip install scip-python` hint is wrong (scip is the Sourcegraph binary, not that PyPI package).
- **Contrast — LIVE:** `rerank.py` IS wired — `retrieve.py:6` imports it, used at `:168,:184`. Runtime-verified on a temp DB: identifier-match +0.5, path overlap +0.2, `tested_by` edge +0.1, recency +0.1 all applied, sort correct. `vecstore.py` IS wired — `retrieve.py` does `from . import vecstore` and calls `vecstore.knn` at `:54`. Runtime-verified: returns `[]` on empty matrix (clean), has numpy + pure-python fallback paths. Both need no findings.
- **Cross-ref:** F-22 (import edges — repo_map would depend on symbols; scip was the "precise resolution" answer that never landed).
- **Affects UI:** For the new console: the "SCIP precision" and "repo-map context" features advertised in AGENTS.md do NOT exist as wired paths — do not design UI around them. Search reranking (identifier/path/tested/recency boosts) IS live and will shape `search` results; design should account for it. If repo-map/SCIP are needed, they must be built new (or scip_indexer re-wired + fixed), not assumed present.

### F-34 — `cip selftest` crashes: `handle_selftest_command` imports `selftest`, but `selftest.py` only defines `run_selftest`
- **Severity:** P1 · **Area:** tests/cli · **Status:** open (Agent 2)
- **Evidence:** `cli.py:250-252` `from .selftest import selftest`; `selftest.py:92` defines only `run_selftest()` (no `selftest` name). Runtime-verified: `handle_selftest_command('.', Namespace())` → `ImportError: cannot import name 'selftest'`. Dispatched at `cli.py:702` + parser `cli.py:569`, so `cip selftest` (documented in AGENTS.md) crashes uncaught. Registry card survives via broad `except` (`command_registry.py:1386-1393`) → error dict.
- **Affects UI:** New console "Run tests" must NOT route through `cip selftest`. Fix = `from .selftest import run_selftest` + `_out({'exit_code': run_selftest()})`.

### F-35 — `dependency_checker.py` orphaned: real `handle_deps_command` lives there, but cli never imports it → `deps` broken in CLI AND registry
- **Severity:** P2 · **Area:** command center/cli · **Status:** open (Agent 2)
- **Evidence:** `dependency_checker.py:137` defines `handle_deps_command(root, args)`; `command_registry.py:1130` does `from .cli import handle_deps_command`, but `cli.py` has **no** such name (runtime-verified ImportError) → `_handle_deps` always errors. `cli.py:618` registers `deps` parser but dispatch `handlers` (`cli.py:669-710`) has no `deps` → "unknown command" (already F-16). `dependency_checker.py` has **zero importers**.
- **Cross-ref:** F-16, CORE-5. **Delta:** the handler exists but was never wired — fix = re-export from cli or add dispatch entry, or delete the module.
- **Affects UI:** Command center `deps` card permanently errors.

### F-36 — `stack/selftest.py` dead code: `run_stack_selftest` has zero callers
- **Severity:** P3 · **Area:** stack/tests · **Status:** open (Agent 2)
- **Evidence:** `stack/selftest.py:122` `run_stack_selftest()`; repo-wide rg finds no callers. Runs a full fixture Next.js+Prisma audit; nothing invokes it.
- **Affects UI:** None; do not expose unless intentionally wired.

### F-37 — `dashboard_state.py` dead code: zero importers
- **Severity:** P3 · **Area:** web · **Status:** dead (remove) (Agent 2)
- **Evidence:** Full read (180 lines). `DashboardState` + `StateUpdater` (30 s polling thread) — **no importer exists** (repo-wide grep). `terminal_dashboard.py:28` has its own unrelated `DashboardState(Enum)`. `StateUpdater._update_state` runs `gapfill.score` + `git` subprocess every 30 s.
- **Affects UI:** None — fresh SPA owns client state. Remove with legacy frontend.

### F-38 — `dashboard.py` unreachable via CLI (no dispatch entry) but `briefing()` is a reusable oracle signal (CORE-51)
- **Severity:** P2 · **Area:** web/oracle · **Status:** extract-briefing (Agent 2)
- **Evidence:** `cli.py:590` registers `dashboard` parser, but dispatch `handlers` (`cli.py:669-710`) has only `dashboard-web` → `cip dashboard` → "unknown command" (part of F-16). `dashboard.py` (122 lines) imports `http.server`, `stack_nextjs`, `stack_prisma`, `stack_impact`; `serve_dashboard` (port 8790) dead. `briefing(root, con)` (`dashboard.py:39-64`) computes refactor/risk/blocker/opportunity notes from `quadrant` + findings + `runtime_adapters.broken` — the CORE-51 oracle input.
- **Cross-ref:** CORE-51, BUG-004, F-16.
- **Affects UI:** Oracle/briefing panel must NOT import `dashboard.py` (pulls in http.server + stack). Extract `briefing()` to a leaf module (e.g. `stack/briefing.py`) taking `(root, con)`; delete the rest.

### F-39 — `websocket_handler.py` legacy WS protocol: only importer is legacy `web_server.py`; emitter uses `asyncio.create_task` from sync context (unsafe)
- **Severity:** P3 · **Area:** web · **Status:** legacy (protocol reference only) (Agent 2)
- **Evidence:** `web_server.py:527,561` imports `DashboardWebSocketServer`; no other importers. `DashboardEventEmitter.emit_*` (`websocket_handler.py:145-183`) call `asyncio.create_task(...)` from sync call sites → `RuntimeError: no running event loop` unless invoked inside the loop; `_running` set but never read. Protocol is sound: `subscribe/unsubscribe/ping/pong/request/response/event` + topic filter with `*` wildcard (lines 52-108).
- **Affects UI:** New console realtime feed (CORE-57) may reuse the subscribe/publish topic protocol as a **model**, but write a fresh emitter on FastAPI WS; do not reuse this module (legacy web removal).

### F-40 — `router.py` verified WIRED and working, but `route_for_agent`'s `cap:code:*` capability names are an un-consumed contract
- **Severity:** P3 · **Area:** retrieve/command center · **Status:** verified-clean (with caveat) (Agent 2)
- **Evidence:** Full read (182 lines). `route` + `route_for_agent` live: `server.py` TOOLS (:30-33) + `call_tool` dispatch (:139-141) + attached to `search` result (:118); `cli.py:205-210` `handle_route_command` (dispatched :687); `predict.py:9` imports router; `selftest.py:81-84` tests it. Runtime-verified: `route("why is this workaround here")→history`, `route("overview of the system")→architecture`. Caveat: `route_for_agent` emits `cap:code:impact/search/graph/...` tool names (`router.py:42-151`) that **no resolver in-repo consumes** — `server.py` TOOLS use bare names (`search`/`symbol`/`impact`); docstring's "Vivim CapabilityResolutionEngine" does not exist in-repo. `_generate_next_ops` also emits `cap:code:*` template strings.
- **Affects UI:** If the console surfaces `route_for_agent` suggestions, map `cap:code:*` → real tool names at the bridge. `route()` intent strings (search/symbol/history/health/architecture) are a useful NL-intent classifier worth reusing for the console command/search bar.

### F-41 — `audit(refresh=True)` silent sub-indexer swallow (F-24 knock-on, item B — decision recorded)
- **Verdict:** Confirmed `stack/audit.py:17-21` wraps `nextjs.index_routes` + `prisma.index_stack` in bare `try/except Exception: pass` — if either fails, rules query **empty** `routes`/`models` tables and report "clean". **Recommendation:** new bridge must call `nextjs.index_routes` / `prisma.index_stack` as an explicit "prepare stack" step (ISSUE-106) with errors surfaced (failed sub-indexers + traceback), not rely on `audit()`'s silent swallow. Do not route console audit through `audit(refresh=True)` for stack prep.
- **Cross-ref:** F-24, CORE-28, ISSUE-106.

### F-42B — Test baseline re-established (item D): 10 failed / 90 passed / 1 skipped / 30 errors / 166.75s — **+1 error vs F-10**
- **Severity:** P3 (baseline delta) · **Area:** tests · **Status:** open (Agent 2, item D done)
- **Evidence:** `python -m pytest tests/` (2026-08-16, full run) → **10 failed, 90 passed, 1 skipped, 30 errors, 166.75s**. F-10 reference was 29 errors → **+1 error**. Breakdown:
  - Failed (10): `tests/test_integration.py` ×8 (`TypeError: expected...` — F-03 stale-signature family), `tests/terminal_dashboard/test_snapshots.py` ×2 (Textual snapshot mismatches).
  - Errors (30): `tests/terminal_dashboard/` ×21 (`test_coverage_improvement` 6 + `test_full_coverage` 13 + `test_interactions` 2 — out of scope, legacy TUI, F-10), `tests/test_integration.py` ×9 (`PermissionError` — the F-03 `sync(con,cfg)` signature fix has NOT landed, so integration tests still can't create their temp repo).
- **Cross-ref:** F-03, F-10, CORE-7.
- **Affects UI:** Test gate remains red on the same F-03 root cause; no NEW failure category appeared this run. Only actionable delta signal = integration `PermissionError` persists until the F-03 test/`sync()` signature fix lands in lockstep with BUG-001.

### F-42 — F-22 root cause CORRECTED: resolver logic is broken, not stale `all_paths`; `sync_global/backups` pollutes 76% of the index; F-23 superseded (tested_by edges now exist but are noise)
- **Severity:** P1 · **Area:** index / audit · **Status:** open (Agent 1)
- **Evidence:** Re-investigated F-22/F-23 on the live DB (which has been re-synced since those entries: `file_imports` 5276, `imports` edges 12, `tested_by` edges 4462). Three things:
  1. **F-22's "stale/empty `all_paths`" hypothesis is WRONG.** `_sync_body` (`indexer.py:298`) does `all_paths = set(known)` then adds new files (`:329`) and removes deleted (`:372`) — the full path set. Runtime-verified `resolve_import('lib/cipkg/store.py', '.base', all_paths)` → **None** even though `lib/cipkg/base.py` IS in `all_paths`. **The real bug is the relative branch (`:42-46`):** `os.path.normpath(os.path.join(os.path.dirname(src_path), spec))` produces `lib/cipkg/.base` for `.base` (the leading dot is kept as a literal path segment) and `lib/cipkg/stack/..base` for `..base` (normpath treats `..base` as one segment, not `..`+`base`). So **relative imports can never resolve** — verified: `cands = ['lib/cipkg/.base', 'lib/cipkg/.base.py', …]`, none exist. This also explains why the earlier simulation showed 0/234: it wasn't stale data, it's the join bug.
  2. **Verified fix (simulated, not applied):** strip leading dots and count levels before joining → `lib/cipkg/base.py` for both `.base` and `..base`; total resolution 0.2% → **43.7%** (relative 0% → **72.7%**, absolute 0.4% → 23.9%). Remaining failures are genuinely external (stdlib 2117, e.g. `os`/`sys`/`json`; third-party ~1004, e.g. `textual.widgets`; plus top in-repo abs fails like `cipkg.base` 210 → needs `lib/` prefix). Target >90% is unreachable for this repo (external imports dominate) — realistic target: 100% of in-repo imports.
  3. **NEW root contributor: `sync_global/backups/` pollutes the index.** 575/753 indexed files (76%) live under `sync_global/backups/*` (dated backup copies of the repo from `sync_global`). `iter_files`/`iter_files_smart` only exclude `DEFAULT_EXCLUDES` + `cfg["index"]["exclude"]` (`base.py:164-207`); `sync_global/backups` is in neither. The repo-level config file is `config.default.toml` (uses `exclude_patterns` — ignored, see CORE-39), not `config.json`/`.cip/config.toml` (which don't exist here). So the index is majority stale backups — symbol/edge counts and import resolution are distorted by duplicate backup copies of the same code.
  4. **F-23 superseded:** `tested_by` edges now exist (4462) because `build_tested_by` (`indexer.py:220-249`) fires its name-mention heuristic (`:234-239`) against chunk text — but the edges are NOISE: e.g. `python://sync_global/backups/backup_.../selftest.py#tearDown` → `lib/cipkg/test_embed.py`; dst is a **path** (`test_embed.py`), not a symbol id, and many src symbols come from backup copies. QA-UNTESTED-HOT's "no tested_by edge" signal is now FALSE-POSITIVE-FREE only in the opposite direction — the 4462 edges are mostly spurious matches, not real test coverage.
- **Cross-ref:** F-22 (root cause now corrected), F-23 (superseded), CORE-39 (config key mismatch → backups not excluded), CORE-40 (schema version drift).
- **Affects UI:** (1) Fix `resolve_import` relative branch (strip leading dots, count levels) + add `lib/` prefix for absolute — this is the highest-value fix in the index path. (2) Add `backups`/`sync_global/backups` to excludes (fix CORE-39 key mapping) and re-sync — until then all graph/edge/search signals are computed on a 76%-duplicate index. (3) Rework `build_tested_by` to resolve imports first (via fixed resolver) and stop name-mention matching against `chunks.text` (or gate it to non-backup paths). (4) QA-UNTESTED-HOT's current 30 findings were generated BEFORE re-sync; after re-sync + fixes, re-run to confirm the signal becomes meaningful.


## 6. Merge notes & ownership
- **This file (`09-bugs-and-issues.md`) is now the single rolling scratch log.** `cip-findings.md` (repo root)
  was the earlier scratch log and is **superseded** (kept for history; do not append new F-entries there).
- New backend findings are appended directly here. F-ids are stable and continue from the last used id
  (currently **F-42**, owned by Agent 1; Agent 1 owns F-31..F-33 + F-42, Agent 2 owns F-34..F-41 — user
  coordinates allocation). New findings that overlap existing BUG-xxx / CORE-xxx get a `Cross-ref:` line.
- **Deep-read status (updated 2026-08-16):** NOT complete. Read this pass: `web_server.py` (full 588 lines —
  caught F-21), `stack/rules.py` + `stack/{common,custom_rules,audit,prisma,nextjs}.py`, `detect.py`, `parse.py`,
  `tree_parser.py`, `indexer.py` (link/resolve/sync paths), full `docs/dev/09` re-read, **plus this pass:**
  `command_adapter.py` (full 475), `interactive.py` (full 325), importer-graph trace for both + `interactive_ui.py`,
  `help_system.py` (full 247; runtime-verified both entry functions crash), **`hooks.py` (full 173) +
  `stack/impact.py` `impact()` + `stack/audit.py` `findings()` + `cli.py` `handle_hook_command` +
  `command_registry.py` `_handle_hook` (all runtime-verified)**.
  Prior passes covered:
  `workflow_engine.py`, `error_system.py`, `intelligent_executor.py`, `command_registry.py`, `cli.py`,
  `retrieve.py`, `context_manager.py`, `bin/cip.py`, `repo-settings/`, `server.py`, `learning.py`,
  `gatekeeper.py`, `daemon.py`, `memory/{episodic,temporal_graph,consolidation}.py`, `suggestion_engine.py`,
  `sync_global/` (root, not `lib/cipkg/sync_global/` — AGENTS.md path is wrong). **Now fully read:**
  the F-25 "still unread" list is exhausted — Agent 1 read `session.py`, `runtime_adapters.py`,
  `watcher.py`, `repo_map.py`, `rerank.py`, `vecstore.py`, `scip_indexer.py` (F-31..F-33); Agent 2 read
  `router.py`, `websocket_handler.py`, `dashboard_state.py`, `dashboard.py`, `dependency_checker.py`,
  `lock.py`, `stack/selftest.py`, `parsers.py`, `tsconfig.py`, `stack/common.py`, `stack/custom_rules.py`
  (F-34..F-41). **Only remaining unread module:** `interactive_ui.py` (contents not read — importer-graph
  only verified dead via F-28; no need to read since its sole importer is dead). Findings this pass: F-21 (hybrid_search), F-22
  (import resolution ~99% fails — root cause), F-23 (tested_by always empty), F-24 (rules dry-run), F-25
  (coverage-map correction), F-26 (command_adapter dead + faked-success placeholder), F-27 (interactive
  unreachable, help advertises nonexistent `cip interactive`), F-28 (interactive_ui dead via F-27),
  F-29 (help_system dead + both entry fns crash; line count 247 not 236), **F-30 (post_edit_hook reads
  non-existent impact keys → always-zero impact summary + `" callees"` typo + root drop)**.
  **Agent 1 (this thread) continued:** `session.py` (full 199) + `retrieve.py` runtime_adapters attribute
  check + `summarize.map_` return shape + `learning.update_prediction_confidence` + `verify` signature +
  `cli.py` session dispatch + `command_registry.py` session cards + `runtime_adapters.broken` (all
  runtime-verified) → **F-31 (session context packet silently empty: `retrieve.runtime_adapters` missing,
  `map_` key mismatch)**. Agent 1 continued: `runtime_adapters.py` (full 99, VERIFIED CLEAN) + `watcher.py`
  (full 114, zero importers + `mark_for_reindex` missing) + `watch.py` (full 34, the ACTIVE daemon watcher) →
  **F-32 (watcher.py dead + broken; CORE-16/57 satisfied by watch.py)**. Agent 1 continued: `repo_map.py` +
  `rerank.py` + `vecstore.py` + `scip_indexer.py` (full reads + runtime probes of rerank/vecstore) →
  **F-33 (repo_map + scip_indexer DEAD; rerank + vecstore LIVE + verified clean)**. **Agent 2 (parallel slip)
  continued** (runtime-verified where possible): `router.py` (full 182) + `websocket_handler.py` (full 183) +
  `dashboard_state.py` (full 180) + `dashboard.py` (full 122) + small leaves `parsers.py`/`tsconfig.py`/
  `dependency_checker.py`/`lock.py`/`stack/{selftest,common,custom_rules}.py` → **F-34 (`cip selftest` crash:
  `from .selftest import selftest` vs module only defines `run_selftest`), F-35 (dependency_checker orphaned:
  `handle_deps_command` never imported by cli), F-36 (`stack/selftest.run_stack_selftest` zero callers),
  F-37 (dashboard_state zero importers — dead), F-38 (dashboard.py unreachable via CLI; `briefing()` =
  CORE-51 oracle input — extract to `stack/briefing.py`), F-39 (websocket_handler legacy; emitter uses
  `asyncio.create_task` from sync context; protocol = CORE-57 model only), F-40 (router VERIFIED CLEAN with
  `cap:code:*` caveat), F-41 (F-24 knock-on decision: explicit "prepare stack" step; never route console
  audit through `audit(refresh=True)`)**. Agent 2 item D (pytest baseline) **aborted by user** — F-10
  remains the reference baseline. **Agent 2 slip COMPLETE except item D.**
- **Scope decision (2026-08-16):** legacy web layer (`web_server.py` routes, `static/js/*`, `dashboard.py`,
  `dashboard_state.py`, `websocket_handler.py`) is being **rebuilt from scratch** — do not spend further
  passes auditing its frontend contract. Web-side entries (BUG-001..004, F-21) remain as fix-in-bridge
  references so the new bridge never copies their stale calls.

### CORE-31 — `run_consolidation_daemon` is a blocking loop with no stop (SPEC-08)
- **Severity:** P2 · **Area:** memory · **Status:** fix-in-bridge
- **Evidence:** `memory/consolidation.py:132` blocking `while` loop.
- **Affects UI:** Must run in managed thread/process with stop flag (like CORE-16).

### CORE-32 — consolidation db_path collision: one shared db vs separate memory.db/episodes.db (SPEC-08)
- **Severity:** P1 · **Area:** memory · **Status:** verify-before-wiring
- **Evidence:** `consolidation.py:17-18` single `db_path` for graph+episodic; `learning_system.py:693-706` separate files.
- **Affects UI:** Consolidation may query empty episodic table; verify correct path before wiring.

### CORE-33 — semantic recall is NOT semantic: facts match by exact command tag (SPEC-08)
- **Severity:** P3 · **Area:** memory · **Status:** open
- **Evidence:** `learning_system.py:813-816` `predicate=f"command:{query[:50]}"`.
- **Affects UI:** Copy must say "facts match by command tag", not semantic recall.

### CORE-34 — memory files sit outside index lifecycle (no sync/vacuum/backup coverage) (SPEC-08)
- **Severity:** P3 · **Area:** memory · **Status:** open
- **Evidence:** `learning_system.py:98` `data_dir(root)/learning_data`; SPEC-04 vacuum covers index.db only.
- **Affects UI:** Show memory disk usage + last write; document vacuum does not prune memory.

### CORE-35 — `git_index` destructively rewrites commits/co_change tables (subprocess, 180 s cap) (SPEC-09)
- **Severity:** P2 · **Area:** git · **Status:** fix-in-bridge
- **Evidence:** `gitindex.py:30-32` DELETE all; `git log` subprocess timeout 180.
- **Affects UI:** Must be a background job with progress + confirm; C1–C3 show "indexing" while running.

### CORE-36 — no per-commit delta lines; churn uses file size proxy (SPEC-09)
- **Severity:** P3 · **Area:** git · **Status:** open
- **Evidence:** `store.py:46` commits table lacks line deltas; `gitindex.hotspots` uses recency weight.
- **Affects UI:** C2 y-axis = hotspot.score (recency-weighted), not raw churn; label honestly.

### CORE-37 — snapshot trends depend on all three job types writing snapshots (SPEC-09)
- **Severity:** P2 · **Area:** snapshots · **Status:** cross-cutting
- **Evidence:** SPEC-04 §5 writer; B1/D2 break if sync/audit/consolidate skip it.
- **Affects UI:** Enforce snapshot write at each job completion hook.

### CORE-38 — E1 graph payload N+1 risk when decorating nodes (SPEC-09)
- **Severity:** P2 · **Area:** graph · **Status:** fix-in-bridge
- **Evidence:** `retrieve.py:265` ids only; per-node metadata needs batch lookups.
- **Affects UI:** `graph_payload` must batch IN lookups (SPEC-15) to stay render-friendly.

### CORE-39 — config key mismatch: `exclude_patterns`/`max_file_size` in TOML vs `exclude`/`max_file_kb` read by core (SPEC-10)
- **Severity:** P1 · **Area:** config · **Status:** open
- **Evidence:** `config.default.toml:10,28` `exclude_patterns`/`max_file_size` (bytes); `gatekeeper.py:114-116` and `base.py:42,173-174` read `exclude`/`max_file_kb`. TOML excludes + size cap silently ignored.
- **Affects UI:** Indexer excludes nothing beyond `.git/.cip` unless users know undocumented `exclude`; settings schema must reconcile (map or rename).

### CORE-40 — `[meta] schema_version=11` in config vs live DB schema_version=4 (SPEC-10)
- **Severity:** P1 · **Area:** config · **Status:** open
- **Evidence:** `config.default.toml:6` = 11; `store.py:5` = 4; live DB = 4 (CORE-3).
- **Affects UI:** Settings must show live DB version; don't trust config meta; offer schema upgrade.

### CORE-41 — `load_config` repo-profile auto-detect silently swallows failures (SPEC-10)
- **Severity:** P2 · **Area:** config · **Status:** open
- **Evidence:** `base.py:114-146` bare `except: pass` on `repo-settings/detectors` import.
- **Affects UI:** Broken profile silently hides intended includes/excludes; settings shows profile source + errors.

### CORE-42 — duplicate/legacy perf & analysis config keys (`[perf]` vs `[performance]`, `health_weights` vs legacy) (SPEC-10)
- **Severity:** P3 · **Area:** config · **Status:** open
- **Evidence:** `config.default.toml:149-160` `[analysis] health_weights`, `[performance] worker_threads`; `[perf] workers`; code reads `cfg["perf"]["workers"]` (indexer) and `[analysis]` weights.
- **Affects UI:** Which wins is ambiguous; schema must reconcile duplicates + mark legacy keys deprecated.

### CORE-43 — `export.export` prints to stdout and returns only `{bytes}` (SPEC-11)
- **Severity:** P2 · **Area:** export · **Status:** fix-in-bridge
- **Evidence:** `export.py:16-17` `print(text)`; return lacks content.
- **Affects UI:** Bridge must capture output (temp out / generator) for streamed downloads.

### CORE-44 — `_lsif`/`_json_dump` load all rows into memory (SPEC-11)
- **Severity:** P3 · **Area:** export · **Status:** fix-in-bridge
- **Evidence:** `export.py:19-60` list comprehensions over full tables.
- **Affects UI:** Cap export size with warning or chunk per table for big repos.

### CORE-45 — `verify._run_typecheck/_run_lint` silently degrade when runner missing (SPEC-11)
- **Severity:** P2 · **Area:** verify · **Status:** fix-in-bridge
- **Evidence:** `verify.py:80,102` subprocess via PATH, ad-hoc detection.
- **Affects UI:** Verify job must report "runner not found" explicitly.

### CORE-46 — `signals` ingest no idempotency; repeated pastes duplicate rows (SPEC-11)
- **Severity:** P2 · **Area:** signals · **Status:** fix-in-bridge
- **Evidence:** `store.py:51` PK is caller-supplied id.
- **Affects UI:** Bridge parser must generate stable hash ids so re-ingest upserts.

### CORE-47 — two freshness definitions: `init_detector` 1h mtime vs `server.index_status` <300s (SPEC-12)
- **Severity:** P2 · **Area:** onboarding · **Status:** fix-in-bridge
- **Evidence:** `init_detector.py:142-155` age_hours<1; `server.py` freshness <300s.
- **Affects UI:** Use one freshness source (SPEC-01 status); treat init_detector.index_fresh as advisory.

### CORE-48 — wizard must never overwrite existing AGENTS.md (SPEC-12)
- **Severity:** P2 · **Area:** onboarding · **Status:** safe-guard
- **Evidence:** `init_detector.py:59` agents_file read; install write path.
- **Affects UI:** Write AGENTS.md only when absent.

### CORE-49 — `_detect_repo` is heuristic; suggested config can be wrong (SPEC-12)
- **Severity:** P3 · **Area:** onboarding · **Status:** open
- **Evidence:** `init_detector.py:159+` file-count heuristics.
- **Affects UI:** Wizard suggestions must be fully editable (manual override) — grounds §7.1-3.

### CORE-50 — install path duplication: `cip init` (CLI) vs bridge `onboarding_install` (SPEC-12)
- **Severity:** P2 · **Area:** onboarding · **Status:** verify-at-integration
- **Evidence:** `__init__.py`/`cli.py` init vs new bridge writer.
- **Affects UI:** Reuse core install or mirror same defaults to avoid config drift.

### CORE-51 — `dashboard.py:briefing` lives in legacy TUI module; oracle needs it cleanly (SPEC-13)
- **Severity:** P2 · **Area:** oracle · **Status:** fix-in-bridge
- **Evidence:** `dashboard.py` briefing (§7.1-16); import may pull curses/rich.
- **Affects UI:** Extract briefing to leaf module or lazy-import with fallback.

### CORE-52 — `SuggestionEngine` swallows analyzer failures + prints to stdout (SPEC-13)
- **Severity:** P2 · **Area:** oracle · **Status:** fix-in-bridge
- **Evidence:** `suggestion_engine.py:636-659` `print(f"Warning: Analyzer ... failed")`.
- **Affects UI:** Capture analyzer status for "why" tooltip; log via log_swallowed, not print.

### CORE-53 — `predict_next_context` confidences are hardcoded, not learning-adjusted (SPEC-13)
- **Severity:** P3 · **Area:** predict · **Status:** open
- **Evidence:** `predict.py:19-60` static confidence values; docstring claims learning adjustments.
- **Affects UI:** Label confidence "estimated"; tie to learning only when real.

### CORE-54 — workflow execution persistence unknown (SPEC-13)
- **Severity:** P3 · **Area:** workflows · **Status:** verify-at-integration
- **Evidence:** `workflow_engine.py:124` StateManager/WorkflowExecution.
- **Affects UI:** Record run history in `events` if core doesn't persist.

### CORE-55 — `events` sync payload is `str(stats)` (Python repr), not JSON (SPEC-14)
- **Severity:** P2 · **Area:** events · **Status:** fix-in-bridge
- **Evidence:** `indexer.py:401` `payload=str(stats)`.
- **Affects UI:** Bridge event writer uses JSON payloads; don't JSON-parse legacy sync rows.

### CORE-56 — no scan-phase progress; `_sync_body` only emits link/embed phases (SPEC-14)
- **Severity:** P3 · **Area:** index · **Status:** open
- **Evidence:** `indexer.py:385-394` scan prints only; progress("link"/"embed") only.
- **Affects UI:** Job bar jumps at link; don't claim scan progress.

### CORE-57 — blocking loops (watch/consolidation daemon) must not run on WS event loop (SPEC-14)
- **Severity:** P2 · **Area:** realtime · **Status:** cross-cutting
- **Evidence:** `watch.py:14`, `consolidation.py:132`; CORE-16/CORE-31.
- **Affects UI:** Managed threads/processes publish events; never on ASGI loop.

### CORE-58 — read-only UI connections create DB file if absent (SPEC-15)
- **Severity:** P2 · **Area:** store · **Status:** fix-in-bridge
- **Evidence:** `store.connect` CREATE IF NOT EXISTS; onboarding reads before install.
- **Affects UI:** Read paths must not write; wizard creates `.cip` explicitly first.

### CORE-59 — legacy `server.py` JSON-RPC (8080) overlaps new REST (8090); MCP port collision risk (SPEC-15)
- **Severity:** P2 · **Area:** runtime · **Status:** open
- **Evidence:** `[mcp] port=8080`, `[web]` absent (CORE-1); NFR-1 one port.
- **Affects UI:** Isolate ports; console may expose MCP tools via SPEC-02 without auto-start clash.

### CORE-60 — concurrent snapshot writes need serialization (WriteLock discipline) (SPEC-15)
- **Severity:** P2 · **Area:** snapshots · **Status:** fix-in-bridge
- **Evidence:** SPEC-04 §5 writer called from multiple job completion hooks.
- **Affects UI:** Queue snapshot writes via JobRunner or serialize on a lock (NFR-2).

---

## 7. Legacy frontend removal process (Agent 2 ownership)
**Decision (2026-08-16, user directive):** the legacy frontend/server surface is fully deprecated — the
new console is built from scratch. Nothing on the remove-list below is worth saving; log findings and
remove. This is the canonical cleanup process for old-frontend code.

### 7.1 Remove-list (disposition per surface)
| Surface | Disposition | Evidence |
|---|---|---|
| `web_server.py` (588) | delete (legacy split-brain web) | BUG-001..004, F-21 |
| `static/` (`dashboard.html`, `css/`, `js/`, `lib/`) | delete (no build step, hand-rolled) | BUG-025 |
| `dashboard.py` (122) | delete **after extracting `briefing()` → `stack/briefing.py`** | F-38, CORE-51, BUG-004 |
| `dashboard_state.py` (180) | delete (dead) | F-37 |
| `websocket_handler.py` (183) | delete (reuse only its subscribe/publish topic protocol as a MODEL) | F-39, CORE-57 |
| `terminal_dashboard.py` (40.8K) | delete (TUI; `bin/cip.py:143` importer) | F-10, F-16 note |
| `interactive.py` / `interactive_ui.py` / `help_system.py` / `command_adapter.py` | delete (dead cluster) | F-26/F-27/F-28/F-29 |
| `server.py` HTTP `serve()` | deprecate HTTP JSON-RPC; **keep `mcp_stdio()`** (MCP agent surface) | CORE-59 |
| `dependency_checker.py` | delete **or** wire `handle_deps_command` into cli | F-35 |
| `stack/selftest.py` | delete **or** wire `run_stack_selftest` | F-36 |
| legacy tests: `tests/terminal_dashboard/` + root `conftest.py` Textual coupling | delete; remove Textual import requirement | F-10 |

### 7.2 Removal process (steps)
1. **Freeze:** stop extending any remove-list file; add `## LEGACY — DO NOT REUSE` header comment as they get touched.
2. **Extract-first:** move `briefing()` (CORE-51) and the WS topic protocol (CORE-57) into leaf modules **before** deleting their hosts.
3. **Remove in dependency order:** leaves first (dead cluster F-26..F-29), then TUI (`terminal_dashboard.py`), then HTTP servers (`dashboard.py` serve, `web_server.py`), then `static/` assets last.
4. **Chip away CLI/registry references in the same commit as each removal** (`dashboard`/`dashboard-web` parsers `cli.py:590-593`, dispatch `cli.py:709`, registry cards `command_registry.py:480,847`); otherwise `cip X` silently returns "unknown command".
5. **Delete legacy tests + root-conftest Textual coupling** so backend tests run without `textual` (F-10).
6. **Keep `mcp_stdio()`** (MCP stdio for agent integration) unless the bridge replaces it; do NOT keep HTTP JSON-RPC `serve()`.
7. **Verify:** re-run `python -m pytest tests/` for the baseline delta (F-10) and `python -m pyflakes lib/cipkg` after deletions.
