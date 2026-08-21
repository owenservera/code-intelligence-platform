# Prep Gap — Enhancements & Upgrades NOT in `09-bugs-and-issues.md`

**Status:** ACTIVE — pre-frontend-build gap inventory.
**Derivation:** re-read all 16 specs (`docs/dev/specs/00-15`) + `05-requirements.md` (§0–§7.5)
and diffed every §6 "Backend additions" + requirements §5 "Backend additions required"
against every entry in `09-bugs-and-issues.md` (BUG-001..025, ISSUE-101..110, CORE-1..60,
F-01..20). This doc lists **only what is required to meet the requirements but is NOT
tracked in 09** — the work that exists in no bug log and must be planned/built explicitly.
Where an item has a partial 09 anchor (a *flagged problem* but no *deliverable*), it is
cross-referenced and the gap is the unbuilt part.
**Date:** 2026-08-16.

---

## 0. The single biggest gap: the `web_bridge` layer itself

`09-bugs-and-issues.md` documents core **problems**. It contains almost **none of the new
construction** the specs require. The entire new module below is untracked in 09:

- **`lib/cipkg/web_bridge.py`** (SPEC-15 §4) — the one module that owns all additions below.
  Contract: imports core only (never legacy web), read-only DB on GET, no dead endpoints,
  JSON event payloads, per-surface cache `{surface: (ttl, loader)}`, stable error shape
  `{ok:false, error:{code, message, core?:file:line}}`, N+1-batch lookups.
  → **Gap: the module + its contract are not in 09.**

---

## 1. Dispatch & jobs (SPEC-02) — gaps

| # | Addition (spec §6) | 09 anchor | What is actually missing |
|---|---|---|---|
| G-01 | `web_bridge.command_table` — extended `server.py:call_tool` map for all **55** commands → (callable, param schema, return-normalizer); direct lib calls, never registry handlers | CORE-5/9 *flag* broken/no-mapping | The **table itself** (work item: map all 55 to real lib functions). CORE-9 says "unverifiable until the table exists" — the table is the deliverable. |
| G-02 | Param-schema merger (registry `CommandParameter` ⊕ argparse flags → canonical JSON Schema) | CORE-8 *flags* incomplete metadata | The **merger implementation** (parse argparse of all 55 subcommands, merge, emit JSON Schema). |
| G-03 | Job runner + `JobRegistry` (in-memory: id, command, params, status, progress, logs[], result, traceback, started/finished, exit; retention ~200; cancel) | CORE-12 *flags* non-blocking need | The **Job model + executor + history + cancel** (thread/process pool, cooperative stop under `WriteLock`). |
| G-04 | `events` writer per job completion (kind, command, duration, status, summary) | CORE-55 *flags* JSON payloads | The **typed event writer** (JSON payload, wired to `events` table + WS). |
| G-05 | stdout capture (`io.StringIO`/`redirect_stdout`) for lib paths that `print` (audit, sync stats) | none | **Capture shim** — no 09 entry at all. |
| G-06 | `next_ops` as live runnable buttons (re-run/related fuel from `server._next_ops`) | none | **`_next_ops` bridge reuse** — no 09 entry. |

## 2. Daemon & embedding (SPEC-03) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-07 | `daemon.start_daemon(root, port, interval)` non-blocking spawn wrapper | CORE-12 *flags* blocking | The **non-blocking wrapper** (thread/subprocess spawn; used by the job). |
| G-08 | `daemon.read_log(root, lines=200)` log-tail helper | ISSUE-110 *notes* "log tail needs new helper" | The **helper** itself. |
| G-09 | Auto-manage hook in `embed.get_embedder` (when `[web].auto_manage_daemon` and no warm daemon: start + bounded warm-wait 60 s, then LocalEmbedder) | CORE-14 *partial* | The **hook** — must not change default behavior (`embed.py:8`). |
| G-10 | Queue/latency telemetry (`/embed/health` `queue_len`; `RemoteEmbedder` per-call latency) | CORE-11 *flags* no data source | The **telemetry** itself (optional enhancement). |

## 3. Index management (SPEC-04) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-11 | `snapshots` table + writer (`web_bridge.write_snapshot(...)` after sync/audit/consolidate; retained indefinitely; exempt from vacuum) | ISSUE-107/CORE-37 *contract*; CORE-17 *flags* pruning conflict | The **schema + writer + exemption** — no table schema in 09. |
| G-12 | `WatchManager` (runs `watch.watch` in thread, stop flag, broadcasts `watch.event` + `index.update`) | CORE-16 *flags* infinite/no-stop | The **manager** itself. |
| G-13 | Progress normalization (map sync scan/link/embed → unified job progress; ETA from cur/total + elapsed) | CORE-56 *flags* no scan progress | The **normalizer + ETA** — no 09 entry. |
| G-14 | `indexer.sync` → snapshot hook (post-commit) | CORE-37 *flags* enforcement | The **hook** in the job completion path. |
| G-15 | Schema-upgrade surface ("Upgrade schema" destructive-ish action; confirm-before-run) | CORE-40/3 *flags* version drift | The **action + confirm flow** — no 09 entry. |

## 4. Search & navigation (SPEC-05) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-16 | Normalized search envelope `{results, query, took_ms}` + `_external_search` fallback flag | CORE-21 *partial* (filters) | The **envelope** (no 09 entry). |
| G-17 | Tier/kind filter support | CORE-21 *flags* missing params | The **filter implementation** (bridge WHERE-clause re-query). |
| G-18 | `graph_payload(root, sid, ...)` — decorates `graph()` with node kind/path/severity + link kinds (batched `IN`) | CORE-22/38 *flag* ids-only + N+1 | The **decorator** (batch lookups). |
| G-19 | First-search embed-warm as background job / pre-warm at server start | CORE-19 *flags* hang | The **warm-state path** (job or pre-warm) — no 09 entry. |

## 5. Deep file panel (SPEC-06) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-20 | `web_bridge.file_bundle(root, path)` — base bundle (symbols/chunks/routes/findings/vectors_n) in one query set | none | **Entirely untracked in 09.** |
| G-21 | `web_bridge.file_findings(path)` findings-by-file helper (SPEC-07 reuses) | none | **Entirely untracked in 09.** |
| G-22 | Monaco lazy-load + large-file streaming (>2 MB) + viewport chunking | none | **Frontend prep — no 09 entry** (Monaco bundle ~2–3 MB, code-split). |
| G-23 | `graph_payload` seed symbol selection (first symbol with most out-edges in file) | none | **Selector logic — no 09 entry.** |

## 6. Quality & audit (SPEC-07) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-24 | `web_bridge.quality_bundle(root)` — health + summary + coverage + quick_wins + gaps; 30 s cache | none | **Entirely untracked in 09.** |
| G-25 | Audit-as-job adapter (wrap `audit(refresh)` with phase progress; snapshot write on completion) | CORE-28 *flags* heavy GET | The **adapter** (job wrapper). |
| G-26 | `findings_query` offset/pagination | CORE-29 *flags* cap 100 | The **pagination** (offset param). |
| G-27 | Custom-rule file watcher (re-run audit job on `.cip/rules.py`/`custom_rules_path` change) | none | **Entirely untracked in 09.** |

## 7. Memory lab (SPEC-08) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-28 | `web_bridge.memory_overview(root)` — counts + last_consolidation + daemon flag (5 s cache) | none | **Entirely untracked in 09.** |
| G-29 | Consolidation-as-job adapter (progress: query episodes → extract patterns → promote) | CORE-31 *flags* blocking loop | The **adapter**. |
| G-30 | Daemon-managed consolidation (schedule via `interval_hours`, stop flag) | CORE-31/32 *flag* path + blocking | The **managed process wiring**. |
| G-31 | `record_user_action` plumbing — server-side user_id default + **batch JSONL writes** | none | **Batching — no 09 entry.** |
| G-32 | Memory disk-usage + last-write display | CORE-34 *flags* outside lifecycle | The **usage telemetry** — no 09 entry. |

## 8. Visualization suite (SPEC-09) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-33 | `web_bridge.vis_bundle(group)` per-group payload composer + cache | none | **Entirely untracked in 09.** |
| G-34 | Snapshot writer extended: per-language (D5) + per-rule (D2) GROUP BYs at write time | CORE-37 *partial* | The **extended snapshot columns**. |
| G-35 | `web_bridge.graph_focus(root, sid, depth)` expansion endpoint (server-side caps) | ISSUE-108 *contract*; CORE-38 | The **endpoint + incremental merge** — no 09 entry. |
| G-36 | `web_bridge.signal_window(days)` — F3 aggregator (signals 14 d by kind/path) | none | **Entirely untracked in 09.** |
| G-37 | Live-refresh bookkeeping (which chart groups each job invalidates → `vis.refresh {groups}`) | none | **Entirely untracked in 09.** |
| G-38 | D5 per-language GROUP BY endpoint (requirements §5 explicitly lists it) | none | **Untracked** — requirements §5 item, no 09 entry. |
| G-39 | F1 temporal-facts count/series endpoint (requirements §5 explicitly lists it) | none | **Untracked** — requirements §5 item, no 09 entry. |

## 9. Settings & config write-back (SPEC-10) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-40 | `web_bridge.config_schema()` — introspect `DEFAULT_CONFIG` + `config.default.toml` → per-key schema | none | **Entirely untracked in 09.** |
| G-41 | `web_bridge.config_write(updates)` — tomlkit write preserving comments, atomic + `.bak`, diff | CORE-39 *flags* key mismatch | The **writer** (must reconcile `exclude_patterns→exclude`, `max_file_size→max_file_kb`). |
| G-42 | `web_bridge.config_reload(root)` — job re-running `load_config`, cache clear, hot-apply safe keys, flag restart keys | none | **Entirely untracked in 09.** |
| G-43 | Config file watcher (mtime on `.cip/config.toml` → `config.written` event) | none | **Entirely untracked in 09.** |
| G-44 | Secret masking in `GET /api/config` (keys with key/password/token masked; write-back still writes real) | none | **Entirely untracked in 09** (SPEC-15 §6). |
| G-45 | Legacy-key deprecation markers (`[perf]` vs `[performance]`, `health_weights` vs analysis weights) | CORE-42 *flags* ambiguity | The **reconciliation + UI deprecation labels**. |

## 10. Export & integration (SPEC-11) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-46 | `web_bridge.export_stream(fmt)` generator (or temp-file stream) | CORE-43 *flags* print/return | The **streaming adapter** (never buffer whole in memory). |
| G-47 | `web_bridge.parse_results(harness, text)` — per-harness parsers (vitest/jest/pytest/tsc/generic) → normalized `{path,line,kind,message}` + stable-hash ids for upsert | CORE-46 *flags* no idempotency | The **parsers** — "Core has no parser" (SPEC-11 §6.2) — no 09 entry. |
| G-48 | `web_bridge.tools_schema()` — tools schema viewer payload from command_table | none | **Entirely untracked in 09.** |
| G-49 | Verify-as-job adapter (typecheck/lint subprocesses never in-request; "runner not found" explicit) | CORE-45 *flags* silent degrade | The **adapter + runner detection**. |
| G-50 | Signal-ingest → snapshot hook (F3 trends include ingest) | CORE-37 *partial* | The **hook**. |

## 11. Onboarding wizard (SPEC-12) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-51 | `web_bridge.onboarding_detect(root)` — `InitDetector.detect()` + `RepoDetection` + profile-suggested config | none | **Entirely untracked in 09.** |
| G-52 | `web_bridge.onboarding_install(cfg, opts)` — write `.cip/config.toml`, create `data/`, AGENTS.md only-if-absent | CORE-48/50 *flags* safeguards | The **writer** (mirror `cip init` or reuse core install). |
| G-53 | Suggested-config generator (detect_repo_type + profile + language evidence → editable defaults) | CORE-49 *flags* heuristic | The **generator**. |
| G-54 | W5 post-sync seed (stats + sample search + health + graph seed symbol) | none | **Entirely untracked in 09.** |

## 12. Oracle / intelligence surface (SPEC-13) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-55 | `web_bridge.oracle_bundle(root)` — suggestions + next-context + repo story + briefing + "for you" (30 s cache) | none | **Entirely untracked in 09.** |
| G-56 | Workflow-as-job adapter (stream `workflow.step`; record run history in `events`) | CORE-54 *flags* persistence unknown | The **adapter + history**. |
| G-57 | Suggestion→action mapping (`web_bridge.resolve_suggestion`) — validate/execute each Suggestion tool+args | CORE-52 *partial* | The **resolver** (no dead buttons). |
| G-58 | Briefing adapter (extract `dashboard.briefing` to leaf module / lazy import w/ fallback) | CORE-51 *flags* TUI deps | The **extraction**. |
| G-59 | Analyzer-status capture for "why" tooltip + `log_swallowed` not `print` | CORE-52 *flags* swallow | The **status capture**. |

## 13. Realtime contract (SPEC-14) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-60 | `web_bridge.WSEvents` hub (client set, typed dispatch, `since`-replay on reconnect) | none | **Entirely untracked in 09.** |
| G-61 | `web_bridge.JobRunner` (thread/process executor, progress + cancel, WriteLock discipline) | CORE-12/57 *implied* | The **executor** — no 09 entry. |
| G-62 | `record_event(kind, payload)` — JSON event writer syncing WS + `events` table | CORE-55 *flags* str(payload) | The **writer**. |
| G-63 | Daemon status poller (10 s poll → `daemon.status` events) | none | **Entirely untracked in 09.** |
| G-64 | WS subscribe/unsubscribe groups (selective, reduce dashboards noise) | none | **Entirely untracked in 09.** |
| G-65 | Polling fallback + `/api/events` replay source + `since` monotonic dedupe | none | **Entirely untracked in 09.** |
| G-66 | Watch-manager → hub integration (`watch.event` + `index.update`) | CORE-16 *flags* | The **wiring**. |

## 14. Cross-cutting / infrastructure (SPEC-15) — gaps

| # | Addition | 09 anchor | What is actually missing |
|---|---|---|---|
| G-67 | Read-only `connect` helper (GETs must not CREATE the DB) | CORE-58 *flags* CREATE IF NOT EXISTS | The **helper**. |
| G-68 | Snapshot-write serialization (queue via JobRunner or lock) | CORE-60 *flags* concurrent busy | The **serialization**. |
| G-69 | Per-surface cache layer with invalidation via `vis.refresh` + job-completion hooks | none | **Entirely untracked in 09** (NFR-3 <300 ms). |
| G-70 | Stable error shape across all endpoints | none | **Entirely untracked in 09.** |
| G-71 | Log redaction (`base.log_swallowed` not `print`; `[logging] debug` gates detail) | CORE-52 *partial* | The **redaction policy**. |
| G-72 | Windows path normalization in bridge (`/` canonical, `base.py:192` pattern; LSIF `file://` URIs) | none | **Entirely untracked in 09.** |
| G-73 | `[web]` config section (host/port/auto_manage_daemon/theme/snapshot retention) | CORE-1/2 *flag* absence | The **section + honoring** — no 09 entry for the values themselves. |

## 15. Frontend-prep items (specified, not in 09)

| # | Item | Spec |
|---|---|---|
| G-74 | Dark dev-tool theme; tokenized palette (no raw hex); shadcn/ui + Tailwind + Recharts; bundle < 300 KB gz main | SPEC-15 §5 / §7.1-13 |
| G-75 | Command-center home; Ctrl+K palette over search + commands; no separate landing | SPEC-01/02/05 / §7.1-2 |
| G-76 | 3D code-graph flagship: node-kind icons, severity/link coloring, click-to-expand, search highlight, 2D LOD fallback | SPEC-09 E1/E2 / §7.1-7, ISSUE-108 |
| G-77 | Monaco code-split; read-only (no edit affordance) | SPEC-06 / §7.1-5, §7.5 |
| G-78 | tanstack-query cache + WS invalidation; coalesce WS storms ≤4 fps | SPEC-14/15 |
| G-79 | Every dashboard empty-state honest (no fake 50/80 scores; source labels on charts) | SPEC-07/09 / CORE-27/30 |
| G-80 | Oracle rail + "needs attention" default sort; every card drills to source + runnable | SPEC-13 / §7.1-9, FR-13 |

## 16. Requirements §5 items — coverage status

| Requirements §5 need | In 09? | Gap |
|---|---|---|
| `snapshots` table (ts, health, components, stats, severity, broken) on sync/audit/consolidate | ISSUE-107/CORE-37 (contract only) | G-11 (schema + writer) |
| Cleaner typed events during new-job runs | CORE-55 (JSON payload) | G-04/G-62 (writer) |
| D5 per-language GROUP BY endpoint | **no** | G-38 |
| E1 3D graph cap + `/api/graph/focus` expansion | ISSUE-108/CORE-38 (contract) | G-35 (endpoint) |
| F1 temporal count/series endpoint | **no** | G-39 |
| Daemon log-read helper | ISSUE-110 (note) | G-08 |

---

## Verification for this doc

- Every `G-xx` was absent from `09-bugs-and-issues.md` at write time (grep against
  BUG-/CORE-/ISSUE-/F- sections, verified 2026-08-16).
- Every item traces to a spec §6 addition or a requirements §5/§7.5 clause (reference kept).
- 09 remains the **bug/problem log**; this doc is the **construction/prep** log. The two are
  complementary: a `fix-in-bridge` in 09 supplies the *why*; a `G-xx` here supplies the *what*.
- When the other agent's 09 append finishes, re-run the diff (new F-2x entries may absorb
  some G-items — e.g. F-20 `FilterEngine.rank` already covers the suggestion-engine crash that
  G-57 partially assumes).
