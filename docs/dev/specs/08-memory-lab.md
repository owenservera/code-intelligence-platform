# SPEC-08 — Memory Lab (FR-8)

- **Requirement source:** `05-requirements.md` §2 FR-8, §7.1(9)(10), ISSUE-102/103
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{learning_system,memory/*}.py`
- **Build order dependency:** SPEC-02 (jobs), SPEC-03 (daemon/consolidation), SPEC-04 (sync/snapshots).

---

## 1. Goal & owner intent

Full memory lab: Temporal Knowledge Graph (facts with valid_from/until, confidence, source),
Episodic memory (agent experiences with embeddings), consolidation daemon (episodes → semantic
patterns, promote >0.7 confidence), learning system (actions → patterns → personalized
suggestions), user profile + recall view. Owners want "show whatever intelligence CIP generates,
visually intuitive" (§7.1-10) and a "full memory lab" (§7.1-9) — not just a recall box.

## 2. Truth-grounded core surface (verified 2026-08-15)

| Need | Core call (verified) | Returns |
|---|---|---|
| Semantic facts | `memory.temporal_graph.TemporalKnowledgeGraph` `temporal_graph.py:23` | `add_fact/query_facts/query_history(?)/...`; schema `temporal_facts(id, subject, predicate, object_value, valid_from, valid_until, confidence, source, metadata, created_at)`; time-boxed validity |
| Agent memory | `AgentMemory` `temporal_graph.py:182` | `remember/learn_preference/...` (semantic layer) |
| Episodic | `memory.episodic.EpisodicMemory` `episodic.py:20` | `record_episode/query_episodes/recall_similar`; schema `episodes(id, timestamp, episode_type, context, outcome, metadata, embedding BLOB)` |
| Experience logger | `AgentExperienceLogger` `episodic.py:134` | recorder wrapper |
| Consolidation | `memory.consolidation.MemoryConsolidator` `consolidation.py:12` | `consolidate(lookback_days=7)`; patterns → promote if confidence>0.7 (`consolidation.py:35`); error/success pattern analysis |
| Consolidation daemon | `run_consolidation_daemon(db_path, interval_hours=24)` `consolidation.py:132` | blocking loop |
| Learning store | `LearningSystem(root)` `learning_system.py:673`; `PatternStorage` `learning_system.py:86` | actions JSONL in `<data_dir>/learning_data/actions/YYYY-MM-DD.jsonl`; profiles JSON; `memory.db` + `episodes.db` under learning_data |
| Record action | `learning_system.record_user_action(root, action_type, **kwargs)` `learning_system.py:832` | convenience → `LearningSystem(root).record_action` |
| Personalization | `get_personalized_suggestions(root, user_id='default', context)` `learning_system.py:849` | ranked suggestions |
| Recall | `LearningSystem.recall_relevant(query)` `learning_system.py:785` | episodes (recall_similar) + facts (query_facts subject=agent, predicate=command:...) sorted by recency, top 10 |
| Pattern analysis | `PatternAnalyzer.analyze_user_patterns(user_id)` `learning_system.py:354` | command sequences, time patterns, error recovery, preference weights |
| Profile | `UserProfile` `learning_system.py:58`; `PersonalizationEngine.update_profile` `learning_system.py:631` | per-user learning state |
| Memory dir | `data_dir(root)` + `learning_data/` | storage location (`learning_system.py:98`) |

## 3. UI/UX contract

- **Memory lab view** (tabs):
  1. **Temporal graph** — visual timeline of facts (SPEC-09 F1? no — this is its own small
     timeline): subject→predicate→object chips, `valid_from→valid_until` bar, confidence meter,
     source badge; filter by subject/predicate/at_time (point-in-time replay slider).
  2. **Episodes** — table (type, timestamp, outcome, context summary, embedding present);
     click → detail; "recall similar" search box → `recall_similar` results.
  3. **Patterns / consolidation** — consolidator output: pattern type (error/success), key,
     value count + common context, confidence; "Run consolidation now" → SPEC-02 job
     (writes promoted facts into graph). Consolidation daemon status from SPEC-03.
  4. **Learning profile** — per-user (default) profile: `analyze_user_patterns` breakdown
     (frequent command sequences, peak hours, recovery strategies, suggestion preferences);
     personalized suggestions list with rationale (`get_personalized_suggestions`).
  5. **Recall** — global recall search → `recall_relevant` (episodes + facts merged, recency-
     sorted, top 10); each with type badge + timestamp + outcome.
- **Write path:** frontend emits `record_user_action` on meaningful actions (open file, run
  audit, sync, search with no results, etc.) via `POST /api/memory/action` — telemetry is
  stored, driving personalization (§7.1-9). Owner keeps control: "Clear memory" reset action.
- **States:** memory.db not yet created (lazy `AgentMemory`) → empty-state explaining memory
  builds from usage; consolidation daemon not running → banner with "start" (SPEC-03);
  embedding absent → "recall similar" degrades to recency sort (episodic.recall_similar).

## 4. API / WS contract

REST:
- `GET /api/memory/overview` → `{facts_n, episodes_n, patterns_n, profiles, last_consolidation,
  daemon_running}`.
- `GET /api/memory/facts?subject=&predicate=&at=` → `TemporalKnowledgeGraph.query_facts`.
- `GET /api/memory/episodes?type=&limit=` → `EpisodicMemory.query_episodes`.
- `GET /api/memory/recall?query=` → `LearningSystem.recall_relevant`.
- `GET /api/memory/patterns?user_id=` → `PatternAnalyzer.analyze_user_patterns`.
- `GET /api/memory/suggestions?user_id=&context=` → `get_personalized_suggestions`.
- `POST /api/memory/action` `{action_type, ...}` → `record_user_action` (200, no echo).
- `POST /api/memory/consolidate` `{lookback_days?}` → `{job_id}` (SPEC-02 job → writes facts).
- `POST /api/memory/clear` (confirm) → wipes memory.db/episodes.db + learning_data.

WS (`/ws`, SPEC-14): `memory.updated` after consolidation job (new pattern/facts counts).

## 5. Data contract

- Reads/writes the memory subsystem's own SQLite files (`learning_data/memory.db`,
  `learning_data/episodes.db`) + JSONL actions/profiles — **separate from `index.db`**.
- `run_consolidation_daemon` uses the **same db_path for graph and episodic** (`consolidation.py:15-18`),
  i.e. both share `memory.db`? — verify at build: `AgentExperienceLogger`/`EpisodicMemory(db_path)`
  and `TemporalKnowledgeGraph(db_path)`; if `LearningSystem` passes distinct paths
  (`memory.db` vs `episodes.db`), consolidation's single-path assumption conflicts.
  → **CORE-32** below.

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge.memory_overview(root)`** — counts + last_consolidation + daemon flag from the
  memory files (cheap COUNTs, cached 5 s).
2. **Consolidation-as-job adapter** — wrap `MemoryConsolidator.consolidate` in SPEC-02 job with
  progress (query episodes → extract patterns → promote); write result summary to events.
3. **Daemon-managed consolidation** — tie to SPEC-03 auto-managed daemon: if enabled, run
  `run_consolidation_daemon` in the managed process (or a thread) with stop flag; surface
  schedule (`interval_hours`) in settings (SPEC-10).
4. **`record_user_action` plumbing** — server-side session/user_id default; batch writes
  (JSONL append is per-call; batch to avoid I/O on every click).

## 7. Core issues / risks (flagged, grounded)

- **CORE-31 — memory and index are separate DBs; consolidation daemon blocking loop.**
  `run_consolidation_daemon` `consolidation.py:132` is a blocking `while` loop like `watch` —
  must run in a managed thread/process with stop (same pattern as CORE-16). *(New issue.)*
- **CORE-32 — db_path collision/confusion: consolidator assumes one shared db for graph +
  episodic (`consolidation.py:17-18`), but `LearningSystem` creates separate `memory.db` and
  `episodes.db` (`learning_system.py:693-706`).** Consolidation pointed at the memory subsystem
  files may query an empty episodic table (both schemas in one file is fine, but the daemon
  must be given the right path). → Bridge must pass `memory.db` (shared) or the daemon path
  used by the active daemon; verify before wiring. *(New issue.)*
- **CORE-33 — `recall_relevant` semantic branch queries `predicate=command:{query[:50]}`
  (exact substring).** `learning_system.py:813-816` — recall of facts is **not semantic**,
  only episodic uses embeddings. → Surface as "facts match by command tag"; don't promise
  semantic fact recall in UI copy. *(New issue.)*
- **CORE-34 — memory files are outside the index lifecycle (no sync/audit visibility).**
  `data_dir(root)/learning_data` — backups/vacuum (SPEC-04) don't cover them; "Clear memory"
  is the only hygiene. → Memory lab shows disk usage + last write; document that vacuum does
  not prune memory.
- **Watch: personalization is per `user_id='default'`** — single-user assumption; fine for v1
  but note in UI ("profile: default").
- **Watch: episode embeddings depend on embedder availability** (`episodic.py` embedding BLOB
  filled by logger) — if embedder off, `recall_similar` falls back; surface embed status.

## 8. Acceptance checks (from §6 / §7.5)

- [ ] Temporal facts render with validity bars + confidence + point-in-time slider.
- [ ] Episodes list + recall-similar + detail view work.
- [ ] Consolidation runs as a job; patterns with confidence>0.7 promote to facts; WS update.
- [ ] Learning profile (patterns/suggestions) renders from `analyze_user_patterns`/suggestions.
- [ ] `POST /api/memory/action` records telemetry; personalization improves suggestions.
- [ ] Consolidation daemon managed (start/stop/schedule) via SPEC-03 + SPEC-10.
- [ ] CORE-32 db-path verified & fixed in bridge before wiring consolidation.
