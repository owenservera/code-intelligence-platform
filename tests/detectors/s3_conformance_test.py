"""S3 — signature / attribute conformance suite (DESIGN §6.3, TRACKER Phase S S3).

Proves the conformance detector (`s3_conformance.conformance_checks`):
- RECALL: it fires on `lib/cipkg`'s documented broken wiring — F-16 (21 parsed
  but undespatched subcommands), F-17 (verify-index misrouted), F-15 (analyze/
  rebuild arity mismatch), F-34 (selftest symbol), F-13 (context-import of
  nonexistent submodules), F-21/F-31/F-32 (attribute calls on attributes the
  modules never export), F-20 (FilterEngine.rank), F-35 (15 registry imports of
  handlers cli.py never defines).
- PRECISION: 0 findings on a synthetic clean package (all wiring consistent)
  and on the clean_ref fixture.

Phase 0 flips (RUNBOOK §4 step 7 — signal flips healthy): F-34 (cli),
F-35/CORE-5 (registry handler imports), F-13 (workflow_engine), F-20
(FilterEngine.rank), F-31 (session runtime_adapters + map_ keys), F-13-cli
(.ingest) and F-35-cli (mcp_main) now assert the evidence is GONE from the live
CLI surface. The remaining live findings are Phase 1 dispatch gaps (F-16/F-17/
F-15) and legacy-frontend deletion targets (terminal_dashboard/web_server/
watcher — replaced by the new frontend), so the RECALL assertions for those
stay.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from tests.detectors import s3_conformance as cc  # noqa: E402

PKG = str(ROOT / "lib" / "cipkg")


def _rules() -> set[str]:
    return {f["rule"] for f in cc.conformance_checks(PKG, "cipkg")}


def _evidence(rule: str) -> list[str]:
    return [f["evidence"] for f in cc.conformance_checks(PKG, "cipkg") if f["rule"] == rule]


# ---------------------------------------------------------------------------
# RECALL — fires on the repo's documented broken wiring
# ---------------------------------------------------------------------------

def test_s3_recall_f16_unhandled_commands():
    """F-16: the 21 registered-but-undispatched subcommands are surfaced."""
    ev = _evidence("CODE-UNHANDLED-COMMAND")
    assert len(ev) >= 21
    for cmd in ("gate", "coverage", "deps", "embedder", "dashboard", "admission",
                "refactors", "routes", "models", "embed-ping", "dead", "circular",
                "blame", "score", "migrations", "env", "logs", "metrics",
                "features", "api", "predict"):
        assert any(cmd in e for e in ev), cmd


def test_s3_recall_f17_misrouted_command():
    """F-17: 'verify-index' is routed to the wrong handler."""
    ev = _evidence("CODE-MISROUTED-COMMAND")
    assert any("verify-index" in e and "handle_verify_command" in e and "handle_verify_index_command" in e for e in ev)


def test_s3_recall_f15_arity_mismatch():
    """F-15: analyze/rebuild handlers cannot accept dispatch's (root, args)."""
    ev = _evidence("CODE-ARITY-MISMATCH")
    assert any("handle_analyze_command" in e for e in ev)
    assert any("handle_rebuild_command" in e for e in ev)


def test_s3_clean_path_f34_selftest_symbol():
    """F-34 (flip): cli.py imports run_selftest, not the nonexistent selftest.

    The remaining `terminal_dashboard.py:985 from cipkg.selftest import
    selftest` site is a legacy-TUI deletion target (new frontend replaces it)
    and stays a documented pending finding, not a live-surface defect.
    """
    ev = _evidence("CODE-MISSING-SYMBOL")
    assert not any("from .selftest import selftest" in e for e in ev)
    assert not any("cli.py" in e and "selftest" in e for e in ev)


def test_s3_clean_path_f35_registry_handler_imports():
    """F-35/CORE-5 (flip): cli.py now defines every registry-imported handler."""
    ev = _evidence("CODE-MISSING-SYMBOL")
    for name in ("handle_gate_command", "handle_deps_command", "handle_predict_command",
                 "handle_coverage_command", "handle_env_command", "handle_api_command",
                 "handle_blame_command", "handle_circular_command", "handle_dead_command",
                 "handle_features_command", "handle_logs_command", "handle_metrics_command",
                 "handle_migrations_command", "handle_refactors_command"):
        assert not any(f"from .cli import {name}" in e for e in ev), name


def test_s3_clean_path_f13_context_imports():
    """F-13 (flip): workflow_engine imports resolve to cipkg.stack.audit/impact."""
    ev = _evidence("CODE-MISSING-SYMBOL") + _evidence("CODE-MISSING-MODULE")
    assert not any("workflow_engine" in e and "import audit" in e for e in ev)
    assert not any("workflow_engine" in e and "import impact" in e for e in ev)


def test_s3_recall_module_attribute_calls():
    """F-21/F-31/F-32: attribute calls on attributes the modules never export.

    F-31 (retrieve.runtime_adapters.broken) was fixed in Phase 0 — flipped to
    clean. F-21 (retrieve.hybrid_search, web_server) and F-32
    (indexer.mark_for_reindex, watcher) are legacy-frontend deletion targets
    and remain live findings until the Phase 1/5 sweep.
    """
    ev = _evidence("CODE-MISSING-SYMBOL")
    assert not any("retrieve.runtime_adapters.broken" in e for e in ev)  # F-31 fixed
    assert any("retrieve.hybrid_search" in e for e in ev)          # F-21 /api/search 500
    assert any("indexer.mark_for_reindex" in e for e in ev)        # F-32 watcher re-index


def test_s3_clean_path_f20_class_instance_member():
    """F-20 (flip): SuggestionEngine now calls FilterEngine.filter (rank gone)."""
    ev = _evidence("CODE-MISSING-SYMBOL")
    assert not any("filter_engine.rank" in e for e in ev)


def test_s3_clean_path_new_broken_import():
    """cli.py (flip): .ingest and server.mcp_main imports now resolve."""
    ev = _evidence("CODE-MISSING-MODULE") + _evidence("CODE-MISSING-SYMBOL")
    assert not any("cli.py" in e and "ingest" in e for e in ev)
    assert not any("from .server import mcp_main" in e for e in ev)


# ---------------------------------------------------------------------------
# PRECISION — silent on clean wiring
# ---------------------------------------------------------------------------

def test_s3_precision_clean_synthetic_package():
    """A well-formed package (all wiring consistent) yields zero findings."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = pathlib.Path(tmp) / "greppkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "libs.py").write_text(
            "def find():\n"
            "    return []\n"
            "def index():\n"
            "    return 0\n",
            encoding="utf-8",
        )
        (pkg / "cli.py").write_text(
            "import argparse\n"
            "def setup_argument_parser():\n"
            "    p = argparse.ArgumentParser()\n"
            "    sub = p.add_subparsers(dest='cmd')\n"
            "    sub.add_parser('find')\n"
            "    sub.add_parser('index')\n"
            "    sub.add_parser('verify-index')\n"
            "    return p\n"
            "def handle_find_command(root, args):\n"
            "    from .libs import find\n"
            "    return find()\n"
            "def handle_index_command(root, args):\n"
            "    from .libs import index\n"
            "    return index()\n"
            "def handle_verify_index_command(root, args):\n"
            "    return None\n"
            "def dispatch_command(root, args):\n"
            "    from .libs import find, index\n"
            "    handlers = {\n"
            "        'find': handle_find_command,\n"
            "        'index': handle_index_command,\n"
            "        'verify-index': handle_verify_index_command,\n"
            "    }\n"
            "    return handlers[args.cmd](root, args)\n"
            "class Searcher:\n"
            "    def __init__(self):\n"
            "        self.lib = Libs()\n"
            "    def run(self):\n"
            "        return self.lib.find()\n"
            "class Libs:\n"
            "    def find(self):\n"
            "        return ['ok']\n",
            encoding="utf-8",
        )
        findings = cc.conformance_checks(str(pkg), "greppkg")
    assert findings == [], f"conformance FPs on clean package: {findings[:3]}"


def test_s3_precision_clean_ref():
    """The clean_ref fixture stays silent (imports + no cli wiring)."""
    clean = str(ROOT / "tests" / "data" / "clean_ref")
    findings = cc.conformance_checks(clean, "clean_ref")
    assert findings == [], f"conformance FPs on clean_ref: {findings}"


# ---------------------------------------------------------------------------
# Lock sanity — the suite itself is a real assertion gate
# ---------------------------------------------------------------------------

def test_s3_findings_are_evidence_carrying():
    """Every finding carries DESIGN-contract evidence; no bare assertions."""
    findings = cc.conformance_checks(PKG, "cipkg")
    for f in findings:
        assert f["evidence"], f["rule"]
        assert f["finding_ref"], f["rule"]