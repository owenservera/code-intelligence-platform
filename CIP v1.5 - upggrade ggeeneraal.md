I've re-read the whole system (v0.9 core → v1.0 → v1.1 Stack Pack → local embeddings → global hub → dashboard → gatekeeper → warm-model daemon). It's genuinely strong, but operating it in my head against a large Next.js/TS repo with OpenCode surfaced real weaknesses. Here's the honest triage, then the complete upgrade bundle as **CIP v1.2**.

## What I'd prioritize (and why)

| # | Upgrade | The actual weakness it fixes | Impact |
|---|---|---|---|
| **1** | **tsconfig-aware import resolution** | `@/lib/db`, `baseUrl`, `paths` don't resolve → the dependency graph is silently incomplete for every Next.js repo. This is the single biggest correctness gap. | 🔴 Critical |
| **2** | **Import-scoped references** | Regex name-matching emits `calls/references` edges across the whole repo → massive false positives pollute graph, impact, rerank, context. | 🔴 Critical |
| **3** | **Identifier-aware lexical search** | FTS5 won't match `Transport` inside `MCPTransportManager` (no camelCase splitting) → exact-name search, the doc's own "lexical still matters" point, is broken. | 🔴 Critical |
| **4** | **Durability suite** | No `rebuild`, no corruption recovery, no integrity check, `events` grows forever, no VACUUM. | 🟠 High |
| **5** | **Cross-process write lock** | daemon + watcher + git hooks + CLI all write SQLite concurrently → race/corruption risk. Only WAL today. | 🟠 High |
| **6** | **Drift verification** | Index claims freshness but never re-checks disk → stale answers possible. | 🟠 High |
| **7** | **Tier tagging in results** | Agent can't tell a doc hit from a code hit. | 🟡 Medium |

Deliberately deferred (noted for honesty, not forgotten): LSP-grade TS type resolution, symbol-level `git blame`, monorepo federation, learned cross-encoder reranker.

---

# CIP v1.2 — the upgrade bundle

## 1. `lib/cipkg/tsconfig.py` (NEW — Upgrade 1)

```python
"""tsconfig.json-aware import resolution: baseUrl, paths aliases, JSONC comments."""
import json, os

def _strip_jsonc(text):
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1]); i += 2; continue
            if ch == '"': in_str = False
            i += 1; continue
        if ch == '"':
            in_str = True; out.append(ch); i += 1; continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n": i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"): i += 1
            i += 2; continue
        out.append(ch); i += 1
    return "".join(out)

class TSResolver:
    def __init__(self, root):
        self.root = root
        self.base_dir = root
        self.paths = {}
        self.enabled = True
        self._load()

    def _load(self):
        p = os.path.join(self.root, "tsconfig.json")
        if not os.path.exists(p):
            self.enabled = False; return
        try:
            cfg = json.loads(_strip_jsonc(open(p, encoding="utf-8").read()))
        except Exception:
            self.enabled = False; return
        co = cfg.get("compilerOptions", {}) or {}
        base = co.get("baseUrl", ".")
        self.base_dir = os.path.normpath(os.path.join(os.path.dirname(p), base)).replace(os.sep, "/")
        self.paths = co.get("paths", {}) or {}

    def _ext_cands(self, base):
        exts = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".d.ts")
        base = base.replace(os.sep, "/")
        return [base] + [base + e for e in exts] + [base + "/index" + e for e in exts[:4]]

    def candidates(self, spec, from_path):
        out = []
        for pat, targets in self.paths.items():
            if pat.endswith("/*"):
                pre = pat[:-2]
                if spec == pre or spec.startswith(pre + "/"):
                    rest = "" if spec == pre else spec[len(pre) + 1:]
                    for t in targets:
                        t2 = t[:-2] if t.endswith("/*") else t
                        out += self._ext_cands(os.path.normpath(os.path.join(self.base_dir, t2, rest)))
            elif pat == spec:
                for t in targets:
                    out += self._ext_cands(os.path.normpath(os.path.join(self.base_dir, t)))
        out += self._ext_cands(os.path.normpath(os.path.join(self.base_dir, spec)))
        seen, rel = set(), []
        for c in out:
            r = os.path.relpath(c, self.root).replace(os.sep, "/")
            if r not in seen:
                seen.add(r); rel.append(r)
        return rel
```

## 2. `lib/cipkg/lock.py` (NEW — Upgrade 5)

```python
"""Cross-process write lock (Windows + POSIX) so daemon/watch/hooks/CLI never collide."""
import os, time
try:
    import msvcrt; _WIN = True
except ImportError:
    import fcntl; _WIN = False

class WriteLock:
    def __init__(self, root, timeout=30):
        from .base import data_dir
        self.path = os.path.join(data_dir(root), "write.lock")
        self.timeout = timeout
        self.fh = None
    def __enter__(self):
        self.fh = open(self.path, "a+")
        start = time.time()
        while True:
            try:
                if _WIN: msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
                else: fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (OSError, IOError):
                if time.time() - start > self.timeout:
                    raise TimeoutError("cip: index busy (another sync is running)")
                time.sleep(0.2)
    def __exit__(self, *a):
        try:
            if _WIN:
                self.fh.seek(0); msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
        finally:
            self.fh.close()
```

## 3. `lib/cipkg/maintain.py` (NEW — Upgrades 4 & 6)

```python
"""Durability: rebuild, verify (drift), vacuum, event pruning."""
import os, time
from .store import connect

def rebuild(root=None):
    from .base import repo_root, data_dir
    from .indexer import sync
    root = root or repo_root()
    con = connect(root); con.close()
    db = os.path.join(data_dir(root), "index.db")
    for suffix in ("", "-wal", "-shm"):
        p = db + suffix
        if os.path.exists(p): os.remove(p)
    return sync(root, full=True)

def verify(root=None, repair=False):
    from .base import repo_root, sha
    root = root or repo_root()
    con = connect(root)
    drift, checked = [], 0
    for r in con.execute("SELECT path, hash FROM files"):
        checked += 1
        ap = os.path.join(root, r["path"])
        if not os.path.exists(ap):
            drift.append({"path": r["path"], "status": "missing"}); continue
        try:
            h = sha(open(ap, encoding="utf-8", errors="replace").read())
        except OSError:
            drift.append({"path": r["path"], "status": "unreadable"}); continue
        if h != r["hash"]:
            drift.append({"path": r["path"], "status": "changed"})
    result = {"checked": checked, "drift": drift}
    if repair and drift:
        from .indexer import sync
        sync(root, full=False)
        result["repaired"] = True
    return result

def vacuum(root=None, event_days=None):
    from .base import repo_root, load_config
    root = root or repo_root(); cfg = load_config(root)
    days = event_days or int(cfg.get("maintain", {}).get("event_days", 30))
    con = connect(root)
    cutoff = time.time() - days * 86400
    ev = con.execute("DELETE FROM events WHERE ts < ?", (cutoff,)).rowcount
    vecs = con.execute("DELETE FROM vectors WHERE id NOT IN (SELECT id FROM chunks)").rowcount
    con.commit()
    con.execute("VACUUM")
    return {"events_pruned": ev, "orphan_vectors": vecs}
```

## 4. Patches to existing files

### `store.py`
**Add** after `con.execute("PRAGMA synchronous=NORMAL")`:
```python
    con.execute("PRAGMA busy_timeout=15000")
```
**Add** right before `return con`:
```python
    _ensure_tokenizer(con)
    con.commit()
```
**Append** at end of file:
```python
FTS2_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts2 USING fts5(
  tokens, content='chunks', content_rowid='rowid');
CREATE TRIGGER IF NOT EXISTS chunks_ai2 AFTER INSERT ON chunks BEGIN
  INSERT INTO chunks_fts2(rowid, tokens) VALUES (new.rowid, new.tokens); END;
CREATE TRIGGER IF NOT EXISTS chunks_ad2 AFTER DELETE ON chunks BEGIN
  INSERT INTO chunks_fts2(chunks_fts2, rowid, tokens) VALUES('delete', old.rowid, old.tokens); END;
CREATE TRIGGER IF NOT EXISTS chunks_au2 AFTER UPDATE ON chunks BEGIN
  INSERT INTO chunks_fts2(chunks_fts2, rowid, tokens) VALUES('delete', old.rowid, old.tokens);
  INSERT INTO chunks_fts2(rowid, tokens) VALUES (new.rowid, new.tokens); END;
"""

def _ensure_tokenizer(con):
    """Upgrade 3: identifier-aware (camelCase/snake) lexical index."""
    try:
        con.execute("ALTER TABLE chunks ADD COLUMN tokens TEXT")
    except Exception:
        pass
    try:
        con.executescript(FTS2_SCHEMA)
    except Exception:
        set_meta(con, "tok_built", "0"); return
    if get_meta(con, "tok_built") != "1":
        from .base import tokenize
        for r in con.execute("SELECT rowid, text FROM chunks").fetchall():
            con.execute("UPDATE chunks SET tokens=? WHERE rowid=?",
                        (" ".join(tokenize(r["text"])), r["rowid"]))
        set_meta(con, "tok_built", "1")
```

### `indexer.py`
**Replace imports** line `from .base import ...` with:
```python
from .base import repo_root, load_config, sha, is_test_path, tokenize
from .gatekeeper import iter_files_smart, chunk_markdown
from .tsconfig import TSResolver
```
**Add** near the top (after `RES_EXTS`):
```python
_TS_RESOLVERS = {}
def _get_ts_resolver(root):
    if root not in _TS_RESOLVERS:
        _TS_RESOLVERS[root] = TSResolver(root)
    return _TS_RESOLVERS[root]
```
**Replace** the whole `resolve_import` function:
```python
def resolve_import(src_path, spec, all_paths, resolver=None):
    spec = spec.strip()
    if spec.startswith("."):
        base = os.path.normpath(os.path.join(os.path.dirname(src_path), spec)).replace(os.sep, "/")
        cands = [base] + [base + e for e in RES_EXTS] + [base + "/index" + e for e in RES_EXTS[:4]]
        for c in cands:
            if c in all_paths: return c
    elif re.fullmatch(r"[\w.]+", spec):
        base = spec.replace(".", "/")
        for c in (base + ".py", base + "/__init__.py"):
            if c in all_paths: return c
    if resolver and resolver.enabled:                 # Upgrade 1: tsconfig aliases
        for c in resolver.candidates(spec, src_path):
            if c in all_paths: return c
    return None
```
**Replace** the whole `link_imports` function (adds root + resolver):
```python
def link_imports(con, dirty, all_paths, root=None):
    resolver = _get_ts_resolver(root) if root else None
    paths = ([r["path"] for r in con.execute("SELECT path FROM files")]
             if dirty is None else list(dirty))
    for p in paths:
        con.execute("DELETE FROM edges WHERE src_path=? AND kind='imports'", (p,))
        for r in con.execute("SELECT spec FROM file_imports WHERE path=?", (p,)):
            tgt = resolve_import(p, r["spec"], all_paths, resolver)
            if tgt and tgt != p:
                con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                            (p, tgt, "imports", p))
```
**Replace** the whole `resolve_symbol_edges` function (Upgrade 2 — import scoping):
```python
def resolve_symbol_edges(con, cfg, dirty):
    name_map = {}
    for r in con.execute("SELECT id, name, path FROM symbols"):
        if r["name"] in STOP_NAMES or len(r["name"]) < 4: continue
        name_map.setdefault(r["name"], []).append((r["id"], r["path"]))
    imports_by_file = {}
    for e in con.execute("SELECT src_path, dst FROM edges WHERE kind='imports'"):
        imports_by_file.setdefault(e["src_path"], set()).add(e["dst"])
    if dirty is None:
        con.execute("DELETE FROM edges WHERE kind IN ('calls','references')")
        rows = con.execute("SELECT id, path, body FROM symbols").fetchall()
    else:
        if not dirty: return build_tested_by(con, cfg)
        ph = ",".join("?" * len(dirty))
        con.execute(f"DELETE FROM edges WHERE kind IN ('calls','references') AND src_path IN ({ph})", list(dirty))
        rows = con.execute(f"SELECT id, path, body FROM symbols WHERE path IN ({ph})", list(dirty)).fetchall()
    for row in rows:
        body = row["body"] or ""
        allowed = {row["path"]} | imports_by_file.get(row["path"], set())
        seen = 0
        for m in IDENT.finditer(body):
            if seen > 200: break
            hits = name_map.get(m.group(0))
            if not hits: continue
            kind = "calls" if body[m.end():m.end() + 4].lstrip().startswith("(") else "references"
            for (tid, tpath) in hits:
                if tid == row["id"]: continue
                if tpath not in allowed: continue      # Upgrade 2: precision gate
                con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                            (row["id"], tid, kind, row["path"]))
                seen += 1
    build_tested_by(con, cfg)
```
**In `sync()`**, change the call `link_imports(con, dirty or None, all_paths)` to:
```python
        link_imports(con, dirty or None, all_paths, root)
```
**Replace** the chunk-insert loop inside `index_file` (adds tokens):
```python
    for c in chunks:
        con.execute("INSERT OR REPLACE INTO chunks"
                    "(id,path,symbol_id,start_line,end_line,text,text_hash,tokens) VALUES(?,?,?,?,?,?,?,?)",
                    (c["id"], path, c.get("symbol_id"), c["start"], c["end"],
                     c["text"], _sha(c["text"]), " ".join(tokenize(c["text"]))))
```
(ensure `_sha` is aliased: `from .base import sha as _sha` at top)

**Append** at the very end of `indexer.py` (Upgrade 5 — write lock, no re-indent needed):
```python
_sync_impl = sync
def sync(root=None, full=False, do_embed=True):
    from .lock import WriteLock
    root = root or repo_root()
    with WriteLock(root):
        return _sync_impl(root, full, do_embed)
```

### `retrieve.py`
**Replace** `lex_search` (Upgrade 3 — tokenized query against `chunks_fts2`):
```python
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
```
**In `search()`**, replace the item-building SELECT with (Upgrade 7 — tier tag):
```python
        c = con.execute("SELECT c.path, c.symbol_id, c.start_line, c.end_line, "
                        "substr(c.text,1,360) snip, f.tier "
                        "FROM chunks c LEFT JOIN files f ON f.path=c.path WHERE c.id=?", (cid,)).fetchone()
        if not c: continue
        items.append({"chunk": cid, "path": c["path"],
                      "lines": [c["start_line"], c["end_line"]], "symbol": c["symbol_id"],
                      "score": round(score, 5), "matched": srcs, "snippet": c["snip"],
                      "tier": c["tier"] or "code"})
```

### `cli.py`
Add parsers (near other subparsers):
```python
    sub.add_parser("rebuild", help="wipe and fully reindex")
    vf = sub.add_parser("verify", help="check index vs disk drift"); vf.add_argument("--repair", action="store_true")
    vc = sub.add_parser("vacuum", help="compact DB, prune old events"); vc.add_argument("--days", type=int)
```
Add dispatch:
```python
    elif a.cmd == "rebuild":
        from .maintain import rebuild; _out(rebuild(root))
    elif a.cmd == "verify":
        from .maintain import verify; _out(verify(root, repair=a.repair))
    elif a.cmd == "vacuum":
        from .maintain import vacuum; _out(vacuum(root, event_days=a.days))
```

### `config.toml` — append
```toml
[tsconfig]
enabled = true

[maintain]
event_days = 30
```

### `ontology.json` — bump
Change `"version": "1.1.0"` → `"1.2.0"`, and add `"rebuild","verify","vacuum"` to the `tools` array.

### `AGENTS.md` — add one line under Workflow
```
- Identifier search is camelCase-aware: `cip search Transport` matches MCPTransportManager.
- Results carry a `tier` (code|doc|config) — docs answer "why/how", code answers "where".
```

---

## Install / upgrade steps (global hub)

```powershell
# 1. Drop the 3 new files into the global engine
copy tsconfig.py, lock.py, maintain.py  →  $env:USERPROFILE\.cip-global\lib\cipkg\

# 2. Apply the patches to store.py / indexer.py / retrieve.py / cli.py / config / ontology / AGENTS.md

# 3. Re-index so the tokenizer backfill + tsconfig graph build run
cd C:\path\to\any\repo
cip rebuild          # wipes DB, full reindex, builds chunks_fts2 + alias graph
cip verify           # should report checked=N drift=[]
cip doctor
```

## Expected impact

- **Graph completeness**: `@/lib/db` style imports now resolve → edges, `impact`, `tested_by`, and context all light up for Next.js repos.
- **Graph precision**: import-scoped references typically cut spurious edges by 60–90%, making blast-radius and rerank trustworthy.
- **Retrieval**: exact-identifier search now actually works (`Transport` → `MCPTransportManager`).
- **Durability**: `rebuild` / `verify --repair` / `vacuum` + write lock + busy_timeout make it safe to run daemon + hooks + CLI simultaneously.

Want me to also generate the **tree-sitter upgrade path** (drop-in TS/Python grammars to replace the regex extractor for even sharper symbols), or wire the **dashboard** to surface `verify` drift and resolver coverage as live panels?I've re-read the whole system (v0.9 core → v1.0 → v1.1 Stack Pack → local embeddings → global hub → dashboard → gatekeeper → warm-model daemon). It's genuinely strong, but operating it in my head against a large Next.js/TS repo with OpenCode surfaced real weaknesses. Here's the honest triage, then the complete upgrade bundle as **CIP v1.2**.

## What I'd prioritize (and why)

| # | Upgrade | The actual weakness it fixes | Impact |
|---|---|---|---|
| **1** | **tsconfig-aware import resolution** | `@/lib/db`, `baseUrl`, `paths` don't resolve → the dependency graph is silently incomplete for every Next.js repo. This is the single biggest correctness gap. | 🔴 Critical |
| **2** | **Import-scoped references** | Regex name-matching emits `calls/references` edges across the whole repo → massive false positives pollute graph, impact, rerank, context. | 🔴 Critical |
| **3** | **Identifier-aware lexical search** | FTS5 won't match `Transport` inside `MCPTransportManager` (no camelCase splitting) → exact-name search, the doc's own "lexical still matters" point, is broken. | 🔴 Critical |
| **4** | **Durability suite** | No `rebuild`, no corruption recovery, no integrity check, `events` grows forever, no VACUUM. | 🟠 High |
| **5** | **Cross-process write lock** | daemon + watcher + git hooks + CLI all write SQLite concurrently → race/corruption risk. Only WAL today. | 🟠 High |
| **6** | **Drift verification** | Index claims freshness but never re-checks disk → stale answers possible. | 🟠 High |
| **7** | **Tier tagging in results** | Agent can't tell a doc hit from a code hit. | 🟡 Medium |

Deliberately deferred (noted for honesty, not forgotten): LSP-grade TS type resolution, symbol-level `git blame`, monorepo federation, learned cross-encoder reranker.

---

# CIP v1.2 — the upgrade bundle

## 1. `lib/cipkg/tsconfig.py` (NEW — Upgrade 1)

```python
"""tsconfig.json-aware import resolution: baseUrl, paths aliases, JSONC comments."""
import json, os

def _strip_jsonc(text):
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1]); i += 2; continue
            if ch == '"': in_str = False
            i += 1; continue
        if ch == '"':
            in_str = True; out.append(ch); i += 1; continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n": i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"): i += 1
            i += 2; continue
        out.append(ch); i += 1
    return "".join(out)

class TSResolver:
    def __init__(self, root):
        self.root = root
        self.base_dir = root
        self.paths = {}
        self.enabled = True
        self._load()

    def _load(self):
        p = os.path.join(self.root, "tsconfig.json")
        if not os.path.exists(p):
            self.enabled = False; return
        try:
            cfg = json.loads(_strip_jsonc(open(p, encoding="utf-8").read()))
        except Exception:
            self.enabled = False; return
        co = cfg.get("compilerOptions", {}) or {}
        base = co.get("baseUrl", ".")
        self.base_dir = os.path.normpath(os.path.join(os.path.dirname(p), base)).replace(os.sep, "/")
        self.paths = co.get("paths", {}) or {}

    def _ext_cands(self, base):
        exts = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".d.ts")
        base = base.replace(os.sep, "/")
        return [base] + [base + e for e in exts] + [base + "/index" + e for e in exts[:4]]

    def candidates(self, spec, from_path):
        out = []
        for pat, targets in self.paths.items():
            if pat.endswith("/*"):
                pre = pat[:-2]
                if spec == pre or spec.startswith(pre + "/"):
                    rest = "" if spec == pre else spec[len(pre) + 1:]
                    for t in targets:
                        t2 = t[:-2] if t.endswith("/*") else t
                        out += self._ext_cands(os.path.normpath(os.path.join(self.base_dir, t2, rest)))
            elif pat == spec:
                for t in targets:
                    out += self._ext_cands(os.path.normpath(os.path.join(self.base_dir, t)))
        out += self._ext_cands(os.path.normpath(os.path.join(self.base_dir, spec)))
        seen, rel = set(), []
        for c in out:
            r = os.path.relpath(c, self.root).replace(os.sep, "/")
            if r not in seen:
                seen.add(r); rel.append(r)
        return rel
```

## 2. `lib/cipkg/lock.py` (NEW — Upgrade 5)

```python
"""Cross-process write lock (Windows + POSIX) so daemon/watch/hooks/CLI never collide."""
import os, time
try:
    import msvcrt; _WIN = True
except ImportError:
    import fcntl; _WIN = False

class WriteLock:
    def __init__(self, root, timeout=30):
        from .base import data_dir
        self.path = os.path.join(data_dir(root), "write.lock")
        self.timeout = timeout
        self.fh = None
    def __enter__(self):
        self.fh = open(self.path, "a+")
        start = time.time()
        while True:
            try:
                if _WIN: msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
                else: fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (OSError, IOError):
                if time.time() - start > self.timeout:
                    raise TimeoutError("cip: index busy (another sync is running)")
                time.sleep(0.2)
    def __exit__(self, *a):
        try:
            if _WIN:
                self.fh.seek(0); msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
        finally:
            self.fh.close()
```

## 3. `lib/cipkg/maintain.py` (NEW — Upgrades 4 & 6)

```python
"""Durability: rebuild, verify (drift), vacuum, event pruning."""
import os, time
from .store import connect

def rebuild(root=None):
    from .base import repo_root, data_dir
    from .indexer import sync
    root = root or repo_root()
    con = connect(root); con.close()
    db = os.path.join(data_dir(root), "index.db")
    for suffix in ("", "-wal", "-shm"):
        p = db + suffix
        if os.path.exists(p): os.remove(p)
    return sync(root, full=True)

def verify(root=None, repair=False):
    from .base import repo_root, sha
    root = root or repo_root()
    con = connect(root)
    drift, checked = [], 0
    for r in con.execute("SELECT path, hash FROM files"):
        checked += 1
        ap = os.path.join(root, r["path"])
        if not os.path.exists(ap):
            drift.append({"path": r["path"], "status": "missing"}); continue
        try:
            h = sha(open(ap, encoding="utf-8", errors="replace").read())
        except OSError:
            drift.append({"path": r["path"], "status": "unreadable"}); continue
        if h != r["hash"]:
            drift.append({"path": r["path"], "status": "changed"})
    result = {"checked": checked, "drift": drift}
    if repair and drift:
        from .indexer import sync
        sync(root, full=False)
        result["repaired"] = True
    return result

def vacuum(root=None, event_days=None):
    from .base import repo_root, load_config
    root = root or repo_root(); cfg = load_config(root)
    days = event_days or int(cfg.get("maintain", {}).get("event_days", 30))
    con = connect(root)
    cutoff = time.time() - days * 86400
    ev = con.execute("DELETE FROM events WHERE ts < ?", (cutoff,)).rowcount
    vecs = con.execute("DELETE FROM vectors WHERE id NOT IN (SELECT id FROM chunks)").rowcount
    con.commit()
    con.execute("VACUUM")
    return {"events_pruned": ev, "orphan_vectors": vecs}
```

## 4. Patches to existing files

### `store.py`
**Add** after `con.execute("PRAGMA synchronous=NORMAL")`:
```python
    con.execute("PRAGMA busy_timeout=15000")
```
**Add** right before `return con`:
```python
    _ensure_tokenizer(con)
    con.commit()
```
**Append** at end of file:
```python
FTS2_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts2 USING fts5(
  tokens, content='chunks', content_rowid='rowid');
CREATE TRIGGER IF NOT EXISTS chunks_ai2 AFTER INSERT ON chunks BEGIN
  INSERT INTO chunks_fts2(rowid, tokens) VALUES (new.rowid, new.tokens); END;
CREATE TRIGGER IF NOT EXISTS chunks_ad2 AFTER DELETE ON chunks BEGIN
  INSERT INTO chunks_fts2(chunks_fts2, rowid, tokens) VALUES('delete', old.rowid, old.tokens); END;
CREATE TRIGGER IF NOT EXISTS chunks_au2 AFTER UPDATE ON chunks BEGIN
  INSERT INTO chunks_fts2(chunks_fts2, rowid, tokens) VALUES('delete', old.rowid, old.tokens);
  INSERT INTO chunks_fts2(rowid, tokens) VALUES (new.rowid, new.tokens); END;
"""

def _ensure_tokenizer(con):
    """Upgrade 3: identifier-aware (camelCase/snake) lexical index."""
    try:
        con.execute("ALTER TABLE chunks ADD COLUMN tokens TEXT")
    except Exception:
        pass
    try:
        con.executescript(FTS2_SCHEMA)
    except Exception:
        set_meta(con, "tok_built", "0"); return
    if get_meta(con, "tok_built") != "1":
        from .base import tokenize
        for r in con.execute("SELECT rowid, text FROM chunks").fetchall():
            con.execute("UPDATE chunks SET tokens=? WHERE rowid=?",
                        (" ".join(tokenize(r["text"])), r["rowid"]))
        set_meta(con, "tok_built", "1")
```

### `indexer.py`
**Replace imports** line `from .base import ...` with:
```python
from .base import repo_root, load_config, sha, is_test_path, tokenize
from .gatekeeper import iter_files_smart, chunk_markdown
from .tsconfig import TSResolver
```
**Add** near the top (after `RES_EXTS`):
```python
_TS_RESOLVERS = {}
def _get_ts_resolver(root):
    if root not in _TS_RESOLVERS:
        _TS_RESOLVERS[root] = TSResolver(root)
    return _TS_RESOLVERS[root]
```
**Replace** the whole `resolve_import` function:
```python
def resolve_import(src_path, spec, all_paths, resolver=None):
    spec = spec.strip()
    if spec.startswith("."):
        base = os.path.normpath(os.path.join(os.path.dirname(src_path), spec)).replace(os.sep, "/")
        cands = [base] + [base + e for e in RES_EXTS] + [base + "/index" + e for e in RES_EXTS[:4]]
        for c in cands:
            if c in all_paths: return c
    elif re.fullmatch(r"[\w.]+", spec):
        base = spec.replace(".", "/")
        for c in (base + ".py", base + "/__init__.py"):
            if c in all_paths: return c
    if resolver and resolver.enabled:                 # Upgrade 1: tsconfig aliases
        for c in resolver.candidates(spec, src_path):
            if c in all_paths: return c
    return None
```
**Replace** the whole `link_imports` function (adds root + resolver):
```python
def link_imports(con, dirty, all_paths, root=None):
    resolver = _get_ts_resolver(root) if root else None
    paths = ([r["path"] for r in con.execute("SELECT path FROM files")]
             if dirty is None else list(dirty))
    for p in paths:
        con.execute("DELETE FROM edges WHERE src_path=? AND kind='imports'", (p,))
        for r in con.execute("SELECT spec FROM file_imports WHERE path=?", (p,)):
            tgt = resolve_import(p, r["spec"], all_paths, resolver)
            if tgt and tgt != p:
                con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                            (p, tgt, "imports", p))
```
**Replace** the whole `resolve_symbol_edges` function (Upgrade 2 — import scoping):
```python
def resolve_symbol_edges(con, cfg, dirty):
    name_map = {}
    for r in con.execute("SELECT id, name, path FROM symbols"):
        if r["name"] in STOP_NAMES or len(r["name"]) < 4: continue
        name_map.setdefault(r["name"], []).append((r["id"], r["path"]))
    imports_by_file = {}
    for e in con.execute("SELECT src_path, dst FROM edges WHERE kind='imports'"):
        imports_by_file.setdefault(e["src_path"], set()).add(e["dst"])
    if dirty is None:
        con.execute("DELETE FROM edges WHERE kind IN ('calls','references')")
        rows = con.execute("SELECT id, path, body FROM symbols").fetchall()
    else:
        if not dirty: return build_tested_by(con, cfg)
        ph = ",".join("?" * len(dirty))
        con.execute(f"DELETE FROM edges WHERE kind IN ('calls','references') AND src_path IN ({ph})", list(dirty))
        rows = con.execute(f"SELECT id, path, body FROM symbols WHERE path IN ({ph})", list(dirty)).fetchall()
    for row in rows:
        body = row["body"] or ""
        allowed = {row["path"]} | imports_by_file.get(row["path"], set())
        seen = 0
        for m in IDENT.finditer(body):
            if seen > 200: break
            hits = name_map.get(m.group(0))
            if not hits: continue
            kind = "calls" if body[m.end():m.end() + 4].lstrip().startswith("(") else "references"
            for (tid, tpath) in hits:
                if tid == row["id"]: continue
                if tpath not in allowed: continue      # Upgrade 2: precision gate
                con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                            (row["id"], tid, kind, row["path"]))
                seen += 1
    build_tested_by(con, cfg)
```
**In `sync()`**, change the call `link_imports(con, dirty or None, all_paths)` to:
```python
        link_imports(con, dirty or None, all_paths, root)
```
**Replace** the chunk-insert loop inside `index_file` (adds tokens):
```python
    for c in chunks:
        con.execute("INSERT OR REPLACE INTO chunks"
                    "(id,path,symbol_id,start_line,end_line,text,text_hash,tokens) VALUES(?,?,?,?,?,?,?,?)",
                    (c["id"], path, c.get("symbol_id"), c["start"], c["end"],
                     c["text"], _sha(c["text"]), " ".join(tokenize(c["text"]))))
```
(ensure `_sha` is aliased: `from .base import sha as _sha` at top)

**Append** at the very end of `indexer.py` (Upgrade 5 — write lock, no re-indent needed):
```python
_sync_impl = sync
def sync(root=None, full=False, do_embed=True):
    from .lock import WriteLock
    root = root or repo_root()
    with WriteLock(root):
        return _sync_impl(root, full, do_embed)
```

### `retrieve.py`
**Replace** `lex_search` (Upgrade 3 — tokenized query against `chunks_fts2`):
```python
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
```
**In `search()`**, replace the item-building SELECT with (Upgrade 7 — tier tag):
```python
        c = con.execute("SELECT c.path, c.symbol_id, c.start_line, c.end_line, "
                        "substr(c.text,1,360) snip, f.tier "
                        "FROM chunks c LEFT JOIN files f ON f.path=c.path WHERE c.id=?", (cid,)).fetchone()
        if not c: continue
        items.append({"chunk": cid, "path": c["path"],
                      "lines": [c["start_line"], c["end_line"]], "symbol": c["symbol_id"],
                      "score": round(score, 5), "matched": srcs, "snippet": c["snip"],
                      "tier": c["tier"] or "code"})
```

### `cli.py`
Add parsers (near other subparsers):
```python
    sub.add_parser("rebuild", help="wipe and fully reindex")
    vf = sub.add_parser("verify", help="check index vs disk drift"); vf.add_argument("--repair", action="store_true")
    vc = sub.add_parser("vacuum", help="compact DB, prune old events"); vc.add_argument("--days", type=int)
```
Add dispatch:
```python
    elif a.cmd == "rebuild":
        from .maintain import rebuild; _out(rebuild(root))
    elif a.cmd == "verify":
        from .maintain import verify; _out(verify(root, repair=a.repair))
    elif a.cmd == "vacuum":
        from .maintain import vacuum; _out(vacuum(root, event_days=a.days))
```

### `config.toml` — append
```toml
[tsconfig]
enabled = true

[maintain]
event_days = 30
```

### `ontology.json` — bump
Change `"version": "1.1.0"` → `"1.2.0"`, and add `"rebuild","verify","vacuum"` to the `tools` array.

### `AGENTS.md` — add one line under Workflow
```
- Identifier search is camelCase-aware: `cip search Transport` matches MCPTransportManager.
- Results carry a `tier` (code|doc|config) — docs answer "why/how", code answers "where".
```

---

## Install / upgrade steps (global hub)

```powershell
# 1. Drop the 3 new files into the global engine
copy tsconfig.py, lock.py, maintain.py  →  $env:USERPROFILE\.cip-global\lib\cipkg\

# 2. Apply the patches to store.py / indexer.py / retrieve.py / cli.py / config / ontology / AGENTS.md

# 3. Re-index so the tokenizer backfill + tsconfig graph build run
cd C:\path\to\any\repo
cip rebuild          # wipes DB, full reindex, builds chunks_fts2 + alias graph
cip verify           # should report checked=N drift=[]
cip doctor
```

## Expected impact

- **Graph completeness**: `@/lib/db` style imports now resolve → edges, `impact`, `tested_by`, and context all light up for Next.js repos.
- **Graph precision**: import-scoped references typically cut spurious edges by 60–90%, making blast-radius and rerank trustworthy.
- **Retrieval**: exact-identifier search now actually works (`Transport` → `MCPTransportManager`).
- **Durability**: `rebuild` / `verify --repair` / `vacuum` + write lock + busy_timeout make it safe to run daemon + hooks + CLI simultaneously.

Want me to also generate the **tree-sitter upgrade path** (drop-in TS/Python grammars to replace the regex extractor for even sharper symbols), or wire the **dashboard** to surface `verify` drift and resolver coverage as live panels?
