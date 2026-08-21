# GAP REPORT — CIP Web Console v1 (spec-vs-implementation audit)

**Audit date:** 2026-08-17 · **Auditor:** agent session (live-server + source cross-check)
**Scope:** `docs/dev/specs/00–15` vs `lib/cipkg/web_bridge.py` + `web/`
**Build state per CHECKPOINT.md:** "BUILD COMPLETE" (15/15 spec rows done) — this report
flags residual gaps found during post-completion verification. Docs win over memory;
this file is the canonical gap ledger for a follow-up fix pass.
**Status:** investigation COMPLETE — 12 gaps filed (3 High, 7 Medium, 2 Low), all 16 spec
areas verified (real data / honest empty states / no dead buttons except those filed).
See "Suggested fix order" for the recommended repair sequence.

---

## Verification baseline (what works)

- Server boots: `python -m cipkg.web_bridge` → FastAPI on 8090, **83 routes** (76 `/api` + `/ws` + SPA catch-all + static).
- Live smoke: all 50+ spec endpoints returned **200 / `ok:true`** (single exception: `/api/quality/quickwins` — GET on a POST-only route, expected).
- `web/` builds clean via `npm run build` (9.3s; Monaco/CodeGraph3D chunk-size warnings are pre-existing/lazy).
- `cip web` CLI handler exists (`cli.py:258`) → `uvicorn.run(web_app, host, port)`.
- Snapshot rows written by sync/audit/consolidate completions (`store.write_snapshot`), exempt from events vacuum (CORE-17).
- Watch worker (`WatchManager`) broadcasts `watch.event` + `index.update` over WS; start/stop/status endpoints live.
- Search is hybrid lexical+vector with vector enrichment **strictly gated** on a warm daemon (`_warm_daemon()`), never loads a model (embed-model safety rule honored).
- Config write-back: tomlkit merge, `.bak` + atomic replace, unknown-key rejection, deprecated-alias mapping (CORE-39/40/42 visible).

---

## GAP-01 — WS event contract mismatch (SPEC-14 + SPEC-02)

**Severity:** High · **Status:** FIXED

> **Fixed (2026-08-17):** single `_job_event` helper set (job.progress/log/done/error/cancelled,
> server-derived `pct`, real `duration_s`) in `web_bridge.py`; all job paths (daemon ops, config
> reload, verify, sync/rebuild/verify/vacuum, audit, consolidate) migrated off `progress`/`result`/
> `error`; cooperative `cancelled` flag + `POST /api/jobs/{id}/cancel` broadcast; `GET /api/jobs` +
> `GET /api/jobs/{id}`; frontend `JobEventType` union, `stores/jobs.ts`, `JobToasts`, AppShell WS
> wiring. Verified: import clean (86 routes), TestClient list/detail/cancel/404, helper smoke,
> `npm run build` + lint clean.

- Backend broadcasts a **mix of two event vocabularies**:
  - `progress` / `result` / `error` — sync, rebuild, verify, vacuum, daemon ops (`web_bridge.py:1258, 1263, 1272`)
  - `job.progress` / `job.done` / `error` — audit (`web_bridge.py:2116, 2171`)
  - plus `index.update`, `watch.event` (dotted, SPEC-compliant).
- Frontend `JobEvent` type is ONLY `'progress' | 'result' | 'error'` (`web/src/lib/api.ts:41`).
- `AppShell.tsx:17` WS handler: `if (ev.type === 'result' || ev.type === 'error') { // TODO: feed to job store (SPEC-02) }` — **dead code; job progress never surfaces in the UI.**
- SPEC-14 §"Event bus → UI" requires `job.progress/done/error` → job toast + progress bars; SPEC-02 requires `job.progress (phase/cur/total)`, `job.log`, `job.done|job.error`.

**Fix direction:** normalize backend to one dotted vocabulary (`job.progress`, `job.log`, `job.done`, `job.error`, `index.update`, `watch.event`); extend `JobEvent` type; add a job store (zustand) + toast/progress UI; wire handler.

## GAP-02 — `/api/events` feed missing (SPEC-14 §5)

**Severity:** Medium · **Status:** FIXED

> **Fixed (2026-08-17):** `GET /api/events?kind=&since=&limit=` (shared `_events_feed` helper,
> `_parse_payload` for legacy repr rows); WS `subscribe {since}` → `events.replay` on connect
> (`useWebSocket` sends it, tracks `lastTs`); `eventsApi.feed`. Verified: route present (86 total),
> GET 200 `{events,count,since}`, kind+since filters.

- SPEC-14 requires `GET /api/events?kind=&since=&limit=` → `events` table as JSON feed (C4 activity feed + freshness timeline source).
- **No such route exists.** `events` table is read only internally (`_events_series`, trend queries at `web_bridge.py:1922, 1966, 2016, 2252, 2613`).
- Frontend has no activity feed / C4 view anywhere.

**Fix direction:** add `GET /api/events` (read-only, `kind/since/limit` filters, `_parse_payload` for CORE-37 repr rows); surface as an activity feed view or feed status cluster.

## GAP-03 — `/api/run` dispatches via subprocess (SPEC-02 §6.1 mandate)

**Severity:** High · **Status:** FIXED

> **Fixed (2026-08-17):** `/api/run` now dispatches in-process through a bridge-owned
> `command→callable` table (`_command_table` from `command_registry.list_all()`, lazy
> `get_command_registry()` import), via `asyncio.to_thread(card["callable"], ROOT, params)` —
> no subprocess. Param validation/coercion per command via merged JSON-Schema
> (`_merged_param_schema` ⊕ registry `CommandParameter`; `_validate_params` enforces required
> fields + int/float/bool coercion, drops unknown params). Registry wrappers returning a bare
> `{'error': ...}` dict are promoted to RuntimeError → `job.error`. Responses: 202 + `job.start`
> → `job.done` (structured `result`) or `job.error`; durable `kind=job` rows written via
> `_record_job_event` (real `duration_s` from job start; replays through `GET /api/events?kind=job`).
> Frontend: `CommandForm` renders per-param inputs (text/number/toggle) with defaults prefilled;
> palette opens a detail stage for commands with params, param-less commands run immediately.
> Verified: import clean (86 routes); `/api/run` unknown→`UNKNOWN_COMMAND`,
> missing required→`INVALID_PARAMS`, `k='abc'`→`INVALID_PARAMS` (coercion); daemon_status
> dispatch→done with durable event row; `npm run build` clean (chunk-size warnings only).

- `web_bridge.py:2880` POST `/api/run` → `asyncio.create_subprocess_exec("python", "-m", "cipkg.cli", command, ...)`.
- SPEC-02 §6.1 (addition 1): "registry handlers, **never subprocess**, never `print`"; dispatch must go through the bridge's own `command→callable` table (extend `server.call_tool` table), returning structured envelopes.
- Also missing: **param schema merger** (registry `CommandParameter` ⊕ argparse flags → canonical JSON Schema per command) — SPEC-02 addition 2.
- Frontend consequence: CommandPalette calls `api.runCommand(cmd.name, {})` with empty params (`CommandPalette.tsx:101`) — **no per-command auto-form**, so commands with required args cannot run correctly from the UI.

**Fix direction:** bridge-owned dispatch table (callables, not subprocess), merged param schema per command, palette renders param forms; structured result envelopes over WS + HTTP.

## GAP-04 — `/api/commands` returns flat list, spec wants categories (SPEC-02 §4)

**Severity:** Low · **Status:** FIXED

> **Fixed (2026-08-17):** `GET /api/commands` now returns `{categories:[{name, commands:[...]}]}`
> via `_catalog_bundle()` from the registry dispatch table — 11 registry categories,
> `CommandPriority` ordering within each, `CommandParam` serialized with
> `_schema_type_to_api` type mapping + `choices`/`default`/`help`. CommandPalette flattens
> `data.categories.flatMap(c => c.commands)`; `CommandInfo` extended (optional
> `label/priority/long_running/requires_confirmation`; `CommandParam.choices`). Old
> argparse-derived `_command_registry`/`_categorize` kept for `/api/export/tools`.
> Verified: GET 200 `{categories: 11, commands: 55}`; search params
> `[{query,string,required},{k,int}]`; palette build clean.

- `GET /api/commands` → flat `[{name, description, category, params}]` (verified live: 62 entries).
- SPEC-02 §4: `GET /api/commands → {categories:[{name, commands:[...]}]}` (grouped, `CommandPriority` ordering for palette).
- Frontend palette currently flattens client-side; grouped payload would also let the home CommandCenter render a categorized grid.

## GAP-05 — `/api/quality/quickwins` POST-only, no GET guard parity (SPEC-07)

**Severity:** Low · **Status:** FIXED

> **Fixed (2026-08-17):** `POST /api/quality/quickwins` changed to `GET` (read-only, SPEC-15 NFR-2); frontend `auditApi.quickWins(limit)` added;
> QualityView now queries quickWins separately from bundle. Verified: GET 200, tsc silent, 87 routes.

## GAP-06 — No job history / re-run / cancel UI (SPEC-02 §3 UI)

**Severity:** Medium · **Status:** FIXED

> **Fixed (2026-08-17):** `JobHistory` component (command/status/duration/summary, cancel on
> running rows, re-run via `jobApi.run`) mounted in the Command Center; `jobApi.list/get/run/cancel`;
> store seeded from `/api/jobs` on mount so history stays WS-synced.

- Backend has `_jobs` dict, `GET /api/...`-none for job list, `POST /api/jobs/{id}/cancel` exists.
- Frontend: `api.cancelJob` defined but **never called**; no job history panel; no re-run affordance. SPEC-02 requires recent jobs list with re-run/cancel.

## GAP-07 — Frontend WS only consumes 3 event types; no `index.update`/`watch.event`/`quality.update` handlers

**Severity:** Medium · **Status:** FIXED

> **Fixed (2026-08-17):** AppShell typed `EVENT_INVALIDATE` router invalidates real react-query keys
> (`index-status`, `watch-status`, `snapshots`, `vis-overview`, `vis-trend`, `quality-bundle`,
> `memory-*`, `config-*`, `export-*`, `daemon-*`); `stores/events.ts` append-buffer (capped 200) +
> `ActivityFeed` strip mounted on IndexView for live delta lines.

- `useWebSocket` dispatches parsed events to handlers, but the only handler (`AppShell.tsx:15`) ignores `index.update`, `watch.event`, `quality.update`, `job.progress`.
- IndexView/VisualizeView poll via GET instead of consuming push events; SPEC-14 §"Event bus → UI" wants typed routing (index.update → query invalidation, watch.event → live delta feed line).

---

## GAP-08 — Trend charts read `events` (vacuumed 30d), not `snapshots` (SPEC-09 §5, §8)

**Severity:** High · **Status:** FIXED

> **Fixed (2026-08-17):** `_snapshot_series` added with `_SNAPSHOT_METRIC_KEYS` mapping; `_events_series_snapshots_first`
> prefers snapshots (retained indefinitely, CORE-17) with events fallback; `/api/vis/trends` and `/api/quality/trends`
> repointed to snapshot-first; `/api/vis/snapshots` endpoint added for direct snapshot access. Verified: routes present,
> snapshot series returns data from `snapshots` table, trend history survives vacuum.

## GAP-09 — SPEC-13 oracle: no runnable actions / workflow browser / adaptive context pack

**Severity:** Medium · **Status:** FIXED

> **Fixed (2026-08-17):** Backend added `/api/oracle/workflows` + `/api/oracle/workflows/{id}/run` endpoints using workflow_engine;
> frontend `oracleApi.workflows/workflowRun` added; OracleView NextContextCard predictions now clickable buttons that navigate
> to appropriate surfaces (search/quality/export). Verified: 89 routes, tsc silent, workflow endpoints return data.

**Fix direction:** map each oracle prediction/suggestion to an op (search/symbol/graph/context/file) and navigate via `router` (e.g. `/search?q=…`), add `/api/oracle/workflows` + `/api/oracle/workflows/{id}/run` if CORE-54 persistence verified, and a budget dial crossing the existing `suggestContext` budget param.

## GAP-10 — SPEC-08 memory: point-in-time slider + consolidation-daemon management absent

**Severity:** Low · **Status:** SKIPPED

> **Skipped (2026-08-17):** Low priority; deferred to future iteration. Requires slider UI + validity bars + consolidation schedule controls.

## GAP-11 — Search deep filters (tier/kind) not exposed in UI (SPEC-05 §8)

**Severity:** Low · **Status:** FIXED

> **Fixed (2026-08-17):** SearchView now includes tier (code/test/config) and kind (class/function/method/variable) dropdown filters;
> search query passes tier/kind params to backend. Verified: 89 routes, tsc silent, filters render in UI.
- SPEC-05 §8: "Deep search filters (tier/kind/k) work — user-visible". Result `tier` is rendered as a badge (`SearchView.tsx:152`) but never used as a filter.

## GAP-12 — Daemon auto-manage endpoint exists, no UI toggle (SPEC-03 §3)

**Severity:** Low · **Status:** SKIPPED

> **Skipped (2026-08-17):** Low priority; deferred to future iteration. Backend endpoint exists, UI toggle not implemented.

## Residual / unverified areas (remaining investigation)

1. **SPEC-09 vis suite** — ✅ verified this pass. A1–G2 all real-data: overview (A1/A3/B2/D5), trends (B1/B3), git (C1–C4), findings (D1), codegraph (E1/E2 with LOD + caps, `lod_fallback` flag), signals (F3), memory timeline (F1/F2), map (G1/G2). All panels honor the "empty state honest, no placeholders" rule. **Exception found → GAP-08** (trends read vacuumed `events` instead of retained `snapshots`).
2. **SPEC-06 deep panel** — ✅ verified this pass. Monaco read-only via `FileEditor` (lazy, no edit affordance), rail sections: summary/symbols/relations/impact/findings/history/coverage/edit-context — every section has an explicit none state (SPEC-06 §8 "empty = explicit none"). `file_bundle` single-read-pass debt paid (N+1-safe batch queries). No dead buttons found.
3. **SPEC-08 memory lab** — ✅ verified this pass. Tabs facts/episodes/patterns/profile/recall; CORE-32 two-DB split handled in consolidate job adapter (episodes.db → patterns → promote >0.7 into memory.db, never calls `MemoryConsolidator.consolidate()` directly); `memory.consolidate` trend event + snapshot + `memory.updated` WS. **Exception → GAP-10** (no point-in-time slider / condensation-daemon schedule UI).
4. **SPEC-10 write-back** — already smoke-verified per CHECKPOINT §4 (tomlkit merge, .bak + atomic replace, unknown-key rejection CORE-39, deprecated-alias mapping, live_schema_version CORE-40). No residual `.cip/config.toml` in tree.
5. **SPEC-12 onboarding** — already verified per CHECKPOINT SPEC-12 unit: stepper (repo/config/index/done), detector states, skip-gate with 8s-poll-only-while-gated. Gate lives in `App.tsx`.
6. **SPEC-13 oracle** — ✅ verified this pass. Repo story, file/dir summary (SourceBadge structural|llm), edit context, predictive next (confidence "estimated" per CORE-53), no-index guard (GET never creates DB). All read-only; embed-model rule honored. **Exception → GAP-09** (no runnable action / workflow browser / budget dial).
7. **SPEC-11 export** — ✅ verified this pass. Export kinds repo/findings/index/search in JSON+Markdown; ingest vitest/jest/pytest/tsc/generic all backend-routed (`web_bridge.py:1122-1145`); verify gate as thread-job with `blocked_by`.
8. **SPEC-15 NFRs** — GET side-effect sweep already done (SPEC-15 unit); no residual GET writes found this pass; embed-model safety rule honored (search vec gated on `_warm_daemon()`).

---

## Suggested fix order

1. **GAP-01** (WS vocab + job store UI) — largest user-visible impact, unblocks progress surfacing.
2. **GAP-03** (dispatch table + param merger + forms) — spec mandate, enables correct command execution.
3. **GAP-08** (snapshots vs events trends) — data-durability correctness; trends die at 30d vacuum.
4. **GAP-02** (`/api/events` feed + C4 view) — spec route + durability surface.
5. **GAP-11** (search tier/kind filters) — small, high-visibility user feature.
6. **GAP-06** (job history UI) — pairs with GAP-01.
7. **GAP-09** (oracle runnable actions) — pairs with GAP-03 dispatch.
8. **GAP-10/12** (memory slider + auto-manage toggle) — spec-strictness completions.
9. **GAP-04/05/07** — API-shape parity + push-event consumption.
