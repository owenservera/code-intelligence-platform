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

CREATE TABLE IF NOT EXISTS tauri_commands(
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  args TEXT,
  file TEXT,
  line INTEGER,
  is_allowed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tauri_capabilities(
  id INTEGER PRIMARY KEY,
  command TEXT NOT NULL UNIQUE
);
"""

def ensure(con):
    con.executescript(STACK_SCHEMA)
