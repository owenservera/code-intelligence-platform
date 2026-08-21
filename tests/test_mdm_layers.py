"""test_mdm_layers.py — Test suite for Master Data Model (L0–LA) Layers, Extraction, and Synthesis.
"""
import json
import os
import sqlite3
import tempfile
import pytest
from pathlib import Path

from cipkg.store import connect, SCHEMA_VERSION
from cipkg.mdm_schema import (
    init_mdm_schema,
    record_entity,
    record_finding_with_trace,
    query_findings,
    get_explainability_trace,
)
from cipkg.mdm_engine import (
    scan_l0_topology,
    scan_l1_syntax,
    scan_l2_symbols_and_deps,
    scan_l3_types_and_semantics,
    scan_l4_flow_and_wiring,
    scan_l5_architectural_boundaries,
    scan_l6_quality_and_smells,
    scan_l8_runtime_signals,
    scan_l9_historical_signals,
    run_mdm_extraction,
)
from cipkg.mdm_synthesis import (
    synthesize_la_findings,
    compute_repo_scorecard,
    generate_full_mdm_report,
    format_report_markdown,
)


@pytest.fixture
def mock_repo(tmp_path):
    """Create a mock repository with files across layers."""
    # Create directories
    (tmp_path / "lib").mkdir()
    (tmp_path / "app").mkdir()
    (tmp_path / ".cip" / "data").mkdir(parents=True)

    # 1. Lib file with function & swallow
    lib_file = tmp_path / "lib" / "core.py"
    lib_file.write_text(
        "class Engine:\n"
        "    def run(self):\n"
        "        try:\n"
        "            x = 1 / 0\n"
        "        except Exception:\n"
        "            pass\n",
        encoding="utf-8",
    )

    # 2. App file with layer violation
    app_file = tmp_path / "app" / "main.py"
    app_file.write_text(
        "from lib.core import Engine\n"
        "def main():\n"
        "    e = Engine()\n"
        "    e.run()\n",
        encoding="utf-8",
    )

    # 3. TS file with Tauri IPC and type leak
    ts_file = tmp_path / "app" / "ui.ts"
    ts_file.write_text(
        "import { invoke } from '@tauri-apps/api';\n"
        "export function loadData(): any {\n"
        "    return invoke('non_existent_command');\n"
        "}\n",
        encoding="utf-8",
    )

    # Populate index.db
    con = connect(str(tmp_path))
    con.execute(
        "INSERT INTO files(path, language, size, lines, hash, mtime, indexed_at, tier) "
        "VALUES('lib/core.py', 'python', 120, 6, 'h1', 100.0, 100.0, 'code')"
    )
    con.execute(
        "INSERT INTO files(path, language, size, lines, hash, mtime, indexed_at, tier) "
        "VALUES('app/main.py', 'python', 100, 4, 'h2', 100.0, 100.0, 'code')"
    )
    con.execute(
        "INSERT INTO files(path, language, size, lines, hash, mtime, indexed_at, tier) "
        "VALUES('app/ui.ts', 'typescript', 150, 5, 'h3', 100.0, 100.0, 'code')"
    )

    con.execute(
        "INSERT INTO symbols(id, name, kind, path, start_line, end_line, signature, body_hash, body) "
        "VALUES('py://lib/core.py#Engine.run', 'run', 'method', 'lib/core.py', 2, 6, 'def run(self):', 'b1', 'body text')"
    )
    con.execute(
        "INSERT INTO symbols(id, name, kind, path, start_line, end_line, signature, body_hash, body) "
        "VALUES('ts://app/ui.ts#loadData', 'loadData', 'function', 'app/ui.ts', 2, 4, 'export function loadData()', 'b2', 'body text')"
    )

    # Add edges
    con.execute("INSERT INTO edges(src, dst, kind, src_path) VALUES('app/main.py', 'lib/core.py', 'imports', 'app/main.py')")
    con.execute("INSERT INTO edges(src, dst, kind, src_path) VALUES('py://app/main.py#main', 'py://lib/core.py#Engine.run', 'calls', 'app/main.py')")
    con.commit()

    return tmp_path


def test_mdm_schema_initialization(mock_repo):
    """Test that MDM schema tables are created and schema version is 5."""
    con = connect(str(mock_repo))
    assert SCHEMA_VERSION == 5

    # Check tables exist
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "mdm_entities" in tables
    assert "mdm_edges" in tables
    assert "mdm_findings" in tables
    assert "mdm_traces" in tables


def test_l0_topology_extraction(mock_repo):
    """Test L0 topology extraction."""
    con = connect(str(mock_repo))
    res = scan_l0_topology(con, str(mock_repo))
    assert res["total_files"] == 3
    # Check repository entity
    repo_ent = con.execute("SELECT * FROM mdm_entities WHERE layer='L0' AND kind='Repository'").fetchone()
    assert repo_ent is not None


def test_l1_syntax_extraction(mock_repo):
    """Test L1 syntax parsing and AST entities."""
    con = connect(str(mock_repo))
    res = scan_l1_syntax(con)
    assert res["ast_nodes_count"] == 2
    assert res["functions_count"] == 2


def test_l2_symbols_and_deps(mock_repo):
    """Test L2 symbol resolution and graph degrees."""
    con = connect(str(mock_repo))
    res = scan_l2_symbols_and_deps(con, str(mock_repo))
    assert res["symbols_count"] == 2


def test_l3_types_and_semantics(mock_repo):
    """Test L3 type leak detection."""
    con = connect(str(mock_repo))
    res = scan_l3_types_and_semantics(con, str(mock_repo))
    assert res["any_usages_count"] >= 1


def test_l4_wiring_gaps(mock_repo):
    """Test L4 Tauri IPC wiring gap and swallow detection."""
    con = connect(str(mock_repo))
    res = scan_l4_flow_and_wiring(con, str(mock_repo))
    assert res["wiring_gaps_count"] >= 1
    gap = res["wiring_gaps"][0]
    assert gap["name"] == "non_existent_command"


def test_la_synthesis_and_explainability_trace(mock_repo):
    """Test LA synthesis produces Finding Records with valid Explainability Traces."""
    con = connect(str(mock_repo))
    run_mdm_extraction(str(mock_repo))
    findings = synthesize_la_findings(con, str(mock_repo))

    assert len(findings) > 0
    # Check that findings have explainability traces
    for f in findings:
        trace = get_explainability_trace(con, f["finding_id"])
        assert len(trace) >= 2
        layers = [t["layer"] for t in trace]
        assert "L0" in layers
        assert "LA" in layers


def test_repo_scorecard(mock_repo):
    """Test 5-dimensional scorecard and letter grades."""
    con = connect(str(mock_repo))
    run_mdm_extraction(str(mock_repo))
    synthesize_la_findings(con, str(mock_repo))

    sc = compute_repo_scorecard(con)
    assert "overall_score" in sc
    assert "overall_grade" in sc
    assert "dimensions" in sc
    assert "reliability_and_flow" in sc["dimensions"]
    assert "security_and_secrets" in sc["dimensions"]


def test_full_report_generation_and_markdown(mock_repo):
    """Test generation of the full executive dossier and markdown formatting."""
    rep = generate_full_mdm_report(str(mock_repo))
    assert "scorecard" in rep
    assert "prioritized_findings" in rep

    md = format_report_markdown(rep)
    assert "# 📊 CIP Repository Forensic Intelligence & Master Data Report (L0–LA)" in md
    assert "5-Dimensional Health Scorecard" in md
    assert "Explainability Trace" in md
