# LEDGER — Machinery Budget, Numeric KPIs, Precision Ledger (v2, NEW)

**Folder:** `docs/dev/cip-bugfix-campaign/` · **Date:** 2026-08-16
**Purpose:** single source of *numbers* for the campaign: machinery-debt budget (DESIGN §5), numeric
KPIs per phase (before/after on the reference repo), and the precision (false-positive) ledger for every
detector. TRACKER tracks status; LEDGER tracks magnitude.
**Scope:** CIP's own dogfood ledger (RUNBOOK §0). The machinery budget measures CIP-product machinery
(rules/doctor-steps) shared with every future repo; precision rules are product gates. A different repo
CIP indexes keeps its own numbers here if audited independently.
**Validation pair:** BROKEN = CIP itself (pre-fix, pinned). CLEAN = `tests/data/clean_ref/` (known-clean
fixture repo). A detector is proven only when it fires on BROKEN and is silent on CLEAN.

---

## 1. Machinery budget (net-new surface per family — DESIGN §5)

| Family | Budget | Used | Status |
|---|---|---|---|
| S / CONFIG | rules 0 · doctor steps 3 | 3 (S5: --static/--config/--runtime scopes; CONFIG-FILE-UNPARSEABLE added as a self-check, not a rules.py rule). S3/S4 = tests/detectors suites only — 0 product LOB. | ☑ within |
| F0 STATIC | rules 2 · doctor 1 | — | ☐ within |
| F1 REACH | rules 3 · doctor 0 | — | ☐ within |
| F3 INDEX | rules 3 · doctor 1 | +s6 detector module, +14 index tests, `_is_backup_path`/gatekeeper segment predicates, `build_tested_by` rewrite (F-23) — tiny, within | ☑ within |
| F4 AUDIT | rules 2 + 1 note · doctor 0 | +s6_audit_integrity module, +8 tests, `enabled_rules()` shared helper, `failed_indexers` surfacing — tiny, within | ☑ within |
| F5 BEHAVIOR | rules 1 · doctor 1 | — | ☐ within |
| tests/detectors | +1 pytest file per family | — | ☐ within |
| **Total net-new LOB** | target ≤ 1,200 | — | ☐ within |

Rule: exceeding a budget forces consolidation (merge family rules) before more work.

---

## 2. Numeric KPIs (reference repo = this index, re-synced; record before/after per phase)

| KPI | Detector / phase | BROKEN value (baseline) | Target after fix | After | Status |
|---|---|---|---|---|---|
| in-repo import resolution % | INDEX-IMPORT-RESOLUTION (Ph3) | ~0% (0/234; 43.7% pre-external-cleanup) | 100% of in-repo | **99.79% (486/487)** — sole miss is the genuinely-broken `cli.py .ingest` (dead ref, Ph0 fix targeted) | ☑ |
| total import resolution % | INDEX-IMPORT-RESOLUTION (Ph3) | ~0.2% (see F-42 correction) | report-only (external dominates) | report-only | ☑ |
| `tested_by` noise count (dst not symbol id) | INDEX-TESTED-BY-NOISE (Ph3) | 4,462 (pre-re-sync); noise after re-sync | ≤10 | **159 total, 0 noise** (all src = real symbol id, non-backup) | ☑ |
| backup/duplicate % of indexed files | INDEX-BACKUP-POLLUTION (Ph3) | 76% (575/753) | 0% | **0.0%** — files 753→156 (575 backup copies + stale rows pruned) | ☑ |
| QA-UNTESTED-HOT findings (spurious) | Ph3/Ph4 | 30 (cap, all noise) | 0 meaningful-relative | | |
| quality_score variance across 2 repos | health-integrity (Ph4) | constant 80 (fallback on nonexistent nextjs.list_findings) | varies; no forced fallback | **100 at 0 findings (live), penalized by real critical/high counts; live health score 55.3 → 61.3 (+6.0 = 0.3×20)** | ☑ |
| findings auto-flipped to `fixed` per audit | AUDIT-FINDING-AUTO-CLOSED (Ph4) | ESLINT:/custom/tauri rows retired by every stack audit | 0 | **0 wrong flips — sweep scoped to rules that RAN (`rule IN enabled_ids`); ESLINT row survives (RECALL test); stale row of a run rule still closes (PRECISION)** | ☑ |
| silent-no-op audits (0 findings, sub-indexers skipped) | AUDIT-SILENT-NO-OP (Ph4) | nextjs.prisma indexer failures swallowed by log_swallowed | 0 | **0 silent — result carries `failed_indexers` (stub-raise → 2 surfaced, not swallowed); clean audit reports `[]`** | ☑ |
| empty-repo health ring | CORE-30 (Ph4) | renders literal 50 | renders "run sync" state | **derived ring (60 at 0 findings; lower with a critical) — never 50, still finding-sensitive** | ☑ |
| `cip X` "unknown command" count | S3 / Ph1 | 21 | 0 | | |
| clipboard-broken registry cards (never-fire errors) | S3 (F-15/F-17/CORE-5) | 16 | 0 | | |
| conformance findings on lib/cipkg (S3 engine, all CODE-* rules) | S3 | 53 (21 UNDISPATCHED, 1 MISROUTED, 2 ARITY, 1 MISSING-MODULE, 28 MISSING-SYMBOL) | 0 (as fixes land Ph0/1/3) | | |
| broad silent-swallow handlers in lib/cipkg | S1 swallow-scanner (AST) | 83 (pre-fix, incl. F-24/F-41, F-11, CORE-52 evidence) | evidence sites fixed; rest guarded by doctor --static (S5), decrement as Ph4/5 land | 79 | |
| undefined-name / unused-import findings | S2 / Ph0 | 103 findings on lib/cipkg (pyflakes 3.4.0, 5 undefined-name incl. BUG-005 + retrieval_bridge F821×4) | 0 (gate); cleanup lands Phase 0 rows 9/11 | | |
| pytest baseline (backend) | F-10/F-42B watch | 10 failed / 90 passed / 1 skipped / 30 errors | never regresses | | |
| sys.path / repo-settings profile loads | CONFIG-PROFILE-SILENT-FAIL (Ph2) | F-11: profile={} always | profile loads (external_search active) | | |
| daemon port truth (config vs code) | CONFIG-PORT-MISMATCH (Ph2) | 8765 vs 8787 | single source | | |
| config.default.toml parseable by loader | CONFIG-FILE-UNPARSEABLE (S4/S5, new find) | invalid TOML — `[analysis] health_weights = {` multi-line inline table (line 151), so the shipped defaults never load (only v2 + hardcoded fallback apply). S4 locks: tomllib.loads raises TOMLDecodeError (flips clean in Ph2); loader returns (cfg, err) immediately, never falls to v2 | parseable via tomllib; defaults actually apply | | S4 test locks invariant + no-fall-through |
| net-new machinery LOB | §1 | 0 | ≤1,200 | | |

Record after-values as fixes land. "report-only" rows track transparency, not a target.

---

## 3. Precision ledger (mandatory per detector — DESIGN §3.3 / RUNBOOK §4.3)

| Detector / family | Fires on BROKEN (recall) | Silent on CLEAN (FP count) | Tolerated FP + mitigation | Status |
|---|---|---|---|---|
| SILENT-SWALLOW (S1 — AST broadcast with no surfacing) | ☑ (audit.py 19/21, base.py 144, suggestion_engine.py 657) | FP=0 (sample.py + good_handling.py) | | S1 test gates both; fixes flipped evidence clean |
| CODE-UNDEFINED-NAME (F0) | ☑ | FP=0 (clean_ref sample.py) | | doc: DESIGN §2 S2 |
| CODE-MISSING-SYMBOL (F0) | ☑ | FP=0 (clean_ref sample.py) | | S2 family test gates both |
| CODE-DEAD-MODULE (F1) | ☐ | FP=0 (exemplars) | | |
| CODE-UNHANDLED-COMMAND (F1) + CODE-MISROUTED-COMMAND + CODE-ARITY-MISMATCH + CODE-MISSING-SYMBOL + CODE-MISSING-MODULE (S3 conformance AST; covers F-13/15/16/17/20/21/31/32/34/35) | ☑ (53 total on lib/cipkg: 21 UNHANDLED, 1 MISROUTED, 2 ARITY, 1 MISSING-MODULE, 28 MISSING-SYMBOL) | FP=0 (synthetic clean cli pkg + clean_ref) | | S3 test gates recall + precision |
| INDEX-IMPORT-RESOLUTION (F3) | ☑ (fires on pre-fix: resolve_import returned None for multi-seg `.stack.common`/`.memory.*` and emitted `lib/cipkg/.base.py` artifacts; unit cases now assert correct targets) | FP=0 (only `cli.py .ingest` unresolved — genuinely-broken module, not a resolver artifact; synthetic clean pkg resolves 100%) | report-only total metric | ☑ locked in `phase3_index_test.py` |
| INDEX-TESTED-BY-NOISE (F3) | ☑ (fires on broken edges: backup-src + missing-src counted) | FP=0 (clean synthetic DB: real tested_by silent) | | ☑ locked |
| INDEX-BACKUP-POLLUTION (F3) | ☑ (detector counts backup-segment files when present; synthetic backup tree the OLD scanner indexed now stays clean — flip) | FP=0 (segment-aware: test filenames *containing* `backup_` are NOT flagged; sync_global source files remain indexed) | | ☑ locked at both surfaces (base.iter_files + gatekeeper `_scan`/`_decide`) |
| AUDIT-FINDING-AUTO-CLOSED (F4) | ☑ (8/8 suite: ESLINT row survives auto-close when its rule didn't run; stale row of a RAN rule still closes) | FP=0 (clean audit root: no findings seeded → sweep no-op; clean_ref untouched) | | ☑ locked in `phase4_audit_test.py` |
| AUDIT-SILENT-NO-OP (F4) | ☑ (stub sub-indexer raises → `failed_indexers` carries 2 names; audits never report success under partial failure) | FP=0 (fully-functioning nest → `failed_indexers == []`, report clean) | | ☑ locked in `phase4_audit_test.py` |
| health-integrity note (F4) | ☑ (no-quality-fallback fixture → real sev counts drive score; empty repo ring ≠ 50 and reacts to one critical) | FP=0 (bogus `list_findings` path removed — no AttributeError swallow; clean repo derives 100/60 without forcing) | | ☑ locked in `phase4_audit_test.py` |
| CONFIG-SCHEMA-DRIFT / KEY-UNUSED / PORT / PROFILE-SILENT-FAIL + FILE-UNPARSEABLE (S4/S5 CONFIG-*) | ☑ (all 7 rules fire on this repo; `cip doctor --config` total=8 fresh findings; S4 locks per-rule refs CORE-2/10/39/40/42 + F-11 + FILE-UNPARSEABLE evidence) | FP=0 (reconciled virtual config + per-rule surgical: one-missing-anatomy → only its rule; port==code-scan silent; schema==store silent) | | S4 + S5 tests gate both directions; S4 loader test proves no v2 fall-through on decode error |
| CODE-UNSAFE-PATTERN (F5) | ☐ | FP=0 | | |
| doctor --runtime probes (S3/S5) | ☑ (only measured claims; RUNTIME-DAEMON-DOWN fires, no fake ok) | FP=0 (probe failure surfaces as RUNTIME-PROBE-FAILED, never silence) | | S5 test asserts evidence required | |

A record with recall=yes and FP>0 + mitigation=set gates to "ok" only after mitigation is described.

---

## 4. Rules of the ledger

1. **Everyone updates it.** TRACKER marks status; LEDGER carries the numbers — keep them in step.
2. **Precision is a gate, not a note.** FP>0 without a written mitigation = detector not yet validated.
3. **KPIs are pinned to the reference repo**, not ad-hoc runs.
4. **Machinery is measured.** The campaign's own disease is excess machinery — stay within budget §1.