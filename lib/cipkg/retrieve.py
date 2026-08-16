"""Hybrid retrieval v1.0: FTS ⊕ vectors → RRF → rerank; graph traversal;
budgeted context packs enriched with summaries and runtime signals."""
import json
import re, subprocess
from .base import repo_root, load_config, est_tokens
from .store import connect, get_meta
from .rerank import rerank
from . import vecstore

def _fts_query(q):
    toks = re.findall(r"[A-Za-z0-9_$]+", q)
    return " ".join(f'"{t}"' for t in toks[:8])

def _tok_query(q):
    from .base import tokenize
    return " ".join(f'"{t}"' for t in tokenize(q)[:8])

def lex_search(con, query, k=30):
    fq = _tok_query(query)
    if not fq:
        return []
    if get_meta(con, "tok_built") == "1":
        try:
            rows = con.execute(
                "SELECT c.id, c.path, c.symbol_id, c.start_line, c.end_line, substr(c.text,1,360) snip "
                "FROM chunks_fts2 f JOIN chunks c ON c.rowid=f.rowid "
                "WHERE chunks_fts2 MATCH ? ORDER BY rank LIMIT ?", (fq, k)).fetchall()
            if rows: return [dict(r) for r in rows]
        except Exception:
            pass
    if get_meta(con, "fts") != "1":
        rows = con.execute("SELECT id, path, symbol_id, start_line, end_line, "
                           "substr(text,1,360) snip FROM chunks WHERE text LIKE ? LIMIT ?",
                           (f"%{query}%", k)).fetchall()
        return [dict(r) for r in rows]
    try:
        rows = con.execute(
            "SELECT c.id, c.path, c.symbol_id, c.start_line, c.end_line, substr(c.text,1,360) snip "
            "FROM chunks_fts f JOIN chunks c ON c.rowid=f.rowid "
            "WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?", (fq, k)).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]

def vec_search(con, cfg, query, k=30):
    row = con.execute("SELECT model FROM vectors LIMIT 1").fetchone()
    if not row: return []
    from .embed import get_embedder
    try:
        emb = get_embedder(cfg)
    except Exception:
        return []
    if emb.name != row["model"]: return []
    qv = emb.embed([query])[0]
    scored = vecstore.knn(con, row["model"], qv, k,
                          cfg.get("vector", {}).get("backend", "sqlite"))
    out = []
    for score, cid in scored:
        c = con.execute("SELECT id, path, symbol_id, start_line, end_line, "
                        "substr(text,1,360) snip FROM chunks WHERE id=?", (cid,)).fetchone()
        if c:
            d = dict(c); d["score"] = round(float(score), 4); out.append(d)
    return out

def rrf(ranked_lists, k=60):
    scores, srcs = {}, {}
    for name, rows in zip(("fts", "vec"), ranked_lists):
        for rank, r in enumerate(rows):
            cid = r["id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            srcs.setdefault(cid, []).append(name)
    return [(cid, s, srcs[cid]) for cid, s in sorted(scores.items(), key=lambda kv: -kv[1])]

def _ensure_embedded(con, cfg):
    """Auto-embed chunks if none exist yet. Silent, one-time."""
    from . import indexer
    row = con.execute("SELECT COUNT(*) c FROM chunks c LEFT JOIN vectors v "
                      "ON v.id=c.id WHERE v.id IS NULL").fetchone()
    if row and row["c"] > 0:
        indexer.embed_pending(con, cfg, batch=64)

def _external_search(root, cfg, query, k):
    """Defer search to external tool (e.g., Vivim's code-index.ts)."""
    external_cfg = cfg.get("external_search", {})
    defer_to = external_cfg.get("defer_to")
    
    if not defer_to:
        return None
    
    args_template = external_cfg.get("args", ["{query}"])
    args = [arg.replace("{query}", query) for arg in args_template]
    
    try:
        result = subprocess.run(
            [defer_to] + args,
            capture_output=True,
            text=True,
            cwd=root,
            timeout=30
        )
        
        if result.returncode != 0:
            return None
        
        # Parse external tool output (assumes JSON format)
        external_results = json.loads(result.stdout)
        
        # Convert external results to CIP format
        items = []
        for ext_item in external_results[:k]:
            items.append({
                "chunk": ext_item.get("id", ""),
                "path": ext_item.get("path", ""),
                "lines": ext_item.get("lines", [0, 0]),
                "symbol": ext_item.get("symbol", ""),
                "score": ext_item.get("score", 0.5),
                "matched": ["external"],
                "snippet": ext_item.get("snippet", ""),
                "tier": ext_item.get("tier", "code")
            })
        
        return items
        
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        # Fall back to internal search if external fails
        return None

def search(root=None, query="", k=10):
    """Perform hybrid search combining lexical and semantic search.
    
    This function combines traditional keyword-based search with
    semantic vector search to provide the most relevant results.
    
    Args:
        root: Repository root path (default: auto-detect)
        query: Search query string
        k: Maximum number of results to return (default: 10)
    
    Returns:
        List of search results, each containing:
        - chunk: Chunk ID
        - path: File path
        - lines: [start_line, end_line]
        - symbol: Associated symbol ID (if any)
        - score: Relevance score (0.0 to 1.0)
        - matched: List of search backends that matched
        - snippet: Code text snippet
        - tier: File tier (code, test, config, etc.)
    
    Raises:
        ValueError: If query is empty
    
    Example:
        >>> results = search('/path/to/repo', 'authentication function')
        >>> for result in results:
        ...     print(f"{result['path']}:{result['lines']} - {result['score']:.2f}")
    
    Note:
        Semantic search requires an embedder to be configured.
        Falls back to lexical-only search if embedder is unavailable.
    """
    root = root or repo_root(); cfg = load_config(root); con = connect(root)
    
    # Check if external search is configured
    external_results = _external_search(root, cfg, query, k)
    if external_results is not None:
        # Layer CIP's audit/impact annotations on external results
        return rerank(query, external_results, con, cfg)[:k]
    
    # Standard internal search
    _ensure_embedded(con, cfg)
    lex = lex_search(con, query, int(cfg["retrieval"]["lexical_k"]))
    vec = vec_search(con, cfg, query, int(cfg["retrieval"]["vector_k"]))
    items = []
    for cid, score, srcs in rrf([lex, vec])[:max(k * 3, 30)]:
        c = con.execute("SELECT c.path, c.symbol_id, c.start_line, c.end_line, "
                        "substr(c.text,1,360) snip, f.tier "
                        "FROM chunks c LEFT JOIN files f ON f.path=c.path WHERE c.id=?", (cid,)).fetchone()
        if not c: continue
        items.append({"chunk": cid, "path": c["path"],
                      "lines": [c["start_line"], c["end_line"]], "symbol": c["symbol_id"],
                      "score": round(score, 5), "matched": srcs, "snippet": c["snip"],
                      "tier": c["tier"] or "code"})
    return rerank(query, items, con, cfg)[:k]

def edge_counts(con, sid):
    out = con.execute("SELECT kind, COUNT(*) c FROM edges WHERE src=? GROUP BY kind", (sid,)).fetchall()
    inc = con.execute("SELECT kind, COUNT(*) c FROM edges WHERE dst=? GROUP BY kind", (sid,)).fetchall()
    return {"out": {r["kind"]: r["c"] for r in out}, "in": {r["kind"]: r["c"] for r in inc}}

def find_symbol(root=None, name="", limit=20):
    """Find symbol definitions with relationship counts.
    
    Args:
        root: Repository root path (default: auto-detect)
        name: Symbol name to search for (supports partial matching)
        limit: Maximum number of results (default: 20)
    
    Returns:
        List of symbol dictionaries containing:
        - id: Symbol ID
        - name: Symbol name
        - kind: Symbol kind (function, class, method, etc.)
        - path: File path
        - start_line: Starting line number
        - end_line: Ending line number
        - signature: Symbol signature
        - counts: Dictionary with 'in' and 'out' edge counts
    
    Example:
        >>> symbols = find_symbol('/path/to/repo', 'hello_world')
        >>> for sym in symbols:
        ...     print(f"{sym['name']} ({sym['kind']}) at {sym['path']}")
    """
    root = root or repo_root(); con = connect(root)
    rows = con.execute("SELECT * FROM symbols WHERE name=? COLLATE NOCASE LIMIT ?",
                       (name, limit)).fetchall()
    if not rows:
        rows = con.execute("SELECT * FROM symbols WHERE name LIKE ? LIMIT ?",
                           (f"%{name}%", limit)).fetchall()
    out = []
    for r in rows:
        d = {k: r[k] for k in ("id", "name", "kind", "path", "start_line", "end_line", "signature")}
        d["counts"] = edge_counts(con, r["id"])
        out.append(d)
    return out

def graph(root=None, sid=None, direction="both", depth=1):
    """Traverse relationships around a symbol or file.
    
    Args:
        root: Repository root path (default: auto-detect)
        sid: Symbol ID to start traversal from (required)
        direction: Traversal direction - 'in', 'out', or 'both' (default: 'both')
        depth: Maximum traversal depth (1-3, default: 1)
    
    Returns:
        Dictionary containing:
        - root: Starting symbol ID
        - nodes: List of connected node IDs
        - edges: List of edge dictionaries with 'src', 'dst', 'kind'
    
    Example:
        >>> result = graph('/path/to/repo', 'symbol_123', direction='both', depth=2)
        >>> print(f"Found {len(result['nodes'])} connected nodes")
    """
    root = root or repo_root(); con = connect(root)
    if not sid: return {"error": "id required"}
    depth = max(1, min(int(depth), 3))
    seen, edges, frontier = {sid}, [], [sid]
    for _ in range(depth):
        nxt = []
        for n in frontier:
            if direction in ("out", "both"):
                for r in con.execute("SELECT src,dst,kind FROM edges WHERE src=?", (n,)):
                    edges.append(dict(r))
                    if r["dst"] not in seen and len(seen) < 200:
                        seen.add(r["dst"]); nxt.append(r["dst"])
            if direction in ("in", "both"):
                for r in con.execute("SELECT src,dst,kind FROM edges WHERE dst=?", (n,)):
                    edges.append(dict(r))
                    if r["src"] not in seen and len(seen) < 200:
                        seen.add(r["src"]); nxt.append(r["src"])
        frontier = nxt
    return {"root": sid, "nodes": sorted(seen), "edges": edges[:400]}

def context(root=None, query=None, symbol=None, budget=None):
    """Token-budgeted context pack: code + summary + relations + tests + failures.
    
    Args:
        root: Repository root path (default: auto-detect)
        query: Search query to find relevant context (optional)
        symbol: Symbol ID or name to get context for (optional)
        budget: Maximum token budget (default: from config)
    
    Returns:
        Dictionary containing:
        - seed: Starting symbol ID (if any)
        - budget_tokens: Maximum token budget
        - used_tokens: Tokens actually used
        - tokens_remaining: Tokens remaining in budget
        - budget_utilization: Percentage of budget used
        - sections: List of context sections with 'why', 'meta', 'text'
        - next_ops: Suggested follow-up operations
    
    Example:
        >>> ctx = context('/path/to/repo', symbol='hello_world')
        >>> print(f"Used {ctx['used_tokens']} of {ctx['budget_tokens']} tokens")
    """
    root = root or repo_root(); cfg = load_config(root); con = connect(root)
    budget = int(budget or cfg["retrieval"]["context_budget_tokens"])
    sections, next_ops, seed = [], [], None

    def add(prio, why, text, meta=None):
        sections.append({"prio": prio, "why": why, "text": text, "meta": meta or {}})

    sym_row = None
    if symbol:
        sym_row = con.execute("SELECT * FROM symbols WHERE id=?", (symbol,)).fetchone()
        if not sym_row:
            hits = find_symbol(root, symbol, limit=1)
            if hits:
                sym_row = con.execute("SELECT * FROM symbols WHERE id=?", (hits[0]["id"],)).fetchone()

    if sym_row:
        seed = sym_row["id"]
        add(0, "seed symbol source", sym_row["body"],
            {"path": sym_row["path"], "lines": [sym_row["start_line"], sym_row["end_line"]]})
        next_ops.append(f"graph(id='{seed}', direction='both')")
        next_ops.append(f"history(path='{sym_row['path']}')")

        try:  # file summary layer
            from .summarize import file_summary
            fs = file_summary(root, sym_row["path"])
            if fs.get("summary"):
                add(1, "file summary", fs["summary"], {"path": sym_row["path"]})
        except Exception:
            pass

        try:  # runtime signals for this file
            from .runtime_adapters import broken as _broken
            sigs = [s for s in _broken(root)["signals"] if s["path"] == sym_row["path"]][:3]
            if sigs:
                add(1, "recent failures in this file",
                    "\n".join(f'{s["kind"]}: {s["name"]}' for s in sigs),
                    {"path": sym_row["path"]})
        except Exception:
            pass

        tests = [r["dst"] for r in con.execute(
            "SELECT dst FROM edges WHERE src=? AND kind='tested_by'", (seed,))]
        for tf in tests[:2]:
            t = con.execute("SELECT text FROM chunks WHERE path=? ORDER BY start_line LIMIT 1",
                            (tf,)).fetchone()
            if t:
                add(1, f"tests for {sym_row['name']}", "\n".join(t["text"].splitlines()[:50]),
                    {"path": tf})
        for r in con.execute("SELECT s.signature, s.path FROM edges e JOIN symbols s ON s.id=e.dst "
                             "WHERE e.src=? AND e.kind IN ('calls','references') LIMIT 8", (seed,)):
            add(2, f"called by {sym_row['name']}", r["signature"], {"path": r["path"]})
        for r in con.execute("SELECT s.signature, s.path FROM edges e JOIN symbols s ON s.id=e.src "
                             "WHERE e.dst=? AND e.kind IN ('calls','references') LIMIT 8", (seed,)):
            add(2, f"caller of {sym_row['name']}", r["signature"], {"path": r["path"]})
        for r in con.execute("SELECT signature FROM symbols WHERE path=? AND id!=? LIMIT 12",
                             (sym_row["path"], seed)):
            add(3, "sibling symbol", r["signature"], {"path": sym_row["path"]})
        hdr = con.execute("SELECT text FROM chunks WHERE path=? ORDER BY start_line LIMIT 1",
                          (sym_row["path"],)).fetchone()
        if hdr:
            add(3, "file header / imports", "\n".join(hdr["text"].splitlines()[:25]),
                {"path": sym_row["path"]})
    else:
        for it in search(root, query or "", k=4):
            row = con.execute("SELECT text FROM chunks WHERE id=?", (it["chunk"],)).fetchone()
            if row:
                add(0 if not seed else 1, "search hit", row["text"],
                    {"path": it["path"], "lines": it["lines"], "score": it["score"]})
            if it.get("symbol") and not seed:
                seed = it["symbol"]
                next_ops.append(f"graph(id='{seed}', direction='both')")

    sections.sort(key=lambda s: s["prio"])
    packed, used = [], 0
    for s in sections:
        t = est_tokens(s["text"])
        if used + t > budget and packed: break
        packed.append(s); used += t
    return {"seed": seed, "budget_tokens": budget, "used_tokens": used,
            "tokens_remaining": budget - used,
            "budget_utilization": round(used / budget * 100, 1) if budget > 0 else 0,
            "sections": [{"why": s["why"], "meta": s["meta"], "text": s["text"]} for s in packed],
            "next_ops": next_ops[:6]}

def history(root=None, path="", n=8):
    """Get git history for a path.
    
    Args:
        root: Repository root path (default: auto-detect)
        path: File path to get history for (required)
        n: Number of commits to return (default: 8)
    
    Returns:
        Dictionary containing:
        - path: File path
        - commits: List of commit strings (hash, date, author, message)
        - note: Error message if git unavailable (optional)
    
    Example:
        >>> hist = history('/path/to/repo', 'src/main.py')
        >>> for commit in hist['commits']:
        ...     print(commit)
    """
    root = root or repo_root()
    try:
        out = subprocess.run(
            ["git", "log", "--pretty=format:%h %ad %an %s", "--date=short", "-n", str(n), "--", path],
            cwd=root, capture_output=True, text=True, timeout=10)
        return {"path": path, "commits": [l for l in out.stdout.splitlines() if l.strip()]}
    except Exception as e:
        return {"path": path, "commits": [], "note": f"git unavailable: {e}"}
