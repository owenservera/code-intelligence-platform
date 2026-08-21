# Bug Report #2

## Bug Report: tests/detectors/s3_conformance_test.py::test_s3_recall_f34_selftest_symbol

Severity: HIGH  
Detected: 2026-08-16T16:50:47.025090  
Error Type: failed

### Error Message
```
def test_s3_recall_f34_selftest_symbol():
        """F-34: selftest.selftest does not exist (cli + terminal_dashboard)."""
        ev = _evidence("CODE-MISSING-SYMBOL")
>       assert any("from .selftest import selftest" in e for e in ev)
E       assert False
E        +  where False = any(<generator object test_s3_recall_f34_selftest_symbol.<locals>.<genexpr> at 0x000001E6318EE260>)

tests\detectors\s3_conformance_test.py:73: AssertionError
```

### Traceback
```
def test_s3_recall_f34_selftest_symbol():
        """F-34: selftest.selftest does not exist (cli + terminal_dashboard)."""
        ev = _evidence("CODE-MISSING-SYMBOL")
>       assert any("from .selftest import selftest" in e for e in ev)
E       assert False
E        +  where False = any(<generator object test_s3_recall_f34_selftest_symbol.<locals>.<genexpr> at 0x000001E6318EE260>)

tests\detectors\s3_conformance_test.py:73: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
