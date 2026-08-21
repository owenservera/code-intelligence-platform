# PLAN-10 — Realtime edit history: timeline + blame + live `file.changed`

**Phase 10 of 10.** Builds SPEC-18 §4-6. Grounded 2026-08-17.
**Depends on:** PLAN-05 (WS + watch producer), PLAN-07/08 (tree + open file), PLAN-09 (diff at commit).
**After this phase:** full edit lifecycle of a file — structured timeline, per-line blame gutter, and
live refresh when the file changes on disk — plus the repo-wide commit graph.

## Goal

Replace the plain-commit-string `HistorySection` (`FileView.tsx:251`) with a structured feed merging
commits + live events + watch deltas; add per-line blame (VS Code Timeline feel); refresh the open file
live via `file.changed`. All project-scoped via `_root()` + per-project WS (PLAN-05).

## Truth anchors (verified)

- `file.changed` producer already emitted in PLAN-05 §5.2 from `WatchManager._run` (`web_bridge.py:504`,
  after `watch.py:37-42` detect) with `payload.{path,repo}`.
- `retrieve.history(root, path, n)` `retrieve.py:374`; `history_shas` (PLAN-09 §9.2).
- `gapfill.blame(root, path, line)` `gapfill.py:181` — `git blame --line-porcelain` `:185`, `-L` `:187`.
- Tables: `commits(sha,ts,author,message,files_changed)` `store.py:46`; `commit_files(sha,path)` `store.py:48`;
  `events(ts,kind,payload)` `store.py:37`; `signals` `store.py:51`.
- WS client: `useWebSocket(handlers)` `AppShell.tsx:56`, hook `web/src/hooks/useWebSocket.ts:10`; **CORE-55** type mismatch
  (server `{type, ts, payload}` vs client cast to `JobEvent` `api.ts:41`) — must reconcile here.
- Commit graph option: research §3.2 `commit-graph` lib (liuliu-dev), fed by `GET /api/git/log`.

## Atomic tasks

### Task 10.1 — backend: `file_edits(root, path, n)`
- **Edit:** `web_bridge.py` — merged feed: `commit_files`→`commits` for the path + `events` whose
  payload references the path; order ts desc; cap `n` (default 30). Read **live git truth** (`history_shas`,
  PLAN-09) rather than possibly-rewritten `commits` (SPEC-18 §7 dedupe note, `gitindex.py:30-32` DELETE).
- **Endpoint:** `GET /api/file/edits?path=&n=` → `{path, entries:[{kind:"commit"|"event"|"active", sha?, ts, author?, message?, ref?}]}`.
- **Verify:** merged + ordered; empty file → honest `[]`.

### Task 10.2 — backend: `file_blame(root, path, line=None)`
- **Edit:** `web_bridge.py` — parse `git blame --line-porcelain` (`gapfill.py:185`) per-line rows
  `{line, sha, author, summary, ts}`; `line` optional (single-line cheap). **Gate by file size**
  (>2 MB → `{"blame":"too_large"}` instead of N-row blast) (SPEC-18 §7).
- **Endpoint:** `GET /api/file/blame?path=&line=`; **Verify:** rows for sample file; single-line; too_large gate.

### Task 10.3 — backend: `git_log(root, n, skip)`
- **Edit:** `web_bridge.py` — structured `git log` (`gitindex.py:13` format technique) →
  `{commits:[{sha, ts, author, message, files}]}`; `_ttl_cache` 30 s (PLAN-02 keyed).
- **Endpoint:** `GET /api/git/log?n=&skip=`; **Verify:** pagination + shape.

### Task 10.4 — reconcile CORE-55 WS types (client)
- **Edit:** `web/src/lib/api.ts:41` + `useWebSocket.ts` — union type `CipEvent =
  JobEvent | {type:'file.changed', payload:{path,repo,kind}} | ...`; dispatch by `type`; **never drop
  unknown types** (log once). This unlocks the live feed (SPEC-18 §7).
- **Verify:** a `file.changed` broadcast reaches the handler; no console "unknown event" spam.

### Task 10.5 — frontend: structured timeline + blame gutter + live refresh + commit graph
- **Edit:** `FileView.tsx` (`HistorySection` `:251` → new `TimelineSection`):
  - **Timeline:** rows from `fileApi.edits` (avatar/author, first-7 sha, relative date, message);
    click → `Review` at `base=<sha>` (PLAN-09). Empty state "No commits for this file yet."
  - **Blame gutter:** per-line chip on hover (from `fileApi.blame`); click → diff at that commit;
    **off by default** (toggle) (SPEC-18 §3).
  - **Live refresh:** on `file.changed {path}` for the open path → `invalidateQueries(['file', path])` +
    timeline/tree keys (SPEC-14 §3 pattern).
  - **Commit graph:** optional `/projects`-level view via `commit-graph` fed by `/api/git/log` (infinite scroll).
- **Verify:** live edit (watch on) refreshes open file; timeline merges commits+events; blame gutter
  works on small files, gated on huge; graph paginates (SPEC-18 §8).

## Acceptance (this phase ends green)

- [ ] `file.changed` fires on disk edit → open file + rail refresh without reload (PLAN-05 watch running).
- [ ] Timeline merged + ordered + honest empty states; click opens diff at commit.
- [ ] Blame gutter per-line author/commit; >2 MB gated; toggle off by default.
- [ ] `edits`/`blame`/`git/log` structured; caps honored; traversal + ref validation enforced.
- [ ] CORE-55 reconciled — union type, no dropped `file.changed`.
- [ ] Repo-wide commit graph renders with infinite scroll (if in scope).

**End of 10-phase plan.** After this: full acceptance pass against `05-requirements.md` §6/§7.5, the
three landed specs' acceptance lists, and `cip selftest` + web `npm run build` green.