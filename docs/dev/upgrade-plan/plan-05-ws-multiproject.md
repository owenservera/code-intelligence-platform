# PLAN-05 — Per-project WS fan-out + per-project watch

**Phase 5 of 10.** Builds SPEC-19 §4/§6.4 + foundation for SPEC-18. Grounded 2026-08-17.
**Depends on:** PLAN-01/02.
**After this phase:** `/ws?repo=<id>` subscribes a connection to one project; `watch` runs per active
project, not once globally; `file.changed`/`job.update` broadcasts reach only their project's clients.

## Goal

Both today are global: `_ws_clients` is one set for all connections (`web_bridge.py:236`), and
`_WATCH = WatchManager()` (`:533`) wraps one `watch.watch(ROOT, ...)` call (`:522`). Multi-project
requires keying consumers by project and routing broadcasts by the connection's subscribed project.

## Truth anchors (verified)

- `_ws_clients: set[WebSocket]` `web_bridge.py:236`; `_broadcast` iterates the set `:240-248`; `_schedule_broadcast` `:251`.
- `ws_endpoint(ws)` `:3052`: `_ws_clients.add(ws)` `:3054`, `while` loop, `_ws_clients.discard(ws)` `:3082`.
- `WatchManager` `:458`; `__init__` `:467`; `start()` `:476`; `_run` `:504`; `watch.watch(ROOT,...)` `:522`; `_WATCH` singleton `:533`.
- `watch.watch(root=None, interval, verbose, stop_event, progress)` `watch.py:14`; `_snapshot(root)` `:4`; loop `:30-42`.
- `_job_progress` `web_bridge.py:290`, `_job_done` `:308` — job events must carry `repo`.

## Atomic tasks

### Task 5.1 — WS connections carry a project
- **Edit:** `ws_endpoint` `web_bridge.py:3051`.
  - Read `repo` from `ws.query_params` (or a subprotocol) at accept time.
  - Replace the single set with `_ws_clients: dict[str, set[WebSocket]]` keyed by project id
    (`"*"` = legacy/no-repo connections). Add/remove in the right bucket.
- **Edit:** `_broadcast` `:240` — new signature `_broadcast(event, repo=None)`:
  - `repo` given → only that bucket (plus `"*"` for backward-compat clients).
  - `repo=None` and event carries `payload.repo` → route by it; else broadcast to `"*"` only (legacy).
- **Edit:** `_schedule_broadcast(event, repo=None)` `:251` — pass through.
- **Edit:** `_job_progress/_job_done/_job_error` — accept optional `repo` and include it in the event so
  job events (SPEC-03) fan out project-scoped; default `repo=_root()` at call sites.
- **Verify:** two connections (no repo + `?repo=<id>`) — a job in project `<id>` reaches only the second.

### Task 5.2 — per-project watch map
- **Edit:** `WatchManager` `web_bridge.py:458`.
  - `self._watchers: dict[str, _Watcher]` (id → thread/stop-event) instead of one thread.
  - `start(project_id, root, interval)` — idempotent per project; `stop(project_id)`;
    `running(project_id)`. Keep `start()`/`stop()`/`running()` no-arg as aliases for the **active / legacy root** to
    preserve `/api/watch/start` `:542`, `/stop` `:549`, `/status` `:536` behavior for the un-scoped console.
  - `_run(project_id, root, interval)`: `watch.watch(root, ...)`, and in the loop after a detected change
    (`watch.py:37-42`) emit `_schedule_broadcast({"type":"file.changed","payload":{"path":...,"repo":project_id}}, repo=project_id)`
    — this is SPEC-18's live producer; PLAN-10 wires the consumer.
- **Edit:** `/api/watch/start` `:542` accepts optional `repo`; defaults to `_root()` so legacy calls are unchanged.
- **Verify:** start watch for two projects → both loops run; `file.changed` from project A reaches only A's clients.

### Task 5.3 — lazy watcher activation
- **Edit:** `WatchManager` — only start a watcher when a project becomes the active console project
  (register an activation hook in PLAN-06), never when merely listed in `GET /api/projects`.
  Keep memory bounded: stop watcher for a project when it's deactivated (SPEC-19 §7 "lazy, not on load").
- **Verify:** register 5 projects, activate 2 → exactly 2 watcher threads alive; deactivate → 1.

### Task 5.4 — per-project daemon port collision guard **[GAP-03]**
- **Bug:** `/api/daemon/start` calls `start_daemon(ROOT, …)` (`web_bridge.py:429/431`); two projects'
  configs both default to the same daemon port (`CIP_DAEMON_PORT`/`embed.service_port`) → second start
  binds-conflict or silently targets the wrong daemon.
- **Edit:** in the daemon endpoints, key the daemon by `_root()` and **probe before start**:
  - If a daemon already runs on the resolved port → return `_ok({port, reused:true, pid})` (no spawn).
  - If the port is taken by a *non-CIP* process → `_err("DAEMON_PORT_CONFLICT", port)`.
  - Else start. Store pid per project in `_DAEMONS: dict[str, dict]` (project id → {port,pid}).
- **Edit:** `/api/daemon` `:357` and `/api/daemon/log` `:371` read `_DAEMONS[_root()]` so stop/log
  target the active project's daemon, not the legacy one.
- **Verify:** two projects with same default port → second `/api/daemon/start` reuses (`reused:true`),
  never double-spawns; stop stops the right pid.

## Acceptance (this phase ends green)

- [x] `ws_endpoint` accepts `?repo=`; project-scoped broadcast verified (only matching client receives).
- [x] Legacy (no-repo) client still receives un-scoped events - `/api/watch/*` unchanged for it.
- [x] Two projects watched simultaneously; events atomized per project.
- [x] Watchers start on activation, stop on deactivation (no zombie threads).
- [x] **[GAP-03]** Daemon start never double-spawns on shared port (`reused:true` or `DAEMON_PORT_CONFLICT`); stop/log target the active project's daemon.
- [x] Pull test: `get status` per project reflects its own watch state.

**Next:** PLAN-06 wires the frontend to all of this (switcher + dashboard + repo-scoped api calls).