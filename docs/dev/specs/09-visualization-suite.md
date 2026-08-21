# SPEC-09 — Visualization Suite (FR-9)

- **Requirement source:** `05-requirements.md` §2 FR-9 (A1–G2), §7.1(8)(11), ISSUE-107/108
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{store,gitindex,summarize,analysis,stack/audit,memory/*}.py`
- **Build order dependency:** SPEC-01 (shell/charts theme), SPEC-04 (snapshots), SPEC-07 (findings),
  SPEC-05 (graph payload), SPEC-08 (memory), SPEC-14 (WS live refresh).

---

## 1. Goal & owner intent

Top-of-the-line visualization: full chart set (A–G) rendered from **real data with
intelligence annotations**; flagship = **3D interactive code graph** (E1) with node-kind icons +
severity/link coloring, zoom/pan/rotate, click-to-expand, search highlight, 2D LOD fallback (E2).
Trends (A2/B1/B2/B3/D2) come from the `snapshots` table (SPEC-04), retained indefinitely. This
spec is the *rendering + data contract*; each group's data source is a verified core function.

## 2. Chart groups → data sources (all verified 2026-08-15)

**A. Health & score**
- A1 radial gauge + component breakdown → `analysis.repo_health_report().overall_score` +
  `_calculate_health_score` weighted components (`analysis.py:35-82`).
- A2 trend → `snapshots` (SPEC-04 §5) series `overall_score`.
- A3 quality gate → composite of `audit.summarize` (critical/high) + freshness; "why" from
  `_generate_recommendations` / health components.

**B. Index & growth**
- B1 files/symbols/chunks/edges/vectors over syncs → snapshot series (each sync writes counts;
  `indexer.compute_stats` `indexer.py:285` for live).
- B2 vector coverage % (vectors/chunks) → live COUNTs (`store.py` tables) + snapshot series.
- B3 freshness timeline (last_sync gaps) → `events` (kind=sync ts) + `meta.last_sync`; gaps =
  diff between consecutive sync events.

**C. Git & activity**
- C1 commit velocity (12-week) → `commits` table (sha, ts) grouped by week (`gitindex.git_index`
  populates `commits`/`commit_files`).
- C2 hotspots horizontal bar + churn-vs-size scatter → `gitindex.hotspots(root, k)` (`gitindex.py:58`)
  score + `files.size/lines` for size axis.
- C3 co-change pairs graph (edges kind=co_change) → `gitindex` edges (`gitindex.py:43-53`,
  co_change_min≥2, top 500 pairs); render coupled files.
- C4 activity feed from `events` (ts, kind, payload) → timeline feed; kinds incl. sync/index/memory.

**D. Quality & debt**
- D1 findings by severity + by rule → `audit.summarize` + `audit.findings` (`stack/audit.py:41/48`).
- D2 opened vs fixed over time → snapshot `by_severity` + `status` transitions (`findings.ts` +
  audit upsert `audit.py:34-37`); needs snapshot series.
- D3 tech debt by category → `_inventory_technical_debt` (`analysis.py:171`).
- D4 quick wins → `stack.audit.quick_wins` (`audit.py:122`).
- D5 per-language breakdown → `files.language` COUNT/GROUP BY (schema `store.py:11`).

**E. Code graph (3D)**
- E1 3D force graph → `retrieve.graph(root, sid, direction, depth)` (`retrieve.py:228`,
  cap 200 nodes / 400 edges) + `web_bridge.graph_payload` (SPEC-05 add 3) decorating nodes with
  kind/path/severity + link kinds; visual indicators per §7.1-8.
- E2 2D LOD fallback → render subgraph on demand via `graph_payload` per-node expansion;
  threshold: nodes > 200 or edges > 400 → LOD prompt.

**F. Memory & signals**
- F1 temporal facts timeline → `TemporalKnowledgeGraph.query_facts` (`temporal_graph.py:82`)
  validity bars + confidence bubbles (SPEC-08).
- F2 episodes timeline colored by outcome → `EpisodicMemory.query_episodes` (`episodic.py:20`).
- F3 broken signals (failing tests + type errors over 14d) → `signals` table (kind, path, ts;
  schema `store.py:51`) + `commit_files` recency; 14-day window.
- F4 embedding panel (model, backend, dim, vector coverage gauge, warm state, queue) →
  `embed.service_health` (`embed.py:44`) + `vectors(model)` counts + `meta` embed config.

**G. Repository map**
- G1 zoomable directory tree-map (hot/cold + file count coloring) → `summarize.map_`
  (`summarize.py:136`: top-level dirs files/symbols + `gitindex.hotspots`) + `files` per dir.
- G2 subsystem overview → `summarize.map_` / `_repo_summary` (`summarize.py:97`) text overview.

## 3. UI/UX contract

- **Dashboards view** (route `/dashboards`): tabbed panels A–G; each panel = section header with
  data source label (e.g. "source: analysis.repo_health_report"), chart(s), and empty/none states.
- **3D graph (E1) is a full-screen mode** (SPEC-01 command center deep-link): 
  - Controls: zoom/pan/rotate (orbit), search-highlight (query → matching nodes glow),
    click-to-expand (node → fetch `graph_payload` focus and merge), node-kind icons, severity
    color legend, link-kind color, direction in/out/both, depth 1–3, LOD toggle (E2).
  - Payload cap: initial ≤200 nodes/≤400 edges; expansion is lazy (ISSUE-108).
- **Trends (A2/B1/B2/B3/D2):** Recharts line/area/stacked from snapshot series; hover tooltips
  show snapshot ts + values; zoomable date range.
- **C2 scatter:** x=size(lines), y=churn score; quadrant split with threshold labels; click point
  → SPEC-06.
- **G1 tree-map:** zoomable rectangles, color = hotspot score (hot/cold), size = file count;
  click dir → drill; tooltip file/symbol counts.
- **States:** per-chart empty state ("no snapshots yet — run sync/audit to build history");
  per-panel source-not-applicable (e.g. git tables empty → "run git_index"). Every chart is
  real-data; no placeholder art (CORE-27/CORE-30 guardrails).

## 4. API / WS contract

REST:
- `GET /api/vis/{A1..G2}` → per-chart payload from the mapped source (cached 30–60 s; heavy
  sources cached longer).
- `GET /api/vis/snapshots?metric=&range=` → snapshot series for trend charts.
- `GET /api/vis/graph/focus` → expansion endpoint for E1 click-to-expand (`graph_payload`).
- `GET /api/vis/map` → G1/G2 payload (`summarize.map_` + hotspots).
- `GET /api/vis/signals?days=14` → F3 payload.

WS (`/ws`, SPEC-14): `vis.refresh` pushed when a job completes that changes any chart's source
(sync → B; audit → A/D; consolidation → F; git_index → C) — charts subscribe by group.

## 5. Data contract

- **Snapshots** (SPEC-04 §5) power A2/B1/B2/B3/D2 — the only new persistent table; retained
  indefinitely (§7.1-8). Written after sync/audit/consolidate jobs.
- Read-only consumption of `files/symbols/chunks/edges/vectors/events/commits/commit_files/
  signals/findings/summaries` + memory files. No other new tables.
- E1 payload via `graph_payload` (SPEC-05 add 3): nodes `{id, kind, path, name, severity?,
  score?}`, edges `{src, dst, kind, dir}`.

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge.vis_bundle(group)`** — per-group payload composer + cache (A/C/D/G are query
  sets; B is snapshot-series; E is graph_payload; F is memory/embed).
2. **Snapshot writer hook** (SPEC-04 add 1) extended to capture per-language (D5) and
  per-rule (D2) breakdowns at write time (cheap GROUP BYs, once per job).
3. **`web_bridge.graph_focus(root, sid, depth)`** — expansion fetch for E1, incremental merge
  into client graph; caps maintained server-side (ISSUE-108).
4. **Signal aggregator** for F3 — `signals` query windowed to 14d, grouped by kind/path
  (`web_bridge.signal_window(days)`).
5. **Live refresh bookkeeping** — track which chart groups each job type invalidates
  (SPEC-14 event → `vis.refresh {groups}`).

## 7. Core issues / risks (flagged, grounded)

- **CORE-35 — `git_index` deletes all commits/co_change edges then re-inserts (500-depth).**
  `gitindex.py:30-32` destructive rewrite; runs `git log` subprocess up to 180 s timeout.
  → Must be a SPEC-02 job with progress + confirm; while running, C1/C2/C3 charts show stale or
  "indexing" state. *(New issue.)*
- **CORE-36 — `commits` table has `files_changed` but no per-commit delta lines; churn for C2
  uses file size as proxy.** `store.py:46` + `gitindex` stores file names not line counts.
  → C2 scatter y-axis is `hotspot.score` (recency-weighted) not raw churn; label honestly.
  *(New issue; UI honesty.)*
- **CORE-37 — snapshot series only as good as job coverage; sync/audit/consolidate must all
  write snapshots or trends look dead.** SPEC-04 add 1 defines the writer; if any of the three
  jobs skip it, B1/D2 break. → Enforce snapshot write at each job completion (SPEC-02 job
  completion hook). *(Cross-cutting, flagged here.)*
- **CORE-38 — E1 graph payloads risk client-side blowup: `retrieve.graph` returns up to
  200/400 with no metadata.** `retrieve.py:265` ids only; adding kind/path/severity requires
  per-node queries (N+1) unless batched. → `graph_payload` must batch `IN` lookups (SPEC-15).
  *(Complements CORE-22.)*
- **Watch: D5 language values depend on parser mapping** (`files.language`, `store.py:11`) —
  unknown extensions may be NULL/empty; group as "other".
- **Watch: F4 queue telemetry doesn't exist yet** (CORE-11) — render warm state + model/dim +
  coverage from `embed.service_health` + vectors counts; show queue only when CORE-11 lands.

## 8. Acceptance checks (from §6 / §7.5)

- [ ] A–G panels render real data with source labels; empty states are honest.
- [ ] 3D graph: zoom/pan/rotate, kind icons, severity/link colors, search highlight,
  click-to-expand, 2D LOD fallback, direction/depth controls.
- [ ] Trends (A2/B1/B2/B3/D2) plot from snapshot history; range zoom works.
- [ ] `git_index` runs as job with confirm; C1–C3 reflect indexed git state.
- [ ] F3 signals windowed 14d; F4 shows model/dim/coverage/warm; queue only when telemetry exists.
- [ ] `graph_focus` expansion respects caps server-side.
