"""Next.js mapping: App Router + Pages Router routes, HTTP methods, client boundaries.
Powers HIDDEN-ROUTE, NEXT-* rules and the `routes` tool."""
import os, re
from .common import ensure

METHOD_RE = re.compile(r"export\s+(?:async\s+)?(?:function|const)\s+(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b")
CLIENT_RE = re.compile(r"""^\s*['"]use client['"]""")

def _read(root, rel):
    try:
        return open(os.path.join(root, rel), encoding="utf-8", errors="replace").read()
    except OSError:
        return ""

def _app_route_path(rel):
    parts = []
    for p in os.path.dirname(rel).split("/"):
        if p == "app" or (p.startswith("(") and p.endswith(")")):
            continue
        parts.append(p)
    return "/" + "/".join(parts) if parts else "/"

def index_routes(con, root):
    ensure(con)
    con.execute("DELETE FROM routes")
    n = 0
    rows = con.execute("SELECT path FROM files WHERE language IN ('typescript','javascript')").fetchall()
    for r in rows:
        rel = r["path"]
        base = os.path.basename(rel)
        if base in ("route.ts", "route.js"):
            kind = "api"
        elif base in ("page.tsx", "page.jsx", "page.js"):
            kind = "page"
        elif base in ("layout.tsx", "layout.jsx"):
            kind = "layout"
        elif "/pages/api/" in "/" + rel:
            kind = "api"
        else:
            continue
        src = _read(root, rel)
        methods = sorted(set(METHOD_RE.findall(src))) if kind == "api" else []
        client = 1 if CLIENT_RE.match(src) else 0
        if rel.split("/")[0] == "app":
            path = _app_route_path(rel)
        else:
            p = rel.split("pages/", 1)[1]
            p = os.path.splitext(p)[0]
            if p.endswith("/index"):
                p = p[:-6]
            path = "/" + p
        con.execute("INSERT OR REPLACE INTO routes(path,file,kind,methods,client) "
                    "VALUES(?,?,?,?,?)", (path, rel, kind, ",".join(methods), client))
        n += 1
    con.commit()
    return {"routes": n}

def route_referenced(con, root, path):
    """Heuristic: is this route path string referenced anywhere in indexed code?"""
    probe = path.replace("[", "").replace("]", "").replace("%", "").replace("_", "").rstrip("/")
    if len(probe) < 4:
        return True
    row = con.execute("SELECT 1 FROM chunks WHERE text LIKE ? LIMIT 1",
                      (f"%{probe}%",)).fetchone()
    return row is not None

def list_routes(root=None):
    from ..base import repo_root
    from ..store import connect
    root = root or repo_root()
    con = connect(root)
    ensure(con)
    if con.execute("SELECT COUNT(*) c FROM routes").fetchone()["c"] == 0:
        index_routes(con, root)
    out = []
    for r in con.execute("SELECT path, file, kind, methods, client FROM routes ORDER BY path"):
        d = dict(r)
        d["referenced"] = route_referenced(con, root, r["path"])
        out.append(d)
    return out
