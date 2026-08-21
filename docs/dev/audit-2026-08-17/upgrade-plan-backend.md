# Audit — upgrade-plan backend (SPEC-16 / SPEC-19)

**Source of truth:** `lib/cipkg/web_bridge.py` (3521 lines), `lib/cipkg/project_registry.py`, `lib/cipkg/cli.py`
**Import test:** `from cipkg import web_bridge` → ok; `import cipkg.project_registry` → ok. Bare `\bROOT\b` count = **0**. Substring `ROOT` = 13 (all inside renamed identifiers: `_CURRENT_ROOT`, `_LEGACY_ROOT`, `CIP_ROOT`, `CIP_WEB_ROOT`, `cli_root`, comments).

## Status table

| Phase | Claimed (TRACKER) | Actual | Evidence | Notes |
|-------|------------------|--------|----------|-------|
| P1 Registry | done | **DONE** | `project_registry.py:24-181` (`get_registry`, `home`, `list`, `register`, `unregister`, `get`, `has`, `touch_onboard`; id=`normcase(abspath)`; atomic `os.replace`+fsync; corrupt→`.bak`) | Matches plan-01 |
| P2 `_root()` sweep + GAP-01/02 | done | **DONE** | `web_bridge.py:35-76` (`_CURRENT_ROOT` ctxvar, `_legacy_root()`, `_LEGACY_ROOT`, `_root()`, `_require_root()`); middleware `93-108`; `ValueError→NO_PROJECT` `125-133`; `_config_path()` fn `696-698` + 11 sites; `_ttl_cache` root-prefix `169-171` | `\bROOT\b` grep = 0 |
| P3 `/api/projects` + GAP-05 | done | **DONE** | `web_bridge.py:1593` (GET+status join), `1656` (POST+`NOT_A_DIR`), `1693` (DELETE+`UNKNOWN_PROJECT`); auto-register `55-63`; `RegisterRequest` `1589` | Idempotent, no-file-delete present |
| P4 Onboard POST / profile | pending | **NOT IMPLEMENTED** | No `init_flow.py`; no `/api/projects/{id}/onboard`; no `/api/projects/{id}/profile` (only `GET /api/onboarding/status` `1710`) | Matches TRACKER |
| P5 Per-project WS/watch + GAP-03 | pending | **NOT IMPLEMENTED** | `_ws_clients` = flat `set[WebSocket]` `:368`; `_broadcast` iterates whole set `:372`; `ws_endpoint` `:3475-3506` ignores `?repo=`; `WatchManager` single-root `:596-669`; no `_DAEMONS` | GAP-03 daemon guard absent |
| P6 backend bits | pending | **PARTIAL** | `CIP_WEB_ROOT` honored `:59-63`; **but** CLI `--project`/`--root` flags absent (cli.py:723-726 only) | GAP-04 env-only |
| P7 `/api/tree` + PATH_ESCAPE | pending | **NOT IMPLEMENTED** | No `/api/tree`, no `dir_listing`; `file_bundle` `:2069` `Path(root)/path` with NO containment check → traversal live | Security bug (see below) |
| P9 diff/at/review + reviews.jsonl | pending | **NOT IMPLEMENTED** | No `file_diff`/`file_at`/`review_store`, no `reviews.jsonl`, no `/api/file/diff\|at\|review` | — |
| P10 edits/blame/git_log + file.changed | pending | **NOT IMPLEMENTED** | No `file_edits`/`file_blame`/`git_log`, no `history_shas`, no `file.changed` producer | — |

**Headline:** TRACKER is **accurate** — P1–P3 genuinely done; P4–P10 (and P5/P7 backend) absent. Docs do not overclaim the backend.

## MISSING / NOT IMPLEMENTED (specifics)
- **P4:** `lib/cipkg/init_flow.py` does not exist; `cmd_init` not extracted to `init_project`; no `POST /api/projects/{id}/onboard`; no `POST /api/projects/{id}/profile`; F-11/CORE-41 warning surfacing absent.
- **P5:** WS not keyed by project (`_ws_clients` still `set`, `:368`); `_broadcast`/ws_endpoint not repo-scoped; `WatchManager` not per-project; GAP-03 (`_DAEMONS`, port-reuse/conflict) absent.
- **P7:** `/api/tree` endpoint, `dir_listing()` helper, and `PATH_ESCAPE` retrofit on `file_bundle` all absent.
- **P9:** No reviews backend, no diff/at endpoints.
- **P10:** No edit-history/blame/git-log endpoints, no live `file.changed` event.
- **GAP-04 (CLI):** `cip web --project`/`--root` not defined in `cli.py:723-726` (env var only works).

## OBVIOUS ENHANCEMENTS / BUGS / RISK
- **[P0 SECURITY] Path traversal in `file_bundle` (`web_bridge.py:2069`):** builds `real = Path(root)/path` and never resolves/validates containment. `GET /api/file?path=../../etc/passwd` reads files above root. Highest-priority; plan-07 T7.4 explicitly calls this out as unfixed. Affects the *live* SPEC-06 `/api/file` endpoint too. Fix: `real = (Path(root)/path).resolve(); assert real.is_relative_to(Path(root).resolve())`.
- **[P3/GAP-05] Import-time side effect:** `web_bridge.py:56-63` calls `get_registry().register(...)` at *module import*, touching disk + `~/.cip`. Plan-01 claims the module is "import-safe / no side effects" — registry write at import violates that; a read-only import now performs a write.
- **[P2 nuance] CI gate fragility:** word-boundary `\bROOT\b` = 0 (P2 gate passes), but substring `ROOT` = 13. Any CI gate written as a raw `ROOT` substring search will **fail** (returns 13) — must exclude renamed identifiers.
- **[GAP-02] Coarse granularity:** every root-requiring endpoint returns `NO_PROJECT` when booted from a non-`.cip` folder, but there is no `?repo=` threading yet (P6), so registry-only mode is currently a dead-end (no way to select a project over the wire from the backend alone).
- **[both] Missing tests:** none of the test files reference `project_registry`, `web_bridge`, `/api/projects`, `/api/tree`, or `onboard` — new backend has **zero** automated coverage (AGENTS.md requires 80% + regression tests).
