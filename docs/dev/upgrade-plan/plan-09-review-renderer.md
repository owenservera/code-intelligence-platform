# PLAN-09 — File review renderer: diff + findings overlay + inline review

**Phase 9 of 10.** Builds SPEC-17 §4-6. Grounded 2026-08-17.
**Depends on:** PLAN-01/02 (`_root()`), PLAN-07 (file surface + PATH_ESCAPE), PLAN-08 (open file).
**After this phase:** a Review mode showing side-by-side diff (base vs working tree) with findings
overlay and persistent threaded user comments, stored additively (never source writes).

## Goal

Review a file: pick a base commit → Monaco `DiffEditor` (`hideUnchangedRegions`) → two overlays:
auto **findings** decorations from the `findings` table, and **user comments** persisted to an
additive `reviews.jsonl` under `cip_dir(_root())/data/`. Console stays read-only for source files;
comments are UI data (SPEC-17 §1 flag).

## Truth anchors (verified)

- `file_findings(path, root)` `web_bridge.py:1783` — `SELECT ... FROM findings WHERE path=? AND status='open'`.
- `impact_diff(root, ref)` `stack/impact.py:119` — `git diff --name-only` pattern to mirror for content diff.
- `retrieve.history(root, path, n)` `retrieve.py:374` — `git log --pretty=format:%h %ad %an %s` (short shas only;
  SPEC-17 §6.4 adds full-shas).
- Monaco already bundled: `FileEditor.tsx:1` imports `@monaco-editor/react`; `readOnly:true` `:50`; DiffEditor ships in same engine (research §2.1).
- `fileApi.*` `api.ts:431`; deep panel header region `FileView.tsx` (mode switch site).
- Additive-write precedent: `/api/daemon/auto-manage` writes `.cip/config.toml` via `tomlkit` `web_bridge.py:446-453`.

## Atomic tasks

### Task 9.1 — backend: `file_diff(root, path, base)` + `file_at(root, path, ref)`
- **Edit:** `web_bridge.py` near `file_bundle` (`:1740`).
  - `file_diff`: `subprocess.run(["git","diff","-U3", base, "--", path], cwd=root)`; parse `@@ -a,b +c,d @@`
    hunks via `_parse_unified`; return `{text, hunks:[...]}`. `_err("GIT_DIFF_FAIL")` on nonzero.
  - `file_at`: `git show <ref>:<path>`; **validate ref** `^[0-9a-f]{7,40}$|^HEAD$` → else `_err("REF_INVALID")`;
    `_err("PATH_ESCAPE")` if path resolves outside root.
- **Endpoints:** `GET /api/file/diff?path=&base=` and `GET /api/file/at?path=&ref=` (both `?repo=`-scoped, PLAN-02).
- **Verify:** valid base → hunks parse; bad ref → REF_INVALID; traversal → PATH_ESCAPE.

### Task 9.2 — backend: full-sha history variant
- **Edit:** `retrieve.py` — add `history_shas(root, path, n)` returning `{sha, date, author, msg}` (full sha,
  `%H %ad %an %s`) alongside `history` `:374`; keep `history` untouched for other consumers.
- **Verify:** base picker gets full shas; `history` unchanged.

### Task 9.3 — backend: review store (read/write, additive)
- **Edit:** `web_bridge.py` — `review_store` manager over `cip_dir(_root())/data/reviews.jsonl`:
  - `GET /api/file/review?path=` → `{path, comments:[{id(uuid), path, line, thread_id, body, author:"web-console", ts}]}`.
  - `POST /api/file/review` `{path, action:'add'|'reply'|'edit'|'delete', ...}` — append one JSON line per comment,
    write-lock + append-atomic; returns updated list. **Never touches source files** (SPEC-17 §7 flag).
- **Verify:** add/edit/reply/delete round-trip across reload; malformed body → `_err`; concurrent writes don't corrupt.

### Task 9.4 — frontend: Review mode (DiffEditor + overlays)
- **Edit:** `FileView.tsx` — `View | Review` mode switch in the editor header (`:41-51` region).
  - **Diff surface:** lazy `DiffEditor`, `hideUnchangedRegions:true`; original = `/api/file/at?ref=`, modified = working text (SPEC-06).
  - **Base picker:** dropdown from `/api/file/history` (`api.ts` `fileApi.history` `:428`) + `HEAD` + `(empty)`.
  - **Findings overlay:** Monaco `glyphMarginClassName` + `hoverMessage` decorations from `fileApi.findings`
    (bundle path), zero new deps; click scrolls to line.
  - **Comments:** `monaco-review` (research §2.2) + `dompurify`; threaded; read-only mode on for source,
    write only for comment payload; autosave + explicit "Save review".
- **Verify:** diff renders with unchanged regions hidden; findings on correct lines; comment add/edit/delete persists across reload (SPEC-17 §8).

## Acceptance (this phase ends green)

- [ ] Review mode: side-by-side diff vs base, base picker lists full shas, regions hidden.
- [ ] Findings overlay + hover; click scrolls.
- [ ] Comments add/edit/reply/delete persist (reload test); additive jsonl under `data/`.
- [ ] Source files never written by review (no write path exists).
- [ ] Diff/at/review reject traversal + bad refs via `_err`.
- [ ] No dead controls (every review action maps to an endpoint).

**Next:** PLAN-10 realtime history (timeline + blame + `file.changed` live refresh).