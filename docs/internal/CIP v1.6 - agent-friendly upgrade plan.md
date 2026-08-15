# CIP v1.6 — Agent-Friendly Upgrade Plan

## Vision: Make CIP the ultimate copilot for AI agents

Current CIP is excellent for human developers, but agents need deeper integration, streaming, predictive assistance, and richer context. This upgrade transforms CIP from a "tool" to an "agent partner."

---

## Priority 1: Agent-First Communication

### 1.1 MCP Streaming Responses
**Problem**: Long operations (sync, large context packs) block the agent with no progress feedback.

**Solution**: Add SSE (Server-Sent Events) streaming to MCP protocol.

```python
# lib/cipkg/server.py - streaming support
def mcp_stdio_streaming(root=None):
    """MCP with streaming for long operations."""
    root = root or repo_root()
    cfg = load_config(root)
    
    # Pre-warm embedder in background
    import threading
    from .embed import get_embedder
    threading.Thread(target=lambda: get_embedder(cfg, root), daemon=True).start()
    
    print("cip: MCP streaming server ready", file=sys.stderr)
    
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try: msg = json.loads(line)
        except Exception: continue
        
        mid, method = msg.get("id"), msg.get("method", "")
        
        if method == "initialize":
            resp = {"protocolVersion": "2024-11-05", 
                   "capabilities": {"tools": {}, "streaming": True},
                   "serverInfo": {"name": "cip", "version": "1.6.0"}}
        elif method == "tools/call":
            p = msg.get("params", {})
            tool_name = p.get("name", "")
            
            # Stream long operations
            if tool_name in ("sync", "context", "search"):
                yield from _stream_tool_call(root, cfg, tool_name, p.get("arguments", {}), mid)
            else:
                env = call_tool(root, cfg, tool_name, p.get("arguments", {}))
                resp = {"content": [{"type": "text", "text": json.dumps(env, default=str)}]}
        elif method.startswith("notifications/"):
            continue
        else:
            resp = {"error": {"code": -32601, "message": "unknown method"}}
        
        if mid is not None and not streaming:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": resp}) + "\n")
            sys.stdout.flush()

def _stream_tool_call(root, cfg, name, args, mid):
    """Stream progress for long operations."""
    if name == "sync":
        from . import indexer
        def progress(phase, cur, total):
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0", "method": "progress", 
                "params": {"phase": phase, "current": cur, "total": total}
            }) + "\n")
            sys.stdout.flush()
        
        stats = indexer.sync(root, progress=progress)
        yield {"content": [{"type": "text", "text": json.dumps(stats, default=str)}]}
    
    elif name == "context":
        from . import retrieve
        pack = retrieve.context(root, args.get("query"), args.get("symbol"), args.get("budget"))
        # Stream sections as they're gathered
        for section in pack.get("sections", []):
            yield {"content": [{"type": "text", "text": f"## {section['why']}\n{section['text'][:500]}..."}]}
```

### 1.2 Intent-Aware Tool Selection
**Problem**: Agents don't know which tool to use for their intent.

**Solution**: Add `cip route --agent` that returns tool recommendations with confidence scores.

```python
# lib/cipkg/router.py - enhanced for agents
def route_for_agent(query, context=None):
    """Return ranked tool suggestions with confidence and rationale."""
    from . import router
    
    base_route = router.route(query)
    
    # Enhance with context-aware suggestions
    suggestions = []
    
    if base_route["intent"] == "search":
        suggestions.append({
            "tool": "search",
            "confidence": 0.95,
            "rationale": "Query asks for code matching keywords/semantics"
        })
        if "how" in query.lower() or "flow" in query.lower():
            suggestions.append({
                "tool": "context",
                "confidence": 0.8,
                "rationale": "Query asks about architecture/flow - context pack better"
            })
    
    elif base_route["intent"] == "impact":
        suggestions.append({
            "tool": "impact",
            "confidence": 0.9,
            "rationale": "Query asks about blast radius/dependencies"
        })
        suggestions.append({
            "tool": "graph",
            "confidence": 0.7,
            "rationale": "Graph traversal provides visual dependency map"
        })
    
    # Add context from previous calls
    if context:
        if context.get("last_tool") == "symbol":
            suggestions.append({
                "tool": "graph",
                "confidence": 0.85,
                "rationale": "After symbol lookup, graph shows relationships"
            })
    
    return {
        "primary": base_route,
        "suggestions": sorted(suggestions, key=lambda x: -x["confidence"]),
        "next_ops": _generate_next_ops(base_route, context)
    }
```

---

## Priority 2: Gap-Fillers for Pressure Test Scenarios

### 2.1 Test Coverage Analysis (Scenarios 63, 228, 229)
```python
# lib/cipkg/gapfill/coverage.py
def analyze_coverage(root):
    """Analyze test coverage using ingested signals."""
    con = connect(root)
    
    # Get all symbols
    symbols = list(con.execute("SELECT id, name, path FROM symbols").fetchall())
    
    # Get tested_by edges
    tested = {r["src"] for r in con.execute("SELECT src FROM edges WHERE kind='tested_by'")}
    
    # Calculate coverage
    coverage = {
        "total_symbols": len(symbols),
        "tested_symbols": len(tested),
        "coverage_pct": len(tested) / len(symbols) * 100 if symbols else 0,
        "untested": []
    }
    
    for sym in symbols:
        if sym["id"] not in tested:
            # Check if it's load-bearing (many dependents)
            deps = con.execute("SELECT COUNT(*) c FROM edges WHERE dst=? AND kind='calls'", 
                             (sym["id"],)).fetchone()["c"]
            if deps > 3:
                coverage["untested"].append({
                    "symbol": sym["name"],
                    "path": sym["path"],
                    "dependents": deps,
                    "severity": "high" if deps > 10 else "medium"
                })
    
    return coverage
```

### 2.2 Dead Code Detection (Scenario 71)
```python
# lib/cipkg/gapfill/dead.py
def find_dead_code(root):
    """Find symbols with no incoming calls/references."""
    con = connect(root)
    
    dead = []
    for sym in con.execute("SELECT id, name, path, kind FROM symbols"):
        # Skip exports, tests, and entry points
        if sym["kind"] in ("test", "module"):
            continue
        
        # Check for incoming edges
        incoming = con.execute(
            "SELECT COUNT(*) c FROM edges WHERE dst=? AND kind IN ('calls', 'references')",
            (sym["id"],)
        ).fetchone()["c"]
        
        # Check if exported
        exported = con.execute(
            "SELECT COUNT(*) c FROM edges WHERE src=? AND dst=? AND kind='exports'",
            (sym["path"], sym["id"])
        ).fetchone()["c"]
        
        if incoming == 0 and exported == 0:
            dead.append({
                "symbol": sym["name"],
                "path": sym["path"],
                "kind": sym["kind"],
                "confidence": "high"
            })
    
    return {"dead_symbols": dead}
```

### 2.3 API Contract Extraction (Scenarios 146-160)
```python
# lib/cipkg/gapfill/api.py
def extract_api_contracts(root):
    """Extract API contracts from route handlers."""
    con = connect(root)
    
    contracts = []
    for route in con.execute("SELECT path FROM files WHERE path LIKE '%route%'"):
        # Parse route file for:
        # - HTTP methods (GET, POST, etc.)
        # - Request schemas (zod, yup, validation)
        # - Response schemas
        # - Error handling patterns
        # - Middleware chain
        
        # This would use tree-sitter to parse the route handler
        # For now, placeholder structure:
        contracts.append({
            "path": route["path"],
            "methods": ["GET", "POST"],  # extracted
            "request_schema": "zod.object({...})",  # extracted
            "response_schema": "UserResponse",  # extracted
            "auth_required": True,  # inferred from middleware
            "rate_limit": "100 req/min"  # inferred
        })
    
    return {"api_contracts": contracts}
```

### 2.4 Migration Inventory (Scenarios 137, 251-258)
```python
# lib/cipkg/gapfill/migrations.py
def inventory_migrations(root):
    """Find and analyze database migration files."""
    con = connect(root)
    
    migrations = []
    for file in con.execute("SELECT path FROM files WHERE path LIKE '%migration%' OR path LIKE '%migrate%'"):
        # Parse migration files for:
        # - Migration number/timestamp
        # - Up/down SQL
        # - Tables affected
        # - Breaking changes
        
        migrations.append({
            "file": file["path"],
            "version": "20240101_001",  # extracted
            "tables": ["users", "posts"],  # extracted
            "breaking": False,  # inferred
            "rollback_available": True  # checked
        })
    
    return {"migrations": sorted(migrations, key=lambda x: x["version"])}
```

---

## Priority 3: Predictive Context Suggestions

### 3.1 Context Pre-Fetching
**Problem**: Agents don't know what context they'll need next.

**Solution**: Predict and pre-fetch likely context based on current operation.

```python
# lib/cipkg/predict.py
def predict_next_context(root, current_operation, current_symbol=None):
    """Predict what context the agent will need next."""
    from .store import connect
    con = connect(root)
    
    predictions = []
    
    if current_operation == "symbol":
        # After symbol lookup, likely need:
        # - Graph of relationships
        # - Context pack for the symbol
        # - Files that use this symbol
        predictions.extend([
            {"tool": "graph", "args": {"id": current_symbol}, "confidence": 0.9},
            {"tool": "context", "args": {"symbol": current_symbol}, "confidence": 0.85},
            {"tool": "search", "args": {"query": f"uses of {current_symbol}"}, "confidence": 0.7}
        ])
    
    elif current_operation == "impact":
        # After impact analysis, likely need:
        # - Test coverage for affected files
        # - Broken tests in the area
        predictions.extend([
            {"tool": "broken", "args": {}, "confidence": 0.8},
            {"tool": "coverage", "args": {}, "confidence": 0.6}
        ])
    
    elif current_operation == "search":
        # After search, likely need:
        # - Context for top results
        # - Graph for top symbols
        predictions.extend([
            {"tool": "context", "args": {"query": "same as search"}, "confidence": 0.75}
        ])
    
    return {"predictions": predictions[:5]}
```

### 3.2 Smart Context Budgeting
**Problem**: Fixed budget wastes tokens on irrelevant context.

**Solution**: Dynamically allocate budget based on query complexity and result relevance.

```python
# lib/cipkg/retrieve.py - enhanced context
def context_adaptive(root, query=None, symbol=None, base_budget=6000):
    """Adaptive context budgeting based on query complexity."""
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
                "text": sym["body"],
                "relevance": 1.0
            })
    
    # Get relationships
    graph = graph(root, symbol, "both", depth=1)
    for node in graph.get("nodes", [])[:5]:
        # Add with decreasing relevance
        sections.append({
            "why": "related_symbol",
            "meta": {"id": node},
            "text": _get_symbol_snippet(con, node),
            "relevance": 0.7
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
        "budget_total": budget,
        "complexity": complexity
    }
```

---

## Priority 4: Cross-Repo Federation

### 4.1 Multi-Repo Search
**Problem**: Agents need to search across related repositories (monorepo, microservices).

**Solution**: Federation layer that searches multiple CIP indexes.

```python
# lib/cipkg/federation.py
class FederatedSearch:
    """Search across multiple CIP-indexed repositories."""
    
    def __init__(self, repo_roots):
        self.roots = repo_roots
    
    def search(self, query, k=10):
        """Search across all repos, merge results with repo source."""
        all_results = []
        
        for root in self.roots:
            try:
                results = retrieve.search(root, query, k=k)
                for r in results:
                    r["repo"] = os.path.basename(root)
                    all_results.append(r)
            except Exception:
                continue
        
        # Re-rank across repos
        scored = [(r, r["score"]) for r in all_results]
        scored.sort(key=lambda x: -x[1])
        
        return {"results": [r for r, _ in scored[:k]], "repos_searched": len(self.roots)}
    
    def symbol(self, name):
        """Find symbol across all repos."""
        all_symbols = []
        
        for root in self.roots:
            try:
                symbols = retrieve.find_symbol(root, name)
                for s in symbols:
                    s["repo"] = os.path.basename(root)
                    all_symbols.append(s)
            except Exception:
                continue
        
        return {"symbols": all_symbols}
```

---

## Priority 5: Learned Reranker

### 5.1 ML-Based Reranking
**Problem**: Current reranking is rule-based, doesn't learn from agent preferences.

**Solution**: Train a lightweight reranker on agent interaction logs.

```python
# lib/cipkg/rerank_learned.py
class LearnedReranker:
    """ML-based reranker using interaction feedback."""
    
    def __init__(self, root):
        self.root = root
        self.model = None
        self._load_or_train()
    
    def _load_or_train(self):
        """Load trained model or train from interaction logs."""
        model_path = os.path.join(data_dir(root), "reranker.pkl")
        
        if os.path.exists(model_path):
            import joblib
            self.model = joblib.load(model_path)
        else:
            self._train_from_logs()
    
    def _train_from_logs(self):
        """Train from agent interaction logs."""
        # Extract features from logs:
        # - Query type
        # - Result position clicked
        # - Time spent on result
        # - Follow-up actions
        
        # Train a simple gradient boosting model
        from sklearn.ensemble import GradientBoostingRegressor
        
        X, y = self._extract_training_data()
        self.model = GradientBoostingRegressor(n_estimators=50)
        self.model.fit(X, y)
        
        # Save
        import joblib
        joblib.dump(self.model, os.path.join(data_dir(root), "reranker.pkl"))
    
    def rerank(self, query, results):
        """Rerank results using learned model."""
        if not self.model:
            return results
        
        features = [self._extract_features(query, r) for r in results]
        scores = self.model.predict(features)
        
        # Combine with original scores
        for r, score in zip(results, scores):
            r["learned_score"] = score
            r["final_score"] = 0.7 * r["score"] + 0.3 * score
        
        results.sort(key=lambda x: -x["final_score"])
        return results
```

---

## Priority 6: Symbol-Level Git Blame

### 6.1 Per-Symbol Authorship
**Problem**: Current git blame is file-level, agents need symbol-level authorship.

**Solution**: Parse git blame output and map to symbol ranges.

```python
# lib/cipkg/git_blame_symbol.py
def symbol_blame(root, symbol_id):
    """Get git blame information for a specific symbol."""
    from .store import connect
    con = connect(root)
    
    # Get symbol location
    sym = con.execute("SELECT path, start_line, end_line FROM symbols WHERE id=?", 
                     (symbol_id,)).fetchone()
    if not sym:
        return {"error": "symbol not found"}
    
    # Run git blame for the range
    import subprocess
    result = subprocess.run(
        ["git", "blame", "-L", f"{sym['start_line']},{sym['end_line']}", 
         "--line-porcelain", sym["path"]],
        cwd=root, capture_output=True, text=True
    )
    
    # Parse blame output
    blame_data = _parse_blame_output(result.stdout)
    
    # Aggregate by author
    author_stats = {}
    for line_data in blame_data:
        author = line_data.get("author", "Unknown")
        author_stats[author] = author_stats.get(author, 0) + 1
    
    return {
        "symbol_id": symbol_id,
        "path": sym["path"],
        "lines": [sym["start_line"], sym["end_line"]],
        "author_stats": author_stats,
        "primary_author": max(author_stats, key=author_stats.get) if author_stats else None,
        "last_modified": blame_data[-1].get("author-time") if blame_data else None
    }
```

---

## Implementation Priority

**Phase 1** (Immediate - 1 week):
1. MCP streaming responses
2. Intent-aware tool selection
3. Test coverage analysis
4. Dead code detection

**Phase 2** (Short-term - 2 weeks):
5. API contract extraction
6. Migration inventory
7. Predictive context suggestions
8. Adaptive context budgeting

**Phase 3** (Medium-term - 1 month):
9. Cross-repo federation
10. Learned reranker
11. Symbol-level git blame
12. Component tree visualization

---

## Expected Agent Experience

**Before**:
```
Agent: "What breaks if I change this function?"
Tool: cip impact <function>
Result: Blast radius analysis
Agent: "What tests cover it?"
Tool: cip graph <function> (manual)
Result: tested_by edges
```

**After**:
```
Agent: "What breaks if I change this function?"
CIP: [Streaming] Analyzing impact...
      [Progress] Found 12 dependents
      [Progress] Checking test coverage...
      Result: Impact analysis + test coverage + suggested next actions
      [Auto-suggested] "Run: cip broken to check failing tests"
```

This transforms CIP from a passive tool to an active agent partner that anticipates needs, streams progress, and provides richer context.
