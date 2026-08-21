# SPEC-17 — File Review Renderer (FR-17)

- **Requirement source:** web-console feature request (FR-17, "file review renderer");
  `docs/dev/web-console-proposal/01-first-pass-proposal.md` §3; `02-research-upgrade.md` §2
- **Grounding verified:** 2026-08-17 against `lib/cipkg/{web_bridge,retrieve,store}.py`, `web/src/{lib/api,views/FileView,components/file/FileEditor}.tsx`
- **Build order dependency:** SPEC-16 (file nav), SPEC-06 (bundle/findings pattern), SPEC-15 (bridge rules),
  **SPEC-19 (project registry — project-scoped)**.

---

## 1. Goal & owner intent

Render a **code review** of a file: side-by-side diff vs an earlier/base state, with inline,
threaded, persistent comments (GitHub/VS Code style review, not PR merge tooling). Two overlays
share one Monaco instance: (a) **CIP findings** — auto decorations from the existing `findings`
table; (b) **user review comments** — authored inline comments persisted by the console. Per `§7.1-5` the console stays read-only **for source files**; *review comments are UI data, not
source edits*, so they may be written without violating the no-edit-file rule (flagged in §7). The
diff/findings/comments all resolve against the **active project** root (`_root()`, SPEC-19); the
review store lives under that project's `data/` dir.

## 2. Truth-grounded core surface (verified)

| Need | Core call (verified) | Returns |
|---|---|---|
| File bundle (findings) | `file_findings(path,root)` `web_bridge.py:1778` — `SELECT id,rule,severity,line,title,status FROM findings WHERE path=? AND status='open' ORDER BY severity` | finding rows for overlay |
| Diff shell-out | `impact_diff(root, ref="HEAD")` `stack/impact.py:119` — `subprocess.run(["git","diff","--name-only", ref])` | git-diff pattern to mirror |
| History (commit list) | `retrieve.history(root, path, n)` `retrieve.py:374` — `git log --pretty=format:%h %ad %an %s --date=short -n N` | pick `base` ref |
| Monaco (bundled) | `FileEditor.tsx:1` imports `@monaco-editor/react` + `monaco-editor`; workers wired `:9-15`; `readOnly:true` `:50` | reuse lazy editors; **DiffEditor ships in same bundle** — no new engine |
| Client API pattern | `fileApi.*` `api.ts:364` (bundle/summary/impact/history/...) | add `diff`/`review` members |

**Gap note:** no `git diff` *content* endpoint and no review-comment storage exist yet.
`retrieve.history` gives only shortened commit strings (`%h %ad %an %s`), no full hashes — the
`base` ref picker must request full hashes (see §6.2).

## 3. UI/UX contract

- **Entry:** from the deep file panel — a mode switch `View | Review` in the `FileView` editor
  header (`FileView.tsx:41-51` header region). Review opens a **lazy-loaded** `DiffViewer`
  (same code-split discipline as `FileEditor` lazy `FileView.tsx:10`).
- **Diff surface:** Monaco `DiffEditor` (bundled, `hideUnchangedRegions: true` for focused review)
  original = file at `base`, modified = working tree (SPEC-06 current text). Base picker: dropdown
  of `history()` commits + `HEAD` + `(empty — new file)`.
- **Findings overlay (auto):** decorations on the *modified* side via Monaco options
  `glyphMarginClassName` + `hoverMessage` + `linesDecorationsClassName` + `overviewRuler` driven
  by the `line` field of findings (`file_findings` rows). No new deps. Clicking a decoration
  scrolls to line.
- **User review comments:** `monaco-review` (research §2.2) mounted on the diff; threaded
  replies, per-comment edit-history rendered in-editor, read-only mode on (review UI is
  write-enabled only for the comment payload). Requires `monaco-review` + `dompurify` (MIT).
- **Persistence:** comments saved async (autosave + explicit "Save review" button); loading state
  while fetch; optimistic append; conflict = server timestamp wins (see §4).
- **States:** no `base` commits → honest "no git history for this file" state with findings
  overlay still available; findings empty → "no findings — good" (SPEC-06 §3 discipline).

## 4. API / WS contract

REST (additive; single `POST` is review-only, flagged in §7; all take optional `?repo=` → `_root()`
per SPEC-19):
- `GET /api/file/diff?path=&base=` → `git diff <base> -- <path>` unified content PLUS structured
  parsed hunks `{hunks:[{old_a,old_b,new_a,new_b,lines:[...]}]}` when parseable.
- `GET /api/file/at?path=&ref=` → file content at `ref` (`git show <ref>:<path>`) → the
  DiffEditor original. `ref` must be a **full/shortened commit sha**, sanitized (`^[0-9a-f]{7,40}$`
  or `HEAD`).
- `GET /api/file/review?path=` → `{path, comments:[{id,line,thread_id,body,author,ts}]}`.
- `POST /api/file/review` `{path, action:'add'|'reply'|'edit'|'delete', ...}` → stored via
  additive writer; returns updated comment list. **(first non-GET endpoint on `/api/file/*`)**.

WS: none required; the review view refetches on SPEC-18 `file.changed`.

## 5. Data contract

- **Reads:** existing `findings` table (`store.py` / `stack/common.py:5` findings schema) for the
  auto overlay; `retrieve.history` for the base picker.
- **New write (review comments):** an **additive** jsonl/SQLite file under `cip_dir(_root())/data/`
  (e.g. `reviews.jsonl`, one JSON object per line with `ts` + `path` filter); **no new schema in
  index.db** (keeps index DB pure). Written with write-lock/append-atomic (single user, localhost).
  The store path derives from the project root, so each project keeps its own reviews.

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge.file_diff(root, path, base)`** — mirrors `impact_diff` pattern (`stack/impact.py:116`):
   `subprocess.run(["git","diff","-U3", base, "--", path])`; parse hunks with a small
   `_parse_unified` helper (lines like `@@ -a,b +c,d @@`).
2. **`web_bridge.file_at(root, path, ref)`** — `git show <ref>:<path>`; validate `ref` pattern;
   resolve under `root` for the file argument; `_err("REF_INVALID")` on failure.
3. **`web_bridge.review_store`** — read (`GET`) + write (`POST`) manager for the additive
   `reviews.jsonl`; list filtered by `path`; each comment `{id (uuid), path, line, thread_id,
   body, author:"web-console", ts}`. Auth N/A (localhost, NFR-4).
4. **History full-hash variant** — add `full=True` to `retrieve.history` or a
   `retrieve.history_shas(root, path, n)` returning `{sha, date, author, msg}` so the base picker
   and diff use stable refs (today `retrieve.py:396` formats `%h %ad %an %s` only).

## 7. Core issues / risks (flagged, grounded)

- **CORE-NEW — `POST /api/file/review` is the first write on the file surface.** The bridge rule
  (`web_bridge.py:11` additive, GET read-only by convention) allows additive endpoints; this spec
  declares it explicitly: it writes **review UI data** to `data/reviews.jsonl`, never source files.
  Gate after owner sign-off. *(New issue — flag in 09.)*
- **CORE-55 carryover — client job-event typing mismatch could affect review WS later:**
  `useWebSocket` expects `JobEvent` (`api.ts:41`), WS sends `{type, ts, payload}` (`web_bridge.py`)
  — reconcile before SPEC-18 wires `file.changed` consumers. *(Cross-reference SPEC-18 §7.)*
- **Watch: `git diff` on huge/new files** — DiffEditor streaming (>2 MB), `_ttl_cache` off for
  per-commit `file/at`.
- **Watch: `monaco-review` maturity** — MIT and maintained (972 commits), but vetted integration
  is required; if blocked, roll back to hand-rolled `IModelDecorationOptions` comments (research
  §2.2 fallback) with the same additive writer.

## 8. Acceptance checks (from §6 / §7.5 / feature request)

- [ ] Review mode shows side-by-side diff (original@base vs working tree) with unchanged regions
      hidden; base picker lists real commits (full SHAs).
- [ ] Findings decorations appear on the correct line with hover detail; clicking scrolls.
- [ ] User review: add/edit/reply/delete comments persist across reload; threaded display.
- [ ] `reviews.jsonl` additive; source files never written by review (no file-write path exists);
      review store is per-project (SPEC-19 root-derived path).
- [ ] Diff/at endpoints reject traversal and bad refs (`_err` envelope).
- [ ] No dead controls: every review action maps to a real endpoint.