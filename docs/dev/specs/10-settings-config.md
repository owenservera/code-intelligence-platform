# SPEC-10 — Settings & Config (FR-10 + FR-15)

- **Requirement source:** `05-requirements.md` §2 FR-10, §2 FR-15, §7.1(13)(14), ISSUE-104/110
- **Grounding verified:** 2026-08-15 against `lib/cipkg/base.py`, `config.default.toml`
- **Build order dependency:** SPEC-01 (settings entry), SPEC-02 (reload/jobs), SPEC-04 (index configs).

---

## 1. Goal & owner intent

Full config **write-back** (§7.1-14 — FR-10's "write-later" is now write-now): view AND edit
supported sections (index, embed, retrieval, memory, audit, maintain, git, perf, summary, rerank,
vector, daemon, mcp, logging, ui, web), save to `.cip/config.toml` with reload notice, versioned
schema. Settings is a first-class surface: edit + save + validate + diff + reload + per-section
source (default/TOML/profile override). Also the **"run any CIP capability"** surface (FR-15)
converges here (SPEC-02 command table).

## 2. Truth-grounded core surface (verified 2026-08-15)

| Need | Core call (verified) | Returns |
|---|---|---|
| Effective config | `base.load_config(root)` `base.py:109` | deep-merged dict: hardcoded DEFAULT_CONFIG → TOML defaults → repo profile → `.cip/config.toml` overrides |
| Hardcoded defaults | `DEFAULT_CONFIG` `base.py:40-59` | `index{max_file_kb:512, exclude:[], test_globs:[...]}`, embed, retrieval, serve, summary, git, rerank, vector, perf, maintain, profile |
| TOML defaults | `_load_default_toml()` `base.py:12` | merges `config.default.toml` + `config.v2.default.toml` |
| Repo profile | `repo-settings/detectors.detect_repo_type/load_repo_profile` `base.py:122-124` | profile merge incl. include/exclude flatten to index |
| Local overrides | `.cip/config.toml` via `tomllib` (`base.py:149-160`) | repo-local config |
| Config file path | `.cip/config.toml` (`base.py:149`) | the write target |
| File iteration | `iter_files(root, cfg)` `base.py:169` | reads `cfg["index"]["max_file_kb"]`, `cfg["index"]["exclude"]`, `cfg["index"]["include"]`, `cfg["index"]["test_globs"]` |
| Effective sections | `config.default.toml` | `[meta] [index] [embed] [retrieval] [memory] [mcp] [daemon] [analysis] [logging] [performance] [ui] [summary] [git] [rerank] [vector] [perf] [maintain] [audit]` |

**Config anchors consumed by core functions (verified):**
- `index.max_file_kb`, `index.exclude`, `index.include`, `index.test_globs` (`base.py:173-213`)
- `embed.backend/model/dim/service_port/autostart` (`embed.py`)
- `retrieval.lexical_k/vector_k/context_budget_tokens` (`retrieve.py:172-173,291`)
- `maintain.event_days` (`maintain.py:39`)
- `git.depth/co_change_min` (`gitindex.py:8`)
- `perf.workers` (`indexer` parallel)
- `audit.ignore_rules`, `audit.custom_rules_path` (rules.py)

## 3. UI/UX contract

- **Settings view** (`/settings`): sectioned editor grouped by category (Index / Embedding /
  Retrieval / Memory / Audit / Git / Perf / Daemon / Web). Each key = labeled input with:
  type-aware control (int/float/bool/string/list-of-strings), current effective value, **source
  badge** (default / config.toml / profile), and description.
- **Write-back flow (FR-10 write-now):** Edit → Validate (type + range checks server-side) →
  **Diff preview** (current file vs proposed) → Save writes `.cip/config.toml` → Reload notice →
  affected subsystems get a SPEC-02 "reload config" job (re-derive iter_files/embedder/etc.).
- **Reset:** per-key "restore default" (removes override) and per-section reset.
- **Config diff view:** effective vs file vs defaults (three-way) for transparency.
- **Web/web-managed settings:** `[web]` section (CORE-1) added on first save (port, host, theme,
  autostart daemon, snapshot retention).
- **FR-15 "run anything"** entry: command table (SPEC-02) + a "run with args" form; this view is
  the control surface root for advanced users.
- **States:** unsaved-changes guard; validation errors inline; reload shows which modules
  re-initialized; write failure (permissions/TOML invalid) → error with original file preserved.

## 4. API / WS contract

REST:
- `GET /api/config` → `{effective, file, defaults, sources}` (per-key source provenance).
- `GET /api/config/schema` → type/range/default per key (drives the form; server is source of
  truth — avoids duplicating TOML knowledge in React).
- `POST /api/config/validate` `{updates:{section:{key:value}}}` → `{ok, errors[]}` (no write).
- `POST /api/config/save` `{updates}` → `{ok, written_keys, diff}` (writes `.cip/config.toml`;
  backup `.cip/config.toml.bak` before overwrite).
- `POST /api/config/reset` `{section?|key?}` → removes override(s).
- `POST /api/config/reload` → SPEC-02 job (re-init affected subsystems); WS `config.reloaded`.

WS (`/ws`, SPEC-14): `config.reloaded {sections}` after reload job; `config.written` broadcast
(single-writer console, but other agents may edit file — watch `.cip/config.toml` mtime).

## 5. Data contract

- Write target: `.cip/config.toml` (existing TOML, `tomllib`-parsed on load). Bridge writes
  TOML preserving comments where feasible (tomlkit or ordered serialize + comment header).
- No DB tables. Reload bookkeeping in-memory (bridge).
- `[web]` section (CORE-1) introduced by this spec — the one new config key set.

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge.config_schema()`** — introspects `DEFAULT_CONFIG` + `config.default.toml` into a
  per-key schema (type, default, range/choices from code paths) → drives the settings form.
2. **`web_bridge.config_write(updates)`** — validate types → merge into `.cip/config.toml`
  (tomlkit, preserve comments) → atomic write + `.bak` → return diff.
3. **`web_bridge.config_reload(root)`** — job that re-runs `load_config`, clears caches
  (embedder, stats, snapshot cache), emits `config.reloaded`; hot-applies safe keys
  (retrieval.k, maintain.event_days, audit ignore_rules); flags full-restart keys (embed backend,
  daemon ports) with notice.
4. **Config file watcher** — mtime watch on `.cip/config.toml` → refresh `GET /api/config`
  cache + `config.written` event (external edits visible live).

## 7. Core issues / risks (flagged, grounded)

- **CORE-39 — config key mismatch: `config.default.toml` uses `[index] exclude_patterns` and
  `max_file_size` (bytes), but core reads `cfg["index"]["exclude"]` and `max_file_kb`.**
  `config.default.toml:10/28` vs `base.py:42-43,173-174`. The TOML exclude list and size cap are
  **silently ignored** — only the hardcoded `DEFAULT_CONFIG` fallback (512 KB, empty excludes)
  applies. → Indexer excludes nothing beyond `.git/.cip` unless users hand-edit `exclude`
  (undocumented key). This spec's schema/validation must expose the **real** keys and reconcile
  (or the bridge must map `exclude_patterns→exclude`, `max_file_size→max_file_kb`). *(New issue.)*
- **CORE-40 — `[meta] schema_version = 11` (config.default.toml:6) vs live DB
  `schema_version=4` (CORE-3).** Config claims v11; store is v4 (`store.py:5`). The settings view
  must not trust `meta.schema_version` from config; show the live DB version + offer the schema
  upgrade action (SPEC-04). *(Reaffirms CORE-3.)*
- **CORE-41 — `load_config` repo-profile auto-detect imports `repo-settings/detectors` and can
  silently fail** (`base.py:114-146` bare `except: pass`) — a broken profile silently falls back,
  hiding intended includes/excludes. → Settings view shows profile source + errors if detection
  fails. *(New issue.)*
- **CORE-42 — `[ui]`/`[logging]`/`[performance]`/`[analysis]` sections exist in
  `config.default.toml` but core reads legacy key names (`health_weights` vs analysis weights;
  `[perf] workers` vs `[performance] worker_threads`).** Two overlapping perf configs
  (`[performance]` and `[perf]`) — which wins is ambiguous. → Schema must reconcile duplicates
  and mark legacy keys deprecated in the UI. *(New issue.)*
- **Watch: `serve.port:8787` (hardcoded, `base.py:47`) is not in `config.default.toml` and
  collides with `embed.service_port=8787`** (CORE-10/11 family). Web's own port must live in
  `[web] port` (NFR-1) to avoid clash.
- **Watch: writing `.cip/config.toml` while daemon/indexer is running** → reload job must run
  under the same single-writer discipline (SPEC-04 lock); config file itself is not DB-locked.

## 8. Acceptance checks (from §6 / §7.5)

- [ ] Settings form driven by `config_schema()` (real keys, correct types); source badges shown.
- [ ] Edit → validate → diff → save writes `.cip/config.toml` (+.bak), reload job re-inits
  affected subsystems, WS `config.reloaded` fires.
- [ ] FR-15 "run anything": command table + args form execute via SPEC-02 dispatch.
- [ ] CORE-39 resolved: exclude/size keys work as documented (map or rename), validated live.
- [ ] CORE-40 handled: live DB schema version shown, not config meta; upgrade action offered.
- [ ] External config edits reflected live via watcher (config.written).
