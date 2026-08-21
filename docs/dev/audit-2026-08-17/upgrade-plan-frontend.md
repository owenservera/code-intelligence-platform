# Audit — upgrade-plan frontend (SPEC-16/17/18/19)

**Source of truth:** `web/src/**` (views, components, lib/api.ts, stores, App.tsx, hooks)
**Type-check:** `cd web; npx tsc --noEmit` → **exit 0** (green only because no upgrade code was added — NOT evidence of implementation).

## Verdict: NOT IMPLEMENTED in the frontend
None of PLAN-06…10 frontend work exists. The console is still a single-repo, flat-route SPA with zero project concept.

## Status table

| Phase / Piece | Claimed | Actual | Evidence | Notes |
|--------------|---------|--------|----------|-------|
| P6.1 store `activeProject`/`projects` | add to store | **absent** | `stores/app.ts:15-21` (AppState = status + commandPalette only) | No `activeProject`, `setActiveProject`, `setProjects` |
| P6.2 thread `?repo=` via `request<T>` | append repo | **absent** | `lib/api.ts:1-16` (no repo logic) | Every call repo-agnostic |
| P6.2 WS `?repo=` reconnect | `/ws?repo=` | **absent** | `hooks/useWebSocket.ts:25` (`/ws`, no query) | No project scope |
| P6.3 repo switcher in top bar | project select | **absent** | `TopBar.tsx:4-32` (only palette + status dot) | No dropdown |
| P6.4 `/projects` dashboard | view+route+nav | **absent** | no `ProjectsView.tsx`; `App.tsx:48-61` = SPEC-01..13 only; `LeftNav.tsx:16-28` no entry | `projectsApi` missing |
| P6.5 arbitrary-folder onboard | POST `/api/projects` | **absent** | `api.ts:899` only `onboardingApi.status`; no `projects` POST | OnboardingView unchanged for registry mode |
| P6.6 CLI `--project`/`--root` (GAP-04) | preselect | **absent** | `cli.py:723-726` only `--port/--host/--no-browser` | Flags missing |
| P6 GAP-06 per-project gate | gate per project | **absent** | `App.tsx:43` global `needs_onboarding`; no `activeProject` branch | Cross-project global wizard |
| P8.1–8.3 `RepoExplorer` rail + lazy tree | headless-tree | **absent** | no `RepoExplorer.tsx`; `AppShell.tsx:84` = `LeftNav` only | `treeApi` missing |
| P8.2 tree state in store | `activePath`/`expanded` | **absent** | `stores/app.ts` no tree state | — |
| P9.4 Review mode (DiffEditor + overlays + comments) | Monaco DiffEditor + glyph + JSONL | **absent** | `FileView.tsx:61` only `<FileEditor>`; no Review mode, no `DiffEditor`, no `glyphMarginClassName` | `api.ts` no `review`/`diff`/`at` |
| P10.4 CORE-55 WS union type | `CipEvent` union + dispatch | **absent** | `api.ts:55-90` `JobEvent` only; `useWebSocket.ts:43,51` casts all to `JobEvent`; `AppShell.tsx:20-35` `EVENT_INVALIDATE` has **no `file.changed` key** | `file.changed` never handled |
| P10.5 Timeline + blame gutter + live refresh + commit graph | structured feed, blame, live | **absent** | `FileView.tsx:251` `HistorySection` still plain `commits.map(...)` string list | `api.ts` no `edits`/`blame`/`git/log` |

## MISSING / NOT IMPLEMENTED (frontend)
- `activeProject` / `projects` state — `stores/app.ts`
- Repo threading through `request<T>` and WS — `api.ts`, `useWebSocket.ts`
- Project switcher UI — `TopBar.tsx`
- `/projects` dashboard view + route + nav entry — `App.tsx`, `LeftNav.tsx`
- `RepoExplorer` tree rail, `treeApi`, lazy `GET /api/tree` consumer — entire P8 frontend
- Review mode (DiffEditor, findings overlay, additive `reviews.jsonl` comments) — `FileView.tsx`, `api.ts`
- Timeline / blame gutter / commit graph / live `file.changed` refresh — `FileView.tsx`, `AppShell.tsx`, `api.ts`
- CORE-55 WS event-type union reconciliation
- CLI `--project` / `--root` preselect flags (GAP-04) — `cli.py`

## OBVIOUS ENHANCEMENTS / BUGS (relative to plan)
- **No frontend tests** for any of this (no `*.test.ts(x)` under `web/src/`) — acceptance "across reload" round-trips unverifiable.
- **Deep-link / `?repo=` gap:** with no `activeProject`, no way to deep-link or scope a session to a project; `?path=` (search→file) still single-repo only.
- **`request<T>` is the single chokepoint** (correctly flagged at plan-06:17) but never edited — adding repo scoping now requires touching the helper *and* every consumer, exactly the coupling the plan predicted.
- **WS `file.changed` silently dropped:** `AppShell.tsx:20-35` only invalidates known job/non-job keys; a `file.changed` event matches nothing and refreshes nothing (real-time requirement unmet even conceptually).
- **No Monaco lazy-load for DiffEditor** (plan-09 says lazy) — moot until Review mode built, but `monaco-editor` is already a full dep (`package.json:20`).
- **`HistorySection` couples to `fileApi.history`** returning raw commit strings; plan's structured timeline needs `fileApi.edits` which doesn't exist.
