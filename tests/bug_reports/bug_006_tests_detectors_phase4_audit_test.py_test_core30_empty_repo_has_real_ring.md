# Bug Report #6

## Bug Report: tests/detectors/phase4_audit_test.py::test_core30_empty_repo_has_real_ring

Severity: HIGH  
Detected: 2026-08-16T15:42:10.557838  
Error Type: failed

### Error Message
```
audit_root = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_core30_empty_repo_has_rea0/repo')

    def test_core30_empty_repo_has_real_ring(audit_root):
        # RECALL: an empty repo (0 symbols) must not hardcode 50 and must still
        # penalize findings (pre-fix `_calculate_health_score` had a literal 50
        # early-return that also masked findings entirely).
>       assert health_empty_repo_literal(audit_root) == 0
E       AssertionError: assert 1 == 0
E        +  where 1 = health_empty_repo_literal(WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_core30_empty_repo_has_rea0/repo'))

tests\detectors\phase4_audit_test.py:149: AssertionError
```

### Traceback
```
audit_root = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_core30_empty_repo_has_rea0/repo')

    def test_core30_empty_repo_has_real_ring(audit_root):
        # RECALL: an empty repo (0 symbols) must not hardcode 50 and must still
        # penalize findings (pre-fix `_calculate_health_score` had a literal 50
        # early-return that also masked findings entirely).
>       assert health_empty_repo_literal(audit_root) == 0
E       AssertionError: assert 1 == 0
E        +  where 1 = health_empty_repo_literal(WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_core30_empty_repo_has_rea0/repo'))

tests\detectors\phase4_audit_test.py:149: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
