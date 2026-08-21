# Bug Report #5

## Bug Report: tests/detectors/s5_doctor_skeleton_test.py::test_s5_config_recall_on_broken_repo

Severity: HIGH  
Detected: 2026-08-16T18:37:06.924493  
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
E       AssertionError: doctor --config missed evidence. got=['CONFIG-FILE-UNPARSEABLE', 'CONFIG-PROFILE-SILENT-FAIL']
E       assert {'CONFIG-FILE...NT-FAIL', ...} <= {'CONFIG-FILE...-SILENT-FAIL'}
E         
E         Extra items in the left set:
E         [0m[33m'[39;49;00m[33mCONFIG-PORT-MISMATCH[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E         [0m[33m'[39;49;00m[33mCONFIG-SCHEMA-DRIFT[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E         [0m[33m'[39;49;00m[33mCONFIG-KEY-DRIFT[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E         [0m[33m'[39;49;00m[33mCONFIG-KEY-UNUSED[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E         [0m[33m'[39;49;00m[33mCONFIG-MISSING-SECTION[39;49;00m[33m'[39;49;00m[90m[39;49;00m

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
E       AssertionError: doctor --config missed evidence. got=['CONFIG-FILE-UNPARSEABLE', 'CONFIG-PROFILE-SILENT-FAIL']
E       assert {'CONFIG-FILE...NT-FAIL', ...} <= {'CONFIG-FILE...-SILENT-FAIL'}
E         
E         Extra items in the left set:
E         [0m[33m'[39;49;00m[33mCONFIG-PORT-MISMATCH[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E         [0m[33m'[39;49;00m[33mCONFIG-SCHEMA-DRIFT[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E         [0m[33m'[39;49;00m[33mCONFIG-KEY-DRIFT[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E         [0m[33m'[39;49;00m[33mCONFIG-KEY-UNUSED[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E         [0m[33m'[39;49;00m[33mCONFIG-MISSING-SECTION[39;49;00m[33m'[39;49;00m[90m[39;49;00m

tests\detectors\s5_doctor_skeleton_test.py:96: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
