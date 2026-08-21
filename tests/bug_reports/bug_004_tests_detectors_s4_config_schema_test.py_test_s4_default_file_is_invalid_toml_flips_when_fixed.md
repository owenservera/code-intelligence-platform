# Bug Report #4

## Bug Report: tests/detectors/s4_config_schema_test.py::test_s4_default_file_is_invalid_toml_flips_when_fixed

Severity: HIGH  
Detected: 2026-08-21T16:59:26.587886  
Error Type: failed

### Error Message
```
tests\detectors\s4_config_schema_test.py:90: in test_s4_default_file_is_invalid_toml_flips_when_fixed
    with pytest.raises(tomllib.TOMLDecodeError):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE <class 'tomllib.TOMLDecodeError'>
```

### Traceback
```
tests\detectors\s4_config_schema_test.py:90: in test_s4_default_file_is_invalid_toml_flips_when_fixed
    with pytest.raises(tomllib.TOMLDecodeError):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE <class 'tomllib.TOMLDecodeError'>
```

### Suggested Fix
BUG: failed. Review the error message and traceback for specific guidance.

---
