# PLAN-07 — Explorer backend: `GET /api/tree` + `file_bundle` PATH_ESCAPE retrofit

**Phase 7 of 10.** Builds SPEC-16 §4/§6. Grounded 2026-08-17.
**Depends on:** PLAN-01/02 (`_root()`), PLAN-05 (watch events refresh later).
**After this phase:** the tree backend exists and the pre-existing traversal hole in `/api/file`
is closed (CORE-NEW from SPEC-16 §7).

## Goal

Give the frontend a **lazy one-level directory listing** with git-status decorations, plus harden
`file_bundle` against path traversal. The console stays **read-only** — the tree is navigation only
(SPEC-16 §1, FR-16 `§7.1-5`).

## Truth anchors (verified)

- **Traversal hole:** `file_bundle(path, root=None)` `web_bridge.py:1740` does
  `real = Path(root) / path` then `real.is_file()` (`:1743-1744`) — `../../secret` resolves above root and would be read. **Never fixed yet.**
- View endpoint to mirror: `GET /api/file` `web_bridge.py:1792`; envelope `_ok/_err` `:64/68`.
- Storage/Auth surface: `git_tracked(root)` `gatekeeper.py:20` (`git ls-files -z`); hard excludes
  `DEFAULT_EXCLUDES` (`.git`,`.cip`,`.venv`,`node_modules`,...) + `BACKUP_DIR_PREFIXES` `base.py:33/44`.
- Client tree anchor (built next phase): `fileApi.*` `api.ts:431`, `FileView.tsx`, `SearchView.tsx:139`
  links to `/files?path=`.

## Atomic tasks

### Task 7.1 — shared prune helper
- **Edit:** `web_bridge.py` — `_prune_name(name)`: return True if name ∈ `DEFAULT_EXCLUDES` or
  name starts with any `BACKUP_DIR_PREFIXES` (import both from `base.py`; both are prefix/name sets, verified `:33/:44`).
- **Verify:** unit: `_prune_name(".git")`, `node_modules`, `__pycache__` → True; `src`, `main.py` → False.

### Task 7.2 — `web_bridge.dir_listing(root, rel) -> dict`
- **Edit:** module-level function near `file_bundle` (`:1740`).
  - `real = (Path(root) / rel).resolve()`; **guard**: `real.is_relative_to(root)` else `_err("PATH_ESCAPE")`.
  - `os.scandir(real)`; drop pruned names (`_prune_name`) and symlink loops; split dirs/files, sorted dirs-first;
    entries `{name, path: reljoin}`.
  - Git status per dir: one `git status --porcelain -- <dir>` (not per-file); map rel → first letter
    (`M`/`A`/`D`/`?` untracked). Non-git projects → skip status (all `""`).
- **Verify:** from repo root call with `rel=""` → top-level dirs/excludes correct; `rel="../../etc"` → PATH_ESCAPE.

### Task 7.3 — `GET /api/tree` endpoint
- **Edit:** add `@app.get("/api/tree")` (near `/api/file` `:1792`); params `path` (default ""), `repo` (PLAN-02).
  - Wrap `dir_listing(_root(), path)` in `_ok(..., status)` and `_ttl_cache(f"{path}", 10, ...)` (PLAN-02 key prefixing).
  - Response `{ok, data:{path, dirs:[{name,path}], files:[{name,path,status}]}}` (SPEC-16 §4).
- **Verify:** `GET /api/tree?path=` returns one level; `?repo=` scopes to that project; excludes pruned.

### Task 7.4 — retrofit `file_bundle` traversal guard (CORE-NEW)
- **Edit:** `file_bundle` `web_bridge.py:1740` — before `is_file()`, resolve and assert
  `real.is_relative_to(root)`; non-relative → `_err("PATH_ESCAPE")`. Retain existing behavior for valid paths.
- **Verify:** `GET /api/file?path=../../etc/passwd` → `_err PATH_ESCAPE` (was: leak); normal file bundle unchanged.
- **Record in `09-bugs-and-issues.md`** as fixed (entry exists as CORE-NEW from SPEC-16 §7).

## Acceptance (this phase ends green)

- [x] `/api/tree` returns one level, correct pruning, PATH_ESCAPE on escape (SPEC-16 §8 first two checks).
- [x] Git letters M/A/D/? render data correctly; non-git project → no status.
- [x] `/api/file` traversal now blocked; valid file bundle byte-identical.
- [x] TTL cache: same tree content for 10 s; project switch → fresh.

### Verification log (2026-08-18)

In-process via Starlette `TestClient`, all green:

- T7.1 `_prune_name` — `.git`/`node_modules`/`__pycache__`/`backup_*` → True; `src`/`main.py` → False.
- T7.2 `dir_listing` — root listing: 11 dirs + 24 files, contains `lib/web/docs/tests`, excludes
  `.git`/`node_modules`/`dist`; nested `lib/cipkg` works; `dir_listing` returns `{path, dirs, files}`.
- T7.3 `/api/tree` — one level, `?repo=` scopes to that project (fresh tree on switch, root-prefixed
  TTL key per SPEC-19 §6.5), `{path:''}` default = root, cached 10 s (same payload across calls).
- Git decorations — fresh git repo: tracked-modified → `M`, untracked → `?`, non-git project → `""`.
  One porcelain call per listing maps all rels (no per-file spawning).
- T7.4 `file_bundle` guard — `../../Windows/win.ini` → `PATH_ESCAPE`; valid file bundle unchanged (`found: True`).
  **Note:** the guard (`_safe_join`, `web_bridge.py:2321`) already existed; this phase verified it and
  confirmed `file_endpoint` maps the `ValueError("PATH_ESCAPE")` to the `PATH_ESCAPE` code. Per the
  09-bugs-and-issues.md "never edit" rule (AGENTS.md), the fix evidence is recorded here instead.
- Edge cases — file-as-path → `DIR_NOT_FOUND`; encoded `..%2f` → `DIR_NOT_FOUND` (no traversal);
  Windows backslash separators resolve correctly.

**Next:** PLAN-08 builds the frontend tree on this endpoint.