# Bug Report #1

## Bug Report: tests/test_integration.py::test_context_retrieval_integration

Severity: HIGH  
Detected: 2026-08-15T22:14:38.513616  
Error Type: failed

### Error Message
```
tests\test_integration.py:110: in test_context_retrieval_integration
    indexer.sync(con, cfg)
lib\cipkg\indexer.py:408: in sync
    with WriteLock(root):
         ^^^^^^^^^^^^^^^
lib\cipkg\lock.py:11: in __init__
    self.path = os.path.join(data_dir(root), "write.lock")
                             ^^^^^^^^^^^^^^
lib\cipkg\base.py:78: in data_dir
    d = os.path.join(cip_dir(root), "data")
                     ^^^^^^^^^^^^^
lib\cipkg\base.py:75: in cip_dir
    def cip_dir(root):  return os.path.join(root, CIP_DIRNAME)
                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen ntpath>:100: in join
    ???
E   TypeError: expected str, bytes or os.PathLike object, not Connection
```

### Traceback
```
tests\test_integration.py:110: in test_context_retrieval_integration
    indexer.sync(con, cfg)
lib\cipkg\indexer.py:408: in sync
    with WriteLock(root):
         ^^^^^^^^^^^^^^^
lib\cipkg\lock.py:11: in __init__
    self.path = os.path.join(data_dir(root), "write.lock")
                             ^^^^^^^^^^^^^^
lib\cipkg\base.py:78: in data_dir
    d = os.path.join(cip_dir(root), "data")
                     ^^^^^^^^^^^^^
lib\cipkg\base.py:75: in cip_dir
    def cip_dir(root):  return os.path.join(root, CIP_DIRNAME)
                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen ntpath>:100: in join
    ???
E   TypeError: expected str, bytes or os.PathLike object, not Connection
```

### Suggested Fix
BUG: Type mismatch in operation. Ensure data types are compatible or add type conversion.

---
