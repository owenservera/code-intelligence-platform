# Gaps & Enhancements — Consolidated Backlog

Prioritized list of everything found during the audit that is **missing, broken, or should be hardened** to get both areas "fully working." Sourced from the four area reports + first-hand checks.

Legend: **P0** = security/correctness, do first · **P1** = blocks the stated "fully implemented" goal · **P2** = quality/polish.

---

## P0 — Security / correctness (fix immediately)

> **Status 2026-08-17:** Both P0 items **FIXED** (code changes applied + verified).

1. **[FIXED] Path traversal in `file_bundle`** — `lib/cipkg/web_bridge.py`
   Added `_safe_join(root, path)` helper (resolves + asserts containment, raises `ValueError("PATH_ESCAPE")`). `file_bundle` now uses it; `GET /api/file` maps it to `_err("PATH_ESCAPE", ...)`. Verified: `../../etc/passwd`, `../outside`, `/etc/passwd`, and Windows `..\..\win.ini` all blocked. (Did not add a committed regression test yet — see P2 #13.)

2. **[FIXED] `SearchView.tsx` latent crash** — removed the no-argument `qc.invalidateQueries()` (threw in React Query v5 on the prediction button). Replaced with a TODO stub; `npx tsc --noEmit` clean.

---

## P1 — Upgrade-plan is only ~30% done (the bulk is missing)

The user expected this fully implemented. Reality: **P1–P3 done; P4–P10 absent** (TRACKER is accurate, the assumption was not).

3. **P4 — Onboard POST** ✅ **DONE (2026-08-17)** — `lib/cipkg/init_flow.py` `init_project`; `cmd_init` delegates; `POST /api/projects/{id}/onboard` (background job + `touch_onboard`); `POST /api/projects/{id}/profile` (`[profile]` tomlkit write); F-11 warnings surfaced via `load_config(warnings=)`. All verified in-process.
4. **P5 — Per-project WS + watch** `_ws_clients` is a flat `set[WebSocket]` (`web_bridge.py:368`); `_broadcast`/ws_endpoint not repo-scoped (`ws_endpoint:3475-3506` ignores `?repo=`); `WatchManager` single-root; **GAP-03 daemon port guard (`_DAEMONS`) absent**.
5. **P6 — Frontend switcher** No `activeProject`/`projects` in `stores/app.ts`; no `?repo=` threading in `api.ts`/`useWebSocket.ts`; no repo switcher in `TopBar.tsx`; no `/projects` dashboard (no `ProjectsView.tsx`, no route, no `LeftNav` entry); `App.tsx` gate is global not per-project (GAP-06).
6. **P6 — CLI `cip web --project`/`--root`** missing (`cli.py:723-726` only has `--port/--host/--no-browser`). GAP-04 only works via `CIP_WEB_ROOT` env.
7. **P7 — `/api/tree` + PATH_ESCAPE** endpoint + `dir_listing()` helper absent (P7 backend is entirely missing beyond the security fix in #1).
8. **P8 — Explorer frontend** No `RepoExplorer` tree rail, no `treeApi`, no lazy tree state in store.
9. **P9 — Review mode** No DiffEditor / findings overlay / additive `reviews.jsonl` comments; `FileView.tsx` has only `<FileEditor>`; `api.ts` has no `review`/`diff`/`at`.
10. **P10 — Realtime history** No `file_edits`/`file_blame`/`git_log` endpoints; `HistorySection` (`FileView.tsx:251`) still a plain commit string list; WS `file.changed` event **never handled** (`AppShell.tsx:20-35` `EVENT_INVALIDATE` has no `file.changed` key; `useWebSocket.ts:43,51` casts all to `JobEvent`); CORE-55 WS union type absent.

---

## P2 — Quality, robustness, polish

11. **Registry written at import time** — `web_bridge.py:56-63` calls `get_registry().register(...)` on module import (writes `~/.cip` from a "read-only" import; violates plan-01 "import-safe" claim). Move to first-request or CLI boot.
12. **CI gate fragility** — word-boundary `\bROOT\b` = 0 (P2 gate passes) but substring `ROOT` = 13 (renamed identifiers). Any raw `ROOT` substring CI check will false-fail.
13. **No automated tests anywhere** — registry, `/api/projects`, all SPEC endpoint groups, all frontend surfaces: zero committed test files. AGENTS.md requires 80% + regression tests. Add `tests/` for `project_registry`, each new endpoint, and at least smoke tests for SPEC views.
14. **ESLint cleanups (real, from editor LSP)** — missing explicit `type` on `<button>` in `CommandCenter.tsx:44`, `DaemonView.tsx:155`, `IndexView.tsx:199/208/237/343`, `SearchView.tsx:135/204/246/276`; index-as-key in `DaemonView.tsx:120`, `SearchView.tsx:254`, `FileView.tsx:212/263/300`. Build passes; lint hygiene only.
15. **`OnboardingView.tsx:61`** uses native `alert()` on sync failure — inconsistent with wizard styling; replace with in-view error state.
16. **Legacy replacement not confirmed deleted** — BUILD.md §2 gate lists deleting `web_server.py`, `dashboard-web`, legacy `static/`; verify before declaring SPEC-15 closed.
17. **Web-console GAP-10 / GAP-12** intentionally skipped (low priority) — document as accepted, not defects.
18. **Perf regression guard** — BUILD.md cites in-process timings (quality 4.2s, file impact 1.9s) with no committed benchmark to catch regressions.

---

## Recommended next steps (to "fully working")

1. Land **P0 #1** (path-traversal) as an immediate standalone security fix + regression test — independent of the upgrade.
2. Land **P0 #2** (SearchView crash) — one-line fix.
3. Resume the upgrade-plan strictly in order (RUNBOOK §2): **P4 → P5 (incl. GAP-03) → P6 (incl. GAP-04 CLI flags, GAP-06, GAP-07 rebuild) → P7 → P8 → P9 → P10**, updating `TRACKER.md`/`CHECKPOINT.md` per phase, and adding a test per new endpoint/feature.
4. Add the missing **test suite** (P2 #13) as part of each phase rather than at the end.
5. Fold **P2 #11/#12/#14/#15/#16** into the relevant phase or a follow-up hygiene pass; record GAP-13.. as needed per RUNBOOK §4.

*Note:* The web-console (SPEC-01–15) needs no further implementation work beyond P0 #1/#2 and the P2 polish items — it is genuinely complete.
