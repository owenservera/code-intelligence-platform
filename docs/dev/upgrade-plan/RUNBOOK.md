# RUNBOOK — Multi-Project Console Upgrade (plans 01–10)

**Folder:** `docs/dev/upgrade-plan/` · **Date:** 2026-08-17
**Read first:** §0 (what this upgrade IS) + `plans-00-index.md` (phase order + GAP table) + the **active
phase doc** + the spec that phase builds (`docs/dev/specs/16|17|18|19-*.md`).
**Source of truth (in order):** `plans-00-index.md` (order + anchors), the active `plan-NN-*.md`
(tasks + verify), `docs/dev/specs/19-project-registry.md` (foundation), the landed spec for the phase,
then the CODE. Docs are never ground truth — only real source (`lib/cipkg/*.py`, `web/src/*`) is.
**One line:** Land the multi-project console in 10 atomic phases: a global project registry + a
`_root()`-scoped backend + a switcher frontend that centrally manages ANY folder and onboards/initializes
it from the web — building on the already-landed SPEC-16 (explorer), SPEC-17 (review), SPEC-18 (history).

---

## 0. What this upgrade IS (and isn't)

CIP today is **single-repo-bound**: `web_bridge.py:36 ROOT = repo_root()` is a module global resolved
from cwd; the console can only ever manage the project it launched inside. This upgrade makes the console
a **central manager**:

1. **Foundation (SPEC-19):** a global `CIP_HOME` registry (`~/.cip/projects.json`) records every code
   folder CIP manages; `_root()` (contextvar, set by middleware from `?repo=`) replaces the module `ROOT`
   across ~140 call sites; the console **boots from any folder** (registry-only mode when no `.cip` above
   cwd — GAP-02); launch root auto-registers (GAP-05); settings read/write the *active* project's config
   (GAP-01); per-project WS + watch (PLAN-05) + daemon port guard (GAP-03).
2. **Features on top:** SPEC-16 repo explorer (tree), SPEC-17 file review (diff + comments), SPEC-18
   realtime history (timeline + blame). All project-scoped, all read-only for source files, comments
   additive (`reviews.jsonl`).
3. **Web onboarding:** `POST /api/projects/{id}/onboard` runs the SAME `init_project` the CLI `cip init`
   uses — full init (`.cip/data`, AGENTS.md, hooks, detect, `indexer.sync`, git-index) as a background
   job with WS progress; F-11/CORE-41 repo-settings warnings surface instead of being swallowed.

**It is NOT** a rewrite of the CLI or core lib — the core already takes `root` params; this is a
web-layer refactor plus new additive endpoints. The console stays read-only for source files (SPEC-15 §4).

**Campaign vs product split:** the *method* (this RUNBOOK §4 loop, atomic task discipline, §6 survival
rules) is how we build the feature safely. The *artifacts* (registry module, `_root()` sweep, endpoints,
frontend switcher) are CIP product code that outlive this upgrade.

---

## 1. Folder layout

```
docs/dev/upgrade-plan/
  plans-00-index.md              # the 10 phases + GAP table + global anchors (READ FIRST)
  plan-01-project-registry.md    # P1: global registry + CIP_HOME JSON store
  plan-02-request-scoped-root.md # P2: _root() contextvar sweep + GAP-01 + GAP-02
  plan-03-projects-rest.md       # P3: /api/projects verbs + GAP-05
  plan-04-onboard-post.md        # P4: extract cmd_init → init_project; onboard/profile POST
  plan-05-ws-multiproject.md     # P5: per-project WS + watch + GAP-03
  plan-06-frontend-switcher.md   # P6: switcher/dashboard/wizard + GAP-04 + GAP-06 + GAP-07
  plan-07-explorer-backend.md    # P7: /api/tree + file_bundle PATH_ESCAPE
  plan-08-explorer-frontend.md   # P8: tree spike + headless-tree build
  plan-09-review-renderer.md     # P9: diff/at/review + reviews.jsonl + Monaco overlays
  plan-10-realtime-history.md    # P10: file_edits/blame/git_log + timeline + file.changed
  RUNBOOK.md                     # this file
  TRACKER.md                     # phase/task statuses (create with P1)
  CHECKPOINT.md                  # canonical anti-erasure narrative (create with P1)
docs/dev/specs/19-project-registry.md  # foundation spec (registry, _root(), onboard, profile)
docs/dev/specs/16-repo-explorer.md     # tree backend+frontend (P7/P8)
docs/dev/specs/17-file-review-renderer.md # diff/at/review (P9)
docs/dev/specs/18-realtime-edit-history.md # edits/blame/git_log/timeline (P10)
lib/cipkg/web_bridge.py          # primary refactor surface (3097 lines, 140 ROOT sites)
lib/cipkg/cli.py                 # cmd_init:420, web subparser:723, handle_web_command:258
web/src/lib/api.ts               # request<T>:3, BASE '/api':1, onboardingApi:883
web/src/App.tsx                  # routes:48-61, onboarding gate:43
web/src/stores/app.ts            # activeProject (added P6)
```

---

## 2. The 10 phases (build STRICTLY in order)

| # | Phase | Verdict |
|---|-------|---------|
| 1 | Registry module (`project_registry.py`) | `python -c "from lib.cipkg.project_registry import get_registry; print(get_registry().home())"` |
| 2 | `_root()` sweep + GAP-01 `_CONFIG_PATH`→fn + GAP-02 tolerant boot | bare-`ROOT` grep gate = 0 hits; console boots from non-CIP folder |
| 3 | Projects REST + GAP-05 auto-register launch root | register/idempotent/NOT_A_DIR round-trip |
| 4 | Onboard POST + profile write + F-11 warning surfacing | `cip init` byte-identical via `init_project`; job streams |
| 5 | Per-project WS + watch + GAP-03 daemon guard | only subscribed project receives its events |
| 6 | Frontend switcher/dashboard/wizard + GAP-04/06/07 | `tsc --noEmit` + `npm run build` green; per-project gate |
| 7 | `/api/tree` + PATH_ESCAPE on `file_bundle` | `../../etc/passwd` → `_err PATH_ESCAPE` |
| 8 | Tree frontend (spike gate → headless-tree) | lazy 1-fetch-per-expand; 50k-file smoke |
| 9 | Diff/at/review + `reviews.jsonl` + Monaco | comments persist across reload; source never written |
| 10 | edits/blame/git_log + timeline + `file.changed` | watch on → open file refreshes without reload |

Each phase doc has **atomic tasks** shaped: edit target (`file:line`) → exact change → verify command →
fail-state. Phase N assumes 1..N-1 merged + green (each ends with its documented verify / `cip selftest`).

---

## 3. How to work (sequential, token-bounded)

- **One phase at a time; one atomic task at a time.** Never start P-N+1 while P-N's acceptance list is
  unchecked.
- **Todo list = the anti-erasure anchor** (AGENTS.md 120K rule). Before ANY work, build the todo list
  from the ACTIVE plan doc's tasks — never from memory.
- **Read, then act, then persist.** Extract only what the current task needs from source, act, record
  the result, drop the rest. Do not hold whole files in context longer than needed.
- **Anchors must be verified at write time.** Every plan line ref is checked against source before
  trust; if a line moved, fix the plan doc, don't guess.
- **Verify with the command in the task.** A task is not done until its verify command exits green and
  the acceptance box is checked in the plan doc.

---

## 4. The mandatory loop (per atomic task)

1. **Restore-read** (see §6.1) — always, even mid-session.
2. **Todo-design** — pull the task's steps + its verify command into the todo list (each todo cites the
   plan doc + task id, e.g. `P2 T2.4 _CONFIG_PATH→fn — plan-02, verify: /api/config/full`).
3. **Ground** — grep/read the exact `file:line` the task names; update the plan doc if the anchor moved.
4. **Act** — make the change (additive-only endpoints; `_root()` never `ROOT`; NFR-3 heavy ops as jobs).
5. **Verify** — run the task's command; capture output.
6. **Checkpoint** — on task completion update `CHECKPOINT.md` (what landed, numbers, next unit); on phase
   completion also flip the `plans-00-index.md` row + mark in TRACKER.
7. **Never claim green without running the command.** Evidence before assertions (verification rule).

**Do not fix GAP-01..07 in isolation** — each is already an atomic task inside its phase (P2 T2.4, P2
T2.1, P5 T5.4, P6 T6.6, P3 T3.4, P6 T6.1, P6 acceptance). If you find NEW missing work, add it as a
`GAP-0N` task inside the owning phase + update `plans-00-index.md` GAP table, then continue.

---

## 5. Grounding truth & invariants (never violated)

- **Docs are never ground truth** — source is. If a plan anchor disagrees with code, the plan is stale; fix the plan.
- **`_root()` everywhere new; `ROOT` never** in new endpoint code. Legacy `?repo=`-less calls behave as today.
- **Registry id = normalized abs path** (Windows-case-insensitive); a hostile `?repo=` string can never
  inject a path — registry keys are the only accepted values.
- **Read-only DB on GET**; heavy ops (`sync`, `index`, `onboard`) run as `_job_*` background jobs.
- **Comments in code are preserved verbatim** (owner rule) — refactors keep every existing comment.
- **Console is read-only for source files**; the only writes are `.cip/` config, registry JSON, `reviews.jsonl`.
- **Envelope never changes:** `_ok`/`_err` (`web_bridge.py:64/68`) and `request<T>` unwrap in `api.ts:15`.

---

## 6. Autonomous-run survival discipline (todos & checkpoints — **MANDATORY**)

Autocompaction WILL fire on long sessions and erase working memory. The **todo list is the only
structure that survives compaction.** Every todo list this upgrade touches MUST be built so a
freshly-compacted agent is force-returned to the persisted docs:

### 6.1 Restore-read (FIRST todo item, ALWAYS)
`[restore] Read RUNBOOK.md §0/§6 + plans-00-index.md + the active plan-NN doc + its spec + TRACKER/CHECKPOINT`

### 6.2 Checkpoint (LAST todo item, ALWAYS)
`[checkpoint] Update TRACKER.md + CHECKPOINT.md + plans-00-index.md row for <phase>`

### 6.3 Every work todo references the docs
Each todo MUST cite the plan doc + task id + verify command (e.g. `P4 T4.1 extract init_project —
plan-04, verify: cip init in scratch`). **No bare todos** — a standalone todo is un-resumable after
compaction. Re-derive tasks from the ACTIVE plan doc, never from memory of what you "were doing".

### 6.4 Re-anchor before any work — always
On EVERY session regardless of apparent context (including right after compaction), the first executed
action is the `[restore]` item. Cheap insurance; never skip. If there is any doubt about phase state,
`[restore]` answers it from TRACKER/CHECKPOINT, not memory.

### 6.5 Checkpoint at every milestone
After any landed task (especially a GAP fix or phase-complete), write `CHECKPOINT.md`: status, verified
commands + their output summary, decisions, next unit. It is the canonical anti-erasure mechanism.

### 6.6 Never derive state from memory
Progress comes ONLY from TRACKER (status) + CHECKPOINT (narrative) + plan docs (acceptance boxes) +
source. If memory and docs disagree, **docs win** — re-anchor immediately.

### 6.7 Hand off cold
End-of-session checkpoint must let a fresh agent with zero prior context resume the next unit (phase
number, task id, exact next command) without re-reading this whole runbook. Include a one-line "where I
am / what's next" at the top of CHECKPOINT.md.

---

## 7. Status vocabulary

- **Phase:** `pending → in-progress → tasks-green → acceptance-checked → done (index row flipped)`.
- **Task:** `todo → grounded → implemented → verified (command run) → acceptance boxed`.
- **GAP:** `identified → folded-into-phase → implemented → verified`.
- **Acceptance:** a box is checked only after its verify command actually ran and exited green.
