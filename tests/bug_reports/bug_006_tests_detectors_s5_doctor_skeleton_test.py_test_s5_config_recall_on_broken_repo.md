# Bug Report #6

## Bug Report: tests/detectors/s5_doctor_skeleton_test.py::test_s5_config_recall_on_broken_repo

Severity: HIGH  
Detected: 2026-08-21T16:59:26.687524  
Error Type: failed

### Error Message
```
tests\detectors\s5_doctor_skeleton_test.py:96: in test_s5_config_recall_on_broken_repo
    assert expected <= rules, f"doctor --config missed evidence. got={sorted(rules)}"
E   AssertionError: doctor --config missed evidence. got=['CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-PORT-MISMATCH', 'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-SCHEMA-DRIFT']
E   assert {'CONFIG-PORT-MISMATCH', 'CONFIG-FILE-UNPARSEABLE', 'CONFIG-MISSING-SECTION', 'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-SCHEMA-DRIFT'} <= {'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-KEY-UNUSED', 'CONFIG-PORT-MISMATCH', 'CONFIG-KEY-DRIFT', 'CONFIG-SCHEMA-DRIFT'}
E     
E     Extra items in the left set:
E     'CONFIG-MISSING-SECTION'
E     'CONFIG-FILE-UNPARSEABLE'
```

### Traceback
```
tests\detectors\s5_doctor_skeleton_test.py:96: in test_s5_config_recall_on_broken_repo
    assert expected <= rules, f"doctor --config missed evidence. got={sorted(rules)}"
E   AssertionError: doctor --config missed evidence. got=['CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-PORT-MISMATCH', 'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-SCHEMA-DRIFT']
E   assert {'CONFIG-PORT-MISMATCH', 'CONFIG-FILE-UNPARSEABLE', 'CONFIG-MISSING-SECTION', 'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-SCHEMA-DRIFT'} <= {'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-KEY-UNUSED', 'CONFIG-PORT-MISMATCH', 'CONFIG-KEY-DRIFT', 'CONFIG-SCHEMA-DRIFT'}
E     
E     Extra items in the left set:
E     'CONFIG-MISSING-SECTION'
E     'CONFIG-FILE-UNPARSEABLE'
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
