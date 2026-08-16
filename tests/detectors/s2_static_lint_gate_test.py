"""S2 static-lint gate detector tests (CODE-UNDEFINED-NAME / F401 family).

Regression-locks RUNBOOK §4.4:

* RECALL  — pyflakes on the still-broken lib fires on the untracked evidence of
  BUG-005/F-02 (`lancedb_store.py:55` uses `json` without importing it) and the
  F-09 unused-import/undefined-name class.
* PRECISION — the same gate is SILENT on the pinned clean reference repo
  (`tests/data/clean_ref/`). A firing detector that stays quiet on clean code is
  the campaign's pass condition (RUNBOOK §4.3, LEDGER §3).

The lib fixes themselves land LATER by design (detect-first, fix-last): the
`import json` fix for BUG-005/F-02 is Phase 0 row 9; F-09 cleanup is Phase 0
row 11. When those land, the RECALL assertion below is retired and flipped to a
`should-be-clean` assertion (see `test_static_lint_gate_clean_path`), not edited
silently — flip it in the same commit as the fix and update LEDGER.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

LIB_DIR = pathlib.Path(__file__).resolve().parents[2] / "lib" / "cipkg"
CLEAN_REF = pathlib.Path(__file__).resolve().parents[1] / "data" / "clean_ref"

# Evidence captured from the broken repo on 2026-08-16 (pyflakes 3.4.0, Py 3.14.4).
# BUG-005 / F-02.
BROKEN_EVIDENCE = ("lancedb_store.py", "undefined name 'json'")
# F-09 (pyflakes-flagged unused/undefined, verified live).
F09_EVIDENCE = ("command_registry.py", "'inspect' imported but unused")


def _pyflakes(targets: list[str]) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pyflakes", *targets],
        capture_output=True,
        text=True,
        cwd=pathlib.Path(__file__).resolve().parents[2],
    )
    return result.stdout


def test_s2_recall_broken_code():
    """RECALL: the gate must fire on the still-broken repo evidence."""
    out = _pyflakes([str(LIB_DIR / "lancedb_store.py")])
    assert BROKEN_EVIDENCE[0] in out and BROKEN_EVIDENCE[1] in out, (
        f"S2 gate failed to fire on BUG-005/F-02 evidence. Got:\n{out}"
    )


def test_s2_recall_f09_class():
    """RECALL: the gate fires on the F-09 unused-import class."""
    out = _pyflakes([str(LIB_DIR / "command_registry.py")])
    assert F09_EVIDENCE[0] in out and F09_EVIDENCE[1] in out, (
        f"S2 gate failed to fire on F-09 evidence. Got:\n{out}"
    )


def test_s2_precision_clean_ref():
    """PRECISION (mandatory): the gate is SILENT on the clean reference repo."""
    out = _pyflakes([str(CLEAN_REF)])
    assert out.strip() == "", f"S2 gate produced false positives:\n{out}"