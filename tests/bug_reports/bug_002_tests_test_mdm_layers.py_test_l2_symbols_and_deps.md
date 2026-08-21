# Bug Report #2

## Bug Report: tests/test_mdm_layers.py::test_l2_symbols_and_deps

Severity: HIGH  
Detected: 2026-08-21T17:33:51.790851  
Error Type: failed

### Error Message
```
tests\test_mdm_layers.py:144: in test_l2_symbols_and_deps
    res = scan_l2_symbols_and_deps(con, str(mock_repo))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
lib\cipkg\mdm_engine.py:252: in scan_l2_symbols_and_deps
    cycle_res = gapfill.circular(root)
                ^^^^^^^^^^^^^^^^^^^^^^
lib\cipkg\gapfill.py:168: in circular
    con = _con(root)
          ^^^^^^^^^^
lib\cipkg\gapfill.py:20: in _con
    return connect(root or repo_root())
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
lib\cipkg\store.py:112: in connect
    con.execute("INSERT INTO meta(key,value) VALUES('schema_version',?) "
E   sqlite3.OperationalError: database is locked
```

### Traceback
```
tests\test_mdm_layers.py:144: in test_l2_symbols_and_deps
    res = scan_l2_symbols_and_deps(con, str(mock_repo))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
lib\cipkg\mdm_engine.py:252: in scan_l2_symbols_and_deps
    cycle_res = gapfill.circular(root)
                ^^^^^^^^^^^^^^^^^^^^^^
lib\cipkg\gapfill.py:168: in circular
    con = _con(root)
          ^^^^^^^^^^
lib\cipkg\gapfill.py:20: in _con
    return connect(root or repo_root())
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
lib\cipkg\store.py:112: in connect
    con.execute("INSERT INTO meta(key,value) VALUES('schema_version',?) "
E   sqlite3.OperationalError: database is locked
```

### Suggested Fix
BUG: failed. Review the error message and traceback for specific guidance.

---
