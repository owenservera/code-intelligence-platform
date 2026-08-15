# CIP v1.8 - Intelligent Repository Analysis System

## Problem Statement
Current CIP provides raw data (files, symbols, edges) but lacks:
- Actionable insights for developers
- Prioritized improvement areas
- Health metrics that guide work
- Clear "what to work on next" guidance

## System Design

### Core Analysis Framework

#### 1. Code Health Score (0-100)
**Components:**
- **Test Coverage**: % of symbols with tests
- **Code Quality**: Density of findings (secrets, dup, complexity)
- **Freshness**: How recently indexed
- **Documentation**: Ratio of docs to code
- **Complexity**: Cyclomatic complexity hotspots

**Formula:**
```
health_score = (coverage * 0.3) + (quality * 0.3) + (freshness * 0.2) + (docs * 0.1) + (complexity * 0.1)
```

#### 2. Priority Work Areas
**Categories:**
- **Critical**: Security issues, breaking changes, high-risk dead code
- **High**: Untested hot code, performance bottlenecks, tech debt
- **Medium**: Code duplication, missing docs, inconsistent patterns
- **Low**: Style issues, minor optimizations

**Detection:**
- Load-bearing symbols without tests (high dependents, zero tests)
- Security findings (secrets, auth issues)
- Performance hotspots (large functions, deep nesting)
- Code duplication (identical implementations)
- Dead code (zero inbound edges, not exported)

#### 3. Impact Analysis
**For any change:**
- Files affected (blast radius)
- Tests to run (coverage mapping)
- Risk level (low/medium/high)
- Dependencies impacted (upstream/downstream)

#### 4. Technical Debt Inventory
**Types:**
- **Test Debt**: Untested load-bearing functions
- **Complexity Debt**: High cyclomatic complexity
- **Duplication Debt**: Repeated code patterns
- **Documentation Debt**: Missing docs for public APIs
- **Security Debt**: Secrets, auth issues

## Implementation Plan

### Phase 1: Enhanced Metrics
```python
def repo_health_report(root):
    """Generate comprehensive health report."""
    return {
        "overall_score": calculate_health_score(),
        "critical_issues": list_critical(),
        "high_priority": list_high_priority(),
        "test_coverage": coverage_analysis(),
        "technical_debt": debt_inventory(),
        "hotspots": identify_hotspots(),
        "recommendations": generate_recommendations()
    }
```

### Phase 2: Actionable Insights
- **"What to fix first"**: Prioritized list by impact/effort
- **"Where to add tests"**: Untested load-bearing code
- **"What to refactor"**: Duplication and complexity
- **"What to document"**: Public APIs without docs

### Phase 3: Interactive Reports
- **Trend analysis**: Health over time
- **Team focus**: Areas needing team attention
- **Sprint planning**: Prioritized backlog items
- **Onboarding**: Key areas for new developers

## Expected Output Format

### Executive Summary
```
Repository Health: 72/100
Critical Issues: 3
High Priority: 12
Test Coverage: 45%
Technical Debt: Medium
```

### Priority Work Areas
```
1. [CRITICAL] Add tests for _read() (11 dependents, 0 tests)
2. [HIGH] Remove duplicate _read() implementation (3 copies)
3. [HIGH] Fix secret in config.ts (line 42)
4. [MEDIUM] Document public API in auth.ts
5. [MEDIUM] Reduce complexity in process() (cyclomatic: 15)
```

### Impact Analysis
```
If you change src/index.ts:
- Risk: LOW
- Files affected: 1
- Tests to run: 0
- Dependencies: 0
```

## Value Proposition
- **Clear priorities**: Know what to work on first
- **Risk awareness**: Understand impact of changes
- **Quality tracking**: Measure improvement over time
- **Team alignment**: Shared understanding of technical state
