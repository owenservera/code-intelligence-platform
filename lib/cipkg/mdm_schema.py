"""mdm_schema.py — Master Data Model (L0–LA) SQLite Schema, DDL and Data Access Layer.

Defines tables for entities, edges, findings, and explainability traces across all
layers L0 to LA, supporting non-destructive database migrations.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple


MDM_SCHEMA_VERSION = 5

MDM_DDL = """
-- L0-L9 Entities table
CREATE TABLE IF NOT EXISTS mdm_entities (
    id TEXT PRIMARY KEY,
    layer TEXT NOT NULL,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    start_line INTEGER DEFAULT 0,
    end_line INTEGER DEFAULT 0,
    name TEXT NOT NULL,
    attributes_json TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mdm_ent_layer ON mdm_entities(layer);
CREATE INDEX IF NOT EXISTS idx_mdm_ent_kind ON mdm_entities(kind);
CREATE INDEX IF NOT EXISTS idx_mdm_ent_path ON mdm_entities(path);

-- L0-L9 Graph Edges table
CREATE TABLE IF NOT EXISTS mdm_edges (
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    kind TEXT NOT NULL,
    layer TEXT NOT NULL,
    attributes_json TEXT,
    PRIMARY KEY (src, dst, kind)
);
CREATE INDEX IF NOT EXISTS idx_mdm_edge_src ON mdm_edges(src);
CREATE INDEX IF NOT EXISTS idx_mdm_edge_dst ON mdm_edges(dst);
CREATE INDEX IF NOT EXISTS idx_mdm_edge_layer ON mdm_edges(layer);
CREATE INDEX IF NOT EXISTS idx_mdm_edge_kind ON mdm_edges(kind);

-- LA Canonical Finding Records
CREATE TABLE IF NOT EXISTS mdm_findings (
    finding_id TEXT PRIMARY KEY,
    layer_origin TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence TEXT NOT NULL,
    path TEXT NOT NULL,
    line INTEGER DEFAULT 0,
    symbol_id TEXT,
    title TEXT NOT NULL,
    detail TEXT,
    suggestion TEXT,
    effort TEXT DEFAULT 'small',
    score REAL DEFAULT 0.0,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mdm_find_sev ON mdm_findings(severity);
CREATE INDEX IF NOT EXISTS idx_mdm_find_rule ON mdm_findings(rule_id);
CREATE INDEX IF NOT EXISTS idx_mdm_find_path ON mdm_findings(path);

-- LA Explainability Trace (Multi-Layer Evidence Chain)
CREATE TABLE IF NOT EXISTS mdm_traces (
    finding_id TEXT NOT NULL,
    step_index INTEGER NOT NULL,
    layer TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    evidence_description TEXT NOT NULL,
    PRIMARY KEY (finding_id, step_index)
);
CREATE INDEX IF NOT EXISTS idx_mdm_trace_fid ON mdm_traces(finding_id);
CREATE INDEX IF NOT EXISTS idx_mdm_trace_eid ON mdm_traces(entity_id);
"""


def init_mdm_schema(con: sqlite3.Connection) -> None:
    """Initialize MDM tables and migrate schema safely without data loss."""
    con.executescript(MDM_DDL)
    try:
        cur_ver = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        v = int(cur_ver["value"]) if cur_ver and cur_ver["value"] else 4
        if v < MDM_SCHEMA_VERSION:
            con.execute(
                "INSERT INTO meta(key,value) VALUES('schema_version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(MDM_SCHEMA_VERSION),),
            )
            con.commit()
    except Exception:
        pass


def record_entity(
    con: sqlite3.Connection,
    entity_id: str,
    layer: str,
    kind: str,
    path: str,
    name: str,
    start_line: int = 0,
    end_line: int = 0,
    attributes: Optional[Dict[str, Any]] = None,
) -> None:
    """Upsert a single MDM entity record."""
    attrs_str = json.dumps(attributes or {}, default=str)
    con.execute(
        "INSERT OR REPLACE INTO mdm_entities(id, layer, kind, path, start_line, end_line, name, attributes_json, created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (entity_id, layer, kind, path, start_line, end_line, name, attrs_str, time.time()),
    )


def record_entities_bulk(
    con: sqlite3.Connection,
    entities: List[Tuple[str, str, str, str, int, int, str, Optional[Dict[str, Any]]]],
) -> int:
    """Bulk upsert entities for performance.
    
    Tuple format: (id, layer, kind, path, start_line, end_line, name, attributes_dict)
    """
    if not entities:
        return 0
    now = time.time()
    rows = [
        (e[0], e[1], e[2], e[3], e[4], e[5], e[6], json.dumps(e[7] or {}, default=str), now)
        for e in entities
    ]
    cur = con.executemany(
        "INSERT OR REPLACE INTO mdm_entities(id, layer, kind, path, start_line, end_line, name, attributes_json, created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return cur.rowcount if cur is not None else len(rows)


def record_edge(
    con: sqlite3.Connection,
    src: str,
    dst: str,
    kind: str,
    layer: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> None:
    """Upsert a single MDM relationship edge."""
    attrs_str = json.dumps(attributes or {}, default=str)
    con.execute(
        "INSERT OR REPLACE INTO mdm_edges(src, dst, kind, layer, attributes_json) "
        "VALUES(?,?,?,?,?)",
        (src, dst, kind, layer, attrs_str),
    )


def record_edges_bulk(
    con: sqlite3.Connection,
    edges: List[Tuple[str, str, str, str, Optional[Dict[str, Any]]]],
) -> int:
    """Bulk upsert relationship edges.
    
    Tuple format: (src, dst, kind, layer, attributes_dict)
    """
    if not edges:
        return 0
    rows = [
        (e[0], e[1], e[2], e[3], json.dumps(e[4] or {}, default=str))
        for e in edges
    ]
    cur = con.executemany(
        "INSERT OR REPLACE INTO mdm_edges(src, dst, kind, layer, attributes_json) "
        "VALUES(?,?,?,?,?)",
        rows,
    )
    return cur.rowcount if cur is not None else len(rows)


def record_finding_with_trace(
    con: sqlite3.Connection,
    finding_id: str,
    layer_origin: str,
    rule_id: str,
    severity: str,
    confidence: str,
    path: str,
    line: int,
    title: str,
    detail: str = "",
    suggestion: str = "",
    effort: str = "small",
    score: float = 0.0,
    symbol_id: Optional[str] = None,
    trace_steps: Optional[List[Tuple[str, str, str]]] = None,
) -> None:
    """Save an LA Finding Record along with its explainability trace chain.
    
    trace_steps format: list of (layer, entity_id, evidence_description)
    """
    now = time.time()
    con.execute(
        "INSERT OR REPLACE INTO mdm_findings(finding_id, layer_origin, rule_id, severity, confidence, "
        "path, line, symbol_id, title, detail, suggestion, effort, score, created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            finding_id,
            layer_origin,
            rule_id,
            severity,
            confidence,
            path,
            line,
            symbol_id,
            title,
            detail,
            suggestion,
            effort,
            score,
            now,
        ),
    )
    if trace_steps:
        con.execute("DELETE FROM mdm_traces WHERE finding_id=?", (finding_id,))
        trace_rows = [
            (finding_id, idx + 1, step[0], step[1], step[2])
            for idx, step in enumerate(trace_steps)
        ]
        con.executemany(
            "INSERT INTO mdm_traces(finding_id, step_index, layer, entity_id, evidence_description) "
            "VALUES(?,?,?,?,?)",
            trace_rows,
        )


def query_findings(
    con: sqlite3.Connection,
    severity: Optional[str] = None,
    rule_id: Optional[str] = None,
    layer: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Query MDM findings with optional filters."""
    sql = "SELECT * FROM mdm_findings WHERE 1=1"
    params: List[Any] = []
    if severity:
        sql += " AND severity=?"
        params.append(severity)
    if rule_id:
        sql += " AND rule_id=?"
        params.append(rule_id)
    if layer:
        sql += " AND layer_origin=?"
        params.append(layer)
    sql += " ORDER BY score DESC, created_at DESC LIMIT ?"
    params.append(limit)
    rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_explainability_trace(con: sqlite3.Connection, finding_id: str) -> List[Dict[str, Any]]:
    """Fetch the step-by-step explainability trace for a finding."""
    rows = con.execute(
        "SELECT step_index, layer, entity_id, evidence_description "
        "FROM mdm_traces WHERE finding_id=? ORDER BY step_index ASC",
        (finding_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def clear_mdm_layer_data(con: sqlite3.Connection, layer: Optional[str] = None) -> None:
    """Clear MDM tables, optionally targeting a specific layer."""
    if layer:
        con.execute("DELETE FROM mdm_entities WHERE layer=?", (layer,))
        con.execute("DELETE FROM mdm_edges WHERE layer=?", (layer,))
        con.execute("DELETE FROM mdm_findings WHERE layer_origin=?", (layer,))
    else:
        con.execute("DELETE FROM mdm_entities")
        con.execute("DELETE FROM mdm_edges")
        con.execute("DELETE FROM mdm_findings")
        con.execute("DELETE FROM mdm_traces")
