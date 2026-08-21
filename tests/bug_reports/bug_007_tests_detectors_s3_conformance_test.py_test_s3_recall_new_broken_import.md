# Bug Report #7

## Bug Report: tests/detectors/s3_conformance_test.py::test_s3_recall_new_broken_import

Severity: HIGH  
Detected: 2026-08-16T16:51:22.707175  
Error Type: failed

### Error Message
```
def test_s3_recall_new_broken_import():
        """cli.py imports from a missing module (ingest) and server.mcp_main."""
        ev = _evidence("CODE-MISSING-MODULE") + _evidence("CODE-MISSING-SYMBOL")
>       assert any("cli.py" in e and "ingest" in e for e in ev)
E       assert False
E        +  where False = any(<generator object test_s3_recall_new_broken_import.<locals>.<genexpr> at 0x000001E631B6BD30>)

tests\detectors\s3_conformance_test.py:110: AssertionError
```

### Traceback
```
def test_s3_recall_new_broken_import():
        """cli.py imports from a missing module (ingest) and server.mcp_main."""
        ev = _evidence("CODE-MISSING-MODULE") + _evidence("CODE-MISSING-SYMBOL")
>       assert any("cli.py" in e and "ingest" in e for e in ev)
E       assert False
E        +  where False = any(<generator object test_s3_recall_new_broken_import.<locals>.<genexpr> at 0x000001E631B6BD30>)

tests\detectors\s3_conformance_test.py:110: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
