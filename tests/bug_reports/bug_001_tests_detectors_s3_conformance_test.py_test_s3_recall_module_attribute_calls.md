# Bug Report #1

## Bug Report: tests/detectors/s3_conformance_test.py::test_s3_recall_module_attribute_calls

Severity: HIGH  
Detected: 2026-08-16T18:36:53.614685  
Error Type: failed

### Error Message
```
def test_s3_recall_module_attribute_calls():
        """F-21/F-31/F-32: attribute calls on attributes the modules never export.
    
        F-31 (retrieve.runtime_adapters.broken) was fixed in Phase 0 — flipped to
        clean. F-21 (retrieve.hybrid_search, web_server) and F-32
        (indexer.mark_for_reindex, watcher) are legacy-frontend deletion targets
        and remain live findings until the Phase 1/5 sweep.
        """
        ev = _evidence("CODE-MISSING-SYMBOL")
        assert not any("retrieve.runtime_adapters.broken" in e for e in ev)  # F-31 fixed
        assert any("retrieve.hybrid_search" in e for e in ev)          # F-21 /api/search 500
>       assert any("indexer.mark_for_reindex" in e for e in ev)        # F-32 watcher re-index
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       assert False
E        +  where False = any(<generator object test_s3_recall_module_attribute_calls.<locals>.<genexpr> at 0x000001EB9A8CE260>)

tests\detectors\s3_conformance_test.py:121: AssertionError
```

### Traceback
```
def test_s3_recall_module_attribute_calls():
        """F-21/F-31/F-32: attribute calls on attributes the modules never export.
    
        F-31 (retrieve.runtime_adapters.broken) was fixed in Phase 0 — flipped to
        clean. F-21 (retrieve.hybrid_search, web_server) and F-32
        (indexer.mark_for_reindex, watcher) are legacy-frontend deletion targets
        and remain live findings until the Phase 1/5 sweep.
        """
        ev = _evidence("CODE-MISSING-SYMBOL")
        assert not any("retrieve.runtime_adapters.broken" in e for e in ev)  # F-31 fixed
        assert any("retrieve.hybrid_search" in e for e in ev)          # F-21 /api/search 500
>       assert any("indexer.mark_for_reindex" in e for e in ev)        # F-32 watcher re-index
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       assert False
E        +  where False = any(<generator object test_s3_recall_module_attribute_calls.<locals>.<genexpr> at 0x000001EB9A8CE260>)

tests\detectors\s3_conformance_test.py:121: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
