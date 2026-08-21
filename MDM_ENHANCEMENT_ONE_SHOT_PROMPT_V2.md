# 🚀 CIP MASTER DATA TAXONOMY (L0–LA) SURGICAL ENHANCEMENT PACK PROMPT (DRAFT 2)

> **EXECUTIVE AGENT DIRECTIVE:**
> You are acting as an elite principal compiler engineer, static analysis architect, and systems programmer specializing in the **Code Intelligence Platform (CIP)** engine (`lib/cipkg/`).
> Your mission is to execute a **complete, truth-grounded, surgical upgrade** to CIP that brings full end-to-end extraction, storage, graph analysis, and multi-layer explainable synthesis across all **11 Master Data Model (MDM) Layers (L0 through LA)** as defined in `docs/MDM/Repo Intelligence System — Master Data.MD`.

---

## 1. WORKSPACE INITIALIZATION & STRICT ZERO-TOKEN-WASTE DIRECTIVE

### A. Repository Ingestion
```powershell
# Clone the repository into your workspace
git clone <REPO_URL> cip-master
cd cip-master
```

### B. Whitelisted Target Subsystems (DO NOT WASTE TOKENS ON VENDOR/CACHE SCANS)
To adhere strictly to the **120K token context budget** and prevent compaction erasure:
1. **DO NOT** perform unbounded recursive directory scans.
2. **DO NOT** inspect `.git`, `__pycache__`, `node_modules`, `.cip/data`, or benchmark cache folders.
3. **ONLY** inspect, extend, and integrate with the following whitelisted files:

```
TARGET SURFACE AREA (STRICT ACCESS WHITELIST):
├── docs/MDM/Repo Intelligence System — Master Data.MD  # Canonical MDM Taxonomy Spec
├── lib/cipkg/
│   ├── store.py           # SQLite CORE_SCHEMA, connect(), bulk(), snapshots, pragmas
│   ├── base.py            # repo_root(), load_config(), sha(), log_swallowed()
│   ├── indexer.py         # prepare_file(), _bulk_write(), resolve_symbol_edges(), link_imports()
│   ├── parse.py           # RULES, parse_file(), extract_imports(), symbol extraction
│   ├── parsers.py         # build_heritage() (extends/implements edges)
│   ├── tree_parser.py     # Tree-sitter AST engine & grammar bindings
│   ├── analysis.py        # repo_health_report(), _calculate_health_score(), _open_findings()
│   ├── stack/rules.py     # Rule engine: F(), run_rules(), 25+ built-in audit rules
│   ├── gapfill.py         # _tarjan_scc(), coverage(), dead(), blame(), api()
│   ├── gitindex.py        # git_index(), hotspots() (time-decayed churn, co_change)
│   ├── doctor.py          # scan_path() AST swallow scanner, pyflakes lint runner
│   ├── context_manager.py # UnifiedContext, RepositoryContext, token budgeting
│   ├── server.py          # MCP JSON-RPC tool declarations & call_tool()
│   ├── cli.py             # CLI arg parsing, subcommands & handle_*_command handlers
│   └── command_registry.py# CommandRegistry, CommandCard, CommandCategory, CommandPriority
└── tests/
    └── test_mdm_layers.py # End-to-end verification test suite
```

---

## 2. TRUTH-GROUNDED ARCHITECTURAL BASELINE & EXTENSION BLUEPRINT

### Existing Codebase Reality (Ground-Truth Invariants)
- **Database Engine**: `lib/cipkg/store.py` manages `index.db` with SQLite WAL mode, memory temp store, 64MB cache, and `foreign_keys=OFF`.
- **Existing Entity Tables**: `meta`, `files`, `symbols`, `chunks`, `file_imports`, `edges`, `vectors`, `events`, `summaries`, `commits`, `commit_files`, `signals`, `symbol_calls`, `snapshots`.
- **Existing Edge Graph Kinds**: `contains`, `exports`, `imports`, `calls`, `references`, `tested_by`, `extends`, `implements`, `modified_by`, `co_change`.
- **Existing Finding Shape**: `F(rule, severity, path, title, detail="", suggestion="", effort="small", line=0, symbol_id=None)` written to the `findings` table.
- **Error Handling Invariant**: Never use bare `except: pass`. Always log swallowed exceptions via `from .base import log_swallowed; log_swallowed("scope_name", err)`.

---

## 3. L0–LA MASTER DATA LAYER SPECIFICATION & IMPLEMENTATION GOALS

You must implement complete detection, graph extraction, and synthesis across the entire taxonomy:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               MASTER DATA TAXONOMY (L0–LA)                             │
├────┬───────────────────────────┬───────────────────────────────────────────────────────┤
│ L0 │ Topology & Ingestion      │ Files, Manifests, Workspaces, Build Maps, Orphan Files│
├────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ L1 │ Syntax & Parse            │ AST nodes, Function/Method/Type/Doc defs, Failures    │
├────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ L2 │ Symbol & Dep Graph        │ FQN symbols, Call/Import/Heritage edges, Tarjan SCC   │
├────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ L3 │ Type & Semantic Layer     │ Inferred types, `any` leaks, Nullable paths, Enums    │
├────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ L4 │ Control & Data Flow       │ CFG branches, Tauri IPC/Event wiring gaps, Swallows   │
├────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ L5 │ Architectural Boundaries  │ Layer violations (lib->ui), Adapter drift, Leakages   │
├────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ L6 │ Code Quality & Smells     │ Complexity traps, Duplications, Untested hot symbols  │
├────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ L7 │ Cross-Cutting Concerns    │ Hardcoded secrets, Raw SQL, Env drift, Tauri ungated  │
├────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ L8 │ Runtime & Operational     │ Snapshots, Panics/Crashes, Feature flag verification  │
├────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ L9 │ Historical & Evolutionary │ Git commit churn, Churn × Complexity hotspots, Drift  │
├────┼───────────────────────────┼───────────────────────────────────────────────────────┤
│ LA │ Governance & Synthesis    │ Finding Records + EXPLAINABILITY TRACES, Debt Index   │
└────┴───────────────────────────┴───────────────────────────────────────────────────────┘
```

### Detailed Layer Responsibilities:
1. **L0 (Topology)**: Parse top-level repository metadata, workspace manifests (`package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`), classify file tiers (`code`, `doc`, `config`), build map associations, and flag orphan files unreachable from any entrypoint or import edge.
2. **L1 (Syntax)**: AST-level syntax parsing via `parse.py` and `tree_parser.py`, recording function signatures, arity, line spans, doc-comment presence, and recording parse errors into an explicit `parse_failures` registry.
3. **L2 (Symbol Graph)**: Resolve fully qualified symbol names (`{language}://{path}#{qualname}`), call edges, import edges, inheritance (`extends`/`implements` via `build_heritage`), compute Fan-In / Fan-Out degree metrics, run Tarjan's SCC (`gapfill._tarjan_scc`) to detect circular loops, and identify God-object candidates.
4. **L3 (Type & Semantic)**: Detect type-suppression signals (`@ts-ignore`, `QA-ANY`), stringly-typed boundaries (magic strings in conditionals vs enums), and error-handling hierarchies.
5. **L4 (Control & Data Flow)**: 
   - Extract control flow traps (dead branches, unawaited database promises via `DB-NO-AWAIT`).
   - Detect **Wiring Gaps**: Cross-correlate Tauri IPC frontend invokes (`invoke('cmd_name')`) vs backend handlers (`#[tauri::command]`), and event emitters (`emit('event')`) vs listeners (`listen('event')`), flagging casing/naming mismatches as **CRITICAL silent wiring gaps**.
   - AST swallow scanner integration (`doctor.py`) for silent `try/except` blocks.
6. **L5 (Architectural Boundaries)**: Detect unidirectional layering violations (`lib/` importing `app/` / `components/` via `ARCH-LAYER-VIOLATION`), adapter interface inconsistencies, and implementation leakages.
7. **L6 (Quality & Smells)**: AST cognitive and cyclomatic complexity scoring, symbol clone detection (`QA-DUP`), untested load-bearing symbols (`QA-UNTESTED-HOT`), and debt comment mining (`TODO`, `FIXME`, `HACK`).
8. **L7 (Cross-Cutting Concerns)**: Entropy secret scanner (`SEC-HARDCODED-SECRET`), SQL injection scanner (`SEC-SQL-RAW`), environment variable drift (`ENV-UNDEFINED`, `ENV-UNREAD`), Next.js client bundle leaks (`NEXT-CLIENT-LEAK`), and Tauri ungated capabilities (`TAURI-UNGATED-COMMAND`).
9. **L8 (Runtime & Operational)**: Ingest snapshot history from `snapshots` table in `store.py`. If runtime telemetry is absent, explicitly annotate findings with `telemetry_status: "static_only"`.
10. **L9 (Historical & Evolutionary)**: Leverage `gitindex.py` for time-decayed churn scores (30d = 1.0, 90d = 0.5, >90d = 0.15), calculate **Churn × Complexity Hotspots** (multiplying L9 churn by L6 complexity/fan-in), and compute co-change coupling.
11. **LA (Governance & Synthesis)**: 
    - Construct canonical **`Finding Record`** entries.
    - **CRITICAL**: Every finding **MUST** contain an **`Explainability Trace`** detailing the exact sequence of facts across L0–L9 that produced the conclusion (e.g., `L0: File` -> `L1: AST Span` -> `L2: Fan-In=14` -> `L6: Untested` -> `L9: Churn=Top-5%` -> `LA: Severity=Critical`).
    - Aggregate the **Technical Debt Index**, **Wiring Gap Report**, **Architecture Health Report**, and **Repo Health Scorecard**.

---

## 4. REQUIRED DELIVERABLES & OUTPUT FORMAT

Your final output must be delivered as a complete, drop-in, zero-placeholder **Surgical Enhancement Pack** comprising the following 4 files:

### DELIVERABLE 1: `MDM_IMPLEMENTATION_GUIDE.md`
A master architectural guide detailing:
- The SQLite table extensions in `store.py` (`mdm_entities`, `mdm_edges`, `mdm_findings`, `mdm_traces`).
- The phased analysis pipeline execution order.
- New CLI commands and MCP tools.
- Verification and self-testing procedures on Windows PowerShell.

### DELIVERABLE 2: NET-NEW CODE MODULES (100% COMPLETE, ZERO PLACEHOLDERS)
1. **`lib/cipkg/mdm_schema.py`**:
   - DDL definitions for L0–LA entities, relations, findings, and explainability traces.
   - Non-destructive database migration routines upgrading `index.db` from `SCHEMA_VERSION=4` to `SCHEMA_VERSION=5`.
2. **`lib/cipkg/mdm_engine.py`**:
   - Full orchestration engine executing the multi-layer extraction and analysis pipeline.
   - Deep wiring gap detector (AST + Regex scanner for IPC commands and Pub/Sub event bindings).
   - Composite Churn × Complexity hotspot scorer combining `gitindex.py` and AST metrics.
   - Dependency cycle & boundary integrity evaluator.
3. **`lib/cipkg/mdm_synthesis.py`**:
   - LA Synthesis generator that builds canonical `Finding Record` objects with multi-layered `Explainability Trace` graphs.
   - Aggregate Technical Debt Index calculator, Wiring Gap reporter, and Markdown/JSON export formatters.
4. **`tests/test_mdm_layers.py`**:
   - Pytest suite verifying L0 topology ingestion, L4 wiring gap detection, L9 churn ranking, and LA explainability trace generation.

### DELIVERABLE 3: SURGICAL DIFF MARKDOWN (`SURGICAL_DIFFS.md`)
Clean, standard unified diffs for existing files:
- **`lib/cipkg/store.py`**: Integration of MDM table DDL and version bump.
- **`lib/cipkg/indexer.py`**: Ingestion hooks for L0/L1/L2 entity persistence.
- **`lib/cipkg/analysis.py`**: Upgrading `repo_health_report()` to incorporate LA MDM synthesis.
- **`lib/cipkg/cli.py`**: Addition of `mdm-scan`, `mdm-report`, `mdm-trace`, and `mdm-gaps` commands.
- **`lib/cipkg/command_registry.py`**: Registration of `CommandCard` entries for MDM commands.
- **`lib/cipkg/server.py`**: Addition of `mdm_scan`, `mdm_report`, `mdm_trace`, and `mdm_gaps` MCP tools.

---

## 5. STRICT CODING & QUALITY CONSTRAINTS
- **Zero Placeholders**: No `# TODO`, `# Implement here`, or omitted method bodies. Provide 100% working Python code.
- **PowerShell / Windows Native**: Use `os.path` and `pathlib.Path` with normalized path separators (`replace("\\", "/")`). Quote paths containing spaces.
- **Deterministic & Traceable**: Every LA synthesis output must explicitly state the underlying lower-layer evidence nodes.
- **Non-Destructive Migrations**: Existing database content (`symbols`, `chunks`, `edges`, `snapshots`) must be preserved during schema updates.

---

**EXECUTION INSTRUCTION:**
Read `docs/MDM/Repo Intelligence System — Master Data.MD` and output Deliverable 1, Deliverable 2, and Deliverable 3 immediately.
