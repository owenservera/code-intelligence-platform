"""mdm_engine.py — Master Data Model (L0–L9) Ingestion, Extraction, and Detection Engine.

Orchestrates multi-layer fact extraction across topology, syntax, symbols, control flow,
architecture, code smells, security/cross-cutting concerns, runtime snapshots, and git churn.
"""
from __future__ import annotations

import ast
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import repo_root, load_config, is_test_path, log_swallowed
from .store import connect, bulk
from . import gapfill, gitindex, doctor
from .mdm_schema import (
    record_entity,
    record_entities_bulk,
    record_edge,
    record_edges_bulk,
    clear_mdm_layer_data,
)


# ---------------------------------------------------------------------------
# L0 — Repo Topology & Ingestion
# ---------------------------------------------------------------------------

MANIFEST_NAMES = {
    "package.json": "npm",
    "Cargo.toml": "cargo",
    "pyproject.toml": "python",
    "setup.py": "python",
    "go.mod": "go",
    "pom.xml": "maven",
    "build.gradle": "gradle",
}


def scan_l0_topology(con: sqlite3.Connection, root: str, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Scan and populate L0 entities: repository, packages, files, manifests, orphan files."""
    root_path = Path(root)
    file_entities: List[Tuple[str, str, str, str, int, int, str, Optional[Dict[str, Any]]]] = []
    edge_entities: List[Tuple[str, str, str, str, Optional[Dict[str, Any]]]] = []

    # 1. Repository entity
    repo_name = root_path.name
    total_files = con.execute("SELECT COUNT(*) c FROM files").fetchone()["c"]
    total_lines = con.execute("SELECT COALESCE(SUM(lines), 0) s FROM files").fetchone()["s"]
    lang_rows = con.execute(
        "SELECT language, COUNT(*) c, SUM(lines) l FROM files GROUP BY language"
    ).fetchall()
    lang_histogram = {r["language"]: {"files": r["c"], "lines": r["l"]} for r in lang_rows}

    record_entity(
        con,
        entity_id=f"repo://{repo_name}",
        layer="L0",
        kind="Repository",
        path="",
        name=repo_name,
        attributes={
            "total_files": total_files,
            "total_lines": total_lines,
            "language_histogram": lang_histogram,
        },
    )

    # 2. Package / Manifest boundaries
    manifests: List[str] = []
    for mname, mkind in MANIFEST_NAMES.items():
        for mf in root_path.rglob(mname):
            if any(part in mf.parts for part in (".git", "node_modules", ".cip", "__pycache__", "target", "dist")):
                continue
            rel = str(mf.relative_to(root_path)).replace("\\", "/")
            manifests.append(rel)
            pkg_name = mf.parent.name if mf.parent != root_path else repo_name
            record_entity(
                con,
                entity_id=f"pkg://{rel}",
                layer="L0",
                kind="Module/Package",
                path=rel,
                name=pkg_name,
                attributes={"manifest_type": mkind, "parent_dir": str(mf.parent.name)},
            )
            edge_entities.append((f"repo://{repo_name}", f"pkg://{rel}", "contains_package", "L0", {}))

    # 3. Ingest files & detect orphan files
    orphan_files: List[str] = []
    file_rows = con.execute("SELECT path, language, size, lines, tier FROM files").fetchall()
    imported_targets = {
        r["dst"] for r in con.execute("SELECT dst FROM edges WHERE kind='imports'").fetchall()
    }

    for f in file_rows:
        p = f["path"]
        is_imported = p in imported_targets
        base = os.path.basename(p)
        is_entry = base in (
            "index.ts", "index.js", "main.py", "main.rs", "lib.rs", "app.tsx",
            "page.tsx", "layout.tsx", "route.ts", "setup.py", "cli.py", "__init__.py"
        )
        is_orphan = not is_imported and not is_entry and f["tier"] == "code" and not is_test_path(p, cfg)

        if is_orphan:
            orphan_files.append(p)

        file_entities.append((
            f"file://{p}",
            "L0",
            "Orphan File" if is_orphan else "File",
            p,
            1,
            f["lines"],
            base,
            {
                "language": f["language"],
                "size_bytes": f["size"],
                "tier": f["tier"],
                "is_orphan": is_orphan,
            },
        ))
        edge_entities.append((f"repo://{repo_name}", f"file://{p}", "contains_file", "L0", {}))

    record_entities_bulk(con, file_entities)
    record_edges_bulk(con, edge_entities)
    con.commit()

    return {
        "manifest_count": len(manifests),
        "total_files": total_files,
        "orphan_count": len(orphan_files),
        "orphans": orphan_files[:20],
    }


# ---------------------------------------------------------------------------
# L1 — Syntax & Parse Layer
# ---------------------------------------------------------------------------

def scan_l1_syntax(con: sqlite3.Connection) -> Dict[str, Any]:
    """Scan and populate L1 syntax entities from symbol and chunk tables."""
    sym_rows = con.execute(
        "SELECT id, name, kind, path, start_line, end_line, signature, body FROM symbols"
    ).fetchall()

    entities: List[Tuple[str, str, str, str, int, int, str, Optional[Dict[str, Any]]]] = []
    edge_entities: List[Tuple[str, str, str, str, Optional[Dict[str, Any]]]] = []
    functions_count = 0
    types_count = 0

    for s in sym_rows:
        body = s["body"] or ""
        lines_count = max(1, s["end_line"] - s["start_line"])
        has_doc = (
            '"""' in body or "'''" in body or "/**" in body or "//!" in body or "///" in body
        )
        kind = s["kind"]
        if kind in ("function", "method"):
            functions_count += 1
            ekind = "Function/Method Def"
        elif kind in ("class", "interface", "type", "struct", "trait", "enum"):
            types_count += 1
            ekind = "Type/Struct/Trait Def"
        else:
            ekind = "AST Node"

        # Cyclomatic complexity heuristic from branch keywords
        cc = 1 + len(re.findall(r"\b(if|elif|else|for|while|case|catch|except|&&|\|\|)\b", body))

        entities.append((
            f"ast://{s['id']}",
            "L1",
            ekind,
            s["path"],
            s["start_line"],
            s["end_line"],
            s["name"],
            {
                "signature": s["signature"],
                "cyclomatic_complexity": cc,
                "has_doc_comment": has_doc,
                "loc": lines_count,
            },
        ))
        edge_entities.append((f"file://{s['path']}", f"ast://{s['id']}", "defines_ast_node", "L1", {}))

    record_entities_bulk(con, entities)
    record_edges_bulk(con, edge_entities)
    con.commit()

    return {
        "ast_nodes_count": len(sym_rows),
        "functions_count": functions_count,
        "types_count": types_count,
    }


# ---------------------------------------------------------------------------
# L2 — Symbol & Dependency Graph Layer
# ---------------------------------------------------------------------------

def scan_l2_symbols_and_deps(con: sqlite3.Connection, root: str) -> Dict[str, Any]:
    """Populate L2 resolved symbol entities, degree metrics, God objects, and Tarjan SCC cycles."""
    # 1. Ingest resolved symbols
    sym_entities: List[Tuple[str, str, str, str, int, int, str, Optional[Dict[str, Any]]]] = []
    edges_l2: List[Tuple[str, str, str, str, Optional[Dict[str, Any]]]] = []

    # Calculate fan-in and fan-out
    fan_in_map: Dict[str, int] = {}
    fan_out_map: Dict[str, int] = {}

    edge_rows = con.execute("SELECT src, dst, kind FROM edges").fetchall()
    for e in edge_rows:
        src, dst, k = e["src"], e["dst"], e["kind"]
        fan_out_map[src] = fan_out_map.get(src, 0) + 1
        fan_in_map[dst] = fan_in_map.get(dst, 0) + 1
        edges_l2.append((src, dst, k, "L2", {}))

    symbols = con.execute("SELECT id, name, kind, path, start_line, end_line FROM symbols").fetchall()
    god_objects: List[Dict[str, Any]] = []

    for s in symbols:
        sid = s["id"]
        fin = fan_in_map.get(sid, 0)
        fout = fan_out_map.get(sid, 0)
        is_god = fin >= 10 and fout >= 8

        sym_entities.append((
            f"sym://{sid}",
            "L2",
            "God Object Candidate" if is_god else "Symbol",
            s["path"],
            s["start_line"],
            s["end_line"],
            s["name"],
            {"fan_in": fin, "fan_out": fout, "kind": s["kind"], "is_god_object": is_god},
        ))

        if is_god:
            god_objects.append({"id": sid, "name": s["name"], "path": s["path"], "fan_in": fin, "fan_out": fout})

    record_entities_bulk(con, sym_entities)
    record_edges_bulk(con, edges_l2)

    # 2. Detect Dependency Cycles using Tarjan SCC directly on in-memory edges
    adj: Dict[str, List[str]] = {}
    nodes: Set[str] = set()
    for e in edges_l2:
        if e[2] in ('calls', 'imports', 'references'):
            adj.setdefault(e[0], []).append(e[1])
            nodes.add(e[0])
            nodes.add(e[1])
    cycles = gapfill._tarjan_scc(list(nodes), adj)
    for idx, members in enumerate(cycles):
        record_entity(
            con,
            entity_id=f"cycle://scc_{idx}",
            layer="L2",
            kind="Dependency Cycle",
            path=members[0] if members else "",
            name=f"SCC Cycle #{idx+1} ({len(members)} nodes)",
            attributes={"members": members, "length": len(members)},
        )

    con.commit()
    return {
        "symbols_count": len(symbols),
        "god_objects_count": len(god_objects),
        "god_objects": god_objects[:10],
        "cycle_count": len(cycles),
    }


# ---------------------------------------------------------------------------
# L3 — Type & Semantic Layer
# ---------------------------------------------------------------------------

def scan_l3_types_and_semantics(con: sqlite3.Connection, root: str) -> Dict[str, Any]:
    """Scan for type suppressions, stringly typed boundaries, and error patterns."""
    entities: List[Tuple[str, str, str, str, int, int, str, Optional[Dict[str, Any]]]] = []
    ts_files = [
        r["path"]
        for r in con.execute(
            "SELECT path FROM files WHERE language IN ('typescript', 'javascript')"
        ).fetchall()
    ]

    any_count = 0
    suppression_count = 0
    stringly_typed_sites: List[Dict[str, Any]] = []

    for rel in ts_files:
        full_path = os.path.join(root, rel)
        try:
            content = open(full_path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue

        # Check for 'any' types
        anys = list(re.finditer(r":\s*any\b|as\s+any\b", content))
        if anys:
            any_count += len(anys)
            for m in anys[:5]:
                ln = content.count("\n", 0, m.start()) + 1
                entities.append((
                    f"type_leak://{rel}:{ln}",
                    "L3",
                    "Inferred Type Leak",
                    rel,
                    ln,
                    ln,
                    "any",
                    {"snippet": m.group(0)},
                ))

        # Check for @ts-ignore / @ts-expect-error
        ts_ignores = list(re.finditer(r"@(ts-ignore|ts-expect-error)", content))
        if ts_ignores:
            suppression_count += len(ts_ignores)
            for m in ts_ignores[:5]:
                ln = content.count("\n", 0, m.start()) + 1
                entities.append((
                    f"ts_ignore://{rel}:{ln}",
                    "L3",
                    "Type Suppression",
                    rel,
                    ln,
                    ln,
                    m.group(0),
                    {"suppression": m.group(0)},
                ))

        # Check for stringly typed provider / event comparisons
        str_comps = list(re.finditer(r'(?:provider|mode|state|kind|type)\s*===?\s*["\']([a-zA-Z0-9_-]+)["\']', content))
        for sc in str_comps:
            ln = content.count("\n", 0, sc.start()) + 1
            val = sc.group(1)
            stringly_typed_sites.append({"path": rel, "line": ln, "value": val})
            entities.append((
                f"stringly://{rel}:{ln}:{val}",
                "L3",
                "Stringly-Typed Boundary",
                rel,
                ln,
                ln,
                val,
                {"matched_pattern": sc.group(0)},
            ))

    record_entities_bulk(con, entities)
    con.commit()

    return {
        "any_usages_count": any_count,
        "type_suppressions_count": suppression_count,
        "stringly_typed_count": len(stringly_typed_sites),
    }


# ---------------------------------------------------------------------------
# L4 — Control & Data Flow Layer (Wiring Gaps & Swallows)
# ---------------------------------------------------------------------------

TAURI_INVOKE_RE = re.compile(r"""(?:invoke|invokePlugin)\s*\(\s*['"]([^'"]+)['"]""")
EVENT_EMIT_RE = re.compile(r"""(?:emit|dispatchEvent|fireEvent)\s*\(\s*['"]([^'"]+)['"]""")
EVENT_LISTEN_RE = re.compile(r"""(?:listen|addEventListener|on)\s*\(\s*['"]([^'"]+)['"]""")

# Path segments that are always excluded from IPC/wiring scans (vendor/generated code)
_L4_EXCLUDE_SEGS = (
    "node_modules", "dist", "build", ".venv", "venv",
    "__pycache__", ".cip", "target", "vendor", ".next",
    "htmlcov", "backups",
)


def _is_source_path(rel: str) -> bool:
    """Return True only if a relative path points to user-authored source (not vendor/generated)."""
    parts = rel.replace("\\", "/").split("/")
    return not any(seg in _L4_EXCLUDE_SEGS for seg in parts)


def scan_l4_flow_and_wiring(con: sqlite3.Connection, root: str) -> Dict[str, Any]:
    """Scan control flow traps, unawaited database calls, silent swallows, and IPC/Event wiring gaps."""
    entities: List[Tuple[str, str, str, str, int, int, str, Optional[Dict[str, Any]]]] = []
    wiring_gaps: List[Dict[str, Any]] = []

    # 1. AST exception swallow scanning via doctor module
    swallow_findings = doctor.scan_path(Path(root) / "lib") if os.path.exists(os.path.join(root, "lib")) else []
    for sw in swallow_findings:
        entities.append((
            f"swallow://{sw['file']}:{sw['line']}",
            "L4",
            "Silent Exception Swallow",
            sw["file"],
            sw["line"],
            sw["line"],
            sw["kind"],
            {"except_source": sw.get("except_source", "")},
        ))

    # 2. Tauri IPC Commands & Pub/Sub Event Wiring (source files only, no vendor)
    frontend_invokes: Set[Tuple[str, str, int]] = set()   # (cmd_name, file, line)
    frontend_listens: Set[Tuple[str, str, int]] = set()   # (event_name, file, line)
    frontend_emits: Set[Tuple[str, str, int]] = set()     # (event_name, file, line)

    backend_commands: Set[Tuple[str, str, int]] = set()   # (cmd_name, file, line)
    backend_emits: Set[Tuple[str, str, int]] = set()      # (event_name, file, line)

    # Scan source files only (excludes node_modules, dist, etc.)
    file_rows = con.execute("SELECT path, language FROM files").fetchall()
    for f in file_rows:
        rel = f["path"]
        # Skip all vendor/generated paths
        if not _is_source_path(rel):
            continue
        full_path = os.path.join(root, rel)
        try:
            src = open(full_path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue

        # Frontend JS/TS scanning
        if f["language"] in ("typescript", "javascript"):
            for m in TAURI_INVOKE_RE.finditer(src):
                ln = src.count("\n", 0, m.start()) + 1
                frontend_invokes.add((m.group(1), rel, ln))

            for m in EVENT_LISTEN_RE.finditer(src):
                ln = src.count("\n", 0, m.start()) + 1
                frontend_listens.add((m.group(1), rel, ln))

            for m in EVENT_EMIT_RE.finditer(src):
                ln = src.count("\n", 0, m.start()) + 1
                frontend_emits.add((m.group(1), rel, ln))

        # Backend Rust / Tauri command scanning
        if f["language"] == "rust" or rel.endswith(".rs"):
            # Match #[tauri::command] fn foo
            for m in re.finditer(r"""#\[tauri::command(?:\([^)]*\))?\]\s*(?:pub\s+)?(?:async\s+)?fn\s+([a-zA-Z0-9_]+)""", src):
                ln = src.count("\n", 0, m.start()) + 1
                backend_commands.add((m.group(1), rel, ln))

            for m in re.finditer(r"""\.emit\s*\(\s*["']([^"']+)["']""", src):
                ln = src.count("\n", 0, m.start()) + 1
                backend_emits.add((m.group(1), rel, ln))

    # Cross-reference frontend invokes vs backend commands
    backend_cmd_names = {c[0] for c in backend_commands}
    for inv_name, fpath, ln in frontend_invokes:
        if inv_name not in backend_cmd_names:
            # Check for snake_case / camelCase mismatch
            snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", inv_name).lower()
            camel_match = snake_name in backend_cmd_names
            gap_item = {
                "type": "IPC_UNREGISTERED_COMMAND",
                "name": inv_name,
                "path": fpath,
                "line": ln,
                "detail": f"Frontend invokes command '{inv_name}' which is not registered in backend" + (
                    f" (found snake_case '{snake_name}' in backend - naming mismatch!)" if camel_match else ""
                ),
            }
            wiring_gaps.append(gap_item)
            entities.append((
                f"wiring_gap://ipc/{inv_name}/{fpath}:{ln}",
                "L4",
                "Callback/Handler Registration Gap",
                fpath,
                ln,
                ln,
                inv_name,
                gap_item,
            ))

    # Cross-reference frontend listeners vs backend emits
    backend_emit_names = {e[0] for e in backend_emits}
    frontend_emit_names = {e[0] for e in frontend_emits}
    all_emitters = backend_emit_names | frontend_emit_names

    for evt_name, fpath, ln in frontend_listens:
        # Ignore standard DOM events
        if evt_name in ("click", "change", "keydown", "keyup", "submit", "resize", "scroll", "load", "error", "message"):
            continue
        if evt_name not in all_emitters:
            gap_item = {
                "type": "DEAD_EVENT_LISTENER",
                "name": evt_name,
                "path": fpath,
                "line": ln,
                "detail": f"Listener registered for '{evt_name}' but no emitter was found in the codebase",
            }
            wiring_gaps.append(gap_item)
            entities.append((
                f"wiring_gap://event/{evt_name}/{fpath}:{ln}",
                "L4",
                "Event/Message Wiring Gap",
                fpath,
                ln,
                ln,
                evt_name,
                gap_item,
            ))

    record_entities_bulk(con, entities)
    con.commit()

    return {
        "swallow_count": len(swallow_findings),
        "wiring_gaps_count": len(wiring_gaps),
        "wiring_gaps": wiring_gaps[:15],
    }


# ---------------------------------------------------------------------------
# L5 — Architectural Boundary Layer
# ---------------------------------------------------------------------------

def scan_l5_architectural_boundaries(con: sqlite3.Connection) -> Dict[str, Any]:
    """Scan and record architectural layer violations and boundary integrity."""
    entities: List[Tuple[str, str, str, str, int, int, str, Optional[Dict[str, Any]]]] = []
    edges_l5: List[Tuple[str, str, str, str, Optional[Dict[str, Any]]]] = []

    LOW_LAYERS = ("lib/", "src/lib/", "packages/", "server/", "backend/")
    HIGH_LAYERS = ("app/", "pages/", "src/app/", "src/pages/", "components/", "src/components/", "frontend/", "ui/")

    violations: List[Dict[str, Any]] = []
    import_edges = con.execute("SELECT src, dst, src_path FROM edges WHERE kind='imports'").fetchall()

    for e in import_edges:
        s, d = e["src"], e["dst"]
        if s.startswith(LOW_LAYERS) and d.startswith(HIGH_LAYERS):
            v = {
                "source": s,
                "target": d,
                "rule": "ARCH-LAYER-VIOLATION",
                "detail": f"Lower library layer '{s}' directly imports upper UI/app layer '{d}'",
            }
            violations.append(v)
            entities.append((
                f"arch_violation://{s}->{d}",
                "L5",
                "Boundary Violation",
                s,
                1,
                1,
                f"{s} -> {d}",
                v,
            ))
            edges_l5.append((f"file://{s}", f"file://{d}", "violates_layer_boundary", "L5", v))

    record_entities_bulk(con, entities)
    record_edges_bulk(con, edges_l5)
    con.commit()

    return {
        "boundary_violations_count": len(violations),
        "violations": violations[:15],
    }


# ---------------------------------------------------------------------------
# L6 — Code Quality & Smells
# ---------------------------------------------------------------------------

def scan_l6_quality_and_smells(con: sqlite3.Connection, root: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Scan and record code smells, clone duplications, and untested hot-path symbols."""
    entities: List[Tuple[str, str, str, str, int, int, str, Optional[Dict[str, Any]]]] = []

    # 1. High-complexity symbols (>100 lines or CC > 15)
    large_syms = con.execute("""
        SELECT id, name, kind, path, start_line, end_line, end_line - start_line as size
        FROM symbols WHERE kind IN ('function', 'method') AND (end_line - start_line) > 80
        ORDER BY size DESC LIMIT 30
    """).fetchall()

    for s in large_syms:
        entities.append((
            f"smell_complexity://{s['id']}",
            "L6",
            "Complexity Trap",
            s["path"],
            s["start_line"],
            s["end_line"],
            s["name"],
            {"loc": s["size"], "threshold": 80},
        ))

    # 2. Untested load-bearing symbols (fan-in >= 5 with no tested_by edge)
    untested_hot = con.execute("""
        SELECT s.id, s.name, s.path, s.start_line, s.end_line, COUNT(e.src) as dependents
        FROM symbols s
        JOIN edges e ON e.dst = s.id AND e.kind IN ('calls', 'references')
        WHERE s.kind IN ('function', 'method', 'class')
          AND NOT EXISTS (SELECT 1 FROM edges t WHERE t.src = s.id AND t.kind = 'tested_by')
        GROUP BY s.id HAVING dependents >= 5
        ORDER BY dependents DESC LIMIT 30
    """).fetchall()

    for u in untested_hot:
        entities.append((
            f"smell_untested://{u['id']}",
            "L6",
            "Test Coverage Gap",
            u["path"],
            u["start_line"],
            u["end_line"],
            u["name"],
            {"dependents": u["dependents"], "severity": "critical" if u["dependents"] > 10 else "high"},
        ))

    # 3. Duplicate symbols (clone bodies)
    dup_rows = con.execute("""
        SELECT body_hash, COUNT(*) c, GROUP_CONCAT(id, ' | ') ids
        FROM symbols WHERE body_hash IS NOT NULL AND length(body) > 80
        GROUP BY body_hash HAVING c > 1 LIMIT 20
    """).fetchall()

    for d in dup_rows:
        ids = d["ids"].split(" | ")
        paths = sorted({i.split("://", 1)[-1].split("#")[0] for i in ids})
        if len(paths) >= 2:
            entities.append((
                f"smell_dup://{d['body_hash']}",
                "L6",
                "Duplication Cluster",
                paths[0],
                1,
                1,
                f"Clone cluster ({len(paths)} files)",
                {"copies": paths, "count": len(paths)},
            ))

    # 4. Debt markers (TODO/FIXME/HACK)
    chunk_rows = con.execute("SELECT path, start_line, text FROM chunks WHERE text LIKE '%TODO%' OR text LIKE '%FIXME%' OR text LIKE '%HACK%' LIMIT 50").fetchall()
    for cr in chunk_rows:
        text = cr["text"]
        for m in re.finditer(r"//\s*(TODO|FIXME|HACK):?\s*(.+)", text):
            entities.append((
                f"debt_marker://{cr['path']}:{cr['start_line']}:{m.group(1)}",
                "L6",
                "TODO/FIXME/HACK Debt Marker",
                cr["path"],
                cr["start_line"],
                cr["start_line"],
                m.group(1),
                {"comment": m.group(2)[:100]},
            ))

    record_entities_bulk(con, entities)
    con.commit()

    return {
        "large_symbols_count": len(large_syms),
        "untested_hot_count": len(untested_hot),
        "duplicate_clusters_count": len(dup_rows),
    }


# ---------------------------------------------------------------------------
# L7 — Cross-Cutting Concern Layer (Security, Env, Secrets)
# ---------------------------------------------------------------------------

def scan_l7_cross_cutting(con: sqlite3.Connection, root: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Scan and record cross-cutting security, secrets, and environment integrity entities."""
    from .stack import rules as stack_rules
    findings = stack_rules.run_rules(con, root, cfg)

    entities: List[Tuple[str, str, str, str, int, int, str, Optional[Dict[str, Any]]]] = []
    sec_count = 0

    for f in findings:
        r = f.get("rule", "")
        if r.startswith("SEC-") or r.startswith("ENV-") or r.startswith("NEXT-CLIENT") or r.startswith("TAURI-UNGATED"):
            sec_count += 1
            entities.append((
                f"cross_cutting://{r}/{f.get('path', '')}:{f.get('line', 0)}",
                "L7",
                "Secret/Credential Exposure" if "SECRET" in r else ("Security Anti-Pattern" if "SQL" in r else "Config Sprawl"),
                f.get("path", ""),
                f.get("line", 0),
                f.get("line", 0),
                f.get("title", ""),
                {
                    "rule": r,
                    "severity": f.get("severity", "medium"),
                    "suggestion": f.get("suggestion", ""),
                    "detail": f.get("detail", ""),
                },
            ))

    record_entities_bulk(con, entities)
    con.commit()

    return {
        "cross_cutting_findings_count": sec_count,
    }


# ---------------------------------------------------------------------------
# L8 — Runtime & Operational Signal Layer
# ---------------------------------------------------------------------------

def scan_l8_runtime_signals(con: sqlite3.Connection) -> Dict[str, Any]:
    """Scan durable snapshot history and record runtime telemetry status."""
    entities: List[Tuple[str, str, str, str, int, int, str, Optional[Dict[str, Any]]]] = []
    snapshots = con.execute("SELECT ts, job, health, components, counts, severity FROM snapshots ORDER BY ts DESC LIMIT 10").fetchall()

    for sn in snapshots:
        entities.append((
            f"snapshot://{sn['job']}/{sn['ts']}",
            "L8",
            "Operational Snapshot",
            "",
            0,
            0,
            sn["job"],
            {
                "timestamp": sn["ts"],
                "health": sn["health"],
                "components": sn["components"],
                "counts": sn["counts"],
                "severity": sn["severity"],
            },
        ))

    # Static-only signal status annotation
    record_entity(
        con,
        entity_id="runtime_signal://status",
        layer="L8",
        kind="Runtime Signal Status",
        path="",
        name="Telemetry & Runtime Status",
        attributes={
            "telemetry_status": "static_only" if not snapshots else "snapshot_backed",
            "snapshot_count": len(snapshots),
        },
    )

    record_entities_bulk(con, entities)
    con.commit()

    return {
        "snapshots_recorded": len(snapshots),
        "status": "snapshot_backed" if snapshots else "static_only",
    }


# ---------------------------------------------------------------------------
# L9 — Historical & Evolutionary Layer (Churn × Complexity Matrix)
# ---------------------------------------------------------------------------

def scan_l9_historical_signals(con: sqlite3.Connection, root: str) -> Dict[str, Any]:
    """Scan git churn, calculate co-change coupling, and build the Churn × Complexity Matrix."""
    entities: List[Tuple[str, str, str, str, int, int, str, Optional[Dict[str, Any]]]] = []
    edges_l9: List[Tuple[str, str, str, str, Optional[Dict[str, Any]]]] = []

    # 1. Hotspots from git history using open connection
    now = time.time()
    hotspot_rows = con.execute(
        "SELECT cf.path, c.ts FROM commit_files cf JOIN commits c ON c.sha=cf.sha"
    ).fetchall()
    scores: Dict[str, float] = {}
    for r in hotspot_rows:
        age_days = max(0.0, (now - r["ts"]) / 86400.0)
        w = 1.0 if age_days <= 30 else (0.5 if age_days <= 90 else 0.15)
        scores[r["path"]] = scores.get(r["path"], 0.0) + w
    hotspot_list = [{"path": p, "score": round(s, 1)} for p, s in sorted(scores.items(), key=lambda kv: -kv[1])[:30]]
    churn_map = {h["path"]: h["score"] for h in hotspot_list}

    for h in hotspot_list:
        entities.append((
            f"churn://{h['path']}",
            "L9",
            "Churn Metric",
            h["path"],
            1,
            1,
            os.path.basename(h["path"]),
            {"churn_score": h["score"]},
        ))

    # 2. Co-change edges from commit history
    co_change_rows = con.execute("SELECT src, dst FROM edges WHERE kind='co_change'").fetchall()
    for cc in co_change_rows:
        edges_l9.append((f"file://{cc['src']}", f"file://{cc['dst']}", "co_changes_with", "L9", {}))

    # 3. Churn × Complexity Hotspot Ranking
    composite_hotspots: List[Dict[str, Any]] = []
    sym_rows = con.execute("""
        SELECT s.id, s.name, s.path, s.start_line, s.end_line,
               (SELECT COUNT(*) FROM edges e WHERE e.dst = s.id AND e.kind IN ('calls', 'references')) as fan_in
        FROM symbols s WHERE s.kind IN ('function', 'method', 'class')
    """).fetchall()

    for s in sym_rows:
        p = s["path"]
        churn = churn_map.get(p, 0.15)
        lines = max(1, s["end_line"] - s["start_line"])
        fan_in = s["fan_in"]
        complexity_score = (lines / 10.0) + (fan_in * 2.0)
        hotspot_risk = round(churn * complexity_score, 1)

        if hotspot_risk >= 15.0:
            item = {
                "symbol_id": s["id"],
                "name": s["name"],
                "path": p,
                "churn_score": churn,
                "complexity_score": round(complexity_score, 1),
                "hotspot_risk": hotspot_risk,
            }
            composite_hotspots.append(item)
            entities.append((
                f"hotspot_risk://{s['id']}",
                "L9",
                "Churn × Complexity Hotspot",
                p,
                s["start_line"],
                s["end_line"],
                s["name"],
                item,
            ))

    composite_hotspots.sort(key=lambda x: x["hotspot_risk"], reverse=True)
    record_entities_bulk(con, entities)
    record_edges_bulk(con, edges_l9)
    con.commit()

    return {
        "churn_files_count": len(hotspot_list),
        "co_change_edges_count": len(co_change_rows),
        "composite_hotspots_count": len(composite_hotspots),
        "top_hotspots": composite_hotspots[:10],
    }


# ---------------------------------------------------------------------------
# Master Orchestration
# ---------------------------------------------------------------------------

def run_mdm_extraction(root: Optional[str] = None) -> Dict[str, Any]:
    """Execute complete L0 through L9 extraction pipeline and return layer summary."""
    root = root or repo_root()
    con = connect(root)
    cfg = load_config(root)

    t0 = time.time()
    clear_mdm_layer_data(con)

    l0_res = scan_l0_topology(con, root, cfg)
    l1_res = scan_l1_syntax(con)
    l2_res = scan_l2_symbols_and_deps(con, root)
    l3_res = scan_l3_types_and_semantics(con, root)
    l4_res = scan_l4_flow_and_wiring(con, root)
    l5_res = scan_l5_architectural_boundaries(con)
    l6_res = scan_l6_quality_and_smells(con, root, cfg)
    l7_res = scan_l7_cross_cutting(con, root, cfg)
    l8_res = scan_l8_runtime_signals(con)
    l9_res = scan_l9_historical_signals(con, root)
    elapsed = round(time.time() - t0, 2)

    total_entities = con.execute("SELECT COUNT(*) c FROM mdm_entities").fetchone()["c"]
    total_edges = con.execute("SELECT COUNT(*) c FROM mdm_edges").fetchone()["c"]

    return {
        "status": "success",
        "elapsed_seconds": elapsed,
        "total_mdm_entities": total_entities,
        "total_mdm_edges": total_edges,
        "layers": {
            "L0_topology": l0_res,
            "L1_syntax": l1_res,
            "L2_symbols": l2_res,
            "L3_types": l3_res,
            "L4_flow_and_wiring": l4_res,
            "L5_architecture": l5_res,
            "L6_quality": l6_res,
            "L7_cross_cutting": l7_res,
            "L8_runtime": l8_res,
            "L9_history": l9_res,
        },
    }
