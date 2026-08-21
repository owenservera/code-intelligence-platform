# Bug Report #5

## Bug Report: tests/test_integration.py::test_impact_analysis_integration

Severity: HIGH  
Detected: 2026-08-16T17:34:08.209770  
Error Type: failed

### Error Message
```
temp_repo = 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\tmpte797ta4'

    def test_impact_analysis_integration(temp_repo):
        """Test impact analysis integration."""
        from cipkg.store import connect
        from cipkg import indexer
        from cipkg.stack.impact import impact
        from cipkg.base import load_config
    
        con = connect(temp_repo)
        cfg = load_config(temp_repo)
    
        # Index first
>       indexer.sync(con, cfg)

tests\test_integration.py:84: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
lib\cipkg\indexer.py:448: in sync
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
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

path = <sqlite3.Connection object at 0x00000191DB055030>, paths = ('.cip',)

>   ???
E   TypeError: expected str, bytes or os.PathLike object, not Connection

<frozen ntpath>:100: TypeError
```

### Traceback
```
temp_repo = 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\tmpte797ta4'

    def test_impact_analysis_integration(temp_repo):
        """Test impact analysis integration."""
        from cipkg.store import connect
        from cipkg import indexer
        from cipkg.stack.impact import impact
        from cipkg.base import load_config
    
        con = connect(temp_repo)
        cfg = load_config(temp_repo)
    
        # Index first
>       indexer.sync(con, cfg)

tests\test_integration.py:84: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
lib\cipkg\indexer.py:448: in sync
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
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

path = <sqlite3.Connection object at 0x00000191DB055030>, paths = ('.cip',)

>   ???
E   TypeError: expected str, bytes or os.PathLike object, not Connection

<frozen ntpath>:100: TypeError
```

### Suggested Fix
BUG: Type mismatch in operation. Ensure data types are compatible or add type conversion.

---
