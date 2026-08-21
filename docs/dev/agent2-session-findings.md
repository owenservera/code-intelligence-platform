# Agent B (Agent 2 slip) — Session Findings (2026-08-16, pre-autocompaction checkpoint)

**Status:** MERGED into `09-bugs-and-issues.md` §5 as **F-34..F-41** + §7 (legacy removal process) on
2026-08-16 after reboot. Guide `10-research-guide.md` §4/§A/§B/§D struck and annotated. This file kept as
the agent-side checkpoint record only; **do not append new findings here** — use `09` §5.
**F-id mapping (as merged):** PF-38→F-34 (selftest crash), PF-39→F-35 (dependency_checker orphan),
PF-40→F-36 (stack/selftest dead), PF-41→F-37 (dashboard_state dead), PF-42→F-38 (dashboard briefing),
PF-43→F-39 (websocket legacy), PF-44→F-40 (router verified-clean caveat), PF-45→F-41 (F-24 knock-on decision).
**Slip owned:** "Server surface + legacy reuse" (guide §4 Agent 2).

---

## Verified findings

### PF-38 — `cip selftest` crashes: `handle_selftest_command` imports `selftest`, but `selftest.py` only defines `run_selftest`
- **Severity:** P1 · **Area:** tests/cli · **Status:** open
- **Evidence:** `cli.py:250-252` `from .selftest import selftest`; `selftest.py:92` defines only `run_selftest()` (no `selftest` name). Runtime-verified: `handle_selftest_command('.', Namespace())` → `ImportError: cannot import name 'selftest'`. Dispatched at `cli.py:702` + parser `cli.py:569`, so `cip selftest` (documented in AGENTS.md) crashes uncaught. Registry card survives via broad `except` (`command_registry.py:1386-1393`) → error dict.
- **Affects UI:** New console "Run tests" must NOT route through `cip selftest`. Fix = `from .selftest import run_selftest` + `_out({'exit_code': run_selftest()})`.

### PF-39 — `dependency_checker.py` orphaned: real `handle_deps_command` lives there, but cli never imports it → `deps` broken in CLI AND registry
- **Severity:** P2 · **Area:** command center/cli · **Status:** open
- **Evidence:** `dependency_checker.py:137` defines `handle_deps_command(root, args)`; `command_registry.py:1130` does `from .cli import handle_deps_command`, but `cli.py` has **no** such name (runtime-verified ImportError) → `_handle_deps` always errors. `cli.py:618` registers `deps` parser but dispatch `handlers` (`cli.py:669-710`) has no `deps` → "unknown command" (already F-16). `dependency_checker.py` has **zero importers**.
- **Cross-ref:** F-16, CORE-5. **Delta:** the handler exists but was never wired — fix = re-export from cli or add dispatch entry, or delete the module.
- **Affects UI:** Command center `deps` card permanently errors.

### PF-40 — `stack/selftest.py` dead code: `run_stack_selftest` has zero callers
- **Severity:** P3 · **Area:** stack/tests · **Status:** open
- **Evidence:** `stack/selftest.py:122` `run_stack_selftest()`; repo-wide rg finds no callers. Runs a full fixture Next.js+Prisma audit; nothing invokes it.
- **Affects UI:** None; do not expose unless intentionally wired.

### PF-41 — `dashboard_state.py` dead code: zero importers
- **Severity:** P3 · **Area:** web · **Status:** dead (remove)
- **Evidence:** Full read (180 lines). `DashboardState` + `StateUpdater` (30 s polling thread) — **no importer exists** (repo-wide grep). `terminal_dashboard.py:28` has its own unrelated `DashboardState(Enum)`. `StateUpdater._update_state` runs `gapfill.score` + `git` subprocess every 30 s.
- **Affects UI:** None — fresh SPA owns client state. Remove with legacy frontend.

### PF-42 — `dashboard.py` unreachable via CLI (no dispatch entry) but `briefing()` is a reusable oracle signal (CORE-51)
- **Severity:** P2 · **Area:** web/oracle · **Status:** extract-briefing
- **Evidence:** `cli.py:590` registers `dashboard` parser, but dispatch `handlers` (`cli.py:669-710`) has only `dashboard-web` → `cip dashboard` → "unknown command" (part of F-16). `dashboard.py` (122 lines) imports `http.server`, `stack_nextjs`, `stack_prisma`, `stack_impact`; `serve_dashboard` (port 8790) dead. `briefing(root, con)` (`dashboard.py:39-64`) computes refactor/risk/blocker/opportunity notes from `quadrant` + findings + `runtime_adapters.broken` — the CORE-51 oracle input.
- **Cross-ref:** CORE-51, BUG-004, F-16.
- **Affects UI:** Oracle/briefing panel must NOT import `dashboard.py` (pulls in http.server + stack). Extract `briefing()` to a leaf module (e.g. `stack/briefing.py`) taking `(root, con)`; delete the rest.

### PF-43 — `websocket_handler.py` legacy WS protocol: only importer is legacy `web_server.py`; emitter uses `asyncio.create_task` from sync context (unsafe)
- **Severity:** P3 · **Area:** web · **Status:** legacy (protocol reference only)
- **Evidence:** `web_server.py:527,561` imports `DashboardWebSocketServer`; no other importers. `DashboardEventEmitter.emit_*` (`websocket_handler.py:145-183`) call `asyncio.create_task(...)` from sync call sites → `RuntimeError: no running event loop` unless inside the loop; `_running` set but never read. Protocol is sound: `subscribe/unsubscribe/ping/pong/request/response/event` + topic filter with `*` wildcard (lines 52-108).
- **Affects UI:** New console realtime feed (CORE-57) may reuse the subscribe/publish topic protocol as a **model**, but write a fresh emitter on FastAPI WS; do not reuse this module (legacy web removal).

### PF-44 — `router.py` verified WIRED and working, but `route_for_agent`'s `cap:code:*` capability names are an un-consumed contract
- **Severity:** P3 · **Area:** retrieve/command center · **Status:** verified-clean (with caveat)
- **Evidence:** Full read (182 lines). `route` + `route_for_agent` live: `server.py` TOOLS (:30-33) + `call_tool` dispatch (:139-141) + attached to `search` result (:118); `cli.py:205-210` `handle_route_command` (dispatched :687); `predict.py:9` imports router; `selftest.py:81-84` tests it. Runtime-verified: `route("why is this workaround here")→history`, `route("overview of the system")→architecture`. Caveat: `route_for_agent` emits `cap:code:impact/search/graph/...` tool names (`router.py:42-151`) that **no resolver in-repo consumes** — `server.py` TOOLS use bare names (`search`/`symbol`/`impact`); docstring's "Vivim CapabilityResolutionEngine" does not exist in-repo. `_generate_next_ops` also emits `cap:code:*` templates.
- **Affects UI:** If the console surfaces `route_for_agent` suggestions, map `cap:code:*` → real tool names at the bridge. `route()` intent strings (search/symbol/history/health/architecture) are a useful NL-intent classifier worth reusing for the console command/search bar.

### PF-45 — `audit(refresh=True)` silent sub-indexer swallow (F-24 knock-on, Agent 2 item B — decision only)
- **Verdict:** Confirmed `stack/audit.py:17-21` wraps `nextjs.index_routes` + `prisma.index_stack` in bare `try/except Exception: pass` — if either fails, rules query **empty** `routes`/`models` tables and report "clean". **Recommendation:** new bridge must call `nextjs.index_routes` / `prisma.index_stack` as an explicit "prepare stack" step (ISSUE-106) with errors surfaced (failed sub-indexers + traceback), not rely on `audit()`'s silent swallow. Do not route console audit through `audit(refresh=True)` for stack prep.
- **Cross-ref:** F-24, CORE-28, ISSUE-106.

---

## Verified-clean (no finding) — small leaves, item A-4

| Module | Verdict | Evidence |
|---|---|---|
| `parsers.py` (49) | **clean/wired** | `indexer.py:23,382` + `repo_map.py:8`; delegates to `parse.parse_file`; `build_heritage` emits extends/implements edges |
| `tsconfig.py` (71) | **clean/wired** | `indexer.py:19` `TSResolver` (JSONC-aware alias resolver) |
| `lock.py` (33) | **clean/wired** | `indexer.py:406` `WriteLock` (Windows msvcrt + POSIX fcntl, 30 s timeout) |
| `stack/common.py` (41) | **clean/wired** | `ensure()` used by audit/impact/nextjs/prisma/tauri/dashboard (F-24 already verified) |
| `stack/custom_rules.py` (46) | **clean/wired** | `rules.py:553` `get_all_rules`; BUG-016 covers the exec concern |

**Also confirmed live:** `server.py` (264 lines) `call_tool` covers all 20 TOOLS; `route`/`route_for_agent`/`audit`/`findings`/`impact` all dispatch to real lib calls (CORE-9 note: still no 1:1 map for the other 35 registry commands).

---

## Item D status — pytest baseline NOT re-established
- `python -m pytest tests/` was started but **aborted by user** before completion. No delta recorded this session; F-10 (10 failed / 90 passed / 29 errors / 174 s) remains the reference baseline. Do not claim a new baseline.

---

## Legacy frontend removal process (Agent 2 ownership — user request)

All of these are **part of the old frontend → categorically removable**, in favor of the fresh from-scratch console (never ground the new frontend in them).

### Remove-list (with disposition)
| Surface | Disposition |
|---|---|
| `web_server.py` (588) | delete (legacy split-brain web; BUG-001..004, F-21) |
| `static/` (`dashboard.html`, `css/`, `js/`, `lib/`) | delete (BUG-025: no build step, hand-rolled) |
| `dashboard.py` (122) | delete **after extracting `briefing()`** → `stack/briefing.py` (CORE-51) |
| `dashboard_state.py` (180) | delete (PF-41, dead) |
| `websocket_handler.py` (183) | delete (PF-43; reuse only its subscribe/publish topic protocol as a model) |
| `terminal_dashboard.py` (40.8K) | delete (TUI; `bin/cip.py:143` importer) |
| `interactive.py` / `interactive_ui.py` / `help_system.py` / `command_adapter.py` | delete (F-27/F-28/F-29/F-26 dead cluster) |
| `server.py` HTTP `serve()` | deprecate HTTP JSON-RPC; **keep** `mcp_stdio()` if MCP agent surface is retained |
| `dependency_checker.py` | delete **or** wire `handle_deps_command` into cli (PF-39) |
| `stack/selftest.py` | delete **or** wire `run_stack_selftest` (PF-40) |
| legacy tests: `tests/terminal_dashboard/` + root `conftest.py` Textual coupling | delete; remove Textual import requirement (F-10) |

### Suggested removal process (merge into `09` after autocompaction)
1. **Freeze:** stop extending any file in the remove-list; add `## LEGACY — DO NOT REUSE` header comments as they get touched.
2. **Extract-first:** move `briefing()` (CORE-51) and the WS topic protocol (CORE-57) into leaf modules *before* deleting their hosts.
3. **Remove in dependency order:** leaves first (dead cluster F-26..F-29), then TUI (`terminal_dashboard.py`), then HTTP servers (`dashboard.py` serve, `web_server.py`), then `static/` assets last.
4. **Chip away CLI/registry references in the same commit as each removal** (`dashboard`/`dashboard-web` parsers `cli.py:590-593`, dispatch `cli.py:709`, registry cards `command_registry.py:480,847`); else `cip X` silently returns "unknown command".
5. **Delete legacy tests + root-conftest Textual coupling** so backend tests run without `textual` (F-10).
6. **Keep `mcp_stdio()`** (MCP stdio for agent integration) unless the bridge replaces it; do NOT keep HTTP JSON-RPC `serve()`.
7. **Verify:** re-run `python -m pytest tests/` for the baseline delta (F-10) and `python -m pyflakes lib/cipkg` after deletions.

---

## End-of-pass status
- Items completed: A-1 (router), A-2 (websocket_handler), A-3 (dashboard_state + dashboard), A-4 (all small leaves), B (F-24 knock-on decision), NEW legacy-removal process.
- Items NOT completed: D (pytest baseline — aborted).
- **MERGED:** F-34..F-41 + §7 appended to `09` §5; guide checklist struck (A-1/A-2/A-3/A-4/B) + D annotated aborted; `09` header + §6 merge-notes + guide status updated. All post-reboot edits verified.
- Provisional F-ids PF-38..PF-45 → merged as **F-34..F-41** (Agent 1 owned F-31..F-33).
