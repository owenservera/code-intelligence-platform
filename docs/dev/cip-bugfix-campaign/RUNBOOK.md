# RUNBOOK — CIP Bug-Fix & Detection Campaign (v2, upgraded)

**Folder:** `docs/dev/cip-bugfix-campaign/` · **Date:** 2026-08-16
**Read first:** §0 (what this campaign is) + `PROFILE.cip.md` (CIP's own wiring).
**Source of truth:** `09-bugs-and-issues.md` (intact), `10-selfcheck-enhancement-plan.md` (v2),
`DESIGN.md` (v2), `DEPENDENCIES.md` (v2), `LEDGER.md` (new).
**One line:** For every bug class, prove a CIP product detector **fires on the broken code AND stays
silent on clean code**, regression-lock it, then fix instances — detect-first, fix-last,
least-dependency, highest-leverage first. Fixes are product-wide, not this-repo-specific.

---

## 0. What this campaign IS (and isn't)

CIP is a **general, polyglot code-indexing + issue-detection system** — one product you run against
any repo, any language, now and for all future repos. This campaign changes that *product*, in two ways,
per family:

1. **Product fixes.** The `09` findings are CIP failing at its own job (missed import edges, silent
   sub-indexer death, forced health 80, config drift). Every fix in `lib/cipkg/**` is a correctness fix
   to the PRODUCT — once landed, CIP behaves correctly for every repo it ever indexes, not just this one.
2. **Product detection features.** The detectors (swallow-scanner, static-lint gate, signature-conformance
   suite, config validator, health-integrity) are shipped INTO CIP's own surfaces
   (`stack/rules.py` / `analysis.py` / `doctor.py` / CI gate) so `cip audit` / `analyze` / `doctor` /
   `gate` then apply them to ANY repo. This repo serves only as CIP **dogfooding** — the proof corpus that
   a detector fires on real broken code (RECALL) and stays silent on clean code (PRECISION), regression-locked
   in `tests/detectors/`.

**Portability is a product property, not a doc-property.** Detectors dispatch by file language (CIP indexes
polyglot repos), so the same mechanisms cover Python, JS/TS, Go, Rust, etc. — see the per-language
instrument table in `PROFILE.cip.md` §2. You do NOT copy this folder into other repos; you run the (fixed,
enhanced) CIP product against them. **No embeddings anywhere** — AST / static-analysis / index-introspection /
config-diff only (keeps sync/search fast on any repo).

**Campaign vs product split:** the *method* (RUNBOOK §4 loop, file specs, LEDGER budgets, §6 checklist
discipline) is how we develop + prove CIP's features using its own bugs as evidence. The *artifacts* the
method produces (rules, doctor steps, gate, fixes) are CIP product code that outlive this campaign.

---

## 1. Folder layout

```
cip-bugfix-campaign/
  09-bugs-and-issues.md        # CIP's own bug log (INTACT — never edit; dogfood corpus)
  10-selfcheck-enhancement-plan.md  # the plan (v2)
  RUNBOOK.md                   # this file — process + file specs (v2)
  DESIGN.md                    # detection architecture, families, budgets (v2)
  PROFILE.cip.md               # CIP's own wiring + per-language instruments (NEW)
  TRACKER.md                   # row statuses, ranking, ceremony level (v2)
  DEPENDENCIES.md              # leverage-first ranking + dep edges (v2)
  LEDGER.md                    # machinery budget + numeric KPIs + precision ledger (NEW)
  bugs/
    <FINDING-ID>/
      detection.md             # how CIP core IDENTIFIES the class (embedding-free)
      fix-design.md            # fully-researched fix design for the defect
      note.md                  # MANUAL-only: single-note (no full drill)
tests/detectors/               # pytest per family: broken-fixture fires / clean-fixture silent
tests/data/clean_ref/          # pinned clean reference repo + broken-fixture twin (precision proof)
```

`<FINDING-ID>` matches `09` (e.g. `BUG-005`, `F-22`, `CORE-39`). Multiple `09` entries that share one
root cause share a folder (see TRACKER for exact mapping). Deletion/legacy rows get **no folder**.

---

## 2. File spec — `detection.md`

1. **Finding ref** — IDs from `09` this detector covers (or `retired-by-S#`).
2. **What's broken** — one paragraph, evidence `file:line`.
3. **Detection strategy (embedding-free)** — technique + CIP surface (`rules.py` rule, `analysis`
   signal, `cip doctor` step, `indexer` probe).
4. **Detector design** — reads (AST / `edges` table / config TOML / DB `meta`), threshold/condition,
   emitted `CheckFinding` shape with `file:line` evidence, **KPI reference** (LEDGER row), **tolerated-FP
   list + mitigation**.
5. **Recall test plan** — exact CIP command + expected findings on the *unfixed* repo.
6. **Precision test plan** — same detector on `tests/data/clean_ref/` + broader corpus; **expected 0 FPs**
   (or documented tolerated set with mitigation).
7. **Regression-lock** — the 2 pytest cases shipped in `tests/detectors/` (fires / silent).
8. **Success criteria** — bullets: on broken repo `cip X` lists <evidence>; after fix, clean; FP count 0.

## 3. File spec — `fix-design.md`

1. **Finding ref** + severity/area + level (systemic/instance/delete/manual).
2. **Root cause** — precise, `file:line`, mechanism.
3. **Proposed fix** — change + code sketch; flag shared-path (indexer/analysis/audit) dependencies.
4. **Dependencies** — prerequisites (cross-ref DEPENDENCIES.md).
5. **KPI target** — the numeric before/after this fix must move (LEDGER metric).
6. **Risks / blast radius** — what else could break; backward-compat.
7. **Verification** — re-run CIP: detector reads clean, FP 0, KPI recorded, existing tests pass.

---

## 4. Process (mandatory order — DETECT + PRECISION FIRST, FIX LAST)

Per family, in DEPENDENCIES.md order (systemic S first, then leverage-ranked phases):

0. **Phase S first (mechanism pass):** S1–S5 land before any instance work; they retire their instances
   by mechanism (TRACKER `retired-by-S#`).
1. **Design the family detector.** Embedding-free. Do not touch the buggy code.
2. **RECALL — prove it fires.** Run the normal CIP command on this repo *with the bug unfixed*; it MUST
   list each instance's evidence. Iterate until it does.
3. **PRECISION — prove it stays silent on clean code. MANDATORY.** Run on `tests/data/clean_ref/` + the
   broader corpus; gate **0 FPs** (or documented tolerated set + mitigation). A recall-only detector is
   not validated (subject of this campaign is FPs: F-22/F-23 → QA-UNTESTED-HOT).
4. **REGRESSION-LOCK.** Write the 2 pytest cases in `tests/detectors/`. Record in LEDGER.
5. **KPI baseline** recorded (LEDGER before-values).
6. **Only now, fix instances** (deps first, minimal change).
7. **Re-run:** signal flips healthy AND FP stays 0; KPI after-values recorded. Proves both.
8. **Machinery ledger:** update net-new rule/step/LOB; enforce budget (§5 DESIGN).
9. **Deletion/legacy rows:** no docs — prove the F1 family on 2–3 exemplars, then bulk-sweep per `09 §7`
   removal order.
10. **Manual rows:** single `note.md`; detector documented "not automatable".
11. Update TRACKER + LEDGER after each finding.

**Do not fix before RECALL + PRECISION + REGRESSION-LOCK are all green.** Fixing first destroys the
evidence and we can't tell the detector works.

---

## 5. How to work (sequential, token-bounded)

- One finding at a time within a phase; systemic pass first; leverage-ranked phases in order.
- If a finding's dependencies are not done, take the next least-dependent/highest-leverage one.
- TRACKER is the single source of campaign progress; LEDGER the single source of numbers.
- Deletion rows and manual rows cost near-zero ceremony by design.
- Stop rule: Phase 5 done, or marginal value drops — measured per phase by LEDGER KPI movement.

---

## 6. Autonomous-run survival discipline (todos & checkpoints — **MANDATORY**)

Autocompaction WILL fire on long autonomous sessions and erase the agent's working memory. The **todo
list is the only structure that survives compaction.** Therefore every todo list this campaign touches
MUST be built so a freshly-compacted agent is force-returned to the persisted docs:

1. **Todo list = the anti-erasure anchor.** Every todo list MUST have FIRST item
   `[restore] Read RUNBOOK.md + TRACKER.md + LEDGER.md + CHECKPOINT.md` and LAST item
   `[checkpoint] Update TRACKER + LEDGER + CHECKPOINT.md`.
2. **Every work-item todo references the docs.** Each todo MUST cite its RUNBOOK § + step, DEPENDENCIES
   rank, and TRACKER row (e.g. `S2 static-lint gate — RUNBOOK §2/§4-step, TRACKER Phase S S2`). No bare
   todos — a standalone todo is un-resumable after compaction.
3. **Re-anchor before any work — always.** On EVERY session regardless of apparent context (including
   right after compaction), the first executed action is the `[restore]` item. Cheap insurance; never skip.
4. **Checkpoint at every milestone.** After any proven detector, any landed fix, or any completed phase,
   write `CHECKPOINT.md` (status, KPI numbers, decisions, next unit). It is the canonical anti-erasure
   mechanism (AGENTS.md 120K-rule §"persist continuously").
5. **Never derive state from memory.** Progress comes ONLY from TRACKER (status) + LEDGER (numbers) +
   CHECKPOINT (narrative) + `09` (evidence). If memory and docs disagree, docs win.
6. **Hand off cold.** End-of-session checkpoint must let a fresh agent with zero prior context resume the
   next unit (RUNBOOK §5, rank number, exact next command) without re-reading this whole campaign.

---

## 7. Status vocabulary

- Detector: `todo → designed → proven(p) → proven(b+c) → regression-locked → clean-after-fix`
  (`proven(p)` = precision gate on clean code; `proven(b+c)` = fires on broken AND silent on clean).
- Fix: `todo → designed → implemented → verified`.
- Level: `systemic → instance → delete → manual`.
- Rank: integer from DEPENDENCIES.md (1 = highest leverage, least deps).