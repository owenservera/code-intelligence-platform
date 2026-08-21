# Bug Report #4

## Bug Report: tests/detectors/phase4_audit_test.py::test_bug014_coverage_reads_given_root

Severity: HIGH  
Detected: 2026-08-16T15:42:09.492149  
Error Type: failed

### Error Message
```
audit_root = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_bug014_coverage_reads_giv0/repo')

    def test_bug014_coverage_reads_given_root(audit_root):
        # RECALL: when a caller passes root, health coverage must come from that
        # root's index, not repo_root()/cwd (pre-fix it read the live/cwd DB).
>       assert health_coverage_root_mismatch(str(audit_root)) == 0
E       AssertionError: assert 1 == 0
E        +  where 1 = health_coverage_root_mismatch('C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_bug014_coverage_reads_giv0\\repo')
E        +    where 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_bug014_coverage_reads_giv0\\repo' = str(WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_bug014_coverage_reads_giv0/repo'))

tests\detectors\phase4_audit_test.py:120: AssertionError
```

### Traceback
```
audit_root = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_bug014_coverage_reads_giv0/repo')

    def test_bug014_coverage_reads_given_root(audit_root):
        # RECALL: when a caller passes root, health coverage must come from that
        # root's index, not repo_root()/cwd (pre-fix it read the live/cwd DB).
>       assert health_coverage_root_mismatch(str(audit_root)) == 0
E       AssertionError: assert 1 == 0
E        +  where 1 = health_coverage_root_mismatch('C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_bug014_coverage_reads_giv0\\repo')
E        +    where 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\pytest-of-VIVIM.inc\\pytest-8\\test_bug014_coverage_reads_giv0\\repo' = str(WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-8/test_bug014_coverage_reads_giv0/repo'))

tests\detectors\phase4_audit_test.py:120: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
