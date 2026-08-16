"""cip doctor - first-class self-diagnostic surface (campaign Phase S, S5).

DESIGN §1/S5 + DESIGN §5 machinery budget: S/CONFIG = rules 0 · doctor steps 3.
The three scopes:
  --static   CODE-* static scans. S1 no-bare-except swallow scanner (promoted
             from tests/detectors/s1_swallow_scanner.py — the regression-locked
             instrument stays importable via that shim) + S2 pyflakes lint gate.
  --config   CONFIG-* self-consistency skeleton (checks land in Phase 2; the
             loader-driven S4 suite deepens these).
  --runtime  runtime / API-contract probes (S3 conformance suite + Phase 5
             behavioral probes extend this scope).

Every check emits the DESIGN §4 CheckFinding shape:
    {rule, finding_ref, severity, title, evidence, recommendation}
A clean scan has zero findings. No embeddings anywhere.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# S1 — no-bare-except swallow scanner (promoted to a product static step)
# ---------------------------------------------------------------------------

BROAD_NAMES = {"Exception", "BaseException"}
LOG_CALLS = {
    "log_swallowed", "log", "logger", "exception", "error", "warning",
    "info", "critical", "debug",
}


def _is_broad(handler: ast.ExceptHandler) -> bool:
    """True if the handler catches a broad/unspecified exception type."""
    if handler.type is None:
        return True
    names: set[str] = set()
    for node in ast.walk(handler.type):
        if isinstance(node, ast.Name):
            names.add(node.id)
    if not names:
        return True
    return bool(names & BROAD_NAMES)


def _is_silent(handler: ast.ExceptHandler) -> bool:
    """True if the handler's body does nothing observable (pass/print only)."""
    for stmt in handler.body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, (ast.Return, ast.Raise, ast.Yield, ast.YieldFrom, ast.Break, ast.Continue)):
            return False  # surfaces control flow
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            func = stmt.value.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in LOG_CALLS:
                return False  # logs -> surfaces
            continue  # bare call or print -> still silent
        return False  # any other statement (assign/with/... -> conservatively surfacing)
    return True


def scan_path(path: Path | str) -> list[dict[str, Any]]:
    """Return swallow findings for a .py file or directory (recursive)."""
    path = Path(path)
    targets = sorted(path.rglob("*.py")) if path.is_dir() else [path]
    findings: list[dict[str, Any]] = []
    for py_file in targets:
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            for handler in node.handlers:
                if _is_broad(handler) and _is_silent(handler):
                    findings.append({
                        "file": str(py_file).replace("\\", "/"),
                        "line": handler.lineno,
                        "kind": "bare" if handler.type is None else "broad",
                        "except_source": ast.get_source_segment(source, handler),
                    })
    return findings


def scan_text(source: str, filename: str = "inline.py") -> list[dict[str, Any]]:
    """Scan a source string; used by the regression tests and precision fixtures."""
    tree = ast.parse(source)
    findings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            if _is_broad(handler) and _is_silent(handler):
                findings.append({
                    "file": filename,
                    "line": handler.lineno,
                    "kind": "bare" if handler.type is None else "broad",
                })
    return findings


# ---------------------------------------------------------------------------
# S2 — pyflakes lint gate (hosted as a doctor --static step)
# ---------------------------------------------------------------------------

def _pyflakes(targets: list[str]) -> str:
    """Run the configured lint instrument and return its stdout."""
    result = subprocess.run(
        [sys.executable, "-m", "pyflakes", *targets],
        capture_output=True,
        text=True,
    )
    return result.stdout


def _parse_pyflakes(out: str) -> list[dict[str, Any]]:
    """Map pyflakes F401/F821 lines to CheckFinding shape."""
    # e.g. "path\\file.py:12: import 'os' unused" / "path\\file.py:7: undefined name 'json'"
    findings: list[dict[str, Any]] = []
    pat = re.compile(r"^(.+?):(\d+):\s*(.+)$")
    for line in out.splitlines():
        m = pat.match(line.strip())
        if not m:
            continue
        msg = m.group(3)
        if "undefined name" in msg:
            rule, title = "CODE-UNDEFINED-NAME", msg
            missing = msg.replace("undefined name", "").strip().strip("'")
            rec = f"add the missing import/definition for {missing!r}"
        elif "imported but unused" in msg or "unused import" in msg:
            rule, title = "CODE-UNUSED-IMPORT", msg
            rec = "remove the unused import"
        else:
            rule, title = "CODE-STATIC-LINT", msg
            rec = "fix the flagged line"
        findings.append({
            "rule": rule,
            "finding_ref": "F-09/BUG-005" if rule == "CODE-UNDEFINED-NAME" else "F-09",
            "severity": "P1" if rule == "CODE-UNDEFINED-NAME" else "P3",
            "title": title,
            "evidence": f"{m.group(1)}:{m.group(2)}",
            "recommendation": rec,
        })
    return findings


def _lint_available() -> bool:
    try:
        import pyflakes  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# CONFIG — self-consistency skeleton (Phase 2 extends)
# ---------------------------------------------------------------------------

def _load_repo_toml(root: str) -> tuple[dict[str, Any], str | None]:
    """Read the repo's default config; return (cfg, toml_error|None).

    The shipped `config.default.toml` may itself be invalid TOML (true for this
    repo — the `[analysis] health_weights` inline table spans lines, which
    tomllib rejects). When that happens we fall back to `base._parse_toml_naive`
    so the scalar key-level checks (CORE-10/39/40/42) still see the text-level
    evidence, and we surface the parse error via CONFIG-FILE-UNPARSEABLE.
    """
    import tomllib
    cfg: dict[str, Any] = {}
    toml_error: str | None = None
    for name in ("config.default.toml", "config.v2.default.toml", ".cip/config.toml"):
        path = os.path.join(root, name)
        if not os.path.exists(path):
            continue
        try:
            with open(path, "rb") as f:
                return dict(tomllib.load(f)), None
        except tomllib.TOMLDecodeError as e:
            if name == "config.default.toml":
                # The shipped defaults are the truth we check; when they cannot
                # be loaded that IS the top finding, so surface it and return
                # rather than falling through to a stale secondary default.
                try:
                    from .base import _parse_toml_naive
                    cfg = _parse_toml_naive(path)
                except Exception:
                    cfg = {}
                return cfg, f"{name}: {e}"
            continue
        except OSError:
            continue
    return cfg, toml_error


def _code_port_defaults(root: str) -> set[int]:
    """Collect the port literals the code actually serves/registers.

    Reads the live source so the check ages correctly with the Phase-2 fix.
    """
    ports: set[int] = set()
    for rel in ("lib/cipkg/daemon.py", "lib/cipkg/command_registry.py"):
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            continue
        try:
            src = Path(p).read_text(encoding="utf-8")
        except OSError:
            continue
        for m in re.finditer(r"default\s*[:=]\s*[\"']?(\d{3,5})", src):
            ports.add(int(m.group(1)))
        for m in re.finditer(r"port or (\d{3,5})", src):
            ports.add(int(m.group(1)))
    return ports


def config_checks(root: str, cfg: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """CONFIG-* self-consistency skeleton (CORE-2/10/39/40/42, F-11/CORE-41).

    Accepts a preloaded cfg (tests inject it) or loads the repo's defaults.
    When `config.default.toml` is itself invalid TOML the loader falls back to
    `base._parse_toml_naive` (text-level sections) and reports the parse error
    first — the worst config bug is a config the loader cannot read at all.
    """
    findings: list[dict[str, Any]] = []
    toml_error: str | None = None
    if cfg is None:
        cfg, toml_error = _load_repo_toml(root)

    # CONFIG-FILE-UNPARSEABLE — the shipped defaults never load.
    if toml_error:
        findings.append({
            "rule": "CONFIG-FILE-UNPARSEABLE",
            "finding_ref": "CORE-39",
            "severity": "P1",
            "title": "config.default.toml is invalid TOML and cannot be loaded",
            "evidence": toml_error,
            "recommendation": "make config.default.toml parse (single-line inline tables) so defaults actually apply",
        })

    # CORE-10 / CONFIG-PORT-MISMATCH — config [daemon] port vs code defaults (8787).
    code_ports = _code_port_defaults(root)
    toml_port = (cfg.get("daemon") or {}).get("port")
    if toml_port and code_ports and int(toml_port) not in code_ports:
        findings.append({
            "rule": "CONFIG-PORT-MISMATCH",
            "finding_ref": "CORE-10",
            "severity": "P2",
            "title": "daemon port disagrees with code default",
            "evidence": f"config.default.toml [daemon].port={toml_port}; code defaults {sorted(code_ports)}",
            "recommendation": "pick one port truth across config + daemon.py + command_registry",
        })

    # CORE-40 / BUG-023 / CONFIG-SCHEMA-DRIFT — declared schema vs store/DB.
    from . import store as _store
    toml_schema = (cfg.get("meta") or {}).get("schema_version")
    if toml_schema is not None and int(toml_schema) != _store.SCHEMA_VERSION:
        findings.append({
            "rule": "CONFIG-SCHEMA-DRIFT",
            "finding_ref": "CORE-40",
            "severity": "P1",
            "title": "declared schema_version differs from store",
            "evidence": (
                f"config.default.toml [meta].schema_version={toml_schema} "
                f"vs store.SCHEMA_VERSION={_store.SCHEMA_VERSION}"
            ),
            "recommendation": "set config schema_version to the live value or migrate",
        })

    # CORE-39 / CONFIG-KEY-DRIFT — TOML keys the core never reads.
    index_keys = cfg.get("index") or {}
    for toml_key, code_key in (("exclude_patterns", "exclude"), ("max_file_size", "max_file_kb")):
        if toml_key in index_keys:
            findings.append({
                "rule": "CONFIG-KEY-DRIFT",
                "finding_ref": "CORE-39",
                "severity": "P1",
                "title": f"index.{toml_key} is ignored; core reads index.{code_key}",
                "evidence": f"config.default.toml [index].{toml_key}; base.py/indexer.py read {code_key}",
                "recommendation": "rename/map the key so excludes + size caps actually apply",
            })

    # CORE-42 / CONFIG-KEY-UNUSED — duplicate perf section ([performance] vs [perf]).
    if cfg.get("performance"):
        findings.append({
            "rule": "CONFIG-KEY-UNUSED",
            "finding_ref": "CORE-42",
            "severity": "P3",
            "title": "[performance] declared but core reads [perf]",
            "evidence": "config.default.toml [performance] vs indexer.py cfg['perf']['workers']",
            "recommendation": "collapse to one section; mark legacy keys deprecated",
        })

    # CORE-2 / CONFIG-MISSING-SECTION — no [web] anchor for the console.
    if "web" not in cfg:
        findings.append({
            "rule": "CONFIG-MISSING-SECTION",
            "finding_ref": "CORE-2",
            "severity": "P3",
            "title": "no [web] config section anchors the console port",
            "evidence": "config.default.toml (fr: FR-1/NFR-1 web port 8090 has no anchor)",
            "recommendation": "add [web] host/port/auto_manage_daemon to defaults",
        })

    # F-11 / CORE-41 / CONFIG-PROFILE-SILENT-FAIL — repo-settings resolution broken.
    root_settings = os.path.join(root, "repo-settings", "detectors.py")
    lib_settings = os.path.join(root, "lib", "repo-settings")
    if os.path.exists(root_settings) and not os.path.exists(lib_settings):
        found_profile = False
        try:
            from .base import load_config as _lc
            found_profile = bool((_lc(root) or {}).get("profile"))
        except Exception:
            found_profile = False
        if not found_profile:
            findings.append({
                "rule": "CONFIG-PROFILE-SILENT-FAIL",
                "finding_ref": "F-11",
                "severity": "P1",
                "title": "repo-settings profiles never load",
                "evidence": (
                    f"repo-settings/detectors.py exists at root but load_config looks at "
                    f"lib/repo-settings (missing); profile={{}}"
                ),
                "recommendation": "resolve repo-settings from repo root and align all 3 import sites",
            })

    return findings


# ---------------------------------------------------------------------------
# RUNTIME — probes skeleton (S3 conformance + Phase 5 extend this scope)
# ---------------------------------------------------------------------------

def runtime_checks(root: str) -> list[dict[str, Any]]:
    """Runtime probes that only claim what they measured (no fake success)."""
    findings: list[dict[str, Any]] = []

    # daemon health — live probe, never invented.
    try:
        from .daemon import daemon_status
        ds = daemon_status(root)
        if not ds.get("alive"):
            findings.append({
                "rule": "RUNTIME-DAEMON-DOWN",
                "finding_ref": "CORE-12",
                "severity": "P3",
                "title": "embed daemon is not running",
                "evidence": "daemon_status: pid=None, alive=False",
                "recommendation": "start `cip daemon start` or rely on auto-start (embed may be slow)",
            })
    except Exception as e:
        findings.append({
            "rule": "RUNTIME-PROBE-FAILED",
            "finding_ref": "S5",
            "severity": "P3",
            "title": "daemon probe could not run",
            "evidence": f"daemon_status raised {type(e).__name__}",
            "recommendation": "inspect failure surfaced above (never swallow silently)",
        })

    # live DB schema vs store constant — the CORE-40/23 live half.
    try:
        from .store import connect, get_meta
        con = None
        try:
            con = connect(root)
            live = get_meta(con, "schema_version")
        finally:
            if con is not None:
                try:
                    con.close()
                except Exception:
                    pass
        if live is not None and int(live) != 4:
            findings.append({
                "rule": "RUNTIME-SCHEMA-DRIFT",
                "finding_ref": "CORE-40",
                "severity": "P1",
                "title": "live DB schema differs from store.SCHEMA_VERSION",
                "evidence": f"live DB meta schema_version={live}, store.SCHEMA_VERSION=4",
                "recommendation": "migrate or pin schema_version to the live value",
            })
    except Exception as e:
        findings.append({
            "rule": "RUNTIME-PROBE-FAILED",
            "finding_ref": "S5",
            "severity": "P3",
            "title": "DB probe could not run",
            "evidence": f"connect/get_meta raised {type(e).__name__}",
            "recommendation": "surface the failure (root may not be indexed yet)",
        })

    return findings


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def static_checks(root: str) -> list[dict[str, Any]]:
    """CODE-* static scans: S1 swallow scanner + S2 pyflakes gate."""
    findings: list[dict[str, Any]] = []

    # S1 — swallow scanner over repo Python sources (dogfoods lib/cipkg).
    swallow = scan_path(root)
    for f in swallow:
        findings.append({
            "rule": "CODE-SILENT-SWALLOW",
            "finding_ref": "F-24",
            "severity": "P2",
            "title": f"broad {f['kind']} except with no surfacing",
            "evidence": f"{f['file']}:{f['line']}",
            "recommendation": "log_swallowed(where, exc) or surface (return/raise/log)",
        })

    # S2 — pyflakes gate (P3/F-09; undefined-name = P1/BUG-005). Optional when
    # the instrument is not installed (the CI gate enforces it separately).
    if _lint_available():
        findings.extend(_parse_pyflakes(_pyflakes([root])))
    return findings


def doctor(root: str, scope: str | None = None) -> dict[str, Any]:
    """Run doctor checks. scope in {static, config, runtime, None(all)}.

    Returns the DESIGN §4 contract: {ok, findings, scopes}. `ok=True` means
    zero findings across the requested scopes. Renders nothing itself — the
    CLI layers the terminal/JSON output on top.
    """
    scopes = {"static", "config", "runtime"}
    want = scopes if not scope else {scope}
    results: dict[str, list[dict[str, Any]]] = {}
    total = 0
    if "static" in want:
        results["static"] = static_checks(root)
        total += len(results["static"])
    if "config" in want:
        results["config"] = config_checks(root)
        total += len(results["config"])
    if "runtime" in want:
        results["runtime"] = runtime_checks(root)
        total += len(results["runtime"])
    return {"ok": total == 0, "scopes": sorted(want), "findings": results, "total": total}