# Bug Report #3

## Bug Report: tests/detectors/s4_config_schema_test.py::test_s4_recall_port_mismatch_code_fires

Severity: HIGH  
Detected: 2026-08-16T03:46:00.863123  
Error Type: failed

### Error Message
```
def test_s4_recall_port_mismatch_code_fires():
        with tempfile.TemporaryDirectory() as tmp:
            _code_ports(tmp, 8787)
            findings = doctor.config_checks(tmp, cfg={"daemon": {"port": 8765}})
>       assert any(f["rule"] == "CONFIG-PORT-MISMATCH" for f in findings)
E       assert False
E        +  where False = any(<generator object test_s4_recall_port_mismatch_code_fires.<locals>.<genexpr> at 0x0000020C53997AC0>)

tests\detectors\s4_config_schema_test.py:203: AssertionError
```

### Traceback
```
def test_s4_recall_port_mismatch_code_fires():
        with tempfile.TemporaryDirectory() as tmp:
            _code_ports(tmp, 8787)
            findings = doctor.config_checks(tmp, cfg={"daemon": {"port": 8765}})
>       assert any(f["rule"] == "CONFIG-PORT-MISMATCH" for f in findings)
E       assert False
E        +  where False = any(<generator object test_s4_recall_port_mismatch_code_fires.<locals>.<genexpr> at 0x0000020C53997AC0>)

tests\detectors\s4_config_schema_test.py:203: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
