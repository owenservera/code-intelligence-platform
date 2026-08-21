# Audit — web-console frontend (SPEC-01–15)

**Source of truth:** `web/src/**` (views, components, lib/api.ts, stores, App.tsx, hooks)
**Verification:** `npx tsc --noEmit` → **silent (exit 0)**. Grep for `TODO|FIXME|placeholder|not implemented|coming soon|Lorem` across all `.ts/.tsx` → **0 matches**. Every SPEC view file is a real, data-bound implementation (no stubs).

## Status table

| Spec | Claimed (BUILD.md) | Actual | Evidence | Notes |
|------|-------------------|--------|----------|-------|
| SPEC-01 App Shell | done | ✅ real | `App.tsx:47-64`, `AppShell.tsx:80-93`, `LeftNav.tsx:16-28`, `TopBar.tsx:4-32`, `StatusBar.tsx:4-33` | Shell + 4-cluster status wired to WS |
| SPEC-02 Command Center | done | ✅ real | `CommandCenter.tsx:14-97`, `CommandPalette.tsx:19-215`, `CommandForm.tsx:24-109` | Hybrid palette, keyboard nav, param form |
| SPEC-03 Daemon | done | ✅ real | `DaemonView.tsx:7-163` | 7 endpoints; start/stop/restart/log |
| SPEC-04 Index | done | ✅ real | `IndexView.tsx:8-387` | sync/vacuum/verify, watch, snapshots, admission |
| SPEC-05 Search | done | ✅ real | `SearchView.tsx:9-291` | code/symbols tabs, k slider, filters, symbol detail |
| SPEC-06 File | done | ✅ real | `FileView.tsx:19-313`, `FileEditor.tsx:43-62` | Monaco lazy + 8 rail sections |
| SPEC-07 Quality | done | ✅ real | `QualityView.tsx:14-296` | score ring, severity chips, findings, quick wins, Run Audit |
| SPEC-08 Memory | done | ✅ real | `MemoryView.tsx:24-476` | 5 tabs, consolidate, two-click clear |
| SPEC-09 Viz | done | ✅ real | `VisualizeView.tsx:39-739`, `CodeGraph3D.tsx:41-393` | A–G panels + lazy 3D graph (three.js) |
| SPEC-10 Settings | done | ✅ real | `SettingsView.tsx:121-506` | 8 categories, validate/save/reload, toml, env |
| SPEC-11 Export | done | ✅ real | `ExportView.tsx:19-384` | downloads, tools schema, ingest, verify gate |
| SPEC-12 Onboarding | done | ✅ real | `OnboardingView.tsx:23-350` | first-run gate on `/`, 4-step stepper |
| SPEC-13 Oracle | done | ✅ real | `OracleView.tsx:372-397` | repo story, file summary, suggest-context, predict |
| SPEC-14 Realtime/WS | done | ✅ real | `useWebSocket.ts:16-81`, `useStatusPoll.ts:6-29`, `stores/jobs.ts:28-93`, `stores/events.ts:87-95` | reconnect + replay + event→invalidate map |
| SPEC-15 NFRs (frontend) | done | ✅ | `api.ts` envelope unwrap `3-16`; StatusBar/TopBar | error-shape handling, no dead endpoints |

## API coverage (`lib/api.ts`) — every SPEC present
`daemonApi` `embedApi` `indexApi` `watchApi` `snapshotsApi` `searchApi` `fileApi` `auditApi` `memoryApi` `vizApi` `settingsApi` `exportApi` `onboardingApi` `oracleApi` `jobApi` `eventsApi`.

## Route discrepancy (BUILD.md vs App.tsx)
**None.** `App.tsx:50-61` routes (`/`, `/daemon`, `/index`, `/search`, `/files`, `/quality`, `/memory`, `/visualize`, `/settings`, `/export`, `/oracle`) match BUILD.md. SPEC-12 renders `OnboardingView` as a gate over `/` (App.tsx:43-45), consistent with BUILD.md.

## MISSING / STUB / PLACEHOLDER
**None.** Every claimed file has >30 lines of real JSX/logic.

## OBVIOUS ENHANCEMENTS / BUGS
1. **[BUG] SearchView.tsx:281** — `qc.invalidateQueries()` called with **no argument**. In React Query v5 this throws `"No query key or filters provided"`, so clicking a `next_ops` prediction button (lines 280-286) would crash. tsc doesn't catch it. Should be removed or given a key.
2. **[UX] OnboardingView.tsx:61** — sync failure uses native `alert(...)`; inconsistent with polished wizard styling elsewhere.
3. **[TESTS] No `*.test.ts(x)`** under `web/src/` — milestone gate lists `tsc`/`bun run build` but no frontend test requirement exists; none present.
4. **[MINOR] CommandCenter / Visualize trend panels** depend on `events` rows; before any sync/audit they show honest empty-states (by design).
