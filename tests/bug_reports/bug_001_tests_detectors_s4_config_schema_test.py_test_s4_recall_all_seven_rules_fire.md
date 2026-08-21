# Bug Report #1

## Bug Report: tests/detectors/s4_config_schema_test.py::test_s4_recall_all_seven_rules_fire

Severity: HIGH  
Detected: 2026-08-21T16:59:26.529277  
Error Type: failed

### Error Message
```
tests\detectors\s4_config_schema_test.py:62: in test_s4_recall_all_seven_rules_fire
    assert CONFIG_REFS.keys() <= rules, f"missing rules: {set(CONFIG_REFS) - rules}"
E   AssertionError: missing rules: {'CONFIG-MISSING-SECTION', 'CONFIG-FILE-UNPARSEABLE'}
E   assert dict_keys(['CONFIG-FILE-UNPARSEABLE', 'CONFIG-PORT-MISMATCH', 'CONFIG-SCHEMA-DRIFT', 'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-MISSING-SECTION', 'CONFIG-PROFILE-SILENT-FAIL']) <= {'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-PORT-MISMATCH', 'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-SCHEMA-DRIFT'}
E    +  where dict_keys(['CONFIG-FILE-UNPARSEABLE', 'CONFIG-PORT-MISMATCH', 'CONFIG-SCHEMA-DRIFT', 'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-MISSING-SECTION', 'CONFIG-PROFILE-SILENT-FAIL']) = <built-in method keys of dict object at 0x000001EB47AA7580>()
E    +    where <built-in method keys of dict object at 0x000001EB47AA7580> = {'CONFIG-FILE-UNPARSEABLE': 'CORE-39', 'CONFIG-PORT-MISMATCH': 'CORE-10', 'CONFIG-SCHEMA-DRIFT': 'CORE-40', 'CONFIG-KEY-DRIFT': 'CORE-39', 'CONFIG-KEY-UNUSED': 'CORE-42', 'CONFIG-MISSING-SECTION': 'CORE-2', 'CONFIG-PROFILE-SILENT-FAIL': 'F-11'}.keys
```

### Traceback
```
tests\detectors\s4_config_schema_test.py:62: in test_s4_recall_all_seven_rules_fire
    assert CONFIG_REFS.keys() <= rules, f"missing rules: {set(CONFIG_REFS) - rules}"
E   AssertionError: missing rules: {'CONFIG-MISSING-SECTION', 'CONFIG-FILE-UNPARSEABLE'}
E   assert dict_keys(['CONFIG-FILE-UNPARSEABLE', 'CONFIG-PORT-MISMATCH', 'CONFIG-SCHEMA-DRIFT', 'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-MISSING-SECTION', 'CONFIG-PROFILE-SILENT-FAIL']) <= {'CONFIG-PROFILE-SILENT-FAIL', 'CONFIG-PORT-MISMATCH', 'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-SCHEMA-DRIFT'}
E    +  where dict_keys(['CONFIG-FILE-UNPARSEABLE', 'CONFIG-PORT-MISMATCH', 'CONFIG-SCHEMA-DRIFT', 'CONFIG-KEY-DRIFT', 'CONFIG-KEY-UNUSED', 'CONFIG-MISSING-SECTION', 'CONFIG-PROFILE-SILENT-FAIL']) = <built-in method keys of dict object at 0x000001EB47AA7580>()
E    +    where <built-in method keys of dict object at 0x000001EB47AA7580> = {'CONFIG-FILE-UNPARSEABLE': 'CORE-39', 'CONFIG-PORT-MISMATCH': 'CORE-10', 'CONFIG-SCHEMA-DRIFT': 'CORE-40', 'CONFIG-KEY-DRIFT': 'CORE-39', 'CONFIG-KEY-UNUSED': 'CORE-42', 'CONFIG-MISSING-SECTION': 'CORE-2', 'CONFIG-PROFILE-SILENT-FAIL': 'F-11'}.keys
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
