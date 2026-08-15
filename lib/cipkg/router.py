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
    """Enhanced routing for AI agents with confidence scores and rationale.
    
    Returns structured output compatible with capability resolution engines
    (e.g., Vivim's CapabilityResolutionEngine). Each suggestion includes:
    - tool: capability identifier
    - confidence: 0.0-1.0 score
    - rationale: human-readable explanation
    - category: optional grouping for capability systems
    """
    q = query.lower()
    base_route = route(query)
    
    suggestions = []
    
    # Analyze query patterns for agent-specific routing
    if "break" in q or "impact" in q or "affect" in q or "depend" in q:
        suggestions.append({
            "tool": "cap:code:impact",
            "confidence": 0.9,
            "rationale": "Query asks about blast radius or dependencies",
            "category": "code-intelligence"
        })
        if base_route["intent"] == "symbol":
            suggestions.append({
                "tool": "cap:code:graph",
                "confidence": 0.85,
                "rationale": "After symbol lookup, graph shows dependency relationships",
                "category": "code-intelligence"
            })
    
    if "test" in q or "coverage" in q:
        suggestions.append({
            "tool": "cap:code:coverage",
            "confidence": 0.85,
            "rationale": "Query asks about test coverage",
            "category": "code-intelligence"
        })
        suggestions.append({
            "tool": "cap:code:broken",
            "confidence": 0.7,
            "rationale": "Check for failing tests",
            "category": "code-intelligence"
        })
    
    if "api" in q or "endpoint" in q or "route" in q:
        suggestions.append({
            "tool": "cap:code:api",
            "confidence": 0.9,
            "rationale": "Query asks about API contracts or endpoints",
            "category": "code-intelligence"
        })
        suggestions.append({
            "tool": "cap:code:routes",
            "confidence": 0.8,
            "rationale": "List available routes",
            "category": "code-intelligence"
        })
    
    if "migration" in q or "schema" in q or "database" in q:
        suggestions.append({
            "tool": "cap:code:migrations",
            "confidence": 0.85,
            "rationale": "Query asks about database migrations or schema",
            "category": "code-intelligence"
        })
        suggestions.append({
            "tool": "cap:code:models",
            "confidence": 0.75,
            "rationale": "Show database models",
            "category": "code-intelligence"
        })
    
    if "dead" in q or "unused" in q:
        suggestions.append({
            "tool": "cap:code:dead",
            "confidence": 0.9,
            "rationale": "Query asks about dead or unused code",
            "category": "code-intelligence"
        })
    
    if "circular" in q or "cycle" in q:
        suggestions.append({
            "tool": "cap:code:circular",
            "confidence": 0.9,
            "rationale": "Query asks about circular dependencies",
            "category": "code-intelligence"
        })
    
    # Add context-aware suggestions
    if context:
        last_tool = context.get("last_tool")
        if last_tool == "symbol":
            suggestions.append({
                "tool": "cap:code:graph",
                "confidence": 0.85,
                "rationale": "After symbol lookup, graph shows relationships",
                "category": "code-intelligence"
            })
            suggestions.append({
                "tool": "cap:code:context",
                "confidence": 0.8,
                "rationale": "Get context for the symbol",
                "category": "code-intelligence"
            })
        elif last_tool == "impact":
            suggestions.append({
                "tool": "cap:code:broken",
                "confidence": 0.8,
                "rationale": "After impact analysis, check for broken tests",
                "category": "code-intelligence"
            })
        elif last_tool == "search":
            suggestions.append({
                "tool": "cap:code:context",
                "confidence": 0.75,
                "rationale": "Get context for search results",
                "category": "code-intelligence"
            })
    
    # If no specific suggestions, use base route
    if not suggestions:
        tool_map = {
            "search": "cap:code:search",
            "symbol": "cap:code:symbol",
            "history": "cap:code:history",
            "health": "cap:code:broken",
            "architecture": "cap:code:map"
        }
        suggestions.append({
            "tool": tool_map.get(base_route["intent"], "cap:code:search"),
            "confidence": 0.7,
            "rationale": f"Based on detected intent: {base_route['intent']}",
            "category": "code-intelligence"
        })
    
    return {
        "primary": base_route,
        "suggestions": sorted(suggestions, key=lambda x: -x["confidence"]),
        "next_ops": _generate_next_ops(base_route, context)
    }

def _generate_next_ops(base_route, context):
    """Generate suggested follow-up operations using capability names."""
    ops = []
    intent = base_route["intent"]
    
    if intent == "symbol":
        ops.extend(["cap:code:graph(id='<symbol_id>', direction='both')", "cap:code:context(symbol='<symbol>')"])
    elif intent == "search":
        ops.extend(["cap:code:context(query='<query>')", "cap:code:graph(id='<top_symbol>')"])
    elif intent == "impact":
        ops.extend(["cap:code:broken()", "cap:code:context(query='<change>')"])
    elif intent == "architecture":
        ops.extend(["cap:code:summary(path='<subsystem>')", "cap:code:hotspots()"])
    elif intent == "health":
        ops.extend(["cap:code:audit(severity='critical')", "cap:code:impact()"])
    
    return ops[:5]
