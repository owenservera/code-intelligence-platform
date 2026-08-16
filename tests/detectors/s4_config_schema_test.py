"""S4 regression test: config-schema loader suite (doctor.config_checks).

RUNBOOK §4 / TRACKER Phase S row S4 / DESIGN §6.4. Deepens the S5 CONFIG-*
skeleton into a loader-driven suite and regression-locks:

* RECALL  — every one of the 7 CONFIG-* rules fires on the repo's deliberately
  broken config, with the DESIGN-contract finding_ref and non-empty evidence.
* INVARIANT — `config.default.toml` is itself invalid TOML to tomllib (line 151
  `[analysis] health_weights = {` multi-line inline table); this is the root
  finding and this assertion FLIPS to clean after the Phase-2 fix.
* LOADER  — `doctor._load_repo_toml` returns `(cfg, toml_error)` and on a
  decode error on the shipped default it returns IMMEDIATELY (never falls
  through to `config.v2.default.toml`); a valid file → `(cfg, None)`.
* PRECISION — per-rule surgical: a config missing only `[web]` fires only
  CONFIG-MISSING-SECTION; `[performance]` fires only CONFIG-KEY-UNUSED;
  `index.exclude_patterns` fires only CONFIG-KEY-DRIFT; daemon port that
  matches the code `default:` literal stays silent; `schema_version` equal to
  `store.SCHEMA_VERSION` stays silent.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile
import tomllib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib"))

from cipkg import doctor  # noqa: E402
from cipkg import store  # noqa: E402

CONFIG_REFS = {
    "CONFIG-FILE-UNPARSEABLE": "CORE-39",
    "CONFIG-PORT-MISMATCH": "CORE-10",
    "CONFIG-SCHEMA-DRIFT": "CORE-40",
    "CONFIG-KEY-DRIFT": "CORE-39",
    "CONFIG-KEY-UNUSED": "CORE-42",
    "CONFIG-MISSING-SECTION": "CORE-2",
    "CONFIG-PROFILE-SILENT-FAIL": "F-11",
}


def repo_rules_and_refs() -> dict[str, str]:
    findings = doctor.config_checks(str(ROOT))
    return {f["rule"]: f["finding_ref"] for f in findings}


def repo_findings(rule: str) -> list[dict]:
    return [f for f in doctor.config_checks(str(ROOT)) if f["rule"] == rule]


# ---------------------------------------------------------------------------
# RECALL — all seven CONFIG-* rules fire with contract refs + evidence
# ---------------------------------------------------------------------------

def test_s4_recall_all_seven_rules_fire():
    rules = set(repo_rules_and_refs())
    assert CONFIG_REFS.keys() <= rules, f"missing rules: {set(CONFIG_REFS) - rules}"


def test_s4_recall_finding_refs_and_evidence():
    by_rule = {f["rule"]: f for f in doctor.config_checks(str(ROOT))}
    for rule, ref in CONFIG_REFS.items():
        assert rule in by_rule, rule
        f = by_rule[rule]
        assert f["finding_ref"] == ref, (rule, f["finding_ref"])
        assert f["evidence"], rule
        assert f["severity"], rule


def test_s4_recall_file_unparseable_evidence():
    """CONFIG-FILE-UNPARSEABLE names the shipped file + the decode error."""
    f = repo_findings("CONFIG-FILE-UNPARSEABLE")
    assert len(f) == 1
    assert "config.default.toml" in f[0]["evidence"]
    assert "TOMLDecodeError" in f[0]["evidence"] or "invalid" in f[0]["evidence"].lower()


@pytest.mark.skipif(
    not (ROOT / "config.default.toml").exists(),
    reason="repo default absent in this checkout",
)
def test_s4_default_file_is_invalid_toml_flips_when_fixed():
    """INVARIANT: the shipped default fails tomllib. FLIPS clean in Phase 2."""
    data = (ROOT / "config.default.toml").read_bytes()
    with pytest.raises(tomllib.TOMLDecodeError):
        tomllib.loads(data.decode("utf-8"))


# ---------------------------------------------------------------------------
# LOADER — _load_repo_toml contract: (cfg, toml_error), no v2 fall-through
# ---------------------------------------------------------------------------

def test_s4_loader_repo_default_returns_error_and_cfg():
    cfg, err = doctor._load_repo_toml(str(ROOT))
    assert err is not None
    assert "config.default.toml" in err
    assert isinstance(cfg, dict)


def test_s4_loader_does_not_fall_through_to_v2_on_decode_error():
    """A %-root invalid default must NOT silently become the v2 defaults."""
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp)
        (p / "config.default.toml").write_text(
            "[analysis]\nhealth_weights = {\n",  # truncated → invalid TOML
            encoding="utf-8",
        )
        (p / "config.v2.default.toml").write_text(
            "[meta]\nschema_version = 4\n",
            encoding="utf-8",
        )
        cfg, err = doctor._load_repo_toml(tmp)
    assert err is not None and "config.default.toml" in err
    assert (cfg or {}).get("meta") != {"schema_version": 4}  # NOT the v2 load


def test_s4_loader_valid_file_returns_cfg_none():
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp)
        (p / "config.default.toml").write_text(
            "[web]\nhost = 'localhost'\nport = 8090\n",
            encoding="utf-8",
        )
        cfg, err = doctor._load_repo_toml(tmp)
    assert err is None
    assert cfg["web"]["port"] == 8090


def test_s4_loader_no_files_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        cfg, err = doctor._load_repo_toml(tmp)
    assert cfg == {} and err is None


# ---------------------------------------------------------------------------
# PRECISION — per-rule surgical (a config missing exactly one anatomy
#             fires ONLY the corresponding rule; no cross-talk)
# ---------------------------------------------------------------------------

def _no_codesite(tmp: str) -> dict:
    """config_checks with no file I/O: code-scan sides absent, profile skipped."""
    return doctor.config_checks(tmp, cfg=None)


def test_s4_precision_missing_web_fires_only_missing_section():
    with tempfile.TemporaryDirectory() as tmp:
        findings = doctor.config_checks(tmp, cfg={"meta": {"schema_version": 4}})
    rules = {f["rule"] for f in findings}
    assert rules == {"CONFIG-MISSING-SECTION"}, rules


def test_s4_precision_performance_fires_only_key_unused():
    with tempfile.TemporaryDirectory() as tmp:
        findings = doctor.config_checks(
            tmp, cfg={"performance": {"workers": 0}, "web": {"port": 8090}}
        )
    rules = {f["rule"] for f in findings}
    assert rules == {"CONFIG-KEY-UNUSED"}, rules


def test_s4_precision_exclude_patterns_fires_only_key_drift():
    with tempfile.TemporaryDirectory() as tmp:
        findings = doctor.config_checks(
            tmp, cfg={"index": {"exclude_patterns": ["b"]}, "web": {"port": 8090}}
        )
    rules = {f["rule"] for f in findings}
    assert rules == {"CONFIG-KEY-DRIFT"}, rules
    assert len(findings) == 1  # only the exclude_patterns pair, not max_file_size


def test_s4_precision_schema_matches_store_is_silent():
    with tempfile.TemporaryDirectory() as tmp:
        findings = doctor.config_checks(tmp, cfg={"meta": {"schema_version": store.SCHEMA_VERSION}})
    assert findings, "expect [] when declared schema matches store"
    assert all(f["rule"] != "CONFIG-SCHEMA-DRIFT" for f in findings)


def test_s4_recall_schema_drift_fires_on_wrong_version():
    with tempfile.TemporaryDirectory() as tmp:
        findings = doctor.config_checks(tmp, cfg={"meta": {"schema_version": 11}})
    assert any(f["rule"] == "CONFIG-SCHEMA-DRIFT" for f in findings)


def _code_ports(tmp: str, port_literal: int) -> str:
    """Materialize a minimal lib/cipkg/daemon.py so the code-scan sees a port."""
    p = pathlib.Path(tmp) / "lib" / "cipkg"
    p.mkdir(parents=True)
    (p / "daemon.py").write_text(
        f"PORT_OPTIONS = {{'default': {port_literal}}}\n"
        f"parser_kwargs = dict(default={port_literal})\n",
        encoding="utf-8",
    )


def test_s4_precision_port_matching_code_is_silent():
    with tempfile.TemporaryDirectory() as tmp:
        _code_ports(tmp, 8787)
        findings = doctor.config_checks(tmp, cfg={"daemon": {"port": 8787}})
    assert all(f["rule"] != "CONFIG-PORT-MISMATCH" for f in findings)


def test_s4_recall_port_mismatch_code_fires():
    with tempfile.TemporaryDirectory() as tmp:
        _code_ports(tmp, 8787)
        findings = doctor.config_checks(tmp, cfg={"daemon": {"port": 8765}})
    assert any(f["rule"] == "CONFIG-PORT-MISMATCH" for f in findings)