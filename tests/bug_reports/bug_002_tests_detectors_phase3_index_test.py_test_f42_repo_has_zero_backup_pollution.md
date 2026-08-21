# Bug Report #2

## Bug Report: tests/detectors/phase3_index_test.py::test_f42_repo_has_zero_backup_pollution

Severity: HIGH  
Detected: 2026-08-16T04:23:23.143983  
Error Type: failed

### Error Message
```
def test_f42_repo_has_zero_backup_pollution():
        backup, total, frac = backup_pollution(REPO)
        assert total > 50
>       assert backup == 0 and frac == 0.0     # pre-fix: 575 / 753 (76.4%)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       assert (2 == 0)

tests\detectors\phase3_index_test.py:148: AssertionError
```

### Traceback
```
def test_f42_repo_has_zero_backup_pollution():
        backup, total, frac = backup_pollution(REPO)
        assert total > 50
>       assert backup == 0 and frac == 0.0     # pre-fix: 575 / 753 (76.4%)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       assert (2 == 0)

tests\detectors\phase3_index_test.py:148: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
