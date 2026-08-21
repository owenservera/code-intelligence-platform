"""Clean reference module for the S2 static-lint gate precision probe.

Every import is used, every name is defined before use, and the module parses
clean. pyflakes MUST report zero findings for this file — any finding here is a
false positive in the S2 gate (RUNBOOK §4.3, LEDGER §3).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def checksum(payload: str, algorithm: str = "sha256") -> str:
    """Return a hex digest of the payload using the given hashlib algorithm."""
    hasher = hashlib.new(algorithm)
    hasher.update(payload.encode("utf-8"))
    return hasher.hexdigest()


def round_trip(data: dict[str, Any]) -> dict[str, Any]:
    """Serialize to JSON and back through a string round-trip."""
    return json.loads(json.dumps(data))