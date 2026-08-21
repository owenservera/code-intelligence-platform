# Bug Report #1

## Bug Report: tests/test_integration.py::test_analysis_repo_health_report

Severity: HIGH  
Detected: 2026-08-21T17:01:05.832481  
Error Type: failed

### Error Message
```
tests\test_integration.py:303: in test_analysis_repo_health_report
    assert 'health_score' in report, "Report should contain health_score"
E   AssertionError: Report should contain health_score
E   assert 'health_score' in {'overall_score': 60.0, 'critical_issues': [], 'high_priority': [], 'test_coverage': {'coverage_files': [], 'framework_signals': {'coverageThreshold': 0, 'toMatchSnapshot': 0, 'jest': 0, 'vitest': 0, 'pytest': 0, '.test.': 0, '.spec.': 0, 'describe(': 0, 'it(': 0}, 'actual_coverage': {'total_symbols': 3, 'tested_symbols': 0, 'coverage_pct': 0.0}, 'untested_load_bearing': [], 'unit_test_ratio_hint': 0, 'note': 'Enhanced with tested_by edge analysis for actual coverage'}, 'technical_debt': {'test_debt': [], 'complexity_debt': [], 'duplication_debt': [], 'documentation_debt': []}, 'hotspots': [{'path': 'test_module.py', 'symbols': 3, 'type': 'dense'}, {'symbol': 'greet', 'path': 'test_module.py', 'dependents': 2, 'type': 'load_bearing'}, {'symbol': 'hello_world', 'path': 'test_module.py', 'dependents': 1, 'type': 'load_bearing'}, {'symbol': 'Greeter', 'path': 'test_module.py', 'dependents': 1, 'type': 'load_bearing'}], 'recommendations': []}
```

### Traceback
```
tests\test_integration.py:303: in test_analysis_repo_health_report
    assert 'health_score' in report, "Report should contain health_score"
E   AssertionError: Report should contain health_score
E   assert 'health_score' in {'overall_score': 60.0, 'critical_issues': [], 'high_priority': [], 'test_coverage': {'coverage_files': [], 'framework_signals': {'coverageThreshold': 0, 'toMatchSnapshot': 0, 'jest': 0, 'vitest': 0, 'pytest': 0, '.test.': 0, '.spec.': 0, 'describe(': 0, 'it(': 0}, 'actual_coverage': {'total_symbols': 3, 'tested_symbols': 0, 'coverage_pct': 0.0}, 'untested_load_bearing': [], 'unit_test_ratio_hint': 0, 'note': 'Enhanced with tested_by edge analysis for actual coverage'}, 'technical_debt': {'test_debt': [], 'complexity_debt': [], 'duplication_debt': [], 'documentation_debt': []}, 'hotspots': [{'path': 'test_module.py', 'symbols': 3, 'type': 'dense'}, {'symbol': 'greet', 'path': 'test_module.py', 'dependents': 2, 'type': 'load_bearing'}, {'symbol': 'hello_world', 'path': 'test_module.py', 'dependents': 1, 'type': 'load_bearing'}, {'symbol': 'Greeter', 'path': 'test_module.py', 'dependents': 1, 'type': 'load_bearing'}], 'recommendations': []}
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
