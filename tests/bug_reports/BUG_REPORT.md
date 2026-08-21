# Terminal Dashboard Bug Report

Generated: 2026-08-21T17:34:02.462381  
Total Bugs Found: 5  
Severity Breakdown:
- CRITICAL: 0
- HIGH: 5
- MEDIUM: 0
- LOW: 0

---

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
## Bug Report: tests/test_mdm_layers.py::test_la_synthesis_and_explainability_trace

Severity: HIGH  
Detected: 2026-08-21T17:33:52.187547  
Error Type: failed

### Error Message
```
tests\test_mdm_layers.py:167: in test_la_synthesis_and_explainability_trace
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
tests\test_mdm_layers.py:167: in test_la_synthesis_and_explainability_trace
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
## Bug Report: tests/test_mdm_layers.py::test_full_report_generation_and_markdown

Severity: HIGH  
Detected: 2026-08-21T17:33:52.548117  
Error Type: failed

### Error Message
```
tests\test_mdm_layers.py:196: in test_full_report_generation_and_markdown
    rep = generate_full_mdm_report(str(mock_repo))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
lib\cipkg\mdm_synthesis.py:296: in generate_full_mdm_report
    ext_res = run_mdm_extraction(root)
              ^^^^^^^^^^^^^^^^^^^^^^^^
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
tests\test_mdm_layers.py:196: in test_full_report_generation_and_markdown
    rep = generate_full_mdm_report(str(mock_repo))
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
lib\cipkg\mdm_synthesis.py:296: in generate_full_mdm_report
    ext_res = run_mdm_extraction(root)
              ^^^^^^^^^^^^^^^^^^^^^^^^
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
## Summary

This bug report was automatically generated by the terminal dashboard test suite.
Each bug represents a real issue found in the dashboard system that needs to be fixed.

### Recommended Action Plan

1. CRITICAL bugs: Fix immediately - these prevent core functionality
2. HIGH bugs: Fix soon - these impact user experience significantly
3. MEDIUM bugs: Fix in next iteration - these are non-critical issues
4. LOW bugs: Fix when convenient - these are minor issues or improvements

### Test Coverage

Current test coverage: 52% (217 of 448 lines uncovered)
Goal: 100% coverage to ensure all code paths are tested.

