# Bug Report #1

## Bug Report: tests/detectors/s5_doctor_skeleton_test.py::test_s5_config_recall_on_broken_repo

Severity: HIGH  
Detected: 2026-08-17T13:21:41.301159  
Error Type: failed

### Error Message
```
def test_s5_config_recall_on_broken_repo():
        """RECALL: the CONFIG-* skeleton fires on the repo's current broken config."""
        findings = doctor.config_checks(str(ROOT))
        rules = {f["rule"] for f in findings}
        # F-42/CORE-39 note: exclude_patterns+max_file_size are the ignored TOML keys.
        expected = {
            "CONFIG-FILE-UNPARSEABLE",       # config.default.toml health_weights = { multi-line
    
            "CONFIG-PORT-MISMATCH",      # CORE-10 8765 vs 8787
    
            "CONFIG-SCHEMA-DRIFT",       # CORE-40/BUG-023 11 vs 4
    
            "CONFIG-KEY-DRIFT",          # CORE-39
    
            "CONFIG-KEY-UNUSED",         # CORE-42 [performance]
    
            "CONFIG-MISSING-SECTION",    # CORE-2 [web]
    
            "CONFIG-PROFILE-SILENT-FAIL",  # F-11
    
        }
>       assert expected <= rules, f"doctor --config missed evidence. got={sorted(rules)}"
E       AssertionError: doctor --config missed evidence. got=['CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-PORT-MISMATCH', 'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-SCHEMA-DRIFT']
E       assert {'CONFIG-FILE...NT-FAIL', ...} <= {'CONFIG-KEY-...SCHEMA-DRIFT'}
E         
E         Extra items in the left set:
E         'CONFIG-MISSING-SECTION'
E         'CONFIG-FILE-UNPARSEABLE'

tests\detectors\s5_doctor_skeleton_test.py:96: AssertionError
```

### Traceback
```
def test_s5_config_recall_on_broken_repo():
        """RECALL: the CONFIG-* skeleton fires on the repo's current broken config."""
        findings = doctor.config_checks(str(ROOT))
        rules = {f["rule"] for f in findings}
        # F-42/CORE-39 note: exclude_patterns+max_file_size are the ignored TOML keys.
        expected = {
            "CONFIG-FILE-UNPARSEABLE",       # config.default.toml health_weights = { multi-line
    
            "CONFIG-PORT-MISMATCH",      # CORE-10 8765 vs 8787
    
            "CONFIG-SCHEMA-DRIFT",       # CORE-40/BUG-023 11 vs 4
    
            "CONFIG-KEY-DRIFT",          # CORE-39
    
            "CONFIG-KEY-UNUSED",         # CORE-42 [performance]
    
            "CONFIG-MISSING-SECTION",    # CORE-2 [web]
    
            "CONFIG-PROFILE-SILENT-FAIL",  # F-11
    
        }
>       assert expected <= rules, f"doctor --config missed evidence. got={sorted(rules)}"
E       AssertionError: doctor --config missed evidence. got=['CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-PORT-MISMATCH', 'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-SCHEMA-DRIFT']
E       assert {'CONFIG-FILE...NT-FAIL', ...} <= {'CONFIG-KEY-...SCHEMA-DRIFT'}
E         
E         Extra items in the left set:
E         'CONFIG-MISSING-SECTION'
E         'CONFIG-FILE-UNPARSEABLE'

tests\detectors\s5_doctor_skeleton_test.py:96: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
