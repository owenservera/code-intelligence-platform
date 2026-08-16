"""S5 regression test: `cip doctor` first-class skeleton (doctor.py).

RUNBOOK §4 / TRACKER Phase S row S5 / DESIGN §6.5 — the S1 swallow-scanner +
S2 pyflakes gate are promoted as `cip doctor --static` steps; the CONFIG-*
skeleton is the Phase-2 host. Regression-locks:

* RECALL  — `doctor.static_checks` fires on a broken swallow fixture and the
  `doctor.config_checks` skeleton fires on the repo's still-broken config
  (CORE-10/39/40/42/2, F-11 evidence).
* PRECISION — `doctor.static_checks` is silent on `tests/data/clean_ref/` and
  `doctor.config_checks` is silent on a fully-reconciled virtual config.
* The S1 evidence sites stay clean (S1 flip preserved through the promotion).
* The runtime scope only reports measured state — never fake success.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "tests" / "detectors"))

from cipkg import doctor  # noqa: E402

AUDIT = ROOT / "lib" / "cipkg" / "stack" / "audit.py"
BASE = ROOT / "lib" / "cipkg" / "base.py"
SUGGESTION_ENGINE = ROOT / "lib" / "cipkg" / "suggestion_engine.py"
CLEAN_REF = ROOT / "tests" / "data" / "clean_ref"

BROKEN_FIXTURE = """\
import time

def run():
    try:
        time.sleep(1)
    except Exception:
        pass
"""


def test_s5_static_swallow_fires_on_broken_scope():
    """RECALL: `doctor.static_checks` (--static) surfaces S1 swallows."""
    with tempfile.TemporaryDirectory() as tmp:
        (pathlib.Path(tmp) / "broken.py").write_text(BROKEN_FIXTURE, encoding="utf-8")
        findings = [
            f for f in doctor.static_checks(tmp)
            if f["rule"] == "CODE-SILENT-SWALLOW"
        ]
    assert findings, "doctor --static FAILED to fire on broken swallow fixture"
    assert all(f["rule"] == "CODE-SILENT-SWALLOW" and f["evidence"] for f in findings)


def test_s5_static_precision_clean_ref():
    """PRECISION: `doctor.static_checks` is silent on the clean reference."""
    findings = doctor.static_checks(str(CLEAN_REF))
    swallows = [f for f in findings if f["rule"] == "CODE-SILENT-SWALLOW"]
    assert swallows == [], f"doctor --static FPs on clean_ref: {swallows}"


def test_s5_static_s1_evidence_sites_clean_after_promotion():
    """S1 flip preserved: the retired evidence sites are clean via doctor."""
    sites = doctor.scan_path(str(AUDIT)) + doctor.scan_path(str(BASE)) + doctor.scan_path(str(SUGGESTION_ENGINE))
    lines = {(f["file"], f["line"]) for f in sites}
    for rel, line in [
        ("stack/audit.py", 19), ("stack/audit.py", 21),
        ("base.py", 144), ("suggestion_engine.py", 657),
    ]:
        flagged = [p for (p, ln) in lines if ln == line and rel in p]
        assert not flagged, f"S1 evidence site {rel}:{line} regressed: {flagged}"


def test_s5_config_recall_on_broken_repo():
    """RECALL: the CONFIG-* skeleton fires on the repo's current broken config."""
    findings = doctor.config_checks(str(ROOT))
    rules = {f["rule"] for f in findings}
    # F-42/CORE-39 note: exclude_patterns+max_file_size are the ignored TOML keys.
    expected = {
        "CONFIG-FILE-UNPARSEABLE",       # config.default.toml health_weights = { multi-line

        "CONFIG-PORT-MISMATCH",      # CORE-10 8765 vs 8787

        "CONFIG-SCHEMA-DRIFT",       # CORE-40/BUG-023 11 vs 4

        "CONFIG-KEY-DRIFT",          # CORE-39

        "CONFIG-KEY-UNUSED",         # CORE-42 [performance]

        "CONFIG-MISSING-SECTION",    # CORE-2 [web]

        "CONFIG-PROFILE-SILENT-FAIL",  # F-11

    }
    assert expected <= rules, f"doctor --config missed evidence. got={sorted(rules)}"


def test_s5_config_precision_clean_virtual_config():
    """PRECISION: a fully-reconciled config yields zero findings."""
    reconciled = {
        "meta": {"schema_version": 4},
        "index": {"exclude": ["node_modules"], "max_file_kb": 512},
        "daemon": {"port": 8787},
        "web": {"host": "localhost", "port": 8090},
        "perf": {"workers": 0},
    }
    # cfg passed explicitly so no repo I/O is needed; profile check skips the
    # F-11 probe because the (temp) root has no repo-settings directory.
    with tempfile.TemporaryDirectory() as tmp:
        findings = doctor.config_checks(tmp, cfg=reconciled)
    assert findings == [], f"doctor --config FPs on reconciled config: {findings}"


def test_s5_runtime_only_reports_measured_state():
    """RUNTIME: probes never fabricate success (no fake no-op 'ok')."""
    with tempfile.TemporaryDirectory() as tmp:
        findings = doctor.runtime_checks(tmp)
    assert isinstance(findings, list)
    for f in findings:
        assert f["rule"].startswith("RUNTIME-")
        assert f["evidence"], "runtime probe finding must carry evidence"
        assert f["title"] != "ok" and f["recommendation"]


def test_s5_cli_parser_exposes_three_scopes():
    """The `doctor` subparser exposes --static/--config/--runtime."""
    from cipkg import cli
    p = cli.setup_argument_parser()
    for flag in ("--static", "--config", "--runtime"):
        assert p.parse_args(["doctor", flag]), flag