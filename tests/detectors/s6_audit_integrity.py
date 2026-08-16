"""Phase 4 detector functions: audit/health-honesty metrics.

Each metric drives real product code (analysis.repo_health_report,
stack.audit.audit, stack.rules.run_rules) against deterministic seeded
fixtures in a tmp repo, so it stays true as the repo changes. Metrics
return an int COUNTER OF DIVERGENCES (0 = healthy) so RECALL/PRECISION
tests assert == 0.

Rules (TRACKER Phase 4 ENHANCE / 10-plan §4):
  AUDIT-FINDINGS-AUTO-CLOSED  — BUG-015: the auto-fix sweep must only close
      stale findings whose rule audit actually RAN this pass. Pre-fix it
      closed ANY open row not in `seen`, silently retiring ESLINT/custom/
      tauri findings ingested on other surfaces.
  AUDIT-SILENT-SUBINDEXER     — F-41/F-24: sub-indexer failures in
      audit(refresh=True) must surface, never be swallowed by log_swallowed.
  HEALTH-COVERAGE-ROOT        — BUG-014: repo_health_report(root) must thread
      root into gapfill.coverage(); pre-fix it read repo_root() (cwd) instead.
  HEALTH-QUALITY-FROM-FINDINGS— F-01/BUG-013/CORE-27: quality component must
      react to real open findings; pre-fix it called the nonexistent
      nextjs.list_findings and fell back to a fixed 80.
  HEALTH-EMPTY-REAL-RING      — CORE-30: empty repo (0 symbols) must not
      return the literal 50, and its ring must still react to findings.
"""

from __future__ import annotations

import os

from cipkg import analysis, base, store


# -- shared seed helpers -------------------------------------------------------

def _seed_dup_pair(con):
    """Insert two identical-body symbols so QA-DUP deterministically fires
    (gives audit() a non-empty `seen` set — the trigger for BUG-015)."""
    con.executemany(
        "INSERT INTO symbols(id,name,kind,path,start_line,end_line,"
        "signature,body_hash,body) VALUES(?,?,?,?,?,?,?,?,?)",
        [("python://src/a.ts#dupA", "dupA", "function", "src/a.ts", 1, 20,
          "dupA()", "ph4dup", "x" * 100),
         ("python://src/b.ts#dupB", "dupB", "function", "src/b.ts", 1, 20,
          "dupB()", "ph4dup", "x" * 100)])


def _seed_eslint_row(con, status="open"):
    """An ESLINT finding ingested through the separate eslint surface — never
    produced by run_rules, so audit() must never auto-close it."""
    from cipkg.stack.audit import _fid
    f = {"rule": "ESLINT:no-unused-vars", "path": "src/a.ts", "line": 3,
         "title": "unused var", "severity": "high"}
    con.execute(
        "INSERT INTO findings(id,rule,severity,path,line,symbol_id,title,"
        "detail,suggestion,effort,ts,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (_fid(f), f["rule"], f["severity"], f["path"], f["line"], None,
         f["title"], "", "", "small", 0.0, status))


def _insert_finding(con, rule, severity, path, title, line=1):
    from cipkg.stack.audit import _fid
    f = {"rule": rule, "severity": severity, "path": path, "line": line,
         "title": title}
    con.execute(
        "INSERT INTO findings(id,rule,severity,path,line,symbol_id,title,"
        "detail,suggestion,effort,ts,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (_fid(f), rule, severity, path, line, None, title, "", "", "small",
         0.0, "open"))


def _fresh_repo(root):
    """Open a real product connection on a tmp repo and ensure stack tables."""
    con = store.connect(str(root))
    from cipkg.stack.common import ensure
    ensure(con)
    return con


# -- BUG-015 -------------------------------------------------------------------

def findings_auto_closed_outside_run(root) -> int:
    """Count open findings flipped to 'fixed' whose rule audit did NOT run.

    Seeds an ESLINT row + a QA-DUP trigger (non-empty `seen`), runs the real
    audit(root, refresh=False), then counts 'fixed' rows whose rule is not in
    this pass's enabled rule set. Pre-fix the sweep closes the ESLINT row
    (returns 1); post-fix it survives (returns 0).
    """
    cfg = base.load_config(str(root))
    con = _fresh_repo(root)
    _seed_dup_pair(con)
    _seed_eslint_row(con)
    con.commit()
    from cipkg.stack.audit import audit
    audit(str(root), refresh=False)
    from cipkg.stack.custom_rules import get_all_rules
    enabled = ({rid for rid, _ in get_all_rules(str(root), cfg)}
               - set(cfg.get("audit", {}).get("ignore_rules", [])))
    fixed = [r["rule"] for r in con.execute(
        "SELECT rule FROM findings WHERE status='fixed'")]
    return sum(1 for rule in fixed if rule not in enabled)


# -- F-41 / F-24 ---------------------------------------------------------------

def audit_silent_subindexer_failures(root) -> int:
    """Count sub-indexer failures swallowed by audit(refresh=True).

    Stubs nextjs.index_routes and prisma.index_stack to raise, runs the real
    audit, then counts failures that never reach the returned summary.
    Pre-fix: both are swallowed (returns 2). Post-fix: they surface in the
    summary's failed_indexers list (returns 0).
    """
    from unittest import mock
    from cipkg.stack import audit as audit_mod
    called = {"nextjs": False, "prisma": False}

    def make(tag):
        def boom(con, root):
            called[tag] = True
            raise RuntimeError(f"{tag} indexer exploded")
        return boom

    with (mock.patch.object(audit_mod.nextjs, "index_routes", make("nextjs")),
          mock.patch.object(audit_mod.prisma, "index_stack", make("prisma"))):
        out = audit_mod.audit(str(root), refresh=True)
    surfaced = set(out.get("failed_indexers", []) or [])
    return sum(1 for tag, hit in called.items() if hit and tag not in surfaced)


# -- BUG-014 -------------------------------------------------------------------

def health_coverage_root_mismatch(root) -> int:
    """1 when repo_health_report(root) coverage came from the wrong repo.

    Seeds 3 function/method symbols, asks the real report for its coverage
    total, and compares with the root's own DB. Pre-fix gapfill.coverage()
    read repo_root()/cwd (~1699 on the live index); post-fix it reads root (3).
    """
    con = _fresh_repo(root)
    con.executemany(
        "INSERT INTO symbols(id,name,kind,path,start_line,end_line,"
        "signature,body_hash,body) VALUES(?,?,?,?,?,?,?,?,?)",
        [("python://src/app.py#f1", "f1", "function", "src/app.py", 1, 5,
          "def f1()", None, ""),
         ("python://src/app.py#f2", "f2", "function", "src/app.py", 7, 12,
          "def f2()", None, ""),
         ("python://src/lib.py#m1", "m1", "method", "src/lib.py", 2, 8,
          "def m1()", None, "")])
    con.commit()
    try:
        report = analysis.repo_health_report(str(root))
        got = report["test_coverage"]["actual_coverage"]["total_symbols"]
    except Exception:
        got = None
    return 0 if got == 3 else 1


# -- F-01 / BUG-013 / CORE-27 --------------------------------------------------

def health_quality_ignores_findings(root) -> int:
    """1 when the health quality component ignores a real critical finding.

    Measures the real report with and without one critical finding in the DB.
    Pre-fix the quality component calls the nonexistent nextjs.list_findings,
    falls back to 80, and the score does not move (returns 1). Post-fix it
    reads findings directly and the critical depresses the score (returns 0).
    """
    con = _fresh_repo(root)
    base_score = analysis.repo_health_report(str(root))["overall_score"]
    _insert_finding(con, "SEC-HARDCODED-SECRET", "critical", "src/app.py",
                    "hardcoded secret")
    con.commit()
    penalized = analysis.repo_health_report(str(root))["overall_score"]
    con.execute("DELETE FROM findings")
    con.commit()
    return 0 if penalized < base_score else 1


# -- CORE-30 -------------------------------------------------------------------

def health_empty_repo_literal(root) -> int:
    """1 when an empty repo yields the literal 50 (CORE-30) or its ring is
    finding-insensitive. Post-fix: derived score != 50 and a critical finding
    still depresses it (returns 0)."""
    con = _fresh_repo(root)
    base_score = analysis.repo_health_report(str(root))["overall_score"]
    _insert_finding(con, "SEC-HARDCODED-SECRET", "critical", "src/app.py",
                    "hardcoded secret")
    con.commit()
    penalized = analysis.repo_health_report(str(root))["overall_score"]
    con.execute("DELETE FROM findings")
    con.commit()
    if base_score == 50 or penalized >= base_score:
        return 1
    return 0