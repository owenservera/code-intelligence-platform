"""S1 regression test: no-bare-except swallow discipline.

Families covered (09): F-24/F-41 (stack/audit.py silent no-op on sub-indexers),
F-11/CORE-41 (base.py load_config bare pass), CORE-52 (suggestion_engine.py
print-swallow). RECALL fires on the live evidence; after the Phase-S fixes the
same test is flipped to assert the evidence sites are clean (RUNBOOK §4.3).

Precision is locked by tests/data/clean_ref: sample.py and good_handling.py
must both yield zero findings (zero false positives).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "detectors"))

from s1_swallow_scanner import scan_path

AUDIT = ROOT / "lib" / "cipkg" / "stack" / "audit.py"
BASE = ROOT / "lib" / "cipkg" / "base.py"
SUGGESTION_ENGINE = ROOT / "lib" / "cipkg" / "suggestion_engine.py"
CLEAN_REF = ROOT / "tests" / "data" / "clean_ref"


def test_s1_recall_evidence_sites():
    """RECALL: the scanner MUST fire on the retired-evidence swallow sites.

    Flip note (RUNBOOK §4): this test originally asserted the evidence existed
    (audit.py 19/21, base.py 144, suggestion_engine.py 657). The S1 fixes ran
    LAST, so it now asserts those same sites are clean — the flip.
    """
    findings = scan_path(AUDIT) + scan_path(BASE) + scan_path(SUGGESTION_ENGINE)
    lines = {(f["file"], f["line"]) for f in findings}
    # stack/audit.py:18-21 — try/except Exception + log_swallowed (F-24/F-41 GONE)
    assert (str(AUDIT).replace("\\", "/"), 19) not in lines
    assert (str(AUDIT).replace("\\", "/"), 21) not in lines
    # base.py:144-146 — except Exception + log_swallowed (F-11 / CORE-41)
    assert (str(BASE).replace("\\", "/"), 144) not in lines
    # suggestion_engine.py:657-659 — routed from print to log_swallowed (CORE-52)
    assert (str(SUGGESTION_ENGINE).replace("\\", "/"), 657) not in lines


def test_s1_precision_clean_ref():
    """PRECISION: zero findings on the clean / well-handled reference modules."""
    findings = scan_path(CLEAN_REF)
    assert findings == []