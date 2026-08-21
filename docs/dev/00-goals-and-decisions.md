# CIP Web Console — Goals & Design Decisions (v0)

**Status:** Draft — living document. Updated as research progresses.
**Last updated:** 2026-08-15

---

## 1. The Problem

CIP (Code Intelligence Platform) currently exposes its full capability through:

- A **CLI** (`bin/cip`) with ~52 command handlers in `lib/cipkg/cli.py`
- A **MCP/JSON-RPC server** (`lib/cipkg/server.py`) — text-interface focused
- A **Textual TUI** (`lib/cipkg/terminal_dashboard.py`)
- A **read-only web dashboard** (`lib/cipkg/web_server.py` + `lib/cipkg/dashboard.py` + `lib/cipkg/static/`)

The web surface is the weakest. `web_server.py` is built on Python stdlib `http.server`
(`HTTPServer` + `SimpleHTTPRequestHandler`) with a hand-rolled WebSocket layer on a
threading base. The frontend is vanilla JS (8 hand-rolled modules) covering only
**6 API calls** (search, impact, memory list/consolidate/clear, file view).

**Result:** the full power of the system — indexing, embedding, analysis, auditing,
memory consolidation, gap-filling, daemon management, command execution — is **not**
reachable from a browser. The dashboard is a read-only viewing surface.

## 2. The Goal (as stated by the owner)

> "I want the **full capability** of this system available in the **web interface**
> with **advanced tooling**, **stats dashboard visualizations** etc, and **fully
> interactive with a stateful repo index**."

Concretely:

1. **Every** CLI command (the full ~52-handler surface) available in the web UI,
   with proper parameter forms and live output.
2. **Advanced tooling**: search, symbol graph, impact analysis, audit, memory
   explorer, gap-fill, file viewer, index management.
3. **Stats dashboard visualizations**: health score, coverage, quality trends,
   embedding/索引 metrics, event timelines.
4. **Fully interactive + stateful**: the dashboard reflects live index state —
   sync/embed/analyze progress streams over WebSocket, daemon status, in-memory
   state that updates as the backend works.

## 3. Design Decisions (made so far)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Backend → FastAPI** (new web surface) | Async, native WebSockets, Pydantic validation, auto OpenAPI docs. Replaces `web_server.py`/`dashboard.py`'s `http.server` base. |
| D2 | **Frontend → Vite + React + TypeScript SPA** | Best fit for stats dashboards, real-time WS state, rich tooling. |
| D3 | **Component/UI stack**: shadcn/ui + Tailwind + Recharts + Zustand + TanStack Query | Proven stack for data-heavy management consoles. |
| D4 | **Next.js rejected** | No SSR/SEO/Node-backend need; adding a second language + runtime for zero backend benefit. |
| D5 | **Core `lib/cipkg` stays intact** | The value is in the Python core (indexer, retrieve, analysis, memory, gapfill). Only the web layer is rebuilt. |
| D6 | **Frontend served as compiled static build by FastAPI** | Single server to run; no CORS gymnastics, no separate static hosting. |
| D7 | **Command bridge endpoint** (`/api/commands/*`) | Expose the existing `command_registry` (CommandCard metadata) as validated REST/WS so the UI can render and execute the full CLI surface dynamically. |
| D8 | **WebSocket `/ws`** for live events | Indexing/embed/sync/memory/daemon progress pushes state to the UI. |
| D9 | **MCP server (`server.py`) untouched** | Separate surface; keep working as-is. |
| D10 | **`gapfill.py` commands under scrutiny** | Owner suspects it "might be junk." Validate value before wiring into the new UI; drop or gate if low-value. |

## 4. Target Architecture (v0 sketch)

```
lib/cipkg/  (core — unchanged)
   └── FastAPI app (new surface; replaces web_server.py / dashboard.py / static/)
         ├── REST:  /api/commands/*   (full registry, param-validated execution)
         ├── REST:  /api/*            (search, graph, impact, audit, memory, stats, config…)
         ├── WS:    /ws               (index/embed/sync/memory/daemon events)
         └── static: Vite+React SPA   (compiled build served here)
server.py (MCP / JSON-RPC) — untouched, separate surface
```

## 5. Open Questions (to resolve during research)

- Q1: Exact port strategy (keep 8765/8080/8081 split? consolidate?).
- Q2: What the "stateful repo index" contract is — is state in SQLite/`store.py`
  (durable) plus an in-memory `dashboard_state.py` (ephemeral)? How do we push updates?
- Q3: Which gapfill commands survive (validate `coverage/dead/circular/blame/score/…`).
- Q4: Embedding runs are heavy (torch + sentence-transformers) — run in-process with
  backpressure, or offload to the daemon?
- Q5: Auth — internal single-user tool (no auth) vs token-gated?

## 6. Research Log (sequential, ongoing)

Research is being done sequentially; each finding lands as a new numbered doc in
`docs/dev/`. This file stays as the top-level anchor.

- [x] `01-repo-overview.md` — full module inventory + roles
- [x] `02-web-layer-current.md` — web_server / dashboard / static analysis
- [x] `03-cli-and-registry.md` — command surface, registry, adapter, executor
- [x] `04-data-and-state.md` — store, memory, embedding, dashboard_state
- [x] `05-requirements.md` — approved v1 requirements (from interview)
- [x] `06-system-log.md` — features, configs, outputs, command layer, API (system log)
- [x] `07-intel-deep-inspection.md` — deep-dive intel from `cip-inntel.md` (v2: full 7179-line log read) + live `.cip` inspection; bugs + architecture + gapfill/stack/analysis internals
- [x] `09-bugs-and-issues.md` — LIVE bugs & issues log (maintained through the design session; supersedes the ad-hoc bug list)
- [x] `specs/00-spec-index.md` — per-requirement truth-grounded build specs (fresh web build; grounded in CIP core, not legacy web). All 16 specs (00–15) written and grounded; one spec per FR, sequential. SPEC-01..15 status = active.
- [ ] `07-api-design.md` — REST + WS endpoint contract (next; consolidate SPEC-04 §4 endpoints into the API doc)
- [ ] `08-migration-plan.md` — phased roadmap (next after 07)
