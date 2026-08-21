# Bug Report #1

## Bug Report: tests/test_integration.py::test_indexer_file_parsing

Severity: HIGH  
Detected: 2026-08-18T17:07:11.574395  
Error Type: failed

### Error Message
```
tests\test_integration.py:348: in test_indexer_file_parsing
    assert result.get('files_indexed', 0) > 0, "Files should be indexed"
E   AssertionError: Files should be indexed
E   assert 0 > 0
E    +  where 0 = <built-in method get of dict object at 0x000001E8C4DC96C0>('files_indexed', 0)
E    +    where <built-in method get of dict object at 0x000001E8C4DC96C0> = {'chunks': 5, 'deleted': 0, 'dirty': 3, 'edges': 6, ...}.get
```

### Traceback
```
tests\test_integration.py:348: in test_indexer_file_parsing
    assert result.get('files_indexed', 0) > 0, "Files should be indexed"
E   AssertionError: Files should be indexed
E   assert 0 > 0
E    +  where 0 = <built-in method get of dict object at 0x000001E8C4DC96C0>('files_indexed', 0)
E    +    where <built-in method get of dict object at 0x000001E8C4DC96C0> = {'chunks': 5, 'deleted': 0, 'dirty': 3, 'edges': 6, ...}.get
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
