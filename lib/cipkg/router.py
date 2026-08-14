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
