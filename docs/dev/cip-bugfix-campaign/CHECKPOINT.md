# CHECKPOINT — CIP Bug-Fix & Detection Campaign (session state)

**Folder:** `docs/dev/cip-bugfix-campaign/` · **Date:** 2026-08-16
**Purpose:** canonical anti-erasure anchor (RUNBOOK §6.4, AGENTS.md 120K rule). If autocompaction fires,
this file + TRACKER + LEDGER are the only truth a fresh agent needs to resume. **Docs win over memory.**

---

## Current position

- **Framing decision (user-confirmed):** CIP is a **general polyglot code-indexing + issue-detection
  SYSTEM**, not a repo-specific fix. Every fix and detector below is CIP-product-wide — it ships in
  `lib/cipkg/**` surfaces and applies to every future repo CIP indexes. The `09` log is CIP dogfooding
  itself. Portability = CIP dispatches detectors by file language (RUNBOOK §0, `PROFILE.cip.md` §2). We do
  NOT copy campaign docs into other repos.
- **Phase S complete (systemic foundation, 5/5) + Phase 3 complete (index integrity, 3/3) + Phase 4
  complete (audit/health honesty, 5/5) + Phase 0 complete (undefined names & broken imports, 9/9) +
  Phase 1 dispatch coverage (F-16/F-15/F-17) landed.**
  Phases remaining: 1 sweep (deletions) → 2 → 5 → manual (DEPENDENCIES.md §2).
- **Next unit: Phase 1 sweep — legacy-frontend / dead-code deletions (ranks 21–30).** F-16 dispatch
  (20/21 wired) + F-15 arity + F-17 misroute are FIXED and regression-locked (conformance 29 → 6).
  Remaining Phase 1 work: the family-sweep deletions per `10-plan §6` (delete `command_adapter.py`,
  `interactive.py`, `interactive_ui.py`, `help_system.py`, `watcher.py`, `dashboard_state.py`,
  `stack/selftest.py`, `ast_chunker.py`, `retrieval_bridge.py`, `lancedb_store.py`; extract
  `briefing()` → `stack/briefing.py` F-38; drop `ast_aware_chunking` BUG-011/024) and the note-only rows
  (F-25, F-40). The 6 residual conformance findings (`dashboard` legacy TUI + 5 legacy-frontend
  MISSING-SYMBOL) clear when the new frontend lands — those sites are NOT fixed.

## Completed this session (Phases S3 + S4 + Phase 4 landing)

### Framing / docs generalized (product-wide, not repo- or Python-specific)
- `PROFILE.cip.md` (NEW): CIP's own wiring + per-language instrument matrix (LINT, swallow, signature
  probe, config diff, test runner — per stack). Portability lives IN the product.
- `RUNBOOK.md` §0 (NEW): what the campaign IS — product fixes + product detection features; this repo is
  the dogfood corpus; no embeddings; method vs artifacts split.
- `DESIGN.md` §0 (NEW) + §2 intro: universal family archetypes, instrumented per language.
- Scoped notes on `LEDGER.md`, `DEPENDENCIES.md`, `TRACKER.md`, `10-selfcheck-enhancement-plan.md`.
- `AGENTS.md`: added "Detection-System Campaign (CIP-product-wide)" section pointing to RUNBOOK §0 +
  PROFILE.cip.md. **Existing comments preserved everywhere.**

### S1 — swallow discipline — **DONE, proven(b+c), regression-locked**
- **Detector:** `tests/detectors/s1_swallow_scanner.py` (AST: broad `except`/`Exception`/`BaseException`
  + silent body = only `pass`/stdout-`print`, no return/raise/break/continue/log).
- **RECALL proven (on broken):** flagged exactly the evidence — `stack/audit.py:19,21` (F-24/F-41),
  `base.py:144` (F-11/CORE-41), `suggestion_engine.py:657` (CORE-52 print-swallow).
- **PRECISION proven:** 0 FPs on `tests/data/clean_ref/` incl. new `good_handling.py` fixture
  (narrow excepts, return/raise surfacing, `log_swallowed` call → NOT flagged).
- **Fixes applied LAST (product-wide):** `stack/audit.py:18-21` → `log_swallowed(...)` instead of
  `pass`; `base.py:144` bare pass → `log_swallowed("base.load_config.repo_settings", e)`;
  `suggestion_engine.py:659` print → `log_swallowed(...)` (added `from .base import log_swallowed`).
- **REGRESSION-LOCK:** `tests/detectors/s1_swallow_discipline_test.py` — `test_s1_recall_evidence_sites`
  FLIPPED to clean-assertion (evidence sites no longer flagged) + `test_s1_precision_clean_ref`.
  Full `tests/detectors/` run: **5 passed** (S1×2 + S2×3), S2 unaffected.
- **pytest.ini:** `python_files` now `test_*.py *_test.py` so the `*_test.py` detector suite is
  discovered by directory runs (S2 had been run by explicit path only).
- **KPI:** broad silent-swallows in `lib/cipkg` = 83 pre-fix → 79 now (evidence sites fixed; the 79 are
  guarded by the gate and decrement as Phase 4/5 behavioral rows land). LEDGER §2 row + §3 precision row
  added. TRACKER S1 Land☑ Verified☑; summary 2/5 mechanics harvested.

### S2 — static-lint gate — (earlier) DONE, proven(b+c), regression-locked
- pyflakes gate (103 findings baseline), `s2_static_lint_gate_test.py` (3 passing), CI workflow
  `.github/workflows/cip-static-lint-gate.yml`. Fix deferred to Phase 0 rows 9/11 (detect-first). F-06
  remapped to S3 runtime probes.

### S5 — `cip doctor` skeleton — **DONE, proven(b+c), regression-locked**
- **Product surface:** `lib/cipkg/doctor.py` (456 lines) — `doctor(root, scope)` returns
  `{ok, scopes, findings, total}`; scopes `--static` (S1 swallow-scanner + S2 pyflakes gate, lint optional
  if instrument missing), `--config` (CONFIG-* self-consistency), `--runtime` (only measured claims).
- **CLI:** `cli.py` doctor subparser (L~579) + `handle_doctor_command` scope dispatch (L224) + entry
  (L~710). `cip doctor` (no flag) = JSON then legacy `cmd_doctor` report.
- **RECALL proven (on this repo):** `cip doctor --config` = 8 findings / 7 rules — CONFIG-FILE-UNPARSEABLE
  (NEW ROOT FINDING: `config.default.toml` is invalid TOML — `[analysis] health_weights = {` multiline
  inline table L151, so shipped defaults never load; loader falls back to `base._parse_toml_naive` +
  hardcoded defaults), PORT-MISMATCH CORE-10 (8765 vs 8787), SCHEMA-DRIFT CORE-40 (11 vs 4),
  KEY-DRIFT CORE-39 (exclude_patterns/max_file_size ×2), KEY-UNUSED CORE-42 ([performance] vs [perf]),
  MISSING-SECTION CORE-2 ([web] absent), PROFILE-SILENT-FAIL F-11. `--runtime` = RUNTIME-DAEMON-DOWN
  (measured, no fake ok). `--static` = CODE-{SILENT-SWALLOW,STATIC-LINT,UNDEFINED-NAME,UNUSED-IMPORT}.
- **Detector promoted:** `tests/detectors/s1_swallow_scanner.py` is now a thin shim re-exporting from
  `cipkg.doctor` (canonical logic lives in the product; S1 tests import the shim and stay green).
- **PRECISION proven:** reconciled virtual config → 0 findings; runtime fails surface as
  RUNTIME-PROBE-FAILED with evidence (never silence); `--static` stays 0-FP on clean_ref.
- **REGRESSION-LOCK:** `tests/detectors/s5_doctor_skeleton_test.py` (7 tests). Windows lock fixed:
  runtime DB probe closes `connect()` (tempdir cleanup no longer blocked). Full `tests/detectors/`
  run: **12 passed** (S1×2 + S2×3 + S5×7).
- **Wiring verified:** parser exposes the 3 flags; `doctor(root, scope)` runs all scopes from the CLI.
- **KPI:** LEDGER §2 row `config.default.toml parseable by loader` added (BROKEN = invalid TOML).
  S5 fix deferred to Phase 2 (config family) — detect-first, fix-last. TRACKER S5 Land☑ Verified☑;
  summary 3/5 mechanics proven.

### S3 — signature/attribute conformance suite — **DONE, proven(b+c), regression-locked**
- **Detector:** `tests/detectors/s3_conformance.py` — pure static AST analyzer over a package root, **no
  execution**. Pass B: parsed subcommands vs dispatch-table entries vs `handle_<cmd>_command` handlers
  (CODE-UNHANDLED-COMMAND F-16, CODE-MISROUTED-COMMAND F-17, CODE-ARITY-MISMATCH F-15 ≥2 positional
  params). Pass C: internal `from {mod} import {name}` against a top-level-name index of every module
  incl. `__init__.py` re-exports + submodule fallback (CODE-MISSING-MODULE F-13, CODE-MISSING-SYMBOL
  F-35). Pass D: module-attribute calls on filter lists (retrieve/indexer module binds) → F-21/F-31/F-32.
  Pass E: class-instance member calls checked against the instance's class (F-20).
- **RECALL proven (on lib/cipkg):** 53 findings — 21 CODE-UNHANDLED-COMMAND (gate, coverage, deps,
  embedder, dashboard, admission, refactors, routes, models, embed-ping, dead, circular, blame, score,
  migrations, env, logs, metrics, features, api, predict), 1 CODE-MISROUTED-COMMAND (verify-index →
  handle_verify_command, not handle_verify_index_command), 2 CODE-ARITY-MISMATCH (handle_analyze_command,
  handle_rebuild_command take only root), 1 CODE-MISSING-MODULE (cli.py:217 `from .ingest import ...`),
  28 CODE-MISSING-SYMBOL (server.mcp_main; selftest.selftest ×2 sites; summarize.map/describe typo (real
  name `map_`); 15 `from .cli import handle_*` in command_registry.py:1085–1313; stack/impact ImpactAnalyzer;
  gapfill GapFiller; retrieve.hybrid_search + runtime_adapters.broken ×2; indexer.mark_for_reindex;
  suggestion_engine self.filter_engine.rank; workflow_engine cipkg.audit/impact).
- **FP scrub:** verified legitimacy of all 28 MISSING-SYMBOL against the real module exports; fixed an
  engine bug where `os.path.relpath` rooted the package root at `"."` not `""` (dropping `__init__.py`
  re-exports — `cipkg.__version__` was a false positive, now correctly resolved). Final: 0 known FPs on
  real signal.
- **PRECISION proven:** 0 findings on a synthetic clean package (all wiring consistent: parsed cmds all
  dispatched, handler arity OK, imports resolve, module-attr + class-member calls exist) AND 0 on
  `tests/data/clean_ref/`.
- **REGRESSION-LOCK:** `tests/detectors/s3_conformance_test.py` (12 tests: 9 RECALL + 2 PRECISION +
  1 evidence-contact sanity). Full `tests/detectors/` run: **24 passed** (S1×2 + S2×3 + S5×7 + S3×12).
- **KPI:** conformance findings on lib/cipkg = 53 (baseline) → 0 as Ph0/1/3 fixes land; `cip X` unknown
  command 21→0; registry cards 16→0. LEDGER §2 + §3 rows added. TRACKER S3 Land☑ Verified☑; summary
  4/5 mechanics proven (detectors 4/53, precision 4/53, locked 4/53, fixes 1/53). Zero product LOB
  (analyzer lives in tests/detectors) — within S/CONFIG budget.

### S4 — config-schema loader suite — **DONE, proven(b+c), regression-locked**
- **Suite:** `tests/detectors/s4_config_schema_test.py` (15 tests) deepens the S5 CONFIG-* skeleton —
  per-rule RECALL with contract refs + evidence, the `_load_repo_toml` loader contract, per-rule surgical
  PRECISION, and a flip-invariant on the broken default file.
- **RECALL proven (on this repo):** all 7 CONFIG-* rules fire with the DESIGN refs — FILE-UNPARSEABLE
  (CORE-39), PORT-MISMATCH (CORE-10), SCHEMA-DRIFT (CORE-40), KEY-DRIFT (CORE-39),
  KEY-UNUSED (CORE-42), MISSING-SECTION (CORE-2), PROFILE-SILENT-FAIL (F-11); FILE-UNPARSEABLE evidence
  names `config.default.toml` + the decode error.
- **INVARIANT locked (FLIPS in Ph2):** `tomllib.loads(config.default.toml)` raises TOMLDecodeError — the
  shipped default is invalid at line 151 (`[analysis] health_weights = {` multi-line inline table).
- **LOADER contract proven:** `_load_repo_toml` returns `(cfg, toml_error)`; on a decode error on the
  shipped default it returns IMMEDIATELY (a %-root invalid default does NOT become the v2 defaults —
  proven by writing an invalid default + a valid v2 in a temp root and asserting the naive fallback cfg
  is returned, not the v2 load); valid file → `(cfg, None)`; no files → `({}, None)`.
- **PRECISION proven (per-rule surgical):** missing only `[web]` → {MISSING-SECTION}; only `[performance]`
  → {KEY-UNUSED}; only `index.exclude_patterns` → {KEY-DRIFT}×1 (not max_file_size); daemon port equal to
  a code-scan `default:` literal (daemon.py fixture) → silent; `schema_version == store.SCHEMA_VERSION`
  → silent; mismatches fire (port 8765 vs code 8787; schema 11 vs 4).
- **REGRESSION-LOCK:** full `tests/detectors/` run: **39 passed** (S1×2 + S2×3 + S5×7 + S3×12 + S4×15).
- **KPI:** `config.default.toml parseable by loader` now locked by both the invariant and the loader
  contract; stays BROKEN until the Ph2 fix (detect-first). **Phase S complete: 5/5 mechanisms.**
  TRACKER S4 Land☑ Verified☑; Total 5/53 detectors, 5/53 precision, 5/53 locked, 1/53 fixes.

## Completed this session (Phase 3 — index integrity, after Phase S landing)

### F-22 — import resolution repair (live index: `imports` edges 12 → 260)
- Product fix in `indexer.resolve_import` (2 edits): relative branch now converts dotted module names to
  submodule paths (`stack.common` → `stack/common`, never a literal `lib/cipkg/stack.common.py` dot-file),
  counts leading dots for parent hops (`..base` from `stack/` → `cipkg/base.py`), normalizes the base dir,
  candidates `__init__.py` first then `RES_EXTS` + `index*` variants; absolute `cipkg.*` specs try
  `("", "lib/", "src/")` prefixes. Missing modules still return `None` (genuine dead refs are NOT
  fake-resolved).
- **In-repo resolution rate: ~0.2% → 99.79% (486/487).** The only unresolved spec is the genuinely-broken
  `lib/cipkg/cli.py .ingest` (dead import, already a S3 CODE-MISSING-MODULE finding; a Ph0 fix target).
- Unit cases regression-locked: multi-seg `.stack.common`, `.memory.episodic`/`.memory.temporal_graph`,
  `..base`/`..store`/`..` from `stack/`, absolute `cipkg.command_registry`, `None` for missing modules.

### F-42 — backup/duplicate pollution (live index: 575 backup files → 0)
- Product fix at BOTH surfaces the pipeline actually uses:
  - `base.py`: `DEFAULT_EXCLUDES` extended (`__pycache__`, `.pytest_cache`, `node_modules`, `.venv`,
    `venv`, `backups`, `htmlcov`, `dist`, `build`, `.tox`) + new `BACKUP_DIR_PREFIXES
    ("backup_", "emergency_")`; `iter_files` prunes both. (Used by `detect.py` + the detector itself.)
  - `gatekeeper.py` (THE ingestion path, `iter_files_smart` → `_scan`/`_decide`): new segment-aware
    `_is_backup_segment` (`backups`/`htmlcov` exact, `backup_`/`emergency_` prefix, `.bak`/`.orig` suffix)
    gates `_decide` (truthful `explain()`; skip reason "backup/duplicate tree") and prunes the `_scan`
    walk. Because `HARD_DIRS = DEFAULT_EXCLUDES`, the `backups`/`htmlcov` exact entries already flow in.
- **Critical over-match bug caught by tests:** flat-substring matching flagged test numbers that merely
  *contain* the word `backup_` (e.g. `bug_...test_f42_backup_pollution.md`) → predicate is segment-aware.
- **Live after:** files 753 → 156 (575 backup copies + stale rows gone), backup pollution **76.4% → 0%**.
  The 8 remaining `sync_global/` files are the *module source* (`core/sync_engine.py` etc.) — legit.

### F-23 — tested_by grounding (live index: 4,462 noise → 0)
- Product fix in `build_tested_by` (indexer.py): tested_by edges now come ONLY from the resolved
  import/call/reference graph of each test file (post-F-22 `imports` edges), no more name-mention chunk
  matching (`name_map` over entire test bodies invented ~4.5k edges), and backup-symbol srcs are dropped
  via the shared segment-aware `_is_backup_path`. Keeps the product convention `src` = tested symbol,
  `dst` = test-file path, `src_path` = symbol path (analysis/gapfill/predict/rerank read this).
- **Live after:** `tested_by` 4462 → **159** edges, noise **0/159**, all src = real non-backup symbol ids,
  10 distinct real test files.

### Detector suite `s6_index_integrity.py` + `phase3_index_test.py` (14 tests, total 53 green)
- Detector module: `INDEX-IMPORT-RESOLUTION` (repo-wide rate using the REAL resolver + parser), 
  `INDEX-BACKUP-POLLUTION` (files under backup segments), `INDEX-TESTED-BY-NOISE` (src missing from
  symbols OR src_path under backup segments — python-side, shares the segment predicate).
- `phase3_index_test.py`: F-22 unit semantics + repo flip (rate ≥ 0.99; sole unresolved = `cli.py .ingest`),
  F-42 synthetic flip (a tree the OLD scanner indexed stays clean with `exclude = []`) + gatekeeper
  `_decide`/`_is_backup_segment` + repo 0-pollution, F-23 RECALL (broken edges counted: backup-src +
  missing-src) + PRECISION (clean synthetic DB silent).
- **Full `tests/detectors/`: 53 passed** (S1×2 + S2×3 + S5×7 + S3×12 + S4×15 + Ph3×14). `tests/data/clean_ref/`
  untouched.
- **TRACKER Phase 3: 3/3 proven(b+c) + precision + locked + fixes; Total 8/53.** LEDGER §2 KPIs filled,
  §3 precision rows FLIPPED to ☑, §1 F3 budget marked within.

### Rebuild mechanics learned (important for Phase 4 KPI work)
- `python -m cipkg.cli rebuild` / `... sync` are **silent no-ops**: `lib/cipkg/cli.py` has NO
  `if __name__ == "__main__":` guard, so `python -m` imports the module and exits 0 doing nothing
  (AGENTS.md documents the `-m` form). The `bin/cip.py` launcher calls `cli_main(...)` directly and works.
  **Discovered + deferred to Phase 0/1 (CLI dispatcher family) — do NOT fix in Phase 3 scope.**
- Correct full rebuild: `PYTHONPATH=lib python -c "from cipkg.maintain import rebuild"` hangs in
  `embed_pending` (config `embed.backend=a auto`, `autostart=True` → tries to spawn the embedding
  service on :8787). Reliable: call `indexer.sync(root='.', full=True, do_embed=False)` directly
  (156 files in ~4.6s). Phase 4 KPIs must measure with `do_embed=False` and note the `-m` gap.
(156 files in ~4.6s). Phase 4 KPIs must measure with `do_embed=False` and note the `-m` gap.

### Phase 4 — audit/health honesty — **DONE, proven(b+c), regression-locked (8/8)**
- **Detector module:** `tests/detectors/s6_audit_integrity.py` — 5 metrics (open-findings plus
  QA-DUP/ESLINT/failed-indexers/quality-severity/health-ring), each **returns int divergence count**
  (0 = healthy). Fixtures: `_seed_dup_pair`, `_seed_eslint_row`, `_insert_finding`, `_fresh_repo`
  (real `store.connect` + `stack.common.ensure`).
- **Suite:** `tests/detectors/phase4_audit_test.py` — 8 tests: BUG-015 recall (ESLINT row survives
  auto-close; rule-not-run), F-41 (stub sub-indexer raise → `failed_indexers` names surfaced),
  BUG-014 (coverage reads given root — 1699≠cwd), F-01/BUG-013 (score reacts to real critical/high),
  CORE-30 (empty repo ring ≠ 50 + finding-sensitive) **+ 2 PRECISION** (stale row of a RAN rule still
  closes; clean audit reports `failed_indexers == []`). **All 8 failed pre-fix, all pass post-fix.**
- **Fixes applied LAST (product-wide):**
  - `analysis.py`: added `_open_findings(con)` (reads the stack findings table directly —
    `nextjs.list_findings` never existed); `gapfill.coverage(root)` threaded (BUG-014); quality_score =
    `max(0, 100 − critical*20 − high*10)` from real findings, no fallback-80 (F-01/BUG-013/CORE-27);
    empty-repo literal-50 early-return removed → derived ring still penalized by findings (CORE-30);
    critical/high lists read `_open_findings`.
  - `stack/rules.py`: extracted `enabled_rules(root, cfg)` (built-in + custom minus `ignore_rules`),
    shared by `run_rules` and the audit sweep (BUG-015).
  - `stack/audit.py`: sub-indexer failures now surface as `failed_indexers` (F-24/F-41, no bare
    swallow); auto-close sweep scoped to `WHERE rule IN (enabled_ids) AND id NOT IN (seen)`.
- **Live after-values (LEDGER §2):** overall health score **55.3 → 61.3**; quality_score 100 at 0
  findings (no forced 80); audit open=0 with 0 wrong flips; `run_rules` 57 findings (medium 41, low 16);
  index intact (156 files, 1699 symbols). `grep list_findings lib/` → 0.
- **Full `tests/detectors/`: 61 passed in 94s** (S1×2 + S2×3 + S5×7 + S3×12 + S4×15 + Ph3×14 + Ph4×8).
  `tests/data/clean_ref/` untouched. **TRACKER Phase 4: 5/5 proven+precision+locked+fixes; Total 13/53.**
  LEDGER §2 after-values + §3 precision rows flipped; §1 F4 budget within.
- **Pre-existing unrelated failures:** `tests/test_integration.py` (test_gapfill_integration,
  test_health_score_integration, test_impact_analysis_integration) — caller passes
  `indexer.sync(con, cfg)` but sync takes `(root=None, full=False, do_embed=True, progress=None)` →
  `TypeError: expected str ... not Connection` in base.data_dir; plus pytest-asyncio deprecation
  warnings from `tests/terminal_dashboard/conftest.py`. Not caused by Ph4 edits.

## Completed this session (Phase 0 — undefined names & broken imports, ranks 9–17)

### One-line product fixes (detect-first, fix-last; regression-locked after)
- **F-06** `retrieve.py:_external_search` — exception tuple `json.JSONDecodeError` referenced `json`
  before the import (line 105 import, line 124 tuple) → `NameError` masking the real error. Fixed import
  placement.
- **F-13** `workflow_engine.py` — `from cipkg import audit` / `from cipkg import impact` (nonexistent
  top-level modules; real names `cipkg.stack.audit` / `cipkg.stack.impact`) → audit/impact steps silently
  no-op'd. Fixed to the real submodule paths.
- **F-20** `suggestion_engine.py:663` — `self.filter_engine.rank(ranked)` but `FilterEngine` only defines
  `filter()` → AttributeError on EVERY suggestion call. Fixed to `self.filter_engine.filter(ranked)`.
- **F-31** `session.py` — `retrieve.runtime_adapters.broken` (no such attribute) + `map_()` key mismatch
  (`totals.files` exists, `subsystems`/`total_files`/`overview` don't) → session context packet silently
  empty. Fixed to `from .runtime_adapters import broken` and the real `map_` keys.
- **BUG-005/F-02** `lancedb_store.py:55` — `json` never imported → NameError in `add_embeddings()`. Added
  import.
- **F-34** `cli.py` `handle_selftest_command` — `from .selftest import selftest` but `selftest.py` only
  defines `run_selftest()` → `cip selftest` ImportError. Fixed to `run_selftest`.
- **F-35** `cli.py` — `deps` parser registered + registry card `from .cli import handle_deps_command`, but
  cli never imported it → `deps` broken in CLI AND registry. Wired the real `dependency_checker`
  handler.
- **CORE-5** — all 14 `CommandCard.handler` names (`gate, refactors, dead, circular, deps, coverage,
  migrations, env, logs, metrics, features, api, blame, predict`) added as real handlers in `cli.py`
  (13 → `gapfill.*`, `gate`/`refactors` → `stack.audit`, `predict` → `predict.predict_next_context`).
- **Live-CLI broken imports found during wiring:** `handle_ingest_command` (`from .ingest import ingest`
  → real `from .runtime_adapters import ingest`), `handle_mcp_command` (`server.mcp_main` → real
  `server.mcp_stdio`), dispatch `map`→`summarize.map_`, `describe`→new `_server_describe` helper
  calling `server.describe`.

### `cli.py __main__` guard (CHECKPOINT Phase-0 item 2)
- Added `if __name__ == "__main__":` guard so `python -m cipkg.cli <cmd>` actually runs instead of
  silently exiting 0. Verified: `python -m cipkg.cli -h` prints usage; `map`/`describe` return real JSON.
  `selftest` still hangs >120s (embed service autostart) — known Phase 2 config item, NOT F-34 scope.

### Conformance + precision (RUNBOOK §4 step 11)
- S3 conformance `conformance_checks('lib/cipkg','cipkg')`: **53 → 29** after Phase 0. The 29 remaining =
  21 CODE-UNHANDLED-COMMAND (F-16) + 1 CODE-MISROUTED-COMMAND (F-17) + 2 CODE-ARITY-MISMATCH (F-15) —
  all Phase 1 dispatch — plus 5 CODE-MISSING-SYMBOL that are **legacy-frontend deletion targets**
  (`terminal_dashboard.py:985` selftest, `web_server.py:226` ImpactAnalyzer, `web_server.py:241`
  GapFiller, `watcher.py:104` mark_for_reindex F-32, `web_server.py:186` hybrid_search F-21).
- In-repo import resolution: **99.79% (486/487) → 100% (487/487)** — the final broken ref
  `cli.py .ingest` fixed. `phase3_index_test.py::test_f22_repo_sole_unresolved_is_known_broken_ref`
  FLIPPED to assert `missed == set()` (repo now resolves 100%).
- S3 RECALL tests flipped clean-path for every Phase-0 fix (F-34 selftest symbol, F-35 registry handler
  imports ×14, F-13 workflow_engine, F-20 filter_engine, `.ingest`/`mcp_main` broken-import). S2 gate
  test re-verified. **Full `tests/detectors/`: 61 passed in 69s** (S1×2 + S2×3 + S5×7 + S3×12 + S4×15 +
  Ph3×14 + Ph4×8). `tests/data/clean_ref/` untouched.
- **TRACKER Phase 0: 9/9 proven(b+c) + precision + locked + fixes; Total 22/53 detectors/precision/
  locked, 18/53 fixes.** LEDGER §2 after-values (import resolution 100%, conformance 29, undefined-name
  scrub) + §3 precision rows updated. `09-bugs-and-issues.md` left UNTOUCHED (guardrail).

## Completed this session (Phase 1 — dead code / dispatch coverage, F-16/F-15/F-17)

### F-16 — 20/21 CLI subcommands wired into `dispatch_command`
- **Detector proven (RECALL):** S3 conformance `conformance_checks('lib/cipkg','cipkg')` surfaced all 21
  CODE-UNHANDLED-COMMAND (F-16) before any fix. Runtime-proven: `cip coverage` → `unknown command` exit 1.
- **Fix (product-wide, detect-first/fix-last):** added 20 `dispatch_command` handlers entries wired to
  REAL lib callables. 14 handlers already existed (added for CORE-5 in Phase 0) but were never dispatched;
  6 new handlers added — `routes`→`stack.nextjs.list_routes`, `models`→`stack.prisma.models_report`,
  `admission`→`gatekeeper.admission_report`/`explain`, `score`→`gapfill.score`, `embedder`→`cmd_embedder`,
  `embed-ping`→`cmd_embed_ping`.
- **`dashboard` left undispatched by design:** it is the legacy TUI (`terminal_dashboard.py`), a deletion
  target for the brand-new frontend — NOT fixed. Remains the single residual CODE-UNHANDLED-COMMAND.
- **Runtime-verified post-fix:** `coverage`, `analyze`, `score`, `admission`, `routes`, `models`,
  `refactors`, `embedder`, `verify-index` all run. `cip gate` still blocks >120s on embed-service
  autostart (known Phase 2 config item, not a dispatch defect).

### F-15 — `analyze`/`rebuild` arity aligned to `(root, args)`
- **Detector proven (RECALL):** CODE-ARITY-MISMATCH fired on both handlers; runtime-proven `cip analyze`
  → `TypeError: handle_analyze_command() takes 1 positional argument but 2 were given`.
- **Fix:** `handle_analyze_command(root)` → `(root, args)`, `handle_rebuild_command(root)` → `(root, args)`.
  `cip analyze` now returns `{overall_score: 61.3, ...}`; `cip rebuild` runs `maintain.rebuild`.

### F-17 — `verify-index` routed to the correct handler
- **Detector proven (RECALL):** CODE-MISROUTED-COMMAND — `handlers['verify-index']` → `handle_verify_command`
  (verification gate) while `handle_verify_index_command` (runs `maintain.verify(repair=)`) existed dead.
- **Fix:** dispatch `"verify-index"` → `handle_verify_index_command`. Runtime-verified: returns
  `{checked: 180, drift: []}` instead of the gate's `broken_tests` report.

### Regression-lock + docs
- **S3 tests flipped clean-path** for F-16 (20 wired, `dashboard` residual asserted), F-17, F-15.
- **Full `tests/detectors/`: 61 passed in 66s** (S1×2 + S2×3 + S5×7 + S3×12 + S4×15 + Ph3×14 + Ph4×8).
  `tests/data/clean_ref/` untouched. pyflakes clean on `cli.py`.
- **Conformance findings: 29 → 6** after Phase 1 (1 UNHANDLED `dashboard` + 5 legacy-frontend
  MISSING-SYMBOL). `cip X` "unknown command" 21 → 1 (deletion-target); registry cards 16 → 0.
- **TRACKER Phase 1: F-16/F-15 rows ☑ (proven+precision+locked+fix); Total 24/53 detectors/precision/
  locked, 20/53 fixes.** LEDGER §2 after-values + §3 precision row updated; `10-plan` §6 F-16/F-15 marked
  LANDED. `09-bugs-and-issues.md` left UNTOUCHED (guardrail).
- **Pre-existing unrelated failures (confirmed via `git stash` — fail on HEAD too):**
  `tests/test_integration.py` (caller passes `indexer.sync(con, cfg)` → TypeError in `base.data_dir`) and
  `tests/terminal_dashboard/` legacy-TUI conftest/asyncio errors. Not caused by Phase 1 edits.

## Docs (all listed values live; `09` intact)
- `09-bugs-and-issues.md` — untouched source of truth (869 lines).
- `PROFILE.cip.md` — CIP wiring + per-language instruments (NEW).
- `RUNBOOK.md` — §0 product framing + §6 MANDATORY todo discipline.
- `DESIGN.md`, `LEDGER.md`, `DEPENDENCIES.md`, `TRACKER.md`, `10-selfcheck-enhancement-plan.md` — v2.
- `tests/detectors/` — s1_swallow_scanner.py + s1_swallow_discipline_test.py + s2_static_lint_gate_test.py
  + s3_conformance.py + s3_conformance_test.py + s4_config_schema_test.py + s5_doctor_skeleton_test.py
  + s6_index_integrity.py + phase3_index_test.py + s6_audit_integrity.py + phase4_audit_test.py
  (**61 tests green**).
- `lib/cipkg/doctor.py` — product surface: `cip doctor` + `cip doctor --static/--config/--runtime`.
- `lib/cipkg/indexer.py` — F-22 (`resolve_import`) + F-23 (`build_tested_by`) fixes.
- `lib/cipkg/gatekeeper.py` + `lib/cipkg/base.py` — F-42 backup-tree gates (ingestion + `iter_files`).
- `lib/cipkg/analysis.py` + `lib/cipkg/stack/rules.py` + `lib/cipkg/stack/audit.py` — Ph4 health-truth
  (`_open_findings`, `enabled_rules`, `failed_indexers`, scoped auto-close).
- Phase 0 fixes: `lib/cipkg/retrieve.py` (F-06), `lib/cipkg/workflow_engine.py` (F-13),
  `lib/cipkg/suggestion_engine.py` (F-20), `lib/cipkg/session.py` (F-31), `lib/cipkg/lancedb_store.py`
  (BUG-005), `lib/cipkg/cli.py` (F-34/F-35/CORE-5/__main__ guard/ingest→runtime_adapters/mcp_stdio/
  map_/describe), `lib/cipkg/error_system.py`, `lib/cipkg/gatekeeper.py`, `lib/cipkg/intelligent_executor.py`,
  `lib/cipkg/command_registry.py`, `lib/cipkg/__init__.py` (F-09 targeted scrub).
- Phase 1 dispatch fixes: `lib/cipkg/cli.py` — 20 F-16 dispatch entries + 6 new handlers (routes/models/
  admission/score/embedder/embed-ping), F-15 arity (`analyze`/`rebuild`), F-17 `verify-index` route;
  `tests/detectors/s3_conformance_test.py` — F-16/F-17/F-15 RECALL tests flipped clean-path.

## Cold handoff — resume Phase 1 sweep (dead-code deletions, next unit)

1. **Restore:** Read RUNBOOK (§0 then §6) + TRACKER + LEDGER + DEPENDENCIES §2 + this file.
   Phases S + 3 + 4 + 0 + **Phase 1 dispatch (F-16 20/21, F-15, F-17)** are regression-locked green
   (**61 tests**).
2. **Phase 1 remaining scope (TRACKER ranks 21–30, "delete" level — no per-instance docs):** per
   `10-plan §6`, delete `command_adapter.py`, `interactive.py`, `interactive_ui.py`, `help_system.py`,
   `watcher.py`, `dashboard_state.py`, `stack/selftest.py`, `ast_chunker.py`, `retrieval_bridge.py`,
   `lancedb_store.py`; **extract `briefing()` → `stack/briefing.py`** (F-38/CORE-51) and reuse the WS
   topic protocol as a model (F-39/CORE-57) before deletion; `repo_map.py`/`scip_indexer.py` deleted or
   wired (F-25/F-33); BUG-011/024 drop `ast_aware_chunking` dead config path; F-40 verified-clean note-only.
   The 6 residual conformance findings (`dashboard` legacy TUI + 5 legacy-frontend MISSING-SYMBOL) are
   **NOT to be fixed** — they clear when the new from-scratch frontend lands; mark closed-by-design then.
3. **After Phase 1 sweep:** Phase 2 (config; fix `config.default.toml` invalid TOML + flip the S4
   invariant, fix embed autostart hang so `cip selftest` and `cip gate` complete) → Phase 5 → manual
   M1–M4, updating TRACKER/LEDGER/CHECKPOINT after each.
4. **Environment:** Windows, pwsh, py 3.14.4. `python -m pytest tests/detectors/ -o addopts="" -q`
   (current = **61 passing**). Measurement only with `do_embed=False`; replay full rebuild with
   `PYTHONPATH=$PWD/lib python -c "from cipkg import indexer; indexer.sync('.', full=True, do_embed=False)"`.
5. **Guardrail reminder:** NEVER edit `09-bugs-and-issues.md` (evidence snapshot, statuses stay "open"
   there by design — status lives in TRACKER/LEDGER only).

## Guardrails
- Do NOT edit `09-bugs-and-issues.md`.
- Do NOT apply fixes before RECALL+PRECISION+regression-lock are green.
- Every change is CIP-product-wide — never a this-repo- or Python-only one-off (PROFILE §2 instruments).
- Stay within machinery budget (LEDGER §1) and the 120K context budget (persist, never carry big files).