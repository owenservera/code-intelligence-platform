"""Feature-based reranker: identifier match, path overlap, tested symbols, recency.
Optional cross-encoder slot documented in SPEC extension points."""
import re, time
from .base import tokenize

def _recent_paths(con, days=30):
    cutoff = time.time() - days * 86400
    try:
        rows = con.execute("SELECT DISTINCT cf.path FROM commit_files cf "
                           "JOIN commits c ON c.sha=cf.sha WHERE c.ts>=?", (cutoff,)).fetchall()
        return {r["path"] for r in rows}
    except Exception:
        return set()

def rerank(query, items, con, cfg):
    if not items or not cfg.get("rerank", {}).get("enabled", True):
        return items
    qtoks = set(tokenize(query))
    idents = set(re.findall(r"[A-Za-z_$][A-Za-z0-9_$]{3,}", query))
    recent = _recent_paths(con)
    for it in items:
        s = it.get("score", 0.0)
        path = it.get("path", "")
        if idents and any(i.lower() in path.lower() for i in idents):
            s += 0.5
        overlap = len(qtoks & set(tokenize(path)))
        if overlap:
            s += min(0.3, 0.1 * overlap)
        if it.get("symbol"):
            c = con.execute("SELECT COUNT(*) c FROM edges WHERE src=? AND kind='tested_by'",
                            (it["symbol"],)).fetchone()["c"]
            if c: s += 0.1
        if path in recent:
            s += 0.1
        it["score"] = round(s, 5)
    items.sort(key=lambda x: -x["score"])
    return items
