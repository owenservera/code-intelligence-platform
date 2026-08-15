"""Prisma schema parsing + usage analysis: models, call sites, where-fields.
Powers HIDDEN-MODEL, DB-MISSING-INDEX and the `models` tool."""
import os, re
from .common import ensure

MODEL_RE = re.compile(r"^model\s+(\w+)\s*\{", re.M)
USAGE_RE = re.compile(
    r"prisma\.(\w+)\.(findMany|findFirst|findUnique|createMany|create|updateMany|update|"
    r"deleteMany|delete|upsert|count|aggregate|groupBy)\s*\(")
WHERE_RE = re.compile(
    r"prisma\.(\w+)\.(?:findFirst|findMany|findUnique|count|update|updateMany|delete|deleteMany)"
    r"\s*\(\s*\{[^{}]*?where:\s*\{([\s\S]{0,400}?)\}")
KEY_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*:", re.M)
LOGICAL = {"AND", "OR", "NOT"}

def find_schema(root):
    for c in ("prisma/schema.prisma", "schema.prisma"):
        if os.path.exists(os.path.join(root, c)):
            return c
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        if rel.count("/") > 1:
            dirnames[:] = []
            continue
        if "schema.prisma" in filenames:
            return (rel + "/" if rel != "." else "") + "schema.prisma"
    return None

def parse_schema(text):
    models = {}
    for m in MODEL_RE.finditer(text):
        name = m.group(1)
        end = text.find("}", m.end())
        block = text[m.end():end] if end != -1 else ""
        fields, uniques, indexes = [], set(), []
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("@@index"):
                cols = re.findall(r"\[([^\]]+)\]", line)
                if cols:
                    indexes.append([c.strip() for c in cols[0].split(",")])
                continue
            if not line or line.startswith(("//", "@@")):
                continue
            fm = re.match(r"^(\w+)\s+([\w\[\]?]+)", line)
            if not fm:
                continue
            fname, ftype = fm.groups()
            fields.append({"name": fname, "type": ftype,
                           "id": "@id" in line, "unique": "@unique" in line})
            if "@id" in line or "@unique" in line:
                uniques.add(fname)
        models[name] = {"fields": fields, "uniques": uniques, "indexes": indexes}
    return models

def _read(root, rel):
    try:
        return open(os.path.join(root, rel), encoding="utf-8", errors="replace").read()
    except OSError:
        return ""

def index_stack(con, root):
    """Persist models + prisma call-site usage. Returns stats."""
    ensure(con)
    rel = find_schema(root)
    models = parse_schema(_read(root, rel)) if rel else {}
    con.execute("DELETE FROM models")
    for name, m in models.items():
        indexed = m["indexes"] + [[u] for u in m["uniques"]]
        con.execute("INSERT INTO models(name,fields,indexes,source) VALUES(?,?,?,?)",
                    (name, str([f["name"] for f in m["fields"]]), str(indexed), rel or ""))
    con.execute("DELETE FROM model_usage")
    usage = 0
    rows = con.execute("SELECT path FROM files WHERE language IN ('typescript','javascript')").fetchall()
    for r in rows:
        src = _read(root, r["path"])
        for m in USAGE_RE.finditer(src):
            model, op = m.group(1), m.group(2)
            if model not in models:
                continue
            ln = src.count("\n", 0, m.start()) + 1
            sym = con.execute(
                "SELECT id FROM symbols WHERE path=? AND start_line<=? AND end_line>=? "
                "ORDER BY (end_line-start_line) LIMIT 1", (r["path"], ln, ln)).fetchone()
            con.execute("INSERT OR IGNORE INTO model_usage(model,operation,symbol_id,path) "
                        "VALUES(?,?,?,?)",
                        (model, op, sym["id"] if sym else "", r["path"]))
            usage += 1
    con.commit()
    return {"models": len(models), "usage_sites": usage, "schema": rel}

def where_fields(con, root):
    """model → set of field names used inside where: clauses."""
    out = {}
    rows = con.execute("SELECT path FROM files WHERE language IN ('typescript','javascript')").fetchall()
    for r in rows:
        src = _read(root, r["path"])
        for m in WHERE_RE.finditer(src):
            model, block = m.group(1), m.group(2)
            keys = {k for k in KEY_RE.findall(block)} - LOGICAL
            if keys:
                out.setdefault(model, set()).update(keys)
    return out

def _resolve_store_contract(src, line_start, line_end):
    """Attempt to resolve store contract method calls to underlying Prisma operations.
    
    For repos that wrap Prisma behind store contracts (like Vivim's src/storage/ layer),
    this maps contract method names to the Prisma operations they wrap.
    """
    # Store contract patterns (repo-agnostic, matches common patterns)
    contract_patterns = [
        (r'(\w+)\.findMany\s*\(', 'findMany'),
        (r'(\w+)\.findFirst\s*\(', 'findFirst'),
        (r'(\w+)\.findUnique\s*\(', 'findUnique'),
        (r'(\w+)\.create\s*\(', 'create'),
        (r'(\w+)\.update\s*\(', 'update'),
        (r'(\w+)\.delete\s*\(', 'delete'),
        (r'(\w+)\.upsert\s*\(', 'upsert'),
    ]
    
    lines = src.splitlines()
    resolved = []
    
    for i in range(line_start - 1, min(line_end, len(lines))):
        line = lines[i]
        for pattern, operation in contract_patterns:
            match = re.search(pattern, line)
            if match:
                resolved.append({
                    'method': match.group(1),
                    'operation': operation,
                    'line': i + 1
                })
    
    return resolved

def index_stack_with_store_contracts(con, root):
    """Extended stack indexing that resolves store contract patterns.
    
    This adds a second pass for repos that wrap Prisma behind architectural layers.
    It walks storage directories and resolves contract methods to underlying Prisma calls.
    """
    ensure(con)
    rel = find_schema(root)
    models = parse_schema(_read(root, rel)) if rel else {}
    
    # Standard indexing
    con.execute("DELETE FROM models")
    for name, m in models.items():
        indexed = m["indexes"] + [[u] for u in m["uniques"]]
        con.execute("INSERT INTO models(name,fields,indexes,source) VALUES(?,?,?,?)",
                    (name, str([f["name"] for f in m["fields"]]), str(indexed), rel or ""))
    
    con.execute("DELETE FROM model_usage")
    usage = 0
    rows = con.execute("SELECT path FROM files WHERE language IN ('typescript','javascript')").fetchall()
    
    # First pass: direct Prisma calls
    for r in rows:
        src = _read(root, r["path"])
        for m in USAGE_RE.finditer(src):
            model, op = m.group(1), m.group(2)
            if model not in models:
                continue
            ln = src.count("\n", 0, m.start()) + 1
            sym = con.execute(
                "SELECT id FROM symbols WHERE path=? AND start_line<=? AND end_line>=? "
                "ORDER BY (end_line-start_line) LIMIT 1", (r["path"], ln, ln)).fetchone()
            con.execute("INSERT OR IGNORE INTO model_usage(model,operation,symbol_id,path) "
                        "VALUES(?,?,?,?)",
                        (model, op, sym["id"] if sym else "", r["path"]))
            usage += 1
    
    # Second pass: store contract resolution for storage directories
    storage_dirs = ["src/storage", "storage", "lib/storage", "app/storage"]
    for storage_dir in storage_dirs:
        storage_path = os.path.join(root, storage_dir)
        if not os.path.isdir(storage_path):
            continue
            
        for dirpath, dirnames, filenames in os.walk(storage_path):
            for filename in filenames:
                if not filename.endswith((".ts", ".js", ".tsx", ".jsx")):
                    continue
                    
                file_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(file_path, root).replace(os.sep, "/")
                src = _read(root, rel_path)
                
                # Look for store contract patterns that might wrap Prisma
                # Pattern: method calls that could be store contracts
                for m in re.finditer(r'(\w+)\.(findMany|findFirst|findUnique|create|update|delete|upsert|createMany|updateMany|deleteMany|count|aggregate|groupBy)\s*\(', src):
                    method_name = m.group(1)
                    operation = m.group(2)
                    
                    # Skip if this is a direct prisma call (already handled)
                    if method_name == "prisma":
                        continue
                        
                    # Try to infer the model from context or patterns
                    # This is heuristic - store contracts often have method names like "findUsers", "createPost"
                    model_guess = None
                    for model_name in models.keys():
                        if model_name.lower() in method_name.lower():
                            model_guess = model_name
                            break
                    
                    if model_guess:
                        ln = src.count("\n", 0, m.start()) + 1
                        sym = con.execute(
                            "SELECT id FROM symbols WHERE path=? AND start_line<=? AND end_line>=? "
                            "ORDER BY (end_line-start_line) LIMIT 1", (rel_path, ln, ln)).fetchone()
                        
                        con.execute("INSERT OR IGNORE INTO model_usage(model,operation,symbol_id,path) "
                                    "VALUES(?,?,?,?)",
                                    (model_guess, operation, sym["id"] if sym else "", rel_path))
                        usage += 1
    
    con.commit()
    return {"models": len(models), "usage_sites": usage, "schema": rel, "store_contract_resolved": True}

def models_report(root=None):
    from ..base import repo_root
    from ..store import connect
    root = root or repo_root()
    con = connect(root)
    ensure(con)
    if con.execute("SELECT COUNT(*) c FROM models").fetchone()["c"] == 0:
        index_stack(con, root)
    out = []
    for m in con.execute("SELECT name FROM models ORDER BY name"):
        name = m["name"]
        ops = con.execute("SELECT operation, COUNT(*) c FROM model_usage WHERE model=? "
                          "GROUP BY operation", (name,)).fetchall()
        users = con.execute("SELECT COUNT(DISTINCT path) c FROM model_usage WHERE model=?",
                            (name,)).fetchone()["c"]
        out.append({"model": name,
                    "total_usage": sum(r["c"] for r in ops),
                    "operations": {r["operation"]: r["c"] for r in ops},
                    "files_using": users, "orphan": users == 0})
    return {"models": out}
