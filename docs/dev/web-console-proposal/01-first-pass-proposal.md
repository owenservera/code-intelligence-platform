# First-Pass Proposal — Web Console Dev-Surface Features

**Status:** PROPOSAL (first pass, not yet approved / not built)
**Date:** 2026-08-17
**Scope:** three frontend features on the CIP Web Console
  1. VS Code-style repo file-system explorer
  2. File review renderer (diff + inline review)
  3. Real-time code-edit history ("etc." surface)

**Grounding rule:** every claim about the current system is verified against source
(`file:line`) or the live `.cip` DB — same rule as `docs/dev/specs/00-spec-index.md`.
This is a **proposal** doc, not a spec: it records the first-pass design so it can be
reviewed, trimmed, or re-scoped before landing specs under `docs/dev/specs/`.

---

## 0. Why this, why now

The console today is an **oracle + control surface** (SPEC-06 §1: read-only viewer, no
edit/save). That identity is preserved — none of these features make the console a code
editor. What they add:

- **Explorer** gives a physical, browsable entry into the repo instead of requiring a search
  hit first (today files are reached via `SearchView` → `/files?path=`).
- **Review renderer** turns "what changed and does it break things" into a visual, reviewable
  flow (diff + inline findings), reusing CIP's existing impact/audit data.
- **Real-time history** makes the console feel live about what is changing on disk, which CIP
  already watches (`watchApi`, fs-watch) but does not surface in the UI.

---

## 1. Current system (verified surface)

| Layer | Verified facts |
|---|---|
| Frontend | React 19 + Vite + TS + Tailwind 4 + Monaco (`@monaco-editor/react` 4.7) + React Router 7 + Zustand + React Query (`web/package.json`). `FileView` renders read-only Monaco + intelligence rail; `FileEditor` is hard-coded `readOnly: true` (`web/src/components/file/FileEditor.tsx:50`). |
| Backend | FastAPI `web_bridge.py` serves `/api/*`, `/ws`, and the built SPA. Bridge is **additive-only, read-only on GET** (`web_bridge.py:11`). Every response uses the `_ok`/`_err` envelope (`web_bridge.py:64,68`). |
| Realtime | `useWebSocket` hook (`web/src/hooks/useWebSocket.ts:10`) auto-reconnects and dispatches `JobEvent`s; wired in `AppShell.tsx:15`. Backend broadcasts via `_schedule_broadcast` (`web_bridge.py:251`); fs-watch emits `watch.event` (`web_bridge.py:437–483`). |
| Repo data | `commits` + `commit_files` tables (`lib/cipkg/store.py:46`), `signals` (`store.py:51`), populated by `gitindex.git_index` (`gitindex.py:8`). `retrieve.history` (`retrieve.py:374`) and `stack.impact.impact_diff` (`stack/impact.py:116`) already shell out to git. |
| Navigation | `SearchView` opens files with `<Link to={'/files?path='+...}>` (`web/src/views/SearchView.tsx:139`). |
| Proxy | Vite proxies `/api` → `:8090` and `/ws` (ws) (`web/vite.config.ts:18–24`). |

**Key gaps found:**
- No endpoint lists directory contents → no tree can be built (`/vis/map` returns only
  aggregated dir totals, `web/src/lib/api.ts:620`).
- No diff endpoint and no "file at commit" content endpoint.
- History UI is a static list of git-log strings (`FileView.tsx:251` `HistorySection`);
  no live refresh when the file changes on disk, and no per-file edit timeline.

---

## 2. Feature 1 — VS Code-style repo file explorer

### 2.1 UX contract
- Left-hand panel (in `FileView`, or a new `ExplorerView` route) showing the repo tree:
  chevrons, indent guides, folder/file icons, lazy expansion per directory.
- Per-file badges where cheap to compute: findings count, symbol count, modified-in-last-N-days.
- Clicking a file opens `/files?path=` (existing deep panel) and highlights it as `activePath`.
- Honours the same ignore set as the indexer so the tree matches what CIP indexes.

### 2.2 Backend (new, additive)
- `GET /api/tree?path=<dir>` → one level:
  `{path, dirs: [{name, path}], files: [{name, path, ext, size, lines}]}`.
  - Root call uses `ROOT` (`web_bridge.py:36`); nested calls are relative and must be
    sanitized against traversal (`..`, absolute) — security rule from AGENTS.md.
  - Reuse the exclusion set from `repo_map._collect_source_files` (`repo_map.py:85`):
    `.git, node_modules, __pycache__, .venv, venv, dist, build`.
  - Optional `badges=1` → join `findings`/`symbols` counts per file (`store.py` tables).
- Nothing in core CIP changes; the bridge walks the FS (like `context_manager.py:259` already
  does). Keep it stateless and cache the listing by `(path, mtime)`.

### 2.3 Frontend
- New `web/src/components/explorer/RepoExplorer.tsx` (recursive `DirNode`/`FileNode`
  components). Follow existing style: `lucide-react` icons, Tailwind tokens
  (`bg-surface`, `text-text-secondary`), `SectionShell`-style headers.
- State: extend `web/src/stores/app.ts` (Zustand) with `expandedDirs: Set<string>`,
  `activePath: string | null`, `toggleDir`, `openFile`.
- API client: add `explorerApi.tree(path, badges?)` to `web/src/lib/api.ts`.
- Optional: `ExplorerView` route in `App.tsx:47` + `LeftNav.tsx:16` nav item.

---

## 3. Feature 2 — File review renderer

### 3.1 UX contract
- A "Review" mode on the file panel that shows a **side-by-side diff** (Monaco diff editor —
  already bundled, no new dependency) and/or **inline review** of the current file.
- Inline review = open `findings` overlaid on the editor as Monaco decorations/markers
  (click → jump to rule details in the rail), with per-finding acknowledge/ignore states.
- Diff base selectable from the existing history list (commit → commit, or working tree vs ref).
- Stays read-only; review actions dispatch as jobs where core supports it (SPEC-02 pattern),
  never writes files directly.

### 3.2 Backend (new, additive)
- `GET /api/file/diff?path=&base=<ref>` → `{path, base, diff}` (unified diff string).
  Use `git diff <base> -- <path>` with `--` terminator (mirrors `impact_diff`, `stack/impact.py:116`).
- `GET /api/file/at?path=&ref=<commit>` → file content at a commit via `git show <ref>:<path>`
  (for the "modified" side when reviewing an old commit vs working tree).
- `GET /api/file/review?path=` → `{path, findings:[...]}` — already available via the base
  bundle (`web_bridge.py:1787`, `file_bundle` returns `findings`); expose a focused endpoint
  only if the bundle is too heavy for the overlay.
- All git calls go through `subprocess` with `cwd=ROOT`, `timeout`, and path sanitization
  (same pattern as `retrieve.history`, `retrieve.py:394`).

### 3.3 Frontend
- Extend `web/src/components/file/FileEditor.tsx` to support a `mode: 'view' | 'review' | 'diff'`:
  - `view` = current read-only editor.
  - `diff` = `@monaco-editor/react` `<DiffEditor original modified readOnly>` (component is
    already installed; needs a lazy `import()` like `FileView.tsx:10`).
  - `review` = current editor + `editor.createDecorationsCollection()` / markers built from
    `bundle.findings` (see `api.ts:338` `FileFinding` shape).
- Wire `HistorySection` (`FileView.tsx:251`) so selecting a commit sets the diff base; a
  toggle in the file header switches `view` ↔ `diff`/`review`.
- API client: add `fileApi.diff(path, base)` and `fileApi.at(path, ref)` to `web/src/lib/api.ts`.

---

## 4. Feature 3 — Real-time code-edit history

### 4.1 UX contract
- A per-file **timeline** on the file panel: recent git commits + watch events + CIP
  `signals` for that path, newest first, with the "what" (message/kind) and "when".
- The open file **auto-refreshes** when the fs-watch reports it changed on disk.
- A small "live" indicator shows the watch connection state (reuse `StatusBar`/`TopBar`).

### 4.2 Backend (new, additive)
- `GET /api/file/edits?path=` → `{path, timeline: [{ts, kind: 'commit'|'watch'|'signal', ...}]}`
  merging `commits`/`commit_files` (`store.py:46`), `events`/`signals` (`store.py:37,51`), and
  recent watch events.
- Extend the existing watch broadcast to carry the changed path: the `watch.event` emission
  (`web_bridge.py:437–483`) already fires on fs changes — add `{path}` to the payload and emit a
  dedicated `file.changed` event so clients can filter without re-parsing.

### 4.3 Frontend
- Add a `EditHistorySection` to `FileView.tsx` (newest-first timeline, lazy per data).
- In `FileView`, subscribe via `useWebSocket` (same hook as `AppShell.tsx:15`): on
  `file.changed` for the open path → invalidate `['file', path]` React Query key (auto refetch)
  and prepend to the timeline. Keep the subscription scoped so closed tabs don't refetch.
- API client: add `fileApi.edits(path)` to `web/src/lib/api.ts`.

---

## 5. Cross-cutting design decisions (first pass)

1. **Backend stays additive & read-only on GET** (`web_bridge.py:11`). All new endpoints are
   GETs in `web_bridge.py`; git reads via `subprocess`; FS reads via `Path`. No core CIP module
   is modified for this proposal.
2. **One envelope, one client.** New endpoints use `_ok`/`_err` (`web_bridge.py:64,68`) and the
   React Query `request<T>` wrapper (`web/src/lib/api.ts:3`) — no new fetch plumbing.
3. **Path safety is non-negotiable.** Every path parameter is validated against traversal and
   resolved under `ROOT` before hitting the FS or git. (AGENTS.md security rules.)
4. **Performance:** tree is lazy (one level per call, cached); review/diff is on-demand;
   edit history is cheap table joins. No polling — WS-driven refresh only.
5. **Scope guard:** read-only surface. No save/edit/format/commit actions in this proposal.

---

## 6. "Etc." items that build naturally on these

- **Tabs** (multiple open files) with active-file sync between explorer and editor.
- **Hot reload** of a dirty open file when it changes on disk (Feature 3).
- **Commit → diff navigation** (click history entry → open diff at that ref, Feature 2).
- **Findings gutter icons** in the editor (Feature 2 review mode).
- **Explorer search/filter** (type to narrow the visible tree).

Each is deliberately out of first-pass scope so the three core features land cleanly first.

---

## 7. Open questions (for review)

1. **Explorer placement:** embed in `FileView` as a left rail, or a separate `/explorer` route?
   (First-pass lean: separate route, reuses `AppShell` layout, keeps `FileView` focused.)
2. **Badges in tree:** per-file finding/symbol counts add N+1 DB queries on expand — worth it,
   or defer to a details pane? (Lean: defer counts, show them only for the active file.)
3. **Diff semantics:** review = diff against a specific commit, or also "diff vs HEAD" as the
   default? (Lean: default `base=HEAD`, allow any commit from history.)
4. **WS `file.changed`:** extend the existing `watch.event` payload (additive, recommended) vs
   a new event type. Lean: additive `path` field + a typed `file.changed` alias.
5. **Review states:** should acknowledge/ignore states persist (needs a new table) or stay
   session-local? (Lean: session-local first pass.)

---

## 8. Rough build order (if approved)

1. `docs/dev/specs/16-repo-explorer.md` (Feature 1) — tree endpoint + explorer + route.
2. `docs/dev/specs/17-file-review-renderer.md` (Feature 2) — diff/at/review endpoints + Monaco
   diff & overlay modes.
3. `docs/dev/specs/18-realtime-edit-history.md` (Feature 3) — edits endpoint + WS payload +
   timeline + auto-refresh.
4. Each lands detect-first style: endpoint → API client → UI → lint (`bun run --cwd web lint`).

---

## 9. Acceptance sketch (what "done" looks like)

- Explorer lists the repo, ignores `node_modules/.git/…`, opens files via `/files?path=`, and
  never traverses above `ROOT`.
- Review mode shows a real diff and overlays open findings on the active file; base selection
  works from history.
- Open file auto-refreshes on disk change with the WS connected; timeline shows commits +
  watch events; disconnect does not break the editor (reconnect via existing hook).
- `bun run --cwd web lint` and `python -m pytest tests/` stay green; `cip selftest` passes.
