# Bug Report #2

## Bug Report: tests/detectors/phase4_audit_test.py::test_f41_subindexer_failures_surfaced

Severity: HIGH  
Detected: 2026-08-16T15:42:08.931253  
Error Type: failed

### Error Message
```
audit_root = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_f41_subindexer_failures_s0/repo')

    def test_f41_subindexer_failures_surfaced(audit_root):
        # RECALL: nextjs.index_routes / prisma.index_stack raising must be visible
        # in the audit result (pre-fix both were swallowed by log_swallowed).
>       assert audit_silent_subindexer_failures(str(audit_root)) == 0
E       AssertionError: assert 2 == 0
E        +  where 2 = audit_silent_subindexer_failures('C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_f41_subindexer_failures_s0\\repo')
E        +    where 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_f41_subindexer_failures_s0\\repo' = str(WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_f41_subindexer_failures_s0/repo'))

tests\detectors\phase4_audit_test.py:102: AssertionError
```

### Traceback
```
audit_root = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_f41_subindexer_failures_s0/repo')

    def test_f41_subindexer_failures_surfaced(audit_root):
        # RECALL: nextjs.index_routes / prisma.index_stack raising must be visible
        # in the audit result (pre-fix both were swallowed by log_swallowed).
>       assert audit_silent_subindexer_failures(str(audit_root)) == 0
E       AssertionError: assert 2 == 0
E        +  where 2 = audit_silent_subindexer_failures('C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_f41_subindexer_failures_s0\\repo')
E        +    where 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_f41_subindexer_failures_s0\\repo' = str(WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_f41_subindexer_failures_s0/repo'))

tests\detectors\phase4_audit_test.py:102: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
