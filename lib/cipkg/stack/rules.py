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

def rule_db_migration_index_drift(con, root, cfg):
    """Detect indexes referenced in migrations but missing from current schema.
    
    This catches schema drift where migrations created indexes that were later
    removed from schema.prisma, potentially causing unexpected query performance.
    """
    from .prisma import find_schema, parse_schema
    rel = find_schema(root)
    if not rel: return []
    
    sp = os.path.join(root, rel)
    mdir = os.path.join(os.path.dirname(sp), "migrations")
    if not os.path.isdir(mdir): return []
    
    # Parse current schema
    current_models = parse_schema(_read(root, rel))
    current_indexes = {}
    for model_name, model_data in current_models.items():
        indexes = model_data.get("indexes", [])
        current_indexes[model_name] = set()
        for idx in indexes:
            if isinstance(idx, list):
                current_indexes[model_name].update(idx)
    
    # Scan migration files for index references
    migration_indexes = {}
    for dirpath, dirnames, filenames in os.walk(mdir):
        for filename in filenames:
            if not filename.endswith(".sql"):
                continue
                
            migration_path = os.path.join(dirpath, filename)
            try:
                content = open(migration_path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
                
            # Look for CREATE INDEX statements
            for match in re.finditer(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+[^\s]+\s+ON\s+(\w+)\s*\(([^)]+)\)', content, re.IGNORECASE):
                table = match.group(1)
                columns = [col.strip() for col in match.group(2).split(',')]
                migration_indexes.setdefault(table, set()).update(columns)
    
    # Compare and report drift
    findings = []
    for table, mig_cols in migration_indexes.items():
        if table not in current_indexes:
            findings.append(F("DB-MIGRATION-INDEX-DRIFT", "medium", rel,
                           f"Table '{table}' has indexes in migrations but missing from current schema",
                           detail=f"Migration indexes: {sorted(mig_cols)}",
                           suggestion=f"Add missing indexes to {table} model or remove orphaned migration files.",
                           effort="small"))
        else:
            missing_cols = mig_cols - current_indexes[table]
            if missing_cols:
                findings.append(F("DB-MIGRATION-INDEX-DRIFT", "medium", rel,
                               f"Table '{table}' missing columns in schema that exist in migrations: {sorted(missing_cols)}",
                               suggestion="Add missing @@index() or remove orphaned migration references.",
                               effort="small"))
    
    return findings[:20]

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

# ---------------- tauri ----------------

def rule_tauri_ungated_command(con, root, cfg):
    """Flag Tauri commands that have no capability grant (security risk)."""
    # Check if Tauri is present in the project
    tauri_dirs = ["src-tauri", "tauri", ".tauri"]
    has_tauri = any(os.path.isdir(os.path.join(root, d)) for d in tauri_dirs)
    
    if not has_tauri:
        return []
    
    # Ensure Tauri tables exist
    con.execute("""
        CREATE TABLE IF NOT EXISTS tauri_commands (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            args TEXT,
            file TEXT,
            line INTEGER,
            is_allowed INTEGER DEFAULT 0
        )
    """)
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS tauri_capabilities (
            id INTEGER PRIMARY KEY,
            command TEXT NOT NULL UNIQUE
        )
    """)
    
    # Index Tauri commands if not already done
    if con.execute("SELECT COUNT(*) c FROM tauri_commands").fetchone()["c"] == 0:
        try:
            from .tauri import index_stack
            index_stack(con, root)
        except ImportError:
            return []
    
    out = []
    rows = con.execute("SELECT name, file, line FROM tauri_commands WHERE is_allowed = 0").fetchall()
    
    for r in rows:
        out.append(F("TAURI-UNGATED-COMMAND", "high", r["file"],
                     f"Tauri command '{r['name']}' has no capability grant",
                     detail=f"Command defined at line {r['line']} is not in any capability manifest",
                     suggestion="Add the command to a capability manifest in src-tauri/capabilities/ or remove if unused.",
                     effort="small",
                     line=r["line"]))
    
    return out[:50]

RULES = [
    ("SEC-HARDCODED-SECRET", rule_secrets), ("SEC-SQL-RAW", rule_sql_raw),
    ("ENV", rule_env),
    ("NEXT-CLIENT-LEAK", rule_next_client_leak),
    ("DB-N1", rule_db_n1), ("DB-MISSING-INDEX", rule_db_missing_index),
    ("DB-NO-AWAIT", rule_db_no_await),
    ("DB-DESTRUCTIVE-MIGRATION", rule_db_destructive_migration),
    ("DB-SCHEMA-DRIFT", rule_db_schema_drift),
    ("DB-MIGRATION-INDEX-DRIFT", rule_db_migration_index_drift),
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
    ("TAURI-UNGATED-COMMAND", rule_tauri_ungated_command),
]

def run_rules(con, root, cfg):
    from .custom_rules import get_all_rules
    skip = set(cfg.get("audit", {}).get("ignore_rules", []))
    findings = []
    
    # Get both built-in and custom rules
    all_rules = get_all_rules(root, cfg)
    
    for rid, fn in all_rules:
        if rid in skip: continue
        try:
            findings.extend(fn(con, root, cfg))
        except Exception as e:
            findings.append(F(rid, "info", "", f"rule {rid} failed: {e}"))
    return findings
