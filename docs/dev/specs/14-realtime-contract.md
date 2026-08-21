# SPEC-14 — Realtime & Live Updates (FR-14 + NFR realtime)

- **Requirement source:** `05-requirements.md` §2 FR-14, NFR-1/2/3, §7.1(7), ISSUE-104/107
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{indexer,watch,daemon,embed,store}.py`
- **Build order dependency:** SPEC-02 (job model), SPEC-04 (sync/events), SPEC-01 (status cluster).

---

## 1. Goal & owner intent

The console is realtime (§7.1-7): WS pushes live job progress, sync/watch deltas, index/quality/
memory updates, config reloads, daemon state. All long ops are background jobs (NFR-3); WS is the
single live channel (`/ws`, NFR-1 same-origin). Falls back to polling when WS is unavailable.

## 2. Truth-grounded core surface (verified 2026-08-15)

| Need | Core call (verified) | Returns |
|---|---|---|
| Sync event | `_sync_body` writes `INSERT INTO events(ts, kind='sync', payload=stats)` `indexer.py:400` | durable activity log row |
| Events table | `events(ts REAL, kind TEXT, payload TEXT)` `store.py:37` | the C4 feed + freshness timeline source |
| Watch loop | `watch.watch(root, interval, verbose)` `watch.py:14` | infinite; prints; no stop (CORE-16) |
| Daemon status | `daemon.daemon_status(root)` `daemon.py:40` | state/uptime/cache |
| Embed health | `embed.service_health` `embed.py:44` / `find_daemon_port` `embed.py:55` | embedder warm state |
| Embed progress | `embed_pending(con, cfg, batch, progress)` `indexer.py:250` | progress("embed", cur, tot) |
| Sync progress | `_sync_body` progress fn `indexer.py:385-394` | progress("link"/"embed", cur, tot) |
| Write lock | `lock.WriteLock(root)` `lock.py` | single-writer gate (NFR-2) |
| Snapshot | SPEC-04 §5 `snapshots` | trend source (SPEC-09) |
| Memory | SPEC-08 (learning_data) | memory.updated events |

**No existing WS server in core to reuse** — legacy `websocket_handler.py` is part of the
replacement target. WS is fresh build here (SPEC-02/14), with `events` table as the durable feed.

## 3. UI/UX contract

- **WS client (frontend):** auto-connect on load to `ws://host:port/ws` (same origin, NFR-1);
  reconnects with backoff; heartbeat ping/pong (30 s); auth none (localhost bind only, NFR-4).
- **Event bus → UI:** typed event routing to consumers:
  - `job.progress/done/error` → job toast + progress bars (SPEC-02).
  - `index.update` → index panel counters + freshness chip (SPEC-04).
  - `watch.event` → live delta feed line (SPEC-04).
  - `quality.update` → health score + findings summary + trends refresh (SPEC-07/09).
  - `memory.updated` → memory lab counts (SPEC-08).
  - `config.written/reloaded` → settings view refresh + reload banner (SPEC-10).
  - `verify.done`, `signals.ingested` → export/verify view (SPEC-11).
  - `workflow.step` → workflow timeline (SPEC-13).
  - `daemon.status` → status cluster chips (SPEC-03).
  - `vis.refresh {groups}` → subscribed charts refetch (SPEC-09).
- **Polling fallback:** if WS unavailable, `GET /api/status` + per-surface polling (5 s base,
  longer for trends). WS is primary.
- **Throttling:** rapid sync progress events coalesced client-side (≤4 fps); trend refreshes
  debounced.
- **Auth/scope:** localhost bind; no per-user channels (single-owner console).

## 4. API / WS contract

WS messages (JSON, `{type, ts, payload}`):
- Server→client: `job.progress {job_id, phase, cur, total, eta_ms}`, `job.done {job_id, result}`,
  `job.error {job_id, message}`, `index.update {stats}`, `watch.event {delta}`, `quality.update
  {summary, snapshot_id}`, `memory.updated {counts}`, `config.written {sections}`,
  `config.reloaded {sections}`, `verify.done {result}`, `signals.ingested {inserted}`,
  `workflow.step {id, step, status}`, `daemon.status {state}`, `vis.refresh {groups}`,
  `hello {server_ts, schema_version}`.
- Client→server: `ping`, `subscribe {groups}`, `unsubscribe {groups}` (selective — reduce noise
  on dashboards), `cancel {job_id}`.

REST (fallback + control):
- `GET /api/events?kind=&since=&limit=` → `events` table as JSON feed (C4 + freshness; the
  durable log the WS replays from).
- `GET /api/status` → SPEC-01 one-shot (WS reconnect recovery).

## 5. Data contract

- `events` table remains the durable activity log (indexer writes sync; bridge writes
  audit/consolidate/config/verify/job rows with same `kind`/`payload` shape).
- Job progress/live state is in-memory (bridge); NOT persisted except via `events` on completion.
- Snapshot writes (SPEC-04 §5) triggered on job completion → trends (SPEC-09).

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge.WSEvents` hub** — fan-out hub (connected clients set), typed dispatch,
  reconnection-safe (client sends `since` on reconnect to replay missed `events` rows).
2. **`web_bridge.JobRunner`** — thread/process executor for SPEC-02 jobs with progress + cancel
  (`cancel {job_id}` → cooperative stop; respects WriteLock). NFR-2 single-writer enforced here.
3. **Event writer** — `web_bridge.record_event(kind, payload)` → `events` table + hub broadcast
  (keeps WS and durable log in sync; indexer keeps its own insert for sync).
4. **Daemon status poller** — 10 s poll of `daemon.daemon_status` + embed health → `daemon.status`
  events (SPEC-03 owns the daemon process; this is the telemetry channel).
5. **Watch manager integration** — `WatchManager` (SPEC-04 add 2) publishes `watch.event` +
  `index.update` here.

## 7. Core issues / risks (flagged, grounded)

- **CORE-55 — `events` payload for sync is `str(stats)` — a Python dict repr, not JSON.**
  `indexer.py:401` `payload=str(stats)`. Any consumer parsing payload as JSON fails.
  → Bridge event writer uses JSON payloads; the sync row stays legacy (don't parse it as JSON —
  or normalize on write in a bridge event). *(New issue.)*
- **CORE-56 — no progress exists for scan phase; `_sync_body` emits only "link" and "embed"
  phases.** `indexer.py:385-394` — scan/track phases print but don't call `progress`.
  → Job progress bar will jump at link; acceptable but UI must not claim scan progress.
  *(New issue.)*
- **CORE-57 — `watch.watch` and `run_consolidation_daemon` are blocking infinite loops**
  (CORE-16/CORE-31) — the WS model must never run them on the event loop; they live in managed
  threads/processes publishing events (SPEC-04/08). *(Cross-reference.)*
- **Watch: WS + FastAPI event loop** — sync/audit jobs must run in a thread/process pool, never
  blocking the ASGI loop; `JobRunner` (add 2) enforces this (NFR-2/3).
- **Watch: reconnect replay** — `since` from `events.ts` monotonic; use `max(ts)` + 1 to avoid
  dupes on reconnect.

## 8. Acceptance checks (from §6 / §7.5)

- [ ] WS connects same-origin, heartbeats, auto-reconnect with `since` replay (no missed events).
- [ ] All job types stream `job.progress/done/error`; cancel works cooperatively under WriteLock.
- [ ] Sync/watch/audit/config/memory/verify/daemon events update their surfaces live.
- [ ] Polling fallback works when WS down; `/api/events` is the durable replay source.
- [ ] `vis.refresh {groups}` drives subscribed charts only (selective subscribe).
- [ ] CORE-55/56 handled: JSON event payloads + honest scan-phase progress.
