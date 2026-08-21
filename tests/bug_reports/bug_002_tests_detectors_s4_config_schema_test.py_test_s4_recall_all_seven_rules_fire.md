# Bug Report #2

## Bug Report: tests/detectors/s4_config_schema_test.py::test_s4_recall_all_seven_rules_fire

Severity: HIGH  
Detected: 2026-08-17T17:42:57.096765  
Error Type: failed

### Error Message
```
tests\detectors\s4_config_schema_test.py:62: in test_s4_recall_all_seven_rules_fire
    assert CONFIG_REFS.keys() <= rules, f"missing rules: {set(CONFIG_REFS) - rules}"
E   AssertionError: missing rules: {'CONFIG-FILE-UNPARSEABLE', 'CONFIG-MISSING-SECTION'}
E   assert dict_keys(['CONFIG-FILE-UNPARSEABLE', 'CONFIG-PORT-MISMATCH', 'CONFIG-SCHEMA-DRIFT', 'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-MISSING-SECTION', 'CONFIG-PROFILE-SILENT-FAIL']) <= {'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-PORT-MISMATCH', 'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-SCHEMA-DRIFT'}
E    +  where dict_keys(['CONFIG-FILE-UNPARSEABLE', 'CONFIG-PORT-MISMATCH', 'CONFIG-SCHEMA-DRIFT', 'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-MISSING-SECTION', 'CONFIG-PROFILE-SILENT-FAIL']) = <built-in method keys of dict object at 0x00000204C88BF940>()
E    +    where <built-in method keys of dict object at 0x00000204C88BF940> = {'CONFIG-FILE-UNPARSEABLE': 'CORE-39', 'CONFIG-KEY-DRIFT': 'CORE-39', 'CONFIG-KEY-UNUSED': 'CORE-42', 'CONFIG-MISSING-SECTION': 'CORE-2', ...}.keys
```

### Traceback
```
tests\detectors\s4_config_schema_test.py:62: in test_s4_recall_all_seven_rules_fire
    assert CONFIG_REFS.keys() <= rules, f"missing rules: {set(CONFIG_REFS) - rules}"
E   AssertionError: missing rules: {'CONFIG-FILE-UNPARSEABLE', 'CONFIG-MISSING-SECTION'}
E   assert dict_keys(['CONFIG-FILE-UNPARSEABLE', 'CONFIG-PORT-MISMATCH', 'CONFIG-SCHEMA-DRIFT', 'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-MISSING-SECTION', 'CONFIG-PROFILE-SILENT-FAIL']) <= {'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-PORT-MISMATCH', 'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-SCHEMA-DRIFT'}
E    +  where dict_keys(['CONFIG-FILE-UNPARSEABLE', 'CONFIG-PORT-MISMATCH', 'CONFIG-SCHEMA-DRIFT', 'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-MISSING-SECTION', 'CONFIG-PROFILE-SILENT-FAIL']) = <built-in method keys of dict object at 0x00000204C88BF940>()
E    +    where <built-in method keys of dict object at 0x00000204C88BF940> = {'CONFIG-FILE-UNPARSEABLE': 'CORE-39', 'CONFIG-KEY-DRIFT': 'CORE-39', 'CONFIG-KEY-UNUSED': 'CORE-42', 'CONFIG-MISSING-SECTION': 'CORE-2', ...}.keys
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
