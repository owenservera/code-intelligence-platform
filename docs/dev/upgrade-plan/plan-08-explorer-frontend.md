# PLAN-08 — Explorer frontend: tree spike + `headless-tree` build

**Phase 8 of 10.** Builds SPEC-16 §3. Grounded 2026-08-17.
**Depends on:** PLAN-07 (`/api/tree`), PLAN-06 (shell + active project).
**After this phase:** a VS Code-style, virtualized, git-decorated, lazy file tree in the console's left rail that opens files in the existing deep panel.

## Spike decision (T8.1, 2026-08-18)

**Chosen base: `@headless-tree/react` v1.7.0** (successor to react-complex-tree).

Decision rule (SPEC-16 §3): spike `@vscode-file-tree/react` first; if it fails any of (maturity, a11y,
token styling) → `headless-tree`. The spike **failed maturity immediately**: the package does not
exist on npm (`npm view @vscode-file-tree/react` → E404). No further spike needed.

`headless-tree` scores: async data sources with caching (lazy per-level fetch), virtualization support
(100k+ items), a11y by default (flat list + aria tree emulation), search/typeahead, keyboard nav, and
unopinionated row rendering (our Tailwind tokens apply directly — token styling preserved).

## Goal

Turn `/api/tree` into an interactive tree. UI contract (SPEC-16 §3): lazy expand one level, git-status
glyphs, active-file highlight + parent auto-expand on route change, client-side filter, read-only.

## Truth anchors (verified)

- Shell insertion: `AppShell.tsx:84` `<LeftNav/>`; nav item pattern `LeftNav.tsx:34-48`.
- Deep panel route: `navigate('/files?path=')` — same as `SearchView.tsx:139`; Monaco file editor `FileEditor.tsx`.
- Store: `useAppStore` `stores/app.ts:23` (add `activePath`, tree node map).
- Research decision (`02-research-upgrade.md §1.1`): **spike `@vscode-file-tree/react` first**; fallback `headless-tree`. Both virtualize so a 50k-file monorepo stays interactive (NFR-6).

## Atomic tasks

### Task 8.1 — spike gate (½–1 day, decide base lib)
- **Create:** throwaway spike in `web/` adding `@vscode-file-tree/react` against `/api/tree`.
  Score: 1:1 VS Code UX, maturity (1 commit / ~0 stars — Apr 2026), Tailwind-token fit, keyboard/a11y.
- **Decision rule (SPEC-16 §3):** if spike fails any of (maturity, a11y, token styling) → **`headless-tree`**,
  custom row JSX matching our tokens exactly. Record decision in this doc's header.
- **Verify:** interactive demo against the real `/api/tree`.

### Task 8.2 — tree state in store
- **Edit:** `stores/app.ts` — `activePath: string|null`, `expanded: Record<string, boolean>` (dir → children loaded),
  `loadingDir`, setters; reset on project switch (PLAN-06 `setActiveProject` consumer).
- **Verify:** `tsc --noEmit`.

### Task 8.3 — `RepoExplorer` rail component
- **Edit:** new `web/src/components/file/RepoExplorer.tsx` mounted in `AppShell.tsx` beside `LeftNav` (collapsible `<aside>`).
  - **Root view:** lazy `GET /api/tree?path=` for active project; render dirs + loose files.
  - **Expand dir:** fetch children on first open (chevron/spinner), collapse in-place; cache per path.
  - **Open file:** `navigate('/files?path=' + encodeURIComponent(rel))` — exact deep-panel route.
  - **Decorations:** git letter from `files[].status` as mono glyph (M/A/D/`?`), tainted by exclude rule.
  - **Filter input:** client-side sibling filter, no RPC (SPEC-16 §3); keyboard Enter/arrows.
  - **Active sync:** on route `?path=` change, highlight node + auto-expand parents.
- **Verify:** lazy expansion → exactly one `GET /api/tree?path=` per expansion (network trace); 50k-file synthetic dir stays responsive (virtualized).

### Task 8.4 — wire refresh on `file.changed`
- **Edit:** `useWebSocket` handlers (see `AppShell.tsx:56`) — on `file.changed` for the active path,
  invalidate the tree node + (PLAN-10) history keys via the existing QueryClient (SPEC-16 §4 "WS: none… SPEC-18 owns refresh" — this is that hook).
- **Verify:** file modified on disk → tree node / open-file panel refreshes without reload (when watch running, PLAN-05).

## Acceptance (this phase ends green)

- [ ] Tree renders project-root dirs/files; lazy per-level fetch; file click opens the **same** deep panel as search.
- [ ] Git letters show; untracked flagged; excludes never appear.
- [ ] Active file highlights and parents expand on route arrival (e.g. from search).
- [ ] Filter + keyboard nav work; read-only (no edit affordance anywhere).
- [ ] `npm run build` green; perf smoke on synthetic 50k dir.

**Next:** PLAN-09 review renderer (diff + inline review).