"""S2 static-lint gate detector tests (CODE-UNDEFINED-NAME / F401 family).

Regression-locks RUNBOOK §4.4:

* RECALL  — the gate fires on undefined-name / unused-import evidence. Per
  detect-first / fix-last, the lib fixes for BUG-005/F-02 (row 9), F-06 (row 10)
  and the F-09 class (row 11) landed in Phase 0, so those RECALL assertions were
  FLIPPED to should-be-clean assertions (see the two tests below) — the gate
  must now stay silent on the fixed files.
* PRECISION — the same gate is SILENT on the pinned clean reference repo
  (`tests/data/clean_ref/`). A firing detector that stays quiet on clean code is
  the campaign's pass condition (RUNBOOK §4.3, LEDGER §3).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

LIB_DIR = pathlib.Path(__file__).resolve().parents[2] / "lib" / "cipkg"
CLEAN_REF = pathlib.Path(__file__).resolve().parents[1] / "data" / "clean_ref"


def _pyflakes(targets: list[str]) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pyflakes", *targets],
        capture_output=True,
        text=True,
        cwd=pathlib.Path(__file__).resolve().parents[2],
    )
    return result.stdout


def test_s2_clean_path_bug005():
    """FLIPPED (Phase 0): the BUG-005/F-02 site no longer fires — `lancedb_store.py`
    imports `json` (and the previously-undef `json` NameError is gone)."""
    out = _pyflakes([str(LIB_DIR / "lancedb_store.py")])
    assert "undefined name 'json'" not in out, f"BUG-005/F-02 no longer broken:\n{out}"


def test_s2_clean_path_f09_class():
    """FLIPPED (Phase 0): the F-09 unused-import class no longer fires on the
    targeted files — `command_registry.py` no longer imports unused `inspect`."""
    out = _pyflakes([str(LIB_DIR / "command_registry.py")])
    assert "'inspect' imported but unused" not in out, (
        f"F-09 site no longer broken:\n{out}"
    )


def test_s2_precision_clean_ref():
    """PRECISION (mandatory): the gate is SILENT on the clean reference repo."""
    out = _pyflakes([str(CLEAN_REF)])
    assert out.strip() == "", f"S2 gate produced false positives:\n{out}"