"""predict.py — predictive context suggestions for AI agents.

Anticipates what context an agent will need next based on current operation
and provides smart budgeting for context packs.
"""
import re
from .base import repo_root, load_config, est_tokens
from .store import connect
from . import retrieve, router
from . import learning

def predict_next_context(root, current_operation, current_symbol=None, current_query=None):
    """Predict what context the agent will need next.
    
    Applies learning-based confidence adjustments from historical session data.
    """
    predictions = []
    
    if current_operation == "symbol":
        # After symbol lookup, likely need:
        # - Graph of relationships
        # - Context pack for the symbol
        # - Files that use this symbol
        if current_symbol:
            symbol_name = current_symbol.split('#')[-1] if '#' in current_symbol else current_symbol
            predictions.extend([
                {"tool": "graph", "args": {"id": current_symbol}, "confidence": 0.9, "reason": "Show symbol relationships"},
                {"tool": "context", "args": {"symbol": current_symbol}, "confidence": 0.85, "reason": "Get symbol context"},
                {"tool": "search", "args": {"query": f"uses of {symbol_name}"}, "confidence": 0.7, "reason": "Find usage locations"}
            ])
    
    elif current_operation == "impact":
        # After impact analysis, likely need:
        # - Test coverage for affected files
        # - Broken tests in the area
        # - Findings in affected area
        predictions.extend([
            {"tool": "broken", "args": {}, "confidence": 0.8, "reason": "Check for failing tests"},
            {"tool": "coverage", "args": {}, "confidence": 0.6, "reason": "Check test coverage"},
            {"tool": "findings", "args": {"severity": "critical"}, "confidence": 0.7, "reason": "Check critical findings"}
        ])
    
    elif current_operation == "search":
        # After search, likely need:
        # - Context for top results
        # - Graph for top symbols
        predictions.extend([
            {"tool": "context", "args": {"query": current_query}, "confidence": 0.75, "reason": "Get context for search results"}
        ])
    
    elif current_operation == "graph":
        # After graph traversal, likely need:
        # - Context for related symbols
        predictions.extend([
            {"tool": "context", "args": {"symbol": current_symbol}, "confidence": 0.8, "reason": "Get context for graph nodes"}
        ])
    
    elif current_operation == "broken":
        # After checking broken tests, likely need:
        # - Impact analysis for failing files
        # - Findings in the area
        predictions.extend([
            {"tool": "findings", "args": {}, "confidence": 0.85, "reason": "Review all findings"},
            {"tool": "refactors", "args": {}, "confidence": 0.7, "reason": "Check quick-win refactors"}
        ])
    
    # Apply learning-based confidence adjustments
    root = root or repo_root()
    adjusted_predictions = learning.apply_learning_to_predictions(root, current_query, predictions)
    
    return {"predictions": adjusted_predictions[:5]}

def context_adaptive(root, query=None, symbol=None, base_budget=6000):
    """Adaptive context budgeting based on query complexity."""
    from .store import connect
    from . import retrieve
    
    con = connect(root)
    cfg = load_config(root)
    
    # Assess query complexity
    complexity = _assess_complexity(query or "")
    
    # Dynamic budget
    if complexity == "simple":
        budget = base_budget * 0.5
    elif complexity == "medium":
        budget = base_budget
    else:  # complex
        budget = base_budget * 1.5
    
    # Gather context with relevance scoring
    sections = []
    if symbol:
        # Get symbol definition
        sym = con.execute("SELECT * FROM symbols WHERE id=?", (symbol,)).fetchone()
        if sym:
            sections.append({
                "why": "symbol_definition",
                "meta": {"path": sym["path"], "lines": [sym["start_line"], sym["end_line"]]},
                "text": sym.get("body", "")[:2000],
                "relevance": 1.0
            })
    
    # Get relationships if symbol provided
    if symbol:
        from . import retrieve
        graph_data = retrieve.graph(root, symbol, "both", depth=1)
        for node in graph_data.get("nodes", [])[:5]:
            if node != symbol:
                sym_data = con.execute("SELECT * FROM symbols WHERE id=?", (node,)).fetchone()
                if sym_data:
                    sections.append({
                        "why": "related_symbol",
                        "meta": {"id": node, "path": sym_data["path"]},
                        "text": sym_data.get("body", "")[:1000],
                        "relevance": 0.7
                    })
    
    # If query provided, add search results
    if query:
        search_results = retrieve.search(root, query, k=5)
        for result in search_results[:3]:
            sections.append({
                "why": "search_hit",
                "meta": {"path": result["path"], "lines": result["lines"]},
                "text": result.get("snippet", ""),
                "relevance": 0.8
            })
    
    # Sort by relevance and fit budget
    sections.sort(key=lambda x: -x["relevance"])
    selected = []
    tokens_used = 0
    
    for section in sections:
        section_tokens = est_tokens(section["text"])
        if tokens_used + section_tokens <= budget:
            selected.append(section)
            tokens_used += section_tokens
    
    return {
        "sections": selected,
        "budget_used": tokens_used,
        "budget_total": int(budget),
        "complexity": complexity,
        "note": f"Adaptive budgeting: {complexity} complexity → {int(budget)} tokens"
    }

def _assess_complexity(query):
    """Assess query complexity based on length and patterns."""
    q = query.lower()
    
    # Simple: short, single concept
    if len(query) < 20 and not any(w in q for w in ("and", "or", "but", "with", "how", "why")):
        return "simple"
    
    # Complex: multiple concepts, nested questions
    if any(w in q for w in ("and", "or", "but")) or len(query) > 60:
        return "complex"
    
    # Medium: everything else
    return "medium"

def suggest_context_for_edit(root, file_path, line_number=None):
    """Suggest relevant context when an agent is about to edit a file."""
    con = connect(root)
    
    suggestions = []
    
    # Get symbols in the file
    symbols = list(con.execute(
        "SELECT id, name, kind, start_line, end_line FROM symbols WHERE path=?",
        (file_path,)
    ).fetchall())
    
    # If line number provided, find nearby symbols
    if line_number:
        nearby = [s for s in symbols if s["start_line"] <= line_number <= s["end_line"] or 
                  abs(s["start_line"] - line_number) < 10]
        for sym in nearby:
            suggestions.append({
                "type": "symbol",
                "id": sym["id"],
                "name": sym["name"],
                "kind": sym["kind"],
                "reason": "Symbol being edited or nearby"
            })
    
    # Get files that import this file
    importers = list(con.execute(
        "SELECT DISTINCT src FROM edges WHERE dst=? AND kind='imports'",
        (file_path,)
    ).fetchall())
    
    if importers:
        suggestions.append({
            "type": "impact",
            "count": len(importers),
            "reason": f"{len(importers)} files import this file"
        })
    
    # Check for test coverage
    tested = con.execute(
        "SELECT COUNT(*) c FROM edges WHERE src=? AND kind='tested_by'",
        (file_path,)
    ).fetchone()["c"]
    
    if tested == 0:
        suggestions.append({
            "type": "warning",
            "reason": "No tests cover this file"
        })
    
    # Check for findings
    findings = list(con.execute(
        "SELECT rule, severity FROM findings WHERE path=?",
        (file_path,)
    ).fetchall())
    
    if findings:
        suggestions.append({
            "type": "findings",
            "count": len(findings),
            "critical": sum(1 for f in findings if f["severity"] == "critical"),
            "reason": f"{len(findings)} findings in this file"
        })
    
    return {"suggestions": suggestions}
