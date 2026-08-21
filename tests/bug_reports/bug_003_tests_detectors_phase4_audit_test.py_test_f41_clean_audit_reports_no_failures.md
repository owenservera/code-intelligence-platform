# Bug Report #3

## Bug Report: tests/detectors/phase4_audit_test.py::test_f41_clean_audit_reports_no_failures

Severity: HIGH  
Detected: 2026-08-16T15:42:09.117446  
Error Type: failed

### Error Message
```
audit_root = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_f41_clean_audit_reports_n0/repo')

    def test_f41_clean_audit_reports_no_failures(audit_root):
        # PRECISION: a healthy audit reports an empty failed_indexers list (the
        # key must exist so consumers can distinguish "no failures" from "silent").
        from cipkg.stack import audit
        out = audit.audit(str(audit_root), refresh=True)
>       assert out.get("failed_indexers") == []
E       AssertionError: assert None == []
E        +  where None = <built-in method get of dict object at 0x000001D6AB9FD440>('failed_indexers')
E        +    where <built-in method get of dict object at 0x000001D6AB9FD440> = {'by_severity': {}, 'critical': 0, 'high': 0, 'open': 0}.get

tests\detectors\phase4_audit_test.py:110: AssertionError
```

### Traceback
```
audit_root = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_f41_clean_audit_reports_n0/repo')

    def test_f41_clean_audit_reports_no_failures(audit_root):
        # PRECISION: a healthy audit reports an empty failed_indexers list (the
        # key must exist so consumers can distinguish "no failures" from "silent").
        from cipkg.stack import audit
        out = audit.audit(str(audit_root), refresh=True)
>       assert out.get("failed_indexers") == []
E       AssertionError: assert None == []
E        +  where None = <built-in method get of dict object at 0x000001D6AB9FD440>('failed_indexers')
E        +    where <built-in method get of dict object at 0x000001D6AB9FD440> = {'by_severity': {}, 'critical': 0, 'high': 0, 'open': 0}.get

tests\detectors\phase4_audit_test.py:110: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
