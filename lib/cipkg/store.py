"""SQLite storage v1.0: + summaries, commits, commit_files, signals.
CREATE IF NOT EXISTS makes old databases upgrade in place."""
import os, sqlite3, threading

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

CREATE TABLE IF NOT EXISTS symbol_calls(symbol_id TEXT, callee_name TEXT);
CREATE INDEX IF NOT EXISTS idx_sc_sym ON symbol_calls(symbol_id);
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
    # ── performance pragmas (v2: tuned for Windows + large repos) ──
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA busy_timeout=30000")
    con.execute("PRAGMA cache_size=-65536")          # 64 MB page cache
    try:
        con.execute("PRAGMA mmap_size=134217728")     # 128 MB memory-mapped IO
    except sqlite3.OperationalError:
        pass
    con.execute("PRAGMA temp_store=MEMORY")           # sorts/joins in RAM
    con.execute("PRAGMA wal_autocheckpoint=2000")     # less frequent WAL churn
    con.execute("PRAGMA foreign_keys=OFF")            # we manage deletes explicitly
    # Don't blow away a warm cache just because a new connection was opened —
    # invalidation is handled by vector_signature() comparison, not by connect().
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
    try:  # v1.2 migration: tier column
        con.execute("ALTER TABLE files ADD COLUMN tier TEXT DEFAULT 'code'")
    except sqlite3.OperationalError:
        pass
    _ensure_tokenizer(con)
    con.commit()
    return con

def get_meta(con, key, default=None):
    r = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default

def set_meta(con, key, value):
    con.execute("INSERT INTO meta(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

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
        try:
            from .base import tokenize
            for r in con.execute("SELECT rowid, text FROM chunks").fetchall():
                con.execute("UPDATE chunks SET tokens=? WHERE rowid=?",
                            (" ".join(tokenize(r["text"])), r["rowid"]))
            set_meta(con, "tok_built", "1")
        except Exception:
            set_meta(con, "tok_built", "0")


# ── v2: bulk-write helpers + cross-call vector cache ──────────────────────────

_VEC_CACHE_LOCK = threading.Lock()
_VEC_CACHE = {}   # db_path -> (signature, ids, matrix) for fast repeated KNN


def bulk(con, sql, rows):
    """executemany with a guard for empty input. Returns rowcount."""
    if not rows:
        return 0
    cur = con.executemany(sql, rows)
    return cur.rowcount if cur is not None else 0


def bulk_delete_paths(con, table, path_col, paths):
    """DELETE … WHERE <path_col> IN (...) in safe chunks."""
    if not paths:
        return 0
    n = 0
    for i in range(0, len(paths), 500):
        ph = ",".join("?" * len(paths[i:i + 500]))
        n += con.execute("DELETE FROM %s WHERE %s IN (%s)" %
                         (table, path_col, ph), paths[i:i + 500]).rowcount
    return n


def vector_signature(con, model):
    """Cheap, cross-process-safe invalidation key for the cached vector matrix."""
    r = con.execute(
        "SELECT COUNT(*) c, COALESCE(MAX(rowid),0) m FROM vectors WHERE model=?",
        (model,)).fetchone()
    return (model, r["c"], r["m"])


def vector_matrix(con, model):
    """Return (ids, numpy_matrix) for a model, cached per connection/database.

    The cache is keyed by a cheap signature (count + max rowid) so it stays
    correct across processes (CLI, daemon, server) without explicit rev counters.
    """
    from .embed import from_blob
    db = os.path.abspath(_db_path(con))
    sig = vector_signature(con, model)
    with _VEC_CACHE_LOCK:
        cached = _VEC_CACHE.get(db)
        if cached is not None and cached[0] == sig and cached[1] is not None:
            return cached[1], cached[2]
    rows = con.execute("SELECT id, vec FROM vectors WHERE model=?", (model,)).fetchall()
    ids, mat = [], None
    if rows:
        try:
            import numpy as np
            ids = [r["id"] for r in rows]
            mat = np.array([from_blob(r["vec"]) for r in rows], dtype=np.float32)
        except ImportError:
            ids = [r["id"] for r in rows]
            mat = [from_blob(r["vec"]) for r in rows]
    with _VEC_CACHE_LOCK:
        _VEC_CACHE[db] = (sig, ids, mat)
    return ids, mat


def _db_path(con):
    try:
        return con.execute("PRAGMA database_list").fetchone()["file"]
    except Exception:
        return "unknown"


def invalidate_vectors(con):
    """Drop any cached vector matrix for this connection's database."""
    try:
        with _VEC_CACHE_LOCK:
            _VEC_CACHE.pop(os.path.abspath(_db_path(con)), None)
    except Exception:
        pass
