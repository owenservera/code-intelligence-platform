# CIP Core Enhancement + Bug-Fix Plan v2 (sequential, embedding-free)

**Status:** PLAN/SPEC (no code yet) · **Date:** 2026-08-16 · **Owner:** interactive (with user)
**Companion doc:** `docs/dev/09-bugs-and-issues.md` (source of truth — **intact**)
**Product framing:** CIP = general polyglot indexing + issue detection. This plan (a) fixes CIP's own
correctness (`09`) and (b) ships the detection features into CIP's product surfaces so every future repo
gets them. Runs inside the campaign framework (RUNBOOK §0, PROFILE.cip.md §2 instruments).
**v2 upgrades:** leverage-first sequencing, Phase S systemic foundation, **mandatory precision gating**,
regression-locked detectors (pytest fires/silent), numeric health KPIs, class-workflow (delete/manual),
machinery-debt budget. RUNBOOK/DESIGN/DEPENDENCIES/TRACKER/LEDGER are the operational layer.
**Two jobs, one sequence — DETECT BEFORE FIX.** We do NOT fix first. The loop per family:
(1) **ENHANCE CIP's core** so it can identify a bug class; (2) **PROVE RECALL** — normal CIP against this
repo while the bug is *still present* must fire on the broken code; (3) **PROVE PRECISION (v2)** — the
same detector on a clean reference repo and the broader index must stay silent (0 FPs, or a documented
tolerated set + mitigation); (4) **REGRESSION-LOCK (v2)** — ship 2 pytest cases (fires / silent);
(5) only **AFTER** 2–4 are green do we **FIX** the defects in `09`. Re-run then shows the signal flip
broken → healthy **with FP count unchanged at 0**, proving both sides. No separate/secondary system — the
detection lives in CIP's real pipelines (audit rules engine, analysis/health, indexer, `cip doctor`).
**Hard constraint:** no embeddings anywhere. Every fix & check is AST / static-analysis /
index-introspection / config-diff — embedding-free by design (keeps `sync`/`search` fast).

---

## 0. Concept (why this shape)

The `09` log is mostly CIP *failing at its own job*: it missed import edges, reported "clean" when
sub-indexers silently died, forced health to a constant 80, and polluted its index with backups. So
"enhancing CIP to find these bugs" = **making CIP's core pipelines correct and self-aware**, then
verifying a normal CIP run on this repo now reports them. Each phase does both — but v2 adds the
**precision gate**: the campaign's own subject is false positives (F-22/F-23 → QA-UNTESTED-HOT), so a
detector validated only for recall is not validated.

**Why systemic-first (v2):** most of the 51 findings trace to 4 root anti-patterns — bare-`except`
swallow, dead-code accumulation, stale signatures, config-key drift. Phase S fixes those *mechanisms*
first, which retires a large slice of instances (BUG-001/F-03, F-13, F-15…F-17, F-20, F-21, F-26,
F-30…F-32, F-34, F-35, CORE-2, CORE-10, CORE-39, CORE-40, F-06, F-09, F-11) before per-finding work.

**Honest limit (user-acknowledged):** `09` came from advanced LLM deep-mining, so we won't catch 100%.
Embedding-free static/structural checks cover the mechanical families (~54 findings); the ~6 that need
semantic/LLM judgement are §8 `manual`.

---

## 1. Package / command shape (core, not secondary)

Enhancements land in CIP's existing surfaces — no new `selfcheck` package. **New in v2:** doctor skeleton
is built in Phase S and `tests/detectors/` + `tests/data/clean_ref/` + `LEDGER.md` are added.

```
lib/cipkg/
  stack/rules.py            # + CODE-* / INDEX-* / AUDIT-* rules (Phase S,0,1,3,4,5)
  analysis.py               # real quality_score + index-integrity signal (Phase 3,4)
  indexer.py                # resolve_import fix + tested_by fix + backup-exclude (Phase 3)
  base.py / config paths    # config key reconciliation, schema-version, port, repo-settings (S,2)
  doctor.py  (core)         # `cip doctor`: CONFIG-* self-consistency + --static/--runtime probes (S,2,5)
  cli.py / command_registry # wiring fixes (S3 covers; Phase 0/1 apply the fixes)
  retrieve.py               # caller/callee labels, graph decoration, auto-embed → background (5)
  daemon.py / maintain.py / workflow_engine.py / stack/audit.py  # behavioral fixes (4,5)
tests/detectors/            # 2-case pytest per family: fires-on-broken / silent-on-clean (NEW)
tests/data/clean_ref/       # pinned clean reference repo + broken fixture twin (NEW)
docs/dev/cip-bugfix-campaign/LEDGER.md   # machinery budget + KPIs + precision ledger (NEW)
```

`cip doctor` is a **first-class CIP command** (like `cip gate`/`cip selftest`), not a side tool. It hosts
the self-consistency + runtime-contract checks. `cip audit` hosts the code/index/audit rules. `cip analyze`
hosts the health-integrity signal. All embedding-free.

**Within-phase order (mandatory):** build the detector, prove RECALL on the *unfixed* code, prove
PRECISION on clean code, RE-GRESSION-LOCK it, then **apply the fix last**. See §0, §10, RUNBOOK §4.

---

## 2. Phase S — Systemic foundation (v2, done FIRST)

A single mechanism pass over the 4 root anti-patterns. **No per-instance ceremony** — each mechanism
retires its instances; TRACKER marks them `retired-by-S#`.

- **S1 — no-bare-except discipline.** `lib/cipkg` bans bare `except Exception: pass` in critical paths;
  must `log_swallowed()` or surface. Retires F-24/F-41 (silent sub-indexer swallow), CORE-41, CORE-52,
  F-11 (profile swallow), BUG-009 (widened embed fallback), BUG-016 (indicator/toggle surfaced).
- **S2 — static-lint gate.** `pyflakes`/ruff wired into CI (`cip-static-lint-gate.yml`) + `cip gate`; the
  regression-locked detector (`tests/detectors/s2_static_lint_gate_test.py`) proves RECALL on the broken
  evidence and PRECISION (silent) on `tests/data/clean_ref/`. Retires F-09, BUG-005/F-02
  (`json` F821). **F-06 is NOT this gate** — pyflakes treats the in-`try` module import as a binding,
  so the runtime-order NameError is invisible to static lint; F-06 is caught by S3 runtime probes.
- **S3 — signature/attribute conformance suite.** `tests/detectors/s3_conformance_test.py`:
  import-graph + `inspect` over `lib/cipkg` — every subcommand parser ↔ dispatch dict ↔ handler arity;
  every referenced `lib.X` attribute exists; every registry card target resolves. Retires BUG-001/F-03
  (`sync(con,cfg)`), F-13 (`cipkg.audit`), F-15, F-16 (21 dispatch gaps), F-17 (`verify-index` misroute),
  F-20 (`FilterEngine.rank`), F-21 (`hybrid_search`), F-26 (adapter caller graph), F-30 (impact keys),
  F-31 (`runtime_adapters.broken`), F-32 (`mark_for_reindex`), F-34 (`selftest`), F-35 (`handle_deps_command`).
  **KICKOFF NOTE (2026-08-16):** implemented as a **pure static AST analyzer** (`s3_conformance.py`,
  zero execution / zero `inspect`) — Passes B–E cover every parsed↔dispatched↔arity rule and module/
  symbol/attribute existence without importing packages (safer than `inspect`, works on packages whose
  imports are themselves broken). RECALL proven at **53 findings** on `lib/cipkg` (21 UNHANDLED, 1
  MISROUTED, 2 ARITY, 1 MISSING-MODULE, 28 MISSING-SYMBOL); PRECISION proven (0 FPs) on a synthetic clean
  package + clean_ref; locked (`s3_conformance_test.py`, 12 tests). The two `inspect`-dependent rows —
  F-06 (runtime-order NameError, pyflakes+AST blind by design) and BUG-001/F-03 (`sync(con,cfg)` arity at
  call time) — stay on S5 `--runtime` probes + Phase 5, not S3.
- **S4 — config-schema loader suite.** `load_config` reads every key core reads; TOML keys == code-read
  keys (map or rename); surfaced live-DB `schema_version`. Retires CORE-2 (`[web]`), CORE-10 (port),
  CORE-39 (`exclude_patterns`↔`exclude`), CORE-40/BUG-023 (11 vs 4), CORE-42 (`[perf]` dup).
  **KICKOFF NOTE (2026-08-16):** locked in `tests/detectors/s4_config_schema_test.py` (15 tests) —
  RECALL: all 7 CONFIG-* rules fire with contract refs + evidence; loader contract `_load_repo_toml`
  returns `(cfg, toml_error)` and on a decode error on the shipped default returns immediately (proven:
  a %-root invalid default does NOT become the v2 defaults); PRECISION: per-rule surgical (a config
  missing exactly one anatomy fires only its rule), port matching the code `default:` literal stays
  silent, `schema_version == store.SCHEMA_VERSION` silent; INVARIANT: `config.default.toml` fails
  `tomllib.loads` (FLIPS clean when the Phase-2 fix lands).
- **S5 — `cip doctor` skeleton.** First-class command hosting `CONFIG-*` + `--static`/`--runtime` probe
  targets; extended in Phases 2/5. Host for all CONFIG/DETECTOR surfaces.

**Acceptance:** `cip doctor --config`/`--static` clean on the fixed repo; before, they list the
instance evidence for every retired row.

---

## 3. Phase 3 — Import-graph & tested_by integrity (front-loaded crown jewel)  (rank 1–3)

**FIX (defects — apply LAST, RECALL+PRECISION green first):**  ✅ **LANDED 2026-08-16**
- F-22 — `indexer.resolve_import` rewritten (relative dotted names → submodule paths, leading-dot parent
  hops, `lib/`/`src/` prefixes for `cipkg.*`). **In-repo resolution 99.79% (486/487)**; sole miss is the
  genuinely-broken `cli.py .ingest` (Ph0 dead-ref target). Live `imports` edges 12 → 260.
- F-42 — excludes hardened at BOTH grader surfaces: `base.DEFAULT_EXCLUDES`+`BACKUP_DIR_PREFIXES`
  (`iter_files`) AND `gatekeeper._scan`/`_decide` segment-aware gate (the real ingestion path; `HARD_DIRS
  = DEFAULT_EXCLUDES` flows the exact-name entries in). **Live: 575 backup files → 0; pollution 76% → 0%**
  (files 753 → 156). Over-match bug (test names containing `backup_`) fixed via segment-aware predicate.
- F-23 — `build_tested_by` grounds tested_by in the resolved import/call/reference graph; name-mention
  chunk matching removed; backup-symbol srcs gated out; keeps `src`=symbol / `dst`=test-file convention.
  **Live `tested_by` 4462 → 159, noise 0.**

**ENHANCE (detectors — build & prove FIRST on the still-broken repo):**  ✅ **LANDED**
- `INDEX-IMPORT-RESOLUTION` (in-repo-scoped) — `tests/detectors/s6_index_integrity.py` drives the REAL
  resolver+parser; threshold 100% of in-repo ⇔ 99.79% (486/487) with the only unresolved spec being the
  known-broken `cli.py .ingest`.
- `INDEX-TESTED-BY-NOISE` — python-side count (src not in symbols OR src_path under backup segments).
- `INDEX-BACKUP-POLLUTION` — segment-aware; synthetic flip (old scanner's tree stays clean, `exclude=[]`)
  + repo 0-pollution + gatekeeper `_decide` "backup/duplicate tree" reason.
- Regression-locked in `tests/detectors/phase3_index_test.py` (14 tests; full suite **52 green**).

**How CIP now identifies it (no embeddings):** `cip audit`/`cip analyze` report resolution rate, noise
count, pollution %, all backed by the retained s6 detectors. Before fix: <1% in-repo resolution + 4,462
noisy edges + 76% duplicates. After fix + re-sync: **99.79% in-repo, 0 noise, 0 pollution**. Import-graph
rules (circular/orphan/layer) now run on a clean 156-file index instead of 753 files of duplicates.

---

## 4. Phase 4 — Audit/health false-positives & silent no-ops (dashboard-critical)  (rank 4–8)

**FIX (defects — apply LAST):**
- BUG-013 / F-01 / CORE-27 — `analysis._calculate_health_score`: stop forcing `quality_score=80`; compute
  from real audit-severity counts (with `gapfill.score()` reconciliation); remove the swallowed AttributeError.
- BUG-015 — `stack/audit.audit()`: only close findings whose rule actually ran; never auto-mark
  ESLINT:/tauri/custom findings `fixed`.
- F-24 / F-41 — surface failed sub-indexers (S1 mechanism) + explicit "prepare stack" step (ISSUE-106);
  new bridge never routes console audit through `audit(refresh=True)` for stack prep.
- BUG-014 — pin one `root` (ISSUE-103); pass `root=` to EVERY lib call.
- CORE-30 — render "no symbols indexed — run sync" instead of a constant 50 ring.

**ENHANCE (detectors — prove FIRST on the still-broken repo):**
- `AUDIT-SILENT-NO-OP` (0 findings on a stack repo while sub-indexers didn't run),
- `AUDIT-FINDING-AUTO-CLOSED` (findings flipped to `fixed` without their rule running),
- health-integrity note ("quality_score forced" badge gone once real).
`cip analyze` shows a varying, real quality score; `cip audit` shows skipped-subindexer warnings.

---

## 5. Phase 0 — Undefined names & broken imports  (rank 9–17; mostly retired by S2/S3)

**FIX (defects — apply LAST):** BUG-005/F-02, F-06, F-09, F-34, F-35, CORE-5, F-13, F-20, F-31 — most are
already mechanically handled by S2 (lint) + S3 (conformance); Phase 0 applies the remaining one-line fixes.
**ENHANCE (detector):** `CODE-UNDEFINED-NAME` + `CODE-MISSING-SYMBOL` rules in `stack/rules.py` (also a
`cip doctor --static` step) = the continuous audit-side surface; S2/S3 are the build-time gates.
**Acceptance:** pre-S2/S3 the gates listed ≥8 findings; post-fix `cip doctor --static` is clean and the
family rule shows 0 FPs on clean-ref.

---

## 6. Phase 1 — Dead code & command-dispatch coverage  (rank 18–31; class-workflow)

**FIX (defects — apply LAST):**
- F-16 (21 missing dispatch entries) + F-15 (`analyze`/`rebuild` arity) — wired by S3 conformance first,
  then `cli.py` handler align to `(root, args)`; registry cards point at real lib callables.
- Legacy removal per `09 §7` (unchanged directive): delete `command_adapter.py`, `interactive.py`,
  `interactive_ui.py`, `help_system.py`, `watcher.py`, `dashboard_state.py`, `stack/selftest.py`,
  `ast_chunker.py`, `retrieval_bridge.py`, `lancedb_store.py`; **extract `briefing()` → `stack/briefing.py`**
  (F-38/CORE-51) and reuse the WS topic protocol as a model (F-39/CORE-57) before deletion;
  `repo_map.py`/`scip_indexer.py` deleted or wired (AGENTS.md claims unsupported — F-25/F-33).
- BUG-011/024 — drop `ast_aware_chunking` dead config path.
- F-40 — verified-clean; note-only (map `cap:code:*` at the bridge).

**ENHANCE (detectors — prove FIRST, then bulk-sweep):** `CODE-DEAD-MODULE` (zero importers + no
CLI/registry entry), `CODE-UNHANDLED-COMMAND`, `CODE-ARITY-MISMATCH`. **Prove each on 2–3 exemplars, then
sweep the rest — no per-instance docs for deletions.**
**Acceptance:** post-cleanup `CODE-DEAD-MODULE` only fires on genuinely-orphaned new code; the 21 commands
no longer print "unknown command"; `briefing()` lives in a leaf module.

---

## 7. Phase 2 — Config consistency & drift  (rank 32–37; doctor-hosted)

**FIX (defects — apply LAST):**
- CORE-10 — pick one daemon port (8765/8787) across config + code + registry.
- CORE-40 / BUG-023 — set `[meta] schema_version` to live DB value (4) or migrate; stop claiming 11.
- CORE-2 — add `[web] host/port/auto_manage_daemon`.
- CORE-42 — collapse `[perf]`/`[performance]`; mark legacy keys deprecated.
- F-11 — fix `base.load_config` repo-settings resolution (walk up from root to `<root>/repo-settings`,
  align the 3 import sites, surface profile-load errors — S1).
- BUG-017 — note-only (tomllib always present).

**ENHANCE (detectors — built first, hosted by `cip doctor`):** `CONFIG-SCHEMA-DRIFT`,
`CONFIG-KEY-UNDEFINED`/`CONFIG-KEY-UNUSED`, `CONFIG-PORT-MISMATCH`, `CONFIG-PROFILE-SILENT-FAIL`.
**Acceptance:** `cip doctor --config` clean after fixes; before, it lists CORE-10/2/40/42 + F-11 + BUG-023.

---

## 8. Phase 5 — Behavioral/job-safety & runtime/API contract  (rank 38–48; last)

**FIX (defects — apply LAST):**
- CORE-12/13/16/31/57 — `daemon()`/`watch()`/`consolidation` in managed thread/subprocess with stop flag;
  web-managed daemon = separate process (never `taskkill /F /T` the console).
- CORE-15 / CORE-35 — `maintain.rebuild`/`git_index` become background jobs with progress + confirm.
- BUG-009 — widen `embed.get_embedder` fallback (offline+uncached → hashing, not only ImportError).
- F-14 — `RecoveryEngine` actually re-runs; `ErrorPatternLearning` reads real history (partial-manual).
- F-30 — `post_edit_hook` reads real impact keys, fixes `" callees"` typo, passes `root` (S3 catches first).
- F-12 — `workflow_engine._run_pytest` parse fix (skips in total).
- F-21 — legacy `web_server._api_search` → delete with `09 §7` legacy removal.
- CORE-20/BUG-008 — fix `retrieve.context()` label swap; CORE-22 — decorated graph nodes.
- CORE-28/29 — audit as background job + pagination.
- BUG-016 — custom-rules `exec_module` warning toggle (S1 indicator).
- CORE-45/46 — verify runners explicit; signals stable-hash upsert.

**ENHANCE (detectors — prove FIRST):** `CODE-UNSAFE-PATTERN` rule (blocking loop on hot path,
destructive `*.db` delete without guard, broad swallow in critical sub-indexers, `exec_module` of repo
code) + `cip doctor --runtime` probes verifying call sites resolve (F-21/F-30/F-31 family) and
`search`/`graph` honor contracts.

---

## 9. Non-automatable (explicitly `manual` — needs LLM / deep judgement)

| Finding | Why not mechanically detectable (embedding-free) |
|---|---|
| F-08 / CORE-33 | "recall is not semantic" — needs judging semantic equivalence of query↔stored facts. |
| F-14 (partial) | recovery stubs *appear* to succeed — only observable by tracing that nothing re-runs. |
| F-26 (partial) | `command_adapter` fakes `success=True` without running — needs behavioral tracing. |
| CORE-53 | hardcoded confidences labeled "learning-adjusted" — wording/intent mismatch. |
| ISSUE-101..104 | design decisions (metric source of truth, trend integrity, embed UX) — product choice. |
| F-25 | "merge-note claimed complete but wasn't" — meta-doc accuracy, human review. |

In v2 these are **single `note.md` rows only** — no full drill, no pretended coverage.

---

## 10. Tracker (living — fill in as we implement each phase)

Columns: **Rank** · **Finding (09 ref)** · **Level** · **Detector proven(b+c)** · **Precision ok** ·
**Regression-locked** · **Fix done** · **KPI** · **Assessment**. Status vocabulary in RUNBOOK §6.

### Phase S — systemic foundation (mechanism pass, no instance docs)
| Mechanism | Fix/land | Retires (09 refs) | Verified |
|---|---|---|---|
| S1 no-bare-except | ◐ | F-24, F-41, CORE-41, CORE-52, F-11, BUG-009, BUG-016 | ☐ |
| S2 static-lint gate | ☑ | F-09, BUG-005/F-02, F-06 | ☑ |
| S3 signature-conformance | ☑ (detector: s3_conformance.py; 53 findings recall; FP=0; 12 tests) | BUG-001/F-03, F-13, F-15, F-16, F-17, F-20, F-21, F-26, F-30, F-31, F-32, F-34, F-35 | ☑ |
| S4 config-schema suite | ☑ (detector: s4_config_schema_test.py; 7 rules recall; per-rule FP=0; loader contract; 15 tests) | CORE-2, CORE-10, CORE-39, CORE-40/BUG-023, CORE-42 | ☑ |
| S5 `cip doctor` skeleton | ☐ | host for CONFIG-*/probes | ☐ |

### Phase 3 — import-graph / tested_by (rank 1–3)
| Full mapping per DEPENDENCIES.md | Detector proven(b+c) | Precision | Locked | Fix | KPI |
|---|---|---|---|---|---|
| F-22 · F-42 · F-23 | ☑ (s6_index_integrity.py + phase3_index_test.py, 14 tests) | ☑ (0-FP segment-aware; only cli.ingest unresolved) | ☑ | ☑ | ☑ 753→156 files; 76%→0 pollution; imports 12→260; in-repo 99.79%; tested_by 4462→159, noise 0 |

### Phase 4 — audit/health (rank 4–8)
| BUG-013/F-01/CORE-27 · BUG-015 · F-24/F-41 · BUG-014 · CORE-30 | ☐ | ☐ | ☐ | ☐ | ☐ |

### Phase 0 — static names (rank 9–17)
| BUG-005/F-02 · F-06 · F-09 · F-34 · F-35 · CORE-5 · F-13 · F-20 · F-31 | ☐ | ☐ | ☐ | ☐ | ☐ |

### Phase 1 — dead code / dispatch (rank 18–31)
| F-16 · F-15 · F-25 · BUG-011/F-04 · F-26..F-29 · F-32 · F-38 · F-36 · F-37 · F-39 · F-40 | ☐ | ☐ | ☐ | ☐ | ☐ |

### Phase 2 — config (rank 32–37)
| CORE-10 · CORE-40/BUG-023 · CORE-2 · CORE-42 · F-11 · BUG-017 | ☐ | ☐ | ☐ | ☐ | ☐ |

### Phase 5 — behavioral / runtime (rank 38–48)
| CORE-12/13/16/31/57 · CORE-15/35 · BUG-009 · F-14 · F-12 · F-21 · CORE-20/BUG-008 · CORE-22 · CORE-28/29 · BUG-016 · CORE-45/46 | ☐ | ☐ | ☐ | ☐ | ☐ |

### Manual (M1–M4) — single note, no pretend coverage
| F-08/CORE-33 · F-14-partial/F-26-partial · CORE-53 · ISSUE-101..104 + F-25-doc | note.md only | | | | |

---

## 11. How we assess interactively (the loop — DETECT, PRECISION, LOCK, then FIX)

For each family / phase *N*, in this exact order:

1. **Design + build the detector** (core enhancement). Embedding-free. Do not touch the buggy code.
2. **RECALL:** run the normal CIP command on this repo **with the bug unfixed**; it must list the
   instance evidence. Iterate until it does.
3. **PRECISION (v2, mandatory):** run the detector on `tests/data/clean_ref/` + broader corpus; **0 FPs**
   (or documented tolerated set + mitigation). Tune thresholds until both 2 and 3 hold.
4. **REGRESSION-LOCK (v2):** ship the 2-case pytest in `tests/detectors/`. KPI baseline → LEDGER.
5. **Confirm working, THEN fix.** Only after 2–4 are green do we apply the **FIX** in `lib/cipkg`.
6. **Re-run to confirm the flip.** Signal healthy **and** FP unchanged at 0; KPI after-value recorded.
7. **Machinery ledger:** net-new rule/step/LOB within the phase budget (DESIGN §5).
8. Fill Phase tracker + LEDGER: `Detector proven(b+c)=yes`, `Precision ok`, `Regression-locked`,
   `Fix done=yes`, `KPI` before/after, one-line `Assessment`.
9. Move to the next cluster. Stop when Phase 5 done or marginal value drops (measured by LEDGER KPIs).

**Why this order:** recall-only validation proves nothing — a detector validated only after the bug is
gone (or only for firing) is overfit to this repo. Validating RECALL on broken code, PRECISION on clean
code, then fixing, gives a clean before/after that proves the enhancement is real **and** not a
false-positive machine.

**Definition of done:** every automatable `09` finding has a tracker row; every detector is recall- AND
precision-proven and regression-locked; every fix lands and is confirmed by a clean re-run with stable 0
FPs; manual findings are single-note and explicitly tagged `manual`.