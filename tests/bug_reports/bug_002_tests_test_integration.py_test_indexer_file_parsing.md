# Bug Report #2

## Bug Report: tests/test_integration.py::test_indexer_file_parsing

Severity: HIGH  
Detected: 2026-08-21T17:01:07.235037  
Error Type: failed

### Error Message
```
tests\test_integration.py:348: in test_indexer_file_parsing
    assert result.get('files_indexed', 0) > 0, "Files should be indexed"
E   AssertionError: Files should be indexed
E   assert 0 > 0
E    +  where 0 = <built-in method get of dict object at 0x000001BDA7BCB9C0>('files_indexed', 0)
E    +    where <built-in method get of dict object at 0x000001BDA7BCB9C0> = {'files': 3, 'symbols': 5, 'chunks': 5, 'edges': 6, 'vectors': 5, 'dirty': 3, 'deleted': 0, 'embedded': 5, 'ms': 1238}.get
```

### Traceback
```
tests\test_integration.py:348: in test_indexer_file_parsing
    assert result.get('files_indexed', 0) > 0, "Files should be indexed"
E   AssertionError: Files should be indexed
E   assert 0 > 0
E    +  where 0 = <built-in method get of dict object at 0x000001BDA7BCB9C0>('files_indexed', 0)
E    +    where <built-in method get of dict object at 0x000001BDA7BCB9C0> = {'files': 3, 'symbols': 5, 'chunks': 5, 'edges': 6, 'vectors': 5, 'dirty': 3, 'deleted': 0, 'embedded': 5, 'ms': 1238}.get
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
