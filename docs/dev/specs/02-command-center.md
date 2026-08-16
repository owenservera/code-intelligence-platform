# SPEC-02 — Command Center (FR-2)

- **Requirement source:** `05-requirements.md` §2 FR-2, §7.1(1)(2)(4), §7.4, §7.5
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{command_registry,cli,server,intelligent_executor}.py` + live registry dump
- **Build order dependency:** SPEC-01 (shell) — the center mounts in the shell; SPEC-14 (realtime/job model) defines the WS events it emits.

---

## 1. Goal & owner intent

The **home screen** is a command center: full 54+ command surface (the entire registry) reachable
via palette (Ctrl+K) with fuzzy search, auto-generated parameter forms, one-click execution,
live progress/logs/structured results, job history, and re-run. "Every capability CIP has should
be executable from the frontend" (§7.1-4). Zero friction, no dead buttons (§7.1-4, §6).

## 2. Truth-grounded core surface (verified 2026-08-15)

### 2.1 Registry = metadata source of truth (verified live)
- `get_command_registry()` (`command_registry.py:1399`) → `CommandRegistry` singleton.
- Live dump: **55 commands, 11 categories**
  `REPOSITORY 6, SERVICES 5, SEARCH 6, QUALITY 5, REFACTORING 5, GAPFILLERS 7, GIT 4,
  INTEGRATION 5, AGENT 6, LEARNING 4, SYSTEM 2`.
- `CommandCard` (`command_registry.py:50`): `command, icon, label, description, category,
  priority, handler, parameters[], has_form, long_running, requires_confirmation, metadata`.
- `CommandParameter` (`command_registry.py:38`): `name, type, description, required, default,
  choices, flag` — **this is the form schema source.**
- `CommandPriority` (`command_registry.py:29`): critical/high/medium/low (palette ordering).

### 2.2 Registry handlers are NOT a safe execution path (verified — critical)
Programmatic audit of all 55 `_handle_*` methods' `from .cli import X` targets:
- **Fixed (Ph1, 2026-08-16):** all 14 previously-missing CLI handlers (`gate, refactors,
  dead, circular, deps, coverage, migrations, env, logs, metrics, features, api, blame,
  predict`) now exist in `cli.py` and are wired into `dispatch_command`. Six additional
  handlers were added (`routes, models, admission, score, embedder, embed-ping`). Only
  `dashboard` (legacy TUI) remains unwired — deletion target for the new frontend.
- **Fixed (Ph1, 2026-08-16):** `handle_analyze_command(root)` and
  `handle_rebuild_command(root)` arity aligned to `(root, args)` — no more TypeError on
  dispatch.
- **Handlers print, don't return:** CLI handlers call `_out(...)` (`cli.py:14`, `json.dumps(...)`
  + `print`), so the underlying value is lost to the caller. Not structured-result friendly.

**Consequence:** the web bridge must **catalog from the registry but dispatch via its own
command→callable table** (mirroring `server.py:call_tool`), never via `card.handler()`.

### 2.3 The correct dispatch model already exists — `server.py:call_tool`
- `call_tool(root, cfg, name, args)` (`server.py:112`) → direct lib dispatch, envelope
  `{ok, tool, result, next_ops, index:{fresh,lag_s,files}}`, try/except with error string.
- Covers only the **20 RPC tools** (`server.py:15-50` TOOLS) — a subset of the registry.
- `_next_ops(name, res)` (`server.py:80`) suggests follow-up commands (agent-native chaining) —
  great "re-run/related" fuel for the command center.
- **Action:** extend this dispatch table to all 55 registry commands, returning structured
  dicts (see §4).

### 2.4 Job/progress primitives available in core
- `indexer.sync(root, full, do_embed, progress)` (`indexer.py:290`) — `progress(phase, cur,
  total)` phases `scan/link/embed`; **the WS progress stream source.** Returns stats dict.
- `intelligent_executor.py` — `ExecutionStatus` enum (`:18`), `ExecutionContext` (`:29`),
  `ExecutionResult` (`:44`), `ProgressUpdate` (`:57`), `IntelligentCommandExecutor.execute_command`
  (`:160`) with precondition/adaptation/recovery + learning hooks. **Heavy/experimental; not the
  job engine to build on directly**, but its dataclasses are a useful naming reference. Note its
  execution still calls `card.handler(...)` (`:210`) → inherits the broken handlers in §2.2.
- `command_adapter.py` `ContextAwareCommand.execute` (`:374`) — context-aware adaptation layer;
  optional; treat as out of scope for v1 execution (metadata only).
- `cli.py` argparse surface (the true parameter authority, `03-cli-and-registry.md` §3) — the
  registry `CommandParameter` list is incomplete vs argparse (e.g. `--host`, `--refresh`).
  **Merge step:** registry params + argparse flags → single form schema.

## 3. UI/UX contract

- **Palette (Ctrl+K, global):** fuzzy search over `label`+`description`+`command`; grouped by
  category; priority-sorted within group; keyboard navigation; recent commands first.
- **Command detail:** selected command → auto-generated form from `CommandParameter[]` +
  argparse extras. Field types map: str→text, int→number, float→number, bool→toggle,
  choices→select, list→tag input.
- **Execute → Job:** confirm toggle if `requires_confirmation` or destructive (rebuild, vacuum,
  export overwrite, upgrade). Returns job id; runs in background worker; WS streams
  `job.progress` (phase/cur/total) + `job.log` (line-by-line) + `job.done|job.error`.
- **Result panel:** live log + pretty structured result (JSON tree) + `next_ops` as re-run/
  drill-down buttons; **no dead buttons** — every suggested op maps to a real command.
- **Job history:** recent jobs (id, command, status, duration, result summary, exit), re-run,
  cancel running.
- **States:** idle → running → success/error/cancelled; error shows full traceback (NFR-5).

## 4. API / WS contract

REST:
- `GET /api/commands` → registry catalog: `{categories:[{name, commands:[CommandCard-serialized]}]}`
  with merged argparse params (server-side build, cached).
- `GET /api/commands/{name}` → one card + param schema.
- `POST /api/commands/{name}/run` → `{job_id}` (202) or `{error}`; body = validated params.
- `GET /api/jobs` / `GET /api/jobs/{id}` → job states (SPEC-14 owns the full Job model).
- `POST /api/jobs/{id}/cancel` → cancel a running worker job.

WS (`/ws`, SPEC-14):
- `job.start {id, command}` · `job.progress {id, phase, current, total, pct}` ·
  `job.log {id, line}` · `job.done {id, result}` · `job.error {id, traceback}` ·
  `job.cancelled {id}` · `job.removed {id}` (history prune).

## 5. Data contract

- Catalog: in-memory, built once from registry + argparse (no table).
- Jobs: in-memory `JobRegistry` (id, command, params, status, progress, logs[], result,
  traceback, started/finished, exit) — **ephemeral**, pruned on retention (e.g. 200 jobs).
- Events: each completed command writes a typed row to `events` table (SPEC-14/C4 activity feed).

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge.command_table`** — extended `server.py:call_tool`-style map for all 55
   commands → (callable, param schema, return-normalizer). Uses lib functions directly, never
   registry handlers, never subprocess, never `print`.
2. **Param schema merger** — registry `CommandParameter` ⊕ argparse flags → canonical JSON Schema
   (type, required, default, enum, description) per command.
3. **Job runner** — background `ThreadPoolExecutor`-based runner honoring SQLite single-writer
   (§4 data-and-state §9); long commands use lib `progress` callbacks → WS; stdout capture via
   `io.StringIO`/`redirect_stdout` for lib paths that `print` (audit, sync stats).
4. **`events` writer** — typed event per job completion (kind, command, duration, status, summary).

## 7. Core issues / risks (flagged, grounded)

- **CORE-5 — 14 registry handlers import nonexistent CLI functions** (verified 2026-08-15;
  `gate/refactors/dead/circular/deps/coverage/migrations/env/logs/metrics/features/api/blame/predict`).
  If the console routed through `card.handler`, these commands would always show
  `{'error': ...}`. → bridge must own dispatch (§2.2, addition 1). *(New issue logged.)*
- **CORE-6 — Registry handlers swallow all exceptions into error dicts** (`command_registry.py:899`
  pattern `except Exception as e: return {'error': ...}`). Kills NFR-5 traceback visibility.
  → bridge rethrows/structures errors properly. *(New issue.)*
- **CORE-7 — CLI handlers `_out()`-print and return `None`** (`cli.py:14-15`) — the actual lib
  result is discarded. Registry wraps these, so structured results are lost. → bridge calls lib
  directly and serializes results. *(New issue.)*
- **CORE-8 — `CommandParameter` metadata is incomplete vs argparse** (no `--host`, `--refresh`,
  `--structured` etc. on many cards) → auto-forms would silently omit real flags. → merge step
  (addition 2) is mandatory, not nice-to-have. *(New issue.)*
- **CORE-9 — no 1:1 command↔lib mapping exists anywhere** (`server.py` covers only 20 of 55).
  The gap means "every command executable" is unverifiable until the table exists. → acceptance
  check: every catalog entry has a non-stub callable. *(New issue.)*
- **Watch:** `indexer.sync` progress is real; but `_ensure_embedded`/embed auto-start can block
  (BUG-010) and full sync ≈18 min on this repo (07-intel §3.2) → sync MUST be a job with
  progress + ETA + cancel, never in-request.

## 8. Acceptance checks (from §6 / §7.5)

- [ ] All 55 catalog entries render in palette with a working auto-form.
- [ ] Every catalog command executes and returns a structured result (or a clear error +
      traceback) — none route through broken registry handlers.
- [ ] Long commands stream progress + logs over WS; job appears in history; re-run works.
- [ ] Destructive commands require explicit confirmation toggle.
- [ ] `next_ops` suggestions are live buttons mapping to real commands (no dead buttons).
- [ ] `events` rows written per job; activity feed (C4) has data.
