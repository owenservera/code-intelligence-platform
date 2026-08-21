# Requirements — CIP Web Console v1 (full capability)

**Status:** Approved baseline from owner interview
**Date:** 2026-08-15
**Source:** `00-goals-and-decisions.md` + interview answers.

---

## 0. Owner decisions (verbatim intent)

1. **Full capability**: every command + every read view exposed in the browser — the
   web console is the primary management surface. Not a read-only dashboard.
2. **Launch & manage the daemon from the UI** — one "full server" story: start the web
   server and control the daemon (start/status/stop/health) from the interface.
3. **No auth, localhost** — single-user internal tool.
4. **Command palette + auto-generated forms** for execution; live progress via WS.
5. **Event-driven live** state; stats auto-refresh on change.
6. **Visualizations: "everything", top-of-the-line** — including **3D interactive code
   graph** with visual indicators on nodes/links.
7. **Command-centered core, designed to be extensible** — the shell is built around the
   full command registry so new capabilities drop in automatically.
8. **"Assume 100% of code is vibe-coded"** — design the complete chart suite we'd want
   as if every data source already existed; list what backend additions each needs.
9. **gapfill: validate, keep the good ones, document.**
10. **Dark dev-tool** design language.

---

## 1. Product principles

- **Command-first**: the app is a console whose source of truth is the command registry.
  Every capability is a command with a form; dashboards are views over command results.
- **Extensible core**: adding a command to `command_registry.py` (or the bridge table)
  automatically gives it a palette entry, a form, a job runner, and WS progress.
- **Stateful**: backend owns an `IndexSnapshot` + `Job` registry; UI mirrors via Zustand,
  updated by WS pushes, hydrated by REST on load.
- **Non-blocking**: heavy ops (sync, embed, audit, consolidate, rebuild, export) run in
  background workers with progress streaming — never block an HTTP request.
- **Direct calls, not subprocess**: the bridge calls lib functions directly (like
  `server.py:call_tool`), avoiding CLI dispatch bugs and shell overhead.

## 2. Functional requirements

### FR-1 App shell
- Single FastAPI server (one port) serving REST + WebSocket + compiled React assets.
- Left nav or top bar with views; global command palette (Ctrl+K) reachable anywhere.
- Connection/daemon/index status indicators always visible.
- Dark dev-tool theme (shadcn/ui + Tailwind).

### FR-2 Command center (palette + forms + execution)
- Palette lists all commands grouped by category (from `CommandRegistry`), with fuzzy search.
- Selecting a command renders an auto-generated form from its parameters
  (type, required, default, enum choices, description).
- Execute → creates a `Job`; runs lib call in a worker; streams stdout/status/progress
  over WS; panel shows live log + final structured result.
- Job history list (recent jobs, status, duration, result summary); re-run.
- Destructive ops (rebuild, vacuum, export overwrite) require an explicit confirmation
  toggle in the form.

### FR-3 Daemon & server management
- Start web server (this app) — already running by definition.
- Daemon panel: status (running/pid/port/health/uptime), start, stop, restart,
  auto-start toggle, log tail. Uses `daemon.py` functions directly.
- Embedding service status: backend, model, dim, warm/loading, queue depth, last latency
  (`embed_ping`/`embedder`).

### FR-4 Index management
- Index stats live (files/symbols/chunks/edges/vectors, last_sync, freshness).
- Trigger sync (full / reembed), index, rebuild, vacuum, verify-index — with progress.
- Watch mode indicator; live updates as watch/sync runs.

### FR-5 Search & navigation
- Global search box (hybrid search) with dropdown; deep search view with filters
  (type, tier, k, backend-matched badges).
- Symbol lookup, graph traversal around a symbol/file.

### FR-6 Deep file panel
- Click file/symbol → panel: source viewer (Monaco, syntax highlighting), impact/blast
  radius viz, audit findings for the file, git history, hot/cold indicators, related
  symbols graph, tests linking in/out.

### FR-7 Quality & audit
- Audit run with progress; findings explorer: filter by severity/rule/path,
  per-file grouping, quick-wins ranked list, quality gate status.
- Rule catalog (from `stack/rules.py` + custom rules) with descriptions.

### FR-8 Memory lab
- Temporal knowledge graph: facts list with validity/confidence + graph view;
  add/recall/update fact UI.
- Episodic memory: episode list/timeline, outcomes, similar-episode search.
- Consolidation: status, last run, run-now, lookback config display.
- Agent memory key/value recall view.

### FR-9 Visualization suite (the full "everything" chart set)

> Per owner: design the complete chart suite as if all data exists. Backend additions
> needed are listed per chart group.

**A. Health & score**
- A1 Health score radial gauge + components breakdown (coverage/quality/freshness/complexity).
- A2 Health score trend over time (snapshots table).
- A3 Quality gate status (pass/fail + why).

**B. Index & growth trends**
- B1 Index size growth: files/symbols/chunks/edges/vectors stacked or multi-line over syncs.
- B2 Vector coverage % trend (vectors/chunks).
- B3 Freshness timeline (last_sync gaps).

**C. Git & activity**
- C1 Commit velocity (12-week bar/area).
- C2 Hotspots: horizontal bar of churn-weighted files + quadrant scatter (churn vs size).
- C3 Co-change pairs graph (edges kind=co_change) — highlight coupled files.
- C4 Activity feed timeline from events table (ingest/sync/memory ops).

**D. Quality & debt**
- D1 Findings by severity (donut/bar) + by rule (horizontal bars).
- D2 Findings trend: opened vs fixed over time (needs snapshot/audit history).
- D3 Technical debt by category (test/complexity/duplication/docs) — stacked.
- D4 Quick wins table with effort/severity chips.
- D5 Per-language breakdown (files/symbols by language).

**E. Code graph (3D)**
- E1 3D interactive force graph of symbols/edges with node kind icons + severity/link
  coloring (visual indicators). Zoom/pan/rotate, click-to-expand, search highlight.
- E2 Optional 2D fallback for very large graphs (LOD: render subgraph on demand).

**F. Memory & signals**
- F1 Temporal facts timeline (valid_from → valid_until), confidence bubbles.
- F2 Episodes timeline colored by outcome.
- F3 Broken signals: failing tests + type errors over 14d (list + per-file counts).
- F4 Embedding panel: model, backend, dim, vector coverage gauge, warm state, queue.

**G. Repository map**
- G1 Zoomable directory tree-map with hot/cold + file count coloring.
- G2 Subsystem overview (summarize.map_).

### FR-10 Settings & config
- View/edit supported config sections (index, embed, retrieval, memory) — read for v1,
  allow saving to `.cip/config.toml` with reload notice (write-later decision).

### FR-11 Export & integration
- Export (json/lsif/markdown) with download; tools schema viewer; ingest test/typecheck
  results (paste/file upload for vitest/jest/pytest/tsc/generic).

## 3. Non-functional requirements

- **NFR-1 Port**: one port (configurable, default 8090); WS same origin `/ws`; static
  served from compiled React build.
- **NFR-2 Concurrency**: SQLite single-writer respected; heavy jobs in background
  workers; read-only DB connections for UI reads.
- **NFR-3 Latency**: API responses < 300ms for reads (cached stats); heavy ops return a
  job id immediately.
- **NFR-4 Security**: localhost bind only; no secrets logged; parameterized SQL (already
  the norm); validate all inputs to lib calls.
- **NFR-5 Robustness**: WS reconnect + backoff; job crash → error state with traceback
  shown; server survives job exceptions.
- **NFR-6 Performance**: graph payloads capped/paginated (3D render friendly); snapshots
  table written once per sync/audit, not per-request.

## 4. Out of scope (v1) / deferred

- Auth/users/RBAC (localhost tool).
- Editing source files in the browser (viewer only).
- Full terminal emulator (palette+forms instead; revisit later).
- Auto-watch reindex triggering (indicator only in v1).
- gapfill command curation: validate now, gate low-value ones behind "advanced".

## 5. Backend additions required (data that doesn't exist yet)

| Need | Addition |
|---|---|
| A2/B1/B2/B3/D2 trends | `snapshots` table (ts, health, components, stats, severity, broken) written on sync/audit/consolidate. |
| C4 activity feed | events table exists; add cleaner typed events during new-job runs. |
| D5 per-language | add `language` GROUP BY endpoint (data exists in `files.language`). |
| E1 3D graph scale | cap initial payload; add `/api/graph/focus` expansion endpoint. |
| F1 temporal viz | facts already carry valid_from/confidence; add count/series endpoint. |
| Daemon log tail | add `daemon.py` log-read helper (append-only file). |

## 6. Acceptance criteria (v1 done =)

- [ ] `cip web` starts one server; console opens at 127.0.0.1:8090.
- [ ] Every command in the registry is reachable via palette, has a working form, and
      executes with live progress + result.
- [ ] Daemon start/status/stop and embedding status work from the UI.
- [ ] Sync/index/rebuild/audit/consolidate run with visible progress and update stats live.
- [ ] Search, symbol, graph (3D), impact, deep file panel, memory lab, findings explorer
      all functional.
- [ ] Snapshot table writes; health/index trends render.
- [ ] No dead buttons (every visible control does something).
- [ ] Old split-brain dashboard removed; single server serves everything.

---

## 7. Addendum — Full-Control Console (owner interview round 2, additive)

> **Status:** Adds to the baseline above; **nothing in §0–§6 is removed or weakened.** Where a
> round-2 answer refines a baseline decision, it is stated explicitly and supersedes only
> that one point.
> **Date:** 2026-08-15 (same session, second interview pass)
> **Driver:** intent = design the fully-powered frontend giving the owner **full control of CIP**
> with **advanced tooling**, **visualization**, and **reporting of the activated repo** — not a
> bug-fix exercise.

### 7.1 Owner decisions (round 2 — verbatim intent, additive)

1. **Single repo, simple.** Console attaches to one activated repo (its `.cip`). No multi-repo
   switcher in v1 — but state and routing are designed repo-scoped so a switcher can be added
   later without rework.
2. **Command center is the home screen.** The app opens on the command palette; every dashboard
   is a view opened from it. Search is one keypress away (Ctrl+K), not a separate landing.
3. **Activation = wizard + direct attach.** If `.cip` exists → attach and open live state.
   If missing → guided onboarding wizard. The wizard must be **intelligent AND manually
   configurable**: auto-detects stack/language/gatekeeper outcome, but every step can be
   overridden by hand (include/exclude, profile, index/embed tuning) before first sync.
4. **Designed for pure vibe coding.** Zero-friction is the bar: everything one click away, no
   dead controls, auto-generated forms with sane defaults. "Everything should be able to
   understand state, and **any capability the CIP system has should be executable from the
   frontend**."
5. **The console is an oracle + control surface, NOT a code editor.** No in-browser source
   edit/save. The deep file panel is a **read-only** Monaco viewer. The value is *seeing what
   CIP knows* and *making CIP act*.
6. **Report = a living visual surface**, not a static artifact. Live visuals of what is
   happening in the repo; full visual of the index; intelligent flagging. **No export
   artifacts in v1** (the registry `export` command stays wired but is not promoted).
7. **3D code graph is the flagship visualization.** Zoom/pan/rotate, click-to-expand, node-kind
   icons, severity/link coloring, search highlight. 2D remains as LOD fallback for large graphs.
8. **Full trend history.** Snapshots written on sync/audit/consolidate and **retained
   indefinitely** (pruning only via explicit vacuum/`--days`).
9. **Intelligent flagging principle:** *show whatever intelligence the CIP system generates in
   a visually intuitive way.* No curated allow-list — any payload the system produces (health,
   findings, dead code, broken signals, anomalies, recommendations) must have a visual surface.
10. **Full config write-back.** Edit supported sections and save to `.cip/config.toml` from the
    UI (with reload notice). Resolves FR-10's "write-later" caveat to *write now*.
11. **Full memory lab.** Temporal facts timeline, episodic outcomes, consolidation control,
    agent-memory KV — all interactive.
12. **Realtime.** Live progress streaming, stats auto-refresh on change, daemon/embed status
    always current. No manual reloads.
13. **Visual language: sleek modern dev-tool** (dark) — generous spacing, big gauges, elegant
    premium charts (shadcn/ui + Tailwind + Recharts), not dense-grey or terminal-core.
14. **Include staff-engineer briefing notes.** The auto-generated narrative (refactor/risk/
    blocker/opportunity/health/pattern/ok) from `dashboard.py:briefing` is surfaced as a
    first-class view.
15. **Runtime design delegated.** Owner: "you design — assume you can upgrade anything in the
    CIP system to accomplish our goals." §7.4 contains the proposed launch model under that
    authority.

### 7.2 New functional requirements (additive to §2)

**FR-12 — Onboarding wizard (repo activation)**
- W1 Detect: stack/language detection, multi-root notice, gatekeeper admission preview
  (`admission_report`: what will index/skip and why).
- W2 Configure: repo profile selection, include/exclude overrides, index/embed tuning,
  `[meta]`/schema review — every default editable before commit.
- W3 Init: if `.cip` missing → `init` from the wizard (config + data dir + meta).
- W4 First sync: full sync + embed as a background job with live progress + ETA.
- W5 Verify: post-sync landing — stats, sample search results, health, graph seed; "did it
  work?" at a glance; re-tune loop back to W2.

**FR-13 — Oracle / intelligence surface**
- One view (or top-level section) that renders **any** intelligence CIP produces:
  briefing notes, health components, critical/high findings, dead/circular signals, broken
  test/type signals, hotspots, recommendations, quick wins, gapfill outputs, anomalies
  (embedder fallback, config drift, custom-rules active).
- Each item is a card with severity/kind coloring, one-click drill-down to its source panel,
  and a run/refresh action where one exists.
- "Needs attention" ranked list is the default sort of this surface.

**FR-14 — Real-time contract (explicit)**
- WS pushes for: job progress/log/result, index snapshot deltas, health recompute, audit
  findings refresh, memory events, daemon/embed status. REST hydrates on load + on-demand.
- Lightweight 30s poll fallback for git branch / dirty-file count only.

**FR-15 — Config editor (write-back)**
- Effective-config viewer (source-annotated: default → profile → `.cip/config.toml`) +
  edit form for `index`, `embed`, `retrieval`, `memory` (and any section the registry knows).
  Save → writes `.cip/config.toml` → shows "reload required" and offers a daemon/state reload.

### 7.3 Resolved open decisions (from `09-bugs-and-issues.md` ISSUE-10x)

| Issue | Resolution (from round 2) |
|---|---|
| ISSUE-101 health source of truth | Both surfaces reconcile through one **snapshot** write; health components must be truthful — the bridge wires real audit-severity counts (fix the dead `list_findings` path) rather than shipping a constant-80 quality bucket. |
| ISSUE-102 findings trend integrity | Trends render from snapshot history; the audit close-query is fixed so only findings whose rule actually ran can be auto-closed. |
| ISSUE-103 root threading | Hard rule: bridge pins one `root`; every lib call gets explicit `root=`. (Single-repo scope makes this simple.) |
| ISSUE-104 embed/long-job UX | Background job + progress + ETA + crash traceback + embedder-resolution indicator (local/daemon/hashing/warm). |
| ISSUE-105 gapfill validation | Keep visible per §7.1(9) "show whatever CIP generates"; gate low-value outputs behind an "advanced" toggle rather than hiding. |
| ISSUE-106 stack table ensure | Lazy `ensure()` on read + a visible "prepare stack" job state in the command runner. |
| ISSUE-107 snapshot contract | Granularity: sync/audit/consolidate; retention: **full/indefinite**; written off the hot path. |
| ISSUE-108 3D graph contract | Flagship; initial payload capped + `/api/graph/focus` expansion; node-kind icons + severity colors on nodes/links. |
| ISSUE-109 external findings tagging | External findings (ESLINT:/custom/tauri) carry a source badge and are never auto-closed by rules audit. |
| ISSUE-110 daemon/embed panel | Auto-managed daemon; panel shows {pid,port,uptime,warm,model,dim,queue,latency} + log tail. |

### 7.4 Runtime proposal (owner-delegated design authority)

Goal: one command, one port, zero ceremony, "best in class" feel.

- `cip web` → single FastAPI process serving REST + WS + compiled React SPA on **one
  configurable port (default 8090)**, localhost bind.
- **Embed daemon is auto-managed** by the console: lazily auto-started on first embedding
  need (with warm-up status), health-checked, shown in the daemon panel, and stoppable/restartable
  from the UI. Manual `cip daemon` workflows still work; the console never requires them.
- Heavy jobs (sync, embed, audit, consolidate, rebuild, export) run in background workers with
  progress streaming; HTTP returns a job id immediately (NFR-3).
- Read-only SQLite connections for UI reads; single-writer respected for jobs (NFR-2).
- Remove the old split-brain surfaces (`web_server.py` dashboard, `dashboard.py` mission
  control) once the new console covers their reads; acceptance = one server serves everything.
- Where the goal requires it, **backend additions in `lib/cipkg` are in scope** (snapshot table,
  daemon log-tail helper, truthful health components, typed event emission) — this is an
  explicit design authority, not a limitation.

### 7.5 Additional acceptance criteria (additive to §6)

- [ ] `cip web` starts one server; console opens at 127.0.0.1:8090 on the **command center**.
- [ ] Repo with `.cip` attaches directly; repo without it goes through the wizard (detect →
  configure → init → sync → verify) and lands on a working console.
- [ ] Every registry command is executable from the frontend with live progress + structured
      result (no dead buttons; "no capability exists only in the CLI").
- [ ] 3D code graph is flagship: click-to-expand, kind icons, severity coloring, search
      highlight, 2D LOD fallback for large payloads.
- [ ] Oracle surface renders any CIP intelligence payload (briefing, findings, dead/circular,
      broken signals, hotspots, recs, quick wins, gapfill, anomalies) with drill-down.
- [ ] Health components are truthful (quality not pinned at 80; security bucket populates).
- [ ] Snapshot history grows unbounded by default; health/index/findings trends render from it.
- [ ] Config editor saves to `.cip/config.toml` and triggers a reload notice.
- [ ] Source viewer is read-only Monaco; no edit/save affordance exists.
- [ ] Memory lab fully interactive (facts timeline, episodes, consolidation, agent KV).
- [ ] Daemon auto-manages embedding; panel is live with log tail.
- [ ] Realtime: job progress + stats update via WS without manual refresh.
