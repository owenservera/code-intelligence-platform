# TRACKER — CIP Bug-Fix & Detection Campaign (v2, upgraded)

**Folder:** `docs/dev/cip-bugfix-campaign/` · **Date:** 2026-08-16
**Scope:** CIP's dogfood instance (RUNBOOK §0, `PROFILE.cip.md`) — the fixes and detectors tracked here
are CIP-product-wide; the rows are the `09` evidence this pass proves them against.
**Source:** `09-bugs-and-issues.md` (intact), `10-selfcheck-enhancement-plan.md` (v2), `DEPENDENCIES.md` (v2), `RUNBOOK.md` (v2)
**Status vocab:** Detector `todo → designed → proven(b+c) → regression-locked → clean-after-fix`; Precision `todo → ok → gated`; Fix `todo → designed → implemented → verified`; Level `systemic|instance|delete|manual`.
Work in phase order (Phase S → 3 → 4 → 0 → 1 → 2 → 5 → manual). Update after each finding. Numbers live in `LEDGER.md`.

---

## Phase S — Systemic foundation (mechanism pass — done FIRST, no instance docs)

| Mechanism | What it is | Retires (09 refs) | Land | Verified |
|---|---|---|---|---|
| S1 | no-bare-except discipline (log_swallowed or surface) — swallow-scanner gate | F-24, F-41, CORE-41, CORE-52, F-11, BUG-009, BUG-016 | ☑ | ☑ |
| S2 | static-lint gate (pyflakes/ruff) in CI + `cip gate` | F-09, BUG-005/F-02 (F-06 → S3: pyflakes blind) | ☑ | ☑ |
| S3 | signature/attribute conformance suite | BUG-001/F-03, F-13, F-15, F-16, F-17, F-20, F-21, F-26, F-30, F-31, F-32, F-34, F-35 | ☑ | ☑ |
| S4 | config-schema loader suite (TOML↔code keys, live schema_version) | CORE-2, CORE-10, CORE-39, CORE-40/BUG-023, CORE-42 | ☑ | ☑ |
| S5 | `cip doctor` skeleton (CONFIG-* + probe hosts) | host for Phases 2/5 | ☑ | ☑ |

## Phase 3 — Index integrity / import graph (rank 1–3, front-loaded crown jewel)

Phase 3 after-values (live `.cip/data/index.db`, rebuilt 2026-08-16 06:xx):
`files` **753 → 156** (575 `sync_global/backups/backup_*` copies pruned) ·
backup pollution **76.4% → 0.0%** (segment-aware gate) · `imports` edges **12 → 260**
(F-22 resolves in-repo) · in-repo resolution rate **0.2% → 99.79%**
(only genuinely-broken `cli.py .ingest` unresolved) · `tested_by` edges
**4462 → 159**, noise **4462 → 0** (F-23 drops name-mention heuristic).
Suite: `tests/detectors/phase3_index_test.py` (14 tests) + `s6_index_integrity.py`.

| Rank | Finding | Folder | Level | Detector proven(b+c) | Precision | Locked | Fix | KPI | Assessment |
|---|---|---|---|---|---|---|---|---|---|
| 1 | F-22 | bugs/F-22 | instance | ☑ INDEX-IMPORT-RESOLUTION | ☑ 99.79% / only cli.ingest | ☑ | ☑ | imports 12→260 | foundation |
| 2 | F-42 | bugs/F-42 | instance | ☑ INDEX-BACKUP-POLLUTION | ☑ 0 FP / segment-aware | ☑ | ☑ | 575→0 files, 76.4%→0 | gatekeeper `_scan`/`_decide` + base F-42 |
| 3 | F-23 | bugs/F-23 | instance | ☑ INDEX-TESTED-BY-NOISE | ☑ clean DB silent | ☑ | ☑ | 4462→159, noise 0 | dep F-22 |

## Phase 4 — Audit/health honesty (rank 4–8, dashboard-critical) **☑ LANDED**

| Rank | Finding | Folder | Level | Detector proven(b+c) | Precision | Locked | Fix | KPI | Assessment |
|---|---|---|---|---|---|---|---|---|---|
| 4 | BUG-013 / F-01 / CORE-27 | bugs/BUG-013 | instance | ☑ | ☑ | ☑ | ☑ | `quality_score` 80→100(+punishment by real sev counts); live health 55.3→61.3 | `_open_findings()` reads the findings table (nextjs.list_findings never existed) |
| 5 | BUG-015 | bugs/BUG-015 | instance | ☑ | ☑ | ☑ | ☑ | findings auto-flipped to `fixed` = 0 (sweep scoped to run rules) | ESLINT:/custom/tauri rows survive every audit |
| 6 | F-24 / F-41 | bugs/F-24 | instance | ☑ | ☑ | ☑ | ☑ | silent-no-op audits = 0 (failed_indexers surfaced) | result carries `failed_indexers`; no bare swallow |
| 7 | BUG-014 | bugs/BUG-014 | instance | ☑ | ☑ | ☑ | ☑ | coverage reads requested root (3≠cwd live 1699 flips clean) | `gapfill.coverage(root)` threaded |
| 8 | CORE-30 | bugs/CORE-30 | instance | ☑ | ☑ | ☑ | ☑ | empty-repo ring != 50, still finding-sensitive | literal 50 early-return removed |

## Phase 0 — Static undefined-name / broken imports (rank 9–17; mostly retired by S2/S3)

| Rank | Finding | Folder | Level | Detector proven(b+c) | Precision | Locked | Fix | KPI | Assessment |
|---|---|---|---|---|---|---|---|---|---|
| 9 | BUG-005 / F-02 | bugs/BUG-005 | instance | ☑ | ☑ | ☑ | ☑ | | dep S2 — fixed Ph0 |
| 10 | F-06 | bugs/F-06 | instance | ☑ | ☑ | ☑ | ☑ | | dep S2 — fixed Ph0 |
| 11 | F-09 | bugs/F-09 | instance | ☑ | ☑ | ☑ | ☑ | | retired-by-S2 — targeted scrub Ph0 |
| 12 | F-34 | bugs/F-34 | instance | ☑ | ☑ | ☑ | ☑ | | retired-by-S3 — fixed Ph0 |
| 13 | F-35 | bugs/F-35 | instance | ☑ | ☑ | ☑ | ☑ | | retired-by-S3 — fixed Ph0 |
| 14 | CORE-5 | bugs/CORE-5 | instance | ☑ | ☑ | ☑ | ☑ | | dep F-34,F-35 (S3) — fixed Ph0 |
| 15 | F-13 | bugs/F-13 | instance | ☑ | ☑ | ☑ | ☑ | | retired-by-S3 — fixed Ph0 |
| 16 | F-20 | bugs/F-20 | instance | ☑ | ☑ | ☑ | ☑ | | retired-by-S3 — fixed Ph0 |
| 17 | F-31 | bugs/F-31 | instance | ☑ | ☑ | ☑ | ☑ | | retired-by-S3 — fixed Ph0 |

## Phase 1 — Dead code / dispatch coverage (rank 18–31; class-workflow, deletions skip docs)

| Rank | Finding | Folder | Level | Detector proven(b+c) | Precision | Locked | Fix | KPI | Assessment |
|---|---|---|---|---|---|---|---|---|---|
| 18 | F-16 | bugs/F-16 | instance | ☑ | ☑ | ☑ | ☑ | 21→20 wired + `dashboard` TUI pending deletion | fixed Ph1 — 20/21 dispatched; `dashboard` legacy TUI = deletion target |
| 19 | F-15 | bugs/F-15 | instance | ☑ | ☑ | ☑ | ☑ | analyze/rebuild run | fixed Ph1 — arity aligned to `(root, args)` |
| 20 | F-25 (line-count/doc corrections) | bugs/F-25 | instance | | | | | | note-only |
| 21 | BUG-011 / F-04 | bugs/BUG-011 | delete | | | | | | family-sweep |
| 22 | F-26 | bugs/F-26 | delete | | | | | | family-sweep |
| 23 | F-27 | bugs/F-27 | delete | | | | | | family-sweep |
| 24 | F-28 | bugs/F-28 | delete | | | | | | family-sweep |
| 25 | F-29 | bugs/F-29 | delete | | | | | | family-sweep |
| 26 | F-32 | bugs/F-32 | delete | | | | | | family-sweep |
| 27 | F-38 (extract `briefing()`) | bugs/F-38 | delete | | | | | | move-leaf |
| 28 | F-36 | bugs/F-36 | delete | | | | | | family-sweep |
| 29 | F-37 | bugs/F-37 | delete | | | | | | family-sweep |
| 30 | F-39 | bugs/F-39 | delete | | | | | | protocol model |
| 31 | F-40 | bugs/F-40 | instance | | | | | | verified-clean note |

## Phase 2 — Config consistency & drift (rank 32–37; doctor-hosted)

| Rank | Finding | Folder | Level | Detector proven(b+c) | Precision | Locked | Fix | KPI | Assessment |
|---|---|---|---|---|---|---|---|---|---|
| 32 | CORE-10 | bugs/CORE-10 | instance | | | | | | dep S4 |
| 33 | CORE-40 / BUG-023 | bugs/CORE-40 | instance | | | | | | dep S4 |
| 34 | CORE-2 | bugs/CORE-2 | instance | | | | | | dep S4 |
| 35 | CORE-42 | bugs/CORE-42 | instance | | | | | | dep S4 |
| 36 | F-11 | bugs/F-11 | instance | | | | | | dep S1, S4 |
| 37 | BUG-017 | bugs/BUG-017 | instance | | | | | | note-only (wontfix) |

## Phase 5 — Behavioral / runtime / API (rank 38–48)

| Rank | Finding | Folder | Level | Detector proven(b+c) | Precision | Locked | Fix | KPI | Assessment |
|---|---|---|---|---|---|---|---|---|---|
| 38 | CORE-12/13/16/31/57 | bugs/CORE-12 | instance | | | | | | |
| 39 | CORE-15 / CORE-35 | bugs/CORE-15 | instance | | | | | | |
| 40 | BUG-009 | bugs/BUG-009 | instance | | | | | | dep S1 |
| 41 | F-14 | bugs/F-14 | instance/manual | | | | | | partial |
| 42 | F-12 | bugs/F-12 | instance | | | | | | |
| 43 | F-21 | bugs/F-21 | instance | | | | | | retired-by-S3 + delete |
| 44 | CORE-20 / BUG-008 | bugs/CORE-20 | instance | | | | | | |
| 45 | CORE-22 | bugs/CORE-22 | instance | | | | | | |
| 46 | CORE-28 / CORE-29 | bugs/CORE-28 | instance | | | | | | |
| 47 | BUG-016 | bugs/BUG-016 | instance | | | | | | dep S1 |
| 48 | CORE-45 / CORE-46 | bugs/CORE-45 | instance | | | | | | |

## Manual (M1–M4 — single `note.md`, no pretend coverage)

| Rank | Finding | Folder | Note |
|---|---|---|---|
| M1 | F-08 / CORE-33 | bugs/F-08 | semantic recall — not automatable |
| M2 | F-14-partial / F-26-partial | bugs/F-14 | recovery stubs / fake success — behavioral tracing |
| M3 | CORE-53 | bugs/CORE-53 | hardcoded confidences — wording/intent |
| M4 | ISSUE-101..104 + F-25-doc-hygiene | bugs/ISSUE-101 | design decisions + doc accuracy — human |

---

## Progress summary (v2) — numbers live in LEDGER.md

| Phase | Findings | Detectors proven(b+c) | Precision ok | Locked | Fixes |
|---|---|---|---|---|---|
| S | 5 mechanisms | 5/5 | 5/5 | 5/5 | 1/5 |
| 3 | 3 | 3/3 | 3/3 | 3/3 | 3/3 |
| 4 | 5 | 5/5 | 5/5 | 5/5 | 5/5 |
| 0 | 9 | 9/9 | 9/9 | 9/9 | 9/9 |
| 1 | 14 | 2/14 | 2/14 | 2/14 | 2/14 |
| 2 | 6 | 0/6 | 0/6 | 0/6 | 0/6 |
| 5 | 11 | 0/11 | 0/11 | 0/11 | 0/11 |
| manual | 4 | — | — | — | — |
| **Total** | **53 rows** | **24/53** | **24/53** | **24/53** | **20/53** |