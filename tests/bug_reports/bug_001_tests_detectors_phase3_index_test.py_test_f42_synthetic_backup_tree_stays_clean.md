# Bug Report #1

## Bug Report: tests/detectors/phase3_index_test.py::test_f42_synthetic_backup_tree_stays_clean

Severity: HIGH  
Detected: 2026-08-16T04:23:23.084063  
Error Type: failed

### Error Message
```
even_with_empty_config_excludes = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-2/test_f42_synthetic_backup_tree0')

    def test_f42_synthetic_backup_tree_stays_clean(even_with_empty_config_excludes):
        # The tree the OLD scanner indexed (backup copies under sync_global) now
        # must not be picked up by iter_files at all.
        root = pathlib.Path(even_with_empty_config_excludes)
        files = list(base.iter_files(str(root), base.load_config(str(root))))
>       assert files == ["lib/cipkg/base.py"]
E       AssertionError: assert ['config.toml...ipkg/base.py'] == ['lib/cipkg/base.py']
E         
E         At index 0 diff: 'config.toml' != 'lib/cipkg/base.py'
E         Left contains one more item: 'lib/cipkg/base.py'
E         Use -v to get more diff

tests\detectors\phase3_index_test.py:142: AssertionError
```

### Traceback
```
even_with_empty_config_excludes = WindowsPath('C:/Users/VIVIM.inc/AppData/Local/Temp/pytest-of-VIVIM.inc/pytest-2/test_f42_synthetic_backup_tree0')

    def test_f42_synthetic_backup_tree_stays_clean(even_with_empty_config_excludes):
        # The tree the OLD scanner indexed (backup copies under sync_global) now
        # must not be picked up by iter_files at all.
        root = pathlib.Path(even_with_empty_config_excludes)
        files = list(base.iter_files(str(root), base.load_config(str(root))))
>       assert files == ["lib/cipkg/base.py"]
E       AssertionError: assert ['config.toml...ipkg/base.py'] == ['lib/cipkg/base.py']
E         
E         At index 0 diff: 'config.toml' != 'lib/cipkg/base.py'
E         Left contains one more item: 'lib/cipkg/base.py'
E         Use -v to get more diff

tests\detectors\phase3_index_test.py:142: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
