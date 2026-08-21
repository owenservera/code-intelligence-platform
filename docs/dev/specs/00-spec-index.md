# Specs — Per-Requirement, Truth-Grounded Build Specs

**Status:** ACTIVE — one spec per requirement, written sequentially before build.
**Base:** `05-requirements.md` (§0–§7, incl. round-2 addendum).
**Grounding rule:** Each spec is grounded in the **CIP core** (`lib/cipkg/*`), never in the
legacy web layer (`web_server.py`/`dashboard.py`/`static/`) — this is a **fresh web build**.
Every claim about the core is verified against source (`file:line`) or the live `.cip` DB.
**Flagging rule:** Each spec carries a **Core issues** section — problems in the current CIP
core that would affect this requirement. New finds also land in `09-bugs-and-issues.md`.

## Spec list (in build order)

| # | Spec | Requirement(s) | Status |
|---|------|----------------|--------|
| 00 | this index | — | active |
| 01 | `01-app-shell.md` | FR-1 App shell | active |
| 02 | `02-command-center.md` | FR-2 Command center | active |
| 03 | `03-daemon-server-mgmt.md` | FR-3 Daemon & server mgmt | active |
| 04 | `04-index-management.md` | FR-4 Index mgmt | active |
| 05 | `05-search-navigation.md` | FR-5 Search & navigation | active |
| 06 | `06-deep-file-panel.md` | FR-6 Deep file panel | active |
| 07 | `07-quality-audit.md` | FR-7 Quality & audit | active |
| 08 | `08-memory-lab.md` | FR-8 Memory lab | active |
| 09 | `09-visualization-suite.md` | FR-9 Visualization suite (A–G) | active |
| 10 | `10-settings-config.md` | FR-10 + FR-15 Config | active |
| 11 | `11-export-integration.md` | FR-11 Export & integration | active |
| 12 | `12-onboarding-wizard.md` | FR-12 Repo activation wizard | active |
| 13 | `13-oracle-surface.md` | FR-13 Oracle / intelligence | active |
| 14 | `14-realtime-contract.md` | FR-14 + NFR Real-time | active |
| 15 | `15-cross-cutting.md` | NFRs, backend additions, bridge rules | active |
| 16 | `16-repo-explorer.md` | FR-16 Repo file explorer (VS Code-style tree) | active |
| 17 | `17-file-review-renderer.md` | FR-17 File review renderer (diff + inline review) | active |
| 18 | `18-realtime-edit-history.md` | FR-18 Realtime edit history (timeline + blame + live) | active |
| 19 | `19-project-registry.md` | FR-19 Multi-project registry (foundation; project-scopes 16/17/18) | active |

## Spec template (every spec follows this shape)

```markdown
# SPEC-NN — <Requirement title>

- Requirement source: <05-requirements.md §X / FR-Y / §7.Z>
- Grounding verified: <date> against lib/cipkg/<file>:<line>
- Build order dependency: <which specs must land first>

## 1. Goal & owner intent
## 2. Truth-grounded core surface (verified)
   - every lib function/db table/endpoint the feature will call, with file:line
## 3. UI/UX contract
   - view layout, interactions, states (from requirements + owner intent)
## 4. API / WS contract
   - REST endpoints, WS events, payload shapes, job model
## 5. Data contract
   - tables/fields/aggregations consumed; new backend data required
## 6. Backend additions (lib/cipkg changes in scope)
## 7. Core issues / risks (flagged, grounded)
## 8. Acceptance checks (from requirements §6 / §7.5)
```
