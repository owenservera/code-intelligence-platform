# SPEC-04 — Index Management (FR-4)

- **Requirement source:** `05-requirements.md` §2 FR-4, §7.1(12), ISSUE-104/107, §7.4
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{indexer,maintain,gatekeeper,lock}.py`
- **Build order dependency:** SPEC-02 (jobs), SPEC-14 (WS progress), SPEC-01 (status).

---

## 1. Goal & owner intent

Live index stats (files/symbols/chunks/edges/vectors, last_sync, freshness) that auto-refresh;
trigger sync (full/reembed), index, rebuild, vacuum, verify-index — all with visible progress;
watch-mode indicator; live updates as watch/sync runs (§7.1-12). Full sync is a long job (~18 min
on this repo, 07-intel §3.2) — must run as a background job with progress + ETA, never in-request.

## 2. Truth-grounded core surface (verified 2026-08-15)

| Need | Core call (verified) | Returns |
|---|---|---|
| Sync (incremental) | `indexer.sync(root, full=False, do_embed=True, progress)` `indexer.py:405` | stats `{files,symbols,chunks,edges,vectors,dirty,deleted,embedded,ms}`; wrapped in `WriteLock` |
| Sync (full/reembed) | same, `full=True` / `do_embed=False` | same |
| Embed-only | `indexer.embed_pending(con, cfg, batch=64, progress)` `indexer.py:250` | count embedded |
| Rebuild (wipe+full) | `maintain.rebuild(root, progress)` `maintain.py:5` | deletes `index.db{-wal,-shm}` then `sync(full=True)` |
| Verify index | `maintain.verify(root, repair=False)` `maintain.py:16` | `{checked, drift:[{path,status}], repaired?}` |
| Vacuum | `maintain.vacuum(root, event_days)` `maintain.py:39` | `{events_pruned, orphan_vectors}`; prunes `events` older than `[maintain].event_days` (default 30) |
| Watch mode | `watch.watch(root, interval, verbose)` `watch.py:14` | infinite loop; mtime-snapshot debounce → `sync`; prints status |
| Stats | `indexer.compute_stats(con)` `indexer.py:285` | `{files,symbols,chunks,edges,vectors}` (5 COUNTs) |
| Freshness | `server.index_status(root)` `server.py:52` | `last_sync, lag_s, fresh(<300s), schema_version, embedder, fts` |
| Admission preview | `gatekeeper.admission_report(root)` `gatekeeper.py:177` | `{mode, index_tiers, skipped, examples}` (trust/transparency) |
| Per-file decision | `gatekeeper.explain(root, rel)` `gatekeeper.py:196` | one-line why-included/excluded |
| Schema upgrade | `upgrade` cmd → `store.connect` CORE_SCHEMA + migrations (`store.py`) | in-place; schema_version meta |
| Concurrency | `lock.WriteLock(root)` (`lock.py`) | single-writer gate for sync/rebuild/vacuum |

**Config anchors (`config.default.toml`):** `[index]` (include/exclude, ast_aware_chunking —
see BUG-011/024), `[perf] workers`, `[embed] batch_size`, `[maintain] event_days=30`.

## 3. UI/UX contract

- **Index panel** (status cluster → detail): live counters with last_sync + freshness chip
  (fresh/stale/never); index-activity indicator when a job is running (phase + progress bar).
- **Actions:** Sync (incremental) · Full sync (confirm) · Re-embed (confirm) · Rebuild
  (confirm, warns DB wiped) · Verify (with repair toggle) · Vacuum (confirm; `--days` param).
  Each → job with progress (SPEC-02).
- **Watch mode indicator:** toggle/indicator showing `watch` is running; live delta feed
  (synced +d -d ~emb in Nms) as it happens.
- **Admission view:** `admission_report` rendered as trust/transparency table (tier counts,
  skip reasons, examples); `explain(file)` per-file decision with reason; deep-link from
  file panel.
- **States:** idle → scan (0..N files) → parsing → linking → embedding (with ETA) → done/error;
  cancelled. Stats refresh live on each phase completion via WS.

## 4. API / WS contract

REST:
- `GET /api/index/status` → `index_status(root)` + `compute_stats` + admission summary.
- `POST /api/index/sync` `{full?, reembed?}` → `{job_id}` (202).
- `POST /api/index/rebuild` → `{job_id}` (destructive confirm).
- `POST /api/index/verify` `{repair?}` → `{job_id}` (or sync result).
- `POST /api/index/vacuum` `{days?}` → `{job_id}`.
- `POST /api/index/watch` `{enable, interval?}` → starts/stops a watch worker → `{job_id}`.
- `GET /api/admission` → `admission_report(root)`.
- `GET /api/admission/explain?path=` → `explain(root, rel)`.

WS (`/ws`, SPEC-14):
- `job.progress` (phase scan/link/embed + cur/total), `job.done` (stats), `job.error`,
  `index.update` (fresh stats after each job), `watch.event` (delta line).

## 5. Data contract

- All stats from existing tables + `meta.last_sync`. No new tables.
- **Snapshot table** (ISSUE-107, §5 backend additions): write one row per sync/audit/consolidate
  (ts, health, components, counts, severity) → powers B1/B2/B3/D2 trends + full-history retention
  (§7.1-8). Written off the hot path, once per job completion.
- `events` table already records each `sync` (`indexer.py:400`); keep as the durable activity log.

## 6. Backend additions (lib/cipkg in scope)

1. **`snapshots` table + writer** — `store.py` schema add; `web_bridge.write_snapshot(...)`
  called after sync/audit/consolidate jobs; retains indefinitely (§7.1-8, prune only via vacuum).
2. **Watch-worker manager** — `web_bridge.WatchManager` running `watch.watch` in a thread,
  broadcasting `watch.event` + `index.update`; allow start/stop from UI (watch is infinite —
  must never block).
3. **Progress normalization** — map `sync` phases (scan/link/embed) to a unified job progress
  schema; add ETA from `cur/total` + elapsed (SPEC-02, SPEC-14).
4. **`indexer.sync` → snapshot hook** — after stats computed, write snapshot row (addition 1)
  inside the same job (post-commit).

## 7. Core issues / risks (flagged, grounded)

- **CORE-15 — `maintain.verify` rehashes every file (full read) and `rebuild` deletes DB files.**
  `maintain.py:16-37` loops all `files` rows reading + sha1-ing; `maintain.py:5-14` removes
  `index.db*` before re-sync. → Both must run as jobs with progress + confirm; verify can be
  slow on big repos (surface as long job, not a read). *(New issue.)*
- **CORE-16 — `watch.watch` has no stop mechanism and logs to stdout only.**
  `watch.py:14-34` `while True` + `print`. → Web needs the WatchManager (addition 2) with a
  stop flag; structured watch events require patching `watch` to emit progress (or capture stdout).
  *(New issue.)*
- **CORE-17 — `vacuum` prunes `events` by `[maintain].event_days` (default 30) — conflicts with
  full-history snapshot retention.** `maintain.py:42-45`. Snapshot history (ISSUE-107, §7.1-8)
  must NOT be pruned by the same sweep; snapshot rows must be exempt or live elsewhere. *(New issue.)*
- **CORE-18 — `indexer.sync` embedded field name collision:** `stats` uses `embedded=n_emb`
  (count) but `watch` prints `stats['embedded']` as `~{emb}` (`watch.py:30`) — consistent, but the
  JSON key `embedded` means "embedded count", while `embed_pending` returns total vectors. Verify
  unit (count vs total) before rendering charts. *(Low; flag in UI tooltips.)*
- **Watch: full sync ≈18 min on this repo** (07-intel §3.2, 2,566 vectors) — confirm full sync
  is opt-in background job with ETA + cancel; incremental is fast. Reconfirm BUG-018 (perf debt)
  is not in the critical path for v1 UI.
- **Watch: `upgrade` runs CORE_SCHEMA migrations in-place** — confirm-before-run; if schema
  version > DB version, offer it as a dedicated "Upgrade schema" destructive-ish action.

## 8. Acceptance checks (from §6 / §7.5)

- [ ] Index stats live; freshness chip correct (fresh/stale/never).
- [ ] Sync/full/reembed/rebuild/verify/vacuum run as jobs with phase progress + ETA + cancel.
- [ ] Rebuild/vacuum require explicit confirmation.
- [ ] Watch mode shows live delta feed; toggles off cleanly.
- [ ] Snapshot rows written per sync/audit; B1/B2/B3/D2 trends render (SPEC-09).
- [ ] Snapshot history is not pruned by the events-vacuum sweep (CORE-17 resolved).
