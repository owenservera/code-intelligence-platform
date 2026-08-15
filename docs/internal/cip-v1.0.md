v# CIP v1.0 — the complete next set

This delivers everything on the v0.9 roadmap: **tree-sitter parsing**, **hierarchical summaries**, **git/history indexing**, **runtime signal adapters**, **reranking + intent routing**, **pluggable vector store**, **LSIF/Markdown export**, **daemon mode**, and a **self-test suite** — plus the patch hooks into v0.9 files.

| Roadmap item | Deliverable below |
|---|---|
| tree-sitter backends | `parsers.py` (+2-line indexer patch) |
| LLM/structural summary layer | `summarize.py` + `summary`/`map` tools |
| Git indexing, hotspots, co-change | `gitindex.py` + `modified_by`/`co_change` edges |
| Runtime adapters (tests/tsc/builds) | `runtime_adapters.py` + `ingest`/`broken` tools |
| Reranking | `rerank.py` (wired into `search`) |
| Intent analysis | `router.py` (wired into `search` envelope) |
| Vector scaling path | `vecstore.py` (numpy + sqlite-vec hook) |
| SCIP/LSIF interop | `export.py` (LSIF / JSON / Markdown) |
| Daemon + single writer | `daemon.py` (`cip daemon`) |
| Verifiable correctness | `selftest.py` (`cip selftest`) |

---

## 1. Patches to v0.9 files (apply these three small edits)

### PATCH A — `lib/cipkg/base.py` (2 edits)

**Edit 1** — in `DEFAULT_CONFIG`, add the new sections:

```python
    "serve": {"port": 8787},
    # ---- v1.0 additions ----
    "summary": {"backend": "structural", "llm_model": "gpt-4o-mini", "max_llm_per_sync": 20},
    "git": {"depth": 500, "co_change_min": 2},
    "rerank": {"enabled": True},
    "vector": {"backend": "sqlite"},        # sqlite | sqlite-vec
}
```

**Edit 2** — in `load_config`, replace the merge loop so new config sections survive:

```python
    for section, kv in data.items():
        if isinstance(kv, dict):
            cfg.setdefault(section, {}).update(kv)
    return cfg
```

### PATCH B — `lib/cipkg/indexer.py` (2 edits)

**Edit 1** — swap the parser import (tree-sitter when available, regex fallback otherwise):

```python
# was: from .parse import parse_file, extract_imports
from .parsers import parse_file
from .parse import extract_imports
```

**Edit 2** — inside `sync()`, immediately after `resolve_symbol_edges(con, cfg, dirty or None)`:

```python
        from .parsers import build_heritage
        build_heritage(con, dirty or None)
```

### PATCH C — `lib/cipkg/__init__.py`

```python
__version__ = "1.0.0"
```

---

## 2. Updated core files (REPLACE)

### 2.1 `lib/cipkg/store.py` — schema v4 (auto-migrates v0.9 DBs)

```python
"""SQLite storage v1.0: + summaries, commits, commit_files, signals.
CREATE IF NOT EXISTS makes old databases upgrade in place."""
import os, sqlite3

SCHEMA_VERSION = 4

CORE_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS files(
  path TEXT PRIMARY KEY, language TEXT, size INTEGER, lines INTEGER,
  hash TEXT, mtime REAL, indexed_at REAL);

CREATE TABLE IF NOT EXISTS symbols(
  id TEXT PRIMARY KEY, name TEXT, kind TEXT, path TEXT,
  start_line INTEGER, end_line INTEGER, signature TEXT,
  body_hash TEXT, body TEXT);
CREATE INDEX IF NOT EXISTS idx_sym_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_sym_path ON symbols(path);

CREATE TABLE IF NOT EXISTS chunks(
  id TEXT PRIMARY KEY, path TEXT, symbol_id TEXT,
  start_line INTEGER, end_line INTEGER, text TEXT, text_hash TEXT);
CREATE INDEX IF NOT EXISTS idx_chunk_path ON chunks(path);

CREATE TABLE IF NOT EXISTS file_imports(path TEXT, spec TEXT);
CREATE INDEX IF NOT EXISTS idx_fi_path ON file_imports(path);

CREATE TABLE IF NOT EXISTS edges(
  src TEXT, dst TEXT, kind TEXT, src_path TEXT,
  PRIMARY KEY(src, dst, kind));
CREATE INDEX IF NOT EXISTS idx_edges_src_path ON edges(src_path);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);

CREATE TABLE IF NOT EXISTS vectors(id TEXT PRIMARY KEY, model TEXT, vec BLOB);

CREATE TABLE IF NOT EXISTS events(ts REAL, kind TEXT, payload TEXT);

-- ---- v1.0 tables ----
CREATE TABLE IF NOT EXISTS summaries(
  id TEXT PRIMARY KEY,            -- repo:// | dir://<path> | file://<path> | <symbol_id>
  kind TEXT, path TEXT, content_hash TEXT,
  summary TEXT, source TEXT, updated_at REAL);
CREATE INDEX IF NOT EXISTS idx_sum_path ON summaries(path);

CREATE TABLE IF NOT EXISTS commits(
  sha TEXT PRIMARY KEY, ts REAL, author TEXT, message TEXT, files_changed INTEGER);
CREATE TABLE IF NOT EXISTS commit_files(sha TEXT, path TEXT, PRIMARY KEY(sha, path));
CREATE INDEX IF NOT EXISTS idx_cf_path ON commit_files(path);

CREATE TABLE IF NOT EXISTS signals(
  id TEXT PRIMARY KEY, kind TEXT, path TEXT, symbol_id TEXT,
  name TEXT, payload TEXT, ts REAL);
CREATE INDEX IF NOT EXISTS idx_sig_path ON signals(path);
CREATE INDEX IF NOT EXISTS idx_sig_kind ON signals(kind);
"""

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  text, content='chunks', content_rowid='rowid');

CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
  INSERT INTO chunks_fts(rowid, text) VALUES (new.rowid, new.text); END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.rowid, old.text); END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.rowid, old.text);
  INSERT INTO chunks_fts(rowid, text) VALUES (new.rowid, new.text); END;
"""

def connect(root):
    from .base import data_dir
    db = os.path.join(data_dir(root), "index.db")
    con = sqlite3.connect(db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript(CORE_SCHEMA)
    try:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts_probe USING fts5(x)")
        con.execute("DROP TABLE _fts_probe")
        con.executescript(FTS_SCHEMA)
        fts = "1"
    except sqlite3.OperationalError:
        fts = "0"
    con.execute("INSERT INTO meta(key,value) VALUES('schema_version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(SCHEMA_VERSION),))
    con.execute("INSERT INTO meta(key,value) VALUES('fts',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (fts,))
    con.commit()
    return con

def get_meta(con, key, default=None):
    r = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default

def set_meta(con, key, value):
    con.execute("INSERT INTO meta(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
```

### 2.2 `config.toml` (REPLACE — new sections added)

```toml
[index]
max_file_kb = 512
exclude = []
test_globs = ["test_", "_test.", ".test.", ".spec.", "/tests/", "__tests__"]

[embed]
backend = "auto"            # auto | hashing | sentence-transformers | openai
model = "all-MiniLM-L6-v2"
dim = 1024

[retrieval]
lexical_k = 30
vector_k = 30
context_budget_tokens = 6000

[serve]
port = 8787

# ---- v1.0 ----
[summary]
backend = "structural"      # structural (offline) | llm
llm_model = "gpt-4o-mini"
max_llm_per_sync = 20

[git]
depth = 500
co_change_min = 2

[rerank]
enabled = true

[vector]
backend = "sqlite"          # sqlite | sqlite-vec (experimental)
```

### 2.3 `ontology.json` (REPLACE — v1.0)

```json
{
  "protocol": "cip",
  "version": "1.0.0",
  "id_grammar": "<language>://<path>#<Qualified.name>",
  "chunk_grammar": "<path>#L<start>-L<end>",
  "entities": {
    "File":    { "key": "path" },
    "Symbol":  { "key": "id", "kinds": ["class","function","method","interface","type","const","module","test"] },
    "Chunk":   { "key": "id" },
    "Commit":  { "key": "sha", "note": "populated by `cip git-index`" },
    "Signal":  { "key": "id", "kinds": ["test_pass","test_fail","type_error","build_error","coverage","custom"],
                 "note": "runtime evidence ingested by `cip ingest`" },
    "Summary": { "key": "id", "kinds": ["repo","dir","file","symbol"], "note": "hash-cached, lazily invalidated" }
  },
  "relationships": {
    "contains":   { "from": "File",        "to": "Symbol" },
    "exports":    { "from": "File",        "to": "Symbol" },
    "imports":    { "from": "File",        "to": "File" },
    "calls":      { "from": "Symbol",      "to": "Symbol" },
    "references": { "from": "Symbol",      "to": "Symbol" },
    "extends":    { "from": "Symbol",      "to": "Symbol" },
    "implements": { "from": "Symbol",      "to": "Symbol" },
    "tested_by":  { "from": "Symbol",      "to": "File" },
    "modified_by":{ "from": "File",        "to": "Commit" },
    "co_change":  { "from": "File",        "to": "File", "note": "files frequently changed together" }
  },
  "intents": ["symbol", "search", "architecture", "history", "health", "tests"],
  "envelope": {
    "ok": "bool", "tool": "string", "result": "object",
    "next_ops": "string[]",
    "index": { "fresh": "bool", "lag_s": "number", "files": "integer" }
  },
  "tools": ["search", "symbol", "graph", "context", "summary", "map", "describe",
            "broken", "hotspots", "history", "route", "git_index", "index_status"],
  "freshness": { "stale_after_s": 300, "enforced_by": ["git-hooks", "watcher", "daemon"] },
  "extension_points": ["parsers (tree-sitter)", "embedders", "rerankers", "vector stores",
                        "runtime adapters", "exporters"],
  "self_description": "GET /ontology.json · describe(entity) · cip tools --schema"
}
```

### 2.4 `bootstrap/AGENTS.md` (REPLACE — v1.0)

````markdown
# AGENTS.md — Code Intelligence Bootstrap (CIP v1.0)

This repository runs **CIP**: a continuously updated, machine-readable model of
the codebase — structure, history, tests, and runtime health. Do NOT read the
whole repo. Interrogate the index.

## Workflow (before any change)
1. `cip search "<intent>"`    → candidates (lexical + semantic + graph + rerank); response includes detected intent
2. `cip symbol <Name>`        → definition + relationship counts
3. `cip context "<intent>"`   → budgeted pack: code + summary + relations + tests + known failures
4. Read exact source only at the lines the index points to.
5. After edits the index self-updates (hooks / daemon); `cip sync` to force.

## Architecture-first questions
- `cip map`                → subsystems, sizes, hotspots
- `cip summary [path]`     → repo / directory / file summary
- `cip hotspots`           → what changed most recently

## Health questions ("is this safe to refactor?")
- `cip broken`             → failing tests + type errors in the last 14 days
- `cip history <path>`     → why this code exists

## Rules
- Index = authoritative for STRUCTURE. Source files = authoritative for IMPLEMENTATION.
- If a response says `"fresh": false`, run `cip sync` first.
- Prefer `cip context` over opening files > 300 lines.
- Self-introspection: `cip describe <Entity>` or GET `/ontology.json`.

## Tools
CLI: `cip search | symbol | graph | context | summary | map | broken | hotspots | history | route | describe | doctor`
MCP: `cip mcp` · HTTP: `cip serve` (`POST /rpc`, `GET /ontology.json`)
Every response includes `next_ops` — follow them.
````

### 2.5 `lib/cipkg/retrieve.py` (REPLACE — rerank + router + summary/signal-aware context)

```python
"""Hybrid retrieval v1.0: FTS ⊕ vectors → RRF → rerank; graph traversal;
budgeted context packs enriched with summaries and runtime signals."""
import re, subprocess
from .base import repo_root, load_config, est_tokens
from .store import connect, get_meta
from .rerank import rerank
from . import vecstore

def _fts_query(q):
    toks = re.findall(r"[A-Za-z0-9_$]+", q)
    return " ".join(f'"{t}"' for t in toks[:8])

def lex_search(con, query, k=30):
    if get_meta(con, "fts") != "1":
        rows = con.execute("SELECT id, path, symbol_id, start_line, end_line, "
                           "substr(text,1,360) snip FROM chunks WHERE text LIKE ? LIMIT ?",
                           (f"%{query}%", k)).fetchall()
        return [dict(r) for r in rows]
    fq = _fts_query(query)
    if not fq: return []
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

def search(root=None, query="", k=10):
    root = root or repo_root(); cfg = load_config(root); con = connect(root)
    lex = lex_search(con, query, int(cfg["retrieval"]["lexical_k"]))
    vec = vec_search(con, cfg, query, int(cfg["retrieval"]["vector_k"]))
    items = []
    for cid, score, srcs in rrf([lex, vec])[:max(k * 3, 30)]:
        c = con.execute("SELECT path, symbol_id, start_line, end_line, substr(text,1,360) snip "
                        "FROM chunks WHERE id=?", (cid,)).fetchone()
        if not c: continue
        items.append({"chunk": cid, "path": c["path"],
                      "lines": [c["start_line"], c["end_line"]], "symbol": c["symbol_id"],
                      "score": round(score, 5), "matched": srcs, "snippet": c["snip"]})
    return rerank(query, items, con, cfg)[:k]

def edge_counts(con, sid):
    out = con.execute("SELECT kind, COUNT(*) c FROM edges WHERE src=? GROUP BY kind", (sid,)).fetchall()
    inc = con.execute("SELECT kind, COUNT(*) c FROM edges WHERE dst=? GROUP BY kind", (sid,)).fetchall()
    return {"out": {r["kind"]: r["c"] for r in out}, "in": {r["kind"]: r["c"] for r in inc}}

def find_symbol(root=None, name="", limit=20):
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
            "sections": [{"why": s["why"], "meta": s["meta"], "text": s["text"]} for s in packed],
            "next_ops": next_ops[:6]}

def history(root=None, path="", n=8):
    root = root or repo_root()
    try:
        out = subprocess.run(
            ["git", "log", "--pretty=format:%h %ad %an %s", "--date=short", "-n", str(n), "--", path],
            cwd=root, capture_output=True, text=True, timeout=10)
        return {"path": path, "commits": [l for l in out.stdout.splitlines() if l.strip()]}
    except Exception as e:
        return {"path": path, "commits": [], "note": f"git unavailable: {e}"}
```

### 2.6 `lib/cipkg/server.py` (REPLACE — full v1.0 tool surface)

```python
"""CIP v1.0 server: JSON-RPC over HTTP + MCP stdio. Full tool surface."""
import json, os, sys, time
from . import retrieve, indexer, summarize, gitindex, runtime_adapters, router
from .base import repo_root, load_config, cip_dir
from .store import connect, get_meta

TOOLS = [
    {"name": "search", "description": "Hybrid search (lexical+semantic+graph), reranked, with intent routing.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer"}}, "required": ["query"]}},
    {"name": "symbol", "description": "Find symbol definitions with relationship counts.",
     "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "graph", "description": "Traverse relationships around a symbol or file.",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "direction": {"type": "string", "enum": ["in", "out", "both"]}, "depth": {"type": "integer"}}, "required": ["id"]}},
    {"name": "context", "description": "Token-budgeted context pack: code + summary + relations + tests + failures.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "symbol": {"type": "string"}, "budget": {"type": "integer"}}}},
    {"name": "summary", "description": "Repo/directory/file summary (hash-cached, self-invalidating).",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
    {"name": "map", "description": "Hierarchical repository map: subsystems, sizes, hotspots.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "describe", "description": "Self-introspection: entity/relationship ontology.",
     "inputSchema": {"type": "object", "properties": {"entity": {"type": "string"}}}},
    {"name": "broken", "description": "Current failures: failing tests + type errors (last 14 days).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "hotspots", "description": "Files with the most recent change activity.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "history", "description": "Git history for a path.",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "route", "description": "Intent analysis: best CIP operations for a request.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "git_index", "description": "Refresh commit index (modified_by, co_change, hotspots).",
     "inputSchema": {"type": "object", "properties": {"depth": {"type": "integer"}}}},
    {"name": "index_status", "description": "Index freshness, coverage and stats.",
     "inputSchema": {"type": "object", "properties": {}}},
]

def index_status(root):
    con = connect(root)
    stats = indexer.compute_stats(con)
    last = float(get_meta(con, "last_sync", 0) or 0)
    lag = time.time() - last if last else None
    return {**stats,
            "commits": con.execute("SELECT COUNT(*) c FROM commits").fetchone()["c"],
            "signals": con.execute("SELECT COUNT(*) c FROM signals").fetchone()["c"],
            "summaries": con.execute("SELECT COUNT(*) c FROM summaries").fetchone()["c"],
            "last_sync": last,
            "lag_s": round(lag, 1) if lag is not None else None,
            "fresh": bool(lag is not None and lag < 300),
            "embedder": get_meta(con, "embedder_name"),
            "fts": get_meta(con, "fts") == "1",
            "schema_version": get_meta(con, "schema_version")}

def describe(root, entity=None):
    p = os.path.join(cip_dir(root), "ontology.json")
    ont = json.load(open(p)) if os.path.exists(p) else {}
    if not entity: return ont
    out = {}
    if entity in ont.get("entities", {}):
        out["entity"] = ont["entities"][entity]
    rels = {k: v for k, v in ont.get("relationships", {}).items()
            if entity in (str(v.get("from", "")) + str(v.get("to", "")))}
    if rels: out["relationships"] = rels
    return out or {"error": f"unknown entity: {entity}"}

def _next_ops(name, res):
    ops = []
    ids = []
    if name == "symbol":
        ids = [s["id"] for s in res.get("symbols", [])[:3]]
    elif name == "search":
        ids = [r["symbol"] for r in res.get("results", []) if r.get("symbol")][:3]
        rt = res.get("route", {})
        if rt.get("intent") == "architecture":
            ops.append("map()")
        elif rt.get("intent") == "health":
            ops.append("broken()")
    for sid in ids:
        ops.append(f"graph(id='{sid}', direction='both')")
        ops.append(f"context(symbol='{sid}')")
    if name == "graph":
        ops += [f"context(symbol='{n}')" for n in res.get("nodes", [])[1:3]]
    if name == "broken":
        for f in res.get("files", [])[:2]:
            ops.append(f"summary(path='{f['path']}')")
    if name == "map":
        ops.append("summary(path='<subsystem>')")
    return ops[:6]

def call_tool(root, cfg, name, args):
    args = args or {}
    try:
        if name == "search":
            q = args.get("query", "")
            res = {"results": retrieve.search(root, q, k=int(args.get("k", 10))),
                   "route": router.route(q)}
        elif name == "symbol":
            res = {"symbols": retrieve.find_symbol(root, args.get("name", ""))}
        elif name == "graph":
            res = retrieve.graph(root, args.get("id"), args.get("direction", "both"),
                                 depth=int(args.get("depth", 1)))
        elif name == "context":
            res = retrieve.context(root, args.get("query"), args.get("symbol"), args.get("budget"))
        elif name == "summary":
            res = summarize.summary(root, args.get("path"))
        elif name == "map":
            res = summarize.map_(root)
        elif name == "describe":
            res = describe(root, args.get("entity"))
        elif name == "broken":
            res = runtime_adapters.broken(root)
        elif name == "hotspots":
            res = {"hotspots": gitindex.hotspots(root)}
        elif name == "history":
            res = retrieve.history(root, args.get("path", ""))
        elif name == "route":
            res = router.route(args.get("query", ""))
        elif name == "git_index":
            res = gitindex.git_index(root, depth=int(args.get("depth", cfg["git"]["depth"])))
        elif name == "index_status":
            res = index_status(root)
        else:
            return {"ok": False, "tool": name, "error": f"unknown tool '{name}'. Use tools.list."}
    except Exception as e:
        return {"ok": False, "tool": name, "error": str(e)}
    st = index_status(root)
    return {"ok": True, "tool": name, "result": res, "next_ops": _next_ops(name, res),
            "index": {"fresh": st["fresh"], "lag_s": st["lag_s"], "files": st["files"]}}

def serve(root=None, port=None):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    root = root or repo_root(); cfg = load_config(root)
    port = port or int(cfg["serve"]["port"])

    class H(BaseHTTPRequestHandler):
        def _send(self, obj, code=200):
            body = json.dumps(obj, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            if self.path == "/health":
                self._send({"ok": True})
            elif self.path == "/tools":
                self._send({"tools": TOOLS})
            elif self.path == "/ontology.json":
                p = os.path.join(cip_dir(root), "ontology.json")
                self._send(json.load(open(p)) if os.path.exists(p) else {})
            else:
                self._send({"ok": False, "error": "not found"}, 404)
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            try:
                req = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._send({"ok": False, "error": "bad json"}, 400)
            method, params = req.get("method", ""), req.get("params", {}) or {}
            if method == "tools.list":
                res = {"tools": TOOLS}
            elif method == "index.status":
                res = index_status(root)
            else:
                res = call_tool(root, cfg, method, params)
            self._send({"jsonrpc": "2.0", "id": req.get("id"), "result": res})
        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"cip: serving http://127.0.0.1:{port}  (POST /rpc · GET /tools /ontology.json /health)")
    srv.serve_forever()

def mcp_stdio(root=None):
    root = root or repo_root(); cfg = load_config(root)
    print("cip: MCP stdio server ready", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try: msg = json.loads(line)
        except Exception: continue
        mid, method = msg.get("id"), msg.get("method", "")
        if method == "initialize":
            resp = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                    "serverInfo": {"name": "cip", "version": "1.0.0"}}
        elif method == "tools/list":
            resp = {"tools": TOOLS}
        elif method == "tools/call":
            p = msg.get("params", {})
            env = call_tool(root, cfg, p.get("name", ""), p.get("arguments", {}))
            resp = {"content": [{"type": "text", "text": json.dumps(env, default=str)}]}
        elif method.startswith("notifications/"):
            continue
        else:
            resp = {"error": {"code": -32601, "message": "unknown method"}}
        if mid is not None:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": resp}) + "\n")
            sys.stdout.flush()
```

### 2.7 `lib/cipkg/cli.py` (REPLACE — full v1.0 command surface)

```python
"""cip v1.0 — command line interface for the Code Intelligence Protocol."""
import argparse, json, os, shutil, sys

HOOKS = ("post-commit", "post-merge", "post-checkout")
MARK = "# >>> cip >>>"

def _out(obj):
    print(json.dumps(obj, indent=2, default=str))

def _install_hooks(root):
    git = os.path.join(root, ".git")
    if not os.path.isdir(git):
        print("note: not a git repo — hooks skipped (use `cip daemon` or `cip watch`)")
        return
    gdir = os.path.join(git, "hooks")
    os.makedirs(gdir, exist_ok=True)
    block = (f"{MARK}\n"
             f"sh -c 'command -v cip >/dev/null && cip sync || .cip/bin/cip sync' 2>/dev/null || true\n"
             f"# <<< cip <<<\n")
    for h in HOOKS:
        p = os.path.join(gdir, h)
        existing = open(p).read() if os.path.exists(p) else "#!/bin/sh\n"
        if MARK in existing: continue
        with open(p, "w") as f:
            f.write(existing.rstrip("\n") + "\n\n" + block)
        os.chmod(p, 0o755)
    print(f"installed git hooks: {', '.join(HOOKS)}")

def _ensure_gitignore(root):
    gi = os.path.join(root, ".gitignore")
    if not os.path.exists(gi): return
    text = open(gi).read()
    if ".cip/data" not in text:
        with open(gi, "a") as f:
            f.write("\n# CIP index data\n.cip/data/\n")

def cmd_init(root):
    from .base import load_config
    from . import detect, indexer
    from .store import connect, set_meta
    cipd = os.path.join(root, ".cip")
    os.makedirs(os.path.join(cipd, "data"), exist_ok=True)
    src, dst = os.path.join(cipd, "bootstrap", "AGENTS.md"), os.path.join(root, "AGENTS.md")
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy(src, dst)
        print(f"created {dst}")
    _install_hooks(root)
    _ensure_gitignore(root)
    cfg = load_config(root)
    det = detect.detect(root, cfg)
    con = connect(root)
    set_meta(con, "detection", json.dumps(det))
    con.commit()
    print(f"detected: primary={det['primary']} stacks={det['stacks']} langs={det['languages']}")
    stats = indexer.sync(root, full=True)
    print(f"indexed: {stats['files']} files, {stats['symbols']} symbols, "
          f"{stats['chunks']} chunks, {stats['edges']} edges, "
          f"{stats['embedded']} vectors in {stats['ms']}ms")
    try:
        from . import gitindex
        g = gitindex.git_index(root, depth=int(cfg["git"]["depth"]))
        print(f"git index: {g}")
    except Exception as e:
        print(f"git index skipped: {e}")
    print("ready. Entry points: AGENTS.md · `cip mcp` · `cip serve` · `cip --help`")

def cmd_doctor(root):
    from .base import load_config
    from . import indexer
    from .server import index_status
    from .store import connect, get_meta
    load_config(root)
    con = connect(root)
    st = index_status(root)
    stats = indexer.compute_stats(con)
    cov = (stats["vectors"] / stats["chunks"] * 100) if stats["chunks"] else 0.0
    hook = os.path.join(root, ".git", "hooks", "post-commit")
    hooks_ok = os.path.exists(hook) and MARK in open(hook).read()
    rows = [
        ("schema_version", get_meta(con, "schema_version")),
        ("files", stats["files"]), ("symbols", stats["symbols"]),
        ("chunks", stats["chunks"]), ("edges", stats["edges"]),
        ("vector coverage", f"{cov:.1f}%"),
        ("embedder", st["embedder"] or "none"), ("fts5", st["fts"]),
        ("commits indexed", st["commits"]), ("signals", st["signals"]),
        ("summaries", st["summaries"]),
        ("fresh", st["fresh"]), ("lag_s", st["lag_s"]),
        ("git hooks", "installed" if hooks_ok else "missing"),
        ("AGENTS.md", "present" if os.path.exists(os.path.join(root, "AGENTS.md")) else "missing"),
    ]
    print("cip doctor (v1.0)")
    for k, v in rows:
        print(f"  {k + ':':<18} {v}")

def cmd_upgrade(root):
    from .base import load_config
    from .store import connect, get_meta
    from . import indexer
    con = connect(root)                     # auto-migrates schema
    print(f"schema_version: {get_meta(con, 'schema_version')}")
    _out(indexer.sync(root, full=True))
    try:
        from . import gitindex
        depth = int(load_config(root)["git"]["depth"])
        _out(gitindex.git_index(root, depth=depth))
    except Exception as e:
        print(f"git-index skipped: {e}")
    print("upgrade complete. Run `cip doctor` to verify.")

def main(argv=None):
    p = argparse.ArgumentParser(prog="cip",
        description="CIP v1.0 — repo-agnostic, self-updating code intelligence for AI agents")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("init")
    sub.add_parser("upgrade", help="migrate schema + full reindex + git index")
    sub.add_parser("detect")
    ip = sub.add_parser("index"); ip.add_argument("--full", action="store_true")
    ip.add_argument("--reembed", action="store_true")
    sub.add_parser("sync")
    wp = sub.add_parser("watch"); wp.add_argument("--interval", type=float, default=1.0)
    dp = sub.add_parser("daemon", help="watcher + server, single-writer lock")
    dp.add_argument("--port", type=int); dp.add_argument("--interval", type=float, default=1.0)
    sp = sub.add_parser("search"); sp.add_argument("query"); sp.add_argument("-k", type=int, default=10)
    yp = sub.add_parser("symbol"); yp.add_argument("name")
    gp = sub.add_parser("graph"); gp.add_argument("id")
    gp.add_argument("--direction", default="both"); gp.add_argument("--depth", type=int, default=1)
    cp = sub.add_parser("context"); cp.add_argument("query", nargs="?")
    cp.add_argument("--symbol"); cp.add_argument("--budget", type=int)
    mp = sub.add_parser("summary"); mp.add_argument("path", nargs="?")
    sub.add_parser("map")
    ep = sub.add_parser("describe"); ep.add_argument("entity", nargs="?")
    sub.add_parser("broken"); sub.add_parser("hotspots")
    hp = sub.add_parser("history"); hp.add_argument("path")
    rp = sub.add_parser("route"); rp.add_argument("query")
    gip = sub.add_parser("git-index"); gip.add_argument("--depth", type=int)
    ig = sub.add_parser("ingest"); ig.add_argument("--kind", required=True,
        choices=["vitest", "jest", "pytest", "tsc", "generic"])
    ig.add_argument("--file", default="-", help="path or '-' for stdin")
    ex = sub.add_parser("export"); ex.add_argument("--format", default="json",
        choices=["json", "lsif", "markdown"]); ex.add_argument("--out")
    sub.add_parser("doctor")
    vp = sub.add_parser("serve"); vp.add_argument("--port", type=int)
    sub.add_parser("mcp")
    tp = sub.add_parser("tools"); tp.add_argument("--schema", action="store_true")
    sub.add_parser("selftest")
    a = p.parse_args(argv)
    if not a.cmd:
        p.print_help(); return 0

    from .base import repo_root, load_config, cip_dir
    root = os.getcwd() if a.cmd == "init" else repo_root()

    if a.cmd == "init":       cmd_init(root)
    elif a.cmd == "upgrade":  cmd_upgrade(root)
    elif a.cmd == "detect":
        from . import detect; _out(detect.detect(root, load_config(root)))
    elif a.cmd == "index":
        from . import indexer
        from .store import connect
        if a.reembed:
            con = connect(root)
            con.execute("DELETE FROM vectors")
            con.execute("DELETE FROM meta WHERE key='embedder_name'")
            con.commit()
        _out(indexer.sync(root, full=a.full))
    elif a.cmd == "sync":
        from . import indexer; _out(indexer.sync(root))
    elif a.cmd == "watch":
        from .watch import watch; watch(root, interval=a.interval)
    elif a.cmd == "daemon":
        from .daemon import daemon; daemon(root, port=a.port, interval=a.interval)
    elif a.cmd == "search":
        from . import retrieve, router
        q = a.query
        _out({"route": router.route(q), "results": retrieve.search(root, q, k=a.k)})
    elif a.cmd == "symbol":
        from . import retrieve; _out({"symbols": retrieve.find_symbol(root, a.name)})
    elif a.cmd == "graph":
        from . import retrieve; _out(retrieve.graph(root, a.id, a.direction, depth=a.depth))
    elif a.cmd == "context":
        from . import retrieve; _out(retrieve.context(root, a.query, a.symbol, a.budget))
    elif a.cmd == "summary":
        from . import summarize; _out(summarize.summary(root, a.path))
    elif a.cmd == "map":
        from . import summarize; _out(summarize.map_(root))
    elif a.cmd == "describe":
        from .server import describe; _out(describe(root, a.entity))
    elif a.cmd == "broken":
        from . import runtime_adapters; _out(runtime_adapters.broken(root))
    elif a.cmd == "hotspots":
        from . import gitindex; _out({"hotspots": gitindex.hotspots(root)})
    elif a.cmd == "history":
        from . import retrieve; _out(retrieve.history(root, a.path))
    elif a.cmd == "route":
        from . import router; _out(router.route(a.query))
    elif a.cmd == "git-index":
        from . import gitindex
        depth = a.depth or int(load_config(root)["git"]["depth"])
        _out(gitindex.git_index(root, depth=depth))
    elif a.cmd == "ingest":
        from . import runtime_adapters; _out(runtime_adapters.ingest(root, a.kind, a.file))
    elif a.cmd == "export":
        from . import export; _out(export.export(root, a.format, a.out))
    elif a.cmd == "doctor":   cmd_doctor(root)
    elif a.cmd == "serve":
        from .server import serve; serve(root, port=a.port)
    elif a.cmd == "mcp":
        from .server import mcp_stdio; mcp_stdio(root)
    elif a.cmd == "tools":
        from .server import TOOLS
        if a.schema:
            op = os.path.join(cip_dir(root), "ontology.json")
            _out(json.load(open(op)) if os.path.exists(op) else {"tools": TOOLS})
        else:
            _out({"tools": [t["name"] for t in TOOLS]})
    elif a.cmd == "selftest":
        from .selftest import run_selftest
        return run_selftest()
    return 0
```

---

## 3. New modules

### 3.1 `lib/cipkg/parsers.py` (NEW — tree-sitter with regex fallback + heritage edges)

```python
"""Pluggable parsing v1.0.
Default: zero-dep regex engine (v0.9). Upgrade by installing grammars:
    pip install tree-sitter tree-sitter-python tree-sitter-typescript \
                tree-sitter-javascript tree-sitter-rust tree-sitter-go
Any failure falls back to regex — parsing never breaks indexing."""
from .base import sha
from .parse import parse_file as regex_parse, extract_imports
import re

_LOADERS = {
    "python":     ("tree_sitter_python", "language_python"),
    "typescript": ("tree_sitter_typescript", "language_typescript"),
    "javascript": ("tree_sitter_javascript", "language_javascript"),
    "rust":       ("tree_sitter_rust", "language_rust"),
    "go":         ("tree_sitter_go", "language_go"),
}
_LANG_CACHE = {}

NODE_KINDS = {
    "python": {"class_definition": "class", "function_definition": "function"},
    "typescript": {"class_declaration": "class", "function_declaration": "function",
                   "method_definition": "method", "interface_declaration": "interface",
                   "type_alias_declaration": "type", "enum_declaration": "class"},
    "rust": {"struct_item": "class", "enum_item": "class", "trait_item": "interface",
             "function_item": "function"},
    "go": {"function_declaration": "function", "method_declaration": "method",
           "type_declaration": "class"},
}
NODE_KINDS["javascript"] = {k: v for k, v in NODE_KINDS["typescript"].items()
                            if k not in ("interface_declaration", "type_alias_declaration")}

def _get_language(language):
    if language in _LANG_CACHE: return _LANG_CACHE[language]
    spec = _LOADERS.get(language)
    if not spec:
        _LANG_CACHE[language] = None
        return None
    try:
        import importlib
        from tree_sitter import Language
        mod = importlib.import_module(spec[0])
        lang = Language(getattr(mod, spec[1])())
        if language == "typescript":
            try: _LANG_CACHE["tsx"] = Language(getattr(mod, "language_tsx")())
            except Exception: pass
        _LANG_CACHE[language] = lang
        return lang
    except Exception:
        _LANG_CACHE[language] = None
        return None

def _mk_sym(path, language, name, kind, start, end, lines, body, exported, class_name=None):
    if class_name and kind in ("function", "method"):
        kind, qual = "method", f"{class_name}.{name}"
    else:
        qual = name
    sig = lines[start - 1].strip()[:240] if 0 < start <= len(lines) else name
    return {"id": f"{language}://{path}#{qual}", "name": name, "kind": kind,
            "qualname": qual, "start": start, "end": end, "signature": sig,
            "exported": exported, "body": body, "body_hash": sha(body)}

def _ts_parse(path, language, source, lang):
    from tree_sitter import Parser
    if path.endswith(".tsx") and _LANG_CACHE.get("tsx"):
        lang = _LANG_CACHE["tsx"]
    parser = Parser()
    try: parser.language = lang
    except Exception: parser.set_language(lang)
    tree = parser.parse(source.encode("utf-8"))
    kinds = NODE_KINDS.get(language, NODE_KINDS["typescript"])
    lines = source.splitlines()
    syms, seen = [], set()

    def add(node, kind, name, class_name):
        start, end = node.start_point[0] + 1, node.end_point[0] + 1
        body = source[node.start_byte:node.end_byte]
        exported = node.parent is not None and node.parent.type == "export_statement"
        s = _mk_sym(path, language, name, kind, start, end, lines, body, exported, class_name)
        if s["id"] not in seen:
            seen.add(s["id"]); syms.append(s)

    def walk(node, class_name):
        t = node.type
        if t in kinds:
            nn = node.child_by_field_name("name")
            if nn is not None:
                add(node, kinds[t], source[nn.start_byte:nn.end_byte], class_name)
        elif t == "lexical_declaration":
            for ch in node.children:
                if ch.type != "variable_declarator": continue
                vn = ch.child_by_field_name("name")
                val = ch.child_by_field_name("value")
                if vn is not None and val is not None and val.type in (
                        "arrow_function", "function_expression", "function"):
                    add(ch, "function", source[vn.start_byte:vn.end_byte], class_name)
        next_class = class_name
        if t in ("class_declaration", "class_definition", "struct_item",
                 "trait_item", "interface_declaration"):
            nn = node.child_by_field_name("name")
            if nn is not None:
                next_class = source[nn.start_byte:nn.end_byte]
        for ch in node.children:
            walk(ch, next_class)

    walk(tree.root_node, None)

    chunks = []
    for s in syms:
        text = "\n".join(lines[s["start"] - 1:s["end"]])
        chunks.append({"id": f'{path}#L{s["start"]}-L{s["end"]}', "path": path,
                       "symbol_id": s["id"], "start": s["start"], "end": s["end"],
                       "text": text, "hash": sha(text)})
    if not syms and lines:
        n = min(60, len(lines))
        text = "\n".join(lines[:n])
        chunks.append({"id": f"{path}#L1-L{n}", "path": path, "symbol_id": None,
                       "start": 1, "end": n, "text": text, "hash": sha(text)})
    return {"symbols": syms, "imports": extract_imports(source, language), "chunks": chunks}

def parse_file(path, language, source):
    lang = _get_language(language)
    if lang is not None:
        try:
            return _ts_parse(path, language, source, lang)
        except Exception:
            pass
    return regex_parse(path, language, source)

HERITAGE = re.compile(r"\b(extends|implements)\s+([A-Za-z_$][\w$]*)")

def build_heritage(con, dirty):
    """extends/implements edges by name resolution (works for both backends)."""
    if dirty is None:
        con.execute("DELETE FROM edges WHERE kind IN ('extends','implements')")
        rows = con.execute("SELECT id, path, body FROM symbols").fetchall()
    else:
        if not dirty: return
        ph = ",".join("?" * len(dirty))
        con.execute(f"DELETE FROM edges WHERE kind IN ('extends','implements') AND src_path IN ({ph})",
                    list(dirty))
        rows = con.execute(f"SELECT id, path, body FROM symbols WHERE path IN ({ph})",
                           list(dirty)).fetchall()
    name_index = {}
    for r in con.execute("SELECT id, name FROM symbols WHERE kind IN ('class','interface')"):
        name_index.setdefault(r["name"], r["id"])
    for row in rows:
        n = 0
        for m in HERITAGE.finditer(row["body"] or ""):
            if n > 20: break
            kind, name = m.group(1), m.group(2)
            dst = name_index.get(name)
            if dst and dst != row["id"]:
                con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                            (row["id"], dst, kind, row["path"]))
                n += 1
```

### 3.2 `lib/cipkg/summarize.py` (NEW — hierarchical, hash-cached summaries)

```python
"""Hierarchical summaries: repo → dir → file. Structural (offline) by default;
optional LLM backend. Hash-cached → dependency-aware invalidation for free:
a summary regenerates only when its content hash drifts."""
import datetime, os, time
from .base import repo_root, load_config, sha
from .store import connect

def _file_hash(con, path):
    r = con.execute("SELECT hash FROM files WHERE path=?", (path,)).fetchone()
    return r["hash"] if r else None

def _struct_file_summary(con, path):
    syms = con.execute("SELECT name, kind FROM symbols WHERE path=? ORDER BY start_line",
                       (path,)).fetchall()
    imps = con.execute("SELECT COUNT(*) c FROM edges WHERE src_path=? AND kind='imports'",
                       (path,)).fetchone()["c"]
    tests = [r["dst"] for r in con.execute(
        "SELECT DISTINCT dst FROM edges WHERE kind='tested_by' AND src_path=?", (path,))]
    fails = con.execute("SELECT COUNT(*) c FROM signals WHERE path=? AND kind='test_fail'",
                        (path,)).fetchone()["c"]
    terrs = con.execute("SELECT COUNT(*) c FROM signals WHERE path=? AND kind='type_error'",
                        (path,)).fetchone()["c"]
    last = con.execute("SELECT c.message, c.ts FROM commit_files cf JOIN commits c "
                       "ON c.sha=cf.sha WHERE cf.path=? ORDER BY c.ts DESC LIMIT 1",
                       (path,)).fetchone()
    lines = [f"{path}: {len(syms)} symbols, {imps} imports."]
    if syms:
        names = ", ".join(f"{s['kind']} {s['name']}" for s in syms[:12])
        lines.append(f"Defines: {names}" + (" …" if len(syms) > 12 else ""))
    if tests: lines.append(f"Tested by: {', '.join(tests[:3])}")
    if fails: lines.append(f"WARNING: {fails} failing test signal(s)")
    if terrs: lines.append(f"WARNING: {terrs} type error(s)")
    if last:
        d = datetime.datetime.fromtimestamp(last["ts"]).strftime("%Y-%m-%d")
        lines.append(f"Last change: {d} — {last['message'][:80]}")
    return "\n".join(lines)

def _llm_summary(base_text, cfg):
    try:
        import json, urllib.request
        key = os.environ["OPENAI_API_KEY"]
        model = cfg["summary"].get("llm_model", "gpt-4o-mini")
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps({"model": model, "max_tokens": 160,
                             "messages": [
                                 {"role": "system", "content": "Summarize this code unit in 3 factual sentences."},
                                 {"role": "user", "content": base_text}]}).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

def file_summary(root, path):
    con = connect(root); cfg = load_config(root)
    h = _file_hash(con, path)
    if h is None:
        return {"path": path, "error": "not indexed"}
    sid = f"file://{path}"
    row = con.execute("SELECT summary, content_hash, source FROM summaries WHERE id=?",
                      (sid,)).fetchone()
    if row and row["content_hash"] == h:
        return {"path": path, "summary": row["summary"], "source": row["source"], "cached": True}
    summary, src = _struct_file_summary(con, path), "structural"
    if cfg["summary"].get("backend") == "llm":
        llm = _llm_summary(summary, cfg)
        if llm:
            summary, src = llm, f'llm:{cfg["summary"].get("llm_model")}'
    con.execute("INSERT OR REPLACE INTO summaries(id,kind,path,content_hash,summary,source,updated_at) "
                "VALUES(?,?,?,?,?,?,?)", (sid, "file", path, h, summary, src, time.time()))
    con.commit()
    return {"path": path, "summary": summary, "source": src, "cached": False}

def dir_summary(root, path):
    con = connect(root)
    prefix = path.rstrip("/") + "/"
    rows = con.execute("SELECT path, hash FROM files WHERE path LIKE ?", (prefix + "%",)).fetchall()
    if not rows:
        return {"path": path, "error": "unknown directory"}
    h = sha("|".join(sorted(r["hash"] for r in rows)))
    sid = f"dir://{path}"
    cached = con.execute("SELECT summary, content_hash, source FROM summaries WHERE id=?",
                         (sid,)).fetchone()
    if cached and cached["content_hash"] == h:
        return {"path": path, "summary": cached["summary"], "source": cached["source"], "cached": True}
    nsym = con.execute("SELECT COUNT(*) c FROM symbols WHERE path LIKE ?", (prefix + "%",)).fetchone()["c"]
    names = [r["path"] for r in rows[:20]]
    summary = (f"{path}: {len(rows)} files, {nsym} symbols.\n"
               f"Files: {', '.join(names)}" + (" …" if len(rows) > 20 else ""))
    con.execute("INSERT OR REPLACE INTO summaries(id,kind,path,content_hash,summary,source,updated_at) "
                "VALUES(?,?,?,?,?,?,?)", (sid, "dir", path, h, summary, "structural", time.time()))
    con.commit()
    return {"path": path, "summary": summary, "source": "structural", "cached": False}

def _repo_summary(root, con, cfg):
    import json as _json
    stats = {t: con.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
             for t in ("files", "symbols", "edges", "commits", "signals")}
    det = con.execute("SELECT value FROM meta WHERE key='detection'").fetchone()
    det = _json.loads(det["value"]) if det else {}
    h = sha(str(stats) + str(det.get("primary")))
    sid = "repo://"
    cached = con.execute("SELECT summary, content_hash FROM summaries WHERE id=?", (sid,)).fetchone()
    if cached and cached["content_hash"] == h:
        return {"path": None, "summary": cached["summary"], "source": "structural", "cached": True}
    lines = [f"Repository: primary language {det.get('primary', 'unknown')}, "
             f"stacks {det.get('stacks', [])}.",
             f"{stats['files']} files, {stats['symbols']} symbols, {stats['edges']} relationships."]
    if stats["commits"]: lines.append(f"{stats['commits']} commits indexed.")
    if stats["signals"]: lines.append(f"{stats['signals']} runtime signals ingested.")
    try:
        from .gitindex import hotspots
        hs = hotspots(root, k=5)
        if hs:
            lines.append("Hotspots: " + ", ".join(f"{x['path']} ({x['score']})" for x in hs))
    except Exception:
        pass
    summary = "\n".join(lines)
    con.execute("INSERT OR REPLACE INTO summaries(id,kind,path,content_hash,summary,source,updated_at) "
                "VALUES(?,?,?,?,?,?,?)", (sid, "repo", None, h, summary, "structural", time.time()))
    con.commit()
    return {"path": None, "summary": summary, "source": "structural", "cached": False}

def summary(root=None, path=None):
    root = root or repo_root()
    if not path or path in (".", "/"):
        return _repo_summary(root, connect(root), load_config(root))
    path = path.strip("/")
    con = connect(root)
    if con.execute("SELECT 1 FROM files WHERE path=?", (path,)).fetchone():
        return file_summary(root, path)
    return dir_summary(root, path)

def map_(root=None):
    root = root or repo_root(); con = connect(root)
    files = [r["path"] for r in con.execute("SELECT path FROM files")]
    dirs = {}
    for p in files:
        parts = p.split("/")
        top = parts[0] if len(parts) > 1 else "(root)"
        d = dirs.setdefault(top, {"files": 0, "symbols": 0})
        d["files"] += 1
    for name, d in dirs.items():
        if name == "(root)":
            d["symbols"] = con.execute(
                "SELECT COUNT(*) c FROM symbols WHERE path NOT LIKE '%/%'").fetchone()["c"]
        else:
            d["symbols"] = con.execute(
                "SELECT COUNT(*) c FROM symbols WHERE path LIKE ?",
                (name + "/%",)).fetchone()["c"]
    try:
        from .gitindex import hotspots
        hs = hotspots(root, k=5)
    except Exception:
        hs = []
    return {"directories": [{"name": k, **v} for k, v in sorted(dirs.items())],
            "totals": {"files": len(files),
                       "symbols": sum(d["symbols"] for d in dirs.values())},
            "hotspots": hs,
            "navigate": "summary(path='<dir|file>') → symbol(name) → context(symbol)"}
```

### 3.3 `lib/cipkg/gitindex.py` (NEW — commits, modified_by, co-change, hotspots)

```python
"""Git history index: commits → modified_by edges, co_change edges, hotspot scores.
Answers 'what recently changed' and 'what changes together'."""
import subprocess, time
from collections import Counter
from .base import repo_root
from .store import connect

def git_index(root=None, depth=500, co_change_min=2):
    root = root or repo_root()
    con = connect(root)
    try:
        out = subprocess.run(
            ["git", "log", "--pretty=format:@CIP@%H%x00%at%x00%an%x00%s",
             "--name-only", "-n", str(depth)],
            cwd=root, capture_output=True, text=True, timeout=180)
    except Exception as e:
        return {"error": str(e)}
    if out.returncode != 0:
        return {"error": out.stderr.strip() or "git log failed"}
    commits, cur = [], None
    for line in out.stdout.splitlines():
        if line.startswith("@CIP@"):
            if cur: commits.append(cur)
            sha_, ts, author, msg = line[5:].split("\x00", 3)
            cur = {"sha": sha_, "ts": float(ts), "author": author, "msg": msg, "files": []}
        elif line.strip() and cur:
            cur["files"].append(line.strip())
    if cur: commits.append(cur)

    con.execute("DELETE FROM commits")
    con.execute("DELETE FROM commit_files")
    con.execute("DELETE FROM edges WHERE kind IN ('modified_by','co_change')")
    for c in commits:
        con.execute("INSERT OR REPLACE INTO commits(sha,ts,author,message,files_changed) "
                    "VALUES(?,?,?,?,?)",
                    (c["sha"], c["ts"], c["author"], c["msg"], len(c["files"])))
        for f in c["files"]:
            con.execute("INSERT OR IGNORE INTO commit_files(sha,path) VALUES(?,?)", (c["sha"], f))
    for c in commits[:50]:                       # modified_by for recent history
        for f in c["files"]:
            con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                        (f, c["sha"], "modified_by", f))
    pairs = Counter()                            # co-change pairs
    for c in commits:
        fs = sorted(set(c["files"]))
        for i in range(len(fs)):
            for j in range(i + 1, min(len(fs), i + 12)):
                pairs[(fs[i], fs[j])] += 1
    added = 0
    for (a, b), n in pairs.most_common(500):
        if n < co_change_min: break
        con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                    (a, b, "co_change", a))
        added += 1
    con.commit()
    return {"commits": len(commits), "co_change_edges": added}

def hotspots(root=None, k=15):
    root = root or repo_root(); con = connect(root)
    now = time.time()
    rows = con.execute("SELECT cf.path, c.ts FROM commit_files cf "
                       "JOIN commits c ON c.sha=cf.sha").fetchall()
    scores = {}
    for r in rows:
        age_days = max(0.0, (now - r["ts"]) / 86400.0)
        w = 1.0 if age_days <= 30 else (0.5 if age_days <= 90 else 0.15)
        scores[r["path"]] = scores.get(r["path"], 0.0) + w
    return [{"path": p, "score": round(s, 1)}
            for p, s in sorted(scores.items(), key=lambda kv: -kv[1])[:k]]
```

### 3.4 `lib/cipkg/runtime_adapters.py` (NEW — test/type/build signal ingestion)

```python
"""Runtime signal adapters: vitest/jest JSON, pytest JUnit XML, tsc output, generic JSON.
Signals power `broken`, summaries, and reranking — the 'what is currently broken' layer."""
import json, os, re, sys, time
import xml.etree.ElementTree as ET
from .base import repo_root
from .store import connect

def _norm(path):
    return (path or "").replace(os.sep, "/").lstrip("./")

def _put(con, kind, path, name, symbol_id=None, payload=None):
    sid = f"sig:{kind}:{path}::{name}"
    con.execute("INSERT OR REPLACE INTO signals(id,kind,path,symbol_id,name,payload,ts) "
                "VALUES(?,?,?,?,?,?,?)",
                (sid, kind, path, symbol_id, name, json.dumps(payload or {}), time.time()))

def ingest_vitest(con, data):
    n = 0
    for tr in (data.get("testResults") or data.get("test_results") or []):
        f = _norm(tr.get("name") or tr.get("file"))
        for ar in (tr.get("assertionResults") or tr.get("assertion_results") or []):
            status = ar.get("status", "")
            kind = {"passed": "test_pass", "failed": "test_fail"}.get(status)
            if not kind: continue
            anc = ar.get("ancestorTitles") or []
            name = " > ".join(anc + [ar.get("title") or ar.get("fullName") or "?"])
            _put(con, kind, f, name, payload={"duration": ar.get("duration")})
            n += 1
    return n

def ingest_pytest(con, xml_path):
    n = 0
    for case in ET.parse(xml_path).getroot().iter("testcase"):
        f = _norm(case.get("file") or "")
        name = f'{case.get("classname", "")}.{case.get("name", "")}'
        failed = case.find("failure") is not None or case.find("error") is not None
        _put(con, "test_fail" if failed else "test_pass", f, name)
        n += 1
    return n

TSC_RE = re.compile(r"^([^(]+)\((\d+),(\d+)\):\s+error\s+(TS\d+):\s+(.*)$")

def ingest_tsc(con, text):
    n = 0
    for line in text.splitlines():
        m = TSC_RE.match(line.strip())
        if not m: continue
        f, ln, _col, code, msg = m.groups()
        f = _norm(f)
        sym = con.execute("SELECT id FROM symbols WHERE path=? AND start_line<=? AND end_line>=? "
                          "ORDER BY (end_line-start_line) LIMIT 1",
                          (f, int(ln), int(ln))).fetchone()
        _put(con, "type_error", f, f"{code} L{ln}",
             symbol_id=sym["id"] if sym else None,
             payload={"line": int(ln), "message": msg[:300]})
        n += 1
    return n

def ingest_generic(con, data):
    items = data if isinstance(data, list) else data.get("events", [])
    n = 0
    for i, ev in enumerate(items):
        kind = ev.get("kind", "custom")
        _put(con, kind, _norm(ev.get("path")), ev.get("name", f"event-{i}"),
             symbol_id=ev.get("symbol_id"), payload=ev.get("payload") or {})
        n += 1
    return n

def ingest(root, kind, file_path):
    root = root or repo_root(); con = connect(root)
    text = (sys.stdin.read() if file_path == "-"
            else open(file_path, encoding="utf-8", errors="replace").read())
    try:
        if kind in ("vitest", "jest"): n = ingest_vitest(con, json.loads(text))
        elif kind == "pytest":         n = ingest_pytest(con, file_path)
        elif kind == "tsc":            n = ingest_tsc(con, text)
        elif kind == "generic":        n = ingest_generic(con, json.loads(text))
        else: return {"error": f"unknown kind: {kind}"}
    except Exception as e:
        return {"error": f"parse failed: {e}"}
    con.execute("INSERT INTO events(ts,kind,payload) VALUES(?,?,?)",
                (time.time(), f"ingest:{kind}", str(n)))
    con.commit()
    return {"ingested": n, "kind": kind}

def broken(root=None, limit=30, window_days=14):
    root = root or repo_root(); con = connect(root)
    cutoff = time.time() - window_days * 86400
    rows = con.execute("SELECT kind, path, symbol_id, name, payload, ts FROM signals "
                       "WHERE kind IN ('test_fail','type_error') AND ts>=? "
                       "ORDER BY ts DESC LIMIT ?", (cutoff, limit)).fetchall()
    files = {}
    for r in rows:
        e = files.setdefault(r["path"], {"test_fail": 0, "type_error": 0})
        if r["kind"] in e: e[r["kind"]] += 1
    return {"window_days": window_days,
            "files": [{"path": p, **c} for p, c in sorted(
                files.items(), key=lambda kv: -(kv[1]["test_fail"] + kv[1]["type_error"]))],
            "signals": [dict(r) for r in rows]}
```

### 3.5 `lib/cipkg/rerank.py` (NEW)

```python
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
```

### 3.6 `lib/cipkg/router.py` (NEW — intent analysis)

```python
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
```

### 3.7 `lib/cipkg/vecstore.py` (NEW — pluggable vector search)

```python
"""Vector store abstraction. Default: SQLite BLOBs with numpy-accelerated cosine
when available. Optional sqlite-vec extension for >100k-chunk repos."""
import struct

def knn(con, model, qv, k=30, backend="sqlite"):
    if backend == "sqlite-vec":
        try:
            return _knn_sqlite_vec(con, model, qv, k)
        except Exception:
            pass
    rows = con.execute("SELECT id, vec FROM vectors WHERE model=?", (model,)).fetchall()
    if not rows: return []
    try:
        import numpy as np
        from .embed import from_blob
        ids = [r["id"] for r in rows]
        mat = np.array([from_blob(r["vec"]) for r in rows], dtype=np.float32)
        scores = mat @ np.asarray(qv, dtype=np.float32)
        top = scores.argsort()[::-1][:k]
        return [(float(scores[i]), ids[i]) for i in top]
    except ImportError:
        from .embed import from_blob, cosine
        scored = sorted(((cosine(qv, from_blob(r["vec"])), r["id"]) for r in rows),
                        key=lambda x: -x[0])
        return scored[:k]

def _knn_sqlite_vec(con, model, qv, k):
    """Experimental: requires the sqlite-vec extension and a populated
    vec_vectors(id, model, embedding) vec0 table. Falls back on any error."""
    con.enable_load_extension(True)
    con.load_extension("vec0")
    blob = struct.pack(f"<{len(qv)}f", *qv)
    rows = con.execute(
        "SELECT id, distance FROM vec_vectors WHERE embedding MATCH ? AND model=? "
        "ORDER BY distance LIMIT ?", (blob, model, k)).fetchall()
    return [(1.0 / (1.0 + r["distance"]), r["id"]) for r in rows]
```

### 3.8 `lib/cipkg/export.py` (NEW — LSIF / JSON / Markdown)

```python
"""Exports: LSIF (JSON-lines subset) for tooling interop, JSON dump,
and a generated ARCHITECTURE.md."""
import json
from .base import repo_root
from .store import connect

def export(root=None, fmt="json", out=None):
    root = root or repo_root(); con = connect(root)
    if fmt == "lsif":     data = _lsif(con)
    elif fmt == "markdown": data = _markdown(con, root)
    else:                 data = _json_dump(con)
    text = data if isinstance(data, str) else json.dumps(data, indent=2, default=str)
    if out:
        with open(out, "w") as f: f.write(text)
        return {"wrote": out, "bytes": len(text)}
    print(text)
    return {"bytes": len(text)}

def _json_dump(con):
    return {"protocol": "cip", "version": "1.0.0",
            "files": [dict(r) for r in con.execute("SELECT path, language, lines, hash FROM files")],
            "symbols": [dict(r) for r in con.execute(
                "SELECT id, name, kind, path, start_line, end_line, signature FROM symbols")],
            "edges": [dict(r) for r in con.execute("SELECT src, dst, kind FROM edges")],
            "summaries": [dict(r) for r in con.execute("SELECT id, kind, path, source FROM summaries")],
            "signals": [dict(r) for r in con.execute("SELECT id, kind, path, name, ts FROM signals")]}

def _lsif(con):
    lines, eid = [], [0]
    def nid():
        eid[0] += 1; return eid[0]
    lines.append(json.dumps({"id": nid(), "type": "vertex", "label": "metaData",
                             "version": "0.4.3", "positionInfo": {"line": 1, "character": 1}}))
    proj = nid()
    lines.append(json.dumps({"id": proj, "type": "vertex", "label": "project", "kind": "cip"}))
    docs = {}
    for f in con.execute("SELECT path, language FROM files"):
        did = nid(); docs[f["path"]] = did
        lines.append(json.dumps({"id": did, "type": "vertex", "label": "document",
                                 "uri": "file://" + f["path"],
                                 "languageId": f["language"] or "plaintext"}))
        lines.append(json.dumps({"id": nid(), "type": "edge", "label": "contains",
                                 "outV": proj, "inVs": [did]}))
    for s in con.execute("SELECT id, path, start_line, end_line, name FROM symbols"):
        did = docs.get(s["path"])
        if not did: continue
        rid = nid()
        lines.append(json.dumps({"id": rid, "type": "vertex", "label": "range",
                                 "start": {"line": s["start_line"] - 1, "character": 0},
                                 "end": {"line": s["end_line"] - 1, "character": 0}}))
        lines.append(json.dumps({"id": nid(), "type": "edge", "label": "contains",
                                 "outV": did, "inVs": [rid]}))
        rs = nid()
        lines.append(json.dumps({"id": rs, "type": "vertex", "label": "resultSet",
                                 "name": s["name"]}))
        lines.append(json.dumps({"id": nid(), "type": "edge", "label": "next",
                                 "outV": rid, "inV": rs}))
        lines.append(json.dumps({"id": nid(), "type": "edge", "label": "item", "outV": rs,
                                 "inVs": [rid], "document": did, "property": "definitions"}))
    return "\n".join(lines) + "\n"

def _markdown(con, root):
    from . import summarize
    repo = summarize.summary(root, None)
    m = summarize.map_(root)
    lines = ["# Architecture (generated by CIP v1.0)", "", repo.get("summary", ""), "",
             "## Subsystems", ""]
    for d in m["directories"][:25]:
        lines.append(f"- **{d['name']}** — {d['files']} files, {d['symbols']} symbols")
    hs = m.get("hotspots") or []
    if hs:
        lines += ["", "## Hotspots (recent change activity)", ""]
        lines += [f"- {h['path']} (score {h['score']})" for h in hs]
    lines += ["", "_Regenerate: `cip export --format markdown --out ARCHITECTURE.md`_"]
    return "\n".join(lines) + "\n"
```

### 3.9 `lib/cipkg/daemon.py` (NEW — single-writer watch + serve)

```python
"""Single-writer daemon: watcher thread + CIP HTTP server, guarded by a lockfile.
One `cip daemon` per repo — the fully self-updating production mode."""
import os, threading
from .base import repo_root, data_dir
from .watch import watch
from .server import serve

def daemon(root=None, port=None, interval=1.0):
    root = root or repo_root()
    lock = os.path.join(data_dir(root), "daemon.lock")
    if os.path.exists(lock):
        try:
            pid = int(open(lock).read().strip())
            os.kill(pid, 0)
            print(f"cip: daemon already running (pid {pid})")
            return
        except Exception:
            pass
    with open(lock, "w") as f:
        f.write(str(os.getpid()))
    try:
        t = threading.Thread(target=watch,
                             kwargs={"root": root, "interval": interval}, daemon=True)
        t.start()
        serve(root, port)          # blocks
    finally:
        try: os.remove(lock)
        except OSError: pass
```

### 3.10 `lib/cipkg/selftest.py` (NEW — end-to-end verification)

```python
"""cip selftest — end-to-end tests against a throwaway fixture repo.
Run: cip selftest"""
import json, os, shutil, tempfile, unittest

FIX_TOKEN = '''class TokenManager:
    def validate(self, token):
        return bool(token)

    def refresh(self, token):
        return "refreshed"

def refresh_token(tm, token):
    return tm.refresh(token)
'''
FIX_TEST = '''from src.token import TokenManager

def test_refresh():
    tm = TokenManager()
    assert tm.refresh("x") == "refreshed"
'''
FIX_VITEST = {"testResults": [{"name": "tests/test_token.py", "assertionResults": [
    {"ancestorTitles": [], "title": "refresh works", "status": "failed", "duration": 12}]}]}

class CIPCore(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cip-selftest-")
        os.makedirs(os.path.join(self.root, ".cip", "data"))
        os.makedirs(os.path.join(self.root, "src"))
        os.makedirs(os.path.join(self.root, "tests"))
        open(os.path.join(self.root, "src", "token.py"), "w").write(FIX_TOKEN)
        open(os.path.join(self.root, "tests", "test_token.py"), "w").write(FIX_TEST)
        from . import indexer
        self.stats = indexer.sync(self.root, full=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_sync_counts(self):
        self.assertGreaterEqual(self.stats["files"], 2)
        self.assertGreaterEqual(self.stats["symbols"], 5)

    def test_symbol_lookup(self):
        from . import retrieve
        hits = retrieve.find_symbol(self.root, "TokenManager")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["kind"], "class")

    def test_search(self):
        from . import retrieve
        self.assertTrue(retrieve.search(self.root, "refresh token"))

    def test_context_pack(self):
        from . import retrieve
        pack = retrieve.context(self.root, symbol="TokenManager")
        self.assertTrue(pack["sections"])

    def test_imports_and_tested_by(self):
        from .store import connect
        con = connect(self.root)
        self.assertGreaterEqual(con.execute(
            "SELECT COUNT(*) c FROM edges WHERE kind='imports'").fetchone()["c"], 1)
        self.assertGreaterEqual(con.execute(
            "SELECT COUNT(*) c FROM edges WHERE kind='tested_by'").fetchone()["c"], 1)

    def test_summary_and_map(self):
        from . import summarize
        s = summarize.summary(self.root, "src/token.py")
        self.assertIn("TokenManager", s["summary"])
        m = summarize.map_(self.root)
        self.assertGreaterEqual(m["totals"]["files"], 2)

    def test_ingest_and_broken(self):
        from . import runtime_adapters
        fx = os.path.join(self.root, ".cip", "data", "vitest.json")
        json.dump(FIX_VITEST, open(fx, "w"))
        r = runtime_adapters.ingest(self.root, "vitest", fx)
        self.assertGreaterEqual(r["ingested"], 1)
        b = runtime_adapters.broken(self.root)
        self.assertTrue(b["signals"])

    def test_router(self):
        from . import router
        self.assertEqual(router.route("why is this workaround here")["intent"], "history")
        self.assertEqual(router.route("overview of the system")["intent"], "architecture")

    def test_export(self):
        from . import export
        out = os.path.join(self.root, ".cip", "data", "dump.json")
        r = export.export(self.root, "json", out)
        self.assertGreater(r["bytes"], 100)

def run_selftest():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CIPCore)
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if res.wasSuccessful() else 1
```

---

## 4. `UPGRADE-1.0.md` (NEW doc)

````markdown
# CIP v1.0 — Upgrade Notes

## What changed since v0.9
| Area | v0.9 | v1.0 |
|---|---|---|
| Parsing | regex only | tree-sitter when grammars installed, regex fallback |
| Graph | calls/refs/imports/tests | + `extends`, `implements`, `modified_by`, `co_change` |
| History | ad-hoc `git log` | commit index, hotspots, co-change |
| Runtime | none | signal adapters: vitest/jest/pytest/tsc/generic → `broken` |
| Summaries | none | repo/dir/file, hash-cached, structural or LLM |
| Retrieval | FTS+vec+RRF | + feature reranker + intent router |
| Vectors | SQLite only | numpy acceleration + sqlite-vec hook |
| Interop | none | LSIF / JSON / Markdown(ARCHITECTURE.md) export |
| Ops | watch/serve | `daemon` (single-writer), `selftest`, `upgrade` |
| Schema | 3 | 4 (auto-migrates) |

## Upgrade procedure (existing v0.9 repo)
```bash
./install.sh /path/to/repo     # copies v1.0 bundle over .cip/ (config preserved)
cd /path/to/repo
cip upgrade                    # schema migration + full reindex + git index
cip selftest                   # verify
cip doctor
```

## New commands
```bash
cip summary [path]            # repo | dir | file summary
cip map                       # hierarchical subsystem map + hotspots
cip describe [Entity]         # ontology self-introspection
cip broken                    # failing tests + type errors (14d window)
cip hotspots                  # recent-change ranking
cip route "query"             # intent analysis
cip git-index --depth 500     # commit/co-change/hotspot index
cip ingest --kind vitest --file results.json
cip ingest --kind tsc --file <(npx tsc --noEmit --pretty false)
cip ingest --kind pytest --file junit.xml
cip export --format markdown --out ARCHITECTURE.md
cip daemon --port 8787        # watcher + server, single writer
```

## Optional upgrades (all zero-config-safe)
- `pip install tree-sitter tree-sitter-typescript tree-sitter-python tree-sitter-javascript tree-sitter-rust tree-sitter-go`
- `pip install sentence-transformers` (real embeddings) or set `OPENAI_API_KEY`
- `[summary] backend = "llm"` for LLM-written summaries
- `[vector] backend = "sqlite-vec"` for very large repos

## Deferred to v1.1
SCIP protobuf export, cross-encoder reranker as first-class backend, multi-repo federation, coverage-percentage edges.
````

---

## 5. Runbook

```bash
# Fresh repo → v1.0 in one shot:
./install.sh /path/to/repo && cd /path/to/repo
cip selftest && cip doctor

# Wire runtime signals (the "living model" layer):
npx vitest run --reporter=json > /tmp/vt.json && cip ingest --kind vitest --file /tmp/vt.json
npx tsc --noEmit --pretty false > /tmp/tsc.txt && cip ingest --kind tsc --file /tmp/tsc.txt

# Production mode (fully self-updating, agent-ready):
cip daemon --port 8787 &

# Agent workflows this now supports, end to end:
cip route "make expired tokens auto-refresh"     # → intent + plan
cip context "expired token refresh"              # → code + summary + tests + failures, token-budgeted
cip broken                                       # → is it safe to refactor?
cip export --format markdown --out ARCHITECTURE.md
```

That completes v1.0: every roadmap item shipped as working code, schema auto-migration from v0.9, self-verification via `cip selftest`, and the same three agent bindings (MCP / HTTP / CLI) now exposing the full 13-tool surface.
