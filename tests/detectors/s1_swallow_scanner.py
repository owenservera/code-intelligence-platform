"""S1 swallow-scanner — promoted to the product (`cipkg.doctor`).

Phase S5 promoted the scanner into `lib/cipkg/doctor.py` (`cip doctor
--static`); this module is now a thin re-export shim so the regression-locked
S1 tests and LEDGER precision rows keep importing `s1_swallow_scanner`
unchanged. Canonical logic lives in `cipkg.doctor`.
"""

from __future__ import annotations

from cipkg.doctor import (  # noqa: F401  (re-export for regression tests)
    BROAD_NAMES,
    LOG_CALLS,
    _is_broad,
    _is_silent,
    scan_path,
    scan_text,
)