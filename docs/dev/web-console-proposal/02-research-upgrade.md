# Research Round 2 — Tools & Solution Landscape (Aug 2026) → Upgraded Proposal

**Status:** RESEARCH + UPGRADE of `01-first-pass-proposal.md`
**Date:** 2026-08-17
**Research window:** live web search, August 2026
**Relation:** supersedes the design decisions in the first-pass proposal where noted.
`01-first-pass-proposal.md` stays as the baseline; this doc records what the 2026 ecosystem
actually offers and re-scopes each feature.

---

## 0. Bottom line (read this first)

| Feature | First-pass plan | 2026 upgrade | New deps added? |
|---|---|---|---|
| 1. Explorer | hand-rolled `RepoExplorer` + `/api/tree` | Keep `/api/tree` backend, but build the tree on **`headless-tree`** (or evaluate turnkey **`@vscode-file-tree/react`**); add **git-status file decorations** and **virtualization** | 1 (headless) or 1 (turnkey) |
| 2. Review renderer | Monaco `DiffEditor` + decorations overlay | **Monaco `DiffEditor` is already correct** (diff editor is a no-op — already installed); upgrade overlay to **`monaco-review`** for GitHub-style inline/threaded comments + event-sourced edit history, or hand-roll via `IModelDecorationOptions` | 1 (`monaco-review` + `dompurify`) or 0 |
| 3. Real-time history | extend WS `file.changed` + timeline | Keep WS (already wired); add **`/api/file/blame`** for line-level history and optionally a **SSE stream** as the transport for file events; render timeline via a custom component or `commit-graph` | 0 or 1 (`commit-graph`) |

**Net:** the first-pass architecture (additive FastAPI endpoints + React Query + existing `/ws`)
survives unchanged. What changes is the *frontend component layer* — proven libraries replace
hand-rolled UI — and *scope*: file decorations and line-level blame become cheap and worth
adding. No new editor engine is needed: **Monaco 0.55/0.56 is the 2026 default** for IDE-grade
browser code surfaces and diffing.

> **Post-research owner ask (2026-08-17):** manage *all* CIP projects from one console — onboard
> any folder (git/monorepo/plain) and switch across projects. This lands **first**, as
> SPEC-19 (multi-project registry + request-scoped root + UI onboarding), because the bridge is
> single-root today (`ROOT = repo_root()`, `web_bridge.py:36`, ~80 endpoints hardwired to it).
> Features 1–3 below are built **project-scoped** on top of it (see §6 build order).

---

## 1. Feature 1 — Repo file explorer: library landscape

### 1.1 What the 2026 ecosystem has

| Option | Notes (Aug 2026) | Verdict for CIP |
|---|---|---|
| **`@vscode-file-tree/react`** (new, Apr 2026) | Purpose-built "VS Code Explorer 1:1": virtual scrolling (10k+ nodes), keyboard nav, DnD, **file decorations (git status colors, badges)**, compact folders, icon themes, full WAI-ARIA tree | **Turnkey win** but brand-new (1 commit, ~0 stars). Evaluate on a spike before committing. |
| **`headless-tree`** (lukasbach) | Headless logic/state: search, hotkeys, virtualization hooks, DnD; you own the row JSX + CSS | **Recommended.** Matches CIP's custom Tailwind tokens exactly (no shadcn dependency), keeps bundle small. |
| **React Arborist** | Virtualized, sortable, DnD, inline rename; battle-tested | Strong backup; heavier opinionation, maintenance has slowed. |
| **`@grida/tree-view`** (May 2026) | Headless, virtualized, shadcn/Tailwind row renderers, VS Code-explorer styling, one controller → many trees | Good fit; young. |
| **react-complex-tree** | a11y-first, multi-select, live search | Overkill for a file tree. |
| **SVAR React File Manager** | MIT, backend-agnostic, lazy folder loading, list/tiles views | File-management oriented, not code-navigation oriented. |
| **rc-tree** | General-purpose, animated, IE9+ | Old-school; no virtualization story. |

### 1.2 Upgrades to the first-pass design

1. **Backend unchanged** — `GET /api/tree?path=` one-level, sanitized, cached (per `01-first-pass-proposal.md` §2.2). Keep the repo_map ignore set (`repo_map.py:85`).
2. **File decorations (new, cheap):** `git status --porcelain` gives `M/A/D/R/U` per path. Return a `status` field per file in `/api/tree` (one `git status` call per directory, not per file). Render as the classic VS Code letter/color in the explorer gutter + use it for the open-file "dirty" indicator. This is the single biggest "feels like VS Code" upgrade and it's ~20 lines of backend.
3. **Virtualization:** pick a tree lib with virtualization built in (both candidates above have it) instead of hand-recursing — the CIP repo is small today but the component should not degrade on a 50k-file monorepo.
4. **Active-file sync:** `activePath` in `stores/app.ts` (first-pass) stays; tree highlights the open file and auto-expands its parent chain when navigating from search.
5. **Recommendation:** spike `@vscode-file-tree/react` for 1 day (it is *exactly* the target UX); if it is not yet stable enough for production, fall back to `headless-tree` with a custom VS Code-style row renderer. Both keep `lucide-react` + Tailwind tokens.

---

## 2. Feature 2 — File review renderer: library landscape

### 2.1 Diff rendering

- **Monaco `DiffEditor` is the correct engine and is already in the bundle** (`@monaco-editor/react` 4.7 / `monaco-editor` 0.56; upstream 0.55.1 is current as of May 2026). Zero new editor dependency. The 2026 comparison (PkgPulse, Mar 2026) confirms Monaco for "code review / diff display" with full TS IntelliSense; CodeMirror 6 is the lighter alternative (not installed, no reason to add).
- Key option for IDE-style review: **`hideUnchangedRegions`** (Monaco 0.4x+ → present in 0.56) folds unchanged hunks, giving the GitHub/VS Code "only changed lines" review UX without any library.
- Alternatives considered: `react-diff-view` (interactive, line-selection for comments, split+unified — good PR-style component), `react-diff-viewer-continued` (maintained fork of the dead `react-diff-viewer`), `diff2html` (static HTML — wrong layer for a React SPA). All viable, all second choice to "Monaco diff + inline comments."

### 2.2 Inline code review (comments on lines)

- **`monaco-review`** (`jburrow/monaco-editor-code-review`, MIT): inline comments, **threaded replies**, **per-comment event-sourced edit history**, read-only mode, overview-ruler markers, keyboard nav (Ctrl+F10/F11/F12), programmatic API (`getComments()`, `selectComment()`), theme-following. Requires `monaco-editor >= 0.34` (have 0.56) + `dompurify`. This single library covers **both** the review-renderer *and* part of the edit-history requirement (comment history is event-sourced).
- Alternative zero-dep path: Monaco `IModelDecorationOptions` (`glyphMarginClassName`, `hoverMessage`, `linesDecorationsClassName`, `overviewRuler`, `injectedText`) + content widgets. Full control, no dependency, more code. Use this if the review comments should be **CIP-generated findings**, not user-authored text.
- **Decision:** two overlays share one Monaco instance:
  - *Findings overlay* (auto): render `bundle.findings` as glyph-margin decorations + hover messages (zero-dep path; data already in `file_bundle`, `web_bridge.py:1787`).
  - *User review* (interactive): `monaco-review` for threaded comments, persist the event log via a new additive endpoint (`POST /api/file/review-events` — the first non-GET, but additive and read-only *by default*; per bridge rule `web_bridge.py:11` this must be called out in the spec).

### 2.3 Diff base selection

First-pass `GET /api/file/diff?path=&base=` and `GET /api/file/at?path=&ref=` stand (`stack/impact.py:116` git pattern). Add `hideUnchangedRegions: true` to the DiffEditor options and default `base=HEAD`.

---

## 3. Feature 3 — Real-time code-edit history

### 3.1 Transport: the 2026 consensus

The Aug-2026 guidance is consistent: **WebSocket for bidirectional interactive; SSE for server→client push.** Specifically:

- WS = chat, collaborative editing (CRDT), command/ack; manual reconnection with exponential backoff + jitter.
- **SSE** = notifications, live feeds, dashboards; `EventSource` auto-reconnects and resumes via `Last-Event-ID`; HTTP-native (load-balancer/CDN/proxy friendly), trivial to implement (~12 lines server-side).
- GitHub itself streams live PR/issue updates over SSE.

**CIP already has `/ws` + a reconnecting `useWebSocket` hook** (`web/src/hooks/useWebSocket.ts:10`). Pragmatic call:

- **Keep `/ws`** as the single channel and add a typed `file.changed {path, kind}` event by extending the existing fs-watch broadcast (`web_bridge.py:437–483`). Zero new transport, zero new client code beyond a handler in `FileView`.
- **Optional second channel:** an SSE endpoint `GET /api/events/file?path=` with `Last-Event-ID` for high-frequency watch bursts and for environments that block WS upgrades. Add only if the watch produces event storms (> ~10/sec per file). Not needed for first pass.

### 3.2 History/timeline rendering

- **Per-file timeline** (first-pass `GET /api/file/edits?path=` merging `commits`/`commit_files` `store.py:46`, `signals` `store.py:51`, watch events): a small custom timeline component is fine (matches existing rail `SectionShell` style in `FileView.tsx`).
- **Repo-wide commit graph** (nice-to-have, "etc."): `commit-graph` (liuliu-dev, v2.4.0 Mar 2026; infinite scroll, diff-stats on click, used by DoltHub) or `react-git-log` (branching graph + paging). Optional `GET /api/git/log` endpoint if adopted.
- **Line-level history (new, cheap):** `git blame --line-porcelain -- path` gives per-line `{commit, author, ts}` — powers a **blame gutter / VS Code Timeline**-style "who last touched this line" and a per-line "open diff at this commit". Add `GET /api/file/blame?path=`. This is the highest-value "etc." upgrade because it makes the review renderer and the history feature reinforce each other: click a blamed line → open diff at that commit (`/api/file/diff` + `/api/file/at`).

### 3.3 Auto-refresh

Unchanged from first pass: `useWebSocket` handler in `FileView` invalidates `['file', path]` React Query key on `file.changed`. Add `invalidateQueries({ queryKey: ['file', path] })` on both the bundle and the timeline keys.

---

## 4. Risks / flags (from research)

1. **`@vscode-file-tree/react` is days old** (Apr 2026, 1 commit). Do not hard-commit; spike first. `headless-tree` is the safe fallback and covers 95% of the value.
2. **`react-diff-viewer` is effectively unmaintained** (6 years). Use `react-diff-viewer-continued` or — preferred — Monaco diff + `monaco-review`. Never add `react-diff-viewer` fresh.
3. **`monaco-review` pulls `dompurify`** for comment sanitization. Acceptable (it sanitizes untrusted text), but the auto-findings overlay should stay dependency-free.
4. **SSE vs WS:** don't add a second transport speculatively. The existing WS already reconnects with backoff; add SSE only if watch event volume justifies it.
5. **Monaco bundle:** unchanged — diff editor reuses the already-lazy-loaded Monaco (`FileEditor.tsx:7` lazy worker config). Keep `import()`-lazy the diff/review components (`FileView.tsx:10` pattern).
6. **New backend surface:** only `GET` endpoints in this proposal; `monaco-review` persistence is the sole `POST` and must be flagged in the spec against the `web_bridge.py:11` additive/read-only rule.

---

## 5. Consolidated target stack (upgraded)

**Editor/review:** Monaco 0.56 (kept) — `DiffEditor` (`hideUnchangedRegions`) + findings overlay via `IModelDecorationOptions` + user comments via `monaco-review`.
**Explorer:** `/api/tree` (kept) + `git status` decorations; UI on `headless-tree` (fallback) / `@vscode-file-tree/react` (spike target); virtualization on.
**Real-time:** `/ws` `file.changed` (kept, payload extended) + `GET /api/file/edits` + `GET /api/file/blame`; auto-refresh via React Query invalidation. Optional SSE only if needed.
**New deps (max):** `monaco-review`, `dompurify`, `headless-tree` (or the vscode-file-tree package) — all MIT, all actively shipping in 2026. `commit-graph` optional for a repo-wide graph.

---

## 6. Build order (revised)

1. Spike `@vscode-file-tree/react` vs `headless-tree` (½–1 day) → decide explorer base. Land `/api/tree` + `git status` decorations meanwhile.
2. `docs/dev/specs/19-project-registry.md` — **multi-project foundation** (owner request 2026-08-17): project registry + request-scoped `_root()` + onboard-any-folder POST + project switcher. **LANDED 2026-08-17.** Builds FIRST — every project-scoped feature depends on it.
3. `docs/dev/specs/16-repo-explorer.md` — explorer (Feature 1), project-scoped via SPEC-19. **LANDED 2026-08-17.**
4. `docs/dev/specs/17-file-review-renderer.md` — diff (`hideUnchangedRegions`) + findings overlay + `monaco-review` comments + diff base from history (Feature 2), project-scoped via SPEC-19. **LANDED 2026-08-17.**
5. `docs/dev/specs/18-realtime-edit-history.md` — `file.changed` payload, `/api/file/edits`, `/api/file/blame`, timeline + blame gutter + auto-refresh + repo-wide commit graph (Feature 3), project-scoped via SPEC-19. **LANDED 2026-08-17.**
6. Acceptance identical to `01-first-pass-proposal.md` §9, plus: "open file auto-refreshes on disk change; blamed line opens diff at that commit; switching projects re-scopes every view."
7. Build order: SPEC-19 (registry + `_root()` sweep) → SPEC-16 → SPEC-17 → SPEC-18, starting with the explorer base spike.

---

## Sources (Aug 2026)

- Tree libs: github.com/jravolio/react-file-tree (`@vscode-file-tree/react`); reactscript.com "7 Best React Tree View Components (2026 Update)"; stillup.to `@grida/tree-view`; svar.dev react filemanager.
- Diff/review: pkgpulse.com "Monaco vs CodeMirror 6 vs Sandpack 2026"; microsoft.github.io/monaco-editor (0.55.1, diff docs, `IModelDecorationOptions`); github.com/jburrow/monaco-editor-code-review (`monaco-review`); npm-compare.com diff2html vs react-diff-view vs react-diff-viewer; SO 71777516 (`hideUnchangedRegions`).
- History: github.com/liuliu-dev/CommitGraph (v2.4.0, Mar 2026); github.com/TomPlum/react-git-log; shadcn.io git-branch-timeline block; git-scm.com/docs/git-blame (`--line-porcelain`).
- Realtime: apiscout.dev "Real-Time APIs: WebSockets vs SSE vs Long Polling 2026"; suprsend.com "Real-Time Notifications Architecture"; abrarqasim.com "SSE vs WebSockets in 2026"; notes.suhaib.in SSE-vs-WS 2026.
