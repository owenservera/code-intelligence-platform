# DEPENDENCIES & PRIORITIZATION RANKING (v2, leverage-first)

**Folder:** `docs/dev/cip-bugfix-campaign/` · **Date:** 2026-08-16
**Scope:** CIP's own dogfood ranking (RUNBOOK §0). The *principles* — systemic-first, leverage-first,
dependency-tiebreak, ceremony levels (systemic/instance/delete/manual) — are CIP-product-wide; the
specific edges/ranks below sequence the `09` evidence for CIP itself, using the same families the product
ships for every repo.
**Rule v2:** sequence by **leverage** (blast radius × downstream-clients × value) first, dependencies as
tiebreaker, systemic mechanisms before instance fixes. Find a finding's detection doc and fix design may
both require a prerequisite fix to exist before they can be *validated*; hard edges are below.
**Ceremony levels (v2):** `systemic` (mechanism pass, no docs) · `instance` (full 2-doc) ·
`delete` (no docs, family-sweep) · `manual` (single note).

---

## 1. Hard dependency edges (prerequisite → dependent)

| Prerequisite fix | Enables / required-by | Why |
|---|---|---|
| **Phase S (S1..S5)** | every later phase | root anti-patterns (swallow, lint, signature conformance, config schema, doctor) are the platform all detectors/fixes sit on |
| **CORE-39** (config key reconciliation; via S4) | **F-42** (backup pollution) | `exclude_patterns`→`exclude` fix is what lets `sync_global/backups` actually be excluded |
| **F-22** (resolve_import rewrite) | **F-23** (tested_by), **F-42** (resolution part) | `build_tested_by` must resolve imports first; F-42's resolution metric needs the fixed resolver |
| **F-34** + **F-35** (missing handlers; via S3) | **CORE-5** (14 registry imports) | CORE-5's missing `cli.handle_*` overlap; one cluster |
| **F-01** (nextjs.list_findings; via S3) | **BUG-013** (forced 80) | same root cause in `analysis._calculate_health_score` |
| **F-24** (audit sub-indexer swallow; via S1) | **F-41** (refresh silent swallow) | F-41 is the decision/knock-on of F-24 |

F-42 embeds two dependencies (CORE-39 then F-22) — do CORE-39 in Phase S, F-22 before F-42.

---

## 2. Phase execution order (leverage-first)

`Phase S (systemic) → Phase 3 (index integrity) → Phase 4 (audit/health) → Phase 0 (static names) →`
`Phase 1 (dead code / dispatch) → Phase 2 (config surplus) → Phase 5 (behavioral/runtime) → Manual`

**Why this order:** Phase S is the shared mechanism (biggest blast radius). Phase 3 front-loads the
crown jewel (F-22) because it unblocks circular/orphan/layer/tested_by + the whole graph UI — v1 ranked
it 28th, after 27 lower-value items. Phase 4 is dashboard-critical data honesty (forced 80, finding
auto-close). Phases 0/1 are largely **retired by S2/S3 mechanisms**; remaining rows are cheap family
sweeps. Phase 5 is last because its behavioral fixes are the widest surface (daemon/thread/process).

---

## 3. Ranking (rank 1 = do first)

| Rank | Finding(s) | Phase | Level | Detector family | dep |
|---|---|---|---|---|---|
| — | S1 no-bare-except discipline | S | systemic | CODE-UNSAFE-PATTERN (partial) | |
| — | S2 static-lint CI gate | S | systemic | F0 gate | |
| — | S3 signature-conformance suite | S | systemic | doctor runtime probes | |
| — | S4 config-schema loader suite | S | systemic | CONFIG-* | |
| — | S5 `cip doctor` skeleton | S | systemic | CONFIG-* + probes | |
| 1 | F-22 | 3 | instance | INDEX-IMPORT-RESOLUTION | (S) |
| 2 | F-42 | 3 | instance | INDEX-BACKUP-POLLUTION · INDEX-IMPORT-RESOLUTION | CORE-39(S), F-22 |
| 3 | F-23 | 3 | instance | INDEX-TESTED-BY-NOISE | F-22 |
| 4 | BUG-013 / F-01 / CORE-27 | 4 | instance | health-integrity signal | F-01(S3) |
| 5 | BUG-015 | 4 | instance | AUDIT-FINDING-AUTO-CLOSED | |
| 6 | F-24 / F-41 | 4 | instance | AUDIT-SILENT-NO-OP · prepare-stack step | S1 |
| 7 | BUG-014 | 4 | instance | root-threading (ISSUE-103) | |
| 8 | CORE-30 | 4 | instance | empty-repo state | |
| 9 | BUG-005 / F-02 | 0 | instance | CODE-UNDEFINED-NAME | S2 |
| 10 | F-06 | 0 | instance | CODE-MISSING-SYMBOL (runtime-order; NOT S2 — pyflakes blind) | S3 |
| 11 | F-09 | 0 | instance | CODE-UNDEFINED-NAME (retired by S2) | S2 |
| 12 | F-34 | 0 | instance | CODE-MISSING-SYMBOL (retired by S3) | S3 |
| 13 | F-35 | 0 | instance | CODE-MISSING-SYMBOL (retired by S3) | S3 |
| 14 | CORE-5 | 0 | instance | CODE-MISSING-SYMBOL | F-34, F-35 (S3) |
| 15 | F-13 | 0 | instance | CODE-MISSING-SYMBOL (retired by S3) | S3 |
| 16 | F-20 | 0 | instance | CODE-MISSING-SYMBOL (retired by S3) | S3 |
| 17 | F-31 | 0 | instance | CODE-MISSING-SYMBOL (retired by S3) | S3 |
| 18 | F-16 | 1 | instance | CODE-UNHANDLED-COMMAND (retired by S3) | S3 |
| 19 | F-15 | 1 | instance | CODE-ARITY-MISMATCH (retired by S3) | S3 |
| 20 | F-25 (line-count/doc corrections) | 1 | instance | CODE-DEAD-MODULE (note-only) | |
| 21 | BUG-011 / F-04 | 1 | delete | CODE-DEAD-MODULE | |
| 22 | F-26 | 1 | delete | CODE-DEAD-MODULE | |
| 23 | F-27 | 1 | delete | CODE-DEAD-MODULE | |
| 24 | F-28 | 1 | delete | CODE-DEAD-MODULE | |
| 25 | F-29 | 1 | delete | CODE-DEAD-MODULE | |
| 26 | F-32 | 1 | delete | CODE-DEAD-MODULE | |
| 27 | F-38 (extract `briefing()`) | 1 | delete | n/a (move-leaf) | |
| 28 | F-36 | 1 | delete | CODE-DEAD-MODULE | |
| 29 | F-37 | 1 | delete | CODE-DEAD-MODULE | |
| 30 | F-39 | 1 | delete | n/a (protocol model) | |
| 31 | F-40 | 1 | instance | note-only (verified-clean) | |
| 32 | CORE-10 | 2 | instance | CONFIG-PORT-MISMATCH | S4 |
| 33 | CORE-40 / BUG-023 | 2 | instance | CONFIG-SCHEMA-DRIFT | S4 |
| 34 | CORE-2 | 2 | instance | CONFIG-KEY-UNDEFINED | S4 |
| 35 | CORE-42 | 2 | instance | CONFIG-KEY-UNUSED / deprecate | S4 |
| 36 | F-11 | 2 | instance | CONFIG-PROFILE-SILENT-FAIL | S1, S4 |
| 37 | BUG-017 | 2 | instance | note-only (tomllib wontfix) | |
| 38 | CORE-12/13/16/31/57 | 5 | instance | CODE-UNSAFE-PATTERN | |
| 39 | CORE-15 / CORE-35 | 5 | instance | CODE-UNSAFE-PATTERN | |
| 40 | BUG-009 | 5 | instance | embed-fallback guard | |
| 41 | F-14 | 5 | instance/manual | (partial) | |
| 42 | F-12 | 5 | instance | workflow parse | |
| 43 | F-21 | 5 | instance | doctor --runtime (retired by S3) | S3 |
| 44 | CORE-20 / BUG-008 | 5 | instance | context labels | |
| 45 | CORE-22 | 5 | instance | graph decoration | |
| 46 | CORE-28 / CORE-29 | 5 | instance | audit job/pagination | |
| 47 | BUG-016 | 5 | instance | exec warning (S1 feeds) | S1 |
| 48 | CORE-45 / CORE-46 | 5 | instance | verify/signals | |
| M1 | F-08 / CORE-33 | — | manual | — | |
| M2 | F-14-partial / F-26-partial | — | manual | — | |
| M3 | CORE-53 | — | manual | — | |
| M4 | ISSUE-101..104 / F-25-doc-hygiene | — | manual | — | |

---

## 4. How to consume this for sequencing

1. Run Phase S (S1–S5) first as one mechanism pass — no rank required.
2. Then walk rank 1→48. For each: follow RUNBOOK §4 (detect → recall → **precision** → regression-lock →
   KPI baseline → fix → verify → KPI after → machinery ledger).
3. Non-empty `dep` rows: ensure prerequisites are `verified` first.
4. `delete` rows (ranks 21–30) and `manual` rows (M1–M4) skip full ceremony by design.
5. Parallelize only independent rows; stay in rank order within a phase.