# Bug Report #6

## Bug Report: tests/detectors/s3_conformance_test.py::test_s3_recall_class_instance_member

Severity: HIGH  
Detected: 2026-08-16T16:51:12.180674  
Error Type: failed

### Error Message
```
def test_s3_recall_class_instance_member():
        """F-20: FilterEngine has no 'rank' member."""
        ev = _evidence("CODE-MISSING-SYMBOL")
>       assert any("filter_engine.rank" in e for e in ev)
E       assert False
E        +  where False = any(<generator object test_s3_recall_class_instance_member.<locals>.<genexpr> at 0x000001E631B6BD30>)

tests\detectors\s3_conformance_test.py:104: AssertionError
```

### Traceback
```
def test_s3_recall_class_instance_member():
        """F-20: FilterEngine has no 'rank' member."""
        ev = _evidence("CODE-MISSING-SYMBOL")
>       assert any("filter_engine.rank" in e for e in ev)
E       assert False
E        +  where False = any(<generator object test_s3_recall_class_instance_member.<locals>.<genexpr> at 0x000001E631B6BD30>)

tests\detectors\s3_conformance_test.py:104: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
