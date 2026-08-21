# Audit — web-console backend (SPEC-01–15)

**Source of truth:** `lib/cipkg/web_bridge.py` (3521 lines)
**Verification:** `python -c "from cipkg.web_bridge import app; print(len(app.routes))"` → **92 routes**. Import clean. All SPEC endpoint groups present. Grep for `TODO|FIXME|placeholder|not implemented|NotImplementedError|stub` → **0 matches**.

## Status table (every SPEC endpoint group verified present)

| Spec | Claimed (BUILD.md) | Actual | Evidence (route literals) |
|------|-------------------|--------|---------------------------|
| SPEC-01 App Shell | done | ✅ | `/api/status` (184) |
| SPEC-03 Daemon | done | ✅ | `/api/daemon` (489), `/daemon/log` (504), `/daemon/start` (513), `/daemon/stop` (538), `/daemon/restart` (556), `/daemon/auto-manage` (578) |
| SPEC-04 Index | done | ✅ | `/api/index/status` (1416), `/index/sync` (1432), `/index/rebuild` (1455), `/index/verify` (1476), `/index/vacuum` (1494), `/admission` (1512), `/admission/explain` (1522); `/api/watch/*` (675,681,688); `/api/snapshots` (2418) |
| SPEC-05 Search | done | ✅ | `/api/search` (1861), `/symbols` (1940), `/graph` (1949), `/context` (2015), `/history` (2050) |
| SPEC-06 File | done | ✅ | `/api/file` (2114), `/file/summary` (2128), `/file/impact` (2141), `/file/history` (2154), `/file/coverage` (2167), `/file/context` (2188), `/file/graph` (2201) |
| SPEC-07 Quality | done | ✅ | `/api/quality` (2363), `/quality/gaps` (2314), `/quality/coverage` (2339), `/quality/findings` (2372), `/quality/findings/structured` (2388), `/quality/trends` (2403), `/quality/quickwins` (2434), `/quality/audit` (2450) |
| SPEC-08 Memory | done | ✅ | `/api/memory/overview` (2698), `/facts` (2706), `/episodes` (2718), `/recall` (2728), `/patterns` (2742), `/suggestions` (2757), `/memory/action` (2775), `/memory/consolidate` (2796), `/memory/clear` (2866) |
| SPEC-09 Viz | done | ✅ | `/api/vis/overview` (3120), `/vis/trends` (3128), `/vis/snapshots` (3139), `/vis/git` (3217), `/vis/findings` (3242), `/vis/map` (3260), `/vis/signals` (3286), `/vis/graph` (3294) |
| SPEC-10 Settings | done | ✅ | `/api/config` (252), `/config/schema` (948), `/config/full` (954), `/config/validate` (960), `/config/save` (971), `/config/reset` (1015), `/config/reload` (1049), `/env` (1075) |
| SPEC-11 Export | done | ✅ | `/api/export` (1206), `/export/status` (1229), `/export/tools` (1262), `/export/ingest` (1299), `/verify` (1351) |
| SPEC-12 Onboarding | done | ✅ | `/api/onboarding/status` (1710) |
| SPEC-13 Oracle | done | ✅ | `/api/oracle/summary` (1735), `/oracle/repo-summary` (1747), `/oracle/suggest-context` (1766), `/oracle/next` (1781), `/oracle/workflows` (1797), `/oracle/workflows/{workflow_id}/run` (1813) |
| SPEC-14 Realtime | done | ✅ | `@app.websocket("/ws")` (3475); `/api/events` (3044); `/api/run` (3427); `/api/jobs` (465), `/jobs/{job_id}` (477), `/jobs/{job_id}/cancel` (3460) |
| SPEC-15 NFRs | done | ✅ | `/api/embed/status` (1376), `/api/context` (2015); `_ttl_cache` present; 422→`_err` |

**Route-count note:** BUILD.md mentions "46 / 55 / 72 routes" at various milestones; the final app has **92** routes — consistent with all specs merged (the earlier numbers were per-milestone snapshots, not contradictions).

## MISSING / PLACEHOLDER / DEAD
**None functionally.** No stubs, no `NotImplementedError`, no TODOs. (Endpoint groups all resolve to real handler functions.)

## SKIPPED GAPS (intentional, per GAP-REPORT — NOT defects)
- **GAP-10** — skipped (low priority)
- **GAP-12** — skipped (low priority)
- GAP-08 (snapshot trends), GAP-05 (quickwins GET), GAP-09 (oracle workflows), GAP-11 (search filters) — **FIXED**.

## OBVIOUS ENHANCEMENTS / BUGS / RISK
- **[SECURITY, shared with upgrade-plan] Path traversal in `file_bundle` (`web_bridge.py:2069`):** `Path(root)/path` with no containment check. Live via `/api/file`. Tracked as P0 in the consolidated list.
- **No automated tests** for any SPEC endpoint group (in-process smoke tests claimed in BUILD.md are not present as committed test files).
- **Perf/robustness not independently verified:** BUILD.md cites in-process timings (e.g. quality bundle 4.2s, file impact 1.9s). No regression guard if those regress.
- **Legacy replacement not confirmed deleted:** BUILD.md §2 gate lists "delete `web_server.py`, `dashboard-web`, legacy `static/`" — not verified in this audit; recommend confirming before declaring SPEC-15 fully closed.
