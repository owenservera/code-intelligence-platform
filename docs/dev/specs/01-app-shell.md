# SPEC-01 — App Shell (FR-1)

- **Requirement source:** `05-requirements.md` §2 FR-1, §3 NFR-1/NFR-4, §7.1(2)(12)(13), §7.4
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{base,server,indexer,daemon}.py` + `config.default.toml`
- **Build order dependency:** none (first spec). Everything else mounts inside this shell.

---

## 1. Goal & owner intent

One FastAPI process on **one port** (default 8090, localhost bind) serving REST + WebSocket +
the compiled React SPA. Left nav / top bar + **command center as home** (§7.1-2), global palette
(Ctrl+K) reachable anywhere, and **always-visible status indicators** for connection / daemon /
index / embedder. Sleek modern dark dev-tool theme (§7.1-13). This is a **fresh build** — the
legacy `web_server.py`/`dashboard.py` surfaces are removed once coverage is complete.

## 2. Truth-grounded core surface (verified)

| Need | Core call (verified) | Returns |
|---|---|---|
| Attach / activation gate | `base.repo_root(start)` `base.py:65` | walks up for `.cip/`; **raises `SystemExit` if none** |
| Effective config | `base.load_config(root)` `base.py:109` | merged dict: `.cip/config.toml` → repo profile (`detectors.detect_repo_type`+`load_repo_profile`) → TOML defaults → hardcoded `DEFAULT_CONFIG` |
| Live index stats | `server.index_status(root)` `server.py:52` | `{files,symbols,chunks,edges,vectors,commits,signals,summaries,last_sync,lag_s,fresh,embedder,fts,schema_version}` |
| Raw counts | `indexer.compute_stats(con)` `indexer.py:285` | `{files,symbols,chunks,edges,vectors}` (5 COUNT queries) |
| Daemon status | `daemon.daemon_status(root)` `daemon.py:40` | `{pid, port, alive, warm, health:{warm,model,dim,pid,uptime_s}}` via `.cip/data/daemon.{lock,port}` |
| Config anchors | `config.default.toml` `[mcp] port=8080` `:122-123`, `[daemon] port=8765` `:134-137` | **no `[web]` section exists today** |

## 3. UI/UX contract

- **Layout:** slim top bar (app name, repo root, global status cluster) + left nav (views) +
  main canvas. Palette overlays everywhere (Ctrl+K).
- **Home = command center** (palette), not a dashboard (§7.1-2).
- **Status cluster (always visible):** Connection (WS up/down/reconnecting) · Index
  (fresh/never-synced/stale + counts) · Embedder (backend/model/warm, from `embed_ping`) ·
  Daemon (running/stopped/pid/port). Each is a clickable chip → detail panel.
- **Empty/never-synced state:** if `index_status` shows `last_sync == 0` (see issue CORE-1),
  the shell shows activation/onboarding CTA (FR-12) instead of a broken grid.
- **Theme:** sleek modern dark; shadcn/ui + Tailwind + Recharts; tokenized palette (no raw hex).

## 4. API / WS contract

REST (hydrate on load) + WS (live):
- `GET /api/status` → `{root, index: index_status(root), daemon: daemon_status(root),
  embed: {backend, model, dim, warm}, ws: "ok"}` — the one-shot shell payload.
- `GET /api/status/ws` not needed — WS `/ws` pushes `status.{index|daemon|embed|ws}` deltas
  (see SPEC-14 for full contract).
- Static: `GET /` serves the SPA (FastAPI `StaticFiles`, built `dist/`); unknown non-`/api` → SPA index.
- Errors: Pydantic-validated, `{error: {code, message, detail}}`; never HTML.

## 5. Data contract

- Status bar derives from `index_status` + `daemon_status` + embed health. No new tables.
- `schema_version` shown must come from **live DB** `meta` (see CORE-3), not config defaults.

## 6. Backend additions (lib/cipkg in scope)

1. `[web]` config section in `config.default.toml` (`host=localhost`, `port=8090`,
   `auto_manage_daemon=true`) + merged via existing `load_config` (no loader change needed).
2. `base.find_repo_root_or_none(start)` — soft variant of `repo_root` that returns `None`
   instead of `SystemExit`, for the activation/wizard path.
3. Shell status aggregation helper (e.g. `web_bridge.shell_status(root)`) composing
   `index_status` + `daemon_status` + embed ping into one cached payload.

## 7. Core issues / risks (flagged, grounded)

- **CORE-1 — `repo_root()` raises `SystemExit`** (`base.py:72`) on no-`.cip`. The web app must
  never crash on an un-activated path; the shell needs the activation/wizard flow. → backend
  addition 2. *(Logged as new issue in `09-bugs-and-issues.md`.)*
- **CORE-2 — no `[web]` section / port anchor exists** (`config.default.toml` has only `[mcp]`
  and `[daemon]`). Port 8090 must be added and honored by the FastAPI runner. *(backend addition 1.)*
- **CORE-3 — `schema_version` drift** (`config.default.toml` docs claim 11; live DB `meta` = 4,
  per `07-intel-deep-inspection.md` §3.2). The shell must surface the live DB version and flag
  drift rather than printing a config-default value. *(BUG-023 linkage.)*
- **CORE-4 — `index_status` runs 5+ full-table COUNTs every call** (`indexer.py:286-288`),
  unbounded by cache; on large repos this breaks NFR-3 (<300 ms reads). Needs snapshot-based
  caching / invalidation. *(SPEC-14 / snapshot table linkage.)*
- **CORE-5 — `load_config` mutates `sys.path` and imports `repo-settings.detectors`** at call
  time (`base.py:116-124`) — process-wide side effect; only safe on a single-root server.
  Keep root pinned (§7.3 ISSUE-103) and call once at startup, not per-request.

## 8. Acceptance checks (from §6 / §7.5)

- [ ] `cip web` starts one server; console opens at 127.0.0.1:8090 on the **command center**.
- [ ] Status cluster always visible and live; WS reconnect works without reload.
- [ ] Un-activated repo shows onboarding CTA, never a crash or blank grid.
- [ ] Live `schema_version` + drift flag shown; stale config defaults not displayed as truth.
- [ ] No legacy web surface (`web_server`/`dashboard`) serves anything once shell is live.
