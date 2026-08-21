# Bug Report #5

## Bug Report: tests/detectors/phase4_audit_test.py::test_f01_quality_reacts_to_findings

Severity: HIGH  
Detected: 2026-08-16T15:42:10.141339  
Error Type: failed

### Error Message
```
audit_root = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_f01_quality_reacts_to_fin0/repo')

    def test_f01_quality_reacts_to_findings(audit_root):
        # RECALL: adding a critical finding must depress overall_score. Pre-fix
        # the quality component never read findings (fallback 80), so the score
        # was insensitive to severity (detector returns 1).
>       assert health_quality_ignores_findings(str(audit_root)) == 0
E       AssertionError: assert 1 == 0
E        +  where 1 = health_quality_ignores_findings('C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_f01_quality_reacts_to_fin0\\repo')
E        +    where 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_f01_quality_reacts_to_fin0\\repo' = str(WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_f01_quality_reacts_to_fin0/repo'))

tests\detectors\phase4_audit_test.py:138: AssertionError
```

### Traceback
```
audit_root = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_f01_quality_reacts_to_fin0/repo')

    def test_f01_quality_reacts_to_findings(audit_root):
        # RECALL: adding a critical finding must depress overall_score. Pre-fix
        # the quality component never read findings (fallback 80), so the score
        # was insensitive to severity (detector returns 1).
>       assert health_quality_ignores_findings(str(audit_root)) == 0
E       AssertionError: assert 1 == 0
E        +  where 1 = health_quality_ignores_findings('C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_f01_quality_reacts_to_fin0\\repo')
E        +    where 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_f01_quality_reacts_to_fin0\\repo' = str(WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_f01_quality_reacts_to_fin0/repo'))

tests\detectors\phase4_audit_test.py:138: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
