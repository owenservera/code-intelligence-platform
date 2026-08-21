# Bug Report #3

## Bug Report: tests/detectors/s3_conformance_test.py::test_s3_recall_f35_registry_handler_imports

Severity: HIGH  
Detected: 2026-08-16T16:50:51.954891  
Error Type: failed

### Error Message
```
def test_s3_recall_f35_registry_handler_imports():
        """F-35/CORE-5: command_registry imports handlers cli.py never defines."""
        ev = _evidence("CODE-MISSING-SYMBOL")
        missing = ("handle_gate_command", "handle_deps_command", "handle_predict_command",
                   "handle_coverage_command", "handle_env_command", "handle_api_command")
        for name in missing:
>           assert any(f"from .cli import {name}" in e for e in ev), name
E           AssertionError: handle_gate_command
E           assert False
E            +  where False = any(<generator object test_s3_recall_f35_registry_handler_imports.<locals>.<genexpr> at 0x000001E6328DF680>)

tests\detectors\s3_conformance_test.py:83: AssertionError
```

### Traceback
```
def test_s3_recall_f35_registry_handler_imports():
        """F-35/CORE-5: command_registry imports handlers cli.py never defines."""
        ev = _evidence("CODE-MISSING-SYMBOL")
        missing = ("handle_gate_command", "handle_deps_command", "handle_predict_command",
                   "handle_coverage_command", "handle_env_command", "handle_api_command")
        for name in missing:
>           assert any(f"from .cli import {name}" in e for e in ev), name
E           AssertionError: handle_gate_command
E           assert False
E            +  where False = any(<generator object test_s3_recall_f35_registry_handler_imports.<locals>.<genexpr> at 0x000001E6328DF680>)

tests\detectors\s3_conformance_test.py:83: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
