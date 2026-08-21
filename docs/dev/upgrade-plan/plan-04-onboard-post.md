# PLAN-04 — Onboard a project over the web (init + profile + progress)

**Phase 4 of 10.** Builds SPEC-19 §4/§6.3. Grounded 2026-08-17.
**Depends on:** PLAN-01/02/03.
**After this phase:** `POST /api/projects/{id}/onboard` runs full init as a background job; `POST
/api/projects/{id}/profile` persists `[profile]` config; onboarding errors (F-11/CORE-41) surface.

## Goal

Move the whole onboarding story into the web: currently `cmd_init(root)` (`cli.py:420`) is the only
full init path and is CLI-only. Extract its body into a callable `init_project(root)` so CLI + web
run the same code, and drive it from the bridge as a **background job** with `job.update` progress
(NFR-3 — a full `indexer.sync` must never block HTTP).

## Truth anchors (verified)

- `cmd_init(root)` `cli.py:420-469`: make `.cip/data` `:426`, copy AGENTS.md `:429-433`, `_install_hooks` `:435`,
  `_ensure_gitignore` `:436`, `install_agent_hooks` per agent `:440-445`, `detect.detect(root,cfg)` `:448`,
  `set_meta(con,"detection",...)` `:450`, **`indexer.sync(root, full=True, do_embed=False, progress=_progress)`** `:455`,
  `gitindex.git_index(root, depth)` `:461`.
- `InitDetector(root).detect()` `init_detector.py:50/61` and `detect_init_status(root)` `:370` — used by the
  read-only `GET /api/onboarding/status` `web_bridge.py:1435`/`:1392`.
- Job scaffold to reuse: `_job_progress` `web_bridge.py:290`, `_job_done` `:308`, `_job_error` `:318`,
  background-thread pattern at `/api/index/sync` `:1282`; `indexer.sync` progress callback → `_job_progress` `:1292`.
- **F-11/CORE-41:** `load_config` swallows repo-settings detection failure `base.py:153-157` (logged via
  `log_swallowed`). Onboard endpoints must surface this instead of silently defaulting (`DEFAULT_CONFIG["profile"]={}` `:66-67`).

## Atomic tasks

### Task 4.1 — extract `cmd_init` → `lib/cipkg/init_flow.py` (new) `init_project(root, progress=None)`
- **Edit:** create `lib/cipkg/init_flow.py`; `def init_project(root, progress: Callable|None = None) -> dict`.
  - Copy the body of `cmd_init` verbatim, replacing `print`/`_desc` with `progress(stage, msg)` calls
    and returning `{"ok":True,"stats":...}`. **Preserve all existing comments** (owner rule).
  - `cmd_init(root)` in `cli.py` becomes `from .init_flow import init_project; return init_project(root)` — the CLI path
    behavior is byte-for-byte identical.
  - Keep `detect.detect(root, cfg)` → `set_meta` and `indexer.sync(root, full=True, do_embed=False, progress=...)`.
- **Verify:** run `cip init` in a scratch folder → identical output/stats to before (compare files produced).

### Task 4.2 — `POST /api/projects/{id}/onboard`
- **Edit:** add endpoint near `/api/index/sync` (`web_bridge.py:1282` pattern).
- **Behavior:**
  1. Resolve root via registry id → `_root()`-independent (job targets the registered root, not the request's active root).
  2. Create `job_id`; background thread runs `init_project(root, progress=_job_progress)`; `_job_done/_job_error`.
  3. On success: `registry.touch_onboard(id)` (updates `last_onboard_ts`); return `_ok({job_id, status:"running"})` immediately.
  4. Pre-flight: folder exists, writable `.cip` dir target; else `_err("ONBOARD_INVALID")` before spawning.
- **Verify:** POST → job appears in `GET /api/jobs` (`:333`), progress streams, `index.db` created, status flips to `indexed`.

### Task 4.3 — surface F-11/CORE-41 instead of swallowing
- **Edit:** in `init_flow.init_project`, after `load_config(root)` capture the repo-settings failure:
  - `load_config` currently logs `log_swallowed("base.load_config.repo_settings", e)` (`base.py:156`).
  - Patch: expose the failure via a return field `warnings:["repo-settings profile load failed: <e>"]` and
    include it in the job's final payload; **do not halt init** (fallback config remains, `:157`).
- **Verify:** on a system without `detectors`, job completes with `warning` visible; UI (PLAN-06) renders it.

### Task 4.4 — `POST /api/projects/{id}/profile` (write `[profile]`)
- **Edit:** endpoint; reads `{profile: {subkey: value}}`.
  - Merge into `<root>/.cip/config.toml` `[profile]` via `tomlkit` (same lib as `/api/daemon/auto-manage`
    `web_bridge.py:446-453`); missing file → create from `DEFAULT_CONFIG` `base.py:67`.
  - Return `_ok({profile_section})`; **second non-GET on the config surface** — flagged (SPEC-19 §7).
- **Verify:** write → `load_config(root)` reflects the new `[profile]`; invalid TOML → `_err`.

## Acceptance (this phase ends green)

- [ ] `cip init` (CLI) produces identical artifacts via `init_flow` (no behavior drift).
- [ ] Web onboard of a non-git folder: `.cip/config.toml` written, index built, progress streamed, job terminal state OK.
- [ ] Re-onboard idempotent (re-runs full sync; registry ts updated).
- [ ] Missing `detectors` → warning surfaced in job result, init not silent-failed.
- [ ] Profile write round-trips through `load_config`; invalid input rejected.

**Next:** PLAN-05 makes WS + watch per-project.