# BUILD — CIP Web Console v1 (canonical tracker)

**Folder:** `docs/dev/web-console/` · **Source of truth:** THIS FILE + `CHECKPOINT.md`.
**Specs:** `docs/dev/specs/00-15`. **Docs win over memory. Never derive state from memory.**

---

## 1. Progress at a glance

| # | Spec | Status | Notes |
|---|------|--------|-------|
| 0 | SPEC-01 App Shell | `done` | scaffold, layout, routing, status cluster |
| 1 | SPEC-02 Command Center | `done` | palette + quick actions (job runner follows) |
| 2 | SPEC-14 Realtime / WS | `done` | ws client + reconnect + shared broadcast |
| 3 | SPEC-03 Daemon & Server Mgmt | `done` | view + 7 endpoints |
| 4 | SPEC-04 Index Management | `done` | view + 6 endpoints |
| 5 | SPEC-05 Search & Navigation | `done` | view + 5 endpoints + palette code search |
| 6 | SPEC-06 Deep File Panel | `done` | view + bundle + 7 file endpoints + Monaco |
| 7 | SPEC-07 Quality & Audit | `done` | view + 8 endpoints + audit job |
| 8 | SPEC-08 Memory Lab | `done` | view + 10 endpoints + consolidate job |
| 9 | SPEC-09 Visualization Suite | `done` | 7 vis endpoints + VisualizeView + 3D graph |
| 10 | SPEC-10 Settings & Config | `done` | 7 config/env endpoints + SettingsView + tomlkit write-back (+ config.default.toml TOML-1.0 parse fix) |
| 11 | SPEC-11 Export & Integration | `done` | `/api/export` (+/status, +/tools, +/ingest), `/api/verify` job; ExportView + exportApi + `/export` route (LAST placeholder gone) |
| 12 | SPEC-12 Onboarding Wizard | `done` | `GET /api/onboarding/status` (InitDetector + index_status); first-run gate on `/`; OnboardingView stepper (repo → config → index → done) + localStorage dismiss + auto-hide on indexed |
| 13 | SPEC-13 Oracle Surface | `done` | `GET /api/oracle/{summary,repo-summary,suggest-context,next}`; OracleView (repo story, file summary, edit context, predict) + `/oracle` route + oracleApi; read-only, index-guarded |
| 14 | SPEC-15 Cross-cutting NFRs | `done` | NFR audit: embed-safe `/api/embed/status`+`/api/context`, 422→`_err`, TTL caches; 72 routes intact |
| **GAP Remediation** | **Wave 3-4** | **done** | GAP-08 (snapshot trends), GAP-05 (quickwins GET), GAP-09 (oracle workflows), GAP-11 (search filters) FIXED; GAP-10/12 SKIPPED (low priority) |

**Frontend** `web/` · **Backend** `lib/cipkg/web_bridge.py` · **CLI** `cip web` · **Port** 8090.

## 2. Milestone gate (all rows `done` = build complete)

- [ ] SPEC-05 → SPEC-13 all real views (no placeholders)
- [ ] `npx tsc --noEmit` silent
- [ ] `bun run build` clean in `web/`
- [ ] Backend imports: `web_bridge` app routes == expected count
- [ ] SPEC-15 cross-cutting pass (error shape, per-surface cache, WS JSON envelope, no dead endpoints)
- [ ] Legacy replacement documented (delete targets: `web_server.py`, `dashboard-web` path, legacy `static/`)
- [ ] `cip web` runs the FastAPI app; SPA served from `web/dist`

---

## 3. Spec work items (row = unit of work)

### SPEC-05 Search & Navigation — `docs/dev/specs/05-search-navigation.md` — `done`
- **Frontend:** `web/src/views/SearchView.tsx`, `/search` route; mode tabs (Code/Symbols), debounced
  type-ahead + Enter, k slider, result score/matched/tier chips, symbol detail graph+context.
  CommandPalette is hybrid: code results listed above commands, Enter deep-links to `/search?q=`.
- **Backend (web_bridge):** `GET /api/search?q=&k=` (hybrid, tier/kind filters bridge-side, `matched_fallback`),
  `GET /api/symbols?name=`, `GET /api/graph?id=&direction=&depth=`, `GET /api/context?symbol=`, `GET /api/history?path=`.
- **Safety rule (IMPORTANT):** web path must NEVER call `retrieve.search` / `vec_search` / `get_embedder` /
  `_ensure_embedded`. They load `LocalEmbedder` / auto-start daemon (up to 120s). Search endpoint is
  lexical-first and enriches via `_warm_daemon()` (<=0.5s HTTP probe) only; `warming` flag drives the UI chip.
- **Acceptance:** search quick + lexical-only when no daemon (probed ~1.6s cold, no model load); symbols quick; graph/context/history sub-0.3s.

### SPEC-06 Deep File Panel — `docs/dev/specs/06-deep-file-panel.md` — `done`
- **Frontend:** `web/src/views/FileView.tsx`, `/files?path=` route. Left: read-only Monaco
  (`src/components/file/FileEditor.tsx`, lazy `React.lazy` — chunk `FileEditor-*.js` ~1.3MB +
  `editor.api-*.js` ~2.6MB loads only when a file panel opens; workers via
  `monaco-editor/editor/editor.worker?worker` + ts worker, imported with the `exports`-map path
  `monaco-editor/...` NOT `.esm/vs/...`). Right rail (8 sections, lazy per-section queries):
  Summary (source badge structural|llm), Symbols, Relations (graph seeded by most-connected symbol),
  Impact (risk/affected/tests/routes/findings/advice), Findings (open, severity chips), History,
  Coverage & gaps, Edit context.
- **Backend (web_bridge):** `file_bundle()` (1-roundtrip read of symbols/chunks/routes/findings +
  vectors_n count, N+1-safe) + `file_findings()`; endpoints `GET /api/file` (bundle),
  `/api/file/summary`, `/api/file/impact?depth=`, `/api/file/history?n=`, `/api/file/coverage`,
  `/api/file/context?line=`, `/api/file/graph` (both depth params). **Route count now 38.**
- **Verified:** all 7 endpoints exercised in-process (base 24ms, summary 31ms, graph 24ms, context 16ms,
  history 204ms, impact 1.9s, coverage 2.9s — the two slow ones are lazy rail sections by design,
  CORE-23/CORE-25 guarded). `tsc --noEmit` silent; `bun run build` clean.
- **Safety:** same rule as SPEC-05 — file endpoints read DB + disk only; no model load, no daemon spawn.
- **Deep-link:** SearchView results + symbol links now navigate to `/files?path=…`.
- **Acceptance (SPEC-06 §8):** deep panel renders Monaco read-only; rail sections show real data or
  explicit none-states; impact cards show risk/affected/tests/routes/advice; Monaco lazy-loaded. ✔ seen.

### SPEC-07 Quality & Audit — `docs/dev/specs/07-quality-audit.md` — `done`
- **Frontend:** `web/src/views/QualityView.tsx`, `/quality`. Health score ring (overall_score) +
  component bars (coverage from report's `test_coverage`, quality from findings summary,
  freshness from last-sync age; complexity `null` → bar hidden, computed in gaps), severity chips
  (Critical/High finding counters), findings table (severity filter pills 'all|critical|high|medium|low',
  rule/title/suggestion/path), Quick Wins list, Run Audit button → audit job via POST.
- **Backend (web_bridge, 46 routes total):** `quality_bundle()` — fast core (health report + findings
  summary + quick wins + trends) cached 30s (`_QUALITY_CACHE`); heavy sections are lazy separate
  endpoints: `GET /api/quality/gaps` (gapfill score/dead/circular/migrations/env/logs/metrics/features/
  deps/api digest, stack-shape gaps → `None` = "not applicable"), `GET /api/quality/coverage`
  (gapfill.coverage), `GET /api/quality/findings?severity=&rule=&path=&limit=&offset=` (paginated),
  `GET /api/quality/findings/structured` (machine-actionable), `GET /api/quality/trends?metric=`,
  `POST /api/quality/quickwins`, `POST /api/quality/audit` (async job, writes a `quality` trend event
  on completion — snapshot stand-in while store snapshots is TODO). Audit job: `connect` imported in
  closure scope; scoped-files via `audit_file`, full via `audit(audit.refresh)`; broadcasts
  `job.progress`/`job.done`.
- **Breakdown math (additive-only):** `repo_health_report` returns only the weighted overall score, so
  components are derived bridge-side WITHOUT duplicating the report's internal ~6.5s `verify`/`dead`
  runs (cold bundle measured 16.7s with duplication → 4.2s without). Freshness is a cheap proxy
  (last `sync` event age <1h → 100). Complexity intentionally `null` in bundle (would need a ~2s
  dead pass) — see gaps endpoint.
- **Verified:** endpoints exercised in-process — bundle 4.2s cold (then 0s cached for 30s), findings/
  trends/structured sub-0.05s; audit job + trend-event write confirmed (scoped `analysis.py` 9s,
  event payload `{open,file,score,coverage_pct}` appears in `/api/quality/trends`). `tsc` silent,
  `bun run build` clean.
- **Acceptance (SPEC-07 §8):** health gauge, findings list, quick wins, severity chips all real data.
  Trends render once ≥1 audit job has run (initially empty — expected, honest none-state).
- **Safety:** same as SPEC-05/06 — read-only DB on GET, no model load, no daemon spawn.

### SPEC-08 Memory Lab — `docs/dev/specs/08-memory-lab.md` — `done`
- **Frontend:** `web/src/views/MemoryView.tsx`, `/memory`. 5 tabs: Temporal Graph (fact cards:
  subject→predicate→object chips, confidence badge, source badge, validity from→until),
  Episodes (table: type/ts/context/outcome/embedding-yes-no), Patterns (promoted `learned_patterns`
  fact cards + `analyze_user_patterns` JSON), Learning Profile (personalized suggestions with
  source + score bars, "profile default" note), Recall (search → `recall_relevant`). Overview strip
  (facts/episodes/patterns/profiles counters) + empty-state when `initialized=false`. Buttons:
  Consolidate Now (job), Clear Memory (two-click confirm → wipes).
- **Backend (web_bridge, 55 routes total):** `memory_overview()` cached 5s (counts from the memory
  subsystem's own DB files, last-consolidation from `events` kind=`memory.consolidate`, daemon flag
  via `daemon.daemon_status`, disk usage). Endpoints: `GET /api/memory/overview` `/facts?subject=&predicate=&at=&limit=` `/episodes?type=&limit=` `/recall?query=` `/patterns?user_id=` `/suggestions?user_id=`; `POST /api/memory/action` (record_user_action telemetry, no echo), `/api/memory/consolidate` (job), `/api/memory/clear` (confirm guard).
- **CORE-32 (verified on disk, resolved in bridge):** `LearningSystem.memory` → `memory.db`
  (temporal_facts), `episodic` → `episodes.db` (episodes) — TWO files. `MemoryConsolidator(one_path)`
  assumes shared — its `.consolidate()` would query an empty episodes table. The consolidate JOB
  adapter reads episodes from `episodes.db` (`EpisodicMemory.query_episodes`) and promotes >0.7−
  confidence patterns into `memory.db` graph via the core consolidator's own `_extract_patterns`/
  `_promote_to_semantic` (additive; core untouched). Broadcasts `memory.updated` WS event.
- **Gotcha repeated:** `connect` is NOT module-level; consolidate job closure had `'connect' is not
  defined` once → `from .store import connect` added inside `_run`. `_MEM_CACHE` reset needs
  `global` in both the closure and `clear`.
- **CORE-33 noted in UI:** `recall_relevant` fact-matching is `predicate=command:{query[:50]}`
  (exact tag, not semantic); episodic uses keyword `find_similar_episodes` (embedding BLOB only
  filled by logger with embedder on — which web never enables → "Embedding: no" + fallback note).
- **Verified:** all endpoints in-process (overview 0.13s, facts/episodes/patterns/suggestions
  sub-0.05s, recall 0.04s, action 0.06s); consolidate job ran to done and wrote a
  `memory.consolidate` event `{lookback_days, episodes, patterns, promoted}` (0 promoted is honest —
  core only extracts error/success patterns, test data was interactions); clear guard rejects
  without `confirm:true`. `tsc` silent, `bun run build` clean.
- **Safety:** same as prior — no model load, no daemon spawn; telemetry POST is JSONL append
  (debounced client-side); SEEDED test facts/episodes remain from smoke (memory.db facts_n=2,
  episodes_n=2) — harmless dev data.

### SPEC-09 Visualization Suite — `docs/dev/specs/09-visualization-suite.md` — `done`
- **Frontend:** `web/src/views/VisualizeView.tsx`, `/visualize` (was Placeholder). Tabbed A–G panels:
  Health & Score (ring + components + quality score trend), Index & Growth (files/symbols/chunks +
  freshness), Git & Activity (velocity, hotspots, co-change, feed), Quality & Debt (by-severity /
  by-rule / pie), Code Graph (3D), Memory & Signals (F3 broken-signals + memory timeline), Repo Map
  (G1 dirs + G2 hotspots). Recharts; every chart real-data with `source: …` label and honest
  empty-state (no placeholder art, CORE-27/30).
- **3D code graph (E1/E2):** `web/src/components/codegraph/CodeGraph3D.tsx` — raw `three` (no fiber/
  drei; `bun add three@0.185.1 @types/three`). Force layout, OrbitControls zoom/pan/rotate, node
  spheres colored by kind, edge lines by link kind, CSS2D labels, search-highlight glow,
  click-to-expand (merges via `setGraph`), direction/depth controls, and a 2D SVG LOD fallback when
  `lod_fallback` (≥200 nodes/400 edges). Lazy-loaded (`React.lazy`) → own 555KB chunk, loaded only
  when the Code Graph tab opens (mirrors the Monaco code-split pattern).
- **Backend (`web_bridge.py`, +7 → 55 `/api` routes):** `/api/vis/{overview,trends,git,findings,map,
  signals,graph}`. `_VIS_CACHE` per-group TTL with **event-driven invalidation** (`max(events.ts)`)
  so sync→'sync', audit→'quality', consolidate→'memory.consolidate' event writes refresh charts
  without touching job closures (SPEC-09 §6.5). `_parse_payload` tolerates core's `str(stats)`
  (Python repr) vs JSON payloads — **CORE-37-sibling**: indexer writes sync payloads as repos, all
  vis parses must not assume JSON. `vis_graph` reuses `_decorate_graph` + caps flag from
  `retrieve.graph`. Graph traversal verified end-to-end: `repo_health_report` depth1=11n/10e,
  depth2=148n/241e; **must URL-encode `#` in symbol ids** (frontend `encodeURIComponent` already).
- **Acceptance:** A1/A2/A3, B1/B2/B3, C1–C4, D1/D5, E1/E2, F3/F1/F2, G1/G2 all verified in-process:
  `tsc --noEmit` silent, `bun run build` clean (555KB CodeGraph3D chunk code-split), all 7 endpoints
  return `ok:true` on real data. Trends render from real event history (2 sync + 1 quality +
  1 consolidate events exist).

### SPEC-10 Settings & Config Editor — `docs/dev/specs/10-settings-config.md` — `done`
- **Backend (web_bridge, +7 → 67 routes):** `GET /api/config/schema` (per-key type/desc/
  choices/range + source badge from `_CONFIG_HINTS`+`_config_sources`, `live_schema_version`
  via `_effective_meta()` CORE-40), `GET /api/config/full` (three-way `{effective,file,defaults,
  sources}`), `POST /api/config/validate` (no write), `POST /api/config/save` (tomlkit merge →
  `.bak` + atomic `.tmp`+`os.replace`, returns `written_keys`+`diff`), `POST /api/config/reset`
  ({section} or {section,keys}), `POST /api/config/reload` (thread job: clears `_QUALITY_CACHE`,
  `_MEM_CACHE`, `_VIS_CACHE`, `embed._EMBEDDER_CACHE`, re-runs `load_config`, broadcasts),
  `GET /api/env` (sanitized CIP_*). POST bodies via Pydantic `ConfigUpdatesRequest`/
  `ConfigResetRequest` (bare `dict` param = query param gotcha). Key safety: unknown keys
  rejected, deprecated aliases mapped (`exclude_patterns→exclude`, `max_file_size→max_file_kb`,
  `performance.worker_threads→perf.workers`), range/choices enforced server-side.
- **Product bug fix (campaign lane):** `config.default.toml` line 151 `health_weights = {...}`
  was a multiline inline table (TOML 1.1); Python `tomllib` rejected the WHOLE file so all
  documented sections (`memory`/`web`/`mcp`/`daemon`/`analysis`/… ) silently never loaded.
  Collapsed to single line → full file parses, `DEFAULT_CONFIG` now carries all sections.
- **Frontend:** `web/src/views/SettingsView.tsx` (category cards Index/Embedding/Retrieval/
  Memory/Audit/Perf/Daemon+Web/Logging, type-aware controls bool-toggle/number/select/array,
  source badges default|config.toml|profile, per-key reset, dirty diff preview, validate→save
  →reload jobs, `.cip/config.toml` file panel, env panel), `settingsApi` in api.ts, `/settings`
  route wired (only `/export` placeholder remains).
- **Acceptance:** schema complete (18 sections), validate/save round-trip persists via tomlkit,
  reload job clears caches, config.default.toml parses — verified in-process.

### SPEC-11 Export & Integration — `docs/dev/specs/11-export-integration.md` — `done`
- **Frontend:** `web/src/views/ExportView.tsx`, `/export` (LAST placeholder removed). Export search
  results / findings / index stats / full index to JSON/Markdown download; MCP/daemon/index integration
  status cards; MCP tools schema viewer (collapsible per-tool param tables); signal ingest (vitest/jest/
  pytest/tsc/generic paste); verification gate buttons (Gate = tests+audit, Full = +typecheck+lint).
- **Backend:** `GET /api/export?kind=&format=` (kind ∈ repo|findings|index|search, format ∈ json|markdown)
  → downloadable attachment via `Content-Disposition`; `GET /api/export/status` (MCP 8080 + daemon 8765
  socket probes + index presence); `GET /api/export/tools` (MCP tools schema from CLI parser);
  `POST /api/export/ingest` (runtime_adapters parsers + stable ids CORE-46, custom `sig:` ids);
  `POST /api/verify` (verify.verify as async job → can_proceed/blocked_by over WS).
- **Verification:** tsc silent, `bun run build` exit 0, 21/21 in-process smoke PASS (download headers on
  all 8 kind/format combos, search export, tools, status, verify job lifecycle, regression on 6 existing
  endpoints), SPA serves built dist on `/export`.
- **Acceptance:** one export download works end-to-end (repo JSON + repo Markdown + findings + index +
  search all verified as `attachment` responses).
- **Decision:** route count baseline corrected — 67 total is the SPEC-11 snapshot (was miscounted as the
  SPEC-10 baseline; authoritative dedupe of `{METHOD path}` on `/api/*` = 67 with SPEC-11, i.e. 62 after
  SPEC-10 + 5). Test residue (smoke `src/a.ts` signal + `ingest:tsc` event) deleted before checkpoint.

### SPEC-12 Onboarding Wizard — `docs/dev/specs/12-onboarding-wizard.md` — `done`
- **Frontend:** first-run gate on `/` (if no `.cip/index.db`); steps: repo root → config review → index
  (jobs) → done. Dismissible once synced (localStorage `cip:onboarding:skipped`), auto-hides + clears
  dismiss when indexed. Poll onboarding only while `needs_onboarding` (avoids per-poll tree walk).
- **Backend:** `GET /api/onboarding/status` → full InitDetector state (`status`, `status_label`,
  `cip_dir_exists`, `config_exists`, `index_exists`, `git_hooks_installed`, `agents_md_exists`,
  `indexed`, `fresh` (CORE-47 from `index_status`), `needs_onboarding`, `detector_index_fresh`
  (advisory 1h-mtime), `detection` (repo type/langs/frameworks/git), `recommendations`).
- **Acceptance:** fresh repo shows wizard (verified: `not_initialized`, `needs_onboarding:true`,
  `python-lib`, no `.cip` side effect); existing repo skips (verified: `indexed:true`). Smoke count 2/2.

### SPEC-13 Oracle Surface — `docs/dev/specs/13-oracle-surface.md` — `done`
- **Frontend:** `web/src/views/OracleView.tsx`. LLM/summary surface: repo story, file summary,
  suggest-context results, predictive next-context. Bold "structural/offline" banner; SourceBadge
  (structural|llm) per summary. No dead buttons (cards rerun).
- **Backend:** `GET /api/oracle/summary?path=` → `summarize.summary`; `GET /api/oracle/suggest-context?file=`
  → `predict.suggest_context_for_edit`; `GET /api/oracle/repo-summary` → `summary()+map_+hotspots`;
  `GET /api/oracle/next?operation=&symbol=&query=` → `predict_next_context` (CORE-53: "estimated").
- **Safety:** all lazy-imported; `_oracle_ready()` = `os.path.isfile(index.db)` guard (GET NEVER creates it —
  verified); never touches embed/retrieve vector paths (embed-model rule).
- **Acceptance:** real summarizer output renders (verified repo-story + file-summary + suggest-context +
  next on ROOT; no-index guard returns `ready:false` on temp repo). Smoke 7/7 backend + guard.

### SPEC-15 Cross-cutting NFRs — `docs/dev/specs/15-cross-cutting.md` — `done` (last)
- **Stable error shape (NFR-1):** global FastAPI `RequestValidationError` handler now wraps every 422
  in the `_err` envelope (`VALIDATION_ERROR`) instead of leaking `{detail:[...]}`. Verified: missing
  required `path` on `/api/admission/explain` → `{ok:false, error:{code:"VALIDATION_ERROR"}}`.
- **Embed-model / daemon safety (NFR-2, center):** full GET sweep (51 routed APIs, per-route 6s thread
  timeout) exposed THREE violations; all fixed:
  1. `/api/embed/status` previously called `embed.get_embedder_with_feedback` → **instantiated an
     embedder + auto-started the daemon on every poll** (frontend polls `embedApi.status` every 10s!).
     Rewritten to config-driven + `_warm_daemon()` probe ONLY (`service_health(port, 0.5)`); never
     loads a model, never `emb.embed`. Verified 1.4s (probe-bound), `ok:true`, no `:8787` spawn line.
  2. `/api/context` previously called `retrieve.context(ROOT, query=...)` → `retrieve.search` →
     `_ensure_embedded` (WRITES embedding rows) + auto-start daemon; also hung ~forever when both
     query & symbol were empty (searched `""`). Now: empty → `_err("EMPTY_CONTEXT")`; symbol path
     delegates to `retrieve.context` ONLY after resolving the id (missing symbol degrades to
     `_safe_context` lexical on the name, never auto-embeds); query path → new bridge-local
     `_safe_context()` (lex_search + `rrf([lex, vec])`, vector only when `_warm_daemon()`, keeps the
     exact `ContextPack` shape: seed/budget_tokens/used_tokens/tokens_remaining/budget_utilization/
     sections/next_ops). Verified: query `"def summarize"` → 0.56s, 8 sections, 636/6000 tokens;
     unresolved symbol → 0.66s lexical, no hang; real symbol → 0.1s, 9 sections.
  3. `/api/quality/gaps` (10 gapfill analyzers, ~6.1s) + `/api/quality/coverage` (~3s) +
     `/api/onboarding/status` (InitDetector tree-walk, ~5-6s) → added `_ttl_cache(key, ttl, fn)`
     (thread-safe, monotonic clock). gaps/coverage 30s, onboarding 5s (App gate polls ≤8s). Verified:
     gaps cold 6.6s → warm 0.02s; onboarding/quality complete with **no embed spawn attempt**.
- **Read-only DB on GET:** re-verified via the sweep — the only prior write-path violators were the
  two fixed embed routes; `_oracle_ready`/`_onboarding_state_dict` guards hold (no `index.db` created).
- **Cache (NFR-7):** existing caches (vis 30s event-invalidated, quality bundle 30s, memory overview
  5s) + the 3 new TTL entries above. All heavy GETs now ≤ ~6s cold, instant warm, sub-6s everywhere
  in the full sweep (slowest cold: gaps 6.0s, onboarding 6.2s — both now cached).
- **No dead endpoints / route count:** 72 `/api` endpoints intact after fixes (dedupe `{METHOD path}`).
- **WS envelope / CLI parity / legacy replacement:** pre-verified in earlier units (SPEC-14 WS JSON
  envelope; `cip web` serves FastAPI + `web/dist`; legacy `web_server.py`/`dashboard-web` documented
  for deletion).
- **Verified:** full 51-route GET sweep — 0 hangs with embed auto-start (3 >6s cold-cache endpoints
  now TTL-cached), no `:8787` spawn in stdio captures; `npx tsc --noEmit` silent; `bun run build`
  clean (13.7s, Monaco chunk-size warnings pre-existing); route count 72.
- **Note:** `/api/admission/explain`'s earlier "422" was a probe artifact (frontend always passes
  `path`); the new handler makes even bare calls envelope-safe.

---

## 4. Backend additions ledger (beyond `web_bridge.py`)

| Module | Addition | Spec | Status |
|--------|----------|------|--------|
| `daemon.py` | `start_daemon()` non-blocking subprocess launcher | SPEC-03 (CORE-12/13) | `done` |
| `daemon.py` | `read_log(root, lines)` tail helper | SPEC-03 §6.2 | `done` |
| `store.py` | `snapshots` table + `write_snapshot`/`snapshot_series`/`prune_snapshots` (ISSUE-107) | SPEC-04 §6.1 | `done` |
| `indexer.py` | post-sync snapshot hook in `_sync_body` (post-commit, off hot path) | SPEC-04 §6.4 | `done` |
| `embed.py` | auto-manage hook in `get_embedder` (opt-in `[web].auto_manage_daemon`, bounded 60s warm-wait; default OFF) | SPEC-03 §6.3 | `done` |
| `watch.py` | `stop_event` + `progress` params (CORE-16); `web_bridge.WatchManager` + `/api/watch/{status,start,stop}` + `watch.event`/`index.update` WS | SPEC-04 §6.2 | `done` |

## 5. Known backend port-drift (grounded, not yet fixed)

- **CORE-10:** config `[daemon] port=8765` vs code default 8787 vs registry 8787. UI must surface the
  EFFECTIVE port; consolidate in a later pass (SPEC-10 settings). Daemon view already shows `port` from
  `.cip/data/daemon.port` (physical truth).

### 5a. Runtime consolidation — DONE (2026)

All runtime consumers now resolve the daemon port through one helper,
`embed.service_port(cfg)`: `[embed].service_port` → `[serve].port` → 8787.
`[daemon].port=8765` stays untouched in the TOML as intentional CONFIG-PORT-MISMATCH
doctor recall evidence (config value keeps testing the detector, never consumed at runtime).

Wired through the helper this pass:
- `/api/status` daemon probe + response `daemon.port` (was hardcoded 8765)
- `/api/env` `CIP_DAEMON_PORT` (was `DEFAULT_CONFIG["daemon"]` = nonexistent key → 8765 fallback)
- `/api/export/status` + `/api/export/tools` daemon port (same stale `DEFAULT_CONFIG` read)
- `embed.find_daemon_port` and `embed.get_embedder*` (were `serve.port`; still honor
  `.cip/data/daemon.port` physical override)
- `cli.cmd_embedder` (was `serve.port`)
- `web_bridge._warm_daemon` (already matched the helper's resolution order)

Verification: TestClient `/api/status` → `daemon.port=8787`, `/api/env` → `CIP_DAEMON_PORT=8787`,
`/api/export/status` → `8787`; watch lifecycle still settles (running → idle); 76 API routes
unchanged; `npx tsc --noEmit` silent; `bun run build` clean; s4/s5 port precision/recall tests
still pass.

## 6. Environment (fixed)

Windows + pwsh 7 · Python 3.14.4 · Node v24.11.1 · **Bun 1.3.14** (use `bun`, NOT npm) ·
FastAPI 0.141 · uvicorn 0.52 · tomlkit · websockets. Repo root `C:\0-BlackBoxProject-0\index`.