# Upgrade Plan — Index (10 atomic phases)

**Purpose:** Sequential, truth-grounded build plan for the multi-project console (SPEC-19) + the
three landed feature specs (SPEC-16/17/18), broken into **10 atomic phases**. Each phase is one
doc with its own verified code anchors, acceptance, and fail-state. Build strictly in order.

**Grounding rule (owner-mandated):** every line reference is verified against real source
(`lib/cipkg/*.py`, `web/src/*`) — not docs. Verified 2026-08-17.

## The 10 phases

| # | Doc | Scope | Builds |
|---|-----|-------|--------|
| 1 | `plan-01-project-registry.md` | Global `project_registry.py` + `CIP_HOME` JSON store | SPEC-19 §1/§5/§6.1 |
| 2 | `plan-02-request-scoped-root.md` | `_root()` contextvar sweep of web_bridge (138 `ROOT` sites) + **[GAP-01 `_CONFIG_PATH`→fn, GAP-02 tolerant boot]** | SPEC-19 §4/§6.2 |
| 3 | `plan-03-projects-rest.md` | `GET/POST/DELETE /api/projects` + status join + **[GAP-05 auto-register launch root]** | SPEC-19 §4 |
| 4 | `plan-04-onboard-post.md` | Onboard POST (extract `cmd_init` → `init_project`) + profile write | SPEC-19 §4/§6.3 |
| 5 | `plan-05-ws-multiproject.md` | Per-project WS fan-out + `watch` per project + **[GAP-03 daemon port guard]** | SPEC-19 §4/§6.4 |
| 6 | `plan-06-frontend-switcher.md` | Repo switcher, `/projects` dashboard, api.ts threading + **[GAP-04 CLI flags, GAP-06 per-project gate, GAP-07 rebuild]** | SPEC-19 §3/§6 |
| 7 | `plan-07-explorer-backend.md` | `GET /api/tree` + PATH_ESCAPE retrofit on `file_bundle` | SPEC-16 §4/§6 |
| 8 | `plan-08-explorer-frontend.md` | Tree spike + `headless-tree` build | SPEC-16 §3 |
| 9 | `plan-09-review-renderer.md` | Diff/at/review endpoints + `reviews.jsonl` + Monaco | SPEC-17 §4-6 |
| 10 | `plan-10-realtime-history.md` | `file.changed` WS + edits/blame/log + timeline | SPEC-18 §4-6 |

## Global anchors (every phase uses these)

| Anchor | Location |
|---|---|
| Module root | `ROOT = repo_root()` `web_bridge.py:36` |
| Envelope | `_ok` `web_bridge.py:64` / `_err` `:68` |
| TTL cache | `_ttl_cache(key,ttl,fn)` `web_bridge.py:91`; `_TTL_CACHE` `:87` |
| Job helpers | `_job_progress` `:290`, `_job_done` `:308`, `_job_error` `:318`, `_job_event` `:275` |
| WS | `_ws_clients` `:236`, `_broadcast` `:240`, `_schedule_broadcast` `:251`, `/ws` `:3052`, `ws_endpoint` `:3051` |
| Watch | `_WATCH = WatchManager()` `web_bridge.py:533`; `_run` `:504` calls `watch.watch(ROOT,...)` `:522` |
| Root discovery | `repo_root(start=None)` `base.py:74` (`SystemExit` `:81`), `cip_dir` `:84`, `data_dir` `:86` |
| Config | `load_config(root)` `base.py:118`; local overrides `<root>/.cip/config.toml` `:160` |
| Init | `cmd_init(root)` `cli.py:420`; `InitDetector(root).detect()` `init_detector.py:50/61`; `detect_init_status(root)` `:370` |
| Watch loop | `watch.watch(root,interval,verbose,stop_event,progress)` `watch.py:14`; `_snapshot(root)` `:4` |
| Client API | `const BASE='/api'` `web/src/lib/api.ts:1`; `request<T>` `:3`; `onboardingApi` `:883` |
| Store | `useAppStore` `web/src/stores/app.ts:23`; `AppShell` mounts `useWebSocket` `AppShell.tsx:56` |
| Routes | `App.tsx:48-61`; `LeftNav` `web/src/components/layout/LeftNav.tsx` |

## Phase zero (every doc): conventions
- **Atomic task = one deployable step** with: edit target (file:line), exact change, verify command, fail-state.
- **Never** rewrite `ROOT` outside `web_bridge.py` wholesale — the sweep is commanded per-endpoint call site.
- **Every new endpoint** must use `_root()`, never `ROOT`.
- **NFR-3:** heavy ops (sync/index/onboard) run as background jobs via `_job_*` helpers, never in-request.
- **Per-file-line requirement:** each acceptance check in a phase maps to a reproducible command.

## Gap additions (owner-requested 2026-08-17, folded into phases)

Beyond the original 10, review of the live system found 7 blockers for "launch from here + centrally
manage any folder + onboard/init". Each is now a **`[GAP-0N]` task inside a phase** (never a separate
doc) so build order is preserved:

| GAP | Blocked by | Folded into |
|-----|-----------|-------------|
| GAP-01 | `_CONFIG_PATH` bound at import → settings write the wrong project's config | PLAN-02 Task 2.4 |
| GAP-02 | Console crashes outside a `.cip` folder (`repo_root()` `SystemExit`) | PLAN-02 Task 2.1 |
| GAP-03 | Two projects share a daemon port → double-spawn / wrong-pid stop | PLAN-05 Task 5.4 |
| GAP-04 | No `cip web --project` / `--root` pre-selection | PLAN-06 Task 6.6 |
| GAP-05 | Launch root not in registry → switcher empty at first boot | PLAN-03 Task 3.4 |
| GAP-06 | Global onboarding gate blocks all projects at once | PLAN-06 Task 6.1 |
| GAP-07 | SPA rebuild (stale `web/dist`) not an acceptance check | PLAN-06 acceptance |

**GAP-02 consequence:** registry-only mode means PLAN-06 `?repo=` threading is *mandatory*, and every
root-requiring endpoint must 4xx `NO_PROJECT` instead of crashing.

---

**Order is enforced.** Phase N assumes Phases 1..N-1 merged and passing (each ends with `cip selftest`
or the documented verify command green).