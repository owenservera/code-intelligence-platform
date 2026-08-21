# Bug Report #2

## Bug Report: tests/detectors/s4_config_schema_test.py::test_s4_precision_exclude_patterns_fires_only_key_drift

Severity: HIGH  
Detected: 2026-08-16T03:46:00.777453  
Error Type: failed

### Error Message
```
def test_s4_precision_exclude_patterns_fires_only_key_drift():
        with tempfile.TemporaryDirectory() as tmp:
            findings = doctor.config_checks(tmp, cfg={"index": {"exclude_patterns": ["b"]}})
        rules = {f["rule"] for f in findings}
>       assert rules == {"CONFIG-KEY-DRIFT"}, rules
E       AssertionError: {'CONFIG-KEY-DRIFT', 'CONFIG-MISSING-SECTION'}
E       assert {'CONFIG-KEY-...SING-SECTION'} == {'CONFIG-KEY-DRIFT'}
E         
E         Extra items in the left set:
E         'CONFIG-MISSING-SECTION'
E         Use -v to get more diff

tests\detectors\s4_config_schema_test.py:168: AssertionError
```

### Traceback
```
def test_s4_precision_exclude_patterns_fires_only_key_drift():
        with tempfile.TemporaryDirectory() as tmp:
            findings = doctor.config_checks(tmp, cfg={"index": {"exclude_patterns": ["b"]}})
        rules = {f["rule"] for f in findings}
>       assert rules == {"CONFIG-KEY-DRIFT"}, rules
E       AssertionError: {'CONFIG-KEY-DRIFT', 'CONFIG-MISSING-SECTION'}
E       assert {'CONFIG-KEY-...SING-SECTION'} == {'CONFIG-KEY-DRIFT'}
E         
E         Extra items in the left set:
E         'CONFIG-MISSING-SECTION'
E         Use -v to get more diff

tests\detectors\s4_config_schema_test.py:168: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
