# SPEC-06 — Deep File Panel (FR-6)

- **Requirement source:** `05-requirements.md` §2 FR-6, §7.1(5), ISSUE-108/109
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{retrieve,summarize,stack/impact,gapfill,gitindex,predict}.py`
- **Build order dependency:** SPEC-05 (search/graph), SPEC-02 (actions), SPEC-07 (findings).

---

## 1. Goal & owner intent

Clicking a file/symbol result opens a **deep panel**: read-only code viewer (Monaco) + every
piece of CIP's intelligence about that file in one screen — symbols, relationships graph,
impact/blast radius, tests to run, findings, git history, hotspots, gap list, summary. The
console is an **oracle + control surface, NOT a code editor** — read-only viewer, no edit/save
(§7.1-5). Every intelligence block must be real (grounded) — no dead sections.

## 2. Truth-grounded core surface (verified 2026-08-15)

| Need | Core call (verified) | Returns |
|---|---|---|
| File content | read path from repo (core has no "get file" — files on disk) | raw text for Monaco |
| Symbols in file | `symbols` table `WHERE path=?` | kind, name, lines |
| Chunks | `chunks` table `WHERE path=?` | start/end, text, symbol_id |
| Graph | `retrieve.graph(root, sid, ...)` `retrieve.py:228` | nodes≤200/edges≤400 |
| Edge counts | `retrieve.edge_counts(con, sid)` `retrieve.py:186` | `{out:{kind:n}, in:{kind:n}}` |
| File summary | `summarize.file_summary(root, path)` `summarize.py:56` | `{summary, source(structure\|llm), tokens?}` |
| Impact/blast | `stack.impact.impact(root, target=path, depth=2)` `stack/impact.py:28` | `{risk, seed_files, affected_files≤50, affected_count, tests_to_run≤20, routes_affected≤10, open_findings_in_area, hotspot_heat, advice}` |
| Structured impact | `impact_structured(...)` `stack/impact.py:77` | `{risk, untested_files, high_risk_files, ...}` (agent todo style) |
| PR/diff impact | `impact_diff(root, ref="HEAD")` `stack/impact.py:116` | per-commit diff blast radius |
| History | `retrieve.history(root, path, n=8)` `retrieve.py:374` | commits for path |
| Hotspots | `gitindex.hotspots(root, k=15)` `gitindex.py:58` | `[{path, score}]` (co-change heat) |
| Edit context | `predict.suggest_context_for_edit(root, file_path, line=None)` `predict.py:165` | symbols/deps/tests/gaps relevant to edit |
| Coverage | `gapfill.coverage(root)` `gapfill.py:39` | per-file test coverage status |
| Dead code | `gapfill.dead(root, limit=50)` `gapfill.py:92` | candidate dead symbols (may include file) |
| Findings | `findings` table `WHERE path=? AND status='open'` | audit findings (SPEC-07 renders) |
| Routes | `routes` table `WHERE file=?` | API routes hit by this file |
| Vectors | `vectors` table `WHERE chunk_id IN (chunks of file)` | embed coverage for file |

**Gap note:** no core function returns a *file* page bundle; the bridge composes these tables.

## 3. UI/UX contract

- **Layout:** left Monaco read-only (tokens/theme via shadcn; `readOnly: true`, no edit menu);
  right rail = intelligence sections (accordion, lazy-loaded per section).
- **Rail sections (each real):**
  1. **Summary** — `file_summary` text (structure or LLM source badge).
  2. **Symbols** — table (kind icon, name, lines) → click opens graph on that symbol.
  3. **Relations** — `edge_counts` in/out by kind + inline `graph()` mini-map (SPEC-09 embed).
  4. **Impact** — `impact(path)` cards: risk badge (low/medium/high), affected_files
     (click → navigate), tests_to_run, routes_affected, open_findings, hotspot_heat, advice.
  5. **Findings** — open `findings` rows for this file (severity chips) → deep audit (SPEC-07).
  6. **History** — `history(path)` commit list (hash, msg, author, date).
  7. **Coverage & gaps** — `coverage()` per file + `gapfill` dead/circular candidates.
  8. **Edit context** — `suggest_context_for_edit` result (symbols/deps/tests/gaps), for
     "before you edit" advice; rendered read-only, actions become SPEC-02 jobs where valid.
- **Actions (SPEC-02 dispatch, no dead buttons):** "View impact (structured)" → `impact_structured`
  shown as todo-list preview; "Run tests in file" → if tests exist (`tests_to_run`), else
  disabled with reason (per core `advice`).
- **States:** loading (per-section spinner), empty ("no findings — good"), error (missing index/
  not indexed → CTA to SPEC-04 sync). Never show a section shell without data.

## 4. API / WS contract

REST:
- `GET /api/file?path=` → `{path, text, symbols, chunks, routes, findings, vectors_n}` (base bundle).
- `GET /api/file/summary?path=` → `file_summary`.
- `GET /api/file/impact?path=&depth=` → `impact()` (+`impact_structured` on demand).
- `GET /api/file/history?path=&n=` → `history()`.
- `GET /api/file/coverage?path=` → `gapfill.coverage` entry.
- `GET /api/file/context?path=&line=` → `suggest_context_for_edit`.
- `GET /api/file/graph?path=` → `graph_payload` (SPEC-05 addition 3) seeded by first symbol or file.

WS (`/ws`, SPEC-14): none required (all per-file reads are fast); optional `file.updated` event
when a sync touches the file (refresh stale sections).

## 5. Data contract

- Pure reads of `files`, `symbols`, `chunks`, `edges`, `routes`, `findings`, `vectors`,
  `events` + git. No new tables.
- File text read from disk on demand (not stored); cache by mtime in bridge (SPEC-15).

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge.file_bundle(root, path)`** — composes base bundle (symbols/chunks/routes/
   findings/vectors count) in one query set (SQL `IN` batches; avoid N+1 per SPEC-15).
2. **`web_bridge.graph_payload`** reuse (SPEC-05) for the relations mini-map; seed symbol
   selection = first symbol with most out-edges in the file.
3. **Monaco-friendly token/perf prep** — file can be large: chunk lines for viewport; Monaco
   virtualization handles it; keep `text` full but stream/limit for >2 MB (SPEC-15).
4. **Findings-by-file helper** — `findings` filter already in `impact`; expose a
   `web_bridge.file_findings(path)` for the rail (SPEC-07 reuses).

## 7. Core issues / risks (flagged, grounded)

- **CORE-23 — `impact_diff` is subprocess-heavy (git) and unbounded per commit.** `stack/impact.py:116`
  runs `git log`/`diff` per target; on big histories the deep panel "PR mode" could be slow.
  → Run as SPEC-02 background job when called, not in-request; or cap commits. *(New issue.)*
- **CORE-24 — `impact()` uses one `file` OR `symbol` seed; a file with no symbols/tests yields
  sparse advice.** `stack/impact.py:30-38` seeds from exact file path else first symbol;
  `_dependents` only follows `imports/calls/references`. → UI must show "no relationships found"
  state (honest) and offer re-sync (SPEC-04) when edges are stale. *(Low; UI-state guidance.)*
- **CORE-25 — `file_summary` may fall back to structure-only silently (no LLM).** `summarize.py:38`
  `_llm_summary` requires embedder/LLM config; failure path returns structure summary.
  → Surface a "structural summary" source badge; don't imply AI analysis when unavailable.
  *(Grounding for the summary badge in §3.1.)*
- **CORE-26 — `suggest_context_for_edit` (predict.py) imports registry-heavy deps** — verify it
  runs standalone under FastAPI (no CLI globals); if it throws, deep panel context section
  degrades to `impact` + symbols (fallback chain). *(Verify at integration; bridge try/except.)*
- **Watch: Monaco bundles are heavy (~2–3 MB)** — load Monaco lazily only when a file panel
  opens (code-split); keep search/command center lightweight (§7.3 perf).

## 8. Acceptance checks (from §6 / §7.5)

- [ ] Clicking any search/symbol/graph result opens the deep panel; Monaco read-only (no edit).
- [ ] Every rail section renders only if real data exists; empty = explicit "none" state.
- [ ] Impact cards show risk + affected files + tests + routes + advice; file/tests links navigate.
- [ ] History, coverage, findings, summary sections populated and correct.
- [ ] `file_bundle` single-roundtrip; large files stream; Monaco lazy-loaded.
- [ ] No dead buttons: every action maps to a verified core function (SPEC-02 dispatch).
