# SPEC-16 — Repo File Explorer (FR-16)

- **Requirement source:** web-console feature request (FR-16, "VS Code-style repo explorer");
  `docs/dev/web-console-proposal/01-first-pass-proposal.md` §2; `02-research-upgrade.md` §1
- **Grounding verified:** 2026-08-17 against `lib/cipkg/{web_bridge,base,gatekeeper,store}.py`, `web/src/{lib/api,views/FileView,components/file/FileEditor,stores/app}.ts`
- **Build order dependency:** SPEC-01 (shell nav), SPEC-06 (file views), SPEC-15 (bridge rules),
  **SPEC-19 (project registry — project-scoped)**.

---

## 1. Goal & owner intent

A VS Code-style navigable file tree for a **project**: expand/collapse directories, click a file to
open the deep panel (SPEC-06), show git worktree status (M/A/D) and tracked/un-tracked as file
decorations. The console stays **read-only** — the tree is navigation only. Lazy-expand one level
at a time; the CIP project is large enough that a full recursive dump must not be in-request
(NFR-3, NFR-6). The tree always resolves against the **active project** (`_root()` from SPEC-19),
so switching projects re-renders the whole tree against that folder.

## 2. Truth-grounded core surface (verified)

| Need | Core call (verified) | Returns |
|---|---|---|
| Active root | `_root()` per-request contextvar from **SPEC-19** (was module `ROOT = repo_root()` `web_bridge.py:36`) | absolute project root for the current `?repo=` |
| Envelope | `_ok(data)` `web_bridge.py:64` / `_err(code,msg,core)` `:68` | stable `{ok,data}` shape |
| TTL cache | `_ttl_cache(key, ttl, fn)` `web_bridge.py:91` | cached computation for GETs |
| Hard excludes | `DEFAULT_EXCLUDES` `base.py:33` (`.git`,`.cip`,`__pycache__`,`.pytest_cache`,`node_modules`,`.venv`,`venv`,`backups`,`htmlcov`,`dist`,`build`,`.tox`) + `BACKUP_DIR_PREFIXES` `base.py:44` | prune dirs from tree |
| Git-tracked truth | `git_tracked(root)` `gatekeeper.py:20` (`git ls-files -z` → set) | gold-standard file set |
| Existing dir aggregation | `summarize.map_` behind `GET /api/vis/map` `web_bridge.py:2818` | aggregated dirs (not a navigable tree) |
| Client API pattern | `request<T>` `web/src/lib/api.ts:3` + `vizApi.map` `:644` | envelope-unwrapping fetch |
| File open target | `Link to /files?path=` `web/src/views/SearchView.tsx:139`; read-only Monaco `FileEditor.tsx:50` | existing deep panel |

**Gap note:** no tree/ls endpoint and no client-side navigable-tree component exist today.
`/api/vis/map` is a static aggregation, not a walkable structure.

## 3. UI/UX contract

- **Placement:** collapsible left rail (collapsible `<aside>`, class-token styled like `LeftNav`)
  gated behind SPEC-01 shell layout; header: project name (`_root()` basename, from SPEC-19 active
  project) + refresh button.
- **Tree behavior:**
  - Root view = top-level dirs + loose files (pruned by `DEFAULT_EXCLUDES`).
  - Click dir → lazy-load its children (chevron + loading spinner in-gutter); expanded node
    shows 🡒 collapse; state in Zustand (see §6).
  - Click file → `navigate('/files?path=')` (EXACT same route SearchView uses); no second view.
- **Decorations (per node):** git status letter (`M` modified / `A` added / `D` deleted / untracked
  `?`) as a colored mono glyph on file rows; findings count badge (from bundle optional) only when
  cheap — no per-row RPC.
- **Active-file sync:** `activePath` in the store; tree highlights open file and auto-expands its
  parent chain when arriving via search (route change).
- **Search filter:** tree-top filter input filters visible siblings (client-side, no RPC);
  keyboard: Enter expands dir / opens file, arrows navigate.
- **Component choice (2026 research, `02-research-upgrade.md` §1.1):** spike
  `@vscode-file-tree/react` (turnkey 1:1 VS Code UX) for ≤1 day; if too immature, build with
  `headless-tree` (virtualized rows, custom JSX = matches Tailwind tokens exactly). Both keep
  virtualization so a 50k-file monorepo does not degrade.

## 4. API / WS contract

REST:
- `GET /api/tree?path=` → one directory level (no recursion). `?repo=` (optional) resolves the
  project root via SPEC-19; omitting it keeps legacy cwd-root behavior.
  - `path` = `""` or project-relative dir; resolved under `_root()`; sanitized (§7 CORE-NEW).
  - Response `{ok, data:{path, dirs:[{name,path}], files:[{name,path,status}]}}`.
  - `status` ∈ `{"M","A","D","",} | "?"` from `git status --porcelain` for that dir (one call, not
    per-file); `""`/`?` = clean/untracked (untracked flagged, not skipped).
  - Pruning: drop any path segment in `DEFAULT_EXCLUDES` or `BACKUP_DIR_PREFIXES` (both sets are
    prefix-based, `base.py:33/44`). Node_modules-leaf decoys filtered. `_ttl_cache` 10 s.
- `GET /api/tree/status?path=` → per-file status for one dir if the tree call omits it
  (fallback; primary plan = status embedded in `/api/tree`).

WS: none (SPEC-18 owns `file.changed` refresh).

## 5. Data contract

- No new tables. Pure FS enumeration of `git_tracked(_root()) ∪ on-disk` minus excludes.
- `git status --porcelain` parsed once per dir; field letter → glyph map on client.
- TTL cache keys carry the project root (SPEC-19 §6) so two projects never collide.

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge.dir_listing(root, rel)`** — one-level enumeration (root passed explicitly, per
   SPEC-19 request-scoping; caller uses `_root()`):
   - resolve `real = (Path(root) / rel).resolve()`; assert `real.is_relative_to(root)` else `_err("PATH_ESCAPE")`.
   - iterate `os.scandir(real)`; for each entry prune hard-exclude names/prefixes (`_prune_name`:
     name in `DEFAULT_EXCLUDES` or starts with `BACKUP_DIR_PREFIXES`); append `{name, path: reljoin,
     }`, dirs and files separately, sorted (dirs first).
   - `git status --porcelain -- <dir>` → map `rel → letter` (first char, or `?` for untracked).
2. **`GET /api/tree` endpoint** — wraps `dir_listing` in `_ok`, path-sanitized, `_ttl_cache` 10 s.
3. **`web_bridge._prune_name` shared helper** — also used by `/api/tree/status` and (later)
   SPEC-18 so exclude logic lives in one place.

## 7. Core issues / risks (flagged, grounded)

- **CORE-NEW — existing `/api/file` has no traversal guard.** `file_bundle` does
  `real = Path(root) / path` then `real.is_file()` `web_bridge.py:1743-1744` — a `path` like
  `../../secret` resolves above root and would be read. New endpoints MUST assert
  `real.relative_to(root)` for the resolved project root; retrofit the guard onto `file_bundle`
  too. *(New issue → also 09-bugs-and-issues.)*
- **Watch: big dirs / long `git status`.** One `git status` per expanded dir ≤ some cap; for
  huge roots run under `_ttl_cache`; never recursive in-request (NFR-3).
- **Watch: virtualized tree lib.** `@vscode-file-tree/react` is 0-star/new (Apr 2026) — the spike
  gate in §3 decides it vs `headless-tree` before SPEC-16 is built.
- **Watch: tree vs `repo_map` ignore-list.** `_collect_source_files` may skip files the explorer
  shows; the explorer must reflect **disk/git truth**, independent of index admission.

## 8. Acceptance checks (from §6 / §7.5 / feature request)

- [ ] `/api/tree?path=` returns one level with correct pruning (no `.git`, `node_modules`,
      `__pycache__`, `backup_*`); path escaping returns `_err PATH_ESCAPE`.
- [ ] `?repo=` scopes the tree: switching projects (SPEC-19) re-renders the tree for the new root.
- [ ] Tree renders + lazy-expands; file click opens the EXACT same deep panel as search.
- [ ] Git status letters show on modified/added/deleted/untracked files.
- [ ] Active file highlights and expands its parents on route change.
- [ ] 50k-file synthetic dir structure stays interactive (virtualized) — perf smoke test.
- [ ] Tree is read-only; no edit/save affordance appears anywhere (FR-16 `§7.1-5` preserved).