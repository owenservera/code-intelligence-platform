# PLAN-02 — Request-Scoped Root (`_root()` contextvar sweep)

**Phase 2 of 10.** Builds SPEC-19 §4/§6.2. Grounded 2026-08-17.
**Depends on:** PLAN-01 (registry).
**After this phase:** every web_bridge endpoint reads the project root per request; legacy `cip web`
(no `?repo=`) behaves exactly as today via default fallback.

## Goal

Replace the module-global `ROOT = repo_root()` (`web_bridge.py:36`) with a **request-scoped root**:
FastAPI middleware reads `?repo=` (or `X-CIP-Project` header), resolves it via the registry, and sets
a `contextvars.ContextVar`. Endpoints call `_root()` instead of `ROOT`. This is the biggest item —
**138 `ROOT` references** across ~80 endpoints — but it is mechanical and low-risk because the core
lib helpers already accept `root` params.

## Truth anchors (verified)

- `ROOT = repo_root()` `web_bridge.py:36`; **140 `\bROOT\b` occurrences** counted in file (module + call sites).
- Endpoint inventory: 74 REST + `/ws` + `/` SPA catch-all (`@app.*` at `web_bridge.py:105..3091`).
- `repo_root()` raises `SystemExit` without `.cip` (`base.py:81`); registry (PLAN-01) replaces traversal for scoped requests.
- These helpers already root-aware: `load_config(root)` `base.py:118`, `retrieve.history(root,..)`, `gapfill.blame(root,..)`, `impact_diff(root,..)`, `store.connect(root)`, `_warm_daemon` uses `load_config(ROOT)` `:79`.
- Envelope `_ok`/`_err` `web_bridge.py:64/68` — sweep must not change.

## Atomic tasks

### Task 2.1 — contextvar + middleware (edit `web_bridge.py` top) **[GAP-02: tolerant boot]**
- **Edit:** after line 36 replace `ROOT = repo_root()` with:
  ```python
  _CURRENT_ROOT: contextvars.ContextVar[str | None] = contextvars.ContextVar("cip_root", default=None)
  def _legacy_root() -> str | None:
      """GAP-02: console boots from ANY folder (registry-manager mode).

      repo_root() raises SystemExit (base.py:81) when no .cip exists above cwd;
      the central console must not crash — it falls back to registry-only mode
      where every endpoint requires an explicit ?repo=."""
      try:
          return repo_root()
      except SystemExit:
          return None
  _LEGACY_ROOT = _legacy_root()  # fallback root; never touched by a ?repo= request
  def _root() -> str | None:
      return _CURRENT_ROOT.get() or _LEGACY_ROOT
  ```
- Add `import contextvars` to imports.
- **Registry-only mode:** every endpoint that *requires* a root must change `_root()` →
  `_require_root()` helper: `r = _root(); if not r: return _err("NO_PROJECT", "call with ?repo=<id>")`.
  Console in a non-CIP folder boots, lists `/api/projects`, onboards folders — but scoped calls 4xx
  until a project is selected. (PLAN-06's `?repo=` threading is mandatory, not optional, in this mode.)
- **Verify:** `cip web` from `C:\` (no `.cip` above) boots and serves the SPA; `/api/projects` returns
  200; `/api/status` (no repo) → `NO_PROJECT` envelope, not a crash.
- Add a **routing middleware** (`@app.middleware("http")`) that: reads `repo` from
  `request.query_params` or `request.headers.get("X-CIP-Project")`; if present, `registry.get(id)`
  → set `_CURRENT_ROOT.set(path)` in a token, `finally reset(token)`. Missing/invalid repo → do **not**
  fail; leave legacy root (SPEC-15 backward compat). Validated `repo` values only ever come from the
  registry — a hostile path string cannot inject; registry keys are normalized absolute paths.
- **Verify:** `cip web` boots; `GET /api/status` returns 200 with no `repo`.

### Task 2.2 — sweep call sites (`ROOT` → `_root()`)
- **Edit:** mechanically replace the 140 `ROOT` references with `_root()`. **Do not** touch `_root` defs,
  the `ROOT` comment, or any string containing "ROOT". Commanded per-endpoint, not via blind sed.
- **Covered surfaces (verified signatures):**
  - status/daemon/config: `:123` `load_config(ROOT)`, `:128` `cip_dir(ROOT)/daemon.pid`, `:135` `cip_dir(ROOT)/index.db`.
  - `_warm_daemon` `:79`; daemon endpoints `:429/431` `daemon_stop(ROOT)/start_daemon(ROOT,...)`.
  - `WatchManager._run` `:522` `watch.watch(ROOT,...)` → `watch.watch(_root(),...)` (PLAN-05 refines).
  - `file_bundle(path, root)` already takes `root` (`:1740`) — call sites pass `_root()`; **retense guard added in PLAN-07**.
  - Every endpoint body that references `ROOT` (search, symbols, graph, context, history, file/*, quality/*, memory/*, vis/*, export, env, admission, onboarding).
- **Verify gate:** grep gate `Select-String -Path web_bridge.py -Pattern '\bROOT\b'` returns **0 hits**
  except `_LEGACY_ROOT`/`_root()` definitions and the docstring. Add this as a CI grep check.
- **Fail-state:** any missed `ROOT` leaks cross-project data — the CI grep gate throws.

### Task 2.3 — `_ttl_cache` root-prefix
- **Edit:** `_ttl_cache` `web_bridge.py:91`: prepend `root` segment by calling `_root()` inside the
  key, i.e. `key = f"{_root()}|{key}"`. Two projects never collide (SPEC-19 §6.5).
- **Verify:** same endpoint, two `?repo=` → distinct cache entries; no stale cross-project hits.

### Task 2.4 — `_CONFIG_PATH` module constant → function **[GAP-01: config goes to wrong project]**
- **Bug:** `_CONFIG_PATH = Path(cip_dir(ROOT)) / "config.toml"` (`web_bridge.py:557`) is bound at
  **import time**, not per-request — it is NOT a `ROOT` call site, so a blind sweep misses it. Under
  `?repo=<id>` every settings GET/POST (`:668,670,790,792,834,844-849,877,893-895`) would read/write
  the *launch root's* config instead of the active project's — silently corrupting per-project settings.
- **Edit:** replace the constant with `def _config_path() -> Path: return Path(cip_dir(_require_root())) / "config.toml"`.
  Replace the 11 usage sites with `_config_path()`. `_require_root()` from Task 2.1.
- **Verify:** with project A active, `GET /api/config/full` reads `A/.cip/config.toml`; write via
  `POST /api/config` lands in A's file, never the legacy root's.

## Acceptance (this phase ends green)

- [ ] Bare-`ROOT` grep gate: 0 matches (CI-able).
- [ ] `GET /api/status`, `/api/search`, `/api/file?path=` still 200 with no `repo` (legacy root).
- [ ] **[GAP-02]** Console boots from a non-CIP folder (registry-only mode); scoped calls → `NO_PROJECT`, never crash.
- [ ] With `?repo=<id>` pointing at a second registered project, results are that project's (spot-check
      a search hit + a file bundle path).
- [ ] **[GAP-01]** Settings read/write hit the *active* project's `config.toml`, not the launch root's.
- [ ] `_ttl_cache` key carries root; switching projects yields correct fresh results.
- [ ] `python -m pytest tests/ -q` still green (bridge import-safe).

**Next:** PLAN-03 exposes the registry over REST.