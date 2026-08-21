# SPEC-18 — Realtime Edit History (FR-18)

- **Requirement source:** web-console feature request (FR-18, "real-time code edit history");
  `docs/dev/web-console-proposal/01-first-pass-proposal.md` §4; `02-research-upgrade.md` §3
- **Grounding verified:** 2026-08-17 against `lib/cipkg/{web_bridge,watch,retrieve,gapfill,store}.py`, `web/src/{hooks/useWebSocket,views/FileView,lib/api,components/layout/AppShell}.tsx`
- **Build order dependency:** SPEC-14 (WS contract), SPEC-16 (tree), SPEC-17 (diff renderer), SPEC-04 (sync/watch),
  **SPEC-19 (project registry — project-scoped)**.

---

## 1. Goal & owner intent

Show the **full edit lifecycle** of a file live: line-level blame (who last touched each line),
per-file commit timeline, and live refresh when the file changes on disk (watch/sync fires).
Realtime via the existing `/ws` — the same channel every other surface uses (NFR-1, SPEC-14). The
timeline merges `commits`/`commit_files`/`events` + watch deltas into one honest feed with
explicit empty/none states. Everything resolves against the **active project** (`_root()`, SPEC-19);
WS connections subscribe per project so live events are project-scoped.

## 2. Truth-grounded core surface (verified)

| Need | Core call (verified) | Returns |
|---|---|---|
| WS channel | `/ws` `web_bridge.py:2946`; `_broadcast` `:240`; `_schedule_broadcast` `:251` (`loop.call_soon_threadsafe`), `_ws_clients` `:236` | fan-out to all clients |
| Watch event loop | `watch.watch(root, interval, verbose, stop_event, progress)` `watch.py:14`; `progress` forwarded `watch.py:42`; WatchManager wraps `_watch.watch(...)` `web_bridge.py:475` | mtime-poll with sync on change |
| Per-file history | `retrieve.history(root, path, n)` `retrieve.py:374` — `%h %ad %an %s` | commit strings for a path |
| Line blame | `gapfill.blame(root, path, line)` `gapfill.py:181` — `git blame --line-porcelain` (`gapfill.py:185`), `-L` per line (`:187`) | author/commit/line summary |
| Commit index tables | `commits(sha,ts,author,message,files_changed)` `store.py:46`; `commit_files(sha,path)` `store.py:48`; populated by `git_index()` `gitindex.py:34-38` | durable per-file commit log |
| Signals/events | `events(ts,kind,payload)` `store.py:37`; `signals` `store.py:51` | activity/signals for the feed |
| Client WS hook | `useWebSocket(handlers)` `web/src/hooks/useWebSocket.ts:10`; `wsRef` + backoff `:7-13`; AppShell mounts it `AppShell.tsx:15` | typed dispatch + reconnect |
| Client history UI today | `HistorySection` `FileView.tsx:251` renders `fileApi.history` strings `• {c}` | replace/augment with structured timeline |
| Git status for tree/feed | `git status --porcelain` (SPEC-16 §6) | modified set for live feed |

**Gap notes:** (a) `watch.py` calls `sync` but emits **no per-file change event** — spec adds one
(§6); (b) `retrieve.history` returns only shortened commit strings (§6.4 in SPEC-17 adds full sha);
(c) `gapfill.blame` returns aggregates (`top_authors`, `commits_touched`) not per-line rows — spec
adds a per-line variant (§6.2).

## 3. UI/UX contract

- **Per-file timeline** (replaces/upgrades `HistorySection` `FileView.tsx:251`): structured list —
  avatar/author, full-ish sha (first 7), relative date, message; click row → open SPEC-17 diff at
  that commit (`base=<sha>`). Empty → "No commits for this file yet." Feed merges:
  1. `commits`/`commit_files` for the path (durable, from `git_index`/`git log`).
  2. Live `events` rows whose payload references the path (SPEC-04 celebration feed).
  3. SPEC-18 live watch deltas (see WS below).
- **Blame gutter (VS Code Timeline feel):** per-line hover chip in the Monaco gutter showing
  author + commit for that line (from `git blame --line-porcelain`, per-line variant); click chip
  → diff at that commit. Off by default (toggle) to spare payload on large files.
- **Live refresh:** when `file.changed` arrives for the open path, `invalidateQueries(['file',
  path])` (+ history/tree keys) via the existing QueryClient — mirrors SPEC-14 §3 refresh patterns.
- **Commit graph (repo-wide, "everything" scope research `02 §3.2`):** optional dashboard view
  using `commit-graph` (liuliu-dev, infinite scroll) fed by `GET /api/git/log`; not in the file
  rail.

## 4. API / WS contract

WS (extends SPEC-14 event set, same `{type, ts, payload}` shape `web_bridge.py`; `?repo=` scopes
the connection per SPEC-19):
- `file.changed {path, kind}` where `kind ∈ {"modified","added","deleted"}` — emitted by the watch
  manager when `watch.py` detects a change (before/after the `sync` call, `watch.py:37-45`), via
  `_schedule_broadcast` from the watch thread. `path` is project-relative (SPEC-16 §6
  normalization); `payload.repo` identifies the project (SPEC-19 WS fan-out).

REST (all GET, additive; optional `?repo=` → `_root()`):
- `GET /api/file/edits?path=&n=` → merged structured feed:
  `{path, entries:[{kind:"commit"|"event"|"active", sha?, ts, author?, message?, ref?}]}` careful
  merge + ordering; capped `n` (default 30).
- `GET /api/file/blame?path=&line=` → per-line or whole-file rows
  `[{line, sha, author, summary, ts}]` (per-line variant of `gapfill.blame`, `gapfill.py:185`).
- `GET /api/git/log?n=&skip=` → structured `{commits:[{sha,ts,author,message,files}]}` from
  `git log` (same `--pretty=format` technique `gitindex.py:13`) for the repo-wide commit graph.

## 5. Data contract

- Reads: `commits` + `commit_files` (`store.py:46,48`), `events` (`store.py:37`), `signals`
  (`store.py:51`), `git log`/`git blame` outputs. No new tables.
- **New live producer:** watch loop change-set — in-memory only (SPEC-14 §5: job/live state in
  memory, not persisted beyond `events`), deduped by path + debounced coalesce (SPEC-14 §3 ≤4 fps).

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge` live `file.changed` producer** — in `WatchManager._run` (`web_bridge.py:457`)
   capture `watch.py`'s per-tick change (new `progress`/callback or a delta fn in `watch.py`):
   after `_snapshot()` differ `watch.py:37-45`, emit `_schedule_broadcast({"type":"file.changed",
   "payload":{"path":...,"repo":<project>}})` for each changed tracked relpath; debounce burst.
   The watch loop per project (SPEC-19 §7) tags events with that project's id.
2. **`web_bridge.file_edits(root, path, n)`** — merge query over `commit_files`/`commits` +
   `events` (kind ∈ commit-like) filtered to path, ordered by ts desc, capped.
3. **`web_bridge.file_blame(root, path, line=None)`** — parse `git blame --line-porcelain`
   (`gapfill.py:185`) into per-line rows `{line, sha, author, summary, ts}`; `line` optional
   (single line = cheap). Reuse `_parse_blame` from gapfill when present.
4. **`web_bridge.git_log(root, n, skip)`** — structured `git log` (`gitindex.py:13` format) for
   the optional global commit graph; `_ttl_cache` 30 s.

## 7. Core issues / risks (flagged, grounded)

- **CORE-55 carryover — WS payload vs client type mismatch.** Server emits `{type, ts, payload}`
  (`web_bridge.py`), client `useWebSocket` casts to `JobEvent {type, job_id, command, data,
  timestamp}` (`api.ts:41`). Before any `file.changed` handler, **reconcile the type**: client
  must accept both job-events and typed events (union type) or the feed silently drops. *(New
  issue — flag in 09.)*
- **CORE-16 carryover — `watch.watch` has no per-file callback.** Emitting `file.changed` needs a
  new optional callback param at `watch.py:14` (backward compatible; NEWS None default) or a
  post-hoc diff of `_snapshot()` results — do not fork the loop.
- **Watch: `git blame` cost on huge files** — per-line blame for the gutter is N-row; gate by
  file size (>2 MB → skip blame gutter, show "blame not shown for large files"); single-line query
  is cheap.
- **Watch: dedupe/feed correctness** — commit rows are rewritten wholesale by `git_index`
  (`gitindex.py:30-32 DELETE`), so `edits` should read `git log` (live truth) rather than stale
  `commits` when the index is fresh-backed; document precedence.

## 8. Acceptance checks (from §6 / §7.5 / feature request)

- [ ] Open file edits while `watch` runs → `file.changed {path}` fires; open file/rail refreshes
      live (no manual reload).
- [ ] Timeline shows commits + live events merged, ordered, empty states honest.
- [ ] Blame gutter shows per-line author/commit; clicking opens diff at that commit (SPEC-17).
- [ ] `GET /api/file/edits`/`blame`/`git/log` return structured shapes; caps honored; traversal &
      ref validation enforced.
- [ ] Global scope: `?repo` scopes edits/blame/log to the active project; WS `file.changed` only
      reaches connections subscribed to that project (SPEC-19).
- [ ] WS type contract reconciled (union) — no dropped `file.changed` on the existing hook.
- [ ] Repo-wide commit graph renders (if "everything" scope) with pagination/infinite scroll.