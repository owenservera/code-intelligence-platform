# SPEC-19 — Multi-Project Registry (foundation for all repo-scoped features)

- **Requirement source:** owner request 2026-08-17 — "manage all my CIP repos from one entry
  point, including onboarding new repos; extend the repo-profiles capability to be managed from a
  single frontend". Extends FR-12 (repo activation) + FR-10 (config/profiles); is the foundation
  SPEC-16/17/18 build on (project-scoped).
- **Grounding verified:** 2026-08-17 against `lib/cipkg/{web_bridge,base,cli,init_detector,watch}.py`,
  `web/src/{lib/api,stores/app,components/layout/AppShell}.tsx`
- **Build order dependency:** SPEC-15 (bridge rules) first; this lands **before** SPEC-16/17/18.

---

## 1. Goal & owner intent

The console must manage **any code folder** ("project" — git repo, monorepo subfolder, or plain
directory) from a single entry point: a project switcher, one dashboard across projects, and the
ability to **onboard a new project** (initialize CIP in it) from the UI. Today the whole bridge is
hardwired to ONE folder: `ROOT = repo_root()` at module scope (`web_bridge.py:36`), 138 direct
`ROOT` references across ~80 endpoints, zero registry of known projects, and onboarding that is
CLI-only (`cmd_init`, `cli.py:420`). This spec replaces the single-root assumption with a
**project registry + request-scoped root**, so every endpoint (existing and SPEC-16/17/18 new ones)
can resolve which folder it operates on. Per NFR-4 the console stays localhost/no-auth.

## 2. Truth-grounded core surface (verified)

| Need | Core call (verified) | Returns |
|---|---|---|
| Single-root assumption | `ROOT = repo_root()` `web_bridge.py:36`; used at **138 sites** across ~80 endpoints (`GET`/`POST`/`websocket` route fns) | module-global absolute path |
| Root discovery | `repo_root()` `base.py:74-82` — walks up from **cwd** for `.cip/`; `cip_dir(root)` `base.py:84`; `data_dir(root)` `base.py:86` | root / `.cip` / `.cip/data` |
| Onboarding detect | `InitDetector(root).detect()` `init_detector.py` (used at `web_bridge.py:1392` for `GET /api/onboarding/status` `:1435`) | repo_type/languages/git state |
| Full init flow | `cmd_init(root)` `cli.py:420` (AGENTS.md copy, hooks, detect, `indexer.sync` full) | CLI-only today; web has **no POST** to run it |
| Config / profiles | `load_config(root)` `base.py:118`; `DEFAULT_CONFIG["profile"]={}` `base.py:66-67`; per-repo overrides in `<root>/.cip/config.toml` `base.py:160` | per-folder config |
| Watch (single) | `WatchManager` wraps one `watch.watch(ROOT,...)` `web_bridge.py:430-478`, `_run` `:457` | one global watcher |
| WS fan-out | `/ws` `web_bridge.py:2946`; `_ws_clients` `:236`; `_schedule_broadcast` `:251` | global client set (no project scoping) |
| TTL cache | `_ttl_cache(key, ttl, fn)` `web_bridge.py:91` | unkeyed by root today |
| Client API | `request<T>(path, init)` `web/src/lib/api.ts:3` — single fetch helper, `BASE='/api'`; store `stores/app.ts` | one place to thread `repo` |
| Shell | `AppShell.tsx` (nav), route table `web/src/App.tsx:48-61` | switcher insertion point |

**Gap notes (all verified):**
- No registry of known projects exists anywhere (`lib/cipkg/sync_global/`, `repo-settings/`,
  `detectors` are referenced in docs/`base.py:131` but **absent on disk**).
- `web/src` has **zero** repo/ROOT concept (grep found no matches) — all queries unscoped.
- `handle_web_command` (`cli.py:258`) serves uvicorn rooted at cwd — one process = one folder.

## 3. UI/UX contract

- **Project switcher (AppShell):** dropdown in the shell header listing registered projects
  (name = folder basename, path, status chip: `initialized` / `indexed` / `no .cip` / `onboarding…`).
  Switch updates `activeProject` in the store → all views re-query the new project. Empty state =
  "no projects yet" + big onboard CTA.
- **Projects dashboard:** a `/projects` view — grid of project cards (path, repo type, index stats,
  findings count, last sync) + "Add project" (onboard) button. Selection opens the project in the
  console (switcher becomes active).
- **Onboard flow (extends FR-12 wizard):** pick any folder on disk (path input; no cwd
  restriction) → run detect → show detected repo type/language → confirm → background init
  (`cmd_init` equivalent) with live progress via WS → on success, register + switch to it. Failure
  states surface the swallowed repo-settings error (F-11/CORE-41, `base.py:153-157`) instead of
  silently continuing with a default profile.
- **Profile management (repo profiles):** per-project profile = the `[profile]` block that
  `load_config` reads from `<root>/.cip/config.toml`. The dashboard offers a read/edit of that
  block for the active project (SPEC-10 config pattern), since `DEFAULT_CONFIG` has no global
  profiles (`base.py:66`). Registry keeps the **list**; profile values stay per-folder.

## 4. API / WS contract

REST (additive):
- `GET /api/projects` → `{ok, data:{projects:[{id, root, name, status, repo_type?, indexed?,
  last_sync?, findings?}]}}` — reads registry, joins live status (init/index/daemon).
- `POST /api/projects` `{root}` → registers a folder (idempotent; `id` = normalized root).
  Does **not** init by default; `{root, init:true}` runs onboarding.
- `DELETE /api/projects?id=` → unregisters (does not delete files).
- `POST /api/projects/{id}/onboard` → starts background init for an existing entry (runs the
  `cmd_init` logic, `cli.py:420`) → returns `job_id`; progress via WS `job.update` (SPEC-03).
- `POST /api/projects/{id}/profile` → write/merge `[profile]` into `<root>/.cip/config.toml`
  (additive, SPEC-10 pattern). *(Second non-GET; flagged §7.)*

Request scoping (the load-bearing change):
- Every existing + new endpoint accepts optional `?repo=<id>` (or `X-CIP-Project` header). A
  middleware resolves `root = registry.root(id)` and sets a **request-scoped contextvar**;
  endpoints read `_root()` instead of the module global. Absent `repo`, fall back to the legacy
  cwd-derived `repo_root()` so `cip web` behavior is unchanged (SPEC-15 backward compat).

WS:
- `/ws?repo=<id>` scopes the connection to one project's event stream; `_ws_clients` becomes a
  per-project map; broadcasts fan out to the connection's project only. `file.changed`
  (SPEC-18) and `job.update` (SPEC-03) carry `repo` in payload.

## 5. Data contract

- **New registry store:** `projects.json` under a **global** CIP home (env `CIP_HOME`, default
  `~/.cip/`) — NOT inside any project, so it survives per-folder init. Shape:
  `{version:1, projects:[{id, root, added_ts, last_onboard_ts}]}`. Written atomically with a lock
  (single user, localhost).
- **Per-folder config stays per-folder:** `<root>/.cip/config.toml` (existing `load_config`,
  `base.py:160`) — registry only references it; no new schema in `index.db`.

## 6. Backend additions (lib/cipkg in scope)

1. **`lib/cipkg/project_registry.py` (new module)** — `list_projects()`, `register(root)`,
   `unregister(id)`, `get(id)`, `set_profile(id, data)`; atomic JSON read/write under `CIP_HOME`;
   `id` derived from normalized absolute root path (stable across sessions).
2. **Request-scoped root in `web_bridge.py`** — middleware sets a `contextvars.ContextVar` from
   `?repo=`/header; new helper `_root()` returns it (fallback `repo_root()`). Mechanical sweep:
   the 138 `ROOT` sites become `_root()` calls. Root param plumbing already exists on the 4
   core helpers that take `root`; most endpoints pass `ROOT` directly today.
3. **`POST /api/projects/{id}/onboard`** — extract the `cmd_init` body (`cli.py:420`) into a
   callable (`init_project(root)` in a new/borrowed lib location) so both CLI and web run the
   same path; run as a background job with `job.update` progress.
4. **WS per-project fan-out** — `_ws_clients` keyed by project; `/ws` accepts `?repo=`; broadcast
   helper filters by the client's project.
5. **`_ttl_cache` root-prefix** — cache keys gain a `root` segment so two projects never collide.
6. **Registry status join** — per project: `.cip` present (`Test-Path cip_dir`), `index.db`
   exists (`data_dir`), daemon pidfile, latest findings count (SPEC-07 aggregation).

## 7. Core issues / risks (flagged, grounded)

- **CORE-19 — module-global `ROOT` is the single biggest refactor in the bridge.** 138 sites,
  ~80 endpoints. Mechanical but must be swept completely; a missed `ROOT` leaks cross-project
  data. Mitigate: grep gate in CI/tests (`no bare ROOT outside web_bridge`), and the contextvar
  default keeps legacy behavior so old routes are never accidentally un-rooted.
- **F-11/CORE-41 carryover — repo-settings profile load is silently swallowed.** `load_config`
  imports `detectors` from a `repo-settings` dir that does not exist (`base.py:131`) and catches
  into `log_swallowed` (`:153-157`). Onboard/profile endpoints must surface this instead of
  silently proceeding with `profile={}`.
- **Watch — one global watcher must become N.** `WatchManager` (`web_bridge.py:430-478`) watches
  a single root; multi-project needs a watcher per registered project (or watch only the active
  one). Keep it lazy: start watch on project activation, not on registry load.
- **Watch — onboarding is heavy.** `cmd_init` runs a full `indexer.sync`; must be a background
  job, not an HTTP block (NFR-3). Registry write + `.cip` creation are quick; sync streams.

## 8. Acceptance checks (from owner request)

- [ ] `GET /api/projects` lists folders registered via `POST /api/projects`; state chips accurate.
- [ ] `?repo=` scopes every endpoint: same `/api/search` returns results for the chosen project;
      no cross-project leakage (cache keys and DB paths carry the root).
- [ ] Onboard a fresh folder (no `.cip`, no git) from the UI → `.cip/config.toml` written, index
      built with live `job.update` progress, project auto-switched on success.
- [ ] Switcher shows all projects; switching re-queries active view against the new root.
- [ ] `file.changed`/`job.update` WS events reach only connections subscribed to that project.
- [ ] Legacy `cip web` (no `repo`) behaves exactly as today (contextvar fallback to `repo_root()`).
- [ ] Profile edit writes `<root>/.cip/config.toml [profile]` and surfaces the F-11/CORE-41
      missing-detectors error instead of swallowing it.
