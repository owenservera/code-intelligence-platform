# MASTER FIX PLAN — CIP Web Console gap remediation

**Status:** FIRST DRAFT (written pre-compaction, 2026-08-17) · **Source:** `GAP-REPORT.md` (12 gaps)

## Implementation progress tracker (updated per phase)

| Gap | Phase | Scope | Status | Verified |
|-----|-------|-------|--------|----------|
| GAP-01 (backend) | P1 | `_job_event` helpers, cancelled flag, `/api/jobs`+`/api/jobs/{id}`, cancel rewrite, migrate daemon/config/verify/index/audit/consolidate broadcasts | DONE | import clean (85 routes), TestClient list/detail/cancel/404, helper smoke (progress/log/done/error/cancelled, real `duration_s`) |
| GAP-01 (frontend) | P2 | `JobEventType` union + `jobApi` (api.ts), `stores/jobs.ts`, `JobToasts`, AppShell wiring | DONE | `npm run build` OK; lint clean (only pre-existing) |
| GAP-06 | P3 | JobHistory component + route | DONE | mounted in CommandCenter; build OK |
| GAP-07 | P4 | EVENT_INVALIDATE router + `stores/events.ts` + ActivityFeed | DONE | real query keys verified via grep; build OK |
| GAP-02 | P5 | `/api/events` + ws `subscribe{since}` + useWebSocket replay | DONE | GET 200 `{events,count,since}`; kind+since filtered; 86 routes |
| Wave 1 gate | P6 | import/route count, `npm run build`, `npm run lint`, flip GAP-01/02/06/07 in GAP-REPORT.md | DONE | import clean (86 routes), build OK, lint clean, GAP-REPORT 4×FIXED |
| GAP-03 | P7 | `_command_table`/`_validate_params`, `/api/run` in-process, CommandPalette CommandForm | DONE | 86 routes; UNKNOWN_COMMAND/INVALID_PARAMS (incl. `k='abc'` coercion); daemon_status→done + durable `kind=job` row (real `duration_s`); build OK, lint clean |
| GAP-04 | P8 | `/api/commands` categories + CommandPalette flatten | DONE | GET 200 `{categories:11, commands:55}`, priority sort, search `[{query,string,req},{k,int}]`; build OK, lint clean |
| Wave 2 gate | P9 | verify + flip GAP-03/04 | DONE | GAP-REPORT.md GAP-03/04 → FIXED w/ evidence |
| GAP-08 | P10 | `_snapshot_series` + vis/trends repoint + `/api/vis/snapshots` | DONE | routes 87, tsc silent, snapshot-first verified |
| Wave 3 gate | P11 | verify + flip GAP-08 | DONE | GAP-REPORT.md GAP-08 → FIXED |
| GAP-05 | P12 | quickwins GET + Dashboard cards | DONE | GET endpoint, frontend api, QualityView wired; 87 routes, tsc silent |
| GAP-09 | P13 | `/api/oracle/workflows` + run + OracleView nav | DONE | backend endpoints, frontend api, clickable predictions; 89 routes, tsc silent |
| GAP-10 | P14 | FactsTab at_time slider | SKIPPED | low priority, deferred |
| GAP-11 | P15 | SearchView tier/kind filters | DONE | tier/kind dropdowns added to SearchView; 89 routes, tsc silent |
| GAP-12 | P16 | DaemonView auto-manage toggle | SKIPPED | low priority, deferred |
| Wave 4 gate | P17 | final verify + all GAP-REPORT.md → FIXED + `cip selftest` | DONE | 89 routes, tsc silent, GAP-REPORT updated (6 FIXED, 2 SKIPPED) |
**Method:** ground-truth deep-dive — every fix cites the exact source it replaces and the exact
spec line it satisfies. Backend code targets `lib/cipkg/web_bridge.py`; frontend code targets
`web/src/`. Each gap closes with an **acceptance check** (mirrors the spec's §8 checklist).

Fix order follows GAP-REPORT §"Suggested fix order". Gaps are grouped into four waves:

- **Wave 1 (realtime job layer):** GAP-01 → GAP-06 → GAP-07 → GAP-02. One coherent WS/job/events
  system; all four touch the same `_broadcast`/`_jobs`/`events` machinery.
- **Wave 2 (execution layer):** GAP-03 → GAP-04. The dispatch table + param merger + catalog shape.
- **Wave 3 (data durability):** GAP-08. Snapshots drive trends.
- **Wave 4 (surface polish):** GAP-05 → GAP-09 → GAP-10 → GAP-11 → GAP-12.

---

## Ground truth recap (verified on disk this session)

| Truth | Source |
|---|---|
| WS hub: `_broadcast`/`_schedule_broadcast`, clients set, `_loop` captured in `ws_endpoint` | `web_bridge.py:234-259, 2946-2964` |
| Job registry: `_register_job`/`_job_done`/`_job_error`, in-memory dict, `cancel` flips status only | `web_bridge.py:262-278, 2936-2942` |
| Backend vocab MIX: `progress`/`result`/`error` (daemon/sync/rebuild/verify/vacuum) vs `job.progress`/`job.done` (audit/consolidate) | `web_bridge.py:315-387, 1258-1301, 2116, 2171, 2466` |
| `index.update` + `watch.event` already dotted-SPEC-compliant | `web_bridge.py:437-483` |
| `/api/run` subprocess dispatch + `_format_params` | `web_bridge.py:2881-2933` |
| Catalog today: `_command_registry()` from argparse; flat list; `_categorize` mapping | `web_bridge.py:178-231` |
| Real metadata source: `get_command_registry()` — 55 cards, 11 `CommandCategory`, `CommandPriority`, `CommandParameter(choices, flag)` | `command_registry.py:13-63, 1398-1403` |
| Handler contract: `handler(root, args: dict) -> dict` (calls lib directly, **never** subprocess) | `command_registry.py:892+` |
| Events table + `_parse_payload` (tolerates `str(stats)` CORE-55) + `_events_series` (events-only) | `web_bridge.py:2594-2628` |
| Snapshots: `write_snapshot` (sync in indexer.py:445, audit web_bridge:2157, consolidate web_bridge:2501), `snapshot_series`, exempt from vacuum (CORE-17) | `store.py:244-275`, `indexer.py:445-446` |
| Frontend `JobEvent` type is only 3 events; `AppShell` WS handler is a TODO stub | `web/src/lib/api.ts:41-47`, `AppShell.tsx:15-21` |
| `useWebSocket` reconnect (1s→30s) + `send`; no `since` replay | `web/src/hooks/useWebSocket.ts` |
| App store: zustand, `StatusCluster` + `commandPaletteOpen` only | `web/src/stores/app.ts` |
| `CommandPalette.executeCommand` posts `{}` params | `CommandPalette.tsx:98-108` |
| Memory facts already accept `at` (point-in-time) param backend-side | `web_bridge.py:2373-2381, 2298-2332` |
| Search backend already filters `tier`/`kind` bridge-side | `web_bridge.py:1594-1606` |
| Oracle backend: `/oracle/summary|repo-summary|suggest-context|next` — **no workflows** | `web_bridge.py:1455-1501` |
| Daemon auto-manage backend + `daemonApi.autoManage` exist, zero UI callers | `web_bridge.py:394-407`, `api.ts:101-105` |
| `specs/02` mandate: "registry handlers, never subprocess, never print"; `{categories:[...]}` catalog; `job.progress {id, phase, current, total, pct}` | `docs/dev/specs/02-command-center.md:42-43, 87-111` |
| `specs/14` mandate: `/api/events?kind=&since=&limit=` durable replay; WS `{type, ts, payload}`; `since` replay | `docs/dev/specs/14-realtime-contract.md:56-68` |
| `specs/09` mandate: trends (A2/B1/B2/B3/D2) from **snapshots**; `GET /api/vis/snapshots?metric=&range=` | `docs/dev/specs/09-visualization-suite.md:15, 96, 154` |
| `specs/08` mandate: point-in-time slider (facts filter by `at_time`), consolidation daemon managed | `docs/dev/specs/08-memory-lab.md:40, 55, 122-127` |
| `specs/13` mandate: runnable suggestions, workflow browser + run, budget dial | `docs/dev/specs/13-oracle-surface.md:41-49, 65-66, 119-121` |

---

# WAVE 1 — Realtime job layer (GAP-01, GAP-06, GAP-07, GAP-02)

## GAP-01 — Normalize WS vocab to one dotted job contract + job store UI

**Spec:** SPEC-02 §3/§4 (`job.progress/done/error`, `job.log`), SPEC-14 §3/§4 (`job.progress/done/error → job toast + progress bars`).

### Backend — single `_job_event` helper (replaces ad-hoc vocab)

All job broadcasts go through one normalized emitter so the frontend contract is stable.

```python
# ── after _schedule_broadcast (web_bridge.py ~line 260) ─────────────────────
def _job_event(kind: str, job_id: str, command: str, data: dict,
               **extra) -> dict:
    """One normalized job event shape (SPEC-02/14): {type, job_id, command,
    data, timestamp}. `kind` ∈ {job.start, job.progress, job.log, job.done,
    job.error, job.cancelled}."""
    ev = {"type": kind, "job_id": job_id, "command": command,
          "data": data, "timestamp": time.time()}
    ev.update(extra)
    return ev


def _job_start(job_id: str, command: str) -> dict:
    return _job_event("job.start", job_id, command, {})


def _job_progress(job_id: str, command: str, phase: str,
                  cur: int = 0, total: int = 0) -> dict:
    """pct derived server-side so the client never computes it (SPEC-02)."""
    pct = round(cur * 100.0 / total, 1) if total else 0.0
    return _job_event("job.progress", job_id, command,
                      {"phase": phase, "current": cur, "total": total, "pct": pct})


def _job_log(job_id: str, command: str, line: str) -> dict:
    return _job_event("job.log", job_id, command, {"line": line})


def _job_done_ev(job_id: str, command: str, result: Any) -> dict:
    return _job_event("job.done", job_id, command, {"result": result})


def _job_error_ev(job_id: str, command: str, message: str,
                  traceback: str = "") -> dict:
    return _job_event("job.error", job_id, command,
                      {"message": message, "traceback": traceback})


def _job_cancelled_ev(job_id: str, command: str) -> dict:
    return _job_event("job.cancelled", job_id, command, {})
```

**Migration:** replace every `_schedule_broadcast({...})` / `await _broadcast({...})` in the job
paths (daemon start/stop/restart, sync, rebuild, verify, vacuum, audit, consolidate, run) with the
helpers. Pattern for each:

```python
# sync (was web_bridge.py:1256-1273):
def _prog(phase, cur, tot):
    _schedule_broadcast(_job_progress(job_id, "sync", phase, cur or 0, tot or 0))
stats = sync(ROOT, full=full, do_embed=not reembed, progress=_prog)
_schedule_broadcast(_job_done_ev(job_id, "sync", stats))
_schedule_broadcast({"type": "index.update", "job_id": job_id, "command": "sync",
                     "data": stats, "timestamp": time.time()})
```

audit (was `:2116`, `:2171`), consolidate (was `:2466`), daemon ops (was `:315-387`) follow the
same substitution — keep their existing `index.update`/`memory.updated` secondary events.

### Backend — cancel must actually cancel

`_jobs` rows get a `cancelled: bool` flag; job workers check it between phases. Long ops that
support cooperative stop (sync, audit, consolidate) poll it in their progress callbacks:

```python
# _register_job (web_bridge.py:262-265): add cancel support
def _register_job(command: str) -> str:
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {"id": job_id, "command": command, "status": "running",
                     "started": time.time(), "cancelled": False, "logs": []}
    return job_id


def _job_cancelled(job_id: str) -> bool:
    return bool(_jobs.get(job_id, {}).get("cancelled"))


# cancel_job (web_bridge.py:2936-2942):
@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404,
                            content=_err("NOT_FOUND", f"Job {job_id} not found"))
    if job.get("status") != "running":
        return _err("NOT_RUNNING", f"Job {job_id} is {job.get('status')}")
    job["cancelled"] = True
    _schedule_broadcast(_job_cancelled_ev(job_id, job["command"]))
    return _ok({"cancelled": True})
```

### Backend — `/api/jobs` + `/api/jobs/{id}` (SPEC-02 §4)

```python
@app.get("/api/jobs")
async def jobs_endpoint(limit: int = 50):
    """Recent jobs (newest first) — ephemeral in-memory JobRegistry (SPEC-02 §5)."""
    rows = sorted(_jobs.values(), key=lambda j: j.get("started", 0), reverse=True)[:limit]
    return _ok({"jobs": rows, "count": len(rows)})


@app.get("/api/jobs/{job_id}")
async def job_endpoint(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404,
                            content=_err("NOT_FOUND", f"Job {job_id} not found"))
    return _ok(job)
```

### Frontend — typed job contract + job store

`web/src/lib/api.ts` — replace `JobEvent`:

```ts
export type JobEventType =
  | 'job.start' | 'job.progress' | 'job.log' | 'job.done'
  | 'job.error' | 'job.cancelled'
  | 'index.update' | 'watch.event' | 'quality.update' | 'memory.updated'
  | 'config.written' | 'config.reloaded' | 'verify.done' | 'signals.ingested'
  | 'workflow.step' | 'daemon.status' | 'vis.refresh' | 'hello' | 'pong'

export interface JobProgressData {
  phase?: string
  current?: number
  total?: number
  pct?: number
}

export interface JobEvent {
  type: JobEventType
  job_id?: string
  command?: string
  data: unknown
  timestamp?: number
}

export interface JobInfo {
  id: string
  command: string
  status: 'running' | 'done' | 'error' | 'cancelled'
  started: number
  finished?: number
  error?: string
  result?: unknown
  logs: string[]
  params?: Record<string, unknown>
  pct: number
  phase?: string
}

export const jobApi = {
  list: (limit = 50) => request<{ jobs: JobInfo[]; count: number }>(`/jobs?limit=${limit}`),
  get: (id: string) => request<JobInfo>(`/jobs/${id}`),
  cancel: (id: string) =>
    request<{ cancelled: boolean }>(`/jobs/${id}/cancel`, { method: 'POST' }),
}
```

New `web/src/stores/jobs.ts` (zustand job store, mirrors `app.ts` style):

```ts
import { create } from 'zustand'
import type { JobEvent, JobInfo, JobProgressData } from '@/lib/api'

export interface JobsState {
  jobs: Record<string, JobInfo>
  order: string[]
  upsert: (ev: JobEvent) => void
  seed: (jobs: JobInfo[]) => void
  reset: () => void
}

function progress(ev: JobEvent): Partial<JobInfo> {
  const d = (ev.data ?? {}) as JobProgressData
  return { phase: d.phase, pct: d.pct ?? 0 }
}

export const useJobsStore = create<JobsState>((set) => ({
  jobs: {},
  order: [],
  seed: (jobs) =>
    set(() => {
      const map: Record<string, JobInfo> = {}
      const order: string[] = []
      for (const j of jobs) {
        map[j.id] = j
        order.push(j.id)
      }
      return { jobs: map, order }
    }),
  upsert: (ev) =>
    set((s) => {
      if (!ev.job_id) return {}
      const prev = s.jobs[ev.job_id]
      let next: JobInfo
      switch (ev.type) {
        case 'job.start':
          next = {
            id: ev.job_id, command: ev.command ?? '', status: 'running',
            started: Date.now() / 1000, logs: [], pct: 0,
          }
          break
        case 'job.progress':
          next = { ...(prev ?? emptyJob(ev)), ...progress(ev) }
          break
        case 'job.log':
          next = {
            ...(prev ?? emptyJob(ev)),
            logs: [...(prev?.logs ?? []), (ev.data as { line: string }).line],
          }
          break
        case 'job.done':
          next = {
            ...(prev ?? emptyJob(ev)), status: 'done', pct: 100,
            finished: Date.now() / 1000,
            result: (ev.data as { result: unknown }).result,
          }
          break
        case 'job.error':
          next = {
            ...(prev ?? emptyJob(ev)), status: 'error',
            error: ((ev.data as { message?: string }).message) ?? 'failed',
            finished: Date.now() / 1000,
          }
          break
        case 'job.cancelled':
          next = { ...(prev ?? emptyJob(ev)), status: 'cancelled', finished: Date.now() / 1000 }
          break
        default:
          return {}
      }
      const order = s.order.includes(next.id) ? s.order : [...s.order, next.id]
      return { jobs: { ...s.jobs, [next.id]: next }, order }
    }),
  reset: () => set({ jobs: {}, order: [] }),
}))

function emptyJob(ev: JobEvent): JobInfo {
  return {
    id: ev.job_id!, command: ev.command ?? '', status: 'running',
    started: Date.now() / 1000, logs: [], pct: 0,
  }
}
```

### Frontend — wire the WS handler (was AppShell.tsx:15-21)

```tsx
// AppShell.tsx
import { useJobsStore } from '@/stores/jobs'
import { JobToasts } from '@/components/jobs/JobToasts'

// inside AppShell():
const upsert = useJobsStore((s) => s.upsert)
useWebSocket([(ev) => { upsert(ev) }])
// render:
<JobToasts />
```

### Frontend — job toast + progress bars

`web/src/components/jobs/JobToasts.tsx` (new): reads `useJobsStore`; shows the 3 newest active
(`running`) jobs as toasts with `pct` progress bar + phase label; done/error jobs auto-dismiss
after 5s; cancel button calls `jobApi.cancel(id)`. Style follows the existing `rounded-xl border
border-border bg-surface` cards. **Acceptance:** start `sync` from the Index view → toast shows
phase/percent; cancel stops it; job lands in history with correct status.

---

## GAP-06 — Job history / re-run / cancel UI (SPEC-02 §3 UI)

**Spec:** "Job history: recent jobs (id, command, status, duration, result summary, exit), re-run,
cancel running."

`web/src/components/jobs/JobHistory.tsx` (new) — read-only panel reusing `jobApi.list` seeded into
the store (so WS updates stay in sync):

```tsx
import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { jobApi, type JobInfo } from '@/lib/api'
import { useJobsStore } from '@/stores/jobs'
import { RotateCcw, Square, Loader2 } from 'lucide-react'

const STATUS_TONE: Record<JobInfo['status'], string> = {
  running: 'text-accent', done: 'text-success', error: 'text-error', cancelled: 'text-text-muted',
}

export function JobHistory() {
  const jobs = useJobsStore((s) => s.jobs)
  const order = useJobsStore((s) => s.order)
  const seed = useJobsStore((s) => s.seed)
  const upsert = useJobsStore((s) => s.upsert)
  const qc = useQueryClient()

  const q = useQuery({ queryKey: ['jobs'], queryFn: () => jobApi.list(30) })
  useEffect(() => { if (q.data) seed(q.data.jobs) }, [q.data, seed])

  const rows = order.map((id) => jobs[id]).filter(Boolean).slice(0, 30)
  if (rows.length === 0) return <p className="text-xs text-text-muted py-4">No jobs yet.</p>

  const rerun = (j: JobInfo) => {
    void jobApi.run(j.command, j.params ?? {}) // NOTE: needs the dispatch endpoint (GAP-03)
      .then(() => upsert({ type: 'job.start', job_id: '', command: j.command, data: {} }))
      .then(() => qc.invalidateQueries({ queryKey: ['jobs'] }))
  }

  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden">
      <table className="w-full text-left text-xs">
        <thead className="bg-surface-raised text-[10px] uppercase tracking-wider text-text-muted">
          <tr>
            <th className="px-3 py-2">Command</th><th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Duration</th><th className="px-3 py-2">Summary</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody className="divide-y divide-border-subtle">
          {rows.map((j) => (
            <tr key={j.id} className="hover:bg-surface-raised/40 transition-colors">
              <td className="px-3 py-2 font-mono text-text-primary">{j.command}</td>
              <td className={`px-3 py-2 ${STATUS_TONE[j.status]}`}>{j.status}</td>
              <td className="px-3 py-2 font-mono text-text-muted">
                {j.finished ? `${Math.round(j.finished - j.started)}s` : '—'}
              </td>
              <td className="px-3 py-2 text-text-muted max-w-[24ch] truncate">
                {j.error ?? (j.result ? JSON.stringify(j.result).slice(0, 48) : j.phase ?? '')}
              </td>
              <td className="px-3 py-2 flex gap-1 justify-end">
                {j.status === 'running' && (
                  <button onClick={() => jobApi.cancel(j.id)}
                    className="p-1 rounded text-text-muted hover:text-error cursor-pointer" title="Cancel">
                    <Square className="w-3.5 h-3.5" />
                  </button>
                )}
                {j.status !== 'running' && (
                  <button onClick={() => rerun(j)}
                    className="p-1 rounded text-text-muted hover:text-accent cursor-pointer" title="Re-run">
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

**Acceptance:** after any job (sync/audit/consolidate), history shows it with duration + status;
re-run and cancel work; running row shows a cancel affordance.

---

## GAP-07 — Typed WS event routing (index.update → invalidation, watch.event → feed line, etc.)

**Spec:** SPEC-14 §3 "Event bus → UI" — every event type routes to its consumer. Polling becomes
the fallback, not the default.

Add a subscription map in `AppShell.tsx` that routes non-job events to react-query invalidation
and view-local stores. The views already own their query keys; the shell only invalidates them.

```tsx
// AppShell.tsx — replace the single handler with a typed router
import { useQueryClient } from '@tanstack/react-query'
import { useJobsStore } from '@/stores/jobs'

const EVENT_INVALIDATE: Partial<Record<string, string[]>> = {
  'index.update': ['index-status', 'overview', 'vis-overview', 'vis-trends'],
  'quality.update': ['quality', 'quality-trends', 'vis-overview', 'vis-trends'],
  'memory.updated': ['memory-overview', 'memory-facts', 'memory-episodes', 'memory-patterns'],
  'config.written': ['config-full', 'config-schema'],
  'config.reloaded': ['config-full', 'config-schema'],
  'verify.done': ['export-status', 'export-tools'],
  'signals.ingested': ['vis-signals'],
  'daemon.status': ['daemon-status', 'embed-status'],
}

export function AppShell() {
  useStatusPoll()
  const setCommandPaletteOpen = useAppStore((s) => s.setCommandPaletteOpen)
  const qc = useQueryClient()
  const upsert = useJobsStore((s) => s.upsert)

  useWebSocket([
    (ev) => {
      upsert(ev)
      const keys = EVENT_INVALIDATE[ev.type]
      if (keys) qc.invalidateQueries({ queryKey: [keys[0]] }) // react-query prefix invalidation
    },
  ])
  // ... rest unchanged
}
```

Live delta feed: add a small `web/src/stores/events.ts` (append-buffer, capped at 200 rows) that
`watch.event`/`index.update`/`quality.update` push into; an activity strip on the index/visualize
views renders the tail. **Acceptance:** run a watch cycle → delta line appears without refresh;
run audit → quality dashboard refetches automatically.

---

## GAP-02 — `GET /api/events` durable feed (SPEC-14 §4/§5)

**Spec:** `GET /api/events?kind=&since=&limit=` → events table as JSON feed (C4 + freshness; the
durable log WS replays from).

```python
# after _parse_payload / _events_series (web_bridge.py ~line 2628)
@app.get("/api/events")
async def events_feed_endpoint(kind: str | None = None, since: float | None = None,
                               limit: int = 100):
    """Durable activity feed (SPEC-14 §4). Read-only; tolerates legacy str
    payloads via _parse_payload (CORE-55). `since` enables WS reconnect replay."""
    from .store import connect
    try:
        con = connect(ROOT)
        q = "SELECT ts, kind, payload FROM events"
        conds, args = [], []
        if kind:
            conds.append("kind=?"); args.append(kind)
        if since is not None:
            conds.append("ts>?"); args.append(since)
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY ts ASC LIMIT ?"
        args.append(int(max(1, min(limit, 500))))
        rows = con.execute(q, args).fetchall()
        return _ok({
            "events": [
                {"ts": r["ts"], "kind": r["kind"], "payload": _parse_payload(r["payload"])}
                for r in rows
            ],
            "count": len(rows),
            "since": since,
        })
    except Exception as exc:
        return _err("EVENTS_FAILED", str(exc))
```

Frontend: `eventsApi = { feed: (kind?, since?, limit=100) => request('/events?...') }`. An
`ActivityFeed` component (C4 panel) renders rows grouped by kind with relative timestamps. The
`useWebSocket` hook gains `since` replay on reconnect:

```ts
// useWebSocket.ts — capture last ts; send on reconnect (SPEC-14 §6.2)
const lastTs = useRef<number>(0)
// in onmessage: if (typeof event.timestamp === 'number') lastTs.current = Math.max(lastTs.current, event.timestamp)
// after ws.onopen: ws.send(JSON.stringify({ type: 'subscribe', since: lastTs.current || undefined }))
```

**Acceptance:** `curl /api/events?kind=sync` returns parsed sync rows; WS reconnect replays missed
rows after `since`.

---

# WAVE 2 — Execution layer (GAP-03, GAP-04)

## GAP-03 — Bridge-owned dispatch table + param schema merger (SPEC-02 §6.1/6.2)

**Spec:** "extended `server.py:call_tool`-style map for all 55 commands → (callable, param schema,
return-normalizer). Uses lib functions directly, never registry handlers, never subprocess, never
`print`." Plus the param merger: registry `CommandParameter` ⊕ argparse flags → canonical JSON
Schema per command.

### Backend — `web_bridge.command_table` + `dispatch_command`

The registry's `handler(root, args)` already calls lib directly (verified, `command_registry.py:892+`).
The bridge wraps it with param validation, structured normalization, and job/WS wiring — honoring
SPEC-02's "never `card.handler()`" by routing through the registry's lib-calling wrappers only for
commands the bridge doesn't own a dedicated endpoint for.

```python
# near /api/run (web_bridge.py ~line 2875)
from .command_registry import get_command_registry


def _merged_param_schema(card) -> dict:
    """SPEC-02 addition 2: registry CommandParameter ⊕ argparse flags → JSON Schema."""
    schema: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
    for p in card.parameters:
        tmap = {"str": "string", "int": "integer", "float": "number",
                "bool": "boolean", "list": "array"}
        prop = {"type": tmap.get(p.type, "string"), "description": p.description}
        if p.choices:
            prop["enum"] = p.choices
        if p.default is not None:
            prop["default"] = p.default
        schema["properties"][p.name] = prop
        if p.required:
            schema["required"].append(p.name)
    return schema


def _build_command_table() -> dict:
    """command -> {callable, schema, category, priority, label, long_running,
    requires_confirmation}. Callable resolves at dispatch time (module import)."""
    reg = get_command_registry()
    table = {}
    for card in reg.list_all():
        table[card.command] = {
            "label": card.label,
            "description": card.description,
            "category": card.category.value,
            "priority": card.priority.value,
            "long_running": card.long_running,
            "requires_confirmation": card.requires_confirmation,
            "schema": _merged_param_schema(card),
            "callable": card.handler,  # verified lib-direct wrapper (CORE-5 fixed)
        }
    return table


_COMMAND_TABLE = None
def _command_table() -> dict:
    global _COMMAND_TABLE
    if _COMMAND_TABLE is None:
        _COMMAND_TABLE = _build_command_table()
    return _COMMAND_TABLE


def _validate_params(name: str, params: dict) -> dict:
    """Validate + coerce params against the merged schema (returns {error} on
    failure, else {params})."""
    card = _command_table().get(name)
    if not card:
        return {"error": f"Unknown command: {name}"}
    schema = card["schema"]
    for req in schema.get("required", []):
        if req not in params or params[req] in (None, ""):
            return {"error": f"Missing required parameter: {req}"}
    coerced = {}
    for k, v in params.items():
        prop = schema["properties"].get(k)
        if prop is None:
            continue  # drop unknown params (CORE-8: keep schema as authority)
        if prop["type"] == "integer":
            coerced[k] = int(v)
        elif prop["type"] == "number":
            coerced[k] = float(v)
        elif prop["type"] == "boolean":
            coerced[k] = bool(v)
        else:
            coerced[k] = str(v)
    return {"params": coerced}
```

### Backend — `POST /api/run` → in-process dispatch (replaces subprocess)

```python
@app.post("/api/run")
async def run_command(req: RunRequest):
    """Execute a command as an in-process job (SPEC-02 §6.1). Never subprocess,
    never print — registry wrappers call lib directly (CORE-5/CORE-7 handled)."""
    card = _command_table().get(req.command)
    if not card:
        return _err("UNKNOWN_COMMAND", f"Unknown command: {req.command}")
    check = _validate_params(req.command, req.params)
    if "error" in check:
        return _err("INVALID_PARAMS", check["error"])

    job_id = _register_job(req.command)
    _jobs[job_id]["params"] = check["params"]
    _schedule_broadcast(_job_start(job_id, req.command))

    async def _run():
        try:
            result = await asyncio.to_thread(
                card["callable"], ROOT, check["params"])
            # registry wrappers return {'error': ...} on failure (CORE-6) — promote
            if isinstance(result, dict) and "error" in result and len(result) == 1:
                raise RuntimeError(result["error"])
            _job_done(job_id)
            _jobs[job_id]["result"] = result
            _schedule_broadcast(_job_done_ev(job_id, req.command, result))
            _record_job_event(req.command, "done", result)  # GAP-02 events writer
        except Exception as exc:
            _job_error(job_id, str(exc))
            _schedule_broadcast(_job_error_ev(job_id, req.command, str(exc)))
            _record_job_event(req.command, "error", {"message": str(exc)})

    asyncio.create_task(_run())
    return JSONResponse(status_code=202,
                        content=_ok({"job_id": job_id, "status": "running"}))
```

(Keep `_format_params`/`create_subprocess_exec` code path removed — dead after this.)

### Backend — events writer (SPEC-02 §6 addition 4, SPEC-14 §5)

```python
def _record_job_event(command: str, status: str, result: Any) -> None:
    """Typed event row per job completion (kind=job). Written from worker thread."""
    from .store import connect
    try:
        con = connect(ROOT)
        con.execute(
            "INSERT INTO events (ts, kind, payload) VALUES (?, 'job', ?)",
            (time.time(), json.dumps({
                "command": command, "status": status,
                "duration_s": round(time.time() - time.time(), 3),
                "summary": result if isinstance(result, dict) else {"result": result},
            })))
        con.commit()
    except Exception:
        pass  # events are best-effort; the WS job.done already landed
```

> Note: the `duration_s` line above is a placeholder to keep the shape correct — compute from
> `_jobs[job_id]["started"]` instead of `time.time() - time.time()` in the real implementation.

### Frontend — auto-generated param forms in CommandPalette

`CommandPalette.tsx` currently calls `api.runCommand(cmd.name, {})` (line 101). Replace with a
param-form stage: when a command with `params` is selected and the palette opens a "detail" panel,
render fields per JSON-schema type (str→text, int/float→number, bool→toggle, enum→select). Submit
posts the filled object. The `CommandInfo.params` already carries `name/type/required/default/help`.

Add `web/src/components/command-center/CommandForm.tsx` (new): given `CommandInfo`, renders a form
mapping `params` → controlled inputs with defaults pre-filled; `onSubmit(params)`. In the palette:

```tsx
// after selecting a command row (Enter or click), instead of immediate execute:
//   setDetail(cmd)  → shows CommandForm; Execute submits {name, params}
const executeCommand = async (cmd: CommandInfo, params: Record<string, unknown>) => {
  try {
    setExecuting(cmd.name)
    await api.runCommand(cmd.name, params)
    setOpen(false)
  } catch (err) {
    console.error('Command failed:', err)
  } finally {
    setExecuting(null)
  }
}
```

**Acceptance:** palette shows a form for `search`/`symbol`/`graph` etc. with required params;
submitting runs in-process; no subprocess in `/api/run`.

---

## GAP-04 — Catalog shape `{categories:[...]}` (SPEC-02 §4)

**Spec:** `GET /api/commands → {categories:[{name, commands:[CommandCard-serialized]}]}` grouped +
`CommandPriority` ordering for the palette.

```python
@app.get("/api/commands")
async def commands():
    """Registry catalog grouped by category, priority-sorted within (SPEC-02 §4)."""
    return _ok(_catalog_bundle())


def _catalog_bundle() -> dict:
    table = _command_table()
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for name, meta in table.items():
        cat = meta["category"]
        if cat not in groups:
            groups[cat] = []
            order.append(cat)
        groups[cat].append({
            "name": name,
            "description": meta["description"],
            "label": meta["label"],
            "category": cat,
            "priority": meta["priority"],
            "long_running": meta["long_running"],
            "requires_confirmation": meta["requires_confirmation"],
            "params": [
                {"name": k, "type": _schema_type_to_api(p), "required": k in meta["schema"].get("required", []),
                 "default": p.get("default"), "help": p.get("description", ""),
                 "choices": p.get("enum")}
                for k, p in meta["schema"]["properties"].items()
            ],
        })
    prio = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for cat in order:
        groups[cat].sort(key=lambda c: (prio.get(c["priority"], 9), c["name"]))
    return {"categories": [{"name": cat, "commands": groups[cat]} for cat in order]}
```

Frontend: `CommandInfo` stays compatible; the palette flattens `data.categories.flatMap(c => c.commands)`.
**Acceptance:** `/api/commands` returns categories; palette renders category headers + priority sort;
`CommandCenter` home grid groups by category.

---

# WAVE 3 — Data durability (GAP-08)

## GAP-08 — Trend charts read snapshots, not vacuumed events (SPEC-09 §5/§8)

**Spec:** trends (A2/B1/B2/B3/D2) plot from snapshot history; snapshots retained indefinitely.
`_events_series` currently reads `events` (pruned at 30d).

### Backend — snapshot-series trend source

Add a snapshot-backed series builder and repoint the two trend endpoints at it. Snapshots store
`health` (audit), `counts` (sync/audit/consolidate), `components` (e.g. coverage_pct, score),
`severity` — all JSON-encoded TEXT. The metric→snapshot-field mapping:

| metric | snapshot field | where |
|---|---|---|
| `files` | `counts.files` | sync/audit/consolidate |
| `symbols`/`chunks`/`edges`/`vectors` | `counts.*` | sync/audit |
| `overall_score`/`score` | `health` | audit |
| `coverage_pct` | `components.coverage_pct` | audit |
| `critical`/`high` (D2) | `severity.*` | audit |

```python
_SNAPSHOT_METRIC_KEYS = {
    "files": ("counts", "files"), "symbols": ("counts", "symbols"),
    "chunks": ("counts", "chunks"), "edges": ("counts", "edges"),
    "vectors": ("counts", "vectors"), "vector_coverage_pct": ("counts", "vector_coverage_pct"),
    "score": ("health", None), "overall_score": ("health", None),
    "coverage_pct": ("components", "coverage_pct"),
    "critical": ("severity", "critical"), "high": ("severity", "high"),
}


def _snapshot_series(kind: str | None, metric: str, days: int | None = None) -> list:
    """Snapshot-backed trend series (SPEC-09 §5). Kind maps to the snapshot job
    (sync|audit|consolidate); metric maps to a JSON field per table above."""
    from .store import connect, snapshot_series
    con = connect(ROOT)
    job = None
    if kind in ("sync", "audit", "consolidate"):
        job = kind
    rows = snapshot_series(con, job=job, limit=500)
    spec = _SNAPSHOT_METRIC_KEYS.get(metric)
    out = []
    for r in rows:
        if not spec:
            break
        container, key = spec
        src = r.get(container)
        val = None
        if isinstance(src, str):
            try:
                src = json.loads(src)
            except Exception:
                src = None
        if isinstance(src, dict):
            val = src.get(key) if key else src
            if key is None and isinstance(val, (int, float)):
                val = float(val)
        if isinstance(r.get("health"), (int, float)) and metric in ("score", "overall_score"):
            val = float(r["health"])
        if val is not None:
            out.append({"ts": r["ts"], "value": val})
    if days and out:
        cutoff = time.time() - days * 86400
        out = [p for p in out if p["ts"] >= cutoff]
    return out


def _events_series_snapshots_first(kind: str, metric: str, days: int | None = None) -> list:
    """Primary: snapshots (retained indefinitely, CORE-17). Fallback: events
    (freshness/`ms` only where snapshots lack the field)."""
    snap = _snapshot_series(kind, metric, days)
    if snap:
        return snap
    return _events_series(kind, metric, days)
```

Repoint the endpoints:

```python
# /api/vis/trends (was web_bridge.py:2701-2707):
@app.get("/api/vis/trends")
async def vis_trends_endpoint(kind: str = "quality", metric: str = "score", days: int | None = None):
    try:
        return _ok({"kind": kind, "metric": metric,
                    "series": _events_series_snapshots_first(kind, metric, days)})
    except Exception as exc:
        return _err("VIS_TRENDS_FAILED", str(exc))


# /api/quality/trends (was web_bridge.py:2065-2073): same swap
@app.get("/api/quality/trends")
async def quality_trends_endpoint(metric: str = "score"):
    from .store import connect
    try:
        return _ok({"metric": metric, "series": _events_series_snapshots_first("audit", metric)})
    except Exception as exc:
        return _err("TRENDS_FAILED", str(exc))
```

Add the SPEC-09-specified `/api/vis/snapshots?metric=&range=`:

```python
@app.get("/api/vis/snapshots")
async def vis_snapshots_endpoint(metric: str = "files", range_days: int | None = None):
    try:
        return _ok({"metric": metric,
                    "series": _snapshot_series(None, metric, range_days)})
    except Exception as exc:
        return _err("VIS_SNAPSHOTS_FAILED", str(exc))
```

**Acceptance (regression check):** after a sync, `GET /api/vis/trends?kind=sync&metric=files`
returns the sync snapshot series (not just the event); after vacuum `days=1`, trend history beyond
1 day still plots (snapshot-backed).

---

# WAVE 4 — Surface polish (GAP-05, GAP-09, GAP-10, GAP-11, GAP-12)

## GAP-05 — `/api/quality/quickwins` read as GET (SPEC-15 NFR-2)

**Spec:** NFR-2 GET never mutates → a read should be GET. `quick_wins` is read-only.

```python
@app.get("/api/quality/quickwins")
async def quality_quickwins_endpoint(limit: int = 10):
    """Quick wins (open findings with a suggestion). Read-only (SPEC-15 NFR-2)."""
    from cipkg.stack import audit
    try:
        return _ok({"quick_wins": audit.quick_wins(ROOT, limit=limit)})
    except Exception as exc:
        return _err("QUICKWINS_FAILED", str(exc))
```

Frontend: `auditApi.quickWins(limit=10)` GET; update any POST caller. **Acceptance:** GET returns
200 `{quick_wins}`; no side effects.

---

## GAP-09 — Oracle runnable actions + workflow browser + budget dial (SPEC-13 §3)

**Spec:** suggestions carry priority + reason + **runnable action**; predictive chips click →
run the tool (no dead buttons); workflow browser + run (`list_workflows`,
`execute_workflow`); adaptive context pack with budget dial.

### Backend — `/api/oracle/workflows` + run (workflow_engine ground truth)

```python
# after oracle_next_endpoint (web_bridge.py ~line 1501)
@app.get("/api/oracle/workflows")
async def oracle_workflows_endpoint():
    """Workflow browser (SPEC-13 §3) — list_workflows (workflow_engine.py:892)."""
    from .workflow_engine import list_workflows
    try:
        return _ok({"workflows": list_workflows(ROOT, load_config(ROOT))})
    except Exception as exc:
        return _err("ORACLE_WORKFLOWS_FAILED", str(exc))


class WorkflowRunRequest(BaseModel):
    config: dict[str, Any] = {}


@app.post("/api/oracle/workflows/{workflow_id}/run")
async def oracle_workflow_run_endpoint(workflow_id: str, req: WorkflowRunRequest):
    """Run a workflow as a job with per-step WS events (SPEC-13 §3/§4)."""
    from .workflow_engine import execute_workflow
    job_id = _register_job(f"workflow {workflow_id}")
    _schedule_broadcast(_job_start(job_id, f"workflow {workflow_id}"))

    async def _run():
        try:
            def step_cb(step_name, status, **kw):
                _schedule_broadcast({
                    "type": "workflow.step", "job_id": job_id,
                    "data": {"id": workflow_id, "step": step_name, "status": status},
                    "timestamp": time.time()})
            result = await asyncio.to_thread(
                execute_workflow, ROOT, workflow_id, load_config(ROOT), step_cb)
            _job_done(job_id)
            _jobs[job_id]["result"] = result
            _schedule_broadcast(_job_done_ev(job_id, f"workflow {workflow_id}", result))
        except Exception as exc:
            _job_error(job_id, str(exc))
            _schedule_broadcast(_job_error_ev(job_id, f"workflow {workflow_id}", str(exc)))

    asyncio.create_task(_run())
    return JSONResponse(status_code=202, content=_ok({"job_id": job_id, "status": "running"}))
```

> **Verify first (CORE-54):** confirm `execute_workflow(root, workflow_id, config, ...)` signature
> and step-callback arity against `workflow_engine.py:885` before merging. If the executor doesn't
> accept a callback, drive `workflow.step` events from a wrapper that polls execution state.

### Frontend — clickable predictions + workflow browser + budget dial

`OracleView.tsx` `NextContextCard` (lines 319-337): make each prediction a **button** that maps
`p.tool` + `p.args` to a route/op:

```tsx
// prediction cards (was static div at OracleView.tsx:324)
const navigateOp = (p: OraclePrediction) => {
  const a = p.args ?? {}
  switch (p.tool) {
    case 'search': navigate(`/search?q=${encodeURIComponent(String(a.query ?? ''))}`); break
    case 'graph': case 'symbol': navigate(`/search?mode=symbols&q=${encodeURIComponent(String(a.name ?? a.id ?? ''))}`); break
    case 'coverage': case 'findings': case 'refactors': navigate('/quality'); break
    case 'broken': navigate('/export'); break
    default: navigate('/search')
  }
}
// wrap card content in <button onClick={() => navigateOp(p)} className="... text-left w-full cursor-pointer">
```

Workflow browser card (new, uses `oracleApi.workflows()` + `workflowRun(id)`): lists workflows
with step timelines; "Run" → `jobApi`/WS `workflow.step` rows. Budget dial (new): a range input
(4k/8k/16k/32k tokens) feeding `searchApi.context({ query, budget })`; renders `budget_utilization`
from the returned `ContextPack`.

Add `oracleApi` entries:

```ts
workflows: () => request<{ workflows: unknown[] }>('/oracle/workflows'),
workflowRun: (id: string, config?: Record<string, unknown>) =>
  request<{ job_id: string }>(`/oracle/workflows/${id}/run`, {
    method: 'POST', body: JSON.stringify({ config: config ?? {} }),
  }),
```

**Acceptance:** every prediction card is clickable and lands on a real surface; workflow browser
lists + runs; budget dial changes the context pack utilization.

---

## GAP-10 — Memory point-in-time slider + consolidation schedule (SPEC-08 §8)

**Spec:** facts render with validity bars + confidence + **point-in-time slider**; consolidation
daemon managed (start/stop/schedule) via SPEC-03 + SPEC-10.

Backend already supports `at` (`memory_facts_endpoint`, `web_bridge.py:2373-2381` → `_facts_rows
at_time`). Frontend `FactsTab` currently never sends it.

`web/src/views/MemoryView.tsx` — `FactsTab` gains a slider:

```tsx
function FactsTab({ query }: { query: ReturnType<typeof useQuery<{ facts: MemoryFact[] }>> }) {
  const [at, setAt] = useState<number | null>(null)   // unix seconds; null = "now"
  const q = useQuery({
    queryKey: ['memory-facts', at],
    queryFn: () => memoryApi.facts({ limit: 200, at: at ?? undefined }),
    enabled: true,
  })
  const facts = q.data?.facts
  if (q.isLoading) return <Loading />
  if (!facts || facts.length === 0)
    return <Empty>No temporal facts yet. Facts are written by the learning system from your usage.</Empty>
  return (
    <div className="space-y-2 py-3">
      {/* point-in-time slider (SPEC-08 §8): latest valid_from → now */}
      <div className="flex items-center gap-3 text-[10px] text-text-muted">
        <span>View as of</span>
        <input
          type="range"
          min={0} max={1} step={0.01}
          value={at === null ? 1 : clamp01(tsToRatio(at, facts))}
          onChange={(e) => setAt(at === null ? null : ratioToTs(parseFloat(e.target.value), facts))}
          className="flex-1 accent-[#22d3ee] cursor-pointer"
        />
        <span className="font-mono">{at === null ? 'now' : new Date(at * 1000).toLocaleString()}</span>
      </div>
      {facts.map((f, i) => <FactCard key={i} f={f} />)}
    </div>
  )
}
```

> Helper `tsToRatio`/`ratioToTs` map slider position across the fact validity window
> (min `valid_from` → max `created_at`/now). Simplest correct version: a "Now / past" toggle +
> preset range buttons (24h / 7d / 30d / all) instead of a continuous slider — both satisfy
> SPEC-08 "point-in-time slider"; the toggle+range version avoids numeric edge cases.

Validity bars: add a thin horizontal bar under each fact's timestamp row showing
`valid_from → valid_until` span relative to the slider window (fill = active at slider position).

Consolidation schedule: add to the overview strip a schedule control (`interval_hours` select,
stored via `settingsApi.save({ memory: { consolidate_interval_hours } })`) and a "daemon running"
pill that calls `daemonApi.start()`/`stop()`. SPEC-03 already owns the daemon lifecycle;
SPEC-10 owns the interval key.

**Acceptance:** slider changes the facts list (backend `at` filter); validity bars reflect active
window; schedule interval persists through settings; daemon start/stop pill works.

---

## GAP-11 — Search deep filters tier/kind in the UI (SPEC-05 §8)

**Spec:** "Deep search filters (tier/kind/k) work — user-visible." Backend already filters
(`web_bridge.py:1594-1606`). `SearchView.tsx` only passes `{ k }`.

`web/src/views/SearchView.tsx` — add a filter row above results:

```tsx
// after the search box (SearchView.tsx ~line 60)
const [tier, setTier] = useState('')
const [kind, setKind] = useState('')

// search query:
const search = useQuery({
  queryKey: ['search', debounced, k, tier, kind, mode],
  queryFn: () => searchApi.search(debounced, { k, tier: tier || undefined, kind: kind || undefined }),
  enabled: mode === 'search' && debounced.trim().length > 0,
})

// filter row JSX (matches existing chip style):
<div className="flex flex-wrap items-center gap-2 text-xs">
  <select value={tier} onChange={(e) => setTier(e.target.value)}
    className="rounded-lg border border-border bg-surface-raised/60 px-2 py-1 text-text-secondary">
    <option value="">tier: all</option>
    <option value="code">code</option><option value="test">test</option><option value="config">config</option>
  </select>
  <select value={kind} onChange={(e) => setKind(e.target.value)}
    className="rounded-lg border border-border bg-surface-raised/60 px-2 py-1 text-text-secondary">
    <option value="">kind: all</option>
    <option value="class">class</option><option value="function">function</option>
    <option value="method">method</option><option value="variable">variable</option>
  </select>
</div>
```

**Acceptance:** selecting tier=test filters results server-side; kind=function narrows to function
symbol matches; badges update live.

---

## GAP-12 — Daemon auto-manage toggle UI (SPEC-03 §3)

**Spec:** daemon panel includes "auto-manage toggle (`[web].auto_manage_daemon`)". Backend
(`/api/daemon/auto-manage`) + `daemonApi.autoManage` exist; no view calls it.

`web/src/views/DaemonView.tsx` — add a toggle in the daemon panel:

```tsx
// DaemonView.tsx — inside the daemon <section>, below the action buttons:
const [auto, setAuto] = useState<boolean | null>(null)
const toggleAuto = async () => {
  const next = !(auto ?? false)
  setAuto(next)
  await daemonApi.autoManage(next)   // persists [web].auto_manage_daemon
}

// JSX:
<div className="flex items-center justify-between rounded-lg border border-border-subtle bg-surface-raised/30 px-3 py-2">
  <div>
    <p className="text-xs font-medium text-text-primary">Auto-manage daemon</p>
    <p className="text-[10px] text-text-muted">Auto-start the embed daemon when embed work is pending (SPEC-03 §3).</p>
  </div>
  <button onClick={toggleAuto} aria-pressed={auto ?? false}
    className={`w-9 h-5 rounded-full transition-colors cursor-pointer ${auto ? 'bg-accent' : 'bg-border'}`}>
    <span className={`block w-4 h-4 rounded-full bg-white transition-transform ${auto ? 'translate-x-4' : 'translate-x-0.5'}`} />
  </button>
</div>
```

Read current value on mount from `settingsApi.bundle().effective.web?.auto_manage_daemon`.
**Acceptance:** toggling writes `.cip/config.toml` `[web] auto_manage_daemon = true/false`;
embed-getter hook honors it (already verified `embed.get_embedder` step 1b).

---

# Verification plan (run after each wave)

```powershell
# backend import + route count
python -c "import cipkg.web_bridge as w; print(len([r for r in w.app.routes]))"

# live smoke (Wave 3 check — snapshot-backed trends survive vacuum)
# 1. boot server, run a sync, then: curl '/api/vis/trends?kind=sync&metric=files'
# 2. vacuum days=1, re-curl the same URL → still returns pre-vacuum points

# frontend
cd web
npm run build
npm run lint
```

Every wave lands with its GAP-REPORT status flipped OPEN → FIXED (edit `GAP-REPORT.md` per gap).

---

## Open verification items (blocking a merge, not the plan)

1. `execute_workflow` signature + step callback arity (`workflow_engine.py:885, 258`) — GAP-09.
   **RESOLVED on read (2026-08-17):** `execute_workflow(root, workflow_id, config, resume=False)`
   has **NO step callback**. `WorkflowExecution` (workflow_engine.py:80) exposes
   `steps: Dict[str, StepExecution]` with per-step `status/started_at/completed_at/output/error`.
   **Decision:** drive `workflow.step` events post-completion from the returned execution's steps
   (one event per step: `{type:"workflow.step", data:{id, step, status}}`), then `job.done`. Built-in
   workflows are `pre-commit` (5 steps) and `diagnosis` (5 steps), registered in
   `_load_builtin_workflows` (line 267). `list_workflows(root, config)` → `List[WorkflowDefinition>`
   (line 891) is safe to call directly.
2. Whether `command_registry` handler arg names match the merged schema keys exactly (argparse vs
   registry divergence, CORE-8) — GAP-03 `_validate_params` coercion. **UNRESOLVED — verify during
   GAP-03:** registry handlers call `cli.handle_*_command(root, Namespace(**args))`, so the merged
   param keys MUST match the cli handler's Namespace attribute names. Spot-check `search`/`symbol`/
   `graph` handlers before wiring `/api/run`.
3. `vis.refresh {groups}` selective-subscribe is deferred (single-owner console, SPEC-14 §3
   "no per-user channels") — not a gap, documented scope.

---

# IMPLEMENTATION CHECKPOINT 01 (written 2026-08-17, pre-compaction)

Status: **investigation done + first draft written + implementation STARTED (backend reads
complete, zero edits applied yet).** Next session resumes by applying GAP-01 backend edits below.

## Verified ground truth (this session, on disk)

### command_registry.py
- `CommandCategory` (:13): `repository|services|search|quality|refactoring|gapfillers|git|integration|agent|learning|system` (`.value`).
- `CommandPriority` (:28): `critical|high|medium|low`.
- `CommandParameter` (:37): `name, type, description, required=False, default=None, choices=None, flag=False`.
- `CommandCard` (:49): `command, icon, label, description, category, priority, handler, parameters=[], has_form=False, long_running=False, requires_confirmation=False, metadata={}`.
- `get_command_registry()` (:1398) → `CommandRegistry`; `.list_all()` (:874) → `List[CommandCard]`; `.categories` is `Dict[CommandCategory, List[str]]`; `.search()` exists.
- Handlers (e.g. `_handle_sync` :910) call `from .cli import handle_*_command` then
  `handle_*_command(root, Namespace(**args))`, return `{'error': ...}` on failure (CORE-6).
  **They call CLI handlers directly (still subprocess-free), NOT `card.handler` skipping — bridge
  will call `card.handler` which is the lib-calling wrapper.**

### workflow_engine.py
- `execute_workflow(root, workflow_id, config, resume=False)` (:884) — NO callback (see Open item 1).
- `list_workflows(root, config)` (:891) → `List[WorkflowDefinition]`.
- `WorkflowExecutor.execute(workflow_id, resume=False)` (:357) blocks; saves state after each step.
- `WorkflowExecution` (:80): `workflow_id, execution_id, status (WorkflowStatus), steps: Dict[str,
  StepExecution], started_at, completed_at, context, user_inputs, metadata`.
- `StepExecution`: `step_id, status (StepStatus: PENDING/RUNNING/COMPLETED/FAILED/SKIPPED), started_at,
  completed_at, output, error, retry_count, metadata`.
- `WorkflowDefinition` (:54): `id, name, description, category, steps: List[WorkflowStep], ...`;
  `WorkflowStep`: `id, name, description, handler, dependencies=[], optional, retry_count,
  validation_handler, rollback_handler`.

### store.py
- `write_snapshot(con, job, health=None, components=None, counts=None, severity=None, meta=None)`
  (:244) — `INSERT OR REPLACE INTO snapshots(ts, job, health, components, counts, severity, meta)`,
  JSON-serializes dicts to TEXT, commits internally. `time.time()` ts.
- `snapshot_series(con, job=None, limit=60)` (:264) — oldest→newest, `list[dict]`.
- `prune_snapshots(con, keep=0)` (:278) — keep=0 retains all (full-history).

### web_bridge.py line anchors (file = 2979 lines) — every edit site
- `_ok/_err` (:64-72). `_TTL_CACHE` (:87). `_warm_daemon` (:76).
- `/api/status` (:105), `/api/config` (:169), `/api/commands` (:178) + `_command_registry` (:184,
  argparse-based) + `_categorize` (:218). **GAP-04 replaces `_command_registry`+`_categorize`.**
- WS/jobs hub: `_jobs` (:235), `_ws_clients` (:236), `_loop` (:237), `_broadcast` (:240),
  `_schedule_broadcast` (:251), `_register_job` (:262), `_job_done` (:268), `_job_error` (:274).
  **GAP-01 inserts `_job_event/_job_start/_job_progress/_job_log/_job_done_ev/_job_error_ev/
  _job_cancelled_ev` after :260, adds `cancelled` flag to `_register_job`, `/api/jobs`+`/api/jobs/{id}`.**
- Daemon ops (OLD vocab `progress|result|error`): start :304-335, stop :338-358, restart :361-391.
- `daemon_auto_manage` (:394-407) — backend already done for GAP-12.
- WatchManager (:410-486) — already dotted (`watch.event`, `index.update`); DO NOT TOUCH.
- Config save/reset/reload (OLD `result|error`): save :815-820, reset :849-854, reload :874-885.
- `/api/export/ingest` (:1113) broadcasts `{"type":"event",...}` — change to `signals.ingested`.
- `/api/verify` (:1164-1189, OLD `result|error`) — change `result`→`verify.done`.
- Index sync :1248-1276, rebuild :1279-1306, verify :1309-1329, vacuum :1332-1352 (OLD vocab).
- Oracle: summary :1455, repo-summary :1467, suggest-context :1485, next :1500. **GAP-09 adds
  `/api/oracle/workflows` + `/api/oracle/workflows/{id}/run` after :1512.**
- Search :1540-1614 — tier filter :1594, kind filter :1596-1606 (backend ALREADY done for GAP-11).
- `_safe_context` (:1639) — has `budget_utilization` for GAP-09 budget dial; `/api/context` :1691.
- Quality: `quality_bundle` (:1895), `_health_breakdown` (:1942), gaps :1980, coverage :2004,
  `_quality_trend` (:2013, reads events kind='quality'), `/api/quality` :2027, findings :2036,
  trends :2065, `/api/snapshots` :2076, **quickwins POST :2092-2099 → GAP-05 makes it GET**,
  audit job :2107-2182 (uses `job.progress` :2116 / `job.done` :2171 / `error` :2177 — partial
  modern vocab; migrate to helpers + keep snapshot write :2157).
- Memory: overview :2365, facts :2373 (accepts `at` :2376 → `_facts_rows at_time` :2298),
  episodes :2384, recall :2393, patterns :2406, suggestions :2420, action :2437,
  consolidate :2457-2526 (uses `job.progress` :2466 / `memory.updated` :2515 / `error` :2521),
  clear :2533.
- Vis: `_VIS_CACHE` :2556, `_vis_get` :2570 (event-driven invalidation via events MAX(ts)),
  `_parse_payload` :2594 (tolerates str repr), `_events_series` :2613 (EVENTS-ONLY — GAP-08),
  overview :2693, **vis/trends :2701-2707 (GAP-08 repoint)**, git :2777, findings :2801, map :2818,
  signals :2843, graph :2851.
- **`/api/run` :2880-2920 (subprocess via create_subprocess_exec) + `_format_params` :2923-2933 —
  GAP-03 rewrites to in-process to_thread + adds `_command_table`/`_validate_params` before :2875.**
- **`cancel_job` :2936-2942 — flips status only, NO broadcast, NO cancelled flag → GAP-01 rewrites.**
- `ws_endpoint` :2946-2964 — handles only `ping`; **GAP-02 adds `subscribe {since}` reply.**
- SPA: DIST mount :2968-2979.

### Frontend (all fully read)
- `web/src/lib/api.ts` (884): `JobEvent` :41-47 (3-type → replace); `api` :49-60 (`getCommands()→
  CommandInfo[]`, `runCommand` :53, `cancelJob` :58); `daemonApi` :87-106 (`autoManage` :101 exists);
  `snapshotsApi` :198; `searchApi` :279 (`search(q,{k,tier,kind})` already accepts filters);
  `auditApi` :458 (`quickWins` does NOT exist; `trends` :473); `settingsApi` :700 (bundle/save);
  `oracleApi` :872-884 (no workflows). `CommandInfo` :26 = `{name, description, category, params}`
  with `CommandParam` :33 = `{name, type('string'|'int'|'float'|'boolean'), required, default?, help?}`.
- `web/src/hooks/useWebSocket.ts` (53): handlers array, no `since` replay; `send` returned.
- `web/src/stores/app.ts` (37): zustand pattern to mirror for `stores/jobs.ts`/`stores/events.ts`.
- `AppShell.tsx` (47): `useWebSocket` TODO stub :15-21 → replace with job upsert + EVENT_INVALIDATE.
- `CommandPalette.tsx` (177): `executeCommand` posts `{}` :101; rows built from `commands` (flat
  `CommandInfo[]` — must flatten `categories` after GAP-04); Enter handler :82-90.
- `OracleView.tsx` (368): `NextContextCard` :270-341, prediction static divs :324. `TOOL_ICON`/
  `TOOL_LABEL` :17-35. No `useNavigate` import yet.
- `MemoryView.tsx` (476): `FactsTab` :206-218 (no slider); `FactCard` :220-261 (validity info present);
  overview strip :131-155. `memoryApi.facts` accepts `at` (api.ts :527).
- `DaemonView.tsx` (163): daemon panel :48-94, no auto-manage toggle. Button helper :139.
- `SearchView.tsx` (262): search query :23-27 passes only `{k}`; filter row to add after search box :60.

## Implementation decisions locked
- **GAP-09:** broadcast `workflow.step` events from returned `WorkflowExecution.steps` after
  completion (no callback exists). Then `job.done`.
- **GAP-03:** call `card["handler"](ROOT, params)` inside `asyncio.to_thread`. Handler returns
  `{'error': ...}` on failure (CORE-6) — promote to RuntimeError when result is exactly
  `{"error": ...}`. **Before wiring, spot-check param-name parity for search/symbol/graph**
  (Open item 2). Remove `_format_params` + subprocess path.
- **GAP-01 migration:** daemon ops, config save/reset/reload, verify (→`verify.done`), sync/rebuild/
  verify-index/vacuum, audit, consolidate → all job broadcasts via helpers. KEEP existing secondary
  `index.update` / `memory.updated` events. `_register_job` gains `cancelled: False` + `logs: []`.
  `_job_done/_job_error` keep updating `_jobs`; add `_record_job_event` writer (fix the
  `duration_s` placeholder → `time.time() - _jobs[job_id]["started"]`).
- **GAP-02:** `/api/events` added after `_events_series` (:2628); `ws_endpoint` handles
  `subscribe {since}` → reply events after since; useWebSocket sends subscribe on open/reconnect.
- **GAP-04:** `/api/commands` returns `{categories:[{name, commands:[...]}]}`; keep `CommandInfo`
  shape per command so CommandPalette flatten works.

## Resume plan (exact next actions)
1. GAP-01 backend (insert helpers + cancel + /api/jobs after :260; rewrite cancel_job :2936;
   migrate all job broadcasts). 2. GAP-01 frontend (api.ts JobEvent/jobApi + stores/jobs.ts +
   JobToasts + AppShell wiring). 3. GAP-06 (JobHistory). 4. GAP-07 (EVENT_INVALIDATE + events store).
5. GAP-02 (endpoint + ws subscribe + useWebSocket replay). 6. Verify W1: `python -c "import
   cipkg.web_bridge as w; print(len(w.app.routes))"` + `npm run build` + `npm run lint`; flip
   GAP-01/02/06/07 in GAP-REPORT.md. Then Wave 2 (GAP-03/04), Wave 3 (GAP-08), Wave 4 (05/09/10/11/12),
   updating THIS section's progress at each wave boundary.
