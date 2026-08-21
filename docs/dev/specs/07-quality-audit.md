# SPEC-07 — Quality & Audit (FR-7)

- **Requirement source:** `05-requirements.md` §2 FR-7, §7.1(8)(12), ISSUE-105/106/109
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{analysis,stack/audit,stack/rules,gapfill}.py`
- **Build order dependency:** SPEC-02 (jobs), SPEC-04 (sync), SPEC-06 (findings deep-link), SPEC-09 (trends).

---

## 1. Goal & owner intent

One "Quality" surface: repo health score, critical/high items, tech debt inventory, hotspots,
audit findings by severity/rule/path with quick-wins, coverage, gap detection (missing docs/tests/
type hints), recommendation list, and quality **trends over time** (B1–B3, D2, §7.1-8). Audit is a
real engine (`stack.audit`) — surface it fully, runnable on demand + scheduled, progress +
summary, findings actionable (no dead rows).

## 2. Truth-grounded core surface (verified 2026-08-15)

| Need | Core call (verified) | Returns |
|---|---|---|
| Health report | `analysis.repo_health_report(root)` `analysis.py:10` | `{overall_score(0–100), critical_issues, high_priority, test_coverage, technical_debt, hotspots, recommendations}` |
| Health score detail | `_calculate_health_score` `analysis.py:35` | weighted: coverage 30% + quality 30% + freshness 20% + complexity 20% |
| Critical issues | `_list_critical_issues` `analysis.py:84` | security findings + untested load-bearing (>5 dependents) |
| High priority | `_list_high_priority` `analysis.py:129` | duplication + very large functions (>100 lines) |
| Tech debt | `_inventory_technical_debt` `analysis.py:171` | test_debt / complexity_debt (>50 lines) / duplication / docs |
| Hotspots | `_identify_hotspots` `analysis.py:214` | dense files + load-bearing symbols |
| Recommendations | `_generate_recommendations` `analysis.py:250` | `{priority, action, impact, effort}` |
| Run audit | `stack.audit.audit(root, refresh=True)` `stack/audit.py:14` | rules → upsert findings (stable sha1 id) → `summarize` |
| Audit summary | `stack.audit.summarize(con)` `audit.py:41` | `{open, by_severity, critical, high}` |
| Findings filter | `stack.audit.findings(root, severity?, rule?, path?, limit=100)` `audit.py:48` | ordered critical→low |
| Structured findings | `findings_structured(...)` `audit.py:59` | agent-edit-ready `{file,line,rule_id,message,suggested_pattern}` |
| Scoped audit | `audit_file` `audit.py:81` / `audit_diff` `audit.py:88` | file-only / working-tree changes |
| Quick wins | `stack.audit.quick_wins(root, limit=10)` `audit.py:122` | open findings with suggestion |
| Coverage | `gapfill.coverage(root)` `gapfill.py:39` | test coverage report |
| Gaps | `gapfill.score(root)` `gapfill.py:208` + dead/circular/migrations/env/logs/metrics/features/deps/api (`gapfill.py`) | gap findings |
| Rules | `stack.rules.run_rules(con, root, cfg)` `stack/rules.py` | rule engine → findings |
| Custom rules | `stack.custom_rules` | user rules (`[audit] custom_rules_path`) |
| Findings table | `findings` | id(sha1), rule, severity, path, line, symbol_id, title, detail, suggestion, effort, ts, status(open/fixed) |

**Config anchors:** `[audit] custom_rules_path`, stack detection; rules severity mapping in `rules.py`.

## 3. UI/UX contract

- **Quality dashboard view** (entry from command-center health chip):
  - **Score ring** (0–100) with component breakdown (coverage/quality/freshness/complexity
    bars) + trend sparkline (SPEC-09 B1, from snapshots).
  - **Tabs:** Critical · High · Findings · Tech debt · Gaps · Recommendations · Coverage.
  - **Critical / High:** cards from `_list_critical_issues` / `_list_high_priority` (type chip,
    title, suggestion, path link → SPEC-06).
  - **Findings:** table with severity chips, rule, path:line, suggestion, effort; filters
    (severity/rule/path) via `audit.findings` params; per-row actions: "Open in file",
    "Structured view" → `findings_structured` shown as copy-ready table.
  - **Tech debt:** `_inventory_technical_debt` category counts + expandable lists.
  - **Gaps:** `gapfill` results grouped (dead code, circular deps, coverage gaps, missing docs/
    tests/type hints via `score`); each with fix suggestion if core provides.
  - **Recommendations:** `_generate_recommendations` list (priority/action/impact/effort badges).
  - **Coverage:** `gapfill.coverage()` per-file coverage table + summary.
- **Run audit:** button → SPEC-02 job (refresh: re-index routes/stack then rules, upsert findings,
  auto-fix stale to 'fixed' — `audit.py:34-37`); progress + summary result; findings refresh live.
  Scheduled audits (cron, §7.4) reuse the same job path.
- **Quick wins:** `quick_wins` rendered as suggested-fix list with "copy suggested pattern".
- **Quality trends (B1–B3, D2):** from snapshot rows (SPEC-04 §5): score over time, findings by
  severity over time, coverage over time, gap count over time. SPEC-09 renders.
- **States:** no findings → celebratory empty state; score neutral (50) for empty repo
  (`analysis.py:40-41`); audit running → phase progress; findings stale vs last audit timestamp.

## 4. API / WS contract

REST:
- `GET /api/quality` → `{health: repo_health_report, findings: summarize, coverage, quick_wins,
  gaps, trends}` (compose; heavy parts cached).
- `GET /api/quality/findings?severity=&rule=&path=&limit=` → `audit.findings`.
- `GET /api/quality/findings/structured?...` → `findings_structured`.
- `POST /api/quality/audit` `{refresh?}` → `{job_id}` (SPEC-02 job; result = `summarize`).
- `POST /api/quality/audit/file` `{path}` / `POST /api/quality/audit/diff` → scoped results.
- `GET /api/quality/trends?metric=score|findings|coverage|gaps` → snapshot series (SPEC-09).
- `POST /api/quality/quickwins` → `quick_wins`.

WS (`/ws`, SPEC-14): `job.progress` (audit phases: routes→stack→rules→upsert), `job.done`
(summary), `quality.update` (fresh summary + snapshot written).

## 5. Data contract

- Reads `findings` (+`symbols`/`edges` for health), `gapfill` outputs; no new tables.
- **Snapshots** (SPEC-04 §5) carry: ts, overall_score, by_severity, coverage_pct, gap counts →
  the trend source for B1–B3/D2. Written once per audit job completion.

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge.quality_bundle(root)`** — composes health + summary + coverage + quick_wins +
  gaps in bounded query batches; cache 30 s (audit is expensive: re-index + rules run).
2. **Audit-as-job adapter** — wrap `audit(root, refresh)` in SPEC-02 job runner with phase
  progress; write snapshot after completion (SPEC-04 addition 1).
3. **`web_bridge.findings_query(...)`** — param pass-through to `audit.findings` + pagination
  (limit is capped 100; add offset for large repos).
4. **Custom-rule file watcher** — if `[audit] custom_rules_path` changes, re-run audit job
  (SPEC-10 write-back covers editing; here just re-trigger).

## 7. Core issues / risks (flagged, grounded)

- **CORE-27 — `analysis` imports `stack.nextjs` directly; non-Next.js repos hit the except
  default quality_score=80 silently.** `analysis.py:49-57` — for Python repos the "quality"
  component is a hardcoded 80 regardless of real findings. → Surface health score with a
  "quality component: fallback (stack not applicable)" note; the score is not comparable across
  stacks. *(New issue.)*
- **CORE-28 — `audit.refresh` re-indexes routes/stack on every run (subprocess-heavy for
  Next/Prisma)** `audit.py:17-21`; full `R.run_rules` is CPU-bound. → Audit is a job with
  progress, not a GET. *(Confirms SPEC-02 job model.)*
- **CORE-29 — `quick_wins` and `findings` are capped (10/100) with no pagination.**
  `audit.py:48` limit=100, `quick_wins` limit=10. → Add offset/pagination in bridge; big repos
  exceed 100. *(New issue.)*
- **CORE-30 — health score "empty repo" returns exactly 50 (neutral)** `analysis.py:40-41` —
  indistinguishable from a genuinely mediocre repo. → UI must show "no symbols indexed — run
  sync" state instead of a 50 score ring. *(Grounds empty-state in §3.)*
- **Watch: `findings` path filter is `LIKE %path%`** `audit.py:53` — broad; fine for deep-link
  but confirm it doesn't over-match (e.g. `store` matches `store.py` and `substore/`). Note in
  UI tooltip.
- **Watch: gapfill `migrations/env/logs/metrics/features/deps/api`** (`gapfill.py:245-494`)
  depend on stack/project shape — some return empty on Python repos; render "not applicable"
  rather than "no gaps".

## 8. Acceptance checks (from §6 / §7.5)

- [ ] Score ring + component breakdown + trend render from real `analysis` + snapshots.
- [ ] Findings table filterable/paginated; per-row deep-link to SPEC-06; structured view works.
- [ ] "Run audit" is a progress job, not a hanging request; summary + snapshot written after.
- [ ] Quick wins, tech debt, gaps, recommendations, coverage all render real data.
- [ ] Empty-repo and non-applicable-stack states shown honestly (no fake 50/80 scores).
- [ ] Trends (B1–B3, D2) render from snapshot history (SPEC-09).
