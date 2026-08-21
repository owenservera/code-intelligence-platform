# SPEC-05 — Search & Navigation (FR-5)

- **Requirement source:** `05-requirements.md` §2 FR-5, §7.1(2)(4)(6), ISSUE-108
- **Grounding verified:** 2026-08-15 against `lib/cipkg/retrieve.py`
- **Build order dependency:** SPEC-01 (shell/global search), SPEC-14 (WS), SPEC-09 (graph viz).

---

## 1. Goal & owner intent

Global hybrid search box reachable everywhere (Ctrl+K doubles as command palette + search);
deep search view with filters (type, tier, k, backend-matched badges); symbol lookup; graph
traversal around a symbol/file. Code search is a primary daily activity; the console is an
**oracle** — searches must surface CIP's full intelligence about matches (§7.1-5).

## 2. Truth-grounded core surface (verified 2026-08-15)

| Need | Core call (verified) | Returns |
|---|---|---|
| Hybrid search | `retrieve.search(root, query, k=10)` `retrieve.py:128` | list of `{chunk, path, lines:[s,e], symbol, score, matched:[fts\|vec], snippet(≤360), tier}` |
| Lexical only | `retrieve.lex_search(con, query, k)` `retrieve.py:17` | FTS5 (tokens → `chunks_fts2` → `chunks_fts`) + LIKE fallback |
| Vector only | `retrieve.vec_search(con, cfg, query, k)` `retrieve.py:44` | knn on normalized matrix |
| Fusion | `retrieve.rrf(lists, k=60)` `retrieve.py:64` | RRF merge |
| Rerank | `retrieve.rerank(query, items, con, cfg)` (imported) | order + annotations |
| Symbol lookup | `retrieve.find_symbol(root, name, limit=20)` `retrieve.py:191` | exact NOCASE → LIKE; symbols with relation counts |
| Graph traversal | `retrieve.graph(root, sid, direction="both", depth=1)` `retrieve.py:228` | `{root, nodes≤200, edges≤400}`; depth clamped 1–3 |
| Context pack | `retrieve.context(root, query?, symbol?, budget?)` `retrieve.py:267` | token-budgeted `sections[{prio,why,text,meta}]` + `next_ops` |
| File history | `retrieve.history(root, path, n=8)` `retrieve.py:374` | commit history for path |
| Edge kinds | `edges` table | contains/exports/imports/calls/references/tested_by/extends/implements |
| Search config | `config.default.toml` `[retrieval]` lexical_k, vector_k, context_budget_tokens | tuning knobs |

**Result shape note:** `search()` returns a **list** (not `{results: ...}`). `server.py` wraps it
in `{"results": [...]}` (`server.py:117`). The bridge must normalize consistently (list for API).

## 3. UI/UX contract

- **Global search (Ctrl+K):** same overlay as the palette — typeahead over both commands and
  code; `enter` on a code hit opens the deep panel, on a command opens its form. Backend-matched
  badges (`fts`/`vec`) on results; tier chips.
- **Deep search view:** query box + filters (kind/type, tier, `k`, min-score); results list with
  snippet, path:lines, matched badges; click → deep file panel (SPEC-06). Re-run via search API.
- **Symbol view:** `find_symbol` result cards (qualified name, kind, path, relation counts);
  click symbol → graph.
- **Graph view (entry):** `graph(sid)` around a symbol/file; used by E1 3D (SPEC-09) and the
  deep panel. Direction + depth controls (1–3); 200/400 cap surfaced ("subgraph of N").
- **Context view:** render `context()` sections (why/meta/text) as collapsible cards; `next_ops`
  become action buttons (SPEC-02 no-dead-buttons).
- **States:** empty-query guard; embedding-warm note if first search triggers `_ensure_embedded`
  (BUG-010 — surface as "warming embedder…" background job, not a hang).

## 4. API / WS contract

REST:
- `GET /api/search?q=&k=&tier=&kind=` → `{results:[...], query, took_ms, matched_fallback?}`.
- `GET /api/symbols?name=&limit=` → `find_symbol` normalized.
- `GET /api/graph?id=&direction=&depth=` → `graph()` payload (SPEC-09 consumes this).
- `GET /api/context?query=|symbol=&budget=` → `context()` + normalized next_ops.
- `GET /api/history?path=` → `history()`.

WS (`/ws`, SPEC-14):
- `search.result {id, query, results}` pushed when a long/external search completes
  (optional; searches are fast — REST primary).

## 5. Data contract

- Purely reads existing `chunks`/`chunks_fts*`/`vectors`/`edges`/`symbols`. No new tables.
- Search result → deep panel handoff via `path`+`symbol`; graph handoff via `sid`.

## 6. Backend additions (lib/cipkg in scope)

1. **Normalized search envelope** in `web_bridge` — consistent `{results, query, took_ms}`
  wrapper over `retrieve.search` + `_external_search` fallback flag; filter param passthrough
  (tier/kind currently NOT filterable in `search()` — add optional `tier`/`kind` WHERE clauses
  in the bridge's own query, not core, or extend `search`).
2. **Tier/kind filter support** — either extend `retrieve.search` (core) or implement filtered
  re-query in the bridge (keeps core intact; prefer bridge).
3. **Graph metadata for 3D** — SPEC-09 needs node labels (kind, path, severity) + link kinds,
  not just ids; add a `web_bridge.graph_payload(root, sid, ...)` that decorates `graph()`
  output from `symbols`/`edges` (cap-friendly).

## 7. Core issues / risks (flagged, grounded)

- **CORE-19 — `search()` blocks on `_ensure_embedded` (BUG-010):** `retrieve.py:171` may
  auto-embed (120 s) on first search after index-add. → the UI must run first-search through a
  background job + "warming" state, or pre-warm embedder at server start (SPEC-03 auto-manage).
  *(Linked to BUG-009/010; reconfirmed in code.)*
- **CORE-20 — `retrieve.context()` caller/callee labels swapped (BUG-008).** `retrieve.py:267`
  context sections label relationships incorrectly. The deep panel must not render raw section
  `why` strings as relationship names until fixed, or render from `edges` directly with correct
  direction. *(Pending fix in core or compensated in bridge.)*
- **CORE-21 — `search()` has no tier/kind filter params** (`retrieve.py:128` signature).
  FR-5 requires "filters (type, tier, k)". → bridge-side filtering or core extension
  (addition 2). *(New issue.)*
- **CORE-22 — `graph()` returns ids only, no labels/kinds for nodes** (`retrieve.py:265`
  `sorted(seen)`). 3D + deep-panel graphs need node metadata (kind, path, severity).
  → `graph_payload` decorator (addition 3). *(New issue.)*
- **Watch: `lex_search` FTS5 phrase-AND over-restriction (BUG-021)** — search quality; note in
  UI (offer raw LIKE fallback toggle if implemented).
- **Watch: external search (`_external_search`, `retrieve.py:81`) subprocess + redundant
  `except (…, Exception)` (BUG-022)** — only active if config routes searches externally;
  default internal. Flag if enabled.

## 8. Acceptance checks (from §6 / §7.5)

- [ ] Ctrl+K searches both commands and code; enter navigates correctly.
- [ ] Deep search filters (tier/kind/k) work and return results.
- [ ] Symbol lookup → graph → deep panel handoff works end-to-end.
- [ ] First-search embed-warm is a visible background state, never a request hang.
- [ ] Graph payload carries node labels + link kinds for 3D rendering (CORE-22 resolved).
- [ ] Context sections render with correct relationship labels (CORE-20 resolved or compensated).
