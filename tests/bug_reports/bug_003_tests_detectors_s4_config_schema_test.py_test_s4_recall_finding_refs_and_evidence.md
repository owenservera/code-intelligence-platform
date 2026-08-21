# Bug Report #3

## Bug Report: tests/detectors/s4_config_schema_test.py::test_s4_recall_finding_refs_and_evidence

Severity: HIGH  
Detected: 2026-08-17T17:42:57.119676  
Error Type: failed

### Error Message
```
tests\detectors\s4_config_schema_test.py:68: in test_s4_recall_finding_refs_and_evidence
    assert rule in by_rule, rule
E   AssertionError: CONFIG-FILE-UNPARSEABLE
E   assert 'CONFIG-FILE-UNPARSEABLE' in {'CONFIG-KEY-DRIFT': {'evidence': 'config.default.toml [index].max_file_size; base.py/indexer.py read max_file_kb', 'finding_ref': 'CORE-39', 'recommendation': 'rename/map the key so excludes + size caps actually apply', 'rule': 'CONFIG-KEY-DRIFT', ...}, 'CONFIG-KEY-UNUSED': {'evidence': "config.default.toml [performance] vs indexer.py cfg['perf']['workers']", 'finding_ref': 'CORE-42', 'recommendation': 'collapse to one section; mark legacy keys deprecated', 'rule': 'CONFIG-KEY-UNUSED', ...}, 'CONFIG-PORT-MISMATCH': {'evidence': 'config.default.toml [daemon].port=8765; code defaults [8787]', 'finding_ref': 'CORE-10', 'recommendation': 'pick one port truth across config + daemon.py + command_registry', 'rule': 'CONFIG-PORT-MISMATCH', ...}, 'CONFIG-PROFILE-SILENT-FAIL': {'evidence': 'repo-settings/detectors.py exists at root but load_config looks at lib/repo-settings (missing); profile={}', 'finding_ref': 'F-11', 'recommendation': 'resolve repo-settings from repo root and align all 3 import sites', 'rule': 'CONFIG-PROFILE-SILENT-FAIL', ...}, ...}
```

### Traceback
```
tests\detectors\s4_config_schema_test.py:68: in test_s4_recall_finding_refs_and_evidence
    assert rule in by_rule, rule
E   AssertionError: CONFIG-FILE-UNPARSEABLE
E   assert 'CONFIG-FILE-UNPARSEABLE' in {'CONFIG-KEY-DRIFT': {'evidence': 'config.default.toml [index].max_file_size; base.py/indexer.py read max_file_kb', 'finding_ref': 'CORE-39', 'recommendation': 'rename/map the key so excludes + size caps actually apply', 'rule': 'CONFIG-KEY-DRIFT', ...}, 'CONFIG-KEY-UNUSED': {'evidence': "config.default.toml [performance] vs indexer.py cfg['perf']['workers']", 'finding_ref': 'CORE-42', 'recommendation': 'collapse to one section; mark legacy keys deprecated', 'rule': 'CONFIG-KEY-UNUSED', ...}, 'CONFIG-PORT-MISMATCH': {'evidence': 'config.default.toml [daemon].port=8765; code defaults [8787]', 'finding_ref': 'CORE-10', 'recommendation': 'pick one port truth across config + daemon.py + command_registry', 'rule': 'CONFIG-PORT-MISMATCH', ...}, 'CONFIG-PROFILE-SILENT-FAIL': {'evidence': 'repo-settings/detectors.py exists at root but load_config looks at lib/repo-settings (missing); profile={}', 'finding_ref': 'F-11', 'recommendation': 'resolve repo-settings from repo root and align all 3 import sites', 'rule': 'CONFIG-PROFILE-SILENT-FAIL', ...}, ...}
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
