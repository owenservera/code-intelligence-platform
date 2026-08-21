"""analysis.py — intelligent repository analysis for actionable insights.

Provides health scoring, priority work areas, technical debt inventory,
and actionable recommendations for developers.
"""
from .base import repo_root, load_config
from .store import connect
from . import gapfill

def repo_health_report(root=None):
    """Generate comprehensive repository health report."""
    root = root or repo_root()
    con = connect(root)
    cfg = load_config(root)
    
    # Gather metrics
    health_score = _calculate_health_score(con, cfg, root)
    critical_issues = _list_critical_issues(con)
    high_priority = _list_high_priority(con)
    test_coverage = gapfill.coverage(root)
    technical_debt = _inventory_technical_debt(con)
    hotspots = _identify_hotspots(con)
    recommendations = _generate_recommendations(con, critical_issues, high_priority, technical_debt)
    
    return {
        "overall_score": health_score,
        "critical_issues": critical_issues,
        "high_priority": high_priority,
        "test_coverage": test_coverage,
        "technical_debt": technical_debt,
        "hotspots": hotspots,
        "recommendations": recommendations
    }

def _open_findings(con):
    """Read open audit findings directly from the stack findings table.

    The stack `findings` table is created lazily by the audit surface, so an
    index that has never been audited simply has none — which must be scored
    as a clean (0 severity) state, never trigger a "stack pack unavailable"
    fallback. Reading the table here removes the dependency on a stack-pack
    method that exists nowhere in this codebase (pre-fix BUG-013/F-01).
    """
    try:
        rows = con.execute("SELECT * FROM findings WHERE status='open'")
        return [dict(r) for r in rows]
    except Exception:
        return []


def _calculate_health_score(con, cfg, root):
    """Calculate overall health score (0-100)."""
    # Get basic stats
    total_symbols = con.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]

    # Test coverage component
    tested = con.execute("SELECT COUNT(*) FROM symbols WHERE id IN (SELECT DISTINCT src FROM edges WHERE kind='tested_by')").fetchone()[0]
    coverage_pct = (tested / total_symbols) * 100 if total_symbols > 0 else 0

    # Quality component (open findings from the audit stack)
    findings = _open_findings(con)
    critical_count = sum(1 for f in findings if f.get("severity") == "critical")
    high_count = sum(1 for f in findings if f.get("severity") == "high")
    quality_score = max(0, 100 - (critical_count * 20) - (high_count * 10))
    
    # Freshness component
    try:
        from .maintain import verify
        verify_result = verify(root)
        fresh = verify_result.get("fresh", False)
        freshness_score = 100 if fresh else 50
    except Exception as e:
        from .base import log_swallowed
        log_swallowed("analysis._calculate_health_score/freshness", e)
        freshness_score = 50
    
    # Complexity component (dead code ratio)
    try:
        dead_result = gapfill.dead(root)
        dead_ratio = dead_result.get("count", 0) / total_symbols if total_symbols > 0 else 0
        complexity_score = max(0, 100 - (dead_ratio * 100))
    except Exception as e:
        from .base import log_swallowed
        log_swallowed("analysis._calculate_health_score/complexity", e)
        complexity_score = 80
    
    # Weighted score
    health = (coverage_pct * 0.3) + (quality_score * 0.3) + (freshness_score * 0.2) + (complexity_score * 0.2)
    return round(health, 1)

def _list_critical_issues(con):
    """List critical issues requiring immediate attention."""
    issues = []
    
    # Security findings
    for f in _open_findings(con):
        if f.get("severity") == "critical":
            issues.append({
                "type": "security",
                "rule": f.get("rule"),
                "path": f.get("path"),
                "line": f.get("line"),
                "title": f.get("title"),
                "suggestion": f.get("suggestion")
            })
    
    # Untested load-bearing symbols
    for row in con.execute("""
        SELECT s.id, s.name, s.path, 
               (SELECT COUNT(*) FROM edges WHERE dst=s.id) as dependents
        FROM symbols s
        WHERE s.kind IN ('function', 'method', 'class')
        AND s.id NOT IN (SELECT DISTINCT src FROM edges WHERE kind='tested_by')
        AND (SELECT COUNT(*) FROM edges WHERE dst=s.id) > 5
        ORDER BY dependents DESC
        LIMIT 5
    """).fetchall():
        issues.append({
            "type": "untested_hot",
            "symbol": row["name"],
            "path": row["path"],
            "dependents": row["dependents"],
            "title": f"'{row['name']}' has {row['dependents']} dependents but no tests",
            "suggestion": "Add at least one test before modifying this load-bearing code"
        })
    
    return issues

def _list_high_priority(con):
    """List high-priority items."""
    items = []
    
    # Code duplication
    for f in _open_findings(con):
        if f.get("severity") == "high" or f.get("rule") == "QA-DUP":
            items.append({
                "type": "quality",
                "rule": f.get("rule"),
                "path": f.get("path"),
                "title": f.get("title"),
                "suggestion": f.get("suggestion")
            })
    
    # High complexity functions
    for row in con.execute("""
        SELECT s.id, s.name, s.path, s.end_line - s.start_line as size
        FROM symbols s
        WHERE s.kind IN ('function', 'method')
        AND (s.end_line - s.start_line) > 100
        ORDER BY size DESC
        LIMIT 5
    """).fetchall():
        items.append({
            "type": "complexity",
            "symbol": row["name"],
            "path": row["path"],
            "size": row["size"],
            "title": f"'{row['name']}' is very large ({row['size']} lines)",
            "suggestion": "Consider breaking this function into smaller, testable pieces"
        })
    
    return items

def _inventory_technical_debt(con):
    """Inventory technical debt by category."""
    debt = {
        "test_debt": [],
        "complexity_debt": [],
        "duplication_debt": [],
        "documentation_debt": []
    }
    
    # Test debt
    for row in con.execute("""
        SELECT s.id, s.name, s.path,
               (SELECT COUNT(*) FROM edges WHERE dst=s.id) as dependents
        FROM symbols s
        WHERE s.kind IN ('function', 'method')
        AND s.id NOT IN (SELECT DISTINCT src FROM edges WHERE kind='tested_by')
        AND (SELECT COUNT(*) FROM edges WHERE dst=s.id) > 2
        ORDER BY dependents DESC
        LIMIT 10
    """).fetchall():
        debt["test_debt"].append({
            "symbol": row["name"],
            "path": row["path"],
            "dependents": row["dependents"]
        })
    
    # Complexity debt
    for row in con.execute("""
        SELECT s.name, s.path, s.end_line - s.start_line as size
        FROM symbols s
        WHERE s.kind IN ('function', 'method')
        AND (s.end_line - s.start_line) > 50
        ORDER BY size DESC
        LIMIT 10
    """).fetchall():
        debt["complexity_debt"].append({
            "symbol": row["name"],
            "path": row["path"],
            "size": row["size"]
        })
    
    return debt

def _identify_hotspots(con):
    """Identify code hotspots (high change/impact areas)."""
    hotspots = []
    
    # Files with most symbols
    for row in con.execute("""
        SELECT path, COUNT(*) as symbol_count
        FROM symbols
        GROUP BY path
        ORDER BY symbol_count DESC
        LIMIT 10
    """).fetchall():
        hotspots.append({
            "path": row["path"],
            "symbols": row["symbol_count"],
            "type": "dense"
        })
    
    # Symbols with most dependents
    for row in con.execute("""
        SELECT s.id, s.name, s.path,
               (SELECT COUNT(*) FROM edges WHERE dst=s.id) as dependents
        FROM symbols s
        WHERE s.kind IN ('function', 'method', 'class')
        ORDER BY dependents DESC
        LIMIT 10
    """).fetchall():
        hotspots.append({
            "symbol": row["name"],
            "path": row["path"],
            "dependents": row["dependents"],
            "type": "load_bearing"
        })
    
    return hotspots

def _generate_recommendations(con, critical, high_priority, debt):
    """Generate actionable recommendations."""
    recommendations = []
    
    # Based on critical issues
    for issue in critical:
        if issue["type"] == "untested_hot":
            recommendations.append({
                "priority": "CRITICAL",
                "action": f"Add tests for {issue['symbol']} in {issue['path']}",
                "impact": f"Affects {issue['dependents']} dependents",
                "effort": "small"
            })
        elif issue["type"] == "security":
            recommendations.append({
                "priority": "CRITICAL",
                "action": f"Fix security issue: {issue['title']}",
                "impact": "Security vulnerability",
                "effort": "medium"
            })
    
    # Based on high priority
    for item in high_priority[:5]:
        if item["type"] == "complexity":
            recommendations.append({
                "priority": "HIGH",
                "action": f"Refactor {item['symbol']} in {item['path']}",
                "impact": "Reduce complexity, improve maintainability",
                "effort": "medium"
            })
    
    # Based on test debt
    for item in debt["test_debt"][:3]:
        recommendations.append({
            "priority": "HIGH",
            "action": f"Add test coverage for {item['symbol']}",
            "impact": f"Protect {item['dependents']} dependents",
            "effort": "small"
        })
    return recommendations


def mdm_analysis(root=None):
    """Run full Master Data Model (L0-LA) multi-layer extraction and synthesis."""
    from .mdm_synthesis import generate_full_mdm_report
    return generate_full_mdm_report(root)


def mdm_report(root=None, fmt="dict"):
    """Get formatted Master Data Model report (dict or markdown)."""
    from .mdm_synthesis import generate_full_mdm_report, format_report_markdown
    report = generate_full_mdm_report(root)
    if fmt == "markdown":
        return format_report_markdown(report)
    return report

