# Bug Report #1

## Bug Report: tests/detectors/phase3_index_test.py::test_f22_repo_inrepo_resolution_rate_high

Severity: HIGH  
Detected: 2026-08-17T17:41:45.719120  
Error Type: failed

### Error Message
```
tests\detectors\phase3_index_test.py:117: in test_f22_repo_inrepo_resolution_rate_high
    assert rate >= 0.99            # pre-fix was ~0.2%
    ^^^^^^^^^^^^^^^^^^^
E   assert 0.9671361502347418 >= 0.99
```

### Traceback
```
tests\detectors\phase3_index_test.py:117: in test_f22_repo_inrepo_resolution_rate_high
    assert rate >= 0.99            # pre-fix was ~0.2%
    ^^^^^^^^^^^^^^^^^^^
E   assert 0.9671361502347418 >= 0.99
```

### Suggested Fix
BUG: failed. Review the error message and traceback for specific guidance.

---
