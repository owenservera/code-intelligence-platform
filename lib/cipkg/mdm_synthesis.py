"""mdm_synthesis.py — Master Data Model Layer LA (Governance, Risk & Synthesis Engine).

Synthesizes L0–L9 empirical evidence into prioritized Finding Records, generates
deterministic Explainability Traces, calculates Technical Debt Index, and formats
comprehensive Executive Dossiers and Scorecards.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

from .base import repo_root, load_config
from .store import connect
from .mdm_schema import record_finding_with_trace, query_findings, get_explainability_trace
from .mdm_engine import run_mdm_extraction


SEVERITY_WEIGHTS = {"critical": 35.0, "high": 20.0, "medium": 10.0, "low": 4.0, "info": 1.0}


def calculate_finding_score(
    severity: str,
    confidence: str,
    fan_in: int = 0,
    churn_score: float = 0.0,
    is_untested: bool = False,
) -> float:
    """Calculate normalized risk score (0-100) for an LA Finding Record."""
    base = SEVERITY_WEIGHTS.get(severity.lower(), 5.0)
    conf_mult = 1.0 if confidence == "high" else (0.8 if confidence == "medium" else 0.5)
    blast_bonus = min(25.0, fan_in * 2.5)
    churn_bonus = min(25.0, churn_score * 3.0)
    untested_bonus = 15.0 if is_untested else 0.0

    raw = (base + blast_bonus + churn_bonus + untested_bonus) * conf_mult
    return round(min(100.0, max(1.0, raw)), 1)


def synthesize_la_findings(con: sqlite3.Connection, root: str) -> List[Dict[str, Any]]:
    """Synthesize findings across L0-L9 entities and store canonical Finding Records with Explainability Traces."""
    findings_out: List[Dict[str, Any]] = []

    # 1. Synthesize from L4 Wiring Gaps (Highest Priority Forensic Issue)
    gap_rows = con.execute("SELECT id, name, path, start_line, attributes_json FROM mdm_entities WHERE layer='L4' AND kind LIKE '%Gap%'").fetchall()
    for gr in gap_rows:
        attrs = json.loads(gr["attributes_json"] or "{}")
        fid = f"LA-GAP-{gr['name']}-{os.path.basename(gr['path'])}"
        title = f"Silent Wiring Gap: {attrs.get('type', 'UNRESOLVED')} '{gr['name']}'"
        detail = attrs.get("detail", f"Wiring disconnection detected in {gr['path']}")
        suggestion = "Wire up the frontend caller and backend handler with identical naming or remove orphaned registration."
        score = 85.0

        trace = [
            ("L0", f"file://{gr['path']}", f"File exists in topology: {gr['path']}"),
            ("L1", f"ast://{gr['path']}:{gr['start_line']}", f"Invocation site at line {gr['start_line']}"),
            ("L4", gr["id"], f"Cross-correlation failed: {detail}"),
            ("LA", fid, "Synthesized as High-Severity Silent Failure Risk (Wiring Gap)"),
        ]

        record_finding_with_trace(
            con,
            finding_id=fid,
            layer_origin="L4",
            rule_id="WIRING-GAP",
            severity="high",
            confidence="high",
            path=gr["path"],
            line=gr["start_line"],
            title=title,
            detail=detail,
            suggestion=suggestion,
            effort="small",
            score=score,
            trace_steps=trace,
        )
        findings_out.append({"finding_id": fid, "title": title, "severity": "high", "score": score, "path": gr["path"], "line": gr["start_line"]})

    # 2. Synthesize from L4 Silent Swallows
    swallow_rows = con.execute("SELECT id, path, start_line, attributes_json FROM mdm_entities WHERE layer='L4' AND kind='Silent Exception Swallow'").fetchall()
    for sw in swallow_rows:
        fid = f"LA-SWALLOW-{os.path.basename(sw['path'])}-{sw['start_line']}"
        title = f"Silent Exception Swallow in {sw['path']}:{sw['start_line']}"
        detail = "Broad except handler catches Exception/BaseException with pass/print only."
        suggestion = "Use log_swallowed('scope_name', err) or re-raise to avoid masked runtime failures."
        score = 80.0

        trace = [
            ("L0", f"file://{sw['path']}", f"File in codebase: {sw['path']}"),
            ("L1", f"ast://{sw['path']}:{sw['start_line']}", f"Try/Except AST block at line {sw['start_line']}"),
            ("L4", sw["id"], "AST inspection confirmed handler has no logging or control flow escape"),
            ("LA", fid, "Synthesized as Critical Reliability Hazard"),
        ]

        record_finding_with_trace(
            con,
            finding_id=fid,
            layer_origin="L4",
            rule_id="S1-SWALLOW",
            severity="critical",
            confidence="high",
            path=sw["path"],
            line=sw["start_line"],
            title=title,
            detail=detail,
            suggestion=suggestion,
            effort="trivial",
            score=score,
            trace_steps=trace,
        )
        findings_out.append({"finding_id": fid, "title": title, "severity": "critical", "score": score, "path": sw["path"], "line": sw["start_line"]})

    # 3. Synthesize from L7 Cross-Cutting Security
    sec_rows = con.execute("SELECT id, name, path, start_line, attributes_json FROM mdm_entities WHERE layer='L7'").fetchall()
    for sr in sec_rows:
        attrs = json.loads(sr["attributes_json"] or "{}")
        rule = attrs.get("rule", "SEC-UNKNOWN")
        sev = attrs.get("severity", "high")
        fid = f"LA-SEC-{rule}-{os.path.basename(sr['path'])}-{sr['start_line']}"
        title = sr["name"] or f"Security finding {rule}"
        detail = attrs.get("detail", "")
        suggestion = attrs.get("suggestion", "Review security posture immediately.")
        score = calculate_finding_score(sev, "high")

        trace = [
            ("L0", f"file://{sr['path']}", f"Source file: {sr['path']}"),
            ("L1", f"ast://{sr['path']}:{sr['start_line']}", f"Line {sr['start_line']} syntax scan"),
            ("L7", sr["id"], f"Rule '{rule}' pattern match: {detail}"),
            ("LA", fid, f"Synthesized as {sev.upper()} security risk"),
        ]

        record_finding_with_trace(
            con,
            finding_id=fid,
            layer_origin="L7",
            rule_id=rule,
            severity=sev,
            confidence="high",
            path=sr["path"],
            line=sr["start_line"],
            title=title,
            detail=detail,
            suggestion=suggestion,
            effort="small",
            score=score,
            trace_steps=trace,
        )
        findings_out.append({"finding_id": fid, "title": title, "severity": sev, "score": score, "path": sr["path"], "line": sr["start_line"]})

    # 4. Synthesize from L9 Churn × Complexity Hotspots
    hot_rows = con.execute("SELECT id, name, path, start_line, attributes_json FROM mdm_entities WHERE layer='L9' AND kind='Churn × Complexity Hotspot' LIMIT 15").fetchall()
    for hr in hot_rows:
        attrs = json.loads(hr["attributes_json"] or "{}")
        fid = f"LA-HOTSPOT-{hr['name']}-{os.path.basename(hr['path'])}"
        title = f"High Churn × Complexity Hotspot: '{hr['name']}'"
        risk = attrs.get("hotspot_risk", 20.0)
        churn = attrs.get("churn_score", 1.0)
        cplx = attrs.get("complexity_score", 10.0)
        detail = f"Top-decile mutation frequency (churn={churn}) compounded by structural complexity ({cplx})."
        suggestion = "Refactor into smaller, decoupled helper functions and verify test coverage."
        score = min(95.0, 50.0 + (risk * 1.5))

        trace = [
            ("L0", f"file://{hr['path']}", f"File: {hr['path']}"),
            ("L1", f"ast://{hr['path']}:{hr['start_line']}", f"Function '{hr['name']}' definition"),
            ("L6", f"complexity://{hr['name']}", f"Cognitive complexity metric: {cplx}"),
            ("L9", f"churn://{hr['path']}", f"Git commit churn score: {churn}"),
            ("LA", fid, f"Synthesized composite risk score: {risk}"),
        ]

        record_finding_with_trace(
            con,
            finding_id=fid,
            layer_origin="L9",
            rule_id="HOTSPOT-RISK",
            severity="high" if score >= 75.0 else "medium",
            confidence="high",
            path=hr["path"],
            line=hr["start_line"],
            title=title,
            detail=detail,
            suggestion=suggestion,
            effort="medium",
            score=score,
            trace_steps=trace,
        )
        findings_out.append({"finding_id": fid, "title": title, "severity": "high" if score >= 75.0 else "medium", "score": score, "path": hr["path"], "line": hr["start_line"]})

    # 5. Synthesize from L5 Layer Violations
    l5_rows = con.execute("SELECT id, name, path, attributes_json FROM mdm_entities WHERE layer='L5' AND kind='Boundary Violation'").fetchall()
    for l5 in l5_rows:
        attrs = json.loads(l5["attributes_json"] or "{}")
        fid = f"LA-ARCH-{l5['name'].replace(' ', '_').replace('->', '_to_')}"
        title = f"Architectural Inversion: {l5['name']}"
        detail = attrs.get("detail", "Lower layer depends on upper layer.")
        suggestion = "Invert dependency using interfaces, adapters, or callback injection."
        score = 65.0

        trace = [
            ("L0", f"file://{l5['path']}", f"Source file: {l5['path']}"),
            ("L2", f"import://{l5['name']}", "Import graph dependency edge"),
            ("L5", l5["id"], f"Layer direction check violation: {detail}"),
            ("LA", fid, "Synthesized as Architectural Boundary Violation"),
        ]

        record_finding_with_trace(
            con,
            finding_id=fid,
            layer_origin="L5",
            rule_id="ARCH-LAYER-VIOLATION",
            severity="medium",
            confidence="high",
            path=l5["path"],
            line=1,
            title=title,
            detail=detail,
            suggestion=suggestion,
            effort="medium",
            score=score,
            trace_steps=trace,
        )
        findings_out.append({"finding_id": fid, "title": title, "severity": "medium", "score": score, "path": l5["path"], "line": 1})

    con.commit()
    return findings_out


def compute_repo_scorecard(con: sqlite3.Connection) -> Dict[str, Any]:
    """Compute 5-dimensional scorecard and letter grades for the repository."""
    # Count findings by layer and severity
    crit = con.execute("SELECT COUNT(*) c FROM mdm_findings WHERE severity='critical'").fetchone()["c"]
    high = con.execute("SELECT COUNT(*) c FROM mdm_findings WHERE severity='high'").fetchone()["c"]
    med = con.execute("SELECT COUNT(*) c FROM mdm_findings WHERE severity='medium'").fetchone()["c"]

    # Dimension 1: Architecture & Boundaries
    arch_violations = con.execute("SELECT COUNT(*) c FROM mdm_findings WHERE layer_origin='L5'").fetchone()["c"]
    cycles = con.execute("SELECT COUNT(*) c FROM mdm_entities WHERE kind='Dependency Cycle'").fetchone()["c"]
    arch_score = max(20.0, 100.0 - (arch_violations * 12.0) - (cycles * 15.0))

    # Dimension 2: Security & Cross-Cutting
    sec_findings = con.execute("SELECT COUNT(*) c FROM mdm_findings WHERE layer_origin='L7'").fetchone()["c"]
    sec_score = max(10.0, 100.0 - (sec_findings * 25.0))

    # Dimension 3: Code Quality & Smells
    smells = con.execute("SELECT COUNT(*) c FROM mdm_entities WHERE layer='L6'").fetchone()["c"]
    quality_score = max(30.0, 100.0 - (smells * 2.0))

    # Dimension 4: Reliability & Flow
    wiring_gaps = con.execute("SELECT COUNT(*) c FROM mdm_findings WHERE rule_id='WIRING-GAP'").fetchone()["c"]
    swallows = con.execute("SELECT COUNT(*) c FROM mdm_findings WHERE rule_id='S1-SWALLOW'").fetchone()["c"]
    reliability_score = max(15.0, 100.0 - (wiring_gaps * 20.0) - (swallows * 25.0))

    # Dimension 5: Temporal & Hotspot Risk
    hotspots = con.execute("SELECT COUNT(*) c FROM mdm_entities WHERE layer='L9' AND kind='Churn × Complexity Hotspot'").fetchone()["c"]
    temporal_score = max(30.0, 100.0 - (hotspots * 5.0))

    overall = round(
        (arch_score * 0.20) + (sec_score * 0.25) + (quality_score * 0.20) + (reliability_score * 0.25) + (temporal_score * 0.10),
        1,
    )

    def grade(score: float) -> str:
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"

    return {
        "overall_score": overall,
        "overall_grade": grade(overall),
        "dimensions": {
            "reliability_and_flow": {"score": round(reliability_score, 1), "grade": grade(reliability_score)},
            "security_and_secrets": {"score": round(sec_score, 1), "grade": grade(sec_score)},
            "architecture_boundaries": {"score": round(arch_score, 1), "grade": grade(arch_score)},
            "code_quality_smells": {"score": round(quality_score, 1), "grade": grade(quality_score)},
            "evolution_and_churn": {"score": round(temporal_score, 1), "grade": grade(temporal_score)},
        },
        "counts": {
            "critical": crit,
            "high": high,
            "medium": med,
            "total_findings": crit + high + med,
        },
    }


def generate_full_mdm_report(root: Optional[str] = None) -> Dict[str, Any]:
    """Run extraction, perform LA synthesis, and compile complete Master Data Model Report."""
    root = root or repo_root()
    con = connect(root)

    # 1. Run L0-L9 extraction
    ext_res = run_mdm_extraction(root)

    # 2. Run LA synthesis
    la_findings = synthesize_la_findings(con, root)

    # 3. Scorecard
    scorecard = compute_repo_scorecard(con)

    # 4. Top prioritized findings with traces
    top_findings = query_findings(con, limit=20)
    enriched_findings: List[Dict[str, Any]] = []
    for tf in top_findings:
        tf_dict = dict(tf)
        tf_dict["trace"] = get_explainability_trace(con, tf["finding_id"])
        enriched_findings.append(tf_dict)

    # 5. Wiring gaps section
    wiring_gaps = [
        f for f in enriched_findings if f.get("rule_id") == "WIRING-GAP" or f.get("layer_origin") == "L4"
    ]

    return {
        "scorecard": scorecard,
        "extraction_summary": ext_res,
        "total_la_findings": len(la_findings),
        "prioritized_findings": enriched_findings,
        "wiring_gaps": wiring_gaps,
    }


def format_report_markdown(report: Dict[str, Any]) -> str:
    """Format the full MDM report into clean GitHub Flavored Markdown."""
    sc = report.get("scorecard", {})
    dims = sc.get("dimensions", {})
    counts = sc.get("counts", {})

    lines: List[str] = [
        "# 📊 CIP Repository Forensic Intelligence & Master Data Report (L0–LA)",
        "",
        f"**Overall Health Grade:** `{sc.get('overall_grade', 'B')}` ({sc.get('overall_score', 0)}/100)  ",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
        "",
        "---",
        "",
        "## 1. 5-Dimensional Health Scorecard",
        "",
        "| Dimension | Score | Grade | Status |",
        "| :--- | :--- | :--- | :--- |",
        f"| **1. Reliability & Flow (L4)** | {dims.get('reliability_and_flow', {}).get('score', 0)}% | `{dims.get('reliability_and_flow', {}).get('grade', 'C')}` | {'⚠️ Needs Attention' if dims.get('reliability_and_flow', {}).get('score', 0) < 75 else '✅ Healthy'} |",
        f"| **2. Security & Secrets (L7)** | {dims.get('security_and_secrets', {}).get('score', 0)}% | `{dims.get('security_and_secrets', {}).get('grade', 'A')}` | {'⚠️ Needs Attention' if dims.get('security_and_secrets', {}).get('score', 0) < 75 else '✅ Healthy'} |",
        f"| **3. Architecture & Boundaries (L5)** | {dims.get('architecture_boundaries', {}).get('score', 0)}% | `{dims.get('architecture_boundaries', {}).get('grade', 'B')}` | {'⚠️ Needs Attention' if dims.get('architecture_boundaries', {}).get('score', 0) < 75 else '✅ Healthy'} |",
        f"| **4. Code Quality & Smells (L6)** | {dims.get('code_quality_smells', {}).get('score', 0)}% | `{dims.get('code_quality_smells', {}).get('grade', 'B')}` | {'⚠️ Needs Attention' if dims.get('code_quality_smells', {}).get('score', 0) < 75 else '✅ Healthy'} |",
        f"| **5. Evolution & Churn Risk (L9)** | {dims.get('evolution_and_churn', {}).get('score', 0)}% | `{dims.get('evolution_and_churn', {}).get('grade', 'A')}` | {'⚠️ Needs Attention' if dims.get('evolution_and_churn', {}).get('score', 0) < 75 else '✅ Healthy'} |",
        "",
        f"**Active Finding Inventory:** 🔴 Critical: `{counts.get('critical', 0)}` · 🟠 High: `{counts.get('high', 0)}` · 🟡 Medium: `{counts.get('medium', 0)}`",
        "",
        "---",
        "",
        "## 2. 🗺️ Critical Wiring Gaps & Silent Runtime Traps (L4)",
        "",
    ]

    wg = report.get("wiring_gaps", [])
    if not wg:
        lines.append("✅ No silent wiring gaps or disconnected IPC/events detected.")
    else:
        for idx, g in enumerate(wg, 1):
            lines.extend([
                f"### #{idx} [{g.get('severity', 'HIGH').upper()}] {g.get('title', '')}",
                f"- **Location:** `{g.get('path', '')}:{g.get('line', 0)}`",
                f"- **Detail:** {g.get('detail', '')}",
                f"- **Actionable Suggestion:** {g.get('suggestion', '')}",
                "",
            ])

    lines.extend([
        "---",
        "",
        "## 3. 🎯 Prioritized Finding Records with Explainability Traces (LA)",
        "",
    ])

    for idx, f in enumerate(report.get("prioritized_findings", [])[:15], 1):
        lines.extend([
            f"### #{idx} [{f.get('severity', 'MEDIUM').upper()}] {f.get('title', '')} (Risk Score: {f.get('score', 0)})",
            f"- **Rule / Layer:** `{f.get('rule_id', '')}` (`{f.get('layer_origin', 'LA')}`)",
            f"- **Location:** `{f.get('path', '')}:{f.get('line', 0)}`",
            f"- **Detail:** {f.get('detail', '')}",
            f"- **Suggested Remediation:** {f.get('suggestion', '')}",
            "",
            "**🔍 Explainability Trace:**",
        ])
        for step in f.get("trace", []):
            lines.append(f"1. **[{step.get('layer', '')}]** {step.get('evidence_description', '')}")
        lines.append("")

    return "\n".join(lines)
