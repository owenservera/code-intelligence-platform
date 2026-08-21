# SPEC-13 — Oracle / Intelligence Surface (FR-13)

- **Requirement source:** `05-requirements.md` §2 FR-13, §7.1(6)(10), ISSUE-109/113
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{predict,suggestion_engine,intelligent_executor,workflow_engine,summarize}.py`
- **Build order dependency:** SPEC-02 (dispatch), SPEC-05 (context/graph), SPEC-06 (deep panel),
  SPEC-08 (memory/personalization), SPEC-09 (vis).

---

## 1. Goal & owner intent

The console is an **oracle + control surface** (§7.1-5): it surfaces every piece of intelligence
CIP generates, visually and intuitively (§7.1-10). FR-13 = the intelligent layer on top of raw
tools: predictive next-context, adaptive context packs, generated suggestions with rationale,
workflow orchestration, repo summary narrative, and a "what should I do next" engine (the magic
in §7.1-3). No dead buttons: every suggestion maps to a runnable SPEC-02 action.

## 2. Truth-grounded core surface (verified 2026-08-15)

| Need | Core call (verified) | Returns |
|---|---|---|
| Next-context predict | `predict.predict_next_context(root, current_operation, current_symbol?, current_query?)` `predict.py:12` | `[{tool, args, confidence, reason}]` (symbol/impact/search/graph/broken/... branches) |
| Adaptive context | `predict.context_adaptive(root, query?, symbol?, base_budget=6000)` `predict.py:73` | budgeted context pack (complexity-adjusted) |
| Edit context | `predict.suggest_context_for_edit(root, file_path, line?)` `predict.py:165` | symbols/deps/tests/gaps for edit |
| Suggestions | `suggestion_engine.SuggestionEngine(root, config).generate_suggestions(context, max=5)` `suggestion_engine.py:649` | ranked `Suggestion` list (Health/Index/Git/Stack/Pattern analyzers + RankingEngine + FilterEngine) |
| Analyzers | `HealthAnalyzer` `:51` `IndexAnalyzer` `:111` `GitAnalyzer` `:199` `NextJSAnalyzer` `:313` `PythonAnalyzer` `:344` `PatternAnalyzer` `:396` | per-domain signal generation |
| Workflow defs | `workflow_engine.list_workflows(root, config)` `workflow_engine.py:892` + `WorkflowRegistry` `:94` | definitions + steps |
| Workflow exec | `workflow_engine.execute_workflow(root, workflow_id, config)` `workflow_engine.py:885` + `WorkflowExecutor` `:258` | execution w/ step status |
| Intent dispatch | `intelligent_executor.IntelligentCommandExecutor` `intelligent_executor.py:67`; `execute_command` `intelligent_executor.py:160` | maps intent → command |
| Repo summary | `summarize.summary(root, path=None)` `summarize.py:126` / `_repo_summary` `:97` / `map_` `:136` | narrative + subsystems |
| Personalization | `learning_system.get_personalized_suggestions(root, user_id, context)` `learning_system.py:849` | learned suggestions (SPEC-08) |
| Briefing | `dashboard.py:briefing` (§7.1-16) | staff-engineer briefing notes (REPLACED — see CORE-51) |

**Data sources feeding analyzers:** `analysis` (health), indexer stats (index), gitindex
(git), stack rules (stack), learning patterns.

## 3. UI/UX contract

- **Oracle rail** (command center, right side): "What should I do next" card stack —
  `SuggestionEngine.generate_suggestions()` (health/index/git/stack/pattern) each with
  priority chip + rationale + **runnable action** (SPEC-02 dispatch). Re-run button + "why"
  tooltip (which analyzer produced it).
- **Predictive next-context:** contextual strip under any active tool — after running
  `graph(id=X)`, show `predict_next_context("graph", symbol=X)` chips (tool + reason + conf %)
  → click runs the predicted tool (no dead buttons; SPEC-02 verifies each).
- **Adaptive context packs:** deep panel "Context" section renders `context_adaptive` (budget
  dial, sections with why/meta, complexity badge from `_assess_complexity`).
- **Workflows:** workflow browser (`list_workflows`): card per workflow + steps timeline;
  "Run workflow" → SPEC-02 job with per-step status (`WorkflowExecutor`). Progress via WS.
- **Repo story:** "About this repo" card — `summary()` narrative + `map_` subsystems +
  hotspots; the oracle's opening statement on landing (W5 seed).
- **Briefing:** staff-engineer briefing notes rendered as a collapsible "Briefing" card
  (CORE-51 — from `dashboard.py:briefing`; verify it's importable without the TUI).
- **Personalized:** `get_personalized_suggestions` surfaced under "For you" (SPEC-08), with
  learning-source badge.
- **States:** empty index → "run sync first"; analyzer failure → that card omitted (not a dead
  card) with a subtle log note; workflow list empty → "no workflows defined".

## 4. API / WS contract

REST:
- `GET /api/oracle/next?operation=&symbol=&query=` → `predict_next_context`.
- `GET /api/oracle/context?symbol=|query=&budget=` → `context_adaptive` (+complexity).
- `GET /api/oracle/suggestions?max=` → `SuggestionEngine.generate_suggestions` (cached 30 s).
- `GET /api/oracle/workflows` → `list_workflows`.
- `POST /api/oracle/workflows/{id}/run` `{config?}` → `{job_id}` (SPEC-02; step events WS).
- `GET /api/oracle/repo` → `summary()` + `map_` + hotspots (W5 seed).
- `GET /api/oracle/briefing` → briefing notes (CORE-51).
- `POST /api/oracle/execute` `{intent}` → `intelligent_executor.execute_command` (SPEC-02
  fallback for fuzzy intents not in command table).

WS (`/ws`, SPEC-14): `workflow.step {id, step, status}`, `oracle.suggestions` (after
sync/audit/git job refreshes inputs), `job.progress/done`.

## 5. Data contract

- Reads all index + git + learning surfaces; no new tables.
- Workflow executions are ephemeral (in-memory) unless core persists them — verify
  `WorkflowExecution` persistence; if not, bridge records run history in `events`.

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge.oracle_bundle(root)`** — compose suggestions + next-context + repo story +
  briefing + "for you" in one cached payload (30 s) for the command-center rail.
2. **Workflow-as-job adapter** — wrap `WorkflowExecutor` in SPEC-02 job model, streaming
  `workflow.step` events; record run history in `events`.
3. **Suggestion→action mapping** — every `Suggestion` carries a `tool`+args that must resolve
  through SPEC-02 dispatch; `web_bridge.resolve_suggestion(s)` validates/executes it (no dead
  buttons).
4. **Briefing adapter (CORE-51)** — extract briefing logic from `dashboard.py` into an
  importable `web_bridge.briefing(root)` (or import `dashboard.briefing` if side-effect-free).

## 7. Core issues / risks (flagged, grounded)

- **CORE-51 — `dashboard.py:briefing` lives in the legacy Mission Control module (TUI); the
  oracle needs it without pulling in the terminal surface.** Importing `dashboard.py` may pull
  curses/rich UI deps. → Extract briefing into a leaf module or import lazily with fallback.
  *(New issue; §7.1-16 explicitly wants these briefing notes.)*
- **CORE-52 — `SuggestionEngine` imports `repo_settings.detectors` and swallows ImportError to a
  `GenericStackAnalyzer`; per-analyzer failures print to stdout, not the log.**
  `suggestion_engine.py:636-659` — a throwing analyzer silently drops its signals. → Bridge must
  capture analyzer status (which analyzers produced suggestions) for the "why" tooltip; log via
  `log_swallowed`, not `print`. *(New issue.)*
- **CORE-53 — `predict_next_context` reasons are hardcoded per operation branch** `predict.py:19-60`
  — they don't actually learn from `learning.py` despite the docstring ("Applies learning-based
  confidence adjustments"). Confidence values are static. → UI labels confidence as "estimated";
  tie to learning only when `learning.py` adjustments are real. *(New issue.)*
- **CORE-54 — `workflow_engine` step/state manager persistence unknown.** `WorkflowExecution`
  (state manager `:124`) — verify whether runs persist across server restarts; if ephemeral,
  run history lives in `events` (bridge). *(Verify-at-integration.)*
- **Watch: `intelligent_executor.execute_command` vs SPEC-02 `call_tool` table** — two dispatch
  paths (intent-based vs table). Oracle "execute intent" uses executor as fallback; command
  center uses the table. Keep both but label provenance (CORE from SPEC-02 §3).
- **Watch: suggestions can point at missing data (stale git, empty index)** — each suggestion
  card shows its source analyzer + a "needs sync" marker when inputs are stale (SPEC-04).

## 8. Acceptance checks (from §6 / §7.5)

- [ ] Oracle rail: suggestions with priority + reason + runnable action; re-run + why works.
- [ ] Predictive next-context chips appear contextually; clicking runs the tool (no dead buttons).
- [ ] Adaptive context pack with budget dial + complexity badge renders.
- [ ] Workflow browser + run (step status via WS); run history recorded.
- [ ] Repo story + briefing cards render from real summaries (CORE-51 resolved).
- [ ] "For you" personalization shown with learning-source badge.
