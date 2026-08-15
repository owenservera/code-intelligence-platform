"""Intent analysis: route a natural-language request to the best CIP operations
(the multi-stage retrieval entry point from the spec)."""
import re

def route(query):
    q = query.lower()
    ops, intent = [], "search"
    has_ident = bool(re.findall(r"\b[A-Z][a-z]+[A-Z]\w*", query)) or bool(re.findall(r"\b\w+_\w+\b", query))
    if any(w in q for w in ("why ", "reason", "history", "blame", "workaround")):
        intent = "history"; ops.append("history(path=<path from search>)")
    if any(w in q for w in ("broken", "failing", "error", "red", "safe to refactor")):
        intent = "health"; ops.append("broken()")
    if any(w in q for w in ("architecture", "structure", "overview", "layout", "map", "how is")):
        intent = "architecture"; ops += ["map()", "summary()"]
    if any(w in q for w in ("test", "coverage")):
        ops.append("search(query='<subject> test')")
    if has_ident and intent == "search":
        intent = "symbol"; ops.insert(0, "symbol(name=<identifier>)")
    if intent == "search":
        ops.insert(0, "search(query=<query>)")
    ops.append("context(query=<query>)")
    return {"intent": intent, "query": query, "suggested_ops": ops[:5]}

def route_for_agent(query, context=None):
    """Enhanced routing for AI agents with confidence scores and rationale."""
    q = query.lower()
    base_route = route(query)
    
    suggestions = []
    
    # Analyze query patterns for agent-specific routing
    if "break" in q or "impact" in q or "affect" in q or "depend" in q:
        suggestions.append({
            "tool": "impact",
            "confidence": 0.9,
            "rationale": "Query asks about blast radius or dependencies"
        })
        if base_route["intent"] == "symbol":
            suggestions.append({
                "tool": "graph",
                "confidence": 0.85,
                "rationale": "After symbol lookup, graph shows dependency relationships"
            })
    
    if "test" in q or "coverage" in q:
        suggestions.append({
            "tool": "coverage",
            "confidence": 0.85,
            "rationale": "Query asks about test coverage"
        })
        suggestions.append({
            "tool": "broken",
            "confidence": 0.7,
            "rationale": "Check for failing tests"
        })
    
    if "api" in q or "endpoint" in q or "route" in q:
        suggestions.append({
            "tool": "api",
            "confidence": 0.9,
            "rationale": "Query asks about API contracts or endpoints"
        })
        suggestions.append({
            "tool": "routes",
            "confidence": 0.8,
            "rationale": "List available routes"
        })
    
    if "migration" in q or "schema" in q or "database" in q:
        suggestions.append({
            "tool": "migrations",
            "confidence": 0.85,
            "rationale": "Query asks about database migrations or schema"
        })
        suggestions.append({
            "tool": "models",
            "confidence": 0.75,
            "rationale": "Show database models"
        })
    
    if "dead" in q or "unused" in q:
        suggestions.append({
            "tool": "dead",
            "confidence": 0.9,
            "rationale": "Query asks about dead or unused code"
        })
    
    if "circular" in q or "cycle" in q:
        suggestions.append({
            "tool": "circular",
            "confidence": 0.9,
            "rationale": "Query asks about circular dependencies"
        })
    
    # Add context-aware suggestions
    if context:
        last_tool = context.get("last_tool")
        if last_tool == "symbol":
            suggestions.append({
                "tool": "graph",
                "confidence": 0.85,
                "rationale": "After symbol lookup, graph shows relationships"
            })
            suggestions.append({
                "tool": "context",
                "confidence": 0.8,
                "rationale": "Get context for the symbol"
            })
        elif last_tool == "impact":
            suggestions.append({
                "tool": "broken",
                "confidence": 0.8,
                "rationale": "After impact analysis, check for broken tests"
            })
        elif last_tool == "search":
            suggestions.append({
                "tool": "context",
                "confidence": 0.75,
                "rationale": "Get context for search results"
            })
    
    # If no specific suggestions, use base route
    if not suggestions:
        tool_map = {
            "search": "search",
            "symbol": "symbol",
            "history": "history",
            "health": "broken",
            "architecture": "map"
        }
        suggestions.append({
            "tool": tool_map.get(base_route["intent"], "search"),
            "confidence": 0.7,
            "rationale": f"Based on detected intent: {base_route['intent']}"
        })
    
    return {
        "primary": base_route,
        "suggestions": sorted(suggestions, key=lambda x: -x["confidence"]),
        "next_ops": _generate_next_ops(base_route, context)
    }

def _generate_next_ops(base_route, context):
    """Generate suggested follow-up operations."""
    ops = []
    intent = base_route["intent"]
    
    if intent == "symbol":
        ops.extend(["graph(id='<symbol_id>', direction='both')", "context(symbol='<symbol>')"])
    elif intent == "search":
        ops.extend(["context(query='<query>')", "graph(id='<top_symbol>')"])
    elif intent == "impact":
        ops.extend(["broken()", "context(query='<change>')"])
    elif intent == "architecture":
        ops.extend(["summary(path='<subsystem>')", "hotspots()"])
    elif intent == "health":
        ops.extend(["findings(severity='critical')", "refactors()"])
    
    return ops[:5]
