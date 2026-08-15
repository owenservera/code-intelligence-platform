# CIP — Assessment, Enhancements & the Complete Drop‑In System

---

## 1. Assessment of the attached design

**Verdict: the architecture is directionally correct and frontier-grade.** It matches where serious code-agent infrastructure is heading (AST + graph + embeddings + reranking + incremental invalidation + self-describing protocol). What it is *not yet* is an engineering artifact: it's a philosophy without a wire format, a schema, or a cold-start path.

| Dimension | Rating | Notes |
|---|---|---|
| Multi-index model (files/symbols/graph/vectors) | ✅ Strong | Correct rejection of "embeddings-only RAG" |
| Incremental + dependency-aware invalidation | ✅ Strong concept | Underspecified: no hash discipline, no correctness rules |
| Hybrid retrieval (BM25 ⊕ vec ⊕ graph) | ✅ Strong | Missing fusion algorithm + context budget |
| Agent ergonomics (bootstrap, capability discovery) | ✅ Excellent | The "index as teacher" idea is the best insight in the doc |
| Concretization | ❌ Weak | No protocol, no schemas, no storage layout, no failure modes |
| Portability / cold start | ❌ Missing | Nothing about language detection, zero-dep operation, offline mode |
| Operability | ❌ Missing | No health checks, freshness contract, observability |

---

## 2. Enhancements identified (each one is implemented below)

1. **No wire protocol** → formalize CIP as JSON-RPC 2.0 over HTTP **and** MCP stdio, with a versioned envelope (`ok / tool / result / next_ops / index`).
2. **No cold-start story** → auto language/framework **detector** + regex symbol engine with **zero hard dependencies**, so it works in *any* repo on day one; tree-sitter is an upgrade, not a requirement.
3. **No offline guarantee** → deterministic **hashing embedder** as default; escalates to sentence-transformers → OpenAI only when available. Index always functions (FTS + graph) even with no embeddings.
4. **Invalidation underspecified** → content hashes at file/symbol/chunk level, mtime fast-path, `src_path`-scoped edge replacement, embedder-version pruning, orphan vector GC.
5. **No context budget** → **budgeted context packer**: seed code → tests → caller/callee signatures → file header, packed by priority into a token budget.
6. **Agent misuse not prevented** → every tool response carries **`next_ops`** (the tool teaches the agent), plus a tiny `AGENTS.md` bootstrap.
7. **No freshness contract** → envelope exposes `fresh`/`lag_s`; staleness enforced by git hooks (`post-commit/merge/checkout`) + polling watcher.
8. **No observability** → `cip doctor`: counts, vector coverage, lag, hooks, embedder, schema version; `events` audit table.
9. **History is hand-wavy** → `history` tool shells to git log per path (the "why does this exist" layer).
10. **Runtime signals vague** → `events` table + documented adapter contract (test runners / type checkers emit JSON events) — scaffolded for v1.
11. **FTS availability risk** → runtime FTS5 probe with LIKE fallback (works on crippled SQLite builds).
12. **Missing interop path** → extension points documented for SCIP/LSIF export and pluggable rerankers (roadmap).

---


## 3. The formal system: **CIP v0.9** (Code Intelligence Protocol)

**Contract:** drop `.cip/` into any repo → run one command → any agent (MCP, HTTP, or CLI) gets a live, self-updating semantic model of that repo.

```
ANY REPO ──▶ detector ──▶ incremental indexer ──▶ stores
              (langs)      (AST/regex, hashes)     ├─ SQLite: files/symbols/chunks+FTS5
                           ▲                       ├─ edges table (typed graph)
              watcher + git hooks                  └─ vectors (pluggable embedder)
              (self-updating)                              │
                                                           ▼
                            retriever: FTS ⊕ vector ⊕ graph → RRF → budgeted pack
                                                           │
                            CIP server: MCP stdio │ HTTP JSON-RPC │ CLI
                                                           │
                                              ANY AI CODING AGENT
```

**What lands in the target repo:**

```
repo/
├── AGENTS.md                  ← 30-line bootstrap for any agent
└── .cip/
    ├── bin/cip                ← CLI entry
    ├── lib/cipkg/*.py         ← the engine (pure stdlib core)
    ├── config.toml            ← tunables
    ├── ontology.json          ← self-describing schema (agent introspection)
    ├── bootstrap/AGENTS.md
    └── data/                  ← gitignored: index.db (WAL) + vectors
```

---

## 4. Core docs

### 4.1 `README.md`

````markdown
# CIP — Code Intelligence Protocol

Drop-in, repo-agnostic, self-updating repository intelligence for AI coding agents.
One folder. Zero hard dependencies (Python ≥ 3.9). Any language. Any agent.

## Quickstart

```bash
./install.sh /path/to/any-repo     # installs .cip/, detects, fully indexes,
                                   # writes AGENTS.md, installs git hooks
```

That's the entire setup. The index now updates itself via git hooks; for live
updates run `cip watch` in a terminal/daemon.

## Point your agent at it

**MCP (Claude Code, OpenCode, Kilo, custom agents):**
```json
{ "mcpServers": { "cip": { "command": "<repo>/.cip/bin/cip", "args": ["mcp"] } } }
```

**HTTP:**
```bash
cip serve --port 8787
curl -s localhost:8787/rpc -d '{"method":"search","params":{"query":"token refresh"}}'
curl -s localhost:8787/ontology.json     # agent self-discovers the schema
```

**CLI (works everywhere, including dumb shells):**
```bash
cip search "how does auth recover from expired tokens"
cip symbol TokenManager
cip context "expired token refresh" --budget 6000
cip history src/auth/token.ts
cip doctor
```

## What you get

| Layer | Implementation |
|---|---|
| File index | paths, languages, sizes, content hashes |
| Symbol index | classes/functions/methods/interfaces/types, qualified IDs (`ts://src/a.ts#Foo.bar`) |
| Relationship graph | contains, imports, exports, calls, references, tested_by |
| Semantic index | symbol-level chunks + pluggable embeddings (offline default) |
| Lexical index | SQLite FTS5 (LIKE fallback) |
| Retrieval | RRF fusion of FTS + vectors, graph expansion, token-budgeted context packs |
| Freshness | mtime/hash incremental sync, git hooks, watcher, staleness in every response |
| History | per-path git log via `history` tool |
| Introspection | `ontology.json`, `tools --schema`, `next_ops` in every response |

## How it stays fresh

- File hashes + mtime fast path → only changed files are reparsed.
- Symbols/chunks are content-hashed → only changed units are re-embedded.
- Edges are rebuilt scoped to changed files (`src_path`), never globally.
- Git hooks run `cip sync` on commit/merge/checkout; `cip watch` polls otherwise.
- Every response says `"fresh": true|false` and `lag_s` — agents can trust or re-sync.

## Configuration (`.cip/config.toml`)

| Key | Default | Meaning |
|---|---|---|
| `index.max_file_kb` | 512 | skip larger files |
| `index.exclude` | [] | extra substring/glob excludes |
| `index.test_globs` | see file | substring markers identifying tests |
| `embed.backend` | auto | `auto|hashing|sentence-transformers|openai` |
| `embed.model` | all-MiniLM-L6-v2 | for sentence-transformers |
| `retrieval.context_budget_tokens` | 6000 | default context pack budget |
| `serve.port` | 8787 | HTTP port |

## Requirements
Python ≥ 3.9, nothing else. Optional upgrades: `sentence-transformers`
(real embeddings), `OPENAI_API_KEY` (API embeddings). SQLite FTS5 recommended
(auto-detected; graceful fallback included).
````

### 4.2 `SPEC.md`

````markdown
# CIP SPEC v0.9

## 1. Design laws
1. **Repo-agnostic**: detection is automatic; unknown languages degrade to a generic extractor, never crash.
2. **Offline-first**: full functionality with zero network, zero pip installs.
3. **Index = structure, source = truth**: the index never claims authority over implementation text.
4. **Every response teaches**: `next_ops` tell the agent the best next move.
5. **Freshness is explicit**: staleness is surfaced, never hidden.

## 2. Identifiers
- Symbol:  `<language>://<path>#<Qualified.name>`   e.g. `typescript://src/runtime/engine.ts#EngineRegistry.resolve`
- Chunk:   `<path>#L<start>-L<end>`
- Edge:    `(src, dst, kind)` with `src_path` for scoped invalidation.

## 3. Ontology (mirrored in `ontology.json`)
Entities: `File`, `Symbol` (kinds: class, function, method, interface, type, const, module, test), `Chunk`, `Commit`.
Relationships: `contains`, `exports`, `imports`, `calls`, `references`, `extends`, `implements`, `tested_by`, `modified_by`.

## 4. Tool contract
| Tool | Input | Output |
|---|---|---|
| `search` | `query`, `k?` | fused chunks: path, lines, symbol, score, matched sources |
| `symbol` | `name` | definitions + relationship counts |
| `graph` | `id`, `direction?`, `depth?` | nodes + typed edges (cap 200/400) |
| `context` | `query? | symbol?`, `budget?` | priority-packed sections + used_tokens |
| `history` | `path` | recent commits for the path |
| `index_status` | — | counts, lag, freshness, embedder, schema version |

**Envelope (every response):**
```json
{ "ok": true, "tool": "search",
  "result": { },
  "next_ops": ["graph(id='...')", "context(symbol='...')"],
  "index": { "fresh": true, "lag_s": 3.2, "files": 812 } }
```

## 5. Freshness contract
`fresh = lag_s < 300`. Enforced by git hooks + `cip watch` + on-demand `cip sync`.
Agents SHOULD re-run `cip sync` when `fresh == false`.

## 6. Incrementality & invalidation
- File: sha256(content) + mtime fast-path.
- Chunk/symbol: content hash; only changed units re-embedded.
- Edges: deleted/rebuilt only for `src_path ∈ dirty set`; `dst`-side edges cleaned on file deletion.
- Vectors: keyed by embedder version; stale-model and orphan vectors are pruned.
- `cip index --reembed` forces full re-embedding after backend change.

## 7. Retrieval pipeline
`FTS5 (BM25) ⊕ vector cosine → RRF (k=60) → graph expansion (context tool) → priority packing under token budget`.
Priorities: seed source(0) → tests(1) → caller/callee signatures(2) → siblings/imports(3).

## 8. Bindings
- **MCP stdio**: `cip mcp` — `initialize`, `tools/list`, `tools/call`.
- **HTTP**: `POST /rpc` JSON-RPC-ish `{method, params}`; `GET /tools`, `/ontology.json`, `/health`.
- **CLI**: identical surface.

## 9. Extension points
- `parse.RULES` — per-language extraction rules (tree-sitter backend slots in here).
- `embed.get_embedder` — any object with `.name/.embed(texts)`.
- `retrieve.rrf` — replace/augment with learned rerankers.
- `events` table — runtime adapters (test runners, tsc, build logs) ingest JSON events.

## 10. Versioning & security
`meta.schema_version` gates migrations. Index respects `.gitignore`-style excludes + size caps. No network unless an embedding backend is explicitly configured. Hooks never overwrite existing git hooks (marker-delimited append).
````

### 4.3 `bootstrap/AGENTS.md` (copied to repo root on `cip init`)

````markdown
# AGENTS.md — Code Intelligence Bootstrap

This repository runs **CIP**: a continuously updated, machine-readable model of
the codebase. Do NOT read the whole repo. Interrogate the index.

## Workflow (before any change)
1. `cip search "<intent>"`   → candidate code (lexical + semantic + graph)
2. `cip symbol <Name>`       → definition + relationship counts
3. `cip context "<intent>"`  → budgeted pack: code + relations + tests
4. Read exact source only at the lines the index points to.
5. After edits, the index self-updates (git hooks / watcher); `cip sync` to force.

## Rules
- The index is authoritative for STRUCTURE (symbols, deps, tests, history).
- Source files are authoritative for IMPLEMENTATION.
- If a response says `"fresh": false`, run `cip sync` first.
- Prefer `cip context` over opening files > 300 lines.

## Tools
CLI: `cip search | symbol | graph | context | history | doctor | tools --schema`
MCP: `cip mcp` (stdio) · HTTP: `cip serve` (`POST /rpc`, `GET /ontology.json`)
Every tool response includes `next_ops` — follow them.

## Health
`cip doctor` → freshness, vector coverage, hooks, embedder.
````

### 4.4 `ontology.json`

```json
{
  "protocol": "cip",
  "version": "0.9.0",
  "id_grammar": "<language>://<path>#<Qualified.name>",
  "chunk_grammar": "<path>#L<start>-L<end>",
  "entities": {
    "File":   { "key": "path" },
    "Symbol": { "key": "id", "kinds": ["class","function","method","interface","type","const","module","test"] },
    "Chunk":  { "key": "id" },
    "Commit": { "key": "sha" }
  },
  "relationships": {
    "contains":   { "from": "File",          "to": "Symbol" },
    "exports":    { "from": "File",          "to": "Symbol" },
    "imports":    { "from": "File",          "to": "File" },
    "calls":      { "from": "Symbol",        "to": "Symbol" },
    "references": { "from": "Symbol",        "to": "Symbol" },
    "extends":    { "from": "Symbol",        "to": "Symbol" },
    "implements": { "from": "Symbol",        "to": "Symbol" },
    "tested_by":  { "from": "Symbol",        "to": "File" },
    "modified_by":{ "from": "File|Symbol",   "to": "Commit" }
  },
  "envelope": {
    "ok": "bool", "tool": "string", "result": "object",
    "next_ops": "string[]",
    "index": { "fresh": "bool", "lag_s": "number", "files": "integer" }
  },
  "freshness": { "stale_after_s": 300, "enforced_by": ["git-hooks", "watcher", "cip sync"] },
  "extension_points": ["parsers", "embedders", "rerankers", "runtime_adapters"],
  "tools": ["search", "symbol", "graph", "context", "history", "index_status"]
}
```

---

## 5. Core code

### 5.1 `install.sh`

```bash
#!/usr/bin/env sh
# CIP installer — drop repository intelligence into any repo.
# Usage: ./install.sh [TARGET_REPO]   (default: current directory)
set -eu
SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(cd "${1:-.}" && pwd)"

mkdir -p "$TARGET/.cip/bin" "$TARGET/.cip/lib" "$TARGET/.cip/bootstrap" "$TARGET/.cip/data"
cp "$SRC/bin/cip"                     "$TARGET/.cip/bin/cip"
cp -R "$SRC/lib/cipkg"                "$TARGET/.cip/lib/"
cp "$SRC/bootstrap/AGENTS.md"         "$TARGET/.cip/bootstrap/AGENTS.md"
cp "$SRC/config.default.toml"         "$TARGET/.cip/config.toml"
cp "$SRC/ontology.json"               "$TARGET/.cip/ontology.json"
chmod +x "$TARGET/.cip/bin/cip"

echo "cip: installed to $TARGET/.cip"
cd "$TARGET" && "$TARGET/.cip/bin/cip" init
echo
echo "Optional: export PATH=\"$TARGET/.cip/bin:\$PATH\""
```

### 5.2 `.cip/bin/cip`

```python
#!/usr/bin/env python3
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..", "lib")))
from cipkg.cli import main
if __name__ == "__main__":
    sys.exit(main())
```

### 5.3 `.cip/config.toml` (default)

```toml
[index]
max_file_kb = 512
exclude = []                        # extra substring excludes, e.g. ["generated/"]
test_globs = ["test_", "_test.", ".test.", ".spec.", "/tests/", "__tests__"]

[embed]
backend = "auto"                    # auto | hashing | sentence-transformers | openai
model = "all-MiniLM-L6-v2"          # used by sentence-transformers
dim = 1024                          # hashing embedder dimension

[retrieval]
lexical_k = 30
vector_k = 30
context_budget_tokens = 6000

[serve]
port = 8787
```

### 5.4 `lib/cipkg/__init__.py`

```python
"""CIP — Code Intelligence Protocol: drop-in repository intelligence for AI agents."""
__version__ = "0.9.0"
```

### 5.5 `lib/cipkg/base.py`

```python
"""Core utilities: repo discovery, config, hashing, file iteration, tokenizing."""
import hashlib, os, re

CIP_DIRNAME = ".cip"

DEFAULT_EXCLUDES = {
    ".git", "node_modules", "dist", "build", "out", ".next", ".nuxt",
    "__pycache__", ".venv", "venv", "target", "vendor", "coverage",
    ".pytest_cache", ".mypy_cache", ".idea", ".vscode", ".turbo",
    ".cache", "tmp", ".cip",
}

DEFAULT_CONFIG = {
    "index": {"max_file_kb": 512, "exclude": [],
              "test_globs": ["test_", "_test.", ".test.", ".spec.", "/tests/", "__tests__"]},
    "embed": {"backend": "auto", "model": "all-MiniLM-L6-v2", "dim": 1024},
    "retrieval": {"lexical_k": 30, "vector_k": 30, "context_budget_tokens": 6000},
    "serve": {"port": 8787},
}

def repo_root(start=None):
    p = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(p, CIP_DIRNAME)):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            raise SystemExit("cip: no .cip/ found here or above. Install the bundle first.")
        p = parent

def cip_dir(root):  return os.path.join(root, CIP_DIRNAME)

def data_dir(root):
    d = os.path.join(cip_dir(root), "data")
    os.makedirs(d, exist_ok=True)
    return d

def sha(x):
    h = hashlib.sha256()
    h.update(x if isinstance(x, bytes) else x.encode("utf-8", "replace"))
    return h.hexdigest()

def _coerce(v):
    if v.startswith('"') and v.endswith('"'): return v[1:-1]
    if v.startswith("["): return re.findall(r'"([^"]*)"', v)
    if v in ("true", "false"): return v == "true"
    try: return int(v)
    except ValueError:
        try: return float(v)
        except ValueError: return v

def _parse_toml_naive(path):
    out, section = {}, None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if not line: continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip(); out.setdefault(section, {})
            elif "=" in line:
                k, v = (s.strip() for s in line.split("=", 1))
                out.setdefault(section or "_", {})[k] = _coerce(v)
    return out

def load_config(root):
    import copy
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    path = os.path.join(cip_dir(root), "config.toml")
    if not os.path.exists(path):
        return cfg
    try:
        import tomllib
        with open(path, "rb") as f: data = tomllib.load(f)
    except ImportError:
        data = _parse_toml_naive(path)
    for section, kv in data.items():
        if section in cfg and isinstance(kv, dict):
            cfg[section].update(kv)
    return cfg

def _excluded(rel_dir, name, extra):
    rel = name if rel_dir in (".", "") else f"{rel_dir}/{name}"
    return any(pat in rel for pat in extra)

def iter_files(root, cfg):
    maxb = int(cfg["index"]["max_file_kb"]) * 1024
    extra = list(cfg["index"]["exclude"])
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        dirnames[:] = [d for d in dirnames
                       if d not in DEFAULT_EXCLUDES and not _excluded(rel_dir, d, extra)]
        for fn in filenames:
            if _excluded(rel_dir, fn, extra): continue
            ap = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(ap) > maxb: continue
            except OSError:
                continue
            yield fn if rel_dir == "." else f"{rel_dir}/{fn}"

def is_test_path(path, cfg):
    p = path.lower()
    return any(m in p for m in cfg["index"]["test_globs"])

_IDENT_SPLIT = re.compile(r"[^0-9A-Za-z_$]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

def tokenize(text):
    out = []
    for part in _IDENT_SPLIT.split(text):
        if not part: continue
        for piece in part.replace("_", " ").split():
            for tok in _CAMEL.split(piece):
                t = tok.lower()
                if len(t) > 1: out.append(t)
    return out

def est_tokens(text):
    return max(1, len(text) // 4)
```

### 5.6 `lib/cipkg/store.py`

```python
"""SQLite storage: files, symbols, chunks(+FTS5 with LIKE fallback), edges, vectors, events."""
import os, sqlite3

SCHEMA_VERSION = 3

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
    con.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
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

### 5.7 `lib/cipkg/detect.py`

```python
"""Language/framework detection — the repo-agnostic cold start."""
import os

EXT_LANG = {
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".py": "python", ".rs": "rust", ".go": "go", ".java": "java", ".kt": "kotlin",
    ".rb": "ruby", ".cs": "csharp", ".cpp": "cpp", ".cc": "cpp", ".c": "c", ".h": "c",
    ".swift": "swift", ".php": "php", ".scala": "scala", ".zig": "zig", ".lua": "lua",
    ".sh": "shell", ".sql": "sql", ".vue": "vue", ".svelte": "svelte",
}

MANIFESTS = {
    "package.json": "node", "pyproject.toml": "python", "setup.py": "python",
    "Cargo.toml": "rust", "go.mod": "go", "pom.xml": "java",
    "build.gradle": "java", "Gemfile": "ruby", "composer.json": "php",
}

def lang_for(path):
    return EXT_LANG.get(os.path.splitext(path)[1].lower(), "")

def detect(root, cfg):
    from .base import iter_files
    counts, stacks = {}, []
    for rel in iter_files(root, cfg):
        l = lang_for(rel)
        if l: counts[l] = counts.get(l, 0) + 1
        if os.path.dirname(rel) == "" and os.path.basename(rel) in MANIFESTS:
            stacks.append(MANIFESTS[os.path.basename(rel)])
    primary = max(counts, key=counts.get) if counts else "unknown"
    return {"languages": counts, "primary": primary, "stacks": sorted(set(stacks))}
```

### 5.8 `lib/cipkg/parse.py`

```python
"""Symbol extraction. Zero-dependency regex engine (always works);
higher-fidelity backends (tree-sitter) plug in via RULES."""
import re
from .base import sha

STOPWORDS = {"if", "for", "while", "switch", "catch", "return", "new", "else",
             "do", "try", "case", "typeof", "delete", "void", "await", "yield"}

def _c(pat): return re.compile(pat)

RULES = {
    "python": [
        (_c(r"^(\s*)class\s+(\w+)"), "class"),
        (_c(r"^(\s*)(?:async\s+)?def\s+(\w+)\s*\("), "function"),
    ],
    "typescript": [
        (_c(r"^(\s*)(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)"), "class"),
        (_c(r"^(\s*)(?:export\s+)?interface\s+(\w+)"), "interface"),
        (_c(r"^(\s*)(?:export\s+)?type\s+(\w+)\s*="), "type"),
        (_c(r"^(\s*)(?:export\s+)?enum\s+(\w+)"), "class"),
        (_c(r"^(\s*)(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([\w$]+)"), "function"),
        (_c(r"^(\s*)(?:export\s+)?(?:const|let|var)\s+([\w$]+)\s*=\s*(?:async\s*)?(?:\(|[\w$]+\s*=>)"), "function"),
        (_c(r"^(\s{2,})(?:(?:public|private|protected|static|async|readonly|get|set)\s+)*([\w$]+)\s*\([^)]*\)\s*[:{]"), "method"),
    ],
    "rust": [
        (_c(r"^(\s*)(?:pub(?:\([^)]*\))?\s+)?(?:struct|enum|trait)\s+(\w+)"), "class"),
        (_c(r"^(\s*)(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+(\w+)"), "function"),
    ],
    "go": [
        (_c(r"^(\s*)type\s+(\w+)\s+(?:struct|interface)"), "class"),
        (_c(r"^func\s+(?:\([^)]*\)\s*)?(\w+)"), "function"),
    ],
}
RULES["javascript"] = RULES["typescript"][0:1] + RULES["typescript"][4:7]
RULES["java"] = RULES["csharp"] = [
    (_c(r"^(\s*)(?:public\s+|final\s+|abstract\s+|static\s+)*class\s+(\w+)"), "class"),
    (_c(r"^(\s{2,})(?:public|private|protected|static|final|async|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*{"), "method"),
]

GENERIC = [
    (_c(r"^(\s*)class\s+(\w+)"), "class"),
    (_c(r"^(\s*)(?:def|function|func|fn)\s+(\w+)"), "function"),
]

INDENT_LANGS = {"python"}

IMPORT_PATS = {
    "typescript": [_c(r"""from\s+['"]([^'"]+)['"]"""),
                   _c(r"""import\s*\(\s*['"]([^'"]+)['"]"""),
                   _c(r"""require\(\s*['"]([^'"]+)['"]""")],
    "python":     [_c(r"^\s*from\s+([\w.]+)\s+import", re.M),
                   _c(r"^\s*import\s+([\w.]+)", re.M)],
    "go":         [_c(r'^\s*(?:\w+\s+)?"([\w./\-]+)"', re.M)],
    "rust":       [_c(r"^\s*(?:pub\s+)?mod\s+(\w+)\s*;", re.M)],
}
IMPORT_PATS["javascript"] = IMPORT_PATS["typescript"]

def _indent_of(line):
    return len(line) - len(line.lstrip())

def _end_indent(lines, i):
    base = _indent_of(lines[i])
    for j in range(i + 1, len(lines)):
        if not lines[j].strip(): continue
        if _indent_of(lines[j]) <= base:
            return j            # 1-based last line of the block
    return len(lines)

def _end_braces(lines, i):
    depth, started = 0, False
    for j in range(i, len(lines)):
        for ch in lines[j]:
            if ch == "{": depth += 1; started = True
            elif ch == "}": depth -= 1
            if started and depth == 0:
                return j + 1
    return i + 1 if not started else len(lines)

def extract_imports(source, language):
    out = []
    for rx in IMPORT_PATS.get(language, []):
        out.extend(m.group(1) for m in rx.finditer(source))
    return out

def parse_file(path, language, source):
    lines = source.splitlines()
    rules = RULES.get(language, GENERIC)
    indent_lang = language in INDENT_LANGS
    raw = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "#", "*", "/*")):
            continue
        for rx, kind in rules:
            m = rx.match(line)
            if not m: continue
            name = m.group(2)
            if name in STOPWORDS: break
            end = _end_indent(lines, i) if indent_lang else _end_braces(lines, i)
            raw.append({"name": name, "kind": kind, "start": i + 1, "end": end,
                        "line": stripped})
            break

    classes = [s for s in raw if s["kind"] == "class"]
    symbols = []
    for s in raw:
        qual = s["name"]
        kind = s["kind"]
        if kind == "function":
            parent = next((c for c in classes
                           if c["start"] < s["start"] and s["end"] <= c["end"]), None)
            if parent:
                qual, kind = f'{parent["name"]}.{s["name"]}', "method"
        body = "\n".join(lines[s["start"] - 1:s["end"]])
        symbols.append({
            "id": f"{language}://{path}#{qual}",
            "name": s["name"], "kind": kind, "qualname": qual,
            "start": s["start"], "end": s["end"],
            "signature": s["line"][:240],
            "exported": s["line"].startswith(("export", "pub ")),
            "body": body, "body_hash": sha(body),
        })

    chunks = []
    for s in symbols:
        text = "\n".join(lines[s["start"] - 1:s["end"]])
        chunks.append({"id": f'{path}#L{s["start"]}-L{s["end"]}', "path": path,
                       "symbol_id": s["id"], "start": s["start"], "end": s["end"],
                       "text": text, "hash": sha(text)})
    if not symbols and lines:
        n = min(60, len(lines))
        text = "\n".join(lines[:n])
        chunks.append({"id": f"{path}#L1-L{n}", "path": path, "symbol_id": None,
                       "start": 1, "end": n, "text": text, "hash": sha(text)})

    return {"symbols": symbols, "imports": extract_imports(source, language), "chunks": chunks}
```

### 5.9 `lib/cipkg/embed.py`

```python
"""Pluggable embeddings. Default: deterministic offline hashing embedder.
Escalation path: sentence-transformers → OpenAI (only if configured/available)."""
import hashlib, math, os, struct

class HashingEmbedder:
    """Signed feature-hashing of identifier tokens. Offline, deterministic, free."""
    def __init__(self, dim=1024):
        self.dim = dim
        self.name = f"hash-{dim}"
    def embed(self, texts):
        from .base import tokenize
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for i, tok in enumerate(tokenize(t)):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                sign = 1.0 if (h >> 120) % 2 == 0 else -1.0
                v[h % self.dim] += sign * (1.0 + 1.0 / (1 + i))
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out

class STEmbedder:
    def __init__(self, model):
        from sentence_transformers import SentenceTransformer
        self.m = SentenceTransformer(model)
        self.name = f"st:{model}"
        self.dim = self.m.get_sentence_embedding_dimension()
    def embed(self, texts):
        return [list(map(float, v)) for v in
                self.m.encode(texts, normalize_embeddings=True)]

class OpenAIEmbedder:
    def __init__(self, model="text-embedding-3-small"):
        self.model = model
        self.name = f"openai:{model}"
        self.dim = 1536
        self.key = os.environ["OPENAI_API_KEY"]
    def embed(self, texts):
        import json, urllib.request
        req = urllib.request.Request(
            "https://api.openai.com/v1/embeddings",
            data=json.dumps({"model": self.model, "input": texts}).encode(),
            headers={"Authorization": f"Bearer {self.key}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.load(r)
        return [d["embedding"] for d in sorted(data["data"], key=lambda x: x["index"])]

def get_embedder(cfg):
    backend = cfg["embed"].get("backend", "auto")
    model = cfg["embed"].get("model", "all-MiniLM-L6-v2")
    if backend in ("auto", "sentence-transformers"):
        try:
            return STEmbedder(model)
        except Exception:
            if backend == "sentence-transformers": raise
    if backend in ("auto", "openai") and os.environ.get("OPENAI_API_KEY"):
        try:
            return OpenAIEmbedder()
        except Exception:
            if backend == "openai": raise
    return HashingEmbedder(int(cfg["embed"].get("dim", 1024)))

def to_blob(v):   return struct.pack(f"<{len(v)}f", *v)
def from_blob(b): return struct.unpack(f"<{len(b)//4}f", b)
def cosine(a, b): return sum(x * y for x, y in zip(a, b))   # vectors are normalized
```

### 5.10 `lib/cipkg/indexer.py`

```python
"""Incremental, content-hashed indexer with scoped edge rebuild and
dependency-aware embedding refresh. This is the self-updating heart of CIP."""
import os, re, time
from .base import repo_root, load_config, iter_files, sha, is_test_path
from .store import connect, get_meta, set_meta
from .detect import lang_for
from .parse import parse_file, extract_imports
from .embed import get_embedder, to_blob

IDENT = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
STOP_NAMES = {"get", "set", "run", "init", "main", "test", "call", "apply", "handle",
              "value", "data", "item", "result", "args", "kwargs", "self", "this",
              "super", "error", "len", "range", "print", "console", "then", "catch",
              "keys", "values", "push", "map", "filter", "reduce", "find", "name"}
RES_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".py", ".rs", ".go")

def resolve_import(src_path, spec, all_paths):
    spec = spec.strip()
    if spec.startswith("."):
        base = os.path.normpath(os.path.join(os.path.dirname(src_path), spec)).replace(os.sep, "/")
        cands = [base] + [base + e for e in RES_EXTS]
        cands += [base + "/index" + e for e in RES_EXTS[:4]]
        for c in cands:
            if c in all_paths: return c
    elif re.fullmatch(r"[\w.]+", spec):
        base = spec.replace(".", "/")
        for c in (base + ".py", base + "/__init__.py"):
            if c in all_paths: return c
    return None

def index_file(con, path, source, h, size, mtime):
    language = lang_for(path)
    parsed = parse_file(path, language, source)
    con.execute("DELETE FROM symbols WHERE path=?", (path,))
    con.execute("DELETE FROM chunks WHERE path=?", (path,))
    con.execute("DELETE FROM edges WHERE src_path=?", (path,))
    con.execute("DELETE FROM file_imports WHERE path=?", (path,))
    con.execute("DELETE FROM vectors WHERE id LIKE ?", (path + "#%",))
    con.execute("INSERT OR REPLACE INTO files(path,language,size,lines,hash,mtime,indexed_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (path, language, size, source.count("\n") + 1, h, mtime, time.time()))
    for s in parsed["symbols"]:
        con.execute("INSERT OR REPLACE INTO symbols"
                    "(id,name,kind,path,start_line,end_line,signature,body_hash,body) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (s["id"], s["name"], s["kind"], path, s["start"], s["end"],
                     s["signature"], s["body_hash"], s["body"]))
        con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                    (path, s["id"], "contains", path))
        if s["exported"]:
            con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                        (path, s["id"], "exports", path))
    for c in parsed["chunks"]:
        con.execute("INSERT OR REPLACE INTO chunks"
                    "(id,path,symbol_id,start_line,end_line,text,text_hash) VALUES(?,?,?,?,?,?,?)",
                    (c["id"], path, c.get("symbol_id"), c["start"], c["end"], c["text"], c["hash"]))
    for spec in parsed["imports"]:
        con.execute("INSERT INTO file_imports(path,spec) VALUES(?,?)", (path, spec))

def remove_file(con, path):
    con.execute("DELETE FROM files WHERE path=?", (path,))
    con.execute("DELETE FROM symbols WHERE path=?", (path,))
    con.execute("DELETE FROM chunks WHERE path=?", (path,))
    con.execute("DELETE FROM edges WHERE src_path=?", (path,))
    con.execute("DELETE FROM edges WHERE dst=?", (path,))
    con.execute("DELETE FROM file_imports WHERE path=?", (path,))
    con.execute("DELETE FROM vectors WHERE id LIKE ?", (path + "#%",))

def link_imports(con, dirty, all_paths):
    paths = ([r["path"] for r in con.execute("SELECT path FROM files")]
             if dirty is None else list(dirty))
    for p in paths:
        con.execute("DELETE FROM edges WHERE src_path=? AND kind='imports'", (p,))
        for r in con.execute("SELECT spec FROM file_imports WHERE path=?", (p,)):
            tgt = resolve_import(p, r["spec"], all_paths)
            if tgt and tgt != p:
                con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                            (p, tgt, "imports", p))

def resolve_symbol_edges(con, cfg, dirty):
    name_map = {}
    for r in con.execute("SELECT id, name, path FROM symbols"):
        if r["name"] in STOP_NAMES or len(r["name"]) < 4: continue
        name_map.setdefault(r["name"], []).append((r["id"], r["path"]))
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
        seen = 0
        for m in IDENT.finditer(body):
            if seen > 200: break
            hits = name_map.get(m.group(0))
            if not hits: continue
            kind = "calls" if body[m.end():m.end() + 4].lstrip().startswith("(") else "references"
            for (tid, _tp) in hits:
                if tid == row["id"]: continue
                con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                            (row["id"], tid, kind, row["path"]))
                seen += 1
    build_tested_by(con, cfg)

def build_tested_by(con, cfg):
    con.execute("DELETE FROM edges WHERE kind='tested_by'")
    test_files = [r["path"] for r in con.execute("SELECT path FROM files")
                  if is_test_path(r["path"], cfg)]
    for tf in test_files:
        targets = {r["dst"] for r in con.execute(
            "SELECT dst FROM edges WHERE src_path=? AND kind IN ('imports','calls','references')", (tf,))}
        for t in targets:
            srow = con.execute("SELECT path FROM symbols WHERE id=?", (t,)).fetchone()
            if srow and srow["path"] != tf:
                con.execute("INSERT OR IGNORE INTO edges(src,dst,kind,src_path) VALUES(?,?,?,?)",
                            (t, tf, "tested_by", srow["path"]))

def embed_pending(con, cfg, batch=64):
    cached = get_meta(con, "embedder_name")
    if cached:
        n = con.execute("SELECT COUNT(*) c FROM chunks c LEFT JOIN vectors v "
                        "ON v.id=c.id AND v.model=? WHERE v.id IS NULL", (cached,)).fetchone()["c"]
        if n == 0:
            con.execute("DELETE FROM vectors WHERE model <> ?", (cached,))
            return 0
    emb = get_embedder(cfg)
    set_meta(con, "embedder_name", emb.name)
    total = 0
    while True:
        rows = con.execute("SELECT c.id, c.text FROM chunks c LEFT JOIN vectors v "
                           "ON v.id=c.id AND v.model=? WHERE v.id IS NULL LIMIT ?",
                           (emb.name, batch)).fetchall()
        if not rows: break
        for r, v in zip(rows, emb.embed([r["text"] for r in rows])):
            con.execute("INSERT OR REPLACE INTO vectors(id,model,vec) VALUES(?,?,?)",
                        (r["id"], emb.name, to_blob(v)))
        con.commit()
        total += len(rows)
    con.execute("DELETE FROM vectors WHERE id NOT IN (SELECT id FROM chunks)")
    con.execute("DELETE FROM vectors WHERE model <> ?", (emb.name,))
    return total

def compute_stats(con):
    q = lambda t: con.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
    return {"files": q("files"), "symbols": q("symbols"), "chunks": q("chunks"),
            "edges": q("edges"), "vectors": q("vectors")}

def sync(root=None, full=False, do_embed=True):
    root = root or repo_root()
    cfg = load_config(root)
    con = connect(root)
    t0 = time.time()
    known = {r["path"]: (r["hash"], r["mtime"])
             for r in con.execute("SELECT path, hash, mtime FROM files")}
    all_paths, dirty, deleted = set(known), [], list(known)

    for rel in iter_files(root, cfg):
        ap = os.path.join(root, rel)
        try: st = os.stat(ap)
        except OSError: continue
        if rel in known: deleted.remove(rel)
        kh = known.get(rel)
        if kh and kh[1] == st.st_mtime and not full:
            continue                                        # mtime fast path
        try:
            with open(ap, encoding="utf-8", errors="replace") as f: src = f.read()
        except OSError: continue
        h = sha(src)
        if kh and kh[0] == h and not full:
            con.execute("UPDATE files SET mtime=? WHERE path=?", (st.st_mtime, rel))
            continue                                        # content unchanged
        index_file(con, rel, src, h, st.st_size, st.st_mtime)
        dirty.append(rel)
        all_paths.add(rel)

    for rel in deleted:
        remove_file(con, rel)
        all_paths.discard(rel)

    if dirty or deleted or full:
        link_imports(con, dirty or None, all_paths)
        resolve_symbol_edges(con, cfg, dirty or None)
        con.commit()

    n_emb = embed_pending(con, cfg) if do_embed else 0
    stats = compute_stats(con)
    stats.update(dirty=len(dirty), deleted=len(deleted), embedded=n_emb,
                 ms=int((time.time() - t0) * 1000))
    set_meta(con, "last_sync", time.time())
    con.execute("INSERT INTO events(ts,kind,payload) VALUES(?,?,?)",
                (time.time(), "sync", str(stats)))
    con.commit()
    return stats
```

### 5.11 `lib/cipkg/retrieve.py`

```python
"""Hybrid retrieval: FTS5 ⊕ vectors → RRF; graph expansion; budgeted context packs."""
import re, subprocess
from .base import repo_root, load_config, est_tokens
from .store import connect, get_meta

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
    from .embed import get_embedder, from_blob, cosine
    try:
        emb = get_embedder(cfg)
    except Exception:
        return []
    if emb.name != row["model"]: return []          # different embedder → lexical only
    qv = emb.embed([query])[0]
    rows = con.execute("SELECT id, vec FROM vectors").fetchall()
    scored = sorted(((cosine(qv, from_blob(r["vec"])), r["id"]) for r in rows),
                    key=lambda x: -x[0])[:k]
    out = []
    for score, cid in scored:
        c = con.execute("SELECT id, path, symbol_id, start_line, end_line, "
                        "substr(text,1,360) snip FROM chunks WHERE id=?", (cid,)).fetchone()
        if c:
            d = dict(c); d["score"] = round(score, 4); out.append(d)
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
    for cid, score, srcs in rrf([lex, vec])[:k]:
        c = con.execute("SELECT path, symbol_id, start_line, end_line, substr(text,1,360) snip "
                        "FROM chunks WHERE id=?", (cid,)).fetchone()
        if not c: continue
        items.append({"chunk": cid, "path": c["path"],
                      "lines": [c["start_line"], c["end_line"]], "symbol": c["symbol_id"],
                      "score": round(score, 5), "matched": srcs, "snippet": c["snip"]})
    return items

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

### 5.12 `lib/cipkg/server.py`

```python
"""CIP server: JSON-RPC over HTTP + MCP stdio. Same tool surface as the CLI."""
import json, os, sys, time
from . import retrieve, indexer
from .base import repo_root, load_config, cip_dir
from .store import connect, get_meta

TOOLS = [
    {"name": "search", "description": "Hybrid lexical+semantic search over the repository.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer"}}, "required": ["query"]}},
    {"name": "symbol", "description": "Find symbol definitions with relationship counts.",
     "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "graph", "description": "Traverse relationships around a symbol (callers/callees/tests/imports).",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "direction": {"type": "string", "enum": ["in", "out", "both"]}, "depth": {"type": "integer"}}, "required": ["id"]}},
    {"name": "context", "description": "Token-budgeted context pack: seed code + relations + tests.",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "symbol": {"type": "string"}, "budget": {"type": "integer"}}}},
    {"name": "history", "description": "Git history for a path (why the code exists).",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "index_status", "description": "Index freshness, coverage and stats.",
     "inputSchema": {"type": "object", "properties": {}}},
]

def index_status(root):
    con = connect(root)
    stats = indexer.compute_stats(con)
    last = float(get_meta(con, "last_sync", 0) or 0)
    lag = time.time() - last if last else None
    return {**stats, "last_sync": last,
            "lag_s": round(lag, 1) if lag is not None else None,
            "fresh": bool(lag is not None and lag < 300),
            "embedder": get_meta(con, "embedder_name"),
            "fts": get_meta(con, "fts") == "1",
            "schema_version": get_meta(con, "schema_version")}

def _next_ops(name, res):
    ops = []
    ids = []
    if name == "symbol":
        ids = [s["id"] for s in res.get("symbols", [])[:3]]
    elif name == "search":
        ids = [r["symbol"] for r in res.get("results", []) if r.get("symbol")][:3]
    for sid in ids:
        ops.append(f"graph(id='{sid}', direction='both')")
        ops.append(f"context(symbol='{sid}')")
    if name == "graph":
        ops += [f"context(symbol='{n}')" for n in res.get("nodes", [])[1:3]]
    return ops[:6]

def call_tool(root, cfg, name, args):
    args = args or {}
    try:
        if name == "search":
            res = {"results": retrieve.search(root, args.get("query", ""), k=int(args.get("k", 10)))}
        elif name == "symbol":
            res = {"symbols": retrieve.find_symbol(root, args.get("name", ""))}
        elif name == "graph":
            res = retrieve.graph(root, args.get("id"), args.get("direction", "both"),
                                 depth=int(args.get("depth", 1)))
        elif name == "context":
            res = retrieve.context(root, args.get("query"), args.get("symbol"), args.get("budget"))
        elif name == "history":
            res = retrieve.history(root, args.get("path", ""))
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
                    "serverInfo": {"name": "cip", "version": "0.9.0"}}
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

### 5.13 `lib/cipkg/watch.py`

```python
"""Self-updating loop: zero-dependency mtime polling with debounce."""
import os, time

def _snapshot(root):
    from .base import load_config, iter_files
    cfg = load_config(root)
    out = {}
    for rel in iter_files(root, cfg):
        try: out[rel] = os.path.getmtime(os.path.join(root, rel))
        except OSError: pass
    return out

def watch(root=None, interval=1.0, verbose=True):
    from .base import repo_root
    from .indexer import sync
    root = root or repo_root()
    seen = _snapshot(root)
    if verbose: print(f"cip: watching {root} (ctrl-c to stop)")
    while True:
        time.sleep(interval)
        snap = _snapshot(root)
        if snap == seen: continue
        time.sleep(0.4)                       # debounce write bursts
        seen = _snapshot(root)
        try:
            stats = sync(root)
            if verbose:
                print(f"cip: synced +{stats['dirty']} -{stats['deleted']} "
                      f"~{stats['embedded']} emb in {stats['ms']}ms")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"cip: sync error: {e}")
```

### 5.14 `lib/cipkg/cli.py`

```python
"""cip — command line interface for the Code Intelligence Protocol."""
import argparse, json, os, shutil, sys

HOOKS = ("post-commit", "post-merge", "post-checkout")
MARK = "# >>> cip >>>"

def _out(obj):
    print(json.dumps(obj, indent=2, default=str))

def _install_hooks(root):
    git = os.path.join(root, ".git")
    if not os.path.isdir(git):
        print("note: not a git repo — hooks skipped (use `cip watch` for live updates)")
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
    print("ready. Agent entry points: AGENTS.md · `cip mcp` · `cip serve` · `cip --help`")

def cmd_doctor(root):
    from .base import load_config
    from . import indexer
    from .server import index_status
    from .store import connect, get_meta
    cfg = load_config(root)          # noqa: F401 (validates config)
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
        ("embedder", st["embedder"] or "none"),
        ("fts5", st["fts"]),
        ("fresh", st["fresh"]), ("lag_s", st["lag_s"]),
        ("git hooks", "installed" if hooks_ok else "missing"),
        ("AGENTS.md", "present" if os.path.exists(os.path.join(root, "AGENTS.md")) else "missing"),
    ]
    print("cip doctor")
    for k, v in rows:
        print(f"  {k + ':':<18} {v}")

def main(argv=None):
    p = argparse.ArgumentParser(prog="cip",
        description="CIP — repo-agnostic, self-updating code intelligence for AI agents")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("init", help="setup repo: AGENTS.md, hooks, detection, full index")
    sub.add_parser("detect", help="print language/framework detection")
    ip = sub.add_parser("index", help="index (incremental by default)")
    ip.add_argument("--full", action="store_true")
    ip.add_argument("--reembed", action="store_true")
    sub.add_parser("sync", help="incremental sync (used by hooks/watcher)")
    wp = sub.add_parser("watch", help="self-updating foreground watcher")
    wp.add_argument("--interval", type=float, default=1.0)
    sp = sub.add_parser("search"); sp.add_argument("query"); sp.add_argument("-k", type=int, default=10)
    yp = sub.add_parser("symbol"); yp.add_argument("name")
    gp = sub.add_parser("graph"); gp.add_argument("id")
    gp.add_argument("--direction", default="both"); gp.add_argument("--depth", type=int, default=1)
    cp = sub.add_parser("context"); cp.add_argument("query", nargs="?")
    cp.add_argument("--symbol"); cp.add_argument("--budget", type=int)
    hp = sub.add_parser("history"); hp.add_argument("path")
    sub.add_parser("doctor", help="index health report")
    vp = sub.add_parser("serve"); vp.add_argument("--port", type=int)
    sub.add_parser("mcp", help="MCP stdio server")
    tp = sub.add_parser("tools"); tp.add_argument("--schema", action="store_true")
    a = p.parse_args(argv)
    if not a.cmd:
        p.print_help(); return 0

    from .base import repo_root, load_config, cip_dir
    root = os.getcwd() if a.cmd == "init" else repo_root()

    if a.cmd == "init":      cmd_init(root)
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
    elif a.cmd == "search":
        from . import retrieve; _out({"results": retrieve.search(root, a.query, k=a.k)})
    elif a.cmd == "symbol":
        from . import retrieve; _out({"symbols": retrieve.find_symbol(root, a.name)})
    elif a.cmd == "graph":
        from . import retrieve; _out(retrieve.graph(root, a.id, a.direction, depth=a.depth))
    elif a.cmd == "context":
        from . import retrieve; _out(retrieve.context(root, a.query, a.symbol, a.budget))
    elif a.cmd == "history":
        from . import retrieve; _out(retrieve.history(root, a.path))
    elif a.cmd == "doctor":  cmd_doctor(root)
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
    return 0
```

---

## 6. Deploy & point your agent at it

```bash
# One-time, per repo (fully automatic setup):
./install.sh /path/to/repo

# Self-updating (pick any; git hooks already cover commit/merge/checkout):
/path/to/repo/.cip/bin/cip watch &        # live watcher daemon
/path/to/repo/.cip/bin/cip serve &        # HTTP for multi-agent setups

# Verify:
/path/to/repo/.cip/bin/cip doctor
/path/to/repo/.cip/bin/cip search "token refresh"
```

Your agent gets the intelligence through **any** of the three bindings — MCP stdio (`cip mcp`), HTTP (`POST /rpc`), or plain CLI — and is taught the workflow by the 30-line `AGENTS.md`. Every answer carries `next_ops` + freshness, so even a weak model navigates like a strong one.

## 7. Roadmap to v1.0 (already scaffolded)

1. **tree-sitter parser backends** registered into `parse.RULES` (precision upgrade, zero contract change).
2. **Runtime adapters**: test-runner / `tsc` / build output → `events` table → `frequently_failing`, `coverage` edges.
3. **LLM summary layer** (file/package summaries, cached by content hash, budget-capped).
4. **SCIP/LSIF export** for interop with existing tooling.
5. **sqlite-vec / LanceDB vector backend** swap when chunk counts exceed ~100k.

That's the complete system: assessed, enhanced, formalized, repo-agnostic, self-updating, and ready to drop into any repository.
