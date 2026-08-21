# Bug Report #5

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
