# CIP Development Review, Assessment & Action Workbook

**Date:** 2026-08-17  
**Scope:** [docs/dev/](file:///c:/0-BlackBoxProject-0/index/docs/dev/) · Core Engine ([lib/cipkg/](file:///c:/0-BlackBoxProject-0/index/lib/cipkg/)) · Web Console ([web/](file:///c:/0-BlackBoxProject-0/index/web/)) · Bug-Fix Campaign ([docs/dev/cip-bugfix-campaign/](file:///c:/0-BlackBoxProject-0/index/docs/dev/cip-bugfix-campaign/))  
**Authors / Context:** Antigravity AI & Engineering Pair

---

## 1. Executive Summary & State of the Union

Over recent intensive development cycles, the **Code Intelligence Platform (CIP)** has undergone major architectural evolutions:

1. **CIP Bug-Fix & Detection Campaign (Complete):**
   - **53/53 TRACKER-ranked findings** across all phases (Phase S, Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5) resolved, proven via detect-first methodology, and regression-locked with **61/61 detector tests passing**.
   - Systematic fixes across index integrity (import resolution, backup pollution elimination, `tested_by` noise cleanup), config consistency (`config.default.toml` syntax, port alignment, schema versioning), static name resolution, and audit honesty.
2. **CIP Web Console v1 Build (13/14 Units Implemented):**
   - Modern, high-performance stack built with **React 19 + TypeScript + Tailwind CSS 4 + Vite** on Bun, backed by a high-throughput **FastAPI backend (`lib/cipkg/web_bridge.py`)** with **72 registered REST endpoints** and live WebSocket telemetry.
   - Fully interactive views implemented: App Shell, Command Center, Daemon & Server Management, Index Management, Search & Navigation, Deep File Panel, Quality & Audit, Memory Lab, Visualization Suite (with code-split Three.js 3D Code Graph & Recharts), Settings & Config writeback, Export & Signal Ingest, Onboarding Wizard, and Oracle AI Surface.

### High-Level Status Dashboard

| Subsystem | State | Health / Coverage | Primary Artifacts |
| :--- | :--- | :--- | :--- |
| **Core Indexer & Store** | 🟢 Healthy | 100% import resolution (487/487), 0% backup pollution | [`lib/cipkg/indexer.py`](file:///c:/0-BlackBoxProject-0/index/lib/cipkg/indexer.py), [`lib/cipkg/store.py`](file:///c:/0-BlackBoxProject-0/index/lib/cipkg/store.py) |
| **Detection Engine** | 🟢 Locked | 61/61 detector tests passing | [`lib/cipkg/stack/rules.py`](file:///c:/0-BlackBoxProject-0/index/lib/cipkg/stack/rules.py), [`tests/detectors/`](file:///c:/0-BlackBoxProject-0/index/tests/detectors/) |
| **Web Console UI** | 🟢 95% Complete | 13/14 spec units done; builds cleanly; 0 placeholder views | [`web/src/`](file:///c:/0-BlackBoxProject-0/index/web/src/), [`docs/dev/web-console/`](file:///c:/0-BlackBoxProject-0/index/docs/dev/web-console/) |
| **Web Bridge API** | 🟢 95% Complete | 72 `/api` routes active; in-process verified | [`lib/cipkg/web_bridge.py`](file:///c:/0-BlackBoxProject-0/index/lib/cipkg/web_bridge.py) |
| **SPEC-15 Cross-Cutting** | 🟡 Pending | Error envelope audit, GET read-only audit, cache review | [`docs/dev/specs/15-cross-cutting.md`](file:///c:/0-BlackBoxProject-0/index/docs/dev/specs/15-cross-cutting.md) |
| **Unranked Core / Spec Bugs** | 🟡 Triage Needed | ~20 unranked issues in `09-bugs-and-issues.md` | [`docs/dev/09-bugs-and-issues.md`](file:///c:/0-BlackBoxProject-0/index/docs/dev/09-bugs-and-issues.md) |
| **Documentation & Guides** | 🟡 Gaps Exist | Missing `07-api-design.md`, `08-migration-plan.md` | [`docs/dev/00-goals-and-decisions.md`](file:///c:/0-BlackBoxProject-0/index/docs/dev/00-goals-and-decisions.md) |

---

## 2. Deep-Dive Gap & Opportunity Assessment

### Area A: Web Console Milestone Closeout (SPEC-15 NFRs)
- **Error Envelope Normalization (NFR-1):** Verify that all 72 endpoints return the uniform `{ok: false, error: {code, message, core?}}` envelope on errors rather than raw uncaught 500 exceptions.
- **Strict Read-Only DB on GET (NFR-2):** Ensure GET endpoints never trigger implicit schema upgrades or write side-effects if SQLite databases do not exist (mirroring the `_oracle_ready()` and `InitDetector` patterns).
- **Caching & Event Invalidation (NFR-3):** Ensure the visualization and expensive computation caches (`_VIS_CACHE`) stay consistent with event timestamps (`max(events.ts)`).
- **Frontend Bundle & Dead Code Sweep:** Validate zero console runtime errors, verify code-split chunks for Monaco Editor and Three.js 3D graph, and verify build artifacts under `web/dist`.

### Area B: Residual Issues in `09-bugs-and-issues.md`
While all 53 high-leverage TRACKER findings were resolved, `09-bugs-and-issues.md` contains unranked items that provide optimization opportunities:
1. **`CORE-1` (Soft Repo Root):** `base.repo_root()` raises `SystemExit` on invalid repo root; web bridge needs graceful handling when invoked outside an initialized repo root.
2. **`CORE-3` (Status Payload COUNTs):** Optimize database row counting queries (`COUNT(*)` on large symbol/chunk tables) by leveraging SQLite table stats or cached metadata.
3. **`CORE-4` (`base.load_config` sys.path mutation):** Avoid implicit `sys.path` pollution during configuration loading.
4. **`CORE-8` & `CORE-9` (Command Parameter Metadata & Command↔Lib Mapping):** Ensure full bi-directional reflection of CLI command parameters and types for dynamic command palette generation.
5. **`CORE-11` & `CORE-14` (Queue-depth Telemetry & Structured Logging):** Add structured JSON logging and job queue telemetry to daemon services.
6. **`CORE-17` (Vacuum Events Conflict):** Prevent write contention during SQLite maintenance vacuum operations while concurrent events are logged.
7. **`BUG-007` to `BUG-012`, `BUG-014`, `BUG-016` to `BUG-022`:** Triage lower-priority items (e.g. SQLite-vec DLL loading fallbacks on Windows, FTS5 lexical search query sanitization, external search swallow logging).

### Area C: Legacy Code Retirement & Clean Packaging
- **Retire Legacy Web Layer:** The legacy stdlib `http.server` backend ([`lib/cipkg/web_server.py`](file:///c:/0-BlackBoxProject-0/index/lib/cipkg/web_server.py), [`lib/cipkg/dashboard.py`](file:///c:/0-BlackBoxProject-0/index/lib/cipkg/dashboard.py), and `lib/cipkg/static/`) is superseded by `lib/cipkg/web_bridge.py` and `web/`. It should be cleanly deprecated or removed.
- **Wire `cip web` CLI Command:** Ensure `cip web` invokes `web_bridge` via `uvicorn` and automatically serves the compiled `web/dist` static assets.

### Area D: System Documentation & Architectural Specs
- **Generate `07-api-design.md`:** Document the complete catalog of 72 REST endpoints, WebSocket schema, and payload contracts.
- **Generate `08-migration-plan.md`:** Provide a comprehensive operational guide detailing the transition from CIP 1.x (CLI/Textual/legacy web) to CIP 2.x (FastAPI/React/Web Console).

---

## 3. Prioritized Action Workbook

```mermaid
flowchart TD
    subgraph Track 1: Web Console Finalization
        T1A[SPEC-15 Cross-Cutting NFR Audit] --> T1B[Frontend E2E / Build Verification]
        T1B --> T1C[Package cip web CLI Launch]
    end

    subgraph Track 2: Core Hardening
        T2A[Triage 09 Unranked Findings] --> T2B[CORE-1/3/4/8/11/17 Hardening]
        T2B --> T2C[SQLite & Memory DB WAL/Lock Tuning]
    end

    subgraph Track 3: Legacy Cleanup & Docs
        T3A[Deprecate web_server.py & static/] --> T3B[Author 07-api-design.md]
        T3B --> T3C[Author 08-migration-plan.md]
    end

    Track 1 --> ProductionRelease[CIP 2.1 Release Candidate]
    Track 2 --> ProductionRelease
    Track 3 --> ProductionRelease
```

---

### Work Package 1: Complete SPEC-15 & Web Console Milestone Gate (P0 — Immediate)

#### Objectives
Complete the final remaining row in [`docs/dev/web-console/BUILD.md`](file:///c:/0-BlackBoxProject-0/index/docs/dev/web-console/BUILD.md) (SPEC-15 Cross-Cutting NFRs) and lock the Web Console v1 build.

#### Tasks & Action Items
- [ ] **Audit 72 REST Endpoints for Stable Error Envelope:**
  - Verify every endpoint in `web_bridge.py` wraps exceptions via `_err(code, message)` and returns 200 with `{ok: false, error: ...}` or properly handled HTTP error status.
- [ ] **Audit Read-Only DB Guard on all GET Requests:**
  - Confirm that no GET endpoint creates SQLite databases or `.cip/` metadata side effects if the repository is uninitialized.
- [ ] **Audit Cache Invalidation Keys:**
  - Verify `_VIS_CACHE` and memory/search caching keys properly track event stream timestamps.
- [ ] **Frontend Production Build Check:**
  - Run `cd web; npx tsc --noEmit` and `cd web; bun run build` to confirm zero TS errors and verify asset generation in `web/dist`.
- [ ] **Update Documentation & Checkpoints:**
  - Update `docs/dev/web-console/BUILD.md` marking SPEC-15 as `done`.
  - Update `docs/dev/web-console/CHECKPOINT.md` with final milestone completion notes.

---

### Work Package 2: Residual Core Bug Triage & Engine Hardening (P1 — Near Term)

#### Objectives
Address residual architectural gaps from `09-bugs-and-issues.md` that improve performance, developer experience, and system resilience.

#### Tasks & Action Items
- [ ] **`CORE-1` / `CORE-4` Configuration & Path Isolation:**
  - Refactor `base.repo_root()` to provide a safe `find_repo_root_or_none()` helper that does not execute `sys.exit(1)`.
  - Remove mutating `sys.path` side-effects inside `base.load_config`.
- [ ] **`CORE-3` Status Query Optimization:**
  - Optimize high-frequency count queries in `server.index_status()` and `store.py` to prevent table scans on large codebases.
- [ ] **`CORE-8` & `CORE-9` Command Center Reflection:**
  - Standardize `CommandParameter` metadata across all CLI subcommands in `cli.py` to ensure rich UI forms in the Web Console Command Center.
- [ ] **`CORE-11` & `CORE-14` Daemon Telemetry:**
  - Introduce queue-depth metrics and structured event logging in `daemon.py`.
- [ ] **SQLite Concurrency & WAL Tuning (`CORE-17`):**
  - Enable Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) and busy timeout handlers across `store.py` and `memory/` databases to eliminate locking during background maintenance.

---

### Work Package 3: Legacy Surface Deprecation & CLI Packaging (P1 — Near Term)

#### Objectives
Cleanly retire obsolete legacy web components and provide a unified single-command launch experience.

#### Tasks & Action Items
- [ ] **Wire `cip web` CLI Subcommand:**
  - Update `lib/cipkg/cli.py` handler `handle_web_command` to invoke `uvicorn.run("cipkg.web_bridge:app", host=host, port=port)`.
  - Mount `StaticFiles(directory=dist_path, html=True)` in `web_bridge.py` when `web/dist` exists.
- [ ] **Deprecate Legacy Web Files:**
  - Mark `lib/cipkg/web_server.py`, `lib/cipkg/dashboard.py`, and `lib/cipkg/static/` as deprecated or archive them.
- [ ] **Verify End-to-End Local Startup:**
  - Test `cip web --port 8090` from PowerShell; verify browser loads full console and establishes WebSocket connection at `ws://localhost:8090/ws`.

---

### Work Package 4: Complete Dev Documentation Suite (P2 — Planned)

#### Objectives
Complete the missing architectural reference documents identified in `docs/dev/00-goals-and-decisions.md`.

#### Tasks & Action Items
- [ ] **Author `docs/dev/07-api-design.md`:**
  - Document all 72 REST endpoints categorized by domain (System, Daemon, Index, Search, File, Audit, Memory, Visualization, Settings, Export, Onboarding, Oracle).
  - Document WebSocket message schemas for real-time progress, job streaming, and status broadcast.
- [ ] **Author `docs/dev/08-migration-plan.md`:**
  - Provide a migration roadmap from legacy CLI/Textual TUI workflows to the unified Web Console and MCP-first architecture.

---

## 4. Verification & Validation Commands

All verification commands are tailored for Windows PowerShell (pwsh) and Bun per workspace rules:

```powershell
# 1. Typecheck and build the Web Console frontend
cd c:\0-BlackBoxProject-0\index\web
bun run build
npx tsc --noEmit

# 2. Run all detector regression tests (61/61 tests)
cd c:\0-BlackBoxProject-0\index
python -m pytest tests/detectors/ -v

# 3. Run CIP self-test and static health doctor
cd c:\0-BlackBoxProject-0\index
python -m cipkg.cli selftest
python -m cipkg.cli doctor --static
python -m cipkg.cli doctor --config

# 4. Verify Web Bridge backend routes and FastAPI startup (in-process)
python -c "from cipkg.web_bridge import app; print(f'Active API routes: {len([r for r in app.routes if getattr(r, \"path\", \"\").startswith(\"/api\")])}')"
```

---

### Work Package 5: Code Forensics, Deep Intelligence & High-Leverage UX (P1 — Active)

Reference: [`docs/dev/FORENSIC_INTELLIGENCE_AND_UX_BLUEPRINT.md`](file:///c:/0-BlackBoxProject-0/index/docs/dev/FORENSIC_INTELLIGENCE_AND_UX_BLUEPRINT.md)

#### Objectives
Transform CIP reporting from generic scorecards into an investigative code forensics studio uncovering hidden features, silent traps, boundary violations, and risk matrices.

#### Tasks & Action Items
- [x] **WP5.1: Interactive Forensic Studio in QualityView:**
  - Replaced flat findings list with 5 categorized tabs: Buried Features (`HIDDEN-*`), Silent Traps (`S1`, `DB-NO-AWAIT`), Architecture (`ARCH-*`, `QA-CIRCULAR`), Risk Matrix (`QA-UNTESTED-HOT`, Churn), and Secrets/Env (`ENV-*`, `SEC-*`).
- [x] **WP5.2: Universal Deep-Link Navigation Fabric:**
  - Wired findings, search results, and symbols to jump directly to line numbers in Monaco Editor with explanatory token highlights.
- [x] **WP5.3: AI Context Pack & Prompt Studio:**
  - Provided an export action bundling token-budgeted signature repo maps, symbols, and dependencies under the 120K context ceiling for Claude/Gemini.
- [x] **WP5.4: Live Pulse Status Bar:**
  - Added persistent footer bar showing WebSocket status, active profile pill, and live background watcher/job activity.

---

## 5. Execution Tracking Matrix

| ID | Task | Owner | Priority | Status | Verification Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **WP1.1** | SPEC-15 Cross-Cutting NFR Review | Pair | P0 | 🟢 Complete | Error envelope & read-only GET audits clean |
| **WP1.2** | Web Frontend Production Build | Pair | P0 | 🟢 Complete | `bun run build` succeeds without errors |
| **WP1.3** | Close Web Console Milestone | Pair | P0 | 🟢 Complete | `BUILD.md` & `CHECKPOINT.md` updated |
| **WP2.1** | `CORE-1`/`CORE-4` Base Hardening | Engine | P1 | 📋 Queued | Safe repo discovery; no sys.path side effects |
| **WP2.2** | `CORE-3` Count Query Optimization | Engine | P1 | 📋 Queued | Fast index_status response on large repos |
| **WP2.3** | SQLite WAL & Lock Tuning | Store | P1 | 📋 Queued | Zero db lock errors during concurrent indexing |
| **WP3.1** | Wire `cip web` to `web_bridge` + SPA | CLI | P1 | 📋 Queued | `cip web` serves React SPA & API on port 8090 |
| **WP3.2** | Archive Legacy `web_server.py` | Core | P1 | 📋 Queued | Legacy server cleanly deprecated |
| **WP4.1** | Author `07-api-design.md` | Docs | P2 | 📋 Queued | Full REST & WS contract documented |
| **WP4.2** | Author `08-migration-plan.md` | Docs | P2 | 📋 Queued | 1.x to 2.x migration path documented |
| **WP5.1** | Interactive Forensic Studio UI | Frontend | P1 | 🟢 Complete | 5 forensic tabs operational in QualityView |
| **WP5.2** | Universal Deep-Link Navigation | Frontend | P1 | 🟢 Complete | Finding clicks jump to Monaco line |
| **WP5.3** | AI Context Pack Studio | Engine/UI | P1 | 🟢 Complete | Token-budgeted context pack generation |
| **WP5.4** | Live Pulse Status Bar | Frontend | P1 | 🟢 Complete | Persistent footer with WS & watcher pulse |

