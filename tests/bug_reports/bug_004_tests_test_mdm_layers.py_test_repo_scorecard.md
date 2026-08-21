# Bug Report #4

## Bug Report: tests/test_mdm_layers.py::test_repo_scorecard

Severity: HIGH  
Detected: 2026-08-21T17:33:52.355863  
Error Type: failed

### Error Message
```
tests\test_mdm_layers.py:183: in test_repo_scorecard
    run_mdm_extraction(str(mock_repo))
lib\cipkg\mdm_engine.py:827: in run_mdm_extraction
    l0_res = scan_l0_topology(con, root)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
lib\cipkg\mdm_engine.py:108: in scan_l0_topology
    is_orphan = not is_imported and not is_entry and f["tier"] == "code" and not is_test_path(p, {})
                                                                                 ^^^^^^^^^^^^^^^^^^^
lib\cipkg\base.py:229: in is_test_path
    globs = (cfg or {}).get("index", {}).get("test_globs", DEFAULT_CONFIG["index"]["test_globs"])
                               ^^^^^^^^^^^^
E   KeyError: 'index'
```

### Traceback
```
tests\test_mdm_layers.py:183: in test_repo_scorecard
    run_mdm_extraction(str(mock_repo))
lib\cipkg\mdm_engine.py:827: in run_mdm_extraction
    l0_res = scan_l0_topology(con, root)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
lib\cipkg\mdm_engine.py:108: in scan_l0_topology
    is_orphan = not is_imported and not is_entry and f["tier"] == "code" and not is_test_path(p, {})
                                                                                 ^^^^^^^^^^^^^^^^^^^
lib\cipkg\base.py:229: in is_test_path
    globs = (cfg or {}).get("index", {}).get("test_globs", DEFAULT_CONFIG["index"]["test_globs"])
                               ^^^^^^^^^^^^
E   KeyError: 'index'
```

### Suggested Fix
BUG: Dictionary key not found. Check that expected keys exist in dictionaries or add error handling for missing keys.

---
