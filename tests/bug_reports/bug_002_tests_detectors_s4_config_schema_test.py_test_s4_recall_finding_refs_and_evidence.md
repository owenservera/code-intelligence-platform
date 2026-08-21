# Bug Report #2

## Bug Report: tests/detectors/s4_config_schema_test.py::test_s4_recall_finding_refs_and_evidence

Severity: HIGH  
Detected: 2026-08-21T16:59:26.551055  
Error Type: failed

### Error Message
```
tests\detectors\s4_config_schema_test.py:68: in test_s4_recall_finding_refs_and_evidence
    assert rule in by_rule, rule
E   AssertionError: CONFIG-FILE-UNPARSEABLE
E   assert 'CONFIG-FILE-UNPARSEABLE' in {'CONFIG-PORT-MISMATCH': {'rule': 'CONFIG-PORT-MISMATCH', 'finding_ref': 'CORE-10', 'severity': 'P2', 'title': 'daemon port disagrees with code default', 'evidence': 'config.default.toml [daemon].port=8765; code defaults [8787]', 'recommendation': 'pick one port truth across config + daemon.py + command_registry'}, 'CONFIG-SCHEMA-DRIFT': {'rule': 'CONFIG-SCHEMA-DRIFT', 'finding_ref': 'CORE-40', 'severity': 'P1', 'title': 'declared schema_version differs from store', 'evidence': 'config.default.toml [meta].schema_version=11 vs store.SCHEMA_VERSION=4', 'recommendation': 'set config schema_version to the live value or migrate'}, 'CONFIG-KEY-DRIFT': {'rule': 'CONFIG-KEY-DRIFT', 'finding_ref': 'CORE-39', 'severity': 'P1', 'title': 'index.max_file_size is ignored; core reads index.max_file_kb', 'evidence': 'config.default.toml [index].max_file_size; base.py/indexer.py read max_file_kb', 'recommendation': 'rename/map the key so excludes + size caps actually apply'}, 'CONFIG-KEY-UNUSED': {'rule': 'CONFIG-KEY-UNUSED', 'finding_ref': 'CORE-42', 'severity': 'P3', 'title': '[performance] declared but core reads [perf]', 'evidence': "config.default.toml [performance] vs indexer.py cfg['perf']['workers']", 'recommendation': 'collapse to one section; mark legacy keys deprecated'}, 'CONFIG-PROFILE-SILENT-FAIL': {'rule': 'CONFIG-PROFILE-SILENT-FAIL', 'finding_ref': 'F-11', 'severity': 'P1', 'title': 'repo-settings profiles never load', 'evidence': 'repo-settings/detectors.py exists at root but load_config looks at lib/repo-settings (missing); profile={}', 'recommendation': 'resolve repo-settings from repo root and align all 3 import sites'}}
```

### Traceback
```
tests\detectors\s4_config_schema_test.py:68: in test_s4_recall_finding_refs_and_evidence
    assert rule in by_rule, rule
E   AssertionError: CONFIG-FILE-UNPARSEABLE
E   assert 'CONFIG-FILE-UNPARSEABLE' in {'CONFIG-PORT-MISMATCH': {'rule': 'CONFIG-PORT-MISMATCH', 'finding_ref': 'CORE-10', 'severity': 'P2', 'title': 'daemon port disagrees with code default', 'evidence': 'config.default.toml [daemon].port=8765; code defaults [8787]', 'recommendation': 'pick one port truth across config + daemon.py + command_registry'}, 'CONFIG-SCHEMA-DRIFT': {'rule': 'CONFIG-SCHEMA-DRIFT', 'finding_ref': 'CORE-40', 'severity': 'P1', 'title': 'declared schema_version differs from store', 'evidence': 'config.default.toml [meta].schema_version=11 vs store.SCHEMA_VERSION=4', 'recommendation': 'set config schema_version to the live value or migrate'}, 'CONFIG-KEY-DRIFT': {'rule': 'CONFIG-KEY-DRIFT', 'finding_ref': 'CORE-39', 'severity': 'P1', 'title': 'index.max_file_size is ignored; core reads index.max_file_kb', 'evidence': 'config.default.toml [index].max_file_size; base.py/indexer.py read max_file_kb', 'recommendation': 'rename/map the key so excludes + size caps actually apply'}, 'CONFIG-KEY-UNUSED': {'rule': 'CONFIG-KEY-UNUSED', 'finding_ref': 'CORE-42', 'severity': 'P3', 'title': '[performance] declared but core reads [perf]', 'evidence': "config.default.toml [performance] vs indexer.py cfg['perf']['workers']", 'recommendation': 'collapse to one section; mark legacy keys deprecated'}, 'CONFIG-PROFILE-SILENT-FAIL': {'rule': 'CONFIG-PROFILE-SILENT-FAIL', 'finding_ref': 'F-11', 'severity': 'P1', 'title': 'repo-settings profiles never load', 'evidence': 'repo-settings/detectors.py exists at root but load_config looks at lib/repo-settings (missing); profile={}', 'recommendation': 'resolve repo-settings from repo root and align all 3 import sites'}}
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
