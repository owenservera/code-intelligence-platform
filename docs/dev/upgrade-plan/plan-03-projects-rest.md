# PLAN-03 — Projects REST endpoints (list / register / unregister / status)

**Phase 3 of 10.** Builds SPEC-19 §4. Grounded 2026-08-17.
**Depends on:** PLAN-01 (registry), PLAN-02 (`_root()`).
**After this phase:** the UI can list, add, and remove projects; status chips are truthful.

## Goal

Expose the registry over the bridge: `GET /api/projects` (registry + live status join),
`POST /api/projects` (register a folder), `DELETE /api/projects?id=` (unregister). Registering a
folder **does not init it** — onboarding is PLAN-04.

## Truth anchors (verified)

- Endpoint pattern to mirror: `@app.get("/api/status")` `web_bridge.py:105`, `/api/onboarding/status`
  `:1435` uses `InitDetector(ROOT)` `:1392`; `_ok`/`_err` `:64/68`.
- Per-project status probe sources (existing): daemon pid `cip_dir(ROOT)/daemon.pid` `:128`;
  index DB `cip_dir(ROOT)/index.db` `:135`; `detect_init_status(root)` `init_detector.py:370`;
  `findings` table via `file_findings(path,root)` `web_bridge.py:1783`; `index_status(root)` `server.py`.
- `registry` (PLAN-01) provides idempotent `register`; plan-02 `_root()` handles scoping.

## Atomic tasks

### Task 3.1 — `GET /api/projects` (list + status join)
- **Edit:** add `@app.get("/api/projects")` near the onboarding block (`web_bridge.py:1435` region).
- **Behavior:**
  1. `reg = get_registry()`; for each registered root: probe status **cheaply** (daemon pid exists?,
     `index.db` exists + mtime fresh?, `.cip` present via `cip_dir(root).is_dir()`).
  2. Return `_ok({"projects":[{id, root, name: basename, status:
     "initialized"|"indexed"|"no_cip"|"onboarding", last_onboard_ts, repo_type?}]})`.
     `repo_type` lazily via `detect_init_status(root)` only when cheap (skip if `index.db` stale).
  3. Never blocks on slow probes: wrap per-project probe in a small timeout/threadpool; partial
     failures → status field `"error"`, still listed.
- **Verify:** `GET /api/projects` returns `{ok:true, data:{projects:[...]}}` after Task 3.2 seeds one.

### Task 3.2 — `POST /api/projects` (register)
- **Edit:** add `@app.post("/api/projects")`. Request body `{root: str}` (Pydantic model).
- **Behavior:**
  - `os.path.abspath(normcase(root))`; require the folder exists (`Path.is_dir()`) else `_err("NOT_A_DIR")`.
  - `registry.register(root)`; return `_ok({id, root, status})` with live probe. Registering an
    already-registered root returns the same entry (idempotent, 200).
  - **No init** here — registration only (SPEC-19 §4: `?init=false` default).
- **Verify:** register a scratch folder → appears in `GET /api/projects`; repeat → same id; bogus path → `_err NOT_A_DIR`.

### Task 3.3 — `DELETE /api/projects?id=` (unregister)
- **Edit:** add `@app.delete("/api/projects")` (query `id`).
- **Behavior:** `registry.unregister(id)`; unknown id → `_err("UNKNOWN_PROJECT")`; never deletes files.
- **Verify:** delete removes entry; second delete errors; files on disk untouched.

### Task 3.4 — auto-register the launch root on console boot **[GAP-05]**
- **Edit:** at `web_bridge.py` import, after Task 2.1's `_LEGACY_ROOT` resolves: if
  `_LEGACY_ROOT` is not None → `get_registry().register(_LEGACY_ROOT)` (idempotent). Result: launching
  `cip web` inside any `.cip` project always lists that project in the switcher, so "manage from here"
  works with zero manual steps.
- **Also honor CLI selection (GAP-04, PLAN-06):** if the console is started with `--root <folder>`
  (env `CIP_WEB_ROOT`), register that folder instead of the cwd walk-up.
- **Verify:** boot inside a `.cip` folder → project appears in `GET /api/projects`; second boot →
  same id, no duplicate.

## Acceptance (this phase ends green)

- [ ] All three verbs work against `http://localhost:8090/api/projects*`; envelope `{ok,data}`.
- [ ] Status chips reflect reality: registered-but-uninit → `no_cip`; after PLAN-04 → `indexed`.
- [ ] Idempotent register; NOT_A_DIR on missing folder; files never deleted by DELETE.
- [ ] **[GAP-05]** Launch root auto-registers on boot; `--root`/`CIP_WEB_ROOT` overrides the walk-up.
- [ ] Legacy `?repo=` default unaffected; `/api/projects` itself is root-independent (registry-level).

**Next:** PLAN-04 real onboarding over the web (init + profile + progress).