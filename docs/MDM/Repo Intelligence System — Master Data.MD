# Repo Intelligence System — Master Data Taxonomy (L0–LA)

A layered Master Data Model (MDM) for a repo-native, AI-assisted analysis engine that ingests a codebase and produces a structured, queryable graph of facts, patterns, risks, and recommendations. Each layer builds on the one below it — lower layers are objective/mechanical, higher layers are interpretive/synthetic. Every entity below is documented the way an MDM steward would document a domain: **Entity → Purpose → Core Attributes → Detection Method → Example Findings → Severity/Confidence Model → Downstream Consumers.**

---

## Layering Philosophy

| Layer | Name | Nature | Question it answers |
|---|---|---|---|
| L0 | Repo Topology & Ingestion | Objective/raw | "What exists?" |
| L1 | Syntax & Parse | Objective/mechanical | "What is it made of?" |
| L2 | Symbol & Dependency Graph | Objective/structural | "What refers to what?" |
| L3 | Type & Semantic Layer | Objective/inferred | "What does it mean?" |
| L4 | Control & Data Flow | Derived | "How does data move and branch?" |
| L5 | Architectural Boundary Layer | Interpretive | "How is the system supposed to be shaped?" |
| L6 | Code Quality & Smell Layer | Interpretive | "Where does it hurt to work?" |
| L7 | Cross-Cutting Concern Layer | Interpretive | "What crosscuts everything (security, config, secrets, i18n)?" |
| L8 | Runtime & Operational Signal Layer | Empirical | "What actually happens when it runs?" |
| L9 | Historical & Evolutionary Layer | Temporal | "How did it get this way, and how fast is it changing?" |
| LA | Governance, Risk & Synthesis Layer | Synthetic/meta | "So what — what should a human do about it?" |

Each layer emits **entities** (nodes), **edges** (relationships), and **findings** (annotated facts with severity/confidence). LA is the only layer that produces prioritized, human-facing recommendations; L0–L9 are the evidence base.

---

## L0 — Repo Topology & Ingestion Layer

**Purpose:** Establish ground truth about what physically exists before any interpretation happens. This is the "inventory" layer — no judgment, pure cataloging.

| Entity | Description | Core Attributes | Detection Method | Example Findings |
|---|---|---|---|---|
| `Repository` | Top-level unit of analysis | repo_id, vcs_type, default_branch, size_bytes, language_histogram | Filesystem walk + VCS metadata | "Repo is 62% Rust, 24% TypeScript, 14% config/markup" |
| `Module/Package` | Logical unit boundary (crate, npm package, Python package) | manifest_path, declared_deps, version, publish_target | Parse manifest files (Cargo.toml, package.json, pyproject.toml) | "3 workspace crates declare overlapping but non-identical dep versions" |
| `File` | Individual source file | path, language, loc, byte_size, encoding, is_generated | Static walk + language sniff | "14 files flagged as generated but lack a 'DO NOT EDIT' header" |
| `Workspace Structure` | Monorepo/multi-crate/multi-package topology | topology_type (mono/poly), workspace_manifest, member_list | Manifest graph parse | "Tauri frontend and Rust backend share no workspace-level lint config" |
| `Build Artifact Map` | What produces what | build_target, entrypoint, output_path | Build config parse (Cargo, Vite, Webpack) | "Two build targets emit to the same output directory (collision risk)" |
| `Ignore/Exclusion Rules` | What's deliberately out of scope | .gitignore, .dockerignore, analyzer excludes | File parse | "node_modules included in size scan, skewing LOC metrics" |
| `Orphan File` | File not referenced by any build/import graph | path, last_modified, reachability_status | Cross-ref with L2 dependency graph | "`legacy_parser_v1.rs` has zero inbound references — dead file candidate" |

**Confidence model:** near-100% — this layer is deterministic. Findings here are facts, not opinions.

**Downstream consumers:** every other layer depends on L0 as its universe of discourse.

---

## L1 — Syntax & Parse Layer

**Purpose:** Turn raw text into structured, queryable syntax trees. This is where "code as text" becomes "code as data."

| Entity | Description | Core Attributes | Detection Method | Example Findings |
|---|---|---|---|---|
| `AST Node` | Parsed syntax unit | node_type, span, parent_id, language | Tree-sitter / native parser per language | Baseline for all higher-layer queries |
| `Function/Method Def` | Callable unit | signature, arity, visibility, is_async, is_generic, cyclomatic_complexity | AST extraction | "`process_provider_response` has cyclomatic complexity 34 (threshold: 10)" |
| `Type/Struct/Trait Def` | Data or interface shape | fields, derives/traits, generic_params | AST extraction | "`ProviderConfig` struct has 21 fields, 9 of which are `Option<T>`" |
| `Comment/Doc Block` | Inline documentation | span, associated_symbol, doc_coverage_flag | AST + doc-comment parse | "42% of public API surface has no doc comment" |
| `Macro/Codegen Expansion` | Compile-time generated code | macro_name, expansion_target, is_derive | Macro-aware parse (where supported) | "Derive macro expands to 400+ hidden LOC not visible in diff review" |
| `Parse Failure` | Code the parser couldn't fully resolve | file, reason, partial_ast | Parser error capture | "3 files fail parse due to unstable syntax feature — analysis coverage gap" |

**Confidence model:** deterministic per-language, but coverage gaps (parse failures, unsupported syntax) should be explicitly surfaced rather than silently dropped — a hidden blind spot is worse than a known one.

**Downstream consumers:** L2 (symbol resolution), L6 (complexity metrics), L9 (churn-per-function).

---

## L2 — Symbol & Dependency Graph Layer

**Purpose:** Resolve names to definitions and build the "what calls/imports/uses what" graph — the backbone every architectural claim rests on.

| Entity | Description | Core Attributes | Detection Method | Example Findings |
|---|---|---|---|---|
| `Symbol` | Resolved named entity (fn, type, var, const) | fqn, definition_site, visibility, kind | Scope-aware resolution | Baseline registry |
| `Call Edge` | Function A calls Function B | caller, callee, call_site, is_conditional | Call-graph construction | "`spawn_browser_session` is called from 11 sites across 4 modules with no shared error path" |
| `Import Edge` | Module A imports Module B | source, target, import_kind (direct/re-export/wildcard) | Import statement parse | "Wildcard import in `engine/mod.rs` obscures where 6 symbols actually originate" |
| `Dependency Cycle` | Circular reference between modules/files/crates | cycle_members, cycle_length, cycle_type (compile-time/runtime) | Graph cycle detection (Tarjan's SCC) | "`canvas_engine` ↔ `render_pipeline` form a 2-node cycle — blocks independent compilation" |
| `Fan-in / Fan-out` | Coupling metrics per symbol/module | fan_in_count, fan_out_count, instability_index | Graph degree calculation | "`AppState` struct has fan-in of 47 — near-universal dependency, high blast radius" |
| `External Dependency` | Third-party crate/package usage | name, version, license, is_direct, is_transitive | Manifest + lockfile parse | "`openssl` pinned to a version with a known CVE; 3 transitive deps pull conflicting versions" |
| `Unused Symbol` | Defined but never referenced | symbol, definition_site, visibility | Graph reachability from entrypoints | "`legacy_migrate_v2()` is `pub` but has zero callers repo-wide" |
| `God Object Candidate` | Node with disproportionate graph centrality | symbol, centrality_score, responsibility_count | Centrality analysis + heuristic on responsibility breadth | "`vivim_core::Engine` is imported by 80% of modules and owns 6 unrelated responsibilities" |

**Confidence model:** high for statically-typed/compiled languages; moderate for dynamic languages with reflection/dynamic dispatch (flag reduced confidence explicitly).

**Downstream consumers:** L5 (architecture), L6 (coupling smells), LA (blast-radius risk scoring).

---

## L3 — Type & Semantic Layer

**Purpose:** Understand *meaning*, not just structure — what a value can be, what a function's contract actually is, where meaning is being smuggled through weak types.

| Entity | Description | Core Attributes | Detection Method | Example Findings |
|---|---|---|---|---|
| `Inferred Type` | Type of an expression/binding | expr_site, resolved_type, is_explicit | Type-checker integration (rustc, tsc, mypy) | "`response.data` typed as `any` in 38 call sites — type safety erased" |
| `Nullable/Optional Path` | Where `null`/`None`/`Option` can flow | binding, is_handled, unwrap_site | Flow-sensitive nullability analysis | "`.unwrap()` called on `Option<Provider>` at 6 sites with no prior guard — panic risk" |
| `Contract Mismatch` | Doc/type says one thing, usage does another | symbol, declared_contract, observed_usage | Cross-reference doc comments vs. call sites | "Doc says `timeout_ms` is optional; every call site passes it — dead default path" |
| `Stringly-Typed Boundary` | Data that should be a type but is a string/dict | site, current_repr, suggested_type | Pattern detection on string comparisons/magic values | "Provider names compared via string literals in 14 places instead of an enum" |
| `Error Type Taxonomy` | How errors are represented and propagated | error_type, is_typed, swallow_sites | Error-type graph + catch/match analysis | "23 distinct error paths collapse into a single generic `AppError::Unknown`" |
| `Implicit Conversion` | Silent type coercion | site, from_type, to_type, risk_class | Compiler/linter coercion warnings | "Implicit `i64 → i32` truncation in token-count accumulator" |

**Confidence model:** high in strongly-typed languages with full type-checker integration; explicitly lower in loosely-typed regions — surface this as a per-file "type confidence score."

**Downstream consumers:** L6 (smell scoring), L7 (security — type confusion is a common vuln class), LA.

---

## L4 — Control & Data Flow Layer

**Purpose:** Trace *how* data and execution actually move — the layer that catches "wiring gaps" (things that look connected but aren't, or connect to the wrong thing).

| Entity | Description | Core Attributes | Detection Method | Example Findings |
|---|---|---|---|---|
| `Control Flow Graph (CFG)` | Branch/loop/exit structure per function | nodes, edges, unreachable_blocks | AST-driven CFG construction | "`handle_provider_error` has an unreachable branch after an early return" |
| `Data Flow Path` | Value's journey from source to sink | source, sink, transform_chain, is_sanitized | Taint-style flow analysis | "User-supplied prompt text flows unsanitized into a shell command construction" |
| `Dead Code Path` | Reachable-by-parser but logically unreachable | site, reason (always-false condition, etc.) | Symbolic/heuristic branch evaluation | "Feature flag check is hardcoded `false` — 200 LOC behind it are dead" |
| `Event/Message Wiring` | Emitter ↔ listener bindings (pub/sub, IPC, Tauri events) | event_name, emitter_sites, listener_sites, match_confidence | String/const correlation across emit/listen calls | "Frontend listens for `'provider:disconnected'`; backend emits `'provider_disconnected'` — **wiring gap, silent no-op**" |
| `Async/Await Boundary` | Points where sync/async semantics meet | site, blocking_risk, unawaited_future | Async graph analysis | "3 `spawn`ed tasks have no `.await` or join handle — fire-and-forget with unhandled panics" |
| `State Mutation Site` | Where shared/global state changes | state_owner, mutation_site, lock_status | Mutability + concurrency primitive tracking | "`AppState.sessions` mutated from 4 async contexts without a consistent lock ordering — race condition risk" |
| `Callback/Handler Registration Gap` | Registered handler with no corresponding trigger, or vice versa | handler_id, registration_site, trigger_site (nullable) | Cross-reference registration calls against invocation sites | "IPC command `restart_provider` registered in Rust but never invoked from any frontend call site" |

**Confidence model:** medium-high for statically traceable flows; string-matched event wiring should carry an explicit "fuzzy match" confidence tier since names can diverge (snake_case vs. kebab-case) without truly being disconnected.

**Downstream consumers:** LA (this is one of the highest-value layers for "wiring gap" reporting specifically), L7 (security — taint flow).

---

## L5 — Architectural Boundary Layer

**Purpose:** Compare the *intended* architecture (layers, boundaries, ownership) against the *actual* graph from L2–L4. This is where "architectural structure warnings" live.

| Entity | Description | Core Attributes | Detection Method | Example Findings |
|---|---|---|---|---|
| `Declared Boundary` | Explicit or inferred architectural layer (e.g., "core engine," "UI," "provider adapters") | boundary_name, member_modules, declared_via (config/convention/doc) | Convention detection + optional architecture-as-code config | "Repo has an implicit `engine/ / bridge/ / ui/` layering with no enforcement config" |
| `Boundary Violation` | Import/call that crosses a layer it shouldn't | source_module, target_module, violated_boundary, rule | Rule-based graph query against declared boundaries | "`ui/canvas` directly imports a `provider/` internal module, bypassing the adapter interface" |
| `Layering Direction Violation` | Lower layer depends on higher layer (inversion) | dependent, dependency, expected_direction | Directed graph check against declared hierarchy | "`core::engine` imports from `bridge::chrome_extension` — inverts intended dependency direction" |
| `Interface/Adapter Consistency` | Are all implementers of a trait/interface structurally consistent? | interface_name, implementer_count, divergence_points | Interface implementation diffing | "5 of 7 provider adapters implement retry logic; 2 silently omit it" |
| `Layering Leakage` | Implementation detail exposed through a public boundary | symbol, boundary, leak_type | Visibility + type analysis at boundary edges | "Internal `SqliteRowId` type leaks into the public `Session` API — storage engine can't be swapped without a breaking change" |
| `Single Responsibility Violation` | Module/file doing structurally unrelated things | module, responsibility_clusters | Symbol co-occurrence clustering within a file/module | "`utils.rs` contains auth logic, string formatting, and browser CDP helpers — 3 unrelated clusters" |
| `Missing Abstraction` | Repeated concrete pattern that should be an interface | pattern_signature, occurrence_sites | Structural clone detection across sibling modules | "6 provider integrations each hand-roll near-identical retry/backoff logic instead of sharing one" |

**Confidence model:** this layer is the first genuinely interpretive one — findings should always cite the specific rule or convention violated, and confidence should be reported as "structural fact" (high) vs. "architectural judgment" (medium, since "should this be a layer violation" is sometimes a legitimate design choice).

**Downstream consumers:** LA (architecture debt scoring), engineering leads directly.

---

## L6 — Code Quality & Smell Layer

**Purpose:** The classic "bad coding practice" layer — localized, well-understood anti-patterns and complexity traps, independent of architecture.

| Entity | Description | Core Attributes | Detection Method | Example Findings |
|---|---|---|---|---|
| `Complexity Trap` | Function/module whose complexity metrics exceed sustainable thresholds | metric_type (cyclomatic/cognitive/nesting-depth), value, threshold | Static complexity metrics | "`resolve_provider_adapter` has cognitive complexity 41 across 6 nesting levels" |
| `Duplication Cluster` | Near-identical code blocks | cluster_id, member_sites, similarity_score, token_count | Token/AST-based clone detection (Type 1–3 clones) | "12 near-duplicate CDP-attachment retry blocks across provider files, ~85% similarity" |
| `Naming Inconsistency` | Same concept named differently across the repo | concept, variant_names, sites | Fuzzy/semantic name clustering | "'session', 'conversation', and 'thread' used interchangeably for the same entity across 3 modules" |
| `Magic Value` | Unexplained literal (number/string) with semantic weight | value, site, suggested_constant_name | Literal usage heuristics (non-trivial, repeated, or business-logic-adjacent literals) | "Timeout literal `30000` hardcoded in 9 places with no shared constant" |
| `Error Swallowing` | Caught error not logged, propagated, or handled | catch_site, handling_action (none/log-only/silent) | Catch/match block analysis | "17 `catch (e) {}` blocks with empty bodies in the browser automation layer" |
| `Long Parameter List` | Function signature exceeding readable arity | function, param_count, threshold | Signature inspection | "`spawn_session(a,b,c,d,e,f,g,h)` — 8 positional params, no builder/config object" |
| `Deep Nesting / Arrow Anti-Pattern` | Excessive conditional/loop nesting | site, depth | AST depth measurement | "5-level nested `if` in provider response parser — candidate for guard clauses" |
| `Test Coverage Gap` | Code paths with no corresponding test | module/function, coverage_pct, criticality_weight | Coverage tool integration + criticality weighting from L2 fan-in | "`token_accounting.rs` has 0% test coverage despite fan-in of 22 (high blast radius, untested)" |
| `Flaky/Brittle Test Signature` | Tests with timing dependence, order dependence, or excessive mocking | test_id, brittleness_indicators | Pattern detection on test source (sleeps, global state, snapshot-only assertions) | "`test_provider_reconnect` uses a hardcoded `sleep(500)` — timing-dependent flake risk" |
| `Commented-Out / Zombie Code` | Dead code preserved as comments | span, age_estimate | Comment pattern + git blame cross-ref (L9) | "140 LOC of commented-out legacy auth flow, untouched for 8 months" |
| `TODO/FIXME/HACK Debt Marker` | Explicit self-flagged debt | marker_type, comment_text, age, associated_symbol | Comment scanning + git blame | "23 `// TODO: fix race condition` markers, oldest is 11 months old" |

**Confidence model:** high — these are the most codified, tool-mature detection patterns in the industry (lint-rule equivalents). Severity should scale with L2 blast-radius (fan-in) so a smell in a hot-path core file outranks the same smell in a leaf utility.

**Downstream consumers:** LA (technical debt index), CI gating.

---

## L7 — Cross-Cutting Concern Layer

**Purpose:** Concerns that don't live in one module but bleed across the whole repo — security, configuration, secrets, i18n, accessibility, licensing.

| Entity | Description | Core Attributes | Detection Method | Example Findings |
|---|---|---|---|---|
| `Secret/Credential Exposure` | Hardcoded or logged sensitive material | site, secret_type, exposure_channel (source/log/comment) | Pattern + entropy-based secret scanning | "API key literal found in a committed config file, also echoed in a debug `println!`" |
| `Security Anti-Pattern` | Known vulnerable pattern (injection, path traversal, unsafe deserialization) | pattern_class (OWASP category), site, taint_path (from L4) | Rule-based pattern match + taint flow cross-ref | "Shell command built via string concatenation of user input in the browser automation layer — command injection risk" |
| `Permission/Privilege Surface` | Where the app requests or exercises elevated capability | capability (filesystem/network/exec/clipboard), grant_site, usage_sites | Manifest + API-call inventory (Tauri capabilities, OS permissions) | "Tauri config grants full filesystem scope; only 2 of 14 commands actually touch the filesystem" |
| `Config Sprawl` | Configuration values scattered across many formats/locations | config_key, locations, format_types, has_single_source_of_truth | Cross-file config-key extraction | "`provider_timeout` is defined independently in 3 files with 3 different default values" |
| `Environment/Secret Leakage Risk` | `.env` or credential file at risk of being committed | file, is_gitignored, is_tracked | .gitignore cross-reference + VCS tracked-file check | "`.env.local` is tracked in git history despite being in current `.gitignore`" |
| `Dependency Vulnerability` | Known CVE in direct/transitive dependency | package, version, CVE_id, severity | Lockfile scan against vulnerability database | "`ws` package pinned to a version with a known DoS CVE, transitively pulled by 2 dev dependencies" |
| `License Compatibility` | Dependency license conflicts with project license | package, license, compatibility_status | License metadata scan | "GPL-licensed dependency pulled into a codebase intended for closed-source distribution" |
| `I18n/L10n Readiness Gap` | Hardcoded user-facing strings | site, string_value, is_externalized | UI string literal scan | "112 hardcoded English strings in the canvas UI with no i18n extraction layer" |
| `Accessibility Gap` | Missing a11y attributes/semantics in UI code | component, missing_attribute | Frontend AST scan for a11y patterns | "18 interactive canvas elements lack ARIA roles or keyboard handlers" |

**Confidence model:** security findings should carry a distinct, conservative confidence rating (prefer false positives over false negatives) and always be flagged for human review before any auto-remediation.

**Downstream consumers:** LA (risk register), security review workflows.

---

## L8 — Runtime & Operational Signal Layer

**Purpose:** Ground static findings in what actually happens when the system runs — the layer that separates "theoretically risky" from "empirically hot."

| Entity | Description | Core Attributes | Detection Method | Example Findings |
|---|---|---|---|---|
| `Hot Path` | Code executed with high frequency in production/dev use | symbol, invocation_frequency, source (profiler/telemetry) | Profiler or opt-in telemetry ingestion | "`parse_provider_stream_chunk` accounts for 40% of CPU time under load" |
| `Exception/Panic Frequency` | Real-world error/crash occurrence tied to a code site | symbol, occurrence_count, source (crash reports/logs) | Log/crash-report correlation back to L2 symbols | "`unwrap()` at `session.rs:212` accounts for 60% of observed panics in the last 30 days" |
| `Performance Regression` | Measured slowdown correlated to a specific change | metric, baseline, current, commit_id (L9 link) | Benchmark tracking over time, bisected to commits | "P95 session-start latency regressed 340ms after commit `a1b2c3`, tracing to a synchronous disk read added in that diff" |
| `Resource Leak Signal` | Growing memory/handle/connection count over runtime | resource_type, growth_pattern, suspected_site | Runtime instrumentation / leak detector integration | "Browser CDP connections show monotonic growth over a 2-hour session — suspected missing `.close()` in error path" |
| `Feature Flag Reality Check` | Flag state in actual deployments vs. code assumption | flag_name, code_assumed_state, observed_state | Runtime config snapshot cross-ref with L4 dead-code findings | "Flag assumed 'off' in 3 code paths is actually 'on' in production — those paths are live, not dead" |

**Confidence model:** this layer is only as strong as the runtime signal available — it should be explicitly marked "unavailable/static-only" when no telemetry, profiler, or logs are wired in, rather than silently omitted.

**Downstream consumers:** LA (prioritizes static findings using real-world evidence — this is what turns "possible bug" into "confirmed hot bug").

---

## L9 — Historical & Evolutionary Layer

**Purpose:** Add the time dimension — churn, ownership, and trend, which is often the single best predictor of where bugs will occur next.

| Entity | Description | Core Attributes | Detection Method | Example Findings |
|---|---|---|---|---|
| `Churn Metric` | Change frequency per file/function | symbol, change_count, time_window, contributor_count | VCS log mining | "`provider_registry.rs` changed in 34 of the last 100 commits — highest churn in repo" |
| `Churn × Complexity Hotspot` | Intersection of high churn (L9) and high complexity (L6) | symbol, churn_score, complexity_score, hotspot_rank | Composite scoring across L6 + L9 | "`Engine::dispatch` is both top-decile complexity and top-decile churn — statistically the most bug-prone function in the repo" |
| `Bus Factor / Ownership Concentration` | How many distinct people understand/maintain a module | module, contributor_count, dominant_owner_pct | Git blame + commit authorship aggregation | "92% of commits to the tokenomics module are from a single author — high bus-factor risk" |
| `Revert/Fix-Commit Density` | Ratio of "fix"/"revert" commits to total commits, per area | module, fix_commit_ratio | Commit message classification + revert detection | "`vivim-p2p-onboarding` has a 3x higher fix-commit ratio than repo average — unstable area" |
| `Stale Code Signal` | Code untouched for an extended period, cross-referenced with usage | symbol, last_modified, is_still_referenced (L2) | Git timestamp + L2 reachability cross-ref | "`legacy_auth_bridge.rs` unmodified for 14 months but still actively imported — undermaintained but load-bearing" |
| `Architectural Drift` | Divergence between originally-documented architecture and current graph shape over time | boundary, drift_score_over_time | Time-series comparison of L5 boundary graphs across historical snapshots | "The engine/bridge boundary had 2 violations 6 months ago; now has 19 — architecture is actively eroding, not static debt" |

**Confidence model:** high — VCS data is objective; the *interpretation* of churn-as-risk is a well-validated heuristic in software engineering research, but should be presented as a strong correlation, not a certainty.

**Downstream consumers:** LA — this layer is often the single highest-signal input to prioritization, since "recently and repeatedly touched + complex" outperforms almost any purely static metric at predicting future defects.

---

## LA — Governance, Risk & Synthesis Layer

**Purpose:** The only layer that talks to a human directly. Synthesizes L0–L9 into prioritized, actionable, explainable findings — this is the "so what" layer, and it's where an MDM steward would define the canonical *finding record* itself.

| Entity | Description | Core Attributes | Detection Method | Example Findings |
|---|---|---|---|---|
| `Finding Record` (canonical output unit) | A single reportable issue | finding_id, layer_origin, category, severity, confidence, evidence_refs (links back to L0–L9 entities), suggested_fix, effort_estimate | Synthesis rules combining multiple layers | The master record every dashboard/report row maps to |
| `Severity Score` | Normalized 0–100 (or Critical/High/Med/Low) risk rating | blast_radius (L2 fan-in), runtime_evidence (L8), churn (L9), security_class (L7) | Weighted composite scoring model | "Severity=Critical: security taint path (L7) + confirmed panic in production (L8) + top-decile churn (L9)" |
| `Confidence Score` | How sure the system is, independent of severity | detection_determinism, cross_layer_corroboration_count | Meta-scoring on how many independent layers agree | "Confidence=High: static (L4) + runtime (L8) + historical (L9) all corroborate" |
| `Technical Debt Index` | Aggregate, trendable debt score per module/repo | debt_score, trend_direction, contributing_findings | Rollup of L5/L6/L7 findings weighted by L2 blast radius and L9 churn | "`bridge/` module debt index rose 18% over the last quarter, driven by 3 new boundary violations" |
| `Wiring Gap Report` | Curated cross-section of L4 findings specifically about broken connections | gap_type (event/handler/IPC/config), emitter, expected_listener, actual_listener_status | Direct rollup from L4 | "5 confirmed dead-letter events, 2 orphaned IPC handlers — see L4 detail" |
| `Architecture Health Report` | Curated cross-section of L5 + L9 drift findings | boundary_violation_count, drift_trend, worst_offending_modules | Rollup from L5 + L9 | "Layering integrity down 22% YoY; `ui/` → `provider/` direct coupling is the largest single contributor" |
| `Remediation Recommendation` | Concrete suggested action tied to a finding | action_type (refactor/test/patch/deprecate/document), estimated_effort, estimated_risk_reduction, suggested_owner (from L9 ownership) | Rule/template-based generation, optionally LLM-assisted narrative | "Extract shared retry/backoff logic from 6 provider adapters into a single trait — est. effort: M, removes 3 duplication-cluster findings and 1 boundary violation" |
| `Risk Register Entry` | Formal tracked risk with lifecycle | risk_id, status (open/acknowledged/mitigated/accepted), linked_findings, review_date | Governance workflow layer on top of Finding Records | "RISK-014: unbounded CDP connection growth — status: acknowledged, owner assigned, review in 2 weeks" |
| `Repo Health Scorecard` | Top-level rollup across all categories | dimension_scores (architecture/security/quality/test/ops), trend_arrows, headline_findings | Weighted rollup across all LA sub-entities | "Overall repo health: B−. Architecture: C+ (declining). Security: B+. Test coverage: D." |
| `Explainability Trace` | For any finding, the full evidence chain back to raw source | finding_id, layer_chain (L0→L9 refs), human_readable_narrative | Graph traversal + template narrative generation | Answers "why did the system flag this?" with a literal path through the layers, not a black-box score |

**Confidence model:** LA confidence is *derived*, never independently asserted — every LA finding must be traceable to specific lower-layer evidence (the `Explainability Trace` entity exists specifically to enforce this; no finding should reach a human without a "show your work" path).

**Governance principle:** LA is also where false-positive feedback loops live — when a human dismisses or overrides a finding, that decision should flow back down as a training/suppression signal rather than being lost, so the system's precision improves per-repo over time.

---

## Cross-Layer Relationship Summary

```
L0 Topology ──┐
L1 Syntax ─────┼──► L2 Symbol/Dep Graph ──► L5 Architecture ──┐
               │                                                │
L1 Syntax ─────┴──► L3 Types/Semantics ──► L4 Control/Data Flow┤
                                                                 │
L6 Quality/Smells ◄──── (uses L1, L2, L3 as input) ────────────┤
                                                                 ├──► LA Synthesis
L7 Cross-Cutting ◄──── (uses L2, L4 taint paths) ───────────────┤     (Finding Records,
                                                                 │      Scorecards,
L8 Runtime Signal ──── (independent empirical evidence) ───────┤      Risk Register)
                                                                 │
L9 Historical ──── (independent temporal evidence) ─────────────┘
```

Every finding surfaced at LA should be able to answer, on demand: *which raw facts, at which layers, produced this conclusion, and how confident should a human be in it.*

---

## Notes on Applying This to a Specific Repo

For a project like a Rust/Tauri hybrid (backend + browser automation + AI provider integration), the layers that will surface the most value first are typically:
- **L4** (event/IPC wiring gaps between Rust backend and Tauri frontend — a very common real-world source of "silent no-ops")
- **L5** (boundary violations between the core engine, browser automation layer, and provider adapters)
- **L7** (secrets/credentials in a project juggling multiple AI provider API keys)
- **L9** (churn×complexity hotspots, since a solo-maintained fast-moving repo accumulates hotspot risk quickly)

If useful, this taxonomy can be turned into an actual JSON/SQL schema (one table per entity, foreign keys forming the evidence chain into `Finding Record`) so it becomes a literal buildable data model rather than just documentation.
