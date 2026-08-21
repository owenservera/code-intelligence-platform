# TRACKER — Multi-Project Console Upgrade

**Source of truth for phase/task status.** Update after every task (RUNBOOK §6). Docs win over memory.

## Phases

| # | Phase doc | Status | Acceptance | Notes |
|---|-----------|--------|-----------|-------|
| 1 | `plan-01-project-registry.md` | done | ✅ | registry module + CIP_HOME store |
| 2 | `plan-02-request-scoped-root.md` | done | ✅ | _root() sweep + GAP-01 + GAP-02 |
| 3 | `plan-03-projects-rest.md` | done | ✅ | /api/projects + GAP-05 |
| 4 | `plan-04-onboard-post.md` | done | ✅ | onboard/profile POST + init_flow |
| 5 | `plan-05-ws-multiproject.md` | done | ✅ | per-project WS/watch + GAP-03 |
| 6 | `plan-06-frontend-switcher.md` | done | ✅ (compile+API; UI clicks pending manual QA) | switcher/dashboard/wizard + GAP-04/06/07 |
| 7 | `plan-07-explorer-backend.md` | done | ✅ | /api/tree + PATH_ESCAPE |
| 8 | `plan-08-explorer-frontend.md` | pending | | tree frontend (spike gate) |
| 9 | `plan-09-review-renderer.md` | pending | | diff/at/review + reviews.jsonl |
| 10 | `plan-10-realtime-history.md` | pending | | edits/blame/log + timeline |

## GAP status

| GAP | Folded into | Status |
|-----|-------------|--------|
| GAP-01 `_CONFIG_PATH`→fn | P2 T2.4 | ✅ done |
| GAP-02 tolerant boot / registry-mode | P2 T2.1 | ✅ done |
| GAP-03 daemon port guard | P5 T5.4 | ✅ done |
| GAP-04 CLI `--project`/`--root` | P6 T6.6 | ✅ done (CIP_WEB_ROOT env var + cli.py flags) |
| GAP-05 auto-register launch root | P3 T3.4 | ✅ done |
| GAP-06 per-project onboarding gate | P6 T6.1 | ✅ done (verified: per-repo status; /onboarding removed from NO_REPO_PREFIXES) |
| GAP-07 SPA rebuild acceptance | P6 acceptance | ✅ done (dist regenerated, served, contains new /projects) |

## Active task

- **Phase:** 7 (COMPLETED). Explorer backend: `GET /api/tree` + `file_bundle` PATH_ESCAPE.
- **Completed tasks:**
  - P7 T7.1 — `_prune_name(name)` helper (DEFAULT_EXCLUDES + BACKUP_DIR_PREFIXES from `base.py`).
  - P7 T7.2 — `dir_listing(root, rel)` — resolve + PATH_ESCAPE guard (`is_relative_to` style), os.scandir,
    prune + symlink-loop skip, dirs-first sort, git status via one `git status --porcelain .`
    (`_git_porcelain_status`), non-git → all `""`.
  - P7 T7.3 — `GET /api/tree?path=&repo=` endpoint — `_ok(dir_listing(_root(), path))`, TTL cache 10 s
    (`tree:{path}` key, root-prefixed), PATH_ESCAPE / DIR_NOT_FOUND / TREE_FAILED errors.
  - P7 T7.4 — verified `file_bundle` traversal guard (`_safe_join` `web_bridge.py:2321` blocks
    `../../Windows/win.ini` → `PATH_ESCAPE`); valid bundle byte-identical. Evidence recorded in
    plan-07 (09-bugs-and-issues.md never-edit rule per AGENTS.md).
  - Verified: prune True/False set; root+nested listings; git M/? + non-git ""; TTL same-for-10s +
    project-switch freshness (root-prefixed key); file-as-path DIR_NOT_FOUND; encoded escape safe.
- **Next unit:** P8 — `plan-08-explorer-frontend.md`: tree frontend (`fileApi.*`, FileView.tsx,
  SearchView links). Spike gate per plan-08 (verify endpoint shape first).
- **Verify command (next):** `npm run build` green in `web/` + browser click-through of the tree.