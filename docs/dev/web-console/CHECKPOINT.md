# CHECKPOINT — CIP Web Console Build (session state)

**Folder:** `docs/dev/web-console/` · **Date:** 2026-08-17
**Purpose:** canonical anti-erasure anchor (RUNBOOK.md §2, AGENTS.md 120K rule). If autocompaction
fires, THIS + BUILD.md are the only truth a fresh agent needs. **Docs win over memory.**

---

## Current position

- **Build:** CIP Web Console v1 — fresh React/Vite frontend + FastAPI backend (`web_bridge.py`) on port 8090.
- **Stack decided (user-confirmed):** Bun (NOT npm) for the frontend; Tailwind CSS 4; dark dev-tool theme.
- **Done (14 units — ALL):** SPEC-01 App Shell · SPEC-02 Command Center · SPEC-14 WS contract · SPEC-03 Daemon
  & Server Mgmt · SPEC-04 Index Management · SPEC-05 Search & Navigation · SPEC-06 Deep File Panel ·
  SPEC-07 Quality & Audit · SPEC-08 Memory Lab · SPEC-09 Visualization Suite · SPEC-10 Settings & Config ·
  **SPEC-11 Export & Integration** · **SPEC-12 Onboarding Wizard** · **SPEC-13 Oracle Surface** ·
  **SPEC-15 Cross-cutting NFRs**.
- **Build status: COMPLETE** — all 15 BUILD.md rows `done`; milestone gate items all green.
- **Post-completion: §4 ledger closed** (4 pledged backend additions shipped + `GET /api/snapshots` +
  watch endpoints → route count **72 → 76**). See "§4 ledger closed" section below.
- **GAP Remediation (Wave 3-4, 2026-08-17):** 4 gaps FIXED, 2 SKIPPED (low priority). See "GAP Remediation" section below.
- **Backend live:** 89 `/api` REST endpoints register (68 after SPEC-12 → **+4 SPEC-13 = 72** →
  **+4 ledger-close = 76** → **+13 gap remediation = 89**). Recount
  authority: route-set dedupe of `{METHOD path}` on `/api/*`. Series: 48 (SPEC-08) → 55 (SPEC-09) →
  62 (SPEC-10) → 67 (SPEC-11) → 68 (SPEC-12) → 72 (SPEC-13) → 76 (ledger close) → 89 (GAP remediation).
- **Frontend live:** NO placeholder routes remain — every nav destination is a real view (11 now:
  `/oracle` added). 3D code graph ships lazy (own 555KB chunk, loads only on Code Graph tab). Recharts
  3.10, `three@0.185`. First-run gate: `/` shows the onboarding wizard when `needs_onboarding` and the
  gate hasn't been skipped.
- **Frontend live:** NO placeholder routes remain — every nav destination is a real view. 3D code graph
  ships lazy (own 555KB chunk, loads only on Code Graph tab). Recharts 3.10, `three@0.185`.

## GAP Remediation (Wave 3-4, 2026-08-17)

**Reference:** `MASTER-FIX-PLAN.md` + `GAP-REPORT.md`

**Completed (4 FIXED, 2 SKIPPED):**
- **GAP-08** (FIXED): Trend charts read snapshots instead of vacuumed events. Added `_snapshot_series` function, `_events_series_snapshots_first` fallback, repointed `/api/vis/trends` and `/api/quality/trends`, added `/api/vis/snapshots` endpoint.
- **GAP-05** (FIXED): Quickwins GET endpoint. Changed `POST /api/quality/quickwins` to `GET`, added `auditApi.quickWins(limit)` to frontend, wired QualityView to query separately.
- **GAP-09** (FIXED): Oracle runnable actions + workflow browser. Added `/api/oracle/workflows` + `/api/oracle/workflows/{id}/run` backend endpoints, added `oracleApi.workflows/workflowRun`, made OracleView NextContextCard predictions clickable buttons that navigate to appropriate surfaces.
- **GAP-11** (FIXED): Search deep filters tier/kind in UI. Added tier (code/test/config) and kind (class/function/method/variable) dropdown filters to SearchView, wired search query to pass tier/kind params to backend.
- **GAP-10** (SKIPPED): Memory point-in-time slider. Low priority; deferred to future iteration.
- **GAP-12** (SKIPPED): Daemon auto-manage toggle. Low priority; deferred to future iteration.

**Verification:**
- Backend: 89 routes (was 76), all imports clean
- Frontend: `npx tsc --noEmit` silent, `bun run build` clean
- Documentation: GAP-REPORT.md updated (6 FIXED, 2 SKIPPED), MASTER-FIX-PLAN.md updated

## Commands that work

```powershell
cd web; npx tsc --noEmit                 # silent = pass
cd web; bun run build                    # → web/dist (Monaco + CodeGraph3D code-split)
cd lib; python -m uvicorn cipkg.web_bridge:app --port 8090   # service
```

## Files

- `web/` — Vite + React 19 + TS 6 + Tailwind 4. Added this unit: `src/views/ExportView.tsx`
  (download cards for repo/findings/index in JSON+Markdown, search-export with query gate, MCP+daemon+
  index status cards, color-coded reachability, MCP tools schema viewer with collapsible param tables,
  signal ingest panel with kind chips, verification gate buttons), `src/lib/api.ts` `exportApi`
  (`status`, `tools`, `downloadUrl`, `ingest`, `verify`). `/export` wired in App.tsx.
- `lib/cipkg/web_bridge.py` — FastAPI app. Added this unit (SPEC-11 block after `/api/env`):
  `_export_payload` (kind repo via `export._json_dump`; findings via `stack.audit.findings`;
  index via `_overview_builder`; search via `retrieve.rrf([lex_search(con,q),[]])` + row re-hydration),
  `_payload_to_markdown` (read-only Markdown renderer per kind), `_findings_export`, `export_endpoint`
  (kind/format validation → `Response` attachment with `Content-Disposition`), `export_status_endpoint`
  (socket probes to MCP 8080/daemon 8765, index counts), `export_tools_endpoint` (MCP tools schema from
  CLI parser, shared `_command_registry` with `/api/commands`), `export_ingest_endpoint` (delegates to
  `runtime_adapters.ingest_*`, pytest via temp JUnit XML, stable ids CORE-46), `verify_gate_endpoint`
  (`verify.verify` as a thread job → `can_proceed`/`blocked_by` over WS). New pydantic models
  `IngestRequest`/`VerifyRequest`. Imported `Response` from fastapi.responses.
- `config.default.toml` — **product fix:** `health_weights` multiline inline table (TOML 1.1, invalid
  for Python `tomllib`) collapsed to one line; the WHOLE file now parses, so `memory/web/mcp/daemon/
  analysis/…` sections finally load into `DEFAULT_CONFIG` (previously silently dropped).
- `lib/cipkg/daemon.py`, `lib/cipkg/cli.py` (`cip web`), `config.default.toml` (`[web]`).
- `docs/dev/web-console/RUNBOOK.md` + `BUILD.md` (tracker, SPEC-11+12+13 rows `done`) + this file.
- SPEC-12 adds: `web/src/views/OnboardingView.tsx` (wizard stepper), `web/src/App.tsx` (first-run gate +
  Splash), `web/src/components/layout/AppShell.tsx` (gate moved out), `web/src/lib/api.ts`
  (`onboardingApi` + types), `lib/cipkg/web_bridge.py` (`_onboarding_state_dict` +
  `GET /api/onboarding/status`), `lib/cipkg/init_detector.py` (framework-loop fix).
- SPEC-13 adds: `web/src/views/OracleView.tsx` (repo story / file summary / edit context / predict),
  `web/src/lib/api.ts` (`oracleApi` + types), `web/src/components/layout/LeftNav.tsx` (`/oracle`),
  `web/src/App.tsx` (`/oracle` route), `lib/cipkg/web_bridge.py` (4 oracle endpoints +
  `_oracle_ready`/`_oracle_no_index`).

## Decisions logged

- **3D graph stack (SPEC-09):** raw `three` (+ OrbitControls + CSS2DRenderer from examples) — NOT
  `@react-three/fiber`/drei. Leaner, no React-19 reconciler version risk. `React.lazy` code-split →
  555KB chunk only on the Code Graph tab. Prefer this pattern over adding fiber for future 3D.
- **Vis cache invalidation (SPEC-09 §6.5):** per-group `_VIS_CACHE[key] = {ts, data, ev}` where
  `ev = max(events.ts)`; request reuses cached data only if `ts` fresh AND `ev` unchanged. This means
  the sync/audit/consolidate jobs need NO changes to refresh charts (they already write events).
- **Config write-back (SPEC-10):** `POST /api/config/save` merges `{section:{key:value}}` into the
  existing `.cip/config.toml` via tomlkit (preserves comments), writes `.bak` then atomic
  `.tmp`+`os.replace`. `GET /api/config` stays as the sanitized legacy; rich three-way lives at
  `/api/config/full`; schema drives the form at `/api/config/schema` (server = source of truth).
- **Key safety (CORE-39):** `_apply_updates_to_doc` REJECTS unknown keys (never writes a key core
  ignores), maps deprecated aliases live (`exclude_patterns→exclude`, `max_file_size→max_file_kb`,
  `performance.worker_threads→perf.workers`), enforces type/choices/range server-side. Deprecated
  keys show `[deprecated…]` descriptions in the schema so CORE-42 is visible, not hidden.
- **CORE-40 handling:** schema + env return `live_schema_version` read from the DB meta table, NOT
  from config `[meta].schema_version` (which lies at 11); SettingsView shows the live value.
- **FastAPI body gotcha:** a bare `updates: dict` param is parsed as a QUERY param (silently empty
  body); POST bodies MUST use Pydantic `BaseModel` (matches `AuditRequest`/`MemoryActionRequest`).
- **Modal test residue:** running save/reset smoke against a real ROOT writes `.cip/config.toml`;
  after smoke, delete it + `.bak` (it does not exist in the repo state).
- **SPE-11 export gotchas:** (1) `retrieve.lex_search` returns row DICTS (id/path/symbol_id/start_line/
  end_line/snip) — there are no `(cid, score)` tuples; use `retrieve.rrf([lex, []])[:k]` to get scored
  tuples for an export (mirrors `/api/search`). (2) If you hand-roll a SELECT for export rows, list every
  column the UI needs (`start_line` AND `end_line`) — sqlite3.Row raises `IndexError: No item with that
  key` on missing columns. (3) Ingest smoke writes a real signal row + `ingest:<kind>` event to the index
  DB — delete them after (cleanup ran post-smoke). (4) `sub.help` does NOT exist on argparse SubParsers
  (AttributeError) — use `sub.description` only; the same bug was in the pre-existing `/api/commands`.
- **Command registry sharing:** `_command_registry()` extracted from `/api/commands` so
  `/api/export/tools` (MCP tools schema) reuses the exact SPEC-02 dispatch table — one source of truth.
- **`_parse_payload` (CORE-37 sibling):** core `indexer.py:440` writes sync event payloads via
  `str(stats)` (Python repr, single quotes); quality/memory events are true JSON. `_events_series`
  and the git C4 feed must use `_parse_payload` — `json.loads` alone throws `Expecting property name`.
- **Graph URL-encode gotcha:** symbol ids are `python://…/#…` — the `#` truncates the query string if
  raw. Frontend `vizApi.graph` already `encodeURIComponent`s; smoke tests must too.
- **Embed-model safety rule (user-mandated):** the web path must NEVER load an embedding model and
  NEVER auto-start the embed daemon. Do not call `retrieve.search`/`vec_search`/`get_embedder`/
  `_ensure_embedded` from web_bridge. `_warm_daemon()` (≤0.5s probe) gates any vector enrichment.
- **Monaco integration:** 0.56 ships no `.esm/vs` worker files; worker imports MUST use the exports-map
  path (`monaco-editor/editor/editor.worker?worker`). Code-split via `React.lazy`.
- **CORE-32 memory db split:** memory.db + episodes.db separate files; consolidate JOB adapter reads
  episodes from `episodes.db`; NEVER call `MemoryConsolidator.consolidate()` directly (empty episodes).
- **CORE-33:** fact/recall matching is keyword/command-tag, not semantic; UI states "Embedding: no".
- Job-closure gotcha: `connect` is NOT module-level — import INSIDE closures (`from .store import
  connect`); `global` for cache resets.
- CORE-10 port drift NOT resolved in config; UI surfaces physical port from `.cip/data/daemon.port`.

## CORE-10 runtime consolidation complete (2026-08-17, follow-up session)

- **One truth helper:** `embed.service_port(cfg)` — `[embed].service_port` → `[serve].port` → 8787.
  All runtime consumers now resolve through it (see BUILD.md §5a). `[daemon].port=8765` left in the
  TOML untouched as intentional CONFIG-PORT-MISMATCH doctor recall evidence (config value is test
  evidence, never a runtime consumer).
- **Consumers rewired this pass:** `/api/status` daemon probe + response `daemon.port` (was hardcoded
  8765); `/api/env` `CIP_DAEMON_PORT` + `/api/export/status` + `/api/export/tools` (were stale
  `DEFAULT_CONFIG.get("daemon")` → 8765 fallback); `embed.find_daemon_port`/`get_embedder*` and
  `cli.cmd_embedder` (were `serve.port`, still honor `.cip/data/daemon.port` physical override).
- **Verified:** TestClient reports `daemon.port=8787`, `CIP_DAEMON_PORT=8787`, export daemon 8787;
  watch lifecycle settles (running → idle); 76 API routes unchanged; `npx tsc --noEmit` silent;
  `bun run build` clean; s4/s5 port precision/recall tests pass.
- **KNOWN PRE-EXISTING (not from this pass):** working-tree `config.default.toml` already edits
  `health_weights` → single-line + adds `[web]`, silencing `CONFIG-FILE-UNPARSEABLE` and
  `CONFIG-MISSING-SECTION` evidence → 6 s4/s5 recall tests fail. Port tests unaffected. Resolution
  deferred: reconcile the detector test evidence with the fixed `config.default.toml` in a later pass.

## SPEC-12 unit complete (2026-08-17, this session)

- **Backend:** `GET /api/onboarding/status` added to `web_bridge.py` after `/api/admission/explain`
  (anchor `# ── SPEC-05: Search & Navigation ──`). `_onboarding_state_dict()`:
  `InitDetector(ROOT).detect()` + `get_init_ui_text(state)` + (only if `state.index_exists`)
  `server.index_status(ROOT)`. Route count 67 → **68**.
- **Frontend:** `web/src/views/OnboardingView.tsx` (stepper: Repo / Config review / Index & verify /
  Done; starts at step 2 on `initialized_no_index`; ERROR card on `status==='error'`; step 0 = detection
  cards + recommendations; step 1 = config review via `settingsApi.bundle` `.effective`; step 2 =
  `indexApi.sync(false)` job + `indexApi.status` poll (3s) + admission tiers; completion effect →
  `onIndexed()` when `files > 0`; skip link; local helpers `InfoCard`/`RecList`/`EffectiveConfig`/
  `IndexSummary`/`fmtArr`). Removed unused `useRef`/`onboardingApi` imports after tsc flagged them.
- **Gate (SPEC-12 close, late addition):** `web/src/App.tsx` + `web/src/components/layout/AppShell.tsx`
  rewritten. `App` holds `useQuery(['onboarding'], onboardingApi.status)` with
  `refetchInterval: (q) => (q.state.data?.needs_onboarding ? 8_000 : false)` — **polls ONLY while
  gated** (InitDetector.detect walks the full tree for `file_count`, don't do it every 5s forever).
  `skipped` in localStorage key `cip:onboarding:skipped`; `needs_onboarding && !skipped` renders
  `<OnboardingView status onSkip onIndexed>` full-screen (no shell; shell mounts on success).
  `onIndexed` clears the skip key + `refetch()`. Loading → `<Splash/>`. AppShell no longer owns the gate.
- **Detector bug fixed (real):** `init_detector.py:269` `for framework, indicators in framework_files:`
  iterated a dict → `ValueError: too many values to unpack`, swallowed by the try/except at 204-207
  → **languages/frameworks always `[]`, repo_type always `generic`**. Fixed to `framework_files.items()`
  (mirrors the correct `.items()` at :255). Verified: ROOT now → `python-lib`, `['python',
  'javascript', 'typescript']`, `['pytest']`.
- **Verified (in-process TestClient, no live server):**
  - fresh temp repo → `not_initialized`, `needs_onboarding:true`, `indexed:false`, detection
    `python-lib`/`['python']`/`has_git:true`, 6 recommendations, **no `.cip` / `index.db` side
    effect created** (GET stays read-only; `detect()` is pure os probing + index_status only when
    `index_exists`).
  - real ROOT → `fully_initialized`, `indexed:true`, `needs_onboarding:false`,
    `detector_index_fresh:true`, `fresh:false` (last_sync >300s, CORE-47 authoritative), 5 recommendations.
  - `npx tsc --noEmit` silent · `bun run build` clean (+~10s, chunk-size warnings only for
    Monaco/editor.api — known/lazy) · backend import 68 routes.
- **Files:** `web/src/App.tsx`, `web/src/views/OnboardingView.tsx` (new), `web/src/lib/api.ts`
  (`onboardingApi` + `OnboardingStatus`/`RepoDetection`/`OnboardingState` types),
  `web/src/components/layout/AppShell.tsx`, `lib/cipkg/init_detector.py` (framework loop fix).
- **SPEC-13 Oracle Surface is next.**

## SPEC-13 unit complete (2026-08-17, this session)

- **Backend:** SPEC-13 block added to `web_bridge.py` after the SPEC-12 onboarding endpoints (before
  `# ── SPEC-05`). 4 read-only routes:
  - `_oracle_ready()` — `os.path.isfile(cip_dir(ROOT)/data/index.db)` guard (GET NEVER creates the DB;
    mirrors SPEC-12 rule). `_oracle_no_index()` → `{ready:false, reason:"no_index", message:"Run a sync
    first — no index found yet."}`.
  - `GET /api/oracle/repo-summary` → `summarize.summary(ROOT)` (repo story) + `summarize.map_(ROOT)`
    (dirs/totals) + hotspots. Verified on ROOT: 754 files story, 9 dirs, 5 hotspots, source structural.
  - `GET /api/oracle/summary?path=` → `summarize.summary(ROOT, path or None)` (repo/dir/file dispatch;
    path="" → repo). Verified on `lib/cipkg/summarize.py`: 8 symbols, 3 imports.
  - `GET /api/oracle/suggest-context?file=` → `predict.suggest_context_for_edit(ROOT, file)`. Empty file →
    `_err("EMPTY_FILE")`. Verified: impact + warning suggestions.
  - `GET /api/oracle/next?operation=&symbol=&query=` → `predict.predict_next_context(ROOT, op, sym, q)`
    (read-only SQL + optional confidence JSON). `ready:true` even without index (no DB use). CORE-53:
    UI labels confidence "estimated". Verified: symbol → graph/context/search (0.9/0.85/0.7).
  - All imports lazy (`from . import summarize/predict`) — no module-level side effects; NEVER calls
    embed/retrieve vector paths (embed-model rule).
- **Frontend:** `web/src/lib/api.ts` — `oracleApi` (`next`, `repoSummary`, `summary`, `suggestContext`)
  + `OraclePrediction`/`OracleNext`/`OracleStory`/`OracleSummary`/`OracleSuggestContext`. Symbol ids →
    `encodeURIComponent` on summary/suggest-context URLs. `web/src/views/OracleView.tsx` — repo story
    (narrative + dir chips + hotspots), file/dir summary input with SourceBadge (structural|llm), edit
    context with detail rows, predictive next-context (op selector, symbol field for symbol/graph ops,
    confidence % "estimated", per-tool icons). Bold offline banner noted in heading copy. `App.tsx`
    `/oracle` route + `LeftNav` `/oracle` "Oracle / AI" (Sparkles).
- **Verified:** `npx tsc --noEmit` silent · `bun run build` clean (~16s, Monaco chunk warnings are
  pre-existing) · backend import **72 routes** · in-process smokes 7/7 on ROOT (repo-summary, summary,
  suggest-context, next, empty-file error) + no-index guard on temp repo (`ready:false`, **no
  index.db created**).
- **Next: SPEC-15 Cross-cutting NFRs (last unit, BUILD.md row 14).**

## SPEC-15 unit complete (2026-08-17, this session) — BUILD COMPLETE

- **Backend fixes in `web_bridge.py` (all NFR violations found by a 51-route GET sweep, per-route
  6s thread timeout):**
  1. `GET /api/embed/status` — was `embed.get_embedder_with_feedback` (INSTANTIATES an embedder +
     auto-starts the daemon; frontend polls it every 10s in DaemonView → spawn attempt per poll).
     Rewritten: config-driven (`cfg[embed][backend]`) + `_warm_daemon()` probe only; never loads a
     model, never `emb.embed`. Verified ~1.4s, `ok:true`, no `:8787` spawn in stdio capture.
  2. `GET /api/context` — was `retrieve.context(ROOT, query=..., symbol=...)` → query path calls
     `retrieve.search` → `_ensure_embedded` (WRITES embedding rows = NFR-2 GET write violation) +
     auto-start daemon; empty q+symbol searched `""` and hung. Now: empty → `_err("EMPTY_CONTEXT")`;
     symbol path resolves the id first (unresolved → safe lexical `_safe_context(ROOT, name)`); query
     path → new `_safe_context()` in bridge — `lex_search` + `rrf([lex, vec])[:8]`, vector gated on
     `_warm_daemon()`, keeps exact `ContextPack` JSON shape (seed/budget_tokens/used_tokens/
     tokens_remaining/budget_utilization/sections/next_ops) for SearchView.tsx:208. Verified:
     query 0.56s/8 sections, unresolved symbol 0.66s no-hang, real symbol 0.1s/9 sections.
  3. New `_ttl_cache(key, ttl, fn)` (thread-safe, `time.monotonic` + lock) cached the slowest GETs:
     `/api/quality/gaps` (30s — 10 gapfill analyzers, cold 6.6s → warm 0.02s),
     `/api/quality/coverage` (30s, ~3s cold), `/api/onboarding/status` (5s — InitDetector tree-walk,
     cold ~6.2s; app gate polls 8s so gate stays reactive). `/api/quality` bundle already cached 30s.
  4. Global `RequestValidationError` handler → every FastAPI 422 returns the stable `_err` envelope
     (`VALIDATION_ERROR: Invalid parameter <loc>: <msg>`) instead of `{detail:[...]}` (NFR-1).
     Imported `RequestValidationError` from `fastapi.exceptions`; `JSONResponse` was already imported.
- **Route count:** 72 `/api` endpoints after all fixes (dedupe `{METHOD path}`) — unchanged, no dead
  routes. GET 51 routed testable.
- **Verified (in-process TestClient, no live server, no `.cip/config.toml` residue):** full 51-route
  sweep — 0 embed auto-start hangs (only 3 >6s cold-cache endpoints, now TTL-cached); `:8787` spawn
  string absent from stdio captures on `/api/embed/status` + `/api/context` + `/api/onboarding/status`
  + `/api/quality`; `npx tsc --noEmit` silent; `bun run build` clean (13.7s, Monaco chunk warnings
  pre-existing/lazy).
- **SPEC-15 scope notes:** WS JSON envelope, `cip web` CLI parity, legacy `web_server.py`/
  `dashboard-web` replacement, no dead nav routes — pre-verified in earlier units (SPEC-14, SPEC-01/11);
  this unit's sweep re-confirmed route parity and the embed/error-shape/cache NFRs.
- **Milestone gate (BUILD.md §2): all items green** — 15/15 spec rows `done`, tsc silent, build clean,
  backend imports 72 routes, cross-cutting pass complete, legacy replacement documented.

## §4 ledger closed (2026-08-17, post-completion) — BUILD.md §4 all `done`

- **Item 1 — snapshots (SPEC-04 §6.1/ISSUE-107, CORE-17):** `store.py` CORE_SCHEMA adds
  `snapshots(ts PK, job, health, components, counts, severity, meta)` + `idx_snap_job`. Writers/readers:
  `write_snapshot(con, job, …)` (INSERT OR REPLACE, commits), `snapshot_series(con, job?, limit)`,
  `prune_snapshots(con, keep)` (the ONLY sanctioned cleanup; keep=0 retains everything). **CORE-17
  resolved by construction:** `maintain.vacuum` only `DELETE`s `events` + orphan `vectors` — it never
  touches `snapshots`, so full history survives the events sweep.
- **Item 2 — sync hook (SPEC-04 §6.4):** `indexer.py:_sync_body` post-commit calls
  `store.write_snapshot(con, "sync", counts={files,symbols,chunks,edges,vectors}, meta={dirty,
  deleted,embedded,ms})` — off the hot path, after the existing `sync` event row. Verified: real sync
  on a copied `cipkg/` tree → 1 row `{files:95, symbols:1545, chunks:1574, edges:7513}`.
- **Item 3 — auto-manage hook (SPEC-03 §6.3):** `embed.get_embedder` inserts step 1b AFTER the warm-daemon
  check, gated on `cfg[web][auto_manage_daemon] and backend in (auto,service)`: calls
  `daemon.start_daemon(root, port)` then bounded-polls `service_health` for **60s** (SPEC-03 §6.3),
  returns RemoteEmbedder once warm, else falls through to hashing/local — **never blocks beyond the
  bound**. Default behavior unchanged (explicit-start remains default; `_start_service`/autostart path
  untouched). The web toggle endpoint (`POST /api/daemon/auto-manage`) already persisted the flag; the
  hook is the missing second half. Verified: `auto_manage_daemon:true` + `backend:hashing` → still
  `HashingEmbedder`, **no spawn**.
- **Item 4 — WatchManager (SPEC-04 §6.2, CORE-16):** `watch.py:watch(root, interval, verbose,
  stop_event=None, progress=None)` — loop exits when `stop_event.is_set()` (CORE-16 stop mechanism),
  forwards `progress` to `sync`. `web_bridge.py` adds `WatchManager` class (thread + `threading.Event`
  + lock; start() no-op while running, stop() sets flag, status() reports running/interval/stopping)
  + `_WATCH` singleton + `GET /api/watch/status`, `POST /api/watch/start?interval=`, `POST
  /api/watch/stop`. WS broadcasts: `watch.event` {start|stop|progress|error|exit} + `index.update`
  {kind:"sync", dirty,deleted,embedded,ms} (SPEC-04 addition 2). Watch never blocks a request.
- **Job wiring:** `audit` job closure now also writes a `snapshots` row (health=overall_score,
  components={score,coverage_pct}, counts=compute_stats, severity=findings summary, meta=scoped_file)
  alongside its existing `quality` trend event; `consolidate` job writes `snapshots` row
  (components={episodes,patterns,promoted}, meta=lookback_days). Both best-effort (snapshot never
  breaks the trend event). New `GET /api/snapshots?job=&limit=` (read-only).
- **Verified:** in-process TestClient — snapshots api 200/ok, watch start→stop lifecycle
  (started→stopping, thread exits), `embed/status` still `ok:true` with **no `:8787`/auto-start in
  stdio**; watch stop-flag unit test exits cleanly; `npx tsc --noEmit` silent; `bun run build` clean
  (13.4s, Monaco chunk warnings pre-existing); route count **72 → 76**. No `.cip/config.toml` residue.
- **Frontend note:** no UI changes this pass (watch/snapshots surfaces are backend + WS; frontend
  polling can consume `GET /api/snapshots` and the watch endpoints when a future unit adds panels).
- **Frontend wired (post-ledger, 2026-08-17):** `web/src/lib/api.ts` gains `watchApi` (status/start/
  stop) + `snapshotsApi` + `WatchStatus`/`Snapshot` types (request() unwrap preserved); `IndexView.tsx`
  adds a **Filesystem Watch** card (start/stop, interval, live `watch.event`-style badge via GET-poll)
  + a **Snapshot History** list (12 rows, job/health/count chips, click-to-expand JSON via
  `bg-surface-raised` pre). Also fixed a backend UX wart: `WatchManager.stop()` previously nulled the
  thread so `stopping` stayed `true` forever after exit — now keeps the thread and `_run`'s finally
  clears the flag, so status settles `running → stopping → idle` (race-free: start() refuses while a
  thread is alive). Verified: tsc silent, `bun run build` clean (11.2s), in-process TestClient —
  76 routes, GET/POST watch endpoints in shape, snapshot list `{job:null,count:0,snapshots:[]}`.

## Next exact commands (cold hand-off) — BUILD COMPLETE, no further unit work

The CIP Web Console v1 build is DONE. If reopening, do a final sanity pass rather than new work:

1. `[restore]` Read `docs/dev/web-console/BUILD.md` + `CHECKPOINT.md` + `RUNBOOK.md`.
2. Sanity (no server spawn — in-process TestClient only): import `cipkg.web_bridge` → expect 76 `/api`
   routes; quick GETs on `/api/embed/status`, `/api/context?query=…`, `/api/quality/gaps` (should be
   cached, instant) with no `:8787`/`auto-start` stdio output.
3. `cd web; npx tsc --noEmit` silent · `cd web; bun run build` clean.
4. Manual run (user-triggered only): `cd lib; python -m uvicorn cipkg.web_bridge:app --port 8090`,
   open http://localhost:8090. First-run shows the onboarding wizard when no index exists.
5. Cleanup sweeps only if smoke residue created: delete `.cip/config.toml`(.bak), seeded memory rows,
   smoke signal rows/`ingest:*` events that a verification pass may have written.