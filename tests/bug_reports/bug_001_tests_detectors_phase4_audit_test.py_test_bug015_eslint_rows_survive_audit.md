# Bug Report #1

## Bug Report: tests/detectors/phase4_audit_test.py::test_bug015_eslint_rows_survive_audit

Severity: HIGH  
Detected: 2026-08-16T15:42:08.515316  
Error Type: failed

### Error Message
```
audit_root = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_bug015_eslint_rows_surviv0/repo')

    def test_bug015_eslint_rows_survive_audit(audit_root):
        # RECALL: an ESLINT finding ingested on the eslint surface must not be
        # silently retired by a later stack audit (pre-fix it was).
>       assert findings_auto_closed_outside_run(str(audit_root)) == 0
E       AssertionError: assert 1 == 0
E        +  where 1 = findings_auto_closed_outside_run('C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_bug015_eslint_rows_surviv0\\repo')
E        +    where 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_bug015_eslint_rows_surviv0\\repo' = str(WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_bug015_eslint_rows_surviv0/repo'))

tests\detectors\phase4_audit_test.py:69: AssertionError
```

### Traceback
```
audit_root = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_bug015_eslint_rows_surviv0/repo')

    def test_bug015_eslint_rows_survive_audit(audit_root):
        # RECALL: an ESLINT finding ingested on the eslint surface must not be
        # silently retired by a later stack audit (pre-fix it was).
>       assert findings_auto_closed_outside_run(str(audit_root)) == 0
E       AssertionError: assert 1 == 0
E        +  where 1 = findings_auto_closed_outside_run('C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_bug015_eslint_rows_surviv0\\repo')
E        +    where 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_bug015_eslint_rows_surviv0\\repo' = str(WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_bug015_eslint_rows_surviv0/repo'))

tests\detectors\phase4_audit_test.py:69: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
