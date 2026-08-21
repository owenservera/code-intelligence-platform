# Bug Report #1

## Bug Report: tests/test_mdm_layers.py::test_l0_topology_extraction

Severity: HIGH  
Detected: 2026-08-21T17:32:45.902940  
Error Type: failed

### Error Message
```
tests\test_mdm_layers.py:126: in test_l0_topology_extraction
    res = scan_l0_topology(con, str(mock_repo))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
lib\cipkg\mdm_engine.py:108: in scan_l0_topology
    is_orphan = not is_imported and not is_entry and f["tier"] == "code" and not is_test_path(p, {})
                                                                                 ^^^^^^^^^^^^^^^^^^^
lib\cipkg\base.py:229: in is_test_path
    return any(m in p for m in cfg["index"]["test_globs"])
                               ^^^^^^^^^^^^
E   KeyError: 'index'
```

### Traceback
```
tests\test_mdm_layers.py:126: in test_l0_topology_extraction
    res = scan_l0_topology(con, str(mock_repo))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
lib\cipkg\mdm_engine.py:108: in scan_l0_topology
    is_orphan = not is_imported and not is_entry and f["tier"] == "code" and not is_test_path(p, {})
                                                                                 ^^^^^^^^^^^^^^^^^^^
lib\cipkg\base.py:229: in is_test_path
    return any(m in p for m in cfg["index"]["test_globs"])
                               ^^^^^^^^^^^^
E   KeyError: 'index'
```

### Suggested Fix
BUG: Dictionary key not found. Check that expected keys exist in dictionaries or add error handling for missing keys.

---
