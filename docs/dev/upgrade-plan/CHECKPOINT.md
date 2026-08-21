# CHECKPOINT — Multi-Project Console Upgrade

**Canonical anti-erasure narrative** (RUNBOOK §6.5). Docs win over memory. A fresh agent with zero
context must be able to resume from the top section alone.

---

## WHERE I AM / WHAT'S NEXT (read this first)

- **Phase:** 7 of 10 — COMPLETED. Explorer backend: `GET /api/tree` lazy one-level directory listing
  (`dir_listing(root, rel)` with resolve + PATH_ESCAPE guard, prune via `_prune_name` =
  DEFAULT_EXCLUDES + backup_*/emergency_*, dirs-first sort, git decorations from one
  `git status --porcelain .` call, non-git → `""`), endpoint wraps in `_ok` + 10 s TTL cache
  (root-prefixed key, fresh on project switch). `file_bundle` traversal hole hardened — verified
  `../../Windows/win.ini` → `PATH_ESCAPE`, valid bundle unchanged.
- **All 10 phase docs + RUNBOOK + TRACKER written and verified.** GAP-01..07 all folded + done.
- **Next unit:** P8 — `plan-08-explorer-frontend.md`: tree frontend (fileApi.*, FileView.tsx,
  SearchView → `/files?path=` links). Spike gate per plan-08 (verify endpoint shape first).
- **Next command to run:** `npm run build` green in `web/` + browser click-through of the tree.

---

## Milestones

- 2026-08-17: Wrote plans 00–10, RUNBOOK, TRACKER, CHECKPOINT, and implemented `project_registry.py`.
- 2026-08-17: Folded GAP-01 (module-level `_CONFIG_PATH`→function) into P2 T2.4 and GAP-02
  (tolerant `_LEGACY_ROOT` boot) into P2 T2.1.
- 2026-08-17: Verified registry round-trip (idempotent+case, unregister, touch_onboard, corrupt
  recovery to `.bak`, default-home fallback).
- 2026-08-17: Completed P2 — `_root()` contextvar sweep: 46 ROOT references replaced with `_root()`/_require_root()`,
  `_ttl_cache` keys root-prefixed, `_config_path()` already request-scoped, middleware for tolerant boot in place.
- 2026-08-17: Completed P3 — Projects REST endpoints: GET /api/projects (list + status join), POST /api/projects (register),
  DELETE /api/projects?id= (unregister), auto-register launch root on boot (GAP-05), CLI selection via CIP_WEB_ROOT env var (GAP-04).
- 2026-08-18: Completed P5 — WS fan-out per project id (dict buckets, `?repo=` subscribe, `"*"` legacy), job events carry
  `repo`, WatchManager per-project watchers + lazy `POST /api/watch/activate`, project-scoped `file.changed` producer,
  GAP-03 daemon port guard (`_DAEMONS` reuse/conflict + always-present `tracked_pid`/`reused`).
- 2026-08-18: Completed P6 — frontend switcher/dashboard/wizard + repo-scoped API; backend bugfix
  (register entry dict); GAP-06 per-project gate verified (two temp projects return distinct states;
  `/onboarding` removed from `NO_REPO_PREFIXES`); GAP-04 CLI preselect verified (uvicorn intercepted);
  GAP-07 verified (fresh dist served, contains `/projects`). `tsc`/`build`/`lint` exit 0.
- 2026-08-18: Completed P7 — `/api/tree` lazy listing (`dir_listing` + `_prune_name` + one porcelain
  git-status call), 10 s TTL cache (root-prefixed, fresh on switch), PATH_ESCAPE on traversal;
  `file_bundle` guard verified. All in-process green (pruning, git M/?/non-git, DIR_NOT_FOUND,
  encoded-escape safety).

## Decisions

- 2026-08-17 Registry id = normalized absolute path (`normcase`/`abspath`) → Windows case-insensitive,
  environment `CIP_HOME` respected.
- 2026-08-17 All 7 GAPs folded as atomic tasks inside existing phases (plan-01 through plan-06) rather
  than separate docs, preserving the 10-phase build order.
- 2026-08-17 `home` property (not method) on `ProjectRegistry`; plan-01 acceptance text updated to match.

## Verified evidence

_Each task lists the verify command + output summary + acceptance box._

## Session log

- 2026-08-17: initial runbook/tracker/checkpoint setup, registry module implemented and verified.
- 2026-08-18: P5 backend verified green in-process — WS bucket delivery (repo+legacy), two watchers in parallel +
  stop-on-deactivate, GAP-03 conflict/reuse, legacy no-arg watch aliases, `file.changed` scoping, /api/projects list.
- 2026-08-18: P6 frontend done + verified — `request<T>` `?repo=` threading, WS `?repo=` reconnect, TopBar switcher,
  ProjectsView, per-project gate (GAP-06), CLI `--project/--root` (GAP-04), SPA rebuild (GAP-07), register bugfix.
  In-process evidence: onboarding.status?path / projects CRUD / status?repo scope / WS bucket isolation / GAP-04 rc paths.
  **Open item:** manual browser QA of switcher/dashboard/wizard (acceptance marked "UI clicks pending").
- 2026-08-18: P7 tree backend verified — root+nested listings, prune set, PATH_ESCAPE, git M/? + non-git "",
  TTL 10 s + project-switch freshness, DIR_NOT_FOUND file-as-path, encoded-escape safety, `file_bundle` guard.