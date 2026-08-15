"""Audit orchestration: run rules → upsert findings (stable IDs, auto-fix),
quick wins, markdown reports, eslint ingestion, CI gate."""
import hashlib, json, os, sys, time
from ..base import repo_root, load_config
from ..store import connect
from .common import ensure
from . import rules as R
from . import nextjs, prisma

def _fid(f):
    return hashlib.sha1(
        f"{f['rule']}:{f['path']}:{f['line']}:{f['title']}".encode()).hexdigest()[:16]

def audit(root=None, refresh=True):
    root = root or repo_root(); cfg = load_config(root); con = connect(root)
    ensure(con)
    if refresh:
        try: nextjs.index_routes(con, root)
        except Exception: pass
        try: prisma.index_stack(con, root)
        except Exception: pass
    findings = R.run_rules(con, root, cfg)
    seen = set()
    for f in findings:
        fid = _fid(f); seen.add(fid)
        con.execute(
            "INSERT INTO findings(id,rule,severity,path,line,symbol_id,title,detail,"
            "suggestion,effort,ts,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,'open') "
            "ON CONFLICT(id) DO UPDATE SET severity=excluded.severity, title=excluded.title, "
            "detail=excluded.detail, suggestion=excluded.suggestion, "
            "effort=excluded.effort, ts=excluded.ts",
            (fid, f["rule"], f["severity"], f["path"], f["line"], f["symbol_id"],
             f["title"], f["detail"], f["suggestion"], f["effort"], time.time()))
    if seen:
        ph = ",".join("?" * len(seen))
        con.execute(f"UPDATE findings SET status='fixed' "
                    f"WHERE status='open' AND id NOT IN ({ph})", list(seen))
    con.commit()
    return summarize(con)

def summarize(con):
    rows = con.execute("SELECT severity, COUNT(*) c FROM findings "
                       "WHERE status='open' GROUP BY severity").fetchall()
    by = {r["severity"]: r["c"] for r in rows}
    return {"open": sum(by.values()), "by_severity": by,
            "critical": by.get("critical", 0), "high": by.get("high", 0)}

def findings(root=None, severity=None, rule=None, path=None, limit=100):
    con = connect(root or repo_root()); ensure(con)
    q, args = "SELECT * FROM findings WHERE status='open'", []
    if severity: q += " AND severity=?"; args.append(severity)
    if rule:     q += " AND rule=?";     args.append(rule)
    if path:     q += " AND path LIKE ?"; args.append(f"%{path}%")
    q += (" ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
          "WHEN 'medium' THEN 2 ELSE 3 END, rule LIMIT ?")
    args.append(limit)
    return [dict(r) for r in con.execute(q, args)]

def findings_structured(root=None, severity=None, rule=None, path=None, limit=100):
    """Return findings in machine-actionable structured format.
    
    Returns {file, line, rule_id, message, suggested_pattern} format
    that agents can directly convert to edits instead of parsing prose.
    """
    raw_findings = findings(root, severity, rule, path, limit)
    structured = []
    
    for f in raw_findings:
        structured.append({
            "file": f.get("path"),
            "line": f.get("line", 0),
            "rule_id": f.get("rule"),
            "message": f.get("title"),
            "suggested_pattern": f.get("suggestion", ""),
            "severity": f.get("severity"),
            "effort": f.get("effort", "unknown")
        })
    
    return structured

def audit_file(root, file_path):
    """Run audit scoped to a single file for fast post-edit checks.
    
    Returns only findings relevant to the specified file.
    """
    return findings(root, path=file_path, limit=20)

def audit_diff(root):
    """Run audit scoped to git diff for fast incremental checks.
    
    Returns findings only for files changed in the current working tree.
    """
    import subprocess
    try:
        # Get list of changed files
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True,
            text=True,
            cwd=root or repo_root()
        )
        changed_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
        
        if not changed_files:
            return {"findings": [], "changed_files": []}
        
        # Run audit for each changed file
        all_findings = []
        for file_path in changed_files:
            file_findings = findings(root, path=file_path, limit=10)
            all_findings.extend(file_findings)
        
        return {
            "findings": all_findings,
            "changed_files": changed_files,
            "total_findings": len(all_findings)
        }
        
    except Exception as e:
        return {"error": str(e), "findings": []}

def quick_wins(root=None, limit=10):
    con = connect(root or repo_root()); ensure(con)
    rows = con.execute(
        "SELECT * FROM findings WHERE status='open' AND suggestion != '' "
        "AND severity IN ('critical','high','medium') AND effort IN ('trivial','small') "
        "ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END, "
        "CASE effort WHEN 'trivial' THEN 0 ELSE 1 END LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

def ingest_eslint(root, file_path):
    root = root or repo_root(); con = connect(root); ensure(con)
    text = sys.stdin.read() if file_path == "-" else open(file_path, encoding="utf-8").read()
    data = json.loads(text)
    n = 0
    for fr in data:
        rel = os.path.relpath(fr.get("filePath", ""), root).replace(os.sep, "/")
        for msg in fr.get("messages", []):
            f = {"rule": f"ESLINT:{msg.get('ruleId') or 'parse'}",
                 "severity": "high" if msg.get("severity", 1) == 2 else "low",
                 "path": rel, "line": msg.get("line", 0), "symbol_id": None,
                 "title": msg.get("message", "")[:200], "detail": "",
                 "suggestion": "", "effort": "small"}
            con.execute(
                "INSERT INTO findings(id,rule,severity,path,line,symbol_id,title,detail,"
                "suggestion,effort,ts,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,'open') "
                "ON CONFLICT(id) DO UPDATE SET ts=excluded.ts",
                (_fid(f), f["rule"], f["severity"], f["path"], f["line"], None,
                 f["title"], "", "", f["effort"], time.time()))
            n += 1
    con.commit()
    return {"ingested": n, "kind": "eslint"}

def report_markdown(root=None):
    root = root or repo_root(); con = connect(root); ensure(con)
    s = summarize(con)
    lines = ["# CIP Stack Audit", "",
             f"Open findings: **{s['open']}** — " +
             ", ".join(f"{v} {k}" for k, v in sorted(s["by_severity"].items())), ""]
    for sev in ("critical", "high", "medium", "low"):
        rows = con.execute("SELECT * FROM findings WHERE status='open' AND severity=? "
                           "ORDER BY rule LIMIT 25", (sev,)).fetchall()
        if not rows: continue
        lines += [f"## {sev.title()} ({len(rows)})", ""]
        for r in rows:
            loc = r["path"] + (f":{r['line']}" if r["line"] else "")
            lines.append(f"- **[{r['rule']}]** `{loc}` — {r['title']}")
            if r["suggestion"]:
                lines.append(f"  - fix: {r['suggestion']} *(effort: {r['effort']})*")
        lines.append("")
    qw = quick_wins(root, limit=10)
    if qw:
        lines += ["## Quick wins", "",
                  "| Rule | Location | Fix | Effort |", "|---|---|---|---|"]
        for q in qw:
            lines.append(f"| {q['rule']} | `{q['path']}` | {q['suggestion'][:90]} | {q['effort']} |")
    return "\n".join(lines) + "\n"

def gate(root=None):
    """CI/pre-commit quality gate: exit non-zero on criticals or broken signals."""
    root = root or repo_root()
    from .. import indexer
    from ..runtime_adapters import broken
    indexer.sync(root)
    stats = audit(root, refresh=True)
    fails = len(broken(root)["signals"])
    reasons = []
    if stats.get("critical", 0):
        reasons.append(f"{stats['critical']} critical findings")
    if fails:
        reasons.append(f"{fails} failing test/type signals")
    return {"ok": not reasons, "reasons": reasons,
            "findings": stats, "broken_signals": fails}
