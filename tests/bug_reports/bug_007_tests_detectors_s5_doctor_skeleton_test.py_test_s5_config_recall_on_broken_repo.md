# Bug Report #7

## Bug Report: tests/detectors/s5_doctor_skeleton_test.py::test_s5_config_recall_on_broken_repo

Severity: HIGH  
Detected: 2026-08-17T17:42:59.179297  
Error Type: failed

### Error Message
```
tests\detectors\s5_doctor_skeleton_test.py:96: in test_s5_config_recall_on_broken_repo
    assert expected <= rules, f"doctor --config missed evidence. got={sorted(rules)}"
E   AssertionError: doctor --config missed evidence. got=['CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-PORT-MISMATCH', 'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-SCHEMA-DRIFT']
E   assert {'CONFIG-FILE...NT-FAIL', ...} <= {'CONFIG-KEY-...SCHEMA-DRIFT'}
E     
E     Extra items in the left set:
E     [0m[33m'[39;49;00m[33mCONFIG-FILE-UNPARSEABLE[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E     [0m[33m'[39;49;00m[33mCONFIG-MISSING-SECTION[39;49;00m[33m'[39;49;00m[90m[39;49;00m
```

### Traceback
```
tests\detectors\s5_doctor_skeleton_test.py:96: in test_s5_config_recall_on_broken_repo
    assert expected <= rules, f"doctor --config missed evidence. got={sorted(rules)}"
E   AssertionError: doctor --config missed evidence. got=['CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-PORT-MISMATCH', 'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-SCHEMA-DRIFT']
E   assert {'CONFIG-FILE...NT-FAIL', ...} <= {'CONFIG-KEY-...SCHEMA-DRIFT'}
E     
E     Extra items in the left set:
E     [0m[33m'[39;49;00m[33mCONFIG-FILE-UNPARSEABLE[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E     [0m[33m'[39;49;00m[33mCONFIG-MISSING-SECTION[39;49;00m[33m'[39;49;00m[90m[39;49;00m
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
