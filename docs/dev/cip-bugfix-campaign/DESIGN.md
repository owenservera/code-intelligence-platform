# DESIGN — CIP Detection System & Fix Architecture (v2, upgraded)

**Folder:** `docs/dev/cip-bugfix-campaign/` · **Date:** 2026-08-16
**Companion:** `10-selfcheck-enhancement-plan.md` (the plan v2), `09-bugs-and-issues.md` (CIP's own findings — **untouched**),
`PROFILE.cip.md` (CIP's wiring + per-language instruments).
**Principle:** enhance CIP's *product* core so a normal CIP run identifies the `09` bugs — and, because
these surfaces are the product, the same detections then apply to **any repo CIP indexes, any language**
(RUNBOOK §0). **No embeddings** anywhere — AST / static-analysis / index-introspection / config-diff only.
**v2 upgrades:** precision gating, leverage-first sequencing, systemic foundation pass (Phase S),
class-workflow for dead/manual items, regression-locked detectors, numeric health KPIs, machinery-debt guard.

---

## 0. Product framing (read before anything else)

CIP = general polyglot code-indexing + issue-detection **system**. This DESIGN makes CIP's *own* surfaces
correct and self-aware by turning the `09` bugs into (a) product-wide fixes in `lib/cipkg/**` and (b)
product-wide detection features that `cip audit` / `cip analyze` / `cip doctor` / `cip gate` carry into
every repo. The sections below describe families (S1–S5, F0–F5) as **universal failure archetypes**;
each archetype is instrumented per language (extension-dispatched) per `PROFILE.cip.md` §2. `tests/detectors/`
is CIP's self-regression (dogfood) suite: fires-on-broken / silent-on-clean, used to prove each feature
against CIP's own bug evidence (`09`) before the fix flips it.

---

## 1. Where detection lives (core, not secondary)

All detectors are wired into CIP's real surfaces so `cip audit` / `cip analyze` / `cip doctor` /
`cip sync` naturally surface findings:

| Surface | Hosts | Phases |
|---|---|---|
| `lib/cipkg/stack/rules.py` | `CODE-*` (dead code, undefined name, unsafe pattern, unhandled command, arity), `INDEX-*` (import-resolution, tested-by noise, backup pollution), `AUDIT-*` (silent no-op, auto-closed) | 0,1,3,4,5 |
| `lib/cipkg/analysis.py` | health-integrity signal (real quality score, empty-repo state, index-integrity) | 3,4 |
| `lib/cipkg/doctor.py` (core cmd) | `CONFIG-*` self-consistency + runtime/API-contract probes (**built first in Phase S**, then extended) | S,2,5 |
| `lib/cipkg/indexer.py` | `resolve_import` fix + `tested_by` fix + backup-exclude | 3 |
| `lib/cipkg/base.py` + config paths | config key reconciliation, schema-version, port, repo-settings resolution | S,2 |
| `lib/cipkg/retrieve.py` | caller/callee label fix, graph decoration, auto-embed → background | 5 |
| `lib/cipkg/daemon.py` `maintain.py` `workflow_engine.py` `stack/audit.py` | behavioral fixes (threading, confirm, swallow surfacing, parse) | 4,5 |
| `tests/detectors/` (**new**) | 2-case regression tests per family (fires-on-broken / silent-on-clean) | all |
| `tests/data/clean_ref/` (**new**) | pinned clean reference repo + fixture Twin used for precision proof | all |
| `docs/dev/cip-bugfix-campaign/LEDGER.md` (**new**) | machinery budget + numeric KPIs + precision ledger | all |

`cip doctor` is a **first-class CIP command** (like `cip gate`/`cip selftest`) — not a side tool.

---

## 2. Detection families (each = a CIP product rule/signal family, regression-locked)

Each family is a *mechanism* shipped inside CIP's surfaces (§1) and instrumented per language by
extension dispatch (`PROFILE.cip.md` §2). The specific per-stack detail below is the Python instance;
other languages re-use the same family rule with their own instrument.

- **S SYSTEMIC (foundation, Phase S)** — the 4 root anti-patterns, fixed as *mechanisms*, not per-finding.
  - **S1** no-bare-`except: pass` in `lib/cipkg` (must `log_swallowed()` or surface; broad swallows banned in critical sub-indexers). Retires F-24/F-41, CORE-41, CORE-52, BUG-016-indicator, F-11, BUG-009-widen.
  - **S2** static lint gate (`pyflakes`/ruff) in CI + `cip gate` + `tests/detectors/s2_static_lint_gate_test.py`.
    Retires F-09, BUG-005/F-02. **(not F-06** — pyflakes treats the in-`try` module import as a binding, so
    the runtime-order NameError is invisible to static lint; F-06 moves to S3 runtime probes).
  - **S3** runtime signature/attribute conformance suite (`inspect` + import-graph over `lib/cipkg`): asserts every parsed/registered subcommand ↔ dispatch dict ↔ handler arity; every referenced `lib.X` attribute exists; every CLI handler is callable with the args the registry passes. Retires BUG-001/F-03, F-13, F-15, F-16, F-17, F-20, F-21, F-26, F-30, F-31, F-32, F-34, F-35.
  - **S4** config-schema loader suite: `load_config` must read every key core reads; TOML keys must equal code-read keys (map or rename); surfaced live-DB `schema_version`. Retires CORE-2, CORE-10, CORE-39, CORE-40/BUG-023, CORE-42.
  - **S5** `cip doctor` skeleton hosting `CONFIG-*` + `doctor --runtime` probes — built first as the platform, extended in Phases 2/5.
- **F0 STATIC (Phase 0)** — `ast`/pyflakes over indexed `.py`: undefined names (F821), missing import
  targets, attribute-missing. S2 is the CI gate; the F0 **rule in `rules.py`** is the continuous
  `audit`/`doctor` surface. → `CODE-UNDEFINED-NAME`, `CODE-MISSING-SYMBOL`.
- **F1 REACH (Phase 1)** — importer graph: zero-importer modules (dead); argparse-subparser vs dispatch
  dict diff; arity mismatch between caller and callee. → `CODE-DEAD-MODULE`, `CODE-UNHANDLED-COMMAND`,
  `CODE-ARITY-MISMATCH`. Class-workflow: prove on 2–3 exemplars, bulk-sweep the rest (no per-instance ceremony).
- **F3 INDEX (Phase 3 — crown jewel)** — after sync: **in-repo-scoped** import-resolution rate (denominator
  = in-repo import specs only; stdlib/third-party excluded), validated `tested_by` edge `dst` is a real
  symbol id, backup-pollution %. → `INDEX-IMPORT-RESOLUTION`, `INDEX-TESTED-BY-NOISE`, `INDEX-BACKUP-POLLUTION`.
  Threshold: **100% of in-repo** (blanket 90% is wrong — external imports dominate; see F-42).
- **F4 AUDIT (Phase 4)** — flag silent-no-op audits (0 findings on a stack repo w/ sub-indexers skipped);
  flag findings auto-flipped to `fixed`; honest health (no forced 80, no fake 50). → `AUDIT-SILENT-NO-OP`,
  `AUDIT-FINDING-AUTO-CLOSED`, health-integrity note.
- **F5 BEHAVIOR (Phase 5)** — unsafe patterns: blocking loop on hot path, destructive `*.db` delete w/o
  guard, broad swallow in critical sub-indexer, `exec_module` of repo code; runtime/API contract probes
  (call sites resolve to real symbols). → `CODE-UNSAFE-PATTERN` + `doctor --runtime`.

---

## 3. Upgraded validation loop (per family — RECALL **and** PRECISION, regression-locked)

For every automatable family, in this exact order:

1. **Design the detector** (family rule / doctor step / indexer probe).
2. **RECALL proof (fires on broken):** run the normal CIP command on this repo **with the bug unfixed**;
   it must list each instance's evidence (`file:line` from `09`). Iterate until it does.
3. **PRECISION proof (silent on clean) — MANDATORY (v2):** run the same detector on the pinned clean
   reference repo (`tests/data/clean_ref/`) and on the broader indexed corpus. Gate: **0 false positives**
   in class — or a documented tolerable-FP set with an explicit mitigation. The campaign's subject is
   false-positive noise (F-22/F-23 → QA-UNTESTED-HOT); a detector validated for recall only is not validated.
4. **REGRESSION-LOCK (v2):** ship the 2 pytest cases (`tests/detectors/<family>_test.py`):
   `broken-fixture fires` / `clean-fixture silent`. Record in LEDGER.
5. **KPI baseline (v2):** record the phase's numeric before-values on the reference repo (LEDGER).
6. **Fix instances** (deps first, minimal change; shared root causes share one folder).
7. **Re-run:** signal flips healthy **and** FP stays 0; KPI after-values recorded. This proves both fix + detector.
8. **Machinery ledger (v2):** count net-new rules/steps/LOB against the phase budget (see §5). If over cap,
   consolidate before proceeding.
9. Update TRACKER + LEDGER.

**Why this order:** recall-only validation proves nothing (see the QA-UNTESTED-HOT cautionary tale).
Detectors tuned only on the 51 known lines overfit to this repo; precision proof on a clean reference
makes the signal trustworthy repo-wide.

---

## 4. Output contract (every detector emits)

```python
CheckFinding(
    rule="CODE-UNDEFINED-NAME",     # or INDEX-/AUDIT-/CONFIG-/KS
    finding_ref="BUG-005",          # links back to 09
    severity="P1",
    title="json used without import",
    evidence="lib/cipkg/lancedb_store.py:55 json.dumps(meta)",
    recommendation="add `import json`",
)
```
Rendered by `cip audit`/`cip doctor` (terminal, severity-colored) and by `cip analyze` (health note).
JSON also emitted for the dashboard/console. Detectors additionally carry a `kpi`/`fp_guard` reference
to their LEDGER row (numeric threshold + tolerated-FP list).

---

## 5. Machinery-debt guard (v2)

A bug-fix campaign must not become a new source of machinery (the tool's core disease is excess dead
machinery — F-04/F-25/F-26). Per family:

| Family | Max new rules | Max new doctor steps | Consolidate into |
|---|---|---|---|
| F0 STATIC | 2 | 1 (`--static`) | `CODE-UNDEFINED-NAME` + `CODE-MISSING-SYMBOL` |
| F1 REACH | 3 | 0 | `CODE-DEAD-MODULE`/`UNHANDLED-COMMAND`/`ARITY-MISMATCH` |
| F3 INDEX | 3 | 1 | the 3 `INDEX-*` signals in one doctor step |
| F4 AUDIT | 2 + 1 note | 0 | `AUDIT-*` rules + health note |
| F5 BEHAVIOR | 1 | 1 (`--runtime`) | `CODE-UNSAFE-PATTERN` + probes |
| S/CONFIG | 0 | 3 (`--config` + skeleton) | doctor steps only |

Budget tracked in LEDGER; exceeding a cap forces consolidation before more work.

---

## 6. Phase S — Systemic foundation (v2, done FIRST)

The 4 root anti-patterns (bare-except swallow, dead-code accumulation, stale-signature drift, config-key
drift) cause most of the 51 findings. Unchanged-objective, higher-leverage) first mechanical pass:

1. **S1** no-bare-except discipline.
2. **S2** static lint in CI (`cip gate`).
3. **S3** runtime signature-conformance suite (`tests/detectors/s3_conformance_test.py`).
4. **S4** config-schema loader suite (`tests/detectors/s4_config_schema_test.py`).
5. **S5** `cip doctor` skeleton (`CONFIG-*` + probe host).

Each is a **mechanism pass** — no per-instance `detection.md`/`fix-design.md` ceremony; instances each
mechanism retires are closed by the mechanism and recorded in TRACKER (`retired-by-S#`).

---

## 7. Grouping by ceremony (v2 — what gets full docs, what doesn't)

| Level | Findings | Ceremony |
|---|---|---|
| **systemic** | retired by S1..S5 | none — mechanism pass; TRACKER `retired-by-S#` |
| **high-value instance** | Phase 3 (F-22/F-42/F-23), Phase 4 (BUG-013/F-01/CORE-27, BUG-015, F-24/F-41, BUG-014, CORE-30) | full `detection.md` + `fix-design.md` per root cause (shared folder when same root) |
| **instance (static/config)** | Phase 0, Phase 2 rows | `detection.md` + `fix-design.md`, shared folder by root cause |
| **delete / legacy** | Phase 1 dead+dispatch, F-38/F-39, F-21 | **no docs** — prove family detector on 2–3 exemplars, bulk-sweep; one-row disposition in TRACKER |
| **manual** | M1..M4 | single short note; detector documented as not automatable |

---

## 8. Non-automatable (manual)

`F-08`/`CORE-33` (semantic recall), `F-14` partial (recovery stubs), `F-26` partial (fake success),
`CORE-53` (hardcoded confidences), `ISSUE-101..104` (design decisions), `F-25` (doc hygiene).
Single-note rows; no ceremony; done last.