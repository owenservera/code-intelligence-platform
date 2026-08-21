# CIP Core Enhancement + Bug-Fix Plan (sequential, embedding-free)

**Status:** PLAN/SPEC (no code yet) · **Date:** 2026-08-16 · **Owner:** interactive (with user)
**Companion doc:** `docs/dev/09-bugs-and-issues.md` (source of truth for what must be fixed & detected)
**Two jobs, one sequence — but DETECT BEFORE FIX.** We do NOT fix first. The loop per cluster is:
(1) **ENHANCE CIP's core** so it can identify a bug class; (2) **PROVE the detector** by running normal
CIP against this repo while the bug is *still present* — it must fire on the broken code; (3) only
**AFTER** the detector is confirmed working do we **FIX** the defect in `09`. Fixing last means the
detector is validated against real evidence, and a re-run then shows the signal flip broken → healthy
(proving both the fix and the detector). No separate/secondary system — the detection lives in CIP's
real pipelines (audit rules engine, analysis/health, indexer, `cip doctor`).
**Hard constraint:** no embeddings anywhere. Every fix & check is AST / static-analysis /
index-introspection / config-diff — embedding-free by design (keeps `sync`/`search` fast).

---

## 0. Concept (why this shape)

The `09` log is mostly CIP *failing at its own job*: it missed import edges, reported "clean" when
sub-indexers silently died, forced health to a constant 80, and polluted its index with backups. So
"enhancing CIP to find these bugs" = **making CIP's core pipelines correct and self-aware**, then
verifying a normal CIP run on this repo now reports them. Each phase below does both:

- **FIX** — repair the defect in `lib/cipkg` (so CIP stops producing the wrong answer).
- **ENHANCE** — add a *core* CIP capability (a rule in `stack/rules.py`, a signal in
  `analysis`/`retrieve`, a `cip doctor` self-check, or an index-integrity probe) that flags this
  class. After the fix, the same run proves the fix worked (the signal moves from "broken" → "healthy").

**Honest limit (user-acknowledged):** `09` came from advanced LLM deep-mining, so we won't catch 100%.
Embedding-free static/structural checks cover the mechanical families (~54 findings); the ~6 that need
semantic/LLM judgement are listed in §8 as `manual`.

---

## 1. Package / command shape (core, not secondary)

Enhancements land in CIP's existing surfaces — no new `selfcheck` package:

```
lib/cipkg/
  stack/rules.py            # + new CODE-* / INDEX-* / AUDIT-* rules (Phase 0,1,3,4,5)
  analysis.py               # real quality_score + index-integrity signal (Phase 3,4)
  indexer.py                # resolve_import fix + tested_by fix (Phase 3)
  base.py / config paths    # config key reconciliation (Phase 2)
  doctor.py  (core)         # `cip doctor`: config/index self-consistency (Phase 2,3,5)
  cli.py / command_registry # wire fixes + `cip doctor` (Phase 0,1)
  retrieve.py               # caller/callee labels, graph decoration (Phase 5)
  daemon.py / maintain.py / workflow_engine.py / stack/audit.py  # behavioral fixes (Phase 4,5)
```

`cip doctor` is a **first-class CIP command** (like `cip gate`/`cip selftest`), not a side tool — it
hosts the self-consistency checks. `cip audit` hosts the code/index/audit rules. `cip analyze` hosts
the health-integrity signal. All embedding-free.

**Within-phase order (mandatory):** for every phase below, first **build & prove the detector** against
the *unfixed* code (it must fire on the broken repo), then **apply the fix last**. See §0 and §10.

---

## 2. Phase 0 — Undefined names & broken imports  (TRIVIAL — do first)

**FIX (defects — apply LAST, only after the detector is proven working):** add/repair the missing names & imports.
- BUG-005 / F-02 — `lancedb_store.py:55` add `import json`.
- F-06 — move `import json` above the `try` in `retrieve.py` (except tuple references it).
- F-34 — `cli.py` `from .selftest import selftest` → `run_selftest`.
- F-35 — wire `handle_deps_command` (re-export from `dependency_checker` into `cli`, or add dispatch).
- CORE-5 — 14 registry cards import nonexistent `cli.handle_*`; point them at real lib callables.
- F-13 — `workflow_engine.py` `from cipkg import audit/impact` → `from cipkg.stack import audit, impact`.
- F-20 — add `FilterEngine.rank` (or route through `ranking_engine.rank` then `filter`).
- F-31 — `session.py` import `runtime_adapters.broken` directly instead of `retrieve.runtime_adapters`.

**ENHANCE (core detector — build & prove FIRST, on the still-broken code):** add `CODE-UNDEFINED-NAME` + `CODE-MISSING-SYMBOL` rules to `stack/rules.py`
(also run as a `cip doctor` step): parse every indexed `.py` with `ast`/pyflakes; for each
`from X import Y`, verify `Y` exists in `X`. Emits a finding with `file:line` evidence.

**How CIP now identifies it (no embeddings):** `cip audit` (or `cip doctor`) on this repo reports
each undefined-name/missing-import as a `CODE-*` finding — same root causes as BUG-005/F-06/F-34/F-35/
CORE-5/F-13/F-20/F-31.

**Acceptance:** after fix, `cip doctor --static` is clean on these; before fix it listed ≥8 findings.

---

## 3. Phase 1 — Dead code & command-dispatch coverage  (LOW)

**FIX (defects — apply LAST, only after the detector is proven working):**
- F-16 — add the 21 missing subcommands to `dispatch_command` handlers (or wire real handlers):
  `coverage gate embedder embed-ping score routes refactors models dashboard admission dead circular
  blame migrations env logs metrics features deps api predict`.
- F-15 — align `analyze`/`rebuild` arity: registry calls `handle_X(root, ns)`; make handlers
  `(root, args)` (or special-case dispatch).
- Legacy-removal (per `09 §7`): delete `command_adapter.py`, `interactive.py`, `interactive_ui.py`,
  `help_system.py`, `watcher.py`, `dashboard_state.py`, `stack/selftest.py`, `ast_chunker.py`,
  `retrieval_bridge.py` (after extracting anything live). `repo_map.py`/`scip_indexer.py` deleted or
  wired (they're dead; AGENTS.md claims are unsupported — F-25).
- BUG-011/024 — drop `ast_aware_chunking` dead config path or wire `ast_chunker` (decide; currently a no-op).

**ENHANCE (core detector — build & prove FIRST, on the still-broken code):** add `CODE-DEAD-MODULE` (zero importers + no CLI/registry entry) and
`CODE-UNHANDLED-COMMAND` (argparse subparser with no dispatch dict entry) + `CODE-ARITY-MISMATCH`
rules. `cip audit` flags dead/unhandled modules in the indexed package.

**How CIP now identifies it:** `cip audit` lists `ast_chunker.py`, `retrieval_bridge.py`,
`command_adapter.py`, `interactive*.py`, `help_system.py`, `watcher.py`, `dashboard_state.py`,
`stack/selftest.py`, `repo_map.py`, `scip_indexer.py` as `CODE-DEAD-MODULE`; the 21 F-16 commands as
`CODE-UNHANDLED-COMMAND`.

**Acceptance:** post-cleanup, `CODE-DEAD-MODULE` only fires on genuinely-orphaned new code; `cip X`
no longer prints "unknown command" for the 21.

---

## 4. Phase 2 — Config consistency & drift  (LOW-MED)

**FIX (defects — apply LAST, only after the detector is proven working):**
- CORE-39 — reconcile `exclude_patterns`/`max_file_size` (TOML) ↔ `exclude`/`max_file_kb` (code):
  map in `load_config` or rename keys.
- CORE-40 / BUG-023 — set `config.default.toml [meta] schema_version` to the real DB value (4) or add
  a migration; stop claiming 11.
- CORE-10 — pick one daemon port (8765 or 8787) across config + code + registry.
- CORE-2 — add `[web] host/port/auto_manage_daemon` to defaults.
- CORE-42 — collapse `[perf]`/`[performance]` duplicates; mark legacy keys deprecated.
- F-11 — fix `base.load_config` repo-settings resolution: walk up from repo root to
  `<root>/repo-settings` (correct path), align the 3 import sites; surface profile load errors instead
  of bare `except: pass`.

**ENHANCE (core detector — build & prove FIRST, on the still-broken code):** `cip doctor --config` checks (embedding-free, pure TOML↔code diff):
- `CONFIG-SCHEMA-DRIFT` (declared vs live-DB `schema_version`).
- `CONFIG-KEY-UNDEFINED` (code reads `cfg[k]` absent from config) / `CONFIG-KEY-UNUSED` (reverse).
- `CONFIG-PORT-MISMATCH`, `CONFIG-PROFILE-SILENT-FAIL` (assert profile actually loads).
Surfaced in `doctor` and as analysis notes.

**How CIP now identifies it:** `cip doctor` reports `schema_version 11 vs 4`, the
`exclude_patterns`→`exclude` gap, the daemon port mismatch, and "repo-settings profile did not load".

**Acceptance:** `cip doctor --config` clean after fixes; before, lists CORE-39/40/10/2/42/11.

---

## 5. Phase 3 — Import-graph & tested_by integrity  (HIGH — the crown jewel)

**FIX (defects — highest-value index fix):**
- F-22 / F-42 — rewrite `indexer.resolve_import` relative branch: strip leading `.`, count levels,
  join; add `lib/` (and `src/`) prefix for absolute `cipkg.*` specs. Verified simulated:
  in-repo resolution 0.2% → **43.7%** (realistic target = 100% of in-repo imports).
- F-23 / F-42 — `build_tested_by`: resolve imports first (via fixed resolver); stop name-mention
  matching against `chunks.text`; gate to non-backup paths. Edge `dst` must be a real symbol id.
- F-42 — add `sync_global/backups/**` (and generic `backups/`) to `DEFAULT_EXCLUDES` so re-sync stops
  indexing 76% duplicate backup copies; re-sync.

**ENHANCE (core detector — build & prove FIRST, on the still-broken code):** add `INDEX-IMPORT-GRAPH-EMPTY` rule + an `analysis` index-integrity signal:
after sync, measure `%` of *in-repo* import specs that resolve; flag if `< 90%`. Add
`INDEX-TESTED-BY-NOISE`: flag `tested_by` edges whose `dst` is not a real symbol id. Both run on every
`cip audit` / `cip analyze`.

**How CIP now identifies it (no embeddings):** `cip audit` reports
`INDEX-IMPORT-GRAPH-EMPTY` (rate shown) and `INDEX-TESTED-BY-NOISE` (count). After the fix + re-sync,
the rate climbs past threshold and the noise count drops → the same run *proves* the fix.

**Acceptance:** pre-fix run shows ~0.2–43% resolution + thousands of noisy tested_by edges; post-fix
run shows healthy rate + near-zero noise; circular/orphan/layer rules (which depend on import edges)
start returning real, non-zero results instead of falsely "clean".

---

## 6. Phase 4 — Audit/health false-positives & silent no-ops  (HIGH)

**FIX (defects — apply LAST, only after the detector is proven working):**
- BUG-013 / F-01 / CORE-27 — `analysis._calculate_health_score`: stop forcing `quality_score=80`;
  compute from real audit-severity counts (or `gapfill.score()` with a reconciliation). Remove the
  `nextjs.list_findings` AttributeError swallow.
- BUG-015 — `stack/audit.audit()`: only close findings whose rule was actually executed (fix the
  `UPDATE … WHERE id NOT IN (seen)` query); never auto-mark ESLINT:/tauri/custom findings `fixed`.
- F-24 / F-41 — stop swallowing `nextjs.index_routes`/`prisma.index_stack` in `try/except: pass`;
  surface failed sub-indexers + traceback (explicit "prepare stack" step, ISSUE-106).
- BUG-014 — pin one `root` (ISSUE-103) and pass it to every lib call; `repo_health_report` uses
  `gapfill.coverage(root)`, never cwd-relative.
- CORE-30 — render "no symbols indexed — run sync" instead of a constant 50 ring on empty repos.
- F-42 — backup pollution fixed in Phase 3 (feeds honest counts).

**ENHANCE (core detector — build & prove FIRST, on the still-broken code):** `AUDIT-SILENT-NO-OP` rule (flags when an audit run produced 0 findings on a repo
known to contain stack code while sub-indexers didn't run), `AUDIT-FINDING-AUTO-CLOSED` integrity
check (flags findings flipped to `fixed` without their rule running), and a health-integrity note
("quality_score forced" badge removed once real). `cip analyze` shows honest health; `cip audit` shows
skipped-subindexer warnings as findings.

**How CIP now identifies it:** `cip audit` reports `AUDIT-SILENT-NO-OP` / `AUDIT-FINDING-AUTO-CLOSED`;
`cip analyze` shows a varying, real quality score (no longer constant 80) and an empty-repo "run sync"
state instead of 50.

**Acceptance:** quality_score varies per repo; findings trend no longer shows misleading "fixed";
stack repos show real TS/Prisma findings after `audit(refresh=True)` stops swallowing.

---

## 7. Phase 5 — Behavioral/job-safety & runtime/API contract  (HIGH)

**FIX (defects — apply LAST, only after the detector is proven working):**
- CORE-12/13/16/31/57 — run `daemon()`/`watch()`/`consolidation` in a managed thread/subprocess with a
  stop flag; web-managed daemon = separate process (never `taskkill /F /T` the console).
- CORE-15 / CORE-35 — `maintain.rebuild`/`git_index` become background jobs with progress + confirm;
  don't delete DB files inline.
- BUG-009 — widen `embed.get_embedder` fallback (`HF_HUB_OFFLINE` + uncached → hashing fallback, not
  just `ImportError`); job error state shows traceback. (Still embedding-aware, but the *fix* is
  guard logic, not embedding use.)
- F-14 — `RecoveryEngine` actually re-runs; `ErrorPatternLearning` reads real history. (Stub removal.)
- F-30 — `post_edit_hook` reads real `impact()` keys (`affected_count`/`risk`/`affected_files`); fix the
  `" callees"` typo; pass `root` (ISSUE-103).
- F-12 — `workflow_engine._run_pytest` parse: split on whitespace then `int(token.split(",")[0])`; count
  skips in total.
- F-21 — `web_server._api_search` (legacy) → `retrieve.search` (and delete legacy server per `09 §7`).
- CORE-20/BUG-008 — fix `retrieve.context()` caller/callee label swap (render edges by direction).
- CORE-22 — `graph()` returns decorated nodes (kind/path/severity) via bridge.
- CORE-28/29 — audit as background job + pagination (offset) for findings/quick_wins caps.
- BUG-016 — `custom_rules` exec: show "custom rules active" indicator + require a warning toggle before
  auditing an untrusted path.
- CORE-45/46 — verify reports "runner not found"; signals ingest uses stable hash ids (upsert).

**ENHANCE (core detector — build & prove FIRST, on the still-broken code):** `CODE-UNSAFE-PATTERN` rule (blocking loop on hot path, destructive `*.db` delete
without guard, broad swallow in critical sub-indexers, `exec_module` of repo code) + a `cip doctor
--runtime` probe verifying call sites resolve to real functions/attributes (F-21/F-30/F-31 family) and
that `search`/`graph` honor their documented contracts.

**How CIP now identifies it:** `cip doctor --runtime` lists the unsafe patterns + broken call sites;
`cip audit` flags `exec_module` of repo code (BUG-016); `cip analyze`/`search` expose correct labels,
decorated graph nodes, and honest job states.

**Acceptance:** `CODE-UNSAFE-PATTERN` fires on the pre-fix daemon/rebuild/git_index paths; post-fix it
goes quiet; `search`/`graph`/`post_edit_hook` return correct shapes.

---

## 8. Non-automatable (explicitly `manual` — needs LLM / deep judgement)

| Finding | Why not mechanically detectable (embedding-free) |
|---|---|
| F-08 / CORE-33 | "recall is not semantic" — needs judging semantic equivalence of query↔stored facts. |
| F-14 (partial) | recovery stubs *appear* to succeed — only observable by tracing that nothing re-runs. |
| F-26 (partial) | `command_adapter` fakes `success=True` without running — needs behavioral tracing. |
| CORE-53 | hardcoded confidences labeled "learning-adjusted" — wording/intent mismatch. |
| ISSUE-101..104 | design decisions (metric source of truth, trend integrity, embed UX) — product choice. |
| F-25 | "merge-note claimed complete but wasn't" — meta-doc accuracy, human review. |

These stay `identified=manual` in the tracker; we don't pretend coverage.

---

## 9. Tracker (living — fill in as we implement each phase)

Columns: **Phase** · **Finding (09 ref)** · **Fix done?** · **Core CIP enhancement** ·
**CIP identifies it now?** · **Assessment (interactive)**.

### Phase 0 — undefined names / broken imports
| Finding | Fix | Enhancement | Identified | Assessment |
|---|---|---|---|---|
| BUG-005 / F-02 | ☐ | CODE-UNDEFINED-NAME | ☐ | |
| F-06 | ☐ | CODE-UNDEFINED-NAME | ☐ | |
| F-09 | ☐ | CODE-UNDEFINED-NAME | ☐ | |
| F-34 | ☐ | CODE-MISSING-SYMBOL | ☐ | |
| F-35 | ☐ | CODE-MISSING-SYMBOL | ☐ | |
| CORE-5 | ☐ | CODE-MISSING-SYMBOL | ☐ | |
| F-13 | ☐ | CODE-MISSING-SYMBOL | ☐ | |
| F-20 | ☐ | CODE-MISSING-SYMBOL | ☐ | |
| F-31 | ☐ | CODE-MISSING-SYMBOL | ☐ | |

### Phase 1 — dead code / dispatch coverage
| Finding | Fix | Enhancement | Identified | Assessment |
|---|---|---|---|---|
| F-16 / CORE-9 | ☐ | CODE-UNHANDLED-COMMAND | ☐ | |
| F-15 | ☐ | CODE-ARITY-MISMATCH | ☐ | |
| BUG-011 / F-04 / F-24 / F-25 | ☐ | CODE-DEAD-MODULE | ☐ | |
| F-26 / F-27 / F-28 / F-29 / F-32 / F-36 / F-37 | ☐ | CODE-DEAD-MODULE | ☐ | |

### Phase 2 — config consistency
| Finding | Fix | Enhancement | Identified | Assessment |
|---|---|---|---|---|
| CORE-39 / CORE-42 | ☐ | CONFIG-KEY-UNDEFINED | ☐ | |
| CORE-40 / BUG-023 | ☐ | CONFIG-SCHEMA-DRIFT | ☐ | |
| CORE-10 | ☐ | CONFIG-PORT-MISMATCH | ☐ | |
| CORE-2 | ☐ | CONFIG-KEY-UNDEFINED | ☐ | |
| F-11 | ☐ | CONFIG-PROFILE-SILENT-FAIL | ☐ | |
| BUG-017 | ☐ | (note) | ☐ | |

### Phase 3 — import-graph / tested_by integrity
| Finding | Fix | Enhancement | Identified | Assessment |
|---|---|---|---|---|
| F-22 / F-42 | ☐ | INDEX-IMPORT-GRAPH-EMPTY | ☐ | |
| F-23 / F-42 | ☐ | INDEX-TESTED-BY-NOISE | ☐ | |
| F-42 (pollution) | ☐ | CONFIG-KEY/pollution | ☐ | |

### Phase 4 — audit/health false-positives
| Finding | Fix | Enhancement | Identified | Assessment |
|---|---|---|---|---|
| BUG-013 / F-01 / CORE-27 | ☐ | health-integrity signal | ☐ | |
| BUG-015 | ☐ | AUDIT-FINDING-AUTO-CLOSED | ☐ | |
| F-24 / F-41 | ☐ | AUDIT-SILENT-NO-OP | ☐ | |
| BUG-014 | ☐ | root-threading (ISSUE-103) | ☐ | |
| CORE-30 | ☐ | empty-repo state | ☐ | |

### Phase 5 — behavioral / runtime / API
| Finding | Fix | Enhancement | Identified | Assessment |
|---|---|---|---|---|
| CORE-12/13/16/31/57 | ☐ | CODE-UNSAFE-PATTERN | ☐ | |
| CORE-15 / CORE-35 | ☐ | CODE-UNSAFE-PATTERN | ☐ | |
| BUG-009 | ☐ | embed-fallback guard | ☐ | |
| F-14 | ☐ | (stub removal) | ☐ | |
| F-30 | ☐ | doctor --runtime | ☐ | |
| F-12 | ☐ | workflow parse | ☐ | |
| F-21 | ☐ | doctor --runtime | ☐ | |
| CORE-20/BUG-008 | ☐ | context labels | ☐ | |
| CORE-22 | ☐ | graph decoration | ☐ | |
| CORE-28/29 | ☐ | audit job/pagination | ☐ | |
| BUG-016 | ☐ | exec warning | ☐ | |
| CORE-45/46 | ☐ | verify/signals | ☐ | |

### Manual (stay `identified=manual`)
| Finding | Note |
|---|---|
| F-08 / CORE-33 | semantic recall |
| F-14 (partial) | recovery stubs |
| F-26 (partial) | fake success |
| CORE-53 | hardcoded confidences |
| ISSUE-101..104 | design decisions |
| F-25 | doc hygiene |

---

## 10. How we assess interactively (the loop — DETECT FIRST, FIX LAST)

For each cluster / phase *N*, in this exact order:

1. **Design + build the detector (core enhancement).** Add the rule/signal/`doctor` step to CIP's real
   pipeline — embedding-free. Do **not** touch the buggy code yet.
2. **Test the detector against the still-broken repo.** Run the normal CIP command
   (`cip doctor` / `cip audit` / `cip analyze`) on this repo **with the bug unfixed**.
3. **Iterate until it identifies the specific bug.** Keep adjusting the detector (thresholds, evidence
   strings, target set) until it fires on exactly the finding we're working on (e.g. `cip doctor`
   reports `lancedb_store.py:55 json` for BUG-005). This is the proof the detector works — it has real
   broken code to catch.
4. **Confirm working, THEN fix.** Only after step 3 shows `yes` do we apply the **FIX** in `lib/cipkg`.
   (If we fixed first, the evidence would be gone and we could not tell the detector worked.)
5. **Re-run to confirm the flip.** Run CIP again: the signal should now read healthy (rate past
   threshold / no undefined names / no auto-closed findings). This proves both the fix and the detector.
6. Fill the Phase *N* tracker: `Detector proven=yes`, `Fix done=yes`, `CIP identifies it now=yes`
   (pre-fix it fired; post-fix it's clean), one-line `Assessment`.
7. Move to the next cluster. Stop when Phase 5 done or marginal value drops.

**Why this order:** the whole point is that CIP should *find its own bugs*. A detector validated only
after the bug is gone proves nothing. Validating on broken code, then fixing, gives a clean
before/after that demonstrates the enhancement is real.

**Definition of done:** every automatable `09` finding has a tracker row; every detector is proven to
fire on the unfixed code; every fix is then landed and confirmed by a clean re-run; manual findings are
explicitly tagged `manual`.
