# CIP v1.1 — **STACK PACK**: TS / Next.js / Prisma / SQLite DevOps Intelligence

Designed from the seat of an agent running a massive Next.js + Prisma + SQLite codebase. What that agent actually needs, daily:

1. **What is broken right now** — without reading 10k files
2. **What will break if I touch X** — blast radius before the change
3. **What is hiding** — dead exports, never-called API routes, orphaned Prisma models (buried features)
4. **What is wrong by construction** — N+1 queries, missing indexes, client/server leaks, hardcoded secrets
5. **What to fix first** — ranked quick wins, not a wall of lint noise
6. **A gate** — one command that says "safe to merge" or not

This pack adds a **24-rule semantic audit engine**, **Prisma schema↔code cross-analysis**, **Next.js route/boundary mapping**, **blast-radius impact analysis**, **unified findings store**, **quality gate**, and Markdown refactoring reports — all on top of the existing CIP graph, zero new hard dependencies.

---

## 1. Docs

### 1.1 `STACKPACK.md` (NEW)

````markdown
# CIP v1.1 — STACK PACK (TypeScript / Next.js / Prisma / SQLite)

A dev-cycle intelligence layer: it audits the codebase like a staff engineer,
finds hidden features, predicts blast radius, and gates merges.

## New capabilities

| Capability | Command / Tool | What it answers |
|---|---|---|
| Auto-issue detection | `cip audit` / `audit` | 24 semantic rules → findings store |
| Refactor triage | `cip refactors` / `refactors` | quick wins ranked by severity ÷ effort |
| Findings query | `cip findings --severity high` / `findings` | slice by rule/severity/path |
| Blast radius | `cip impact <file\|symbol>` / `impact` | dependents, routes, tests, risk level |
| PR risk | `cip impact --ref origin/main` | union impact of the whole diff |
| Route inventory | `cip routes` / `routes` | every API/page route + called-or-orphan |
| DB model intel | `cip models` / `models` | Prisma usage per model, orphans |
| Quality gate | `cip gate` | exit 1 on critical findings / broken signals |
| Reports | `cip audit --md REPORT.md` | human/PR-ready markdown |
| Lint unification | `cip ingest --kind eslint --file r.json` | eslint → same findings stream |

## Rule catalog

| ID | Sev | Detects |
|---|---|---|
| SEC-HARDCODED-SECRET | critical | live keys, conn strings w/ password, private keys |
| SEC-SQL-RAW | high | `$queryRawUnsafe` / `$executeRawUnsafe` |
| ENV-UNDEFINED | high | `process.env.X` used but in no `.env*` |
| NEXT-CLIENT-LEAK | high | `"use client"` file importing prisma/fs/server modules |
| DB-N1 | high | awaited prisma query inside loop/map/forEach |
| DB-NO-AWAIT | high | prisma call with no await/return/assignment |
| DB-DESTRUCTIVE-MIGRATION | high | DROP TABLE / DROP COLUMN in migrations |
| DB-MISSING-INDEX | medium | fields used in `where:` with no @id/@unique/@@index (SQLite full scan) |
| DB-SCHEMA-DRIFT | medium | schema.prisma newer than last migration |
| HIDDEN-ROUTE | medium | API route never referenced anywhere |
| HIDDEN-MODEL | medium | Prisma model with zero code usage |
| NEXT-ROUTE-NO-ERROR | medium | API route handler without try/catch |
| NEXT-ACTION-NO-VALIDATE | medium | `"use server"` fn with no schema validation |
| QA-CIRCULAR | medium | circular import chains |
| QA-GOD-MODULE | medium | huge high-fan-in files |
| QA-UNTESTED-HOT | medium | heavily-used symbols with no tests |
| ARCH-LAYER-VIOLATION | medium | lib layer importing UI layer |
| HIDDEN-EXPORT | low | exported TS symbols never referenced (hidden features) |
| ARCH-ORPHAN-FILE | low | files nothing imports |
| ENV-UNREAD | low | `.env` vars never read |
| QA-DUP | low | identical function bodies in multiple places |
| QA-ANY / QA-TSIGNORE / QA-CONSOLE | low | hygiene thresholds exceeded |

## Dev-cycle workflows

**Morning triage (2 commands):**
```bash
cip audit && cip refactors
```

**Before opening a PR:**
```bash
cip impact --ref origin/main     # what does my diff touch, transitively?
cip gate                         # hard gate: criticals + broken signals
```

**Hidden-feature hunt:**
```bash
cip findings --rule HIDDEN-ROUTE
cip findings --rule HIDDEN-EXPORT
cip models                        # orphan models = buried backend features
```

**DB health (SQLite-specific):**
```bash
cip models                        # usage per model
cip findings --rule DB-MISSING-INDEX
```

**CI (GitHub Actions):**
```yaml
- run: |
    ./install.sh .
    .cip/bin/cip upgrade
    npx vitest run --reporter=json > vt.json || true
    .cip/bin/cip ingest --kind vitest --file vt.json
    .cip/bin/cip gate
```

Findings are **idempotent** (stable IDs) and track status: `open → fixed` happens
automatically when the condition disappears. `dismiss` by deleting the rule from
config: `[audit] ignore_rules = ["QA-CONSOLE"]`.
````

### 1.2 `ontology.json` (REPLACE — v1.1)

```json
{
  "protocol": "cip",
  "version": "1.1.0",
  "id_grammar": "<language>://<path>#<Qualified.name>",
  "chunk_grammar": "<path>#L<start>-L<end>",
  "entities": {
    "File":    { "key": "path" },
    "Symbol":  { "key": "id", "kinds": ["class","function","method","interface","type","const","module","test"] },
    "Chunk":   { "key": "id" },
    "Commit":  { "key": "sha" },
    "Signal":  { "key": "id", "kinds": ["test_pass","test_fail","type_error","build_error","coverage","custom","eslint"] },
    "Summary": { "key": "id", "kinds": ["repo","dir","file","symbol"] },
    "Route":   { "key": "path", "kinds": ["api","page","layout"], "note": "Next.js App/Pages router" },
    "Model":   { "key": "name", "note": "Prisma schema model with usage stats" },
    "Finding": { "key": "id", "severities": ["critical","high","medium","low","info"],
                 "statuses": ["open","fixed","dismissed"],
                 "note": "audit rule output; stable IDs, auto-fixed detection" }
  },
  "relationships": {
    "contains":   { "from": "File",   "to": "Symbol" },
    "exports":    { "from": "File",   "to": "Symbol" },
    "imports":    { "from": "File",   "to": "File" },
    "calls":      { "from": "Symbol", "to": "Symbol" },
    "references": { "from": "Symbol", "to": "Symbol" },
    "extends":    { "from": "Symbol", "to": "Symbol" },
    "implements": { "from": "Symbol", "to": "Symbol" },
    "tested_by":  { "from": "Symbol", "to": "File" },
    "modified_by":{ "from": "File",   "to": "Commit" },
    "co_change":  { "from": "File",   "to": "File" },
    "uses_model": { "from": "Symbol", "to": "Model", "note": "prisma.<model>.<op>() call sites" },
    "serves":     { "from": "Route",  "to": "File" },
    "flagged_in": { "from": "Finding","to": "File|Symbol" }
  },
  "intents": ["symbol","search","architecture","history","health","tests","quality","impact"],
  "envelope": {
    "ok": "bool", "tool": "string", "result": "object",
    "next_ops": "string[]",
    "index": { "fresh": "bool", "lag_s": "number", "files": "integer" }
  },
  "tools": ["search","symbol","graph","context","summary","map","describe",
            "broken","hotspots","history","route","git_index","index_status",
            "audit","findings","refactors","impact","routes","models"],
  "freshness": { "stale_after_s": 300, "enforced_by": ["git-hooks","watcher","daemon"] },
  "self_description": "GET /ontology.json · describe(entity) · cip tools --schema"
}
```

### 1.3 `AGENTS.md` (REPLACE — v1.1; adds Quality & DevOps section)

````markdown
# AGENTS.md — Code Intelligence Bootstrap (CIP v1.1 + Stack Pack)

This repository runs **CIP**: a continuously updated model of the codebase —
structure, history, tests, runtime health, and a semantic audit layer for the
TS/Next.js/Prisma/SQLite stack. Do NOT read the whole repo. Interrogate the index.

## Workflow (before any change)
1. `cip search "<intent>"`  → candidates + detected intent
2. `cip symbol <Name>`      → definition + relationship counts
3. `cip impact <file>`      → blast radius BEFORE editing (dependents, routes, tests, risk)
4. `cip context "<intent>"` → budgeted pack: code + summary + relations + tests + failures
5. Read exact source only where the index points.

## Quality & DevOps (this repo is stack-audited)
- `cip audit`      → refresh findings (secrets, N+1, missing indexes, client leaks…)
- `cip refactors`  → ranked quick wins (fix these first)
- `cip findings --severity critical` → must-fix list
- `cip broken`     → failing tests + type errors right now
- `cip gate`       → merge gate; if it fails, fix before committing
- `cip routes` / `cip models` → route inventory, Prisma usage, orphans (hidden features)
- After your change: re-run `cip audit`; findings that disappeared auto-close as `fixed`.

## Architecture-first questions
`cip map` · `cip summary [path]` · `cip hotspots` · `cip history <path>`

## Rules
- Index = authoritative for STRUCTURE. Source = authoritative for IMPLEMENTATION.
- If `"fresh": false` → `cip sync` first.
- Never delete a `HIDDEN-*` finding's target without checking `cip impact` and git history.
- Self-introspection: `cip describe <Entity>` · `cip tools --schema`.

## Tools
CLI/MCP (`cip mcp`) / HTTP (`cip serve`): search, symbol, graph, context, summary, map,
describe, broken, hotspots, history, route, git_index, index_status, audit, findings,
refactors, impact, routes, models. Every response includes `next_ops` — follow them.
````

### 1.4 `config.toml` (APPEND)

```toml
# ---- v1.1 stack pack ----
[audit]
ignore_rules = []        # e.g. ["QA-CONSOLE", "QA-ANY"]
```

---

## 2. New modules — `lib/cipkg/stack/`

### 2.1 `stack/__init__.py`

```python
"""CIP Stack Pack v1.1 — TS/Next.js/Prisma/SQLite dev-cycle intelligence:
audit rules, blast-radius impact, route/model inventories, quality gate."""
__version__ = "1.1.0"
```

### 2.2 `stack/common.py`

```python
"""Stack-pack schema: findings, routes, models, model_usage.
Tables are ensured lazily — no edits to core store.py required."""

STACK_SCHEMA = """
CREATE TABLE IF NOT EXISTS findings(
  id TEXT PRIMARY KEY, rule TEXT, severity TEXT,
  path TEXT, line INTEGER, symbol_id TEXT,
  title TEXT, detail TEXT, suggestion TEXT, effort TEXT,
  ts REAL, status TEXT DEFAULT 'open');
CREATE INDEX IF NOT EXISTS idx_find_rule ON findings(rule);
CREATE INDEX IF NOT EXISTS idx_find_path ON findings(path);
CREATE INDEX IF NOT EXISTS idx_find_status ON findings(status);

CREATE TABLE IF NOT EXISTS routes(
  path TEXT PRIMARY KEY, file TEXT, kind TEXT,
  methods TEXT, client INTEGER DEFAULT 0);

CREATE TABLE IF NOT EXISTS models(
  name TEXT PRIMARY KEY, fields TEXT, indexes TEXT, source TEXT);

CREATE TABLE IF NOT EXISTS model_usage(
  model TEXT, operation TEXT, symbol_id TEXT, path TEXT,
  PRIMARY KEY(model, operation, symbol_id, path));
"""

def ensure(con):
    con.executescript(STACK_SCHEMA)
```

### 2.3 `stack/prisma.py`

```python
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
```

### 2.4 `stack/nextjs.py`

```python
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
```

### 2.5 `stack/rules.py` — the 24-rule engine

```python
"""Audit rule engine. Each rule is a pure function over the CIP index + source,
returning Finding dicts. Rules are idempotent, cheap, and fail in isolation."""
import ast, os, re
from ..base import is_test_path

def F(rule, severity, path, title, detail="", suggestion="", effort="small",
      line=0, symbol_id=None):
    return {"rule": rule, "severity": severity, "path": path, "line": line,
            "symbol_id": symbol_id, "title": title, "detail": detail,
            "suggestion": suggestion, "effort": effort}

def _read(root, rel):
    try:
        return open(os.path.join(root, rel), encoding="utf-8", errors="replace").read()
    except OSError:
        return ""

def _ts_files(con):
    return [r["path"] for r in con.execute(
        "SELECT path FROM files WHERE language IN ('typescript','javascript')")]

ENTRY_BASENAMES = {"page.tsx", "page.jsx", "page.js", "route.ts", "route.js",
                   "layout.tsx", "layout.jsx", "middleware.ts", "instrumentation.ts",
                   "next.config.js", "next.config.mjs", "next.config.ts"}

# ---------------- hidden features ----------------

def rule_hidden_export(con, root, cfg):
    out = []
    rows = con.execute("""
        SELECT s.id, s.name, s.path FROM symbols s
        JOIN files f ON f.path = s.path
        WHERE f.language IN ('typescript','javascript')
          AND s.signature LIKE 'export%'
          AND s.kind IN ('class','function','interface','type')
          AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.dst = s.id
                          AND e.kind IN ('calls','references'))""").fetchall()
    for s in rows:
        if os.path.basename(s["path"]) in ENTRY_BASENAMES: continue
        if is_test_path(s["path"], cfg): continue
        if s["path"].endswith((".tsx", ".jsx")) and s["name"][:1].isupper(): continue  # JSX usage invisible to parser
        out.append(F("HIDDEN-EXPORT", "low", s["path"],
                     f"Exported symbol '{s['name']}' is never referenced",
                     detail=s["id"], symbol_id=s["id"],
                     suggestion="Hidden feature or dead code: delete it, or document/expose it.",
                     effort="trivial"))
    return out[:200]

def rule_hidden_route(con, root, cfg):
    from .nextjs import route_referenced
    out = []
    for r in con.execute("SELECT path, file FROM routes WHERE kind='api'"):
        if not route_referenced(con, root, r["path"]):
            out.append(F("HIDDEN-ROUTE", "medium", r["file"],
                         f"API route {r['path']} is never called from this codebase",
                         suggestion="Check for external callers; otherwise delete or document (hidden feature)."))
    return out

def rule_hidden_model(con, root, cfg):
    out = []
    for m in con.execute("SELECT name FROM models"):
        c = con.execute("SELECT COUNT(*) c FROM model_usage WHERE model=?",
                        (m["name"],)).fetchone()["c"]
        if c == 0:
            out.append(F("HIDDEN-MODEL", "medium", "prisma/schema.prisma",
                         f"Prisma model '{m['name']}' has no usage in code",
                         suggestion="Buried backend feature or leftover: remove from schema or find its consumers."))
    return out

# ---------------- prisma / sqlite ----------------

N1_RE = re.compile(r"(?:for\s*\(|\.map\s*\(|\.forEach\s*\()[\s\S]{0,200}?"
                   r"await\s+prisma\.(\w+)\.(?:findFirst|findMany|findUnique)\s*\(")

def rule_db_n1(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        src = _read(root, rel)
        for m in N1_RE.finditer(src):
            ln = src.count("\n", 0, m.start()) + 1
            out.append(F("DB-N1", "high", rel,
                         f"Probable N+1: prisma.{m.group(1)} query inside a loop",
                         suggestion="Batch it: one query with `in:`/include, then map in memory.",
                         effort="small", line=ln))
    return out[:100]

def rule_db_missing_index(con, root, cfg):
    from .prisma import where_fields
    wf = where_fields(con, root)
    models = {r["name"]: r for r in con.execute("SELECT name, fields, indexes FROM models")}
    out = []
    for model, used in wf.items():
        m = models.get(model)
        if not m: continue
        try:
            field_names = ast.literal_eval(m["fields"])
            indexed = {c for combo in ast.literal_eval(m["indexes"]) for c in combo}
        except Exception:
            continue
        for f in sorted(used):
            if f in field_names and f not in indexed:
                out.append(F("DB-MISSING-INDEX", "medium", "prisma/schema.prisma",
                             f"{model}.{f} is filtered in where: but has no index",
                             detail="SQLite does a full table scan for this.",
                             suggestion=f"Add @@index([{f}]) to model {model}, then `prisma migrate dev`.",
                             effort="trivial"))
    return out

def rule_db_no_await(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        for i, line in enumerate(_read(root, rel).splitlines()):
            s = line.strip()
            if "prisma." not in s or "(" not in s: continue
            if s.startswith(("//", "*", "/*")): continue
            if any(k in s for k in ("await", "return", "=", "then(", "=>", "yield", "void")): continue
            out.append(F("DB-NO-AWAIT", "high", rel,
                         "Prisma call without await/return",
                         suggestion="Add await/return — unawaited promises swallow errors.",
                         effort="trivial", line=i + 1))
    return out[:50]

def rule_db_destructive_migration(con, root, cfg):
    out = []
    mdir = os.path.join(root, "prisma", "migrations")
    if not os.path.isdir(mdir):
        return out
    for dirpath, _dirs, files in os.walk(mdir):
        for fn in files:
            if not fn.endswith(".sql"): continue
            p = os.path.join(dirpath, fn)
            try: text = open(p, encoding="utf-8", errors="replace").read()
            except OSError: continue
            for m in re.finditer(r"(?i)\bDROP\s+(TABLE|COLUMN)\b", text):
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                out.append(F("DB-DESTRUCTIVE-MIGRATION", "high", rel,
                             f"Destructive migration: DROP {m.group(1).upper()}",
                             suggestion="Confirm data loss is intended; back up SQLite DB before applying."))
    return out[:30]

def rule_db_schema_drift(con, root, cfg):
    from .prisma import find_schema
    rel = find_schema(root)
    if not rel: return []
    sp = os.path.join(root, rel)
    mdir = os.path.join(os.path.dirname(sp), "migrations")
    if not os.path.isdir(mdir): return []
    try:
        newest = max(os.path.getmtime(os.path.join(mdir, d)) for d in os.listdir(mdir))
    except ValueError:
        return []
    if os.path.getmtime(sp) > newest:
        return [F("DB-SCHEMA-DRIFT", "medium", rel,
                  "schema.prisma changed since the last migration",
                  suggestion="Run `prisma migrate dev` (or `migrate diff`) to reconcile.",
                  effort="trivial")]
    return []

# ---------------- security / env ----------------

SECRET_RES = [
    (re.compile(r"sk_live_[A-Za-z0-9]{10,}"), "Stripe live key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"(?:postgres|mysql|mongodb)(?:\+srv)?://[^/\s:]+:[^@\s]+@"), "connection string with password"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9\-]{10,}"), "GitHub/Slack token"),
    (re.compile(r"""(?:password|passwd|secret|apiKey|api_key)\s*[:=]\s*['"][^'"]{6,}['"]""", re.I), "hardcoded credential"),
]

def rule_secrets(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        if any(x in rel.lower() for x in ("test", "fixture", "mock", ".env")): continue
        for i, line in enumerate(_read(root, rel).splitlines()):
            if "process.env" in line or "example" in line.lower(): continue
            for rx, label in SECRET_RES:
                if rx.search(line):
                    out.append(F("SEC-HARDCODED-SECRET", "critical", rel,
                                 f"Hardcoded secret: {label}",
                                 suggestion="Rotate this credential NOW; move to env/secret manager.",
                                 effort="trivial", line=i + 1))
    return out[:30]

def rule_sql_raw(con, root, cfg):
    out = []
    rx = re.compile(r"\$(?:query|execute)RawUnsafe")
    for rel in _ts_files(con):
        src = _read(root, rel)
        for m in rx.finditer(src):
            ln = src.count("\n", 0, m.start()) + 1
            out.append(F("SEC-SQL-RAW", "high", rel,
                         "Raw SQL without parameterization (…RawUnsafe)",
                         suggestion="Use prisma.$queryRaw`` tagged templates or parameter binding.",
                         effort="small", line=ln))
    return out[:30]

ENV_USE_RE = re.compile(r"process\.env\.([A-Z_][A-Z0-9_]*)")
SKIP_ENV = {"NODE_ENV", "CI", "PORT", "TZ", "VERCEL_ENV", "VERCEL_URL", "NEXT_RUNTIME"}

def _env_defined(root):
    keys = set()
    for f in (".env", ".env.local", ".env.development", ".env.production", ".env.example"):
        p = os.path.join(root, f)
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="replace"):
                m = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=", line)
                if m: keys.add(m.group(1))
    return keys

def rule_env(con, root, cfg):
    defined = _env_defined(root)
    used = {}
    for rel in _ts_files(con):
        src = _read(root, rel)
        for m in ENV_USE_RE.finditer(src):
            k = m.group(1)
            if k not in used:
                used[k] = (rel, src.count("\n", 0, m.start()) + 1)
    out = []
    for k, (p, ln) in used.items():
        if k in SKIP_ENV: continue
        if k not in defined:
            out.append(F("ENV-UNDEFINED", "high", p,
                         f"process.env.{k} is used but defined in no .env*",
                         suggestion=f"Add {k} to .env / deployment secrets (crashes or silent undefined in prod).",
                         effort="trivial", line=ln))
    for k in sorted(defined - set(used)):
        out.append(F("ENV-UNREAD", "low", ".env",
                     f"{k} is defined but never read", effort="trivial"))
    return out

# ---------------- next.js ----------------

def _server_spec(spec):
    for s in ("@prisma/client", "server-only", "fs", "node:fs",
              "child_process", "node:child_process"):
        if spec == s: return s
    for s in ("prisma", "lib", "server"):
        parts = spec.split("/")
        if s in parts and ("db" in parts or s != "lib"):
            if s == "lib" and "db" not in parts: continue
            return spec
    return None

def rule_next_client_leak(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        src = _read(root, rel)
        if not re.match(r"""^\s*['"]use client['"]""", src): continue
        for m in re.finditer(r"""from\s+['"]([^'"]+)['"]""", src):
            hit = _server_spec(m.group(1))
            if hit:
                ln = src.count("\n", 0, m.start()) + 1
                out.append(F("NEXT-CLIENT-LEAK", "high", rel,
                             f'Client component imports server module "{m.group(1)}"',
                             suggestion="Move data access to a server component/API route; pass props down.",
                             effort="small", line=ln))
    return out[:50]

def rule_route_no_error(con, root, cfg):
    out = []
    for r in con.execute("SELECT file, path FROM routes WHERE kind='api'"):
        src = _read(root, r["file"])
        if "GET" not in src and "POST" not in src: continue
        if "try" not in src or "catch" not in src:
            out.append(F("NEXT-ROUTE-NO-ERROR", "medium", r["file"],
                         f"API route {r['path']} has no try/catch",
                         suggestion="Wrap handlers; return NextResponse.json({ error }, { status: 500 }).",
                         effort="trivial"))
    return out

def rule_action_no_validate(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        src = _read(root, rel)
        if not re.search(r"""['"]use server['"]""", src): continue
        if not re.search(r"zod|safeParse|\.parse\(", src):
            out.append(F("NEXT-ACTION-NO-VALIDATE", "medium", rel,
                         "Server action without input validation",
                         suggestion="Validate with zod/parse before touching the DB — server actions are public endpoints.",
                         effort="small"))
    return out[:30]

# ---------------- quality / architecture ----------------

def rule_qa_any(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        src = _read(root, rel)
        n = len(re.findall(r":\s*any\b|as\s+any\b", src))
        if n > 10:
            out.append(F("QA-ANY", "low", rel, f"{n} uses of `any`",
                         suggestion="Type the top offenders; `any` defeats every other safety layer."))
    return out[:30]

def rule_qa_tsignore(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        src = _read(root, rel)
        n = src.count("@ts-ignore") + src.count("@ts-expect-error")
        if n > 5:
            out.append(F("QA-TSIGNORE", "low", rel, f"{n} suppressed type errors",
                         suggestion="Each suppression hides a potential runtime bug; triage them."))
    return out[:30]

def rule_qa_console(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        if is_test_path(rel, cfg): continue
        n = _read(root, rel).count("console.log")
        if n > 5:
            out.append(F("QA-CONSOLE", "low", rel, f"{n} console.log calls",
                         suggestion="Replace with a logger or remove before shipping."))
    return out[:30]

def rule_qa_dup(con, root, cfg):
    out = []
    rows = con.execute("""SELECT body_hash, COUNT(*) c, GROUP_CONCAT(id, ' | ') ids
                          FROM symbols WHERE body_hash IS NOT NULL AND length(body) > 80
                          GROUP BY body_hash HAVING c > 1 LIMIT 30""").fetchall()
    for r in rows:
        ids = r["ids"].split(" | ")
        paths = sorted({i.split("://", 1)[-1].split("#")[0] for i in ids})
        if len(paths) < 2: continue
        out.append(F("QA-DUP", "low", paths[0],
                     f"Identical implementation in {len(paths)} places",
                     detail=", ".join(paths[:4]),
                     suggestion="Extract a shared helper — duplicated logic drifts into bugs.",
                     effort="small"))
    return out

def rule_qa_circular(con, root, cfg):
    adj = {}
    for e in con.execute("SELECT src, dst FROM edges WHERE kind='imports'"):
        adj.setdefault(e["src"], set()).add(e["dst"])
    cycles, seen = [], set()
    def dfs(node, path):
        if len(path) > 6: return
        for nxt in list(adj.get(node, ()))[:20]:
            if nxt in path:
                i = path.index(nxt)
                key = tuple(sorted(path[i:]))
                if key not in seen:
                    seen.add(key)
                    cycles.append(path[i:] + [nxt])
            else:
                dfs(nxt, path + [nxt])
    for n in list(adj)[:400]:
        dfs(n, [n])
    return [F("QA-CIRCULAR", "medium", c[0],
              "Circular import: " + " → ".join(c[:6]),
              suggestion="Break the cycle: shared code moves down a layer, or use events/interfaces.",
              effort="medium") for c in cycles[:20]]

def rule_qa_god_module(con, root, cfg):
    out = []
    rows = con.execute("""
        SELECT f.path, f.lines,
               (SELECT COUNT(*) FROM symbols s WHERE s.path = f.path) sc,
               (SELECT COUNT(*) FROM edges e WHERE e.dst = f.path AND e.kind='imports') fi
        FROM files f WHERE f.language IN ('typescript','javascript')
          AND f.lines > 600""").fetchall()
    for r in rows:
        if r["sc"] > 15 or r["fi"] > 8:
            out.append(F("QA-GOD-MODULE", "medium", r["path"],
                         f"God module: {r['lines']} lines, {r['sc']} symbols, fan-in {r['fi']}",
                         suggestion="Split by responsibility; high fan-in + size = merge-conflict and bug magnet.",
                         effort="large"))
    return out[:30]

def rule_qa_untested_hot(con, root, cfg):
    out = []
    rows = con.execute("""
        SELECT s.id, s.name, s.path, COUNT(e.src) c FROM symbols s
        JOIN edges e ON e.dst = s.id AND e.kind IN ('calls','references')
        WHERE NOT EXISTS (SELECT 1 FROM edges t WHERE t.src = s.id AND t.kind='tested_by')
        GROUP BY s.id HAVING c >= 5 ORDER BY c DESC LIMIT 30""").fetchall()
    for r in rows:
        out.append(F("QA-UNTESTED-HOT", "medium", r["path"],
                     f"'{r['name']}' has {r['c']} dependents but no tests",
                     detail=r["id"], symbol_id=r["id"],
                     suggestion="Add at least one test before modifying — this is load-bearing code.",
                     effort="small"))
    return out

def rule_layer_violation(con, root, cfg):
    out, seen = [], set()
    LOW = ("lib/", "src/lib/", "packages/", "server/")
    HIGH = ("app/", "pages/", "src/app/", "src/pages/", "components/", "src/components/")
    for e in con.execute("SELECT src, dst FROM edges WHERE kind='imports'"):
        s, d = e["src"], e["dst"]
        if s.startswith(LOW) and d.startswith(HIGH) and (s, d) not in seen:
            seen.add((s, d))
            out.append(F("ARCH-LAYER-VIOLATION", "medium", s,
                         f"Library layer imports UI layer: {d}",
                         suggestion="Invert the dependency — UI calls lib, never the reverse.",
                         effort="medium"))
    return out[:50]

def rule_orphan_file(con, root, cfg):
    out = []
    rows = con.execute("""
        SELECT f.path FROM files f
        WHERE f.language IN ('typescript','javascript')
          AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.dst = f.path AND e.kind='imports')""").fetchall()
    for r in rows:
        p = r["path"]
        base = os.path.basename(p)
        if base in ENTRY_BASENAMES or is_test_path(p, cfg): continue
        if base.startswith("index.") or base.endswith((".d.ts", ".config.ts", ".config.js")): continue
        out.append(F("ARCH-ORPHAN-FILE", "low", p,
                     "File is imported by nothing",
                     suggestion="Hidden feature or dead file — verify, then delete or wire up.",
                     effort="trivial"))
    return out[:100]

RULES = [
    ("SEC-HARDCODED-SECRET", rule_secrets), ("SEC-SQL-RAW", rule_sql_raw),
    ("ENV", rule_env),
    ("NEXT-CLIENT-LEAK", rule_next_client_leak),
    ("DB-N1", rule_db_n1), ("DB-MISSING-INDEX", rule_db_missing_index),
    ("DB-NO-AWAIT", rule_db_no_await),
    ("DB-DESTRUCTIVE-MIGRATION", rule_db_destructive_migration),
    ("DB-SCHEMA-DRIFT", rule_db_schema_drift),
    ("HIDDEN-EXPORT", rule_hidden_export), ("HIDDEN-ROUTE", rule_hidden_route),
    ("HIDDEN-MODEL", rule_hidden_model),
    ("NEXT-ROUTE-NO-ERROR", rule_route_no_error),
    ("NEXT-ACTION-NO-VALIDATE", rule_action_no_validate),
    ("QA-ANY", rule_qa_any), ("QA-TSIGNORE", rule_qa_tsignore),
    ("QA-CONSOLE", rule_qa_console), ("QA-DUP", rule_qa_dup),
    ("QA-CIRCULAR", rule_qa_circular), ("QA-GOD-MODULE", rule_qa_god_module),
    ("QA-UNTESTED-HOT", rule_qa_untested_hot),
    ("ARCH-LAYER-VIOLATION", rule_layer_violation),
    ("ARCH-ORPHAN-FILE", rule_orphan_file),
]

def run_rules(con, root, cfg):
    skip = set(cfg.get("audit", {}).get("ignore_rules", []))
    findings = []
    for rid, fn in RULES:
        if rid in skip: continue
        try:
            findings.extend(fn(con, root, cfg))
        except Exception as e:
            findings.append(F(rid, "info", "", f"rule {rid} failed: {e}"))
    return findings
```

### 2.6 `stack/audit.py` — orchestration, reports, gate

```python
"""Audit orchestration: run rules → upsert findings (stable IDs, auto-fix),
quick wins, markdown reports, eslint ingestion, CI gate."""
import hashlib, json, os, sys, time
from ..base import repo_root, load_config
from ..store import connect
from .common import ensure
from . import rules as R
from . import nextjs, prisma

def _fid(f):
    return hashlib.sha1(
        f"{f['rule']}:{f['path']}:{f['line']}:{f['title']}".encode()).hexdigest()[:16]

def audit(root=None, refresh=True):
    root = root or repo_root(); cfg = load_config(root); con = connect(root)
    ensure(con)
    if refresh:
        try: nextjs.index_routes(con, root)
        except Exception: pass
        try: prisma.index_stack(con, root)
        except Exception: pass
    findings = R.run_rules(con, root, cfg)
    seen = set()
    for f in findings:
        fid = _fid(f); seen.add(fid)
        con.execute(
            "INSERT INTO findings(id,rule,severity,path,line,symbol_id,title,detail,"
            "suggestion,effort,ts,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,'open') "
            "ON CONFLICT(id) DO UPDATE SET severity=excluded.severity, title=excluded.title, "
            "detail=excluded.detail, suggestion=excluded.suggestion, "
            "effort=excluded.effort, ts=excluded.ts",
            (fid, f["rule"], f["severity"], f["path"], f["line"], f["symbol_id"],
             f["title"], f["detail"], f["suggestion"], f["effort"], time.time()))
    if seen:
        ph = ",".join("?" * len(seen))
        con.execute(f"UPDATE findings SET status='fixed' "
                    f"WHERE status='open' AND id NOT IN ({ph})", list(seen))
    con.commit()
    return summarize(con)

def summarize(con):
    rows = con.execute("SELECT severity, COUNT(*) c FROM findings "
                       "WHERE status='open' GROUP BY severity").fetchall()
    by = {r["severity"]: r["c"] for r in rows}
    return {"open": sum(by.values()), "by_severity": by,
            "critical": by.get("critical", 0), "high": by.get("high", 0)}

def findings(root=None, severity=None, rule=None, path=None, limit=100):
    con = connect(root or repo_root()); ensure(con)
    q, args = "SELECT * FROM findings WHERE status='open'", []
    if severity: q += " AND severity=?"; args.append(severity)
    if rule:     q += " AND rule=?";     args.append(rule)
    if path:     q += " AND path LIKE ?"; args.append(f"%{path}%")
    q += (" ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
          "WHEN 'medium' THEN 2 ELSE 3 END, rule LIMIT ?")
    args.append(limit)
    return [dict(r) for r in con.execute(q, args)]

def quick_wins(root=None, limit=10):
    con = connect(root or repo_root()); ensure(con)
    rows = con.execute(
        "SELECT * FROM findings WHERE status='open' AND suggestion != '' "
        "AND severity IN ('critical','high','medium') AND effort IN ('trivial','small') "
        "ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END, "
        "CASE effort WHEN 'trivial' THEN 0 ELSE 1 END LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

def ingest_eslint(root, file_path):
    root = root or repo_root(); con = connect(root); ensure(con)
    text = sys.stdin.read() if file_path == "-" else open(file_path, encoding="utf-8").read()
    data = json.loads(text)
    n = 0
    for fr in data:
        rel = os.path.relpath(fr.get("filePath", ""), root).replace(os.sep, "/")
        for msg in fr.get("messages", []):
            f = {"rule": f"ESLINT:{msg.get('ruleId') or 'parse'}",
                 "severity": "high" if msg.get("severity", 1) == 2 else "low",
                 "path": rel, "line": msg.get("line", 0), "symbol_id": None,
                 "title": msg.get("message", "")[:200], "detail": "",
                 "suggestion": "", "effort": "small"}
            con.execute(
                "INSERT INTO findings(id,rule,severity,path,line,symbol_id,title,detail,"
                "suggestion,effort,ts,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,'open') "
                "ON CONFLICT(id) DO UPDATE SET ts=excluded.ts",
                (_fid(f), f["rule"], f["severity"], f["path"], f["line"], None,
                 f["title"], "", "", f["effort"], time.time()))
            n += 1
    con.commit()
    return {"ingested": n, "kind": "eslint"}

def report_markdown(root=None):
    root = root or repo_root(); con = connect(root); ensure(con)
    s = summarize(con)
    lines = ["# CIP Stack Audit", "",
             f"Open findings: **{s['open']}** — " +
             ", ".join(f"{v} {k}" for k, v in sorted(s["by_severity"].items())), ""]
    for sev in ("critical", "high", "medium", "low"):
        rows = con.execute("SELECT * FROM findings WHERE status='open' AND severity=? "
                           "ORDER BY rule LIMIT 25", (sev,)).fetchall()
        if not rows: continue
        lines += [f"## {sev.title()} ({len(rows)})", ""]
        for r in rows:
            loc = r["path"] + (f":{r['line']}" if r["line"] else "")
            lines.append(f"- **[{r['rule']}]** `{loc}` — {r['title']}")
            if r["suggestion"]:
                lines.append(f"  - fix: {r['suggestion']} *(effort: {r['effort']})*")
        lines.append("")
    qw = quick_wins(root, limit=10)
    if qw:
        lines += ["## Quick wins", "",
                  "| Rule | Location | Fix | Effort |", "|---|---|---|---|"]
        for q in qw:
            lines.append(f"| {q['rule']} | `{q['path']}` | {q['suggestion'][:90]} | {q['effort']} |")
    return "\n".join(lines) + "\n"

def gate(root=None):
    """CI/pre-commit quality gate: exit non-zero on criticals or broken signals."""
    root = root or repo_root()
    from .. import indexer
    from ..runtime_adapters import broken
    indexer.sync(root)
    stats = audit(root, refresh=True)
    fails = len(broken(root)["signals"])
    reasons = []
    if stats.get("critical", 0):
        reasons.append(f"{stats['critical']} critical findings")
    if fails:
        reasons.append(f"{fails} failing test/type signals")
    return {"ok": not reasons, "reasons": reasons,
            "findings": stats, "broken_signals": fails}
```

### 2.7 `stack/impact.py` — blast radius

```python
"""Blast-radius analysis: transitive dependents, affected routes, tests to run,
risk level — for a file, a symbol, or an entire git diff (PR mode)."""
import subprocess
from ..base import repo_root
from ..store import connect
from .common import ensure

def _to_file(con, node):
    if "://" in node:
        r = con.execute("SELECT path FROM symbols WHERE id=?", (node,)).fetchone()
        return r["path"] if r else None
    return node

def _dependents(con, seed_files, depth=2):
    frontier, seen = set(seed_files), set(seed_files)
    for _ in range(max(1, min(depth, 3))):
        nxt = set()
        for f in frontier:
            for r in con.execute(
                    "SELECT src FROM edges WHERE dst=? AND kind IN ('imports','calls','references')",
                    (f,)):
                p = _to_file(con, r["src"])
                if p and p not in seen:
                    seen.add(p); nxt.add(p)
        frontier = nxt
    return seen

def impact(root=None, target="", depth=2):
    root = root or repo_root(); con = connect(root); ensure(con)
    seed = set()
    if con.execute("SELECT 1 FROM files WHERE path=?", (target,)).fetchone():
        seed.add(target)
    else:
        sym = con.execute("SELECT path FROM symbols WHERE id=? OR name=? LIMIT 1",
                          (target, target)).fetchone()
        if sym: seed.add(sym["path"])
    if not seed:
        return {"error": f"unknown target: {target}"}
    dep = _dependents(con, seed, depth)
    tests = set()
    for r in con.execute("SELECT src, dst FROM edges WHERE kind='tested_by'"):
        s = con.execute("SELECT path FROM symbols WHERE id=?", (r["src"],)).fetchone()
        if s and s["path"] in dep:
            tests.add(r["dst"])
    ph = ",".join("?" * len(dep))
    routes_hit = [dict(r) for r in con.execute(
        f"SELECT path, kind FROM routes WHERE file IN ({ph})", list(dep))]
    findings_hit = con.execute(
        f"SELECT COUNT(*) c FROM findings WHERE status='open' AND path IN ({ph})",
        list(dep)).fetchone()["c"]
    try:
        from ..gitindex import hotspots
        hs = {h["path"]: h["score"] for h in hotspots(root, k=50)}
        heat = max((hs.get(p, 0.0) for p in dep), default=0.0)
    except Exception:
        heat = 0.0
    risk = "low"
    if routes_hit or len(dep) > 8 or findings_hit > 3: risk = "medium"
    if len(dep) > 20 or (routes_hit and heat > 2): risk = "high"
    advice = []
    if risk == "high":
        advice.append("High blast radius: land in small increments; full test pass required.")
    if routes_hit:
        advice.append(f"{len(routes_hit)} route(s) affected — verify API contracts and consumers.")
    if tests:
        advice.append("Run the listed tests before merging.")
    else:
        advice.append("No tests cover this area — add one test for the changed behavior first.")
    return {"target": target, "risk": risk,
            "seed_files": sorted(seed),
            "affected_files": sorted(dep)[:50], "affected_count": len(dep),
            "tests_to_run": sorted(tests)[:20],
            "routes_affected": routes_hit[:10],
            "open_findings_in_area": findings_hit,
            "hotspot_heat": round(heat, 1), "advice": advice}

def impact_diff(root=None, ref="HEAD"):
    root = root or repo_root()
    try:
        out = subprocess.run(["git", "diff", "--name-only", ref],
                             cwd=root, capture_output=True, text=True, timeout=30)
    except Exception as e:
        return {"error": str(e)}
    files = [l.strip() for l in out.stdout.splitlines() if l.strip()]
    union, all_tests, all_routes, worst = set(), set(), [], "low"
    order = {"low": 0, "medium": 1, "high": 2}
    for f in files[:20]:
        r = impact(root, f)
        if "error" in r: continue
        union.update(r["affected_files"])
        all_tests.update(r["tests_to_run"])
        all_routes += r["routes_affected"]
        if order[r["risk"]] > order[worst]: worst = r["risk"]
    return {"base": ref, "changed_files": files,
            "risk": worst, "affected_count": len(union),
            "affected_files": sorted(union)[:60],
            "tests_to_run": sorted(all_tests)[:25],
            "routes_affected": all_routes[:10]}
```

### 2.8 `stack/selftest.py`

```python
"""Stack-pack self-test: fixture Next.js+Prisma repo with planted defects."""
import os, shutil, tempfile, unittest

SCHEMA = """
model User {
  id    String @id
  email String
  posts Post[]
}

model Post {
  id    String @id
  title String
}
"""
ROUTE = """import { prisma } from "@/lib/db";

export async function GET() {
  const users = await prisma.user.findMany();
  return Response.json(users);
}
"""
CLIENT = """"use client";
import { prisma } from "@prisma/client";

export default function Dashboard() { return null; }
"""
USERS = """import { prisma } from "@/lib/db";

export async function loadUsers(ids: string[]) {
  const out: unknown[] = [];
  for (const id of ids) {
    const u = await prisma.user.findUnique({ where: { id } });
    out.push(u);
  }
  const first = await prisma.user.findFirst({ where: { email: "x@y.z" } });
  return { out, first };
}
"""
CONFIG = """export const stripeKey = "sk_live_abcdefghijklmnop1234";
export const dbUrl = "postgres://admin:hunter22@db.internal/app";
export const flag = process.env.MISSING_VAR;
"""

class StackPack(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cip-stacktest-")
        os.makedirs(os.path.join(self.root, ".cip", "data"))
        os.makedirs(os.path.join(self.root, "prisma"))
        os.makedirs(os.path.join(self.root, "app", "api", "users"))
        os.makedirs(os.path.join(self.root, "components"))
        os.makedirs(os.path.join(self.root, "lib"))
        w = lambda p, t: open(os.path.join(self.root, p), "w").write(t)
        w("prisma/schema.prisma", SCHEMA)
        w("app/api/users/route.ts", ROUTE)
        w("components/Dashboard.tsx", CLIENT)
        w("lib/users.ts", USERS)
        w("lib/config.ts", CONFIG)
        from .. import indexer
        indexer.sync(self.root, full=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_audit_detects_planted_defects(self):
        from . import audit as sa
        stats = sa.audit(self.root)
        self.assertGreater(stats["open"], 0)
        found = {f["rule"] for f in sa.findings(self.root, limit=500)}
        for expected in ("DB-N1", "NEXT-CLIENT-LEAK", "SEC-HARDCODED-SECRET",
                         "DB-MISSING-INDEX", "NEXT-ROUTE-NO-ERROR",
                         "HIDDEN-MODEL", "ENV-UNDEFINED"):
            self.assertIn(expected, found, f"missing rule output: {expected}")
        self.assertGreaterEqual(stats["critical"], 1)

    def test_quick_wins_and_report(self):
        from . import audit as sa
        sa.audit(self.root)
        self.assertTrue(sa.quick_wins(self.root))
        md = sa.report_markdown(self.root)
        self.assertIn("# CIP Stack Audit", md)

    def test_models_and_routes(self):
        from . import prisma as sp, nextjs as sn
        m = sp.models_report(self.root)
        names = {x["model"]: x for x in m["models"]}
        self.assertIn("User", names); self.assertIn("Post", names)
        self.assertTrue(names["Post"]["orphan"])
        self.assertFalse(names["User"]["orphan"])
        routes = sn.list_routes(self.root)
        self.assertTrue(any(r["path"] == "/api/users" for r in routes))

    def test_impact(self):
        from . import impact as si
        r = si.impact(self.root, target="lib/users.ts")
        self.assertNotIn("error", r)
        self.assertIn("lib/users.ts", r["affected_files"])

def run_stack_selftest():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StackPack)
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if res.wasSuccessful() else 1
```

---

## 3. Patches to v1.0 files (exact anchors)

### 3.1 `cli.py` — 4 edits

**Edit 1** — after `sub.add_parser("selftest")` add:

```python
    # ---- v1.1 stack pack ----
    ap = sub.add_parser("audit", help="run TS/Next/Prisma audit rules")
    ap.add_argument("--md", help="write markdown report to file")
    ap.add_argument("--no-refresh", action="store_true")
    fp = sub.add_parser("findings")
    fp.add_argument("--severity"); fp.add_argument("--rule"); fp.add_argument("--path")
    fp.add_argument("--limit", type=int, default=100)
    sub.add_parser("refactors", help="top quick-win refactors")
    mp = sub.add_parser("impact"); mp.add_argument("target", nargs="?")
    mp.add_argument("--ref"); mp.add_argument("--depth", type=int, default=2)
    sub.add_parser("routes"); sub.add_parser("models")
    sub.add_parser("gate", help="quality gate: exit 1 on critical findings/broken signals")
```

**Edit 2** — replace the `ingest` parser lines:

```python
    ig = sub.add_parser("ingest"); ig.add_argument("--kind", required=True,
        choices=["vitest", "jest", "pytest", "tsc", "generic", "eslint"])
    ig.add_argument("--file", default="-", help="path or '-' for stdin")
```

**Edit 3** — replace the `ingest` dispatch:

```python
    elif a.cmd == "ingest":
        if a.kind == "eslint":
            from .stack import audit as sa; _out(sa.ingest_eslint(root, a.file))
        else:
            from . import runtime_adapters; _out(runtime_adapters.ingest(root, a.kind, a.file))
```

**Edit 4** — replace the `selftest` dispatch and append stack commands before `return 0`:

```python
    elif a.cmd == "selftest":
        from .selftest import run_selftest
        rc = run_selftest()
        from .stack.selftest import run_stack_selftest
        rc2 = run_stack_selftest()
        return rc or rc2
    elif a.cmd == "audit":
        from .stack import audit as sa
        _out(sa.audit(root, refresh=not a.no_refresh))
        if a.md:
            open(a.md, "w").write(sa.report_markdown(root))
            print(f"report written: {a.md}")
    elif a.cmd == "findings":
        from .stack import audit as sa
        _out({"findings": sa.findings(root, severity=a.severity, rule=a.rule,
                                      path=a.path, limit=a.limit)})
    elif a.cmd == "refactors":
        from .stack import audit as sa; _out({"quick_wins": sa.quick_wins(root)})
    elif a.cmd == "impact":
        from .stack import impact as si
        if a.ref: _out(si.impact_diff(root, ref=a.ref))
        elif a.target: _out(si.impact(root, target=a.target, depth=a.depth))
        else: print("usage: cip impact <file|symbol>   |   cip impact --ref origin/main")
    elif a.cmd == "routes":
        from .stack import nextjs as sn; _out({"routes": sn.list_routes(root)})
    elif a.cmd == "models":
        from .stack import prisma as sp; _out(sp.models_report(root))
    elif a.cmd == "gate":
        from .stack import audit as sa
        g = sa.gate(root); _out(g)
        return 0 if g["ok"] else 1
```

### 3.2 `server.py` — 3 edits

**Edit 1** — imports:

```python
from . import retrieve, indexer, summarize, gitindex, runtime_adapters, router
from .stack import audit as stack_audit, impact as stack_impact
from .stack import nextjs as stack_nextjs, prisma as stack_prisma
```

**Edit 2** — insert into `TOOLS` before the closing `]`:

```python
    {"name": "audit", "description": "Run the TS/Next/Prisma/SQLite audit rules; returns finding counts.",
     "inputSchema": {"type": "object", "properties": {"refresh": {"type": "boolean"}}}},
    {"name": "findings", "description": "Query open findings by severity/rule/path.",
     "inputSchema": {"type": "object", "properties": {"severity": {"type": "string"}, "rule": {"type": "string"}, "path": {"type": "string"}, "limit": {"type": "integer"}}}},
    {"name": "refactors", "description": "Top quick-win refactors ranked by severity/effort.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "impact", "description": "Blast radius for a file/symbol, or for a git diff with `ref`.",
     "inputSchema": {"type": "object", "properties": {"target": {"type": "string"}, "ref": {"type": "string"}, "depth": {"type": "integer"}}}},
    {"name": "routes", "description": "Next.js route inventory with referenced/orphan status.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "models", "description": "Prisma model usage report incl. orphan detection.",
     "inputSchema": {"type": "object", "properties": {}}},
```

**Edit 3** — dispatch: insert before `elif name == "index_status":`, and extend `_next_ops` before its `return`:

```python
        elif name == "audit":
            res = stack_audit.audit(root, refresh=bool(args.get("refresh", True)))
        elif name == "findings":
            res = {"findings": stack_audit.findings(root, severity=args.get("severity"),
                   rule=args.get("rule"), path=args.get("path"),
                   limit=int(args.get("limit", 100)))}
        elif name == "refactors":
            res = {"quick_wins": stack_audit.quick_wins(root)}
        elif name == "impact":
            res = (stack_impact.impact_diff(root, ref=args["ref"]) if args.get("ref")
                   else stack_impact.impact(root, target=args.get("target", ""),
                                            depth=int(args.get("depth", 2))))
        elif name == "routes":
            res = {"routes": stack_nextjs.list_routes(root)}
        elif name == "models":
            res = stack_prisma.models_report(root)
```

```python
    # inside _next_ops, before `return ops[:6]`:
    if name == "audit":
        ops += ["refactors()", "findings(severity='critical')"]
    if name == "findings":
        ops += [f"impact(target='{f['path']}')" for f in res.get("findings", [])[:2]]
    if name == "impact":
        ops += ["broken()", "context(query='<planned change>')"]
    if name == "models":
        ops += ["findings(rule='DB-MISSING-INDEX')"]
```

---

## 4. Runbook

```bash
# install into a Next.js repo (v0.9/v1.0 already there → auto-upgrade):
./install.sh /path/to/nextjs-repo && cd /path/to/nextjs-repo
cip upgrade && cip selftest          # core + stack-pack tests both green

# the daily dev-cycle loop:
cip audit --md AUDIT.md              # what's wrong, human-readable
cip refactors                        # what to fix first (severity ÷ effort)
cip impact src/features/auth         # blast radius before touching it
cip impact --ref origin/main         # PR risk summary (paste into the PR)
cip gate                             # hard gate for hooks/CI

# hidden-feature discovery:
cip routes                           # orphan API routes
cip models                           # orphan Prisma models
cip findings --rule HIDDEN-EXPORT

# wire existing tooling into the unified findings stream:
npx eslint . --format json > eslint.json && cip ingest --kind eslint --file eslint.json
npx tsc --noEmit --pretty false > tsc.txt && cip ingest --kind tsc --file tsc.txt
npx vitest run --reporter=json > vt.json  && cip ingest --kind vitest --file vt.json
cip broken                           # everything currently red, one view
```

**What this gives the agent on a massive project:** one compact interface where *"is this safe?"* (`impact`), *"what's broken?"* (`broken` + `findings`), *"what's hiding?"* (`routes`/`models`/`HIDDEN-*`), and *"what should I fix first?"* (`refactors`) are each a single call — no repo reading required, findings auto-close when fixed, and `cip gate` makes the whole thing enforceable in CI.# CIP v1.1 — **STACK PACK**: TS / Next.js / Prisma / SQLite DevOps Intelligence

Designed from the seat of an agent running a massive Next.js + Prisma + SQLite codebase. What that agent actually needs, daily:

1. **What is broken right now** — without reading 10k files
2. **What will break if I touch X** — blast radius before the change
3. **What is hiding** — dead exports, never-called API routes, orphaned Prisma models (buried features)
4. **What is wrong by construction** — N+1 queries, missing indexes, client/server leaks, hardcoded secrets
5. **What to fix first** — ranked quick wins, not a wall of lint noise
6. **A gate** — one command that says "safe to merge" or not

This pack adds a **24-rule semantic audit engine**, **Prisma schema↔code cross-analysis**, **Next.js route/boundary mapping**, **blast-radius impact analysis**, **unified findings store**, **quality gate**, and Markdown refactoring reports — all on top of the existing CIP graph, zero new hard dependencies.

---

## 1. Docs

### 1.1 `STACKPACK.md` (NEW)

````markdown
# CIP v1.1 — STACK PACK (TypeScript / Next.js / Prisma / SQLite)

A dev-cycle intelligence layer: it audits the codebase like a staff engineer,
finds hidden features, predicts blast radius, and gates merges.

## New capabilities

| Capability | Command / Tool | What it answers |
|---|---|---|
| Auto-issue detection | `cip audit` / `audit` | 24 semantic rules → findings store |
| Refactor triage | `cip refactors` / `refactors` | quick wins ranked by severity ÷ effort |
| Findings query | `cip findings --severity high` / `findings` | slice by rule/severity/path |
| Blast radius | `cip impact <file\|symbol>` / `impact` | dependents, routes, tests, risk level |
| PR risk | `cip impact --ref origin/main` | union impact of the whole diff |
| Route inventory | `cip routes` / `routes` | every API/page route + called-or-orphan |
| DB model intel | `cip models` / `models` | Prisma usage per model, orphans |
| Quality gate | `cip gate` | exit 1 on critical findings / broken signals |
| Reports | `cip audit --md REPORT.md` | human/PR-ready markdown |
| Lint unification | `cip ingest --kind eslint --file r.json` | eslint → same findings stream |

## Rule catalog

| ID | Sev | Detects |
|---|---|---|
| SEC-HARDCODED-SECRET | critical | live keys, conn strings w/ password, private keys |
| SEC-SQL-RAW | high | `$queryRawUnsafe` / `$executeRawUnsafe` |
| ENV-UNDEFINED | high | `process.env.X` used but in no `.env*` |
| NEXT-CLIENT-LEAK | high | `"use client"` file importing prisma/fs/server modules |
| DB-N1 | high | awaited prisma query inside loop/map/forEach |
| DB-NO-AWAIT | high | prisma call with no await/return/assignment |
| DB-DESTRUCTIVE-MIGRATION | high | DROP TABLE / DROP COLUMN in migrations |
| DB-MISSING-INDEX | medium | fields used in `where:` with no @id/@unique/@@index (SQLite full scan) |
| DB-SCHEMA-DRIFT | medium | schema.prisma newer than last migration |
| HIDDEN-ROUTE | medium | API route never referenced anywhere |
| HIDDEN-MODEL | medium | Prisma model with zero code usage |
| NEXT-ROUTE-NO-ERROR | medium | API route handler without try/catch |
| NEXT-ACTION-NO-VALIDATE | medium | `"use server"` fn with no schema validation |
| QA-CIRCULAR | medium | circular import chains |
| QA-GOD-MODULE | medium | huge high-fan-in files |
| QA-UNTESTED-HOT | medium | heavily-used symbols with no tests |
| ARCH-LAYER-VIOLATION | medium | lib layer importing UI layer |
| HIDDEN-EXPORT | low | exported TS symbols never referenced (hidden features) |
| ARCH-ORPHAN-FILE | low | files nothing imports |
| ENV-UNREAD | low | `.env` vars never read |
| QA-DUP | low | identical function bodies in multiple places |
| QA-ANY / QA-TSIGNORE / QA-CONSOLE | low | hygiene thresholds exceeded |

## Dev-cycle workflows

**Morning triage (2 commands):**
```bash
cip audit && cip refactors
```

**Before opening a PR:**
```bash
cip impact --ref origin/main     # what does my diff touch, transitively?
cip gate                         # hard gate: criticals + broken signals
```

**Hidden-feature hunt:**
```bash
cip findings --rule HIDDEN-ROUTE
cip findings --rule HIDDEN-EXPORT
cip models                        # orphan models = buried backend features
```

**DB health (SQLite-specific):**
```bash
cip models                        # usage per model
cip findings --rule DB-MISSING-INDEX
```

**CI (GitHub Actions):**
```yaml
- run: |
    ./install.sh .
    .cip/bin/cip upgrade
    npx vitest run --reporter=json > vt.json || true
    .cip/bin/cip ingest --kind vitest --file vt.json
    .cip/bin/cip gate
```

Findings are **idempotent** (stable IDs) and track status: `open → fixed` happens
automatically when the condition disappears. `dismiss` by deleting the rule from
config: `[audit] ignore_rules = ["QA-CONSOLE"]`.
````

### 1.2 `ontology.json` (REPLACE — v1.1)

```json
{
  "protocol": "cip",
  "version": "1.1.0",
  "id_grammar": "<language>://<path>#<Qualified.name>",
  "chunk_grammar": "<path>#L<start>-L<end>",
  "entities": {
    "File":    { "key": "path" },
    "Symbol":  { "key": "id", "kinds": ["class","function","method","interface","type","const","module","test"] },
    "Chunk":   { "key": "id" },
    "Commit":  { "key": "sha" },
    "Signal":  { "key": "id", "kinds": ["test_pass","test_fail","type_error","build_error","coverage","custom","eslint"] },
    "Summary": { "key": "id", "kinds": ["repo","dir","file","symbol"] },
    "Route":   { "key": "path", "kinds": ["api","page","layout"], "note": "Next.js App/Pages router" },
    "Model":   { "key": "name", "note": "Prisma schema model with usage stats" },
    "Finding": { "key": "id", "severities": ["critical","high","medium","low","info"],
                 "statuses": ["open","fixed","dismissed"],
                 "note": "audit rule output; stable IDs, auto-fixed detection" }
  },
  "relationships": {
    "contains":   { "from": "File",   "to": "Symbol" },
    "exports":    { "from": "File",   "to": "Symbol" },
    "imports":    { "from": "File",   "to": "File" },
    "calls":      { "from": "Symbol", "to": "Symbol" },
    "references": { "from": "Symbol", "to": "Symbol" },
    "extends":    { "from": "Symbol", "to": "Symbol" },
    "implements": { "from": "Symbol", "to": "Symbol" },
    "tested_by":  { "from": "Symbol", "to": "File" },
    "modified_by":{ "from": "File",   "to": "Commit" },
    "co_change":  { "from": "File",   "to": "File" },
    "uses_model": { "from": "Symbol", "to": "Model", "note": "prisma.<model>.<op>() call sites" },
    "serves":     { "from": "Route",  "to": "File" },
    "flagged_in": { "from": "Finding","to": "File|Symbol" }
  },
  "intents": ["symbol","search","architecture","history","health","tests","quality","impact"],
  "envelope": {
    "ok": "bool", "tool": "string", "result": "object",
    "next_ops": "string[]",
    "index": { "fresh": "bool", "lag_s": "number", "files": "integer" }
  },
  "tools": ["search","symbol","graph","context","summary","map","describe",
            "broken","hotspots","history","route","git_index","index_status",
            "audit","findings","refactors","impact","routes","models"],
  "freshness": { "stale_after_s": 300, "enforced_by": ["git-hooks","watcher","daemon"] },
  "self_description": "GET /ontology.json · describe(entity) · cip tools --schema"
}
```

### 1.3 `AGENTS.md` (REPLACE — v1.1; adds Quality & DevOps section)

````markdown
# AGENTS.md — Code Intelligence Bootstrap (CIP v1.1 + Stack Pack)

This repository runs **CIP**: a continuously updated model of the codebase —
structure, history, tests, runtime health, and a semantic audit layer for the
TS/Next.js/Prisma/SQLite stack. Do NOT read the whole repo. Interrogate the index.

## Workflow (before any change)
1. `cip search "<intent>"`  → candidates + detected intent
2. `cip symbol <Name>`      → definition + relationship counts
3. `cip impact <file>`      → blast radius BEFORE editing (dependents, routes, tests, risk)
4. `cip context "<intent>"` → budgeted pack: code + summary + relations + tests + failures
5. Read exact source only where the index points.

## Quality & DevOps (this repo is stack-audited)
- `cip audit`      → refresh findings (secrets, N+1, missing indexes, client leaks…)
- `cip refactors`  → ranked quick wins (fix these first)
- `cip findings --severity critical` → must-fix list
- `cip broken`     → failing tests + type errors right now
- `cip gate`       → merge gate; if it fails, fix before committing
- `cip routes` / `cip models` → route inventory, Prisma usage, orphans (hidden features)
- After your change: re-run `cip audit`; findings that disappeared auto-close as `fixed`.

## Architecture-first questions
`cip map` · `cip summary [path]` · `cip hotspots` · `cip history <path>`

## Rules
- Index = authoritative for STRUCTURE. Source = authoritative for IMPLEMENTATION.
- If `"fresh": false` → `cip sync` first.
- Never delete a `HIDDEN-*` finding's target without checking `cip impact` and git history.
- Self-introspection: `cip describe <Entity>` · `cip tools --schema`.

## Tools
CLI/MCP (`cip mcp`) / HTTP (`cip serve`): search, symbol, graph, context, summary, map,
describe, broken, hotspots, history, route, git_index, index_status, audit, findings,
refactors, impact, routes, models. Every response includes `next_ops` — follow them.
````

### 1.4 `config.toml` (APPEND)

```toml
# ---- v1.1 stack pack ----
[audit]
ignore_rules = []        # e.g. ["QA-CONSOLE", "QA-ANY"]
```

---

## 2. New modules — `lib/cipkg/stack/`

### 2.1 `stack/__init__.py`

```python
"""CIP Stack Pack v1.1 — TS/Next.js/Prisma/SQLite dev-cycle intelligence:
audit rules, blast-radius impact, route/model inventories, quality gate."""
__version__ = "1.1.0"
```

### 2.2 `stack/common.py`

```python
"""Stack-pack schema: findings, routes, models, model_usage.
Tables are ensured lazily — no edits to core store.py required."""

STACK_SCHEMA = """
CREATE TABLE IF NOT EXISTS findings(
  id TEXT PRIMARY KEY, rule TEXT, severity TEXT,
  path TEXT, line INTEGER, symbol_id TEXT,
  title TEXT, detail TEXT, suggestion TEXT, effort TEXT,
  ts REAL, status TEXT DEFAULT 'open');
CREATE INDEX IF NOT EXISTS idx_find_rule ON findings(rule);
CREATE INDEX IF NOT EXISTS idx_find_path ON findings(path);
CREATE INDEX IF NOT EXISTS idx_find_status ON findings(status);

CREATE TABLE IF NOT EXISTS routes(
  path TEXT PRIMARY KEY, file TEXT, kind TEXT,
  methods TEXT, client INTEGER DEFAULT 0);

CREATE TABLE IF NOT EXISTS models(
  name TEXT PRIMARY KEY, fields TEXT, indexes TEXT, source TEXT);

CREATE TABLE IF NOT EXISTS model_usage(
  model TEXT, operation TEXT, symbol_id TEXT, path TEXT,
  PRIMARY KEY(model, operation, symbol_id, path));
"""

def ensure(con):
    con.executescript(STACK_SCHEMA)
```

### 2.3 `stack/prisma.py`

```python
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
```

### 2.4 `stack/nextjs.py`

```python
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
```

### 2.5 `stack/rules.py` — the 24-rule engine

```python
"""Audit rule engine. Each rule is a pure function over the CIP index + source,
returning Finding dicts. Rules are idempotent, cheap, and fail in isolation."""
import ast, os, re
from ..base import is_test_path

def F(rule, severity, path, title, detail="", suggestion="", effort="small",
      line=0, symbol_id=None):
    return {"rule": rule, "severity": severity, "path": path, "line": line,
            "symbol_id": symbol_id, "title": title, "detail": detail,
            "suggestion": suggestion, "effort": effort}

def _read(root, rel):
    try:
        return open(os.path.join(root, rel), encoding="utf-8", errors="replace").read()
    except OSError:
        return ""

def _ts_files(con):
    return [r["path"] for r in con.execute(
        "SELECT path FROM files WHERE language IN ('typescript','javascript')")]

ENTRY_BASENAMES = {"page.tsx", "page.jsx", "page.js", "route.ts", "route.js",
                   "layout.tsx", "layout.jsx", "middleware.ts", "instrumentation.ts",
                   "next.config.js", "next.config.mjs", "next.config.ts"}

# ---------------- hidden features ----------------

def rule_hidden_export(con, root, cfg):
    out = []
    rows = con.execute("""
        SELECT s.id, s.name, s.path FROM symbols s
        JOIN files f ON f.path = s.path
        WHERE f.language IN ('typescript','javascript')
          AND s.signature LIKE 'export%'
          AND s.kind IN ('class','function','interface','type')
          AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.dst = s.id
                          AND e.kind IN ('calls','references'))""").fetchall()
    for s in rows:
        if os.path.basename(s["path"]) in ENTRY_BASENAMES: continue
        if is_test_path(s["path"], cfg): continue
        if s["path"].endswith((".tsx", ".jsx")) and s["name"][:1].isupper(): continue  # JSX usage invisible to parser
        out.append(F("HIDDEN-EXPORT", "low", s["path"],
                     f"Exported symbol '{s['name']}' is never referenced",
                     detail=s["id"], symbol_id=s["id"],
                     suggestion="Hidden feature or dead code: delete it, or document/expose it.",
                     effort="trivial"))
    return out[:200]

def rule_hidden_route(con, root, cfg):
    from .nextjs import route_referenced
    out = []
    for r in con.execute("SELECT path, file FROM routes WHERE kind='api'"):
        if not route_referenced(con, root, r["path"]):
            out.append(F("HIDDEN-ROUTE", "medium", r["file"],
                         f"API route {r['path']} is never called from this codebase",
                         suggestion="Check for external callers; otherwise delete or document (hidden feature)."))
    return out

def rule_hidden_model(con, root, cfg):
    out = []
    for m in con.execute("SELECT name FROM models"):
        c = con.execute("SELECT COUNT(*) c FROM model_usage WHERE model=?",
                        (m["name"],)).fetchone()["c"]
        if c == 0:
            out.append(F("HIDDEN-MODEL", "medium", "prisma/schema.prisma",
                         f"Prisma model '{m['name']}' has no usage in code",
                         suggestion="Buried backend feature or leftover: remove from schema or find its consumers."))
    return out

# ---------------- prisma / sqlite ----------------

N1_RE = re.compile(r"(?:for\s*\(|\.map\s*\(|\.forEach\s*\()[\s\S]{0,200}?"
                   r"await\s+prisma\.(\w+)\.(?:findFirst|findMany|findUnique)\s*\(")

def rule_db_n1(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        src = _read(root, rel)
        for m in N1_RE.finditer(src):
            ln = src.count("\n", 0, m.start()) + 1
            out.append(F("DB-N1", "high", rel,
                         f"Probable N+1: prisma.{m.group(1)} query inside a loop",
                         suggestion="Batch it: one query with `in:`/include, then map in memory.",
                         effort="small", line=ln))
    return out[:100]

def rule_db_missing_index(con, root, cfg):
    from .prisma import where_fields
    wf = where_fields(con, root)
    models = {r["name"]: r for r in con.execute("SELECT name, fields, indexes FROM models")}
    out = []
    for model, used in wf.items():
        m = models.get(model)
        if not m: continue
        try:
            field_names = ast.literal_eval(m["fields"])
            indexed = {c for combo in ast.literal_eval(m["indexes"]) for c in combo}
        except Exception:
            continue
        for f in sorted(used):
            if f in field_names and f not in indexed:
                out.append(F("DB-MISSING-INDEX", "medium", "prisma/schema.prisma",
                             f"{model}.{f} is filtered in where: but has no index",
                             detail="SQLite does a full table scan for this.",
                             suggestion=f"Add @@index([{f}]) to model {model}, then `prisma migrate dev`.",
                             effort="trivial"))
    return out

def rule_db_no_await(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        for i, line in enumerate(_read(root, rel).splitlines()):
            s = line.strip()
            if "prisma." not in s or "(" not in s: continue
            if s.startswith(("//", "*", "/*")): continue
            if any(k in s for k in ("await", "return", "=", "then(", "=>", "yield", "void")): continue
            out.append(F("DB-NO-AWAIT", "high", rel,
                         "Prisma call without await/return",
                         suggestion="Add await/return — unawaited promises swallow errors.",
                         effort="trivial", line=i + 1))
    return out[:50]

def rule_db_destructive_migration(con, root, cfg):
    out = []
    mdir = os.path.join(root, "prisma", "migrations")
    if not os.path.isdir(mdir):
        return out
    for dirpath, _dirs, files in os.walk(mdir):
        for fn in files:
            if not fn.endswith(".sql"): continue
            p = os.path.join(dirpath, fn)
            try: text = open(p, encoding="utf-8", errors="replace").read()
            except OSError: continue
            for m in re.finditer(r"(?i)\bDROP\s+(TABLE|COLUMN)\b", text):
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                out.append(F("DB-DESTRUCTIVE-MIGRATION", "high", rel,
                             f"Destructive migration: DROP {m.group(1).upper()}",
                             suggestion="Confirm data loss is intended; back up SQLite DB before applying."))
    return out[:30]

def rule_db_schema_drift(con, root, cfg):
    from .prisma import find_schema
    rel = find_schema(root)
    if not rel: return []
    sp = os.path.join(root, rel)
    mdir = os.path.join(os.path.dirname(sp), "migrations")
    if not os.path.isdir(mdir): return []
    try:
        newest = max(os.path.getmtime(os.path.join(mdir, d)) for d in os.listdir(mdir))
    except ValueError:
        return []
    if os.path.getmtime(sp) > newest:
        return [F("DB-SCHEMA-DRIFT", "medium", rel,
                  "schema.prisma changed since the last migration",
                  suggestion="Run `prisma migrate dev` (or `migrate diff`) to reconcile.",
                  effort="trivial")]
    return []

# ---------------- security / env ----------------

SECRET_RES = [
    (re.compile(r"sk_live_[A-Za-z0-9]{10,}"), "Stripe live key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"(?:postgres|mysql|mongodb)(?:\+srv)?://[^/\s:]+:[^@\s]+@"), "connection string with password"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9\-]{10,}"), "GitHub/Slack token"),
    (re.compile(r"""(?:password|passwd|secret|apiKey|api_key)\s*[:=]\s*['"][^'"]{6,}['"]""", re.I), "hardcoded credential"),
]

def rule_secrets(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        if any(x in rel.lower() for x in ("test", "fixture", "mock", ".env")): continue
        for i, line in enumerate(_read(root, rel).splitlines()):
            if "process.env" in line or "example" in line.lower(): continue
            for rx, label in SECRET_RES:
                if rx.search(line):
                    out.append(F("SEC-HARDCODED-SECRET", "critical", rel,
                                 f"Hardcoded secret: {label}",
                                 suggestion="Rotate this credential NOW; move to env/secret manager.",
                                 effort="trivial", line=i + 1))
    return out[:30]

def rule_sql_raw(con, root, cfg):
    out = []
    rx = re.compile(r"\$(?:query|execute)RawUnsafe")
    for rel in _ts_files(con):
        src = _read(root, rel)
        for m in rx.finditer(src):
            ln = src.count("\n", 0, m.start()) + 1
            out.append(F("SEC-SQL-RAW", "high", rel,
                         "Raw SQL without parameterization (…RawUnsafe)",
                         suggestion="Use prisma.$queryRaw`` tagged templates or parameter binding.",
                         effort="small", line=ln))
    return out[:30]

ENV_USE_RE = re.compile(r"process\.env\.([A-Z_][A-Z0-9_]*)")
SKIP_ENV = {"NODE_ENV", "CI", "PORT", "TZ", "VERCEL_ENV", "VERCEL_URL", "NEXT_RUNTIME"}

def _env_defined(root):
    keys = set()
    for f in (".env", ".env.local", ".env.development", ".env.production", ".env.example"):
        p = os.path.join(root, f)
        if os.path.exists(p):
            for line in open(p, encoding="utf-8", errors="replace"):
                m = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=", line)
                if m: keys.add(m.group(1))
    return keys

def rule_env(con, root, cfg):
    defined = _env_defined(root)
    used = {}
    for rel in _ts_files(con):
        src = _read(root, rel)
        for m in ENV_USE_RE.finditer(src):
            k = m.group(1)
            if k not in used:
                used[k] = (rel, src.count("\n", 0, m.start()) + 1)
    out = []
    for k, (p, ln) in used.items():
        if k in SKIP_ENV: continue
        if k not in defined:
            out.append(F("ENV-UNDEFINED", "high", p,
                         f"process.env.{k} is used but defined in no .env*",
                         suggestion=f"Add {k} to .env / deployment secrets (crashes or silent undefined in prod).",
                         effort="trivial", line=ln))
    for k in sorted(defined - set(used)):
        out.append(F("ENV-UNREAD", "low", ".env",
                     f"{k} is defined but never read", effort="trivial"))
    return out

# ---------------- next.js ----------------

def _server_spec(spec):
    for s in ("@prisma/client", "server-only", "fs", "node:fs",
              "child_process", "node:child_process"):
        if spec == s: return s
    for s in ("prisma", "lib", "server"):
        parts = spec.split("/")
        if s in parts and ("db" in parts or s != "lib"):
            if s == "lib" and "db" not in parts: continue
            return spec
    return None

def rule_next_client_leak(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        src = _read(root, rel)
        if not re.match(r"""^\s*['"]use client['"]""", src): continue
        for m in re.finditer(r"""from\s+['"]([^'"]+)['"]""", src):
            hit = _server_spec(m.group(1))
            if hit:
                ln = src.count("\n", 0, m.start()) + 1
                out.append(F("NEXT-CLIENT-LEAK", "high", rel,
                             f'Client component imports server module "{m.group(1)}"',
                             suggestion="Move data access to a server component/API route; pass props down.",
                             effort="small", line=ln))
    return out[:50]

def rule_route_no_error(con, root, cfg):
    out = []
    for r in con.execute("SELECT file, path FROM routes WHERE kind='api'"):
        src = _read(root, r["file"])
        if "GET" not in src and "POST" not in src: continue
        if "try" not in src or "catch" not in src:
            out.append(F("NEXT-ROUTE-NO-ERROR", "medium", r["file"],
                         f"API route {r['path']} has no try/catch",
                         suggestion="Wrap handlers; return NextResponse.json({ error }, { status: 500 }).",
                         effort="trivial"))
    return out

def rule_action_no_validate(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        src = _read(root, rel)
        if not re.search(r"""['"]use server['"]""", src): continue
        if not re.search(r"zod|safeParse|\.parse\(", src):
            out.append(F("NEXT-ACTION-NO-VALIDATE", "medium", rel,
                         "Server action without input validation",
                         suggestion="Validate with zod/parse before touching the DB — server actions are public endpoints.",
                         effort="small"))
    return out[:30]

# ---------------- quality / architecture ----------------

def rule_qa_any(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        src = _read(root, rel)
        n = len(re.findall(r":\s*any\b|as\s+any\b", src))
        if n > 10:
            out.append(F("QA-ANY", "low", rel, f"{n} uses of `any`",
                         suggestion="Type the top offenders; `any` defeats every other safety layer."))
    return out[:30]

def rule_qa_tsignore(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        src = _read(root, rel)
        n = src.count("@ts-ignore") + src.count("@ts-expect-error")
        if n > 5:
            out.append(F("QA-TSIGNORE", "low", rel, f"{n} suppressed type errors",
                         suggestion="Each suppression hides a potential runtime bug; triage them."))
    return out[:30]

def rule_qa_console(con, root, cfg):
    out = []
    for rel in _ts_files(con):
        if is_test_path(rel, cfg): continue
        n = _read(root, rel).count("console.log")
        if n > 5:
            out.append(F("QA-CONSOLE", "low", rel, f"{n} console.log calls",
                         suggestion="Replace with a logger or remove before shipping."))
    return out[:30]

def rule_qa_dup(con, root, cfg):
    out = []
    rows = con.execute("""SELECT body_hash, COUNT(*) c, GROUP_CONCAT(id, ' | ') ids
                          FROM symbols WHERE body_hash IS NOT NULL AND length(body) > 80
                          GROUP BY body_hash HAVING c > 1 LIMIT 30""").fetchall()
    for r in rows:
        ids = r["ids"].split(" | ")
        paths = sorted({i.split("://", 1)[-1].split("#")[0] for i in ids})
        if len(paths) < 2: continue
        out.append(F("QA-DUP", "low", paths[0],
                     f"Identical implementation in {len(paths)} places",
                     detail=", ".join(paths[:4]),
                     suggestion="Extract a shared helper — duplicated logic drifts into bugs.",
                     effort="small"))
    return out

def rule_qa_circular(con, root, cfg):
    adj = {}
    for e in con.execute("SELECT src, dst FROM edges WHERE kind='imports'"):
        adj.setdefault(e["src"], set()).add(e["dst"])
    cycles, seen = [], set()
    def dfs(node, path):
        if len(path) > 6: return
        for nxt in list(adj.get(node, ()))[:20]:
            if nxt in path:
                i = path.index(nxt)
                key = tuple(sorted(path[i:]))
                if key not in seen:
                    seen.add(key)
                    cycles.append(path[i:] + [nxt])
            else:
                dfs(nxt, path + [nxt])
    for n in list(adj)[:400]:
        dfs(n, [n])
    return [F("QA-CIRCULAR", "medium", c[0],
              "Circular import: " + " → ".join(c[:6]),
              suggestion="Break the cycle: shared code moves down a layer, or use events/interfaces.",
              effort="medium") for c in cycles[:20]]

def rule_qa_god_module(con, root, cfg):
    out = []
    rows = con.execute("""
        SELECT f.path, f.lines,
               (SELECT COUNT(*) FROM symbols s WHERE s.path = f.path) sc,
               (SELECT COUNT(*) FROM edges e WHERE e.dst = f.path AND e.kind='imports') fi
        FROM files f WHERE f.language IN ('typescript','javascript')
          AND f.lines > 600""").fetchall()
    for r in rows:
        if r["sc"] > 15 or r["fi"] > 8:
            out.append(F("QA-GOD-MODULE", "medium", r["path"],
                         f"God module: {r['lines']} lines, {r['sc']} symbols, fan-in {r['fi']}",
                         suggestion="Split by responsibility; high fan-in + size = merge-conflict and bug magnet.",
                         effort="large"))
    return out[:30]

def rule_qa_untested_hot(con, root, cfg):
    out = []
    rows = con.execute("""
        SELECT s.id, s.name, s.path, COUNT(e.src) c FROM symbols s
        JOIN edges e ON e.dst = s.id AND e.kind IN ('calls','references')
        WHERE NOT EXISTS (SELECT 1 FROM edges t WHERE t.src = s.id AND t.kind='tested_by')
        GROUP BY s.id HAVING c >= 5 ORDER BY c DESC LIMIT 30""").fetchall()
    for r in rows:
        out.append(F("QA-UNTESTED-HOT", "medium", r["path"],
                     f"'{r['name']}' has {r['c']} dependents but no tests",
                     detail=r["id"], symbol_id=r["id"],
                     suggestion="Add at least one test before modifying — this is load-bearing code.",
                     effort="small"))
    return out

def rule_layer_violation(con, root, cfg):
    out, seen = [], set()
    LOW = ("lib/", "src/lib/", "packages/", "server/")
    HIGH = ("app/", "pages/", "src/app/", "src/pages/", "components/", "src/components/")
    for e in con.execute("SELECT src, dst FROM edges WHERE kind='imports'"):
        s, d = e["src"], e["dst"]
        if s.startswith(LOW) and d.startswith(HIGH) and (s, d) not in seen:
            seen.add((s, d))
            out.append(F("ARCH-LAYER-VIOLATION", "medium", s,
                         f"Library layer imports UI layer: {d}",
                         suggestion="Invert the dependency — UI calls lib, never the reverse.",
                         effort="medium"))
    return out[:50]

def rule_orphan_file(con, root, cfg):
    out = []
    rows = con.execute("""
        SELECT f.path FROM files f
        WHERE f.language IN ('typescript','javascript')
          AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.dst = f.path AND e.kind='imports')""").fetchall()
    for r in rows:
        p = r["path"]
        base = os.path.basename(p)
        if base in ENTRY_BASENAMES or is_test_path(p, cfg): continue
        if base.startswith("index.") or base.endswith((".d.ts", ".config.ts", ".config.js")): continue
        out.append(F("ARCH-ORPHAN-FILE", "low", p,
                     "File is imported by nothing",
                     suggestion="Hidden feature or dead file — verify, then delete or wire up.",
                     effort="trivial"))
    return out[:100]

RULES = [
    ("SEC-HARDCODED-SECRET", rule_secrets), ("SEC-SQL-RAW", rule_sql_raw),
    ("ENV", rule_env),
    ("NEXT-CLIENT-LEAK", rule_next_client_leak),
    ("DB-N1", rule_db_n1), ("DB-MISSING-INDEX", rule_db_missing_index),
    ("DB-NO-AWAIT", rule_db_no_await),
    ("DB-DESTRUCTIVE-MIGRATION", rule_db_destructive_migration),
    ("DB-SCHEMA-DRIFT", rule_db_schema_drift),
    ("HIDDEN-EXPORT", rule_hidden_export), ("HIDDEN-ROUTE", rule_hidden_route),
    ("HIDDEN-MODEL", rule_hidden_model),
    ("NEXT-ROUTE-NO-ERROR", rule_route_no_error),
    ("NEXT-ACTION-NO-VALIDATE", rule_action_no_validate),
    ("QA-ANY", rule_qa_any), ("QA-TSIGNORE", rule_qa_tsignore),
    ("QA-CONSOLE", rule_qa_console), ("QA-DUP", rule_qa_dup),
    ("QA-CIRCULAR", rule_qa_circular), ("QA-GOD-MODULE", rule_qa_god_module),
    ("QA-UNTESTED-HOT", rule_qa_untested_hot),
    ("ARCH-LAYER-VIOLATION", rule_layer_violation),
    ("ARCH-ORPHAN-FILE", rule_orphan_file),
]

def run_rules(con, root, cfg):
    skip = set(cfg.get("audit", {}).get("ignore_rules", []))
    findings = []
    for rid, fn in RULES:
        if rid in skip: continue
        try:
            findings.extend(fn(con, root, cfg))
        except Exception as e:
            findings.append(F(rid, "info", "", f"rule {rid} failed: {e}"))
    return findings
```

### 2.6 `stack/audit.py` — orchestration, reports, gate

```python
"""Audit orchestration: run rules → upsert findings (stable IDs, auto-fix),
quick wins, markdown reports, eslint ingestion, CI gate."""
import hashlib, json, os, sys, time
from ..base import repo_root, load_config
from ..store import connect
from .common import ensure
from . import rules as R
from . import nextjs, prisma

def _fid(f):
    return hashlib.sha1(
        f"{f['rule']}:{f['path']}:{f['line']}:{f['title']}".encode()).hexdigest()[:16]

def audit(root=None, refresh=True):
    root = root or repo_root(); cfg = load_config(root); con = connect(root)
    ensure(con)
    if refresh:
        try: nextjs.index_routes(con, root)
        except Exception: pass
        try: prisma.index_stack(con, root)
        except Exception: pass
    findings = R.run_rules(con, root, cfg)
    seen = set()
    for f in findings:
        fid = _fid(f); seen.add(fid)
        con.execute(
            "INSERT INTO findings(id,rule,severity,path,line,symbol_id,title,detail,"
            "suggestion,effort,ts,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,'open') "
            "ON CONFLICT(id) DO UPDATE SET severity=excluded.severity, title=excluded.title, "
            "detail=excluded.detail, suggestion=excluded.suggestion, "
            "effort=excluded.effort, ts=excluded.ts",
            (fid, f["rule"], f["severity"], f["path"], f["line"], f["symbol_id"],
             f["title"], f["detail"], f["suggestion"], f["effort"], time.time()))
    if seen:
        ph = ",".join("?" * len(seen))
        con.execute(f"UPDATE findings SET status='fixed' "
                    f"WHERE status='open' AND id NOT IN ({ph})", list(seen))
    con.commit()
    return summarize(con)

def summarize(con):
    rows = con.execute("SELECT severity, COUNT(*) c FROM findings "
                       "WHERE status='open' GROUP BY severity").fetchall()
    by = {r["severity"]: r["c"] for r in rows}
    return {"open": sum(by.values()), "by_severity": by,
            "critical": by.get("critical", 0), "high": by.get("high", 0)}

def findings(root=None, severity=None, rule=None, path=None, limit=100):
    con = connect(root or repo_root()); ensure(con)
    q, args = "SELECT * FROM findings WHERE status='open'", []
    if severity: q += " AND severity=?"; args.append(severity)
    if rule:     q += " AND rule=?";     args.append(rule)
    if path:     q += " AND path LIKE ?"; args.append(f"%{path}%")
    q += (" ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
          "WHEN 'medium' THEN 2 ELSE 3 END, rule LIMIT ?")
    args.append(limit)
    return [dict(r) for r in con.execute(q, args)]

def quick_wins(root=None, limit=10):
    con = connect(root or repo_root()); ensure(con)
    rows = con.execute(
        "SELECT * FROM findings WHERE status='open' AND suggestion != '' "
        "AND severity IN ('critical','high','medium') AND effort IN ('trivial','small') "
        "ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END, "
        "CASE effort WHEN 'trivial' THEN 0 ELSE 1 END LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

def ingest_eslint(root, file_path):
    root = root or repo_root(); con = connect(root); ensure(con)
    text = sys.stdin.read() if file_path == "-" else open(file_path, encoding="utf-8").read()
    data = json.loads(text)
    n = 0
    for fr in data:
        rel = os.path.relpath(fr.get("filePath", ""), root).replace(os.sep, "/")
        for msg in fr.get("messages", []):
            f = {"rule": f"ESLINT:{msg.get('ruleId') or 'parse'}",
                 "severity": "high" if msg.get("severity", 1) == 2 else "low",
                 "path": rel, "line": msg.get("line", 0), "symbol_id": None,
                 "title": msg.get("message", "")[:200], "detail": "",
                 "suggestion": "", "effort": "small"}
            con.execute(
                "INSERT INTO findings(id,rule,severity,path,line,symbol_id,title,detail,"
                "suggestion,effort,ts,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,'open') "
                "ON CONFLICT(id) DO UPDATE SET ts=excluded.ts",
                (_fid(f), f["rule"], f["severity"], f["path"], f["line"], None,
                 f["title"], "", "", f["effort"], time.time()))
            n += 1
    con.commit()
    return {"ingested": n, "kind": "eslint"}

def report_markdown(root=None):
    root = root or repo_root(); con = connect(root); ensure(con)
    s = summarize(con)
    lines = ["# CIP Stack Audit", "",
             f"Open findings: **{s['open']}** — " +
             ", ".join(f"{v} {k}" for k, v in sorted(s["by_severity"].items())), ""]
    for sev in ("critical", "high", "medium", "low"):
        rows = con.execute("SELECT * FROM findings WHERE status='open' AND severity=? "
                           "ORDER BY rule LIMIT 25", (sev,)).fetchall()
        if not rows: continue
        lines += [f"## {sev.title()} ({len(rows)})", ""]
        for r in rows:
            loc = r["path"] + (f":{r['line']}" if r["line"] else "")
            lines.append(f"- **[{r['rule']}]** `{loc}` — {r['title']}")
            if r["suggestion"]:
                lines.append(f"  - fix: {r['suggestion']} *(effort: {r['effort']})*")
        lines.append("")
    qw = quick_wins(root, limit=10)
    if qw:
        lines += ["## Quick wins", "",
                  "| Rule | Location | Fix | Effort |", "|---|---|---|---|"]
        for q in qw:
            lines.append(f"| {q['rule']} | `{q['path']}` | {q['suggestion'][:90]} | {q['effort']} |")
    return "\n".join(lines) + "\n"

def gate(root=None):
    """CI/pre-commit quality gate: exit non-zero on criticals or broken signals."""
    root = root or repo_root()
    from .. import indexer
    from ..runtime_adapters import broken
    indexer.sync(root)
    stats = audit(root, refresh=True)
    fails = len(broken(root)["signals"])
    reasons = []
    if stats.get("critical", 0):
        reasons.append(f"{stats['critical']} critical findings")
    if fails:
        reasons.append(f"{fails} failing test/type signals")
    return {"ok": not reasons, "reasons": reasons,
            "findings": stats, "broken_signals": fails}
```

### 2.7 `stack/impact.py` — blast radius

```python
"""Blast-radius analysis: transitive dependents, affected routes, tests to run,
risk level — for a file, a symbol, or an entire git diff (PR mode)."""
import subprocess
from ..base import repo_root
from ..store import connect
from .common import ensure

def _to_file(con, node):
    if "://" in node:
        r = con.execute("SELECT path FROM symbols WHERE id=?", (node,)).fetchone()
        return r["path"] if r else None
    return node

def _dependents(con, seed_files, depth=2):
    frontier, seen = set(seed_files), set(seed_files)
    for _ in range(max(1, min(depth, 3))):
        nxt = set()
        for f in frontier:
            for r in con.execute(
                    "SELECT src FROM edges WHERE dst=? AND kind IN ('imports','calls','references')",
                    (f,)):
                p = _to_file(con, r["src"])
                if p and p not in seen:
                    seen.add(p); nxt.add(p)
        frontier = nxt
    return seen

def impact(root=None, target="", depth=2):
    root = root or repo_root(); con = connect(root); ensure(con)
    seed = set()
    if con.execute("SELECT 1 FROM files WHERE path=?", (target,)).fetchone():
        seed.add(target)
    else:
        sym = con.execute("SELECT path FROM symbols WHERE id=? OR name=? LIMIT 1",
                          (target, target)).fetchone()
        if sym: seed.add(sym["path"])
    if not seed:
        return {"error": f"unknown target: {target}"}
    dep = _dependents(con, seed, depth)
    tests = set()
    for r in con.execute("SELECT src, dst FROM edges WHERE kind='tested_by'"):
        s = con.execute("SELECT path FROM symbols WHERE id=?", (r["src"],)).fetchone()
        if s and s["path"] in dep:
            tests.add(r["dst"])
    ph = ",".join("?" * len(dep))
    routes_hit = [dict(r) for r in con.execute(
        f"SELECT path, kind FROM routes WHERE file IN ({ph})", list(dep))]
    findings_hit = con.execute(
        f"SELECT COUNT(*) c FROM findings WHERE status='open' AND path IN ({ph})",
        list(dep)).fetchone()["c"]
    try:
        from ..gitindex import hotspots
        hs = {h["path"]: h["score"] for h in hotspots(root, k=50)}
        heat = max((hs.get(p, 0.0) for p in dep), default=0.0)
    except Exception:
        heat = 0.0
    risk = "low"
    if routes_hit or len(dep) > 8 or findings_hit > 3: risk = "medium"
    if len(dep) > 20 or (routes_hit and heat > 2): risk = "high"
    advice = []
    if risk == "high":
        advice.append("High blast radius: land in small increments; full test pass required.")
    if routes_hit:
        advice.append(f"{len(routes_hit)} route(s) affected — verify API contracts and consumers.")
    if tests:
        advice.append("Run the listed tests before merging.")
    else:
        advice.append("No tests cover this area — add one test for the changed behavior first.")
    return {"target": target, "risk": risk,
            "seed_files": sorted(seed),
            "affected_files": sorted(dep)[:50], "affected_count": len(dep),
            "tests_to_run": sorted(tests)[:20],
            "routes_affected": routes_hit[:10],
            "open_findings_in_area": findings_hit,
            "hotspot_heat": round(heat, 1), "advice": advice}

def impact_diff(root=None, ref="HEAD"):
    root = root or repo_root()
    try:
        out = subprocess.run(["git", "diff", "--name-only", ref],
                             cwd=root, capture_output=True, text=True, timeout=30)
    except Exception as e:
        return {"error": str(e)}
    files = [l.strip() for l in out.stdout.splitlines() if l.strip()]
    union, all_tests, all_routes, worst = set(), set(), [], "low"
    order = {"low": 0, "medium": 1, "high": 2}
    for f in files[:20]:
        r = impact(root, f)
        if "error" in r: continue
        union.update(r["affected_files"])
        all_tests.update(r["tests_to_run"])
        all_routes += r["routes_affected"]
        if order[r["risk"]] > order[worst]: worst = r["risk"]
    return {"base": ref, "changed_files": files,
            "risk": worst, "affected_count": len(union),
            "affected_files": sorted(union)[:60],
            "tests_to_run": sorted(all_tests)[:25],
            "routes_affected": all_routes[:10]}
```

### 2.8 `stack/selftest.py`

```python
"""Stack-pack self-test: fixture Next.js+Prisma repo with planted defects."""
import os, shutil, tempfile, unittest

SCHEMA = """
model User {
  id    String @id
  email String
  posts Post[]
}

model Post {
  id    String @id
  title String
}
"""
ROUTE = """import { prisma } from "@/lib/db";

export async function GET() {
  const users = await prisma.user.findMany();
  return Response.json(users);
}
"""
CLIENT = """"use client";
import { prisma } from "@prisma/client";

export default function Dashboard() { return null; }
"""
USERS = """import { prisma } from "@/lib/db";

export async function loadUsers(ids: string[]) {
  const out: unknown[] = [];
  for (const id of ids) {
    const u = await prisma.user.findUnique({ where: { id } });
    out.push(u);
  }
  const first = await prisma.user.findFirst({ where: { email: "x@y.z" } });
  return { out, first };
}
"""
CONFIG = """export const stripeKey = "sk_live_abcdefghijklmnop1234";
export const dbUrl = "postgres://admin:hunter22@db.internal/app";
export const flag = process.env.MISSING_VAR;
"""

class StackPack(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cip-stacktest-")
        os.makedirs(os.path.join(self.root, ".cip", "data"))
        os.makedirs(os.path.join(self.root, "prisma"))
        os.makedirs(os.path.join(self.root, "app", "api", "users"))
        os.makedirs(os.path.join(self.root, "components"))
        os.makedirs(os.path.join(self.root, "lib"))
        w = lambda p, t: open(os.path.join(self.root, p), "w").write(t)
        w("prisma/schema.prisma", SCHEMA)
        w("app/api/users/route.ts", ROUTE)
        w("components/Dashboard.tsx", CLIENT)
        w("lib/users.ts", USERS)
        w("lib/config.ts", CONFIG)
        from .. import indexer
        indexer.sync(self.root, full=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_audit_detects_planted_defects(self):
        from . import audit as sa
        stats = sa.audit(self.root)
        self.assertGreater(stats["open"], 0)
        found = {f["rule"] for f in sa.findings(self.root, limit=500)}
        for expected in ("DB-N1", "NEXT-CLIENT-LEAK", "SEC-HARDCODED-SECRET",
                         "DB-MISSING-INDEX", "NEXT-ROUTE-NO-ERROR",
                         "HIDDEN-MODEL", "ENV-UNDEFINED"):
            self.assertIn(expected, found, f"missing rule output: {expected}")
        self.assertGreaterEqual(stats["critical"], 1)

    def test_quick_wins_and_report(self):
        from . import audit as sa
        sa.audit(self.root)
        self.assertTrue(sa.quick_wins(self.root))
        md = sa.report_markdown(self.root)
        self.assertIn("# CIP Stack Audit", md)

    def test_models_and_routes(self):
        from . import prisma as sp, nextjs as sn
        m = sp.models_report(self.root)
        names = {x["model"]: x for x in m["models"]}
        self.assertIn("User", names); self.assertIn("Post", names)
        self.assertTrue(names["Post"]["orphan"])
        self.assertFalse(names["User"]["orphan"])
        routes = sn.list_routes(self.root)
        self.assertTrue(any(r["path"] == "/api/users" for r in routes))

    def test_impact(self):
        from . import impact as si
        r = si.impact(self.root, target="lib/users.ts")
        self.assertNotIn("error", r)
        self.assertIn("lib/users.ts", r["affected_files"])

def run_stack_selftest():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StackPack)
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if res.wasSuccessful() else 1
```

---

## 3. Patches to v1.0 files (exact anchors)

### 3.1 `cli.py` — 4 edits

**Edit 1** — after `sub.add_parser("selftest")` add:

```python
    # ---- v1.1 stack pack ----
    ap = sub.add_parser("audit", help="run TS/Next/Prisma audit rules")
    ap.add_argument("--md", help="write markdown report to file")
    ap.add_argument("--no-refresh", action="store_true")
    fp = sub.add_parser("findings")
    fp.add_argument("--severity"); fp.add_argument("--rule"); fp.add_argument("--path")
    fp.add_argument("--limit", type=int, default=100)
    sub.add_parser("refactors", help="top quick-win refactors")
    mp = sub.add_parser("impact"); mp.add_argument("target", nargs="?")
    mp.add_argument("--ref"); mp.add_argument("--depth", type=int, default=2)
    sub.add_parser("routes"); sub.add_parser("models")
    sub.add_parser("gate", help="quality gate: exit 1 on critical findings/broken signals")
```

**Edit 2** — replace the `ingest` parser lines:

```python
    ig = sub.add_parser("ingest"); ig.add_argument("--kind", required=True,
        choices=["vitest", "jest", "pytest", "tsc", "generic", "eslint"])
    ig.add_argument("--file", default="-", help="path or '-' for stdin")
```

**Edit 3** — replace the `ingest` dispatch:

```python
    elif a.cmd == "ingest":
        if a.kind == "eslint":
            from .stack import audit as sa; _out(sa.ingest_eslint(root, a.file))
        else:
            from . import runtime_adapters; _out(runtime_adapters.ingest(root, a.kind, a.file))
```

**Edit 4** — replace the `selftest` dispatch and append stack commands before `return 0`:

```python
    elif a.cmd == "selftest":
        from .selftest import run_selftest
        rc = run_selftest()
        from .stack.selftest import run_stack_selftest
        rc2 = run_stack_selftest()
        return rc or rc2
    elif a.cmd == "audit":
        from .stack import audit as sa
        _out(sa.audit(root, refresh=not a.no_refresh))
        if a.md:
            open(a.md, "w").write(sa.report_markdown(root))
            print(f"report written: {a.md}")
    elif a.cmd == "findings":
        from .stack import audit as sa
        _out({"findings": sa.findings(root, severity=a.severity, rule=a.rule,
                                      path=a.path, limit=a.limit)})
    elif a.cmd == "refactors":
        from .stack import audit as sa; _out({"quick_wins": sa.quick_wins(root)})
    elif a.cmd == "impact":
        from .stack import impact as si
        if a.ref: _out(si.impact_diff(root, ref=a.ref))
        elif a.target: _out(si.impact(root, target=a.target, depth=a.depth))
        else: print("usage: cip impact <file|symbol>   |   cip impact --ref origin/main")
    elif a.cmd == "routes":
        from .stack import nextjs as sn; _out({"routes": sn.list_routes(root)})
    elif a.cmd == "models":
        from .stack import prisma as sp; _out(sp.models_report(root))
    elif a.cmd == "gate":
        from .stack import audit as sa
        g = sa.gate(root); _out(g)
        return 0 if g["ok"] else 1
```

### 3.2 `server.py` — 3 edits

**Edit 1** — imports:

```python
from . import retrieve, indexer, summarize, gitindex, runtime_adapters, router
from .stack import audit as stack_audit, impact as stack_impact
from .stack import nextjs as stack_nextjs, prisma as stack_prisma
```

**Edit 2** — insert into `TOOLS` before the closing `]`:

```python
    {"name": "audit", "description": "Run the TS/Next/Prisma/SQLite audit rules; returns finding counts.",
     "inputSchema": {"type": "object", "properties": {"refresh": {"type": "boolean"}}}},
    {"name": "findings", "description": "Query open findings by severity/rule/path.",
     "inputSchema": {"type": "object", "properties": {"severity": {"type": "string"}, "rule": {"type": "string"}, "path": {"type": "string"}, "limit": {"type": "integer"}}}},
    {"name": "refactors", "description": "Top quick-win refactors ranked by severity/effort.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "impact", "description": "Blast radius for a file/symbol, or for a git diff with `ref`.",
     "inputSchema": {"type": "object", "properties": {"target": {"type": "string"}, "ref": {"type": "string"}, "depth": {"type": "integer"}}}},
    {"name": "routes", "description": "Next.js route inventory with referenced/orphan status.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "models", "description": "Prisma model usage report incl. orphan detection.",
     "inputSchema": {"type": "object", "properties": {}}},
```

**Edit 3** — dispatch: insert before `elif name == "index_status":`, and extend `_next_ops` before its `return`:

```python
        elif name == "audit":
            res = stack_audit.audit(root, refresh=bool(args.get("refresh", True)))
        elif name == "findings":
            res = {"findings": stack_audit.findings(root, severity=args.get("severity"),
                   rule=args.get("rule"), path=args.get("path"),
                   limit=int(args.get("limit", 100)))}
        elif name == "refactors":
            res = {"quick_wins": stack_audit.quick_wins(root)}
        elif name == "impact":
            res = (stack_impact.impact_diff(root, ref=args["ref"]) if args.get("ref")
                   else stack_impact.impact(root, target=args.get("target", ""),
                                            depth=int(args.get("depth", 2))))
        elif name == "routes":
            res = {"routes": stack_nextjs.list_routes(root)}
        elif name == "models":
            res = stack_prisma.models_report(root)
```

```python
    # inside _next_ops, before `return ops[:6]`:
    if name == "audit":
        ops += ["refactors()", "findings(severity='critical')"]
    if name == "findings":
        ops += [f"impact(target='{f['path']}')" for f in res.get("findings", [])[:2]]
    if name == "impact":
        ops += ["broken()", "context(query='<planned change>')"]
    if name == "models":
        ops += ["findings(rule='DB-MISSING-INDEX')"]
```

---

## 4. Runbook

```bash
# install into a Next.js repo (v0.9/v1.0 already there → auto-upgrade):
./install.sh /path/to/nextjs-repo && cd /path/to/nextjs-repo
cip upgrade && cip selftest          # core + stack-pack tests both green

# the daily dev-cycle loop:
cip audit --md AUDIT.md              # what's wrong, human-readable
cip refactors                        # what to fix first (severity ÷ effort)
cip impact src/features/auth         # blast radius before touching it
cip impact --ref origin/main         # PR risk summary (paste into the PR)
cip gate                             # hard gate for hooks/CI

# hidden-feature discovery:
cip routes                           # orphan API routes
cip models                           # orphan Prisma models
cip findings --rule HIDDEN-EXPORT

# wire existing tooling into the unified findings stream:
npx eslint . --format json > eslint.json && cip ingest --kind eslint --file eslint.json
npx tsc --noEmit --pretty false > tsc.txt && cip ingest --kind tsc --file tsc.txt
npx vitest run --reporter=json > vt.json  && cip ingest --kind vitest --file vt.json
cip broken                           # everything currently red, one view
```

**What this gives the agent on a massive project:** one compact interface where *"is this safe?"* (`impact`), *"what's broken?"* (`broken` + `findings`), *"what's hiding?"* (`routes`/`models`/`HIDDEN-*`), and *"what should I fix first?"* (`refactors`) are each a single call — no repo reading required, findings auto-close when fixed, and `cip gate` makes the whole thing enforceable in CI.
