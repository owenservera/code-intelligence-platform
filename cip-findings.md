# CIP Deep Code Inspection — Verified Findings Log

**Scope:** backend/core only (frontend/dashboard/terminal-UI excluded per instruction).
**Repo:** `C:\0-BlackBoxProject-0\index` — CIP Code Intelligence Platform v2.0.
**Base commit:** `a949242` (master, clean HEAD). Working tree has modified + untracked files.
**Verification env:** Python 3.14.4, ruff 0.15.12, pyflakes 3.4.0, pytest 8.4.2.

This doc is a rolling findings log written at ~150k-token intervals so nothing is lost on compaction.

> **SUPERSEDED (2026-08-16):** This file was the early scratch log. Findings are now consolidated into
> `docs/dev/09-bugs-and-issues.md` §5 (F-01..F-14) which is the single rolling scratch log going forward.
> Do not append new F-entries here.

---

## Priority legend
- **P0** = breaks core indexing/search/analysis; security.
- **P1** = silent wrong behavior / dead core path / broken test infra.
- **P2** = feature or edge path broken/weak, no user-visible crash today.
- **P3** = style, unused code, docs drift.

---

## F-01 [P1] `analysis.py` calls nonexistent `nextjs.list_findings` — quality component of health score always defaults to 80

- `lib/cipkg/analysis.py:49-57`, `:89-105`, `:133-149`
- Each function does `from .stack import nextjs as sn` then `sn.list_findings(con)`.
- `lib/cipkg/stack/nextjs.py` exposes ONLY: `_read`, `_app_route_path`, `index_routes`, `route_referenced`, `list_routes`. **No `list_findings`.**
- Consequence: `AttributeError` raised on every call, swallowed by `except Exception` → `log_swallowed` → `quality_score = 80` fallback **always**.
  - `_calculate_health_score`: the quality component never computes real findings.
  - `_list_critical_issues`: "security findings" section is always empty.
  - `_list_high_priority`: "code duplication" section is always empty.
- Fix: implement `list_findings` in `nextjs.py` (or `stack/rules.py`'s `run_rules`) and call the real API.

## F-02 [P1] `lancedb_store.py` uses `json` without importing it

- `lib/cipkg/lancedb_store.py:55` → `"metadata": json.dumps(meta)` → `NameError` if executed.
- Confirmed: no `import json` in file (imports are lancedb, pyarrow, numpy, typing, os; `sqlite3` + `from .store import vector_matrix` are inside `migrate_sqlite_to_lancedb`).
- Module is also **dead code** (see F-04).

## F-03 [P1] Integration tests call stale `indexer.sync(con, cfg)` signature

- `indexer.sync(root=None, full=False, do_embed=True, progress=None)` (`indexer.py:405`).
- Tests call `indexer.sync(con, cfg)`:
  - `tests/test_integration.py:41,66,84,110,130,150,170,192`
  - `tests/conftest.py:91` (`initialized_repo` fixture).
- `con` (sqlite3.Connection) is bound to `root`; `cfg` to `full` → wrong path; and `do_embed=True` default triggers model load → **single test hangs >120s** (confirmed by direct run timing out) and full-suite run reports `PermissionError` errors.
- Impact: all 10 `test_integration.py` tests + `initialized_repo` fixture error. Correct call is `indexer.sync(root=temp_repo, do_embed=False)` or `_sync_body`.

## F-04 [P1] Three backend modules are dead code and/or broken

| Module | Referenced by | Problem |
|---|---|---|
| `lib/cipkg/retrieval_bridge.py` | only `tests/test_integration.py:185` (`search_and_format`) | `ContextManager` references `con` that is never defined in scope (pyflakes F821 "undefined name 'con'"), missing `import sqlite3`/`connect`; unreachable from `cli.py`/`server.py`/`retrieve.py` |
| `lib/cipkg/ast_chunker.py` | nothing (grep across repo: 0 hits) | `chunk_by_ast`/`chunk_file_ast_aware` defined but never wired into `indexer.py`/`parsers.py` |
| `lib/cipkg/lancedb_store.py` | only a string reference in `dependency_checker.py` | not wired into `embed.py`/`store.py`/`vecstore.py`; `migrate_sqlite_to_lancedb` unreachable; missing `json` import (F-02) |

All three are **untracked files** in git (never committed).

## F-05 [P2] `stack/tauri.py` capability regex likely never matches real Tauri v2 manifests

- `lib/cipkg/stack/tauri.py:7` — `CAPABILITY_RE = r'"allow":\s*\[\s*\{[^}]*"cmd":\s*"([^"]+)"'`
- Real Tauri v2 capability files use permission objects like `{ "identifier": "shell:allow-open", "allow": [{ "name": "open" }] }` — key is `"name"`, not `"cmd"`, and allow entries are not `{ "cmd": ... }` objects.
- `parse_capabilities` reads raw file content and regex-matches it; never `json.loads` the file (`json` imported but unused).
- Net effect: `allowed_commands` is effectively always empty → `TAURI-UNGATED-COMMAND` (rules.py:481) flags every indexed command as ungated; `is_allowed` always False. Tauri security analysis is non-functional.
- Also `except (OSError, json.JSONDecodeError)` catches an exception class that can never be raised here (dead except).

## F-06 [P2] `retrieve.py` `_external_search` broken exception tuple + fragile control flow

- `lib/cipkg/retrieve.py:124` — `except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception)`
  - `import json` happens at line 105 **inside** the `try`. If `subprocess.TimeoutExpired` fires before line 105 runs, evaluating the except tuple raises `NameError: name 'json' is not defined`, masking the original exception.
  - Trailing `Exception` makes the two specific tuples redundant and swallows every error (only used for external-search fallback, so low impact).
- Also `retrieve.py:172-173` does `cfg["retrieval"]["lexical_k"]` direct dict access → `KeyError` if config section missing.

## F-07 [P2] Memory DB path inconsistency — two separate memory stores

- `lib/cipkg/learning_system.py:693-706` → `AgentMemory(<data_dir>/learning_data/memory.db)`, `AgentExperienceLogger(<data_dir>/learning_data/episodes.db)`.
- `lib/cipkg/web_server.py:270-281, 458-483` → `TemporalKnowledgeGraph(<root>/.cip/memory.db)`, `EpisodicMemory(<root>/.cip/episodes.db)`.
- AGENTS.md documents `.cip/memory.db` + `.cip/episodes.db`.
- Both are SQLite tables created by `TemporalKnowledgeGraph`/`EpisodicMemory`, but on **different database files** → learning + memory layers never share data.

## F-08 [P3] `learning_system.py` recall and suggestion-preference analysis are near-dead logic

- `recall_relevant` (semantic branch): predicate built as `f"command:{query[:50]}"` — matches only if the identical command string was previously stored via `remember(command=...)`. No fuzzy/embedding recall. Weak.
- `_analyze_suggestion_preferences`: `category = action.context.get('category', 'general')`, but `record_suggestion_response` stores only `{'suggestion_id': ...}` (no category) → every suggestion lands in `'general'`; preference analysis collapses to a single bucket.

## F-09 [P3] pyflakes-flagged unused/undefined items (real, verified)

- `lib/cipkg/lancedb_store.py:55` — `json` used, not imported (F-02).
- `lib/cipkg/retrieval_bridge.py` — `con` undefined (F821); missing `sqlite3`/`connect` import.
- `lib/cipkg/error_system.py:97` — local `error_type` assigned, never used.
- `lib/cipkg/gatekeeper.py:225` — local `title` assigned, never used.
- `lib/cipkg/intelligent_executor.py` — unused imports `datetime`, `threading`, `Callable`.
- `lib/cipkg/__init__.py:5` — F401 unused imports.
- `lib/cipkg/command_registry.py:11` — F401 `inspect`.
- `lib/cipkg/base.py` — E401/E701/E702 style violations; `cli.py` E702.

## F-10 [P2/P3] Test-suite state (recorded)

- `tests/sync-system/` → **15 passed, 19.5s** (sync engine, validation, cip global) ✅
- Full suite `pytest tests` → **10 failed, 90 passed, 1 skipped, 29 errors, 174s**.
  - Errors: all `tests/terminal_dashboard/*` (out of scope) + `tests/test_integration.py` (F-03).
  - `tests/conftest.py:20-31` imports `cipkg.terminal_dashboard` at module import time → every collected test (incl. non-dashboard) requires Textual dashboard importable. A root-conftest coupling smell.
- Test files shipped inside package: `lib/cipkg/test_embed.py`, `lib/cipkg/test_gapfill.py` (would be collected by any `pytest` run over `lib/`).

## F-11 [P1] Repo-profile system (`repo-settings/`) is dead in every runtime code path — profiles & `external_search` never load

- `lib/cipkg/base.py:117-122` — `cip_base_dir = os.path.dirname(os.path.dirname(__file__))`; `__file__` = `lib/cipkg/base.py` → resolves to `lib`, so `repo_settings_dir = lib/repo-settings`, which **does not exist** (`Test-Path lib/repo-settings` → False). `from detectors import ...` → ImportError → silently swallowed by bare `except Exception: pass` at line 144.
- Verified at runtime: `load_config('.')` → `profile: {}`, no `external_search` key, `index.exclude` empty.
- `lib/cipkg/context_manager.py:155` and `lib/cipkg/suggestion_engine.py:637` do `from repo_settings.detectors import detect_repo_type` — but the actual directory is named `repo-settings` (hyphen), which cannot be imported as `repo_settings` → always `ImportError` → `RepositoryProvider.provide` always falls to `_fallback_provide` (repo_type=`generic`, config=`{}`). Verified: `import repo_settings.detectors` → `ModuleNotFoundError`.
- Only `bin/cip.py:42-45` computes the correct path (`<root>/repo-settings`) and it works — but that code only prints a banner during `cip init`.
- Impact:
  - `retrieve.py:81-84` `_external_search` reads `cfg["external_search"]` → always empty → the vivim-final `defer_to = "bun"` / `code-index search` integration (external_search.toml) **silently never runs**.
  - Profile overrides (retrieval k-values, stack rule toggles, include/exclude, profile settings in `RepositoryContext.profile_settings`) are never applied anywhere.
  - `context_manager` repo_type is always `generic`; repo profile is always `{}`.
- Also: `AGENTS.md` documents `lib/cipkg/repo-settings/`, which does not exist; `repo-settings/profiles/vivim-final/custom_rules.toml` is dead config — `stack/custom_rules.py:load_custom_rules` reads only `.cip/rules.py` and never reads `cfg`.
- Positive control (shows data is fine): adding `<root>/repo-settings` to `sys.path` → `detect_repo_type('.')` returns `index`, `load_repo_profile` returns sections `profile/language/retrieval/stack`.
- Fix: resolve `repo-settings` from the repo root (walk up from cwd) or install a properly named package; `context_manager.py`/`suggestion_engine.py` should import `detectors` the same way as `base.py`.

---

## Cleared hypotheses (verified NOT bugs)

- `stack/prisma.py` DOES define `index_stack` (line 62) → `stack/audit.py:20` call is valid.
- `maintain.verify` exists (`maintain.py:16`); `gapfill.dead` exists (`gapfill.py:92`) → `analysis.py` calls valid.
- `indexer.py`/`retrieve.py` core logic is sound (parallel parse worker, mtime+hash fast path, RRF, scoped edge rebuild, tested_by rebuild). No obvious correctness bug in the hot path.
- `stack/rules.py` `RULES` list IS consumed: `custom_rules.get_all_rules` → `RULES + custom` → `run_rules`. Not dead.
- `learning.py` (used by `cli.py:9`) and `learning_system.py` (used by `intelligent_executor`, `command_adapter`, `interactive`) are distinct features, not a naming conflict.
- `compileall -q` over lib/cipkg, repo-settings, sync_global → exit 0 (no syntax errors).

---

## Repro / evidence notes
- pyflakes run: `python -m pyflakes lib/cipkg` → flags above.
- pytest singles: `python -m pytest tests/test_integration.py -q` → hangs >120s (embed model load via stale-signature full sync).
- `python -m pytest tests/sync-system -q` → 15 passed in 19.5s.

*Next checkpoint targets:* `workflow_engine.py`, `error_system.py`, `intelligent_executor.py`, `command_registry.py`, `cli.py`, `server.py`, `learning.py`, `memory/episodic.py` + `memory/consolidation.py`, `sync_global/`. *(Done this pass: `stack/audit.py`, `stack/impact.py`, `gapfill.py`, `store.py`, `embed.py`, `vecstore.py`, `rerank.py`, `base.py`, `parsers.py`, `parse.py`, `tree_parser.py`, `detect.py`, `retrieve.py` (full), `context_manager.py` (full), `bin/cip.py`, `repo-settings/` → F-11.)*
