# SPEC-15 — Cross-Cutting NFRs, Bridge Rules & Backend Additions

- **Requirement source:** `05-requirements.md` §3 NFR-1..8, §7.4 runtime, §7.5, ISSUE-104/107/110
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{base,store,lock,server,embed}.py`
- **Build order dependency:** all specs (this is the consolidation of NFRs + bridge conventions).

---

## 1. Goal & owner intent

The single source for NFRs and engineering rules every spec assumes: one port, concurrency
discipline, latency budgets, security posture, theming, perf budget, and the **`web_bridge`
module contract** (all backend additions across SPEC-02..14 live in one place). Also resolves
the runtime (§7.4) and records the cross-cutting CORE issues found along the way.

## 2. Runtime & architecture (from §7.4, grounded)

- **`cip web`** — one FastAPI process, port 8090 default (`[web] port`, CORE-1), localhost bind
  only (NFR-4). Serves compiled React build (NFR-1 static) + `/api/*` + `/ws`.
- **Daemon** — embedded, auto-managed by console (lazy start, warm-up status, stoppable);
  separate subprocess (Windows `taskkill /F /T` safety, CORE-13) with health polling (SPEC-03).
- **Heavy jobs** — SPEC-02 `JobRunner` (SPEC-14 add 2): background worker threads/processes
  streaming progress; never in-request (NFR-3).
- **SQLite** — single-writer respected via `lock.WriteLock` (`lock.py`) + read-only connections
  for UI reads (NFR-2).
- **Replacement targets** — legacy `web_server.py`/`dashboard.py`/`websocket_handler.py`/
  `server.py` surfaces removed once covered by new surface; additions to `lib/cipkg` in scope.

## 3. Non-functional requirements (NFR-1..8) — contract

| NFR | Rule | Where it lands |
|---|---|---|
| NFR-1 | One port (default 8090); WS same-origin `/ws`; static from compiled build | `[web]` config; FastAPI mount |
| NFR-2 | SQLite single-writer; heavy ops in workers; read-only connections for reads | `JobRunner`; `WriteLock`; read-only `connect` for GETs |
| NFR-3 | Reads <300 ms (cached stats); heavy ops return job id immediately | per-surface cache (30–60 s); job model |
| NFR-4 | localhost bind; no secrets logged; parameterized SQL; no eval/exec | server bind; logging redaction; existing patterns |
| NFR-5 | (from §3 as written) | see `05-requirements.md` NFR-5 |
| NFR-6 | Graph payloads capped/paginated (3D friendly); snapshots bounded writes | SPEC-09 caps; SPEC-04 snapshot batching |
| NFR-7 | (from §3) | see `05-requirements.md` NFR-7 |
| NFR-8 | (from §3) | see `05-requirements.md` NFR-8 |

*(NFR-5/7/8 read the exact clauses from §3 during build — listed here to keep the cross-cut
complete.)*

## 4. `web_bridge` module contract (all backend additions in one place)

Location: `lib/cipkg/web_bridge.py` (+ `web_bridge/` package if large). Rules:

1. **Imports core only** — never legacy web modules (`web_server`, `dashboard`, `websocket_handler`).
2. **Read-only DB on GET** — a dedicated read-only connection helper; writes go through the
   single-writer path (`WriteLock` or job worker).
3. **No dead endpoints** — every endpoint maps to a verified core function (each spec's §2 table).
4. **JSON event payloads** — `record_event` writes JSON payloads (CORE-55); never `str(dict)`.
5. **Caching** — per-surface cache map `{surface: (ttl, loader)}`; invalidate via WS `vis.refresh`
   groups (SPEC-14) and job completion hooks.
6. **Stable error shape** — `{ok:false, error:{code, message, core?: file:line}}` everywhere;
   UI surfaces friendly text + optional core pointer.
7. **N+1 avoidance** — batch `IN` lookups for symbol/node decoration (CORE-38); bounded
   result caps on all lists.
8. **All additions listed here**:

| Addition | Spec | Purpose |
|---|---|---|
| `command_table` + param merger + job runner + events writer | SPEC-02 | dispatch model (replaces broken registry handlers) |
| Watch/daemon managers | SPEC-03/04/14 | managed subprocess + thread wrappers |
| `snapshots` table + writer | SPEC-04/09 | trends + full-history retention |
| `graph_payload`/`graph_focus` | SPEC-05/09 | decorated graph payloads |
| `file_bundle` | SPEC-06 | deep panel single-roundtrip |
| `quality_bundle` + audit job | SPEC-07 | quality dashboard |
| `memory_overview` + consolidation job | SPEC-08 | memory lab |
| `vis_bundle`/`signal_window` | SPEC-09 | chart payloads |
| `config_schema`/`config_write`/`config_reload` | SPEC-10 | settings write-back |
| `export_stream`/`parse_results`/`tools_schema` | SPEC-11 | export + ingest |
| `onboarding_detect`/`install` | SPEC-12 | wizard |
| `oracle_bundle`/workflow job | SPEC-13 | intelligence rail |
| `WSEvents` hub + `JobRunner` | SPEC-14 | realtime |

## 5. Frontend conventions (from §7.3)

- **Stack:** React + TypeScript + Vite; shadcn/ui + Tailwind + Recharts; dark sleek theme
  (§7.1-17). Monaco code-split (SPEC-06) — loaded only when deep panel opens.
- **State:** tanstack-query for server data (cache + refetch on `vis.refresh`); WS client
  (SPEC-14) dispatches to query invalidation; lightweight stores for UI-local state.
- **Routing:** `command center` (home) → `/index` `/search` `/quality` `/memory` `/dashboards`
  `/settings` `/export` `/onboarding` `/file/:path`; Ctrl+K palette (SPEC-05) navigates all.
- **Perf budget:** bundle < 300 KB gz main; Monaco + 3D graph lazy; no layout thrash on WS
  storms (coalesce/requestAnimationFrame).
- **i18n:** English v1; token strings in a single file (reuse existing patterns if present).
- **Accessibility:** keyboard nav, ARIA on all charts (SVG titles), contrast for dark theme.

## 6. Security & ops (NFR-4 + §6)

- Bind `127.0.0.1` only (configurable, warn if 0.0.0.0).
- No API keys/secrets in the bundle; config values with `key/password/token` keys are masked in
  `GET /api/config` (write-back still writes real values).
- Parameterized SQL everywhere (already the rule in `store.py`); no `eval`/`exec` in new code.
- Log redaction: `base.log_swallowed` used (not `print`, CORE-52); `[logging] debug` gates detail.
- All destructive actions (rebuild, vacuum, clear memory, config overwrite) require confirm
  (already spec'd per surface) + non-destructive defaults.

## 7. Core issues / risks (flagged, grounded)

- **CORE-58 — read-only UI connections still create the DB file if absent** (`store.connect`
  with `CREATE IF NOT EXISTS`). Read paths must NOT write during onboarding/attach; the wizard
  creates `.cip` explicitly (SPEC-12), then reads. *(New issue.)*
- **CORE-59 — `server.py` (legacy JSON-RPC) overlaps with the new REST surface; port 8080 vs
  `[web] 8090`.** MCP (`[mcp] port=8080`) is a separate protocol the console may expose via
  SPEC-02 tools; avoid port collisions when daemon/MCP auto-start (§7.4). *(New issue; NFR-1.)*
- **CORE-60 — snapshot writer must run under the same WriteLock discipline as sync/audit.**
  Two jobs writing snapshots concurrently → SQLite busy. → Snapshot writes are queued via
  `JobRunner` (SPEC-14) or serialized on a lock. *(New issue; NFR-2.)*
- **Watch: `[web]` section missing from config.default.toml (CORE-1)** — every spec references
  `[web] port/host/theme`; it's introduced by SPEC-10/12 write-back. Flagged once here.
- **Watch: Windows path handling** — `file://` URIs in LSIF/export, `\` vs `/` in paths:
  bridge normalizes to `/` (existing core uses `/`; `base.py:192` replace os.sep).

## 8. Acceptance checks (from §3 / §7.4 / §7.5)

- [ ] `cip web` serves app + API + WS on one port; static from build; no legacy web modules.
- [ ] All heavy ops are jobs; reads <300 ms cached; single-writer respected.
- [ ] `web_bridge` module follows contract (no legacy imports, JSON events, batch lookups).
- [ ] Frontend conventions applied (lazy Monaco/3D, query cache + WS invalidation, dark theme).
- [ ] Secrets masked in config API; destructive ops confirm; localhost bind.
- [ ] CORE-58/59/60 handled (read-only connect, port isolation, snapshot write serialization).
