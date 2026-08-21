# Research Guide Index — where to investigate next

**Status:** LIVE reference list for backend deep-dive sessions. **Two parallel work slips (Agent 1 + Agent 2)
defined in §4 — every remaining deep-dive item is assigned; §C stays design-side/unassigned.**
**Agent 2 slip (2026-08-16): COMPLETE except item D (pytest baseline — aborted by user, retry later).**
**Purpose:** A simple, lossless checklist of investigation areas, ranked by expected value, grounded in
`docs/dev/09-bugs-and-issues.md` as of 2026-08-16 (F-34..F-41 appended by Agent 2, F-42 = F-22 root cause by Agent 1, F-42B = test baseline by Agent 2, last id F-42B).
**Rule:** When a pass produces findings, append to `09-bugs-and-issues.md` (F-ids continue from F-43; user
coordinates F-id allocation between the two agents) and strike the item here.

---

## 0. What we are doing and why (read this first)

- **The project:** CIP (`lib/cipkg/`) is a code-intelligence platform (semantic search, impact analysis,
  quality audit, agent memory). A brand-new web console is being designed from scratch
  (`docs/dev/05-requirements.md`, `07-api-design.md`, `specs/`).
- **This research = risk discovery for that build.** Every new console screen will call into `lib/cipkg`
  functions. If those functions are broken, dead, or silently wrong, the console will look broken no matter
  how good the frontend is. So the design work depends on knowing **what the core actually does**, not what
  the docs claim.
- **Two kinds of output:**
  1. **Findings** → appended to `docs/dev/09-bugs-and-issues.md` (the single living log; evidence + severity +
     "Affects UI" consequence). This is what drives design decisions.
  2. **Coverage notes** → recorded here (checklist items checked off, "verified clean" annotations). This is
     how we prove we actually looked, so a future session doesn't re-read the same files.
- **Why lossless matters:** sessions are long and can be auto-compacted or interrupted. The docs are the only
  memory that survives. Anything worth knowing must be written down before the session ends — never trust a
  mental summary.

## 1. How to proceed (per-pass workflow)

1. **Open this guide and `09-bugs-and-issues.md`.** Confirm the last F-id (currently F-41) and read the §6
   merge-notes for the latest coverage state — they are the ground truth of what's already been done.
2. **Pick ONE area** from sections A–C below. Finish it before starting another. Do not bounce between areas.
3. **Read the target module(s) fully** (not grep-skims): note imports, public functions, who calls them, and
   any docstrings claiming features (e.g. "SCIP integration") that need wiring evidence.
4. **Verify behavior at runtime** where cheap:
   - small `python -c` / temp-script probes against the live DB (read-only; or an in-memory copy via
     `sqlite3.Connection.backup`),
   - `python -m pyflakes lib/cipkg` for undefined/unused names,
   - the rules dry-run harness (in-memory DB + `run_rules`) after any rules/indexer change.
5. **Ground every candidate finding against `09` first** — if an entry already covers it (same file+issue),
   skip it or add only the *delta* as a `Cross-ref:`.
6. **Write findings BEFORE moving on** (see §3). Then check off / annotate this guide and commit to the
   checklist item being resolved.
7. **End-of-pass:** update §6 merge-notes in `09` (new F-ids, files read, scope decisions), update this
   guide's status line, and note the next recommended area.

## 2. Where to log findings

- **Primary log:** `docs/dev/09-bugs-and-issues.md` — the ONLY place new findings are appended.
  - §1 = BUG-xxx (web/deep-inspection), §4 = CORE-xxx (spec-driven), §5 = F-xx (backend deep-dive, live).
  - New backend findings go in **§5** with the next stable F-id (continue from F-43).
  - Each entry: `Severity` (P0/P1/P2/P3), `Area`, `Status`, `Evidence` (file:line + verification method),
    `Cross-ref:` if it overlaps a BUG-/CORE- entry, `Affects UI` (the console consequence).
- **Superseded / do-not-use:** `cip-findings.md` (repo root) and `cip-inntel.md` — history only. Never append
  new F-entries there.
- **Checklist:** this guide (`10-research-guide.md`) — for coverage tracking, not findings.
- **Harnesses/scripts:** keep under the OS temp dir or a scratch folder, not in the repo, unless they're
  genuinely reusable test utilities.

## 3. Cadence — how frequently to write things down

- **Hard rule — persist before you lose it:** any discovery that (a) would change a design decision, (b) is a
  P1/P2 bug, or (c) took effort to verify MUST be written into `09` immediately, in the same pass, before
  starting the next module. Auto-compaction and interruption can happen at any time — do not accumulate a
  mental backlog.
- **Small/trivial items:** batch them at the end of a pass, but same session.
- **End of every session:** the `09` merge-notes + this guide's status line are updated as the last act.
- **Checklist hygiene:** strike an item here the moment its module is read (with a one-line verdict), so the
  checklist stays an accurate mirror of reality rather than an optimistic to-do.

---

## 4. Parallel work slips — split of ALL remaining deep-dive work (2026-08-16)

The remaining deep-dive work below is split into **two non-overlapping slips**. Run the two agents in
parallel. Each agent OWNS every item on its slip; no shared files, no shared findings. If a slip finishes
early, the agent re-verifies its own items — it does not reach into the other agent's list.

Both agents follow §1 workflow and §3 cadence. Findings still append to `09-bugs-and-issues.md` §5 — the
user coordinates F-id allocation between the two agents to avoid collisions. Every item struck here must
carry its F-id verdict.

### Agent 1 slip — "Core + data correctness" (owns the highest-priority active bugs)

1. **A:** `session.py` (193) — `learning.update_prediction_confidence` wiring (F-08/CORE-53 relevance).
2. **A:** `runtime_adapters.py` (90) — `broken()` used by `audit.gate()` and the `broken` tool.
3. **A:** `watcher.py` (111) — separate impl from `watch.py`; CORE-16/57 loop claims.
4. **A:** `repo_map.py` (102) + `rerank.py` (35) + `vecstore.py` (33) + `scip_indexer.py` (159) —
   AGENTS.md claims SCIP + repo-map + rerank; NO wiring evidence. High-value verification.
5. **B:** F-22 import-resolution root cause (prefix-aware resolver; confirm `all_paths` at `indexer.py:380`)
   then re-run the resolution simulation — target >90%. Then F-23 tested_by re-verify (BUG-007 edge
   direction).
6. **D:** `python -m pyflakes lib/cipkg` re-check (F-01/F-03/F-09) + rules dry-run harness after any
   rules/indexer change.

### Agent 2 slip — "Server surface + legacy reuse" (read-only where legacy)

**Status (2026-08-16, end-of-pass): COMPLETE except item D (pytest — aborted by user, retry later).**
A-1 router (F-40 verified clean + cap:code caveat), A-2 websocket_handler (F-39 legacy protocol model),
A-3 dashboard_state + dashboard (F-37 dead / F-38 briefing-extract for CORE-51), A-4 small leaves (F-35
dependency_checker orphan, F-36 stack/selftest dead; rest verified clean), B F-24 knock-on (F-41 decision:
explicit "prepare stack" step). Legacy-frontend removal process documented in `09` (Agent 2 ownership).

1. **A:** `router.py` (179) — feeds `server.py` route/route_for_agent (CORE-9).
2. **A:** `websocket_handler.py` (178) — legacy; out of scope for the new web, read only for WS protocol reuse.
3. **A:** `dashboard_state.py` (175) + `dashboard.py` (114) — legacy TUI/state; skim for CORE-51 (briefing).
4. **A:** small leaves — `parsers.py`, `tsconfig.py`, `dependency_checker.py`, `lock.py`,
   `stack/selftest.py`, `stack/common.py`, `stack/custom_rules.py` (confirm reachability + no dead code).
5. **B:** F-24 knock-on — `audit(refresh=True)`'s `nextjs.index_routes` / `prisma.index_stack` silent
   error swallow (`audit.py:17-21`); decide surface-errors vs explicit "prepare stack" job (ISSUE-106).
6. **D:** `python -m pytest tests/` — re-establish the 10 failed/29 errors baseline (F-03, F-10); do NOT
   attempt fixes, just record the delta vs baseline.

**Unassigned (deliberately):** §C CORE-xx spec-gap entries stay open for the design-side agent / bridge
decisions — not deep-dive work, do not pick them up.

---

## A. Unread backend modules (F-25 baseline — merge-note "complete" claim was false)

These have **zero** report mentions / evidence lines. Read them, note what they wire into, and either file
findings or mark "verified clean."

- [ ] `stack/rules.py` — DONE (F-24) ✅ — but re-read is required for any rule change
- [x] `command_adapter.py` (475 lines) — DONE (F-26): fully dead code; `_execute_original` placeholder fakes
      success without executing; imported only by `interactive.py`; `adapt_command`/`get_adaptation_info` have
      zero callers. NOT the CORE-5/F-16 bridge the checklist assumed.
- [x] `interactive.py` (325 lines) + `interactive_ui.py` (691) — DONE (F-27/F-28): whole interactive cluster
      unreachable — zero importers, no `cip interactive` subcommand, yet help advertises it; `interactive_ui.py`
      content not read, but reachable only from dead `interactive.py` (F-28).
- [x] `help_system.py` (247 lines) — DONE (F-29): dead (only importer is dead `interactive.py`) AND broken —
      `display_help` crashes on None `index_status` (`:104`), `display_suggestions` hits F-20 (`:223`),
      `_get_base_help` is a literal placeholder, and it advertises `cip help`/`workflow`/`suggest`/`--classic`
      which don't exist.
- [x] `hooks.py` (173 lines) — DONE (F-30): post_edit_hook reads `callers`/`callees`/`risk_score`/`summary`
      keys that `stack/impact.impact()` never returns → always-zero impact summary; `" callees"` typo key;
      root dropped through `handle_hook_command`/`run_hook_command`. audit half works. Reachable (unlike
      the F-26..F-29 dead cluster) via `cip hook post-edit|pre-edit`.
- [x] `session.py` (199 lines, guide said 193) — DONE (F-31) → **was [A1]**: wired+reachable (`cip session start/end/status`), but `session_start` context packet silently empty — `retrieve.runtime_adapters` doesn't exist (`:48,:182`, correct target `runtime_adapters.broken` works), `architecture` reads keys `map_()` never returns (`subsystems/total_files/overview` vs actual `totals.files`). `update_prediction_confidence` + `verify` halves work.
- [x] `router.py` (182 lines — guide said 179) — DONE (F-40) → **was [A2]**: verified WIRED + working
      (`server.py` TOOLS :30-33 + call_tool :139-141 + search-result attach :118; `cli.py:205-210`
      handle_route_command; `predict.py:9`; `selftest.py:81-84`); runtime-verified route → history/architecture.
      Caveat: `route_for_agent` emits `cap:code:*` tool names no in-repo resolver consumes (server TOOLS use
      bare names); `route()` intent strings are a reusable NL classifier for the console search bar.
- [x] `runtime_adapters.py` (99 lines) — VERIFIED CLEAN → **was [A1]**: `ingest()`/`ingest_vitest`/`ingest_tsc`/`broken()` all work end-to-end on a temp DB (schema auto-created by CORE_SCHEMA); correctly wired in `cli.py` (`broken` parser :547 + dispatch :684), `stack/audit.py:183`, `verify.py:6`, `server.py:133`, `dashboard.py`, `selftest.py`. Only bug is the F-31 consumer path (`session.py` uses `retrieve.runtime_adapters`). `audit.gate()` verified correct statically (runtime requires embed model — skipped).
- [x] `watcher.py` (114 lines, guide said 111) — DONE (F-32) → **was [A1]**: watchdog-based impl is dead (zero
      importers) AND broken if wired (`indexer.mark_for_reindex` doesn't exist; only `embed_pending`). The
      ACTIVE watcher is `watch.py` (zero-dep mtime polling) used by `daemon.py:154` — CORE-16/57 claims are
      satisfied by that, not this file. Cleanup candidate.
- [x] `websocket_handler.py` (183 lines — guide said 178) — DONE (F-39) → **was [A2]**: only importer is
      legacy `web_server.py:527,561`; emitter uses `asyncio.create_task` from sync context (unsafe unless
      inside loop); `_running` set but never read. Protocol (subscribe/publish/ping/pong/event + `*` wildcard,
      lines 52-108) is sound — reuse as a MODEL for the console realtime feed (CORE-57), fresh emitter on
      FastAPI WS. Legacy web removal.
- [x] `dashboard_state.py` (180 lines — guide said 175) + `dashboard.py` (122 — guide said 114) — DONE
      (F-37/F-38) → **was [A2]**: `dashboard_state.py` zero importers (dead, remove). `dashboard.py`
      unreachable via CLI (`dashboard` parser at `cli.py:590` but dispatch has only `dashboard-web` → unknown
      command); `serve_dashboard` (8790) dead; **`briefing(root, con)` (`:39-64`) is the CORE-51 oracle input —
      extract to `stack/briefing.py` (leaf), delete the rest.**
- [x] `repo_map.py` (107), `rerank.py` (37), `vecstore.py` (37), `scip_indexer.py` (162) — DONE (F-33) →
      **was [A1]**: `repo_map.py` + `scip_indexer.py` DEAD (zero importers, no CLI; AGENTS.md SCIP/repo-map
      claims unsupported; scip_indexer also broken-if-wired). `rerank.py` + `vecstore.py` LIVE + verified
      working at runtime (retrieve.py imports/calls both).
- [x] `parsers.py`, `tsconfig.py`, `dependency_checker.py`, `lock.py`, `stack/selftest.py`,
      `stack/common.py`, `stack/custom_rules.py` — small leaf modules → **was [A2]**: **verified clean/wired:**
      `parsers.py` (49, `indexer.py:23,382` + `repo_map.py:8`), `tsconfig.py` (71, `indexer.py:19` TSResolver),
      `lock.py` (33, `indexer.py:406` WriteLock), `stack/common.py` (41, `ensure()` used by audit/impact/
      nextjs/prisma/tauri), `stack/custom_rules.py` (46, `rules.py:553`; BUG-016 covers exec concern).
      **Findings:** `dependency_checker.py` orphaned (real `handle_deps_command` at :137 never imported by
      cli → F-35); `stack/selftest.py` `run_stack_selftest` (:122) zero callers (F-36).

## B. Root-cause follow-ups — resolved / superseded

- [x] **F-22 import resolution — root cause identified and simulated fix verified (F-42)**: the bug is NOT a stale `all_paths` (that set is complete). The `resolve_import` relative branch (`indexer.py:42-46`) uses `os.path.join(dirname, spec)` which keeps `.base`/`..base` as literal segments → relative imports can NEVER resolve (0/2143). Fix verified in simulation: strip leading dots + count levels → relative 72.7%, total 43.7% (remaining failures are stdlib 2117 + 3rd-party ~1004 externals, genuinely unresolvable to repo files). **Action:** apply the relative-branch fix + add `lib/`/`src/` prefix for absolute in-repo imports → total 43.7% of imports resolvable in-repo; remaining ~56% are stdlib/external which is expected-empty. Target: 100% of in-repo imports resolvable.

- [x] **F-23 tested_by — superseded by F-42**: `tested_by` edges now exist (4462) but are mostly noise: src symbols come from `sync_global/backups/*` (backup copies of the repo that are 76% of the index), dst = `lib/cipkg/test_embed.py` matches via name-mention heuristic on test chunks. The name-mention heuristic (:234-239 in `indexer.py`) produces spurious edges — `build_tested_by` should first resolve imports via fixed resolver and stop raw substring matching against chunk text. BUG-007 edge-direction still relevant as a secondary concern.

- [x] **F-24 knock-on — decided (F-41)**: confirmed `audit(refresh=True)`'s `nextjs.index_routes` / `prisma.index_stack` swallow errors (`audit.py:17-21`) → rules silently query empty tables and report "clean". **Decision (F-41, [A2]):** new bridge calls `nextjs.index_routes`/`prisma.index_stack` as an explicit "prepare stack" step (ISSUE-106) with errors surfaced; never route console audit through `audit(refresh=True)` for stack prep.

## C. Spec-gap entries still open in §4 (CORE-) — pick by feature priority

- [ ] CORE-3 / ISSUE-107 — stats COUNTs caching + snapshot table contract (affects every dashboard read)
- [ ] CORE-5 / F-16 / F-17 — command-center dispatch table (bridge owns dispatch; 21 CLI cmds + 14 registry
      cards broken)
- [ ] CORE-12/13/16/31/57 — blocking loops + Windows taskkill: managed-thread/process wrappers
- [ ] CORE-19 — first-search auto-embed hang (background job + warming)
- [ ] CORE-39/40 — config key mismatches (`exclude_patterns` vs `exclude`; schema_version 11 vs 4)
- [ ] CORE-46 — signals ingest idempotency (stable hash ids)
- [ ] CORE-51/52/53 — oracle/suggestion: extract `briefing`, capture analyzer status, confidence labeling

## D. Re-verification after any change

- [ ] `python -m pyflakes lib/cipkg` — re-check F-01/F-03/F-09 against edits → **[A1]**
- [x] `python -m pytest tests/` — **DONE (2026-08-16, [A2])**: re-established baseline → **10 failed, 90 passed,
      1 skipped, 30 errors, 166.75s** (F-10 reference was 29 errors → **+1 error**). Failed = 8 integration
      `TypeError` + 2 Textual snapshot mismatches; errors = 22 terminal_dashboard (out of scope, F-10) + 9
      integration `PermissionError` (F-03 signature fix not yet landed). Recorded as F-42B. Verify fixes keep
      them green.
- [ ] Rules dry-run harness (in-memory DB backup + `run_rules`) — rerun after any rules/indexer change
      → **[A1]**

## E. Ground rules for future passes

- Ground every new finding in `09-bugs-and-issues.md` first — no duplicates. Add `Cross-ref:` when related.
- `.cip` index is Python-only (indexed before TS/web existed) — TS/Prisma rule results of 0 are expected-empty,
  not findings.
- Legacy web layer (`web_server.py` routes, `static/js/*`, `dashboard*`, `websocket_handler.py`) is out of
  scope — new frontend from scratch. Web findings stay only as fix-in-bridge references.
- F-ids are stable: F-42 is taken (F-22 root cause, Agent 1), F-42B is the test baseline (Agent 2) — continue from F-43. Append to §5, keep merge-notes (§6) accurate.
- Cadence is set in §3 — the default is "write it down immediately, same pass," never "later."
- If a pass is interrupted mid-module, record partial state in §6 merge-notes (e.g. "read lines 1–150 of X,
  rest pending") so the next session resumes, not re-reads.
