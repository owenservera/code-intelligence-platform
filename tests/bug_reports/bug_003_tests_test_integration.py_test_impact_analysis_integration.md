# Bug Report #3

## Bug Report: tests/test_integration.py::test_impact_analysis_integration

Severity: HIGH  
Detected: 2026-08-17T17:57:42.611703  
Error Type: failed

### Error Message
```
tests\test_integration.py:97: in test_impact_analysis_integration
    indexer.sync(con, cfg)
lib\cipkg\indexer.py:457: in sync
    with WriteLock(root):
         ^^^^^^^^^^^^^^^
lib\cipkg\lock.py:11: in __init__
    self.path = os.path.join(data_dir(root), "write.lock")
                             ^^^^^^^^^^^^^^
lib\cipkg\base.py:87: in data_dir
    d = os.path.join(cip_dir(root), "data")
                     ^^^^^^^^^^^^^
lib\cipkg\base.py:84: in cip_dir
    def cip_dir(root):  return os.path.join(root, CIP_DIRNAME)
                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen ntpath>:100: in join
    ???
E   TypeError: expected str, bytes or os.PathLike object, not Connection
```

### Traceback
```
tests\test_integration.py:97: in test_impact_analysis_integration
    indexer.sync(con, cfg)
lib\cipkg\indexer.py:457: in sync
    with WriteLock(root):
         ^^^^^^^^^^^^^^^
lib\cipkg\lock.py:11: in __init__
    self.path = os.path.join(data_dir(root), "write.lock")
                             ^^^^^^^^^^^^^^
lib\cipkg\base.py:87: in data_dir
    d = os.path.join(cip_dir(root), "data")
                     ^^^^^^^^^^^^^
lib\cipkg\base.py:84: in cip_dir
    def cip_dir(root):  return os.path.join(root, CIP_DIRNAME)
                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen ntpath>:100: in join
    ???
E   TypeError: expected str, bytes or os.PathLike object, not Connection
```

### Suggested Fix
BUG: Type mismatch in operation. Ensure data types are compatible or add type conversion.

---
