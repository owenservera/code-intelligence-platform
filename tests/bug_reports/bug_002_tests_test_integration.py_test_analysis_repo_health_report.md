# Bug Report #2

## Bug Report: tests/test_integration.py::test_analysis_repo_health_report

Severity: HIGH  
Detected: 2026-08-18T17:07:13.344408  
Error Type: failed

### Error Message
```
tests\test_integration.py:303: in test_analysis_repo_health_report
    assert 'health_score' in report, "Report should contain health_score"
E   AssertionError: Report should contain health_score
E   assert 'health_score' in {'critical_issues': [], 'high_priority': [], 'hotspots': [{'path': 'test_module.py', 'symbols': 3, 'type': 'dense'}, {'dependents': 2, 'path': 'test_module.py', 'symbol': 'greet', 'type': 'load_bearing'}, {'dependents': 1, 'path': 'test_module.py', 'symbol': 'hello_world', 'type': 'load_bearing'}, {'dependents': 1, 'path': 'test_module.py', 'symbol': 'Greeter', 'type': 'load_bearing'}], 'overall_score': 60.0, ...}
```

### Traceback
```
tests\test_integration.py:303: in test_analysis_repo_health_report
    assert 'health_score' in report, "Report should contain health_score"
E   AssertionError: Report should contain health_score
E   assert 'health_score' in {'critical_issues': [], 'high_priority': [], 'hotspots': [{'path': 'test_module.py', 'symbols': 3, 'type': 'dense'}, {'dependents': 2, 'path': 'test_module.py', 'symbol': 'greet', 'type': 'load_bearing'}, {'dependents': 1, 'path': 'test_module.py', 'symbol': 'hello_world', 'type': 'load_bearing'}, {'dependents': 1, 'path': 'test_module.py', 'symbol': 'Greeter', 'type': 'load_bearing'}], 'overall_score': 60.0, ...}
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
