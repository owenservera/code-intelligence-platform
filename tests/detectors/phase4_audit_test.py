"""Phase 4 regression tests: audit/health-honesty detectors.

RUNBOOK §4 / TRACKER Phase 4 / 10-plan §4. Regression-locks five audit/health
honesty fixes on the retail surface, all driven by real product code against
deterministic seeded fixtures:

F-01/BUG-013/CORE-27  HEALTH-QUALITY-FROM-FINDINGS — quality component must
      react to real open findings. Pre-fix it called nextjs.list_findings
      (does not exist on the nextjs module) so `except` fell back to a fixed
      80 and the score never moved with severity counts.
BUG-014               HEALTH-COVERAGE-ROOT — repo_health_report(root) must
      thread root into gapfill.coverage(); pre-fix it read repo_root()/cwd.
BUG-015               AUDIT-FINDINGS-AUTO-CLOSED — the auto-fix sweep must
      only close stale findings whose rule audit RAN this pass; pre-fix it
      closed any open row not in `seen`, retiring ESLINT/custom findings.
F-24/F-41             AUDIT-SILENT-SUBINDEXER — sub-indexer failures in
      audit(refresh=True) must surface in the result, not be swallowed.
CORE-30               HEALTH-EMPTY-REAL-RING — empty repo (0 symbols) must
      not return the literal 50 and must still react to findings.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from cipkg import base, store  # noqa: E402
from cipkg.stack.common import ensure  # noqa: E402

from s6_audit_integrity import (  # noqa: E402
    audit_silent_subindexer_failures,
    findings_auto_closed_outside_run,
    health_coverage_root_mismatch,
    health_empty_repo_literal,
    health_quality_ignores_findings,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def audit_root(tmp_path):
    """A real tmp repo (`.cip`, index DB, stack tables) for detector seeds."""
    root = tmp_path / "repo"
    root.mkdir()
    con = store.connect(str(root))
    ensure(con)
    con.commit()
    con.close()
    return root


# ---------------------------------------------------------------------------
# BUG-015 — auto-close sweep must not retire findings from rules it didn't run
# ---------------------------------------------------------------------------

def test_bug015_eslint_rows_survive_audit(audit_root):
    # RECALL: an ESLINT finding ingested on the eslint surface must not be
    # silently retired by a later stack audit (pre-fix it was).
    assert findings_auto_closed_outside_run(str(audit_root)) == 0


def test_bug015_sweep_still_closes_stale_rows_of_run_rules(audit_root):
    # PRECISION: the sweep must still auto-close stale findings of rules that
    # DID run this pass (standard auditing keeps working).
    from cipkg.stack.audit import _fid, audit
    con = store.connect(str(audit_root))
    from s6_audit_integrity import _seed_dup_pair
    _seed_dup_pair(con)
    stale = {"rule": "QA-DUP", "path": "src/a.ts", "line": 999,
             "title": "Identical implementation in 2 places"}
    con.execute(
        "INSERT INTO findings(id,rule,severity,path,line,symbol_id,title,"
        "detail,suggestion,effort,ts,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (_fid(stale), "QA-DUP", "low", "src/a.ts", 999, None, stale["title"],
         "", "", "small", 0.0, "open"))
    con.commit()
    audit(str(audit_root), refresh=False)
    row = con.execute(
        "SELECT status FROM findings WHERE id=?", (_fid(stale),)).fetchone()
    # its line moved (999 -> 0), so the rule re-issued a NEW id and the old
    # one is genuinely stale → must have been closed
    assert row is None or row["status"] == "fixed"


# ---------------------------------------------------------------------------
# F-41 / F-24 — sub-indexer failures must surface, not be swallowed
# ---------------------------------------------------------------------------

def test_f41_subindexer_failures_surfaced(audit_root):
    # RECALL: nextjs.index_routes / prisma.index_stack raising must be visible
    # in the audit result (pre-fix both were swallowed by log_swallowed).
    assert audit_silent_subindexer_failures(str(audit_root)) == 0


def test_f41_clean_audit_reports_no_failures(audit_root):
    # PRECISION: a healthy audit reports an empty failed_indexers list (the
    # key must exist so consumers can distinguish "no failures" from "silent").
    from cipkg.stack import audit
    out = audit.audit(str(audit_root), refresh=True)
    assert out.get("failed_indexers") == []


# ---------------------------------------------------------------------------
# BUG-014 — coverage must be read from the requested root
# ---------------------------------------------------------------------------

def test_bug014_coverage_reads_given_root(audit_root):
    # RECALL: when a caller passes root, health coverage must come from that
    # root's index, not repo_root()/cwd (pre-fix it read the live/cwd DB).
    assert health_coverage_root_mismatch(str(audit_root)) == 0


def test_bug014_no_mismatch_when_cwd_is_root(audit_root, monkeypatch):
    # PRECISION: single-repo usage (cwd == root) matches regardless of the
    # root-threading fix — no spurious divergence when paths align.
    monkeypatch.chdir(str(audit_root))
    assert health_coverage_root_mismatch(str(audit_root)) == 0


# ---------------------------------------------------------------------------
# F-01 / BUG-013 / CORE-27 — quality must react to real findings
# ---------------------------------------------------------------------------

def test_f01_quality_reacts_to_findings(audit_root):
    # RECALL: adding a critical finding must depress overall_score. Pre-fix
    # the quality component never read findings (fallback 80), so the score
    # was insensitive to severity (detector returns 1).
    assert health_quality_ignores_findings(str(audit_root)) == 0


# ---------------------------------------------------------------------------
# CORE-30 — empty repo must have a real (non-literal-50) ring
# ---------------------------------------------------------------------------

def test_core30_empty_repo_has_real_ring(audit_root):
    # RECALL: an empty repo (0 symbols) must not hardcode 50 and must still
    # penalize findings (pre-fix `_calculate_health_score` had a literal 50
    # early-return that also masked findings entirely).
    assert health_empty_repo_literal(audit_root) == 0