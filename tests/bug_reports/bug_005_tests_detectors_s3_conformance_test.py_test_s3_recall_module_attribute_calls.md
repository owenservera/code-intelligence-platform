# Bug Report #5

## Bug Report: tests/detectors/s3_conformance_test.py::test_s3_recall_module_attribute_calls

Severity: HIGH  
Detected: 2026-08-16T16:51:07.118314  
Error Type: failed

### Error Message
```
def test_s3_recall_module_attribute_calls():
        """F-21/F-31/F-32: attribute calls on attributes the modules never export."""
        ev = _evidence("CODE-MISSING-SYMBOL")
        assert any("retrieve.hybrid_search" in e for e in ev)          # F-21 /api/search 500
>       assert any("retrieve.runtime_adapters.broken" in e for e in ev)  # F-31 session context
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       assert False
E        +  where False = any(<generator object test_s3_recall_module_attribute_calls.<locals>.<genexpr> at 0x000001E631B6BD30>)

tests\detectors\s3_conformance_test.py:97: AssertionError
```

### Traceback
```
def test_s3_recall_module_attribute_calls():
        """F-21/F-31/F-32: attribute calls on attributes the modules never export."""
        ev = _evidence("CODE-MISSING-SYMBOL")
        assert any("retrieve.hybrid_search" in e for e in ev)          # F-21 /api/search 500
>       assert any("retrieve.runtime_adapters.broken" in e for e in ev)  # F-31 session context
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       assert False
E        +  where False = any(<generator object test_s3_recall_module_attribute_calls.<locals>.<genexpr> at 0x000001E631B6BD30>)

tests\detectors\s3_conformance_test.py:97: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
