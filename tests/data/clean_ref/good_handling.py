"""Good-handling fixture for the S1 swallow-discipline precision probe.

Every handler here is *legitimate*: either narrowly typed, or it surfaces
control flow (return/raise), or it logs the exception. The S1 swallow-scanner
MUST report zero findings for this file — any finding here is a false positive
in the S1 gate (RUNBOOK §4.3, LEDGER §3).
"""

from __future__ import annotations

from typing import Any


def log_swallowed(where: str, exc: Exception) -> None:
    """Stand-in for lib/cipkg/base.log_swallowed used by the fixture."""
    print(f"{where}: {exc}")


def parse_intish(value: str) -> int:
    """Narrow exception type: not broad, never flagged."""
    try:
        return int(value)
    except ValueError:
        return 0


def lookup(key: str, table: dict[str, int]) -> int | None:
    """Broad catch but surfaces control flow by returning None."""
    try:
        return table[key]
    except Exception:
        return None


def read_lenient(path: str) -> str:
    """Broad catch but logs via the codebase's log_swallowed convention."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except Exception as exc:
        log_swallowed("fixture.read_lenient", exc)
        return ""


def split_strict(row: str) -> list[Any]:
    """Multi-type catch that re-raises: surfaces, never flagged."""
    try:
        return list(row.split(","))
    except (ValueError, TypeError) as exc:
        raise RuntimeError("bad row") from exc