# Bug Report #1

## Bug Report: tests/detectors/s4_config_schema_test.py::test_s4_precision_performance_fires_only_key_unused

Severity: HIGH  
Detected: 2026-08-16T03:46:00.749994  
Error Type: failed

### Error Message
```
def test_s4_precision_performance_fires_only_key_unused():
        with tempfile.TemporaryDirectory() as tmp:
            findings = doctor.config_checks(tmp, cfg={"performance": {"workers": 0}})
        rules = {f["rule"] for f in findings}
>       assert rules == {"CONFIG-KEY-UNUSED"}, rules
E       AssertionError: {'CONFIG-KEY-UNUSED', 'CONFIG-MISSING-SECTION'}
E       assert {'CONFIG-KEY-...SING-SECTION'} == {'CONFIG-KEY-UNUSED'}
E         
E         Extra items in the left set:
E         'CONFIG-MISSING-SECTION'
E         Use -v to get more diff

tests\detectors\s4_config_schema_test.py:161: AssertionError
```

### Traceback
```
def test_s4_precision_performance_fires_only_key_unused():
        with tempfile.TemporaryDirectory() as tmp:
            findings = doctor.config_checks(tmp, cfg={"performance": {"workers": 0}})
        rules = {f["rule"] for f in findings}
>       assert rules == {"CONFIG-KEY-UNUSED"}, rules
E       AssertionError: {'CONFIG-KEY-UNUSED', 'CONFIG-MISSING-SECTION'}
E       assert {'CONFIG-KEY-...SING-SECTION'} == {'CONFIG-KEY-UNUSED'}
E         
E         Extra items in the left set:
E         'CONFIG-MISSING-SECTION'
E         Use -v to get more diff

tests\detectors\s4_config_schema_test.py:161: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
