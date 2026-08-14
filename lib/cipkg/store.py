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
