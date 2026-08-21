# Bug Report #2

## Bug Report: tests/detectors/phase3_index_test.py::test_f23_noise_detector_fires_on_broken_edges

Severity: HIGH  
Detected: 2026-08-16T04:22:21.118020  
Error Type: failed

### Error Message
```
def test_f23_noise_detector_fires_on_broken_edges():
        # RECALL: the old heuristic emitted tested_by edges from backup-symbol
        # srcs and from src ids that no longer exist — the detector must count them.
        con = _make_db(
            edges=[("python://sync_global/backups/bak/x.py#f", "tests/test_x.py", "tested_by",
                    "sync_global/backups/bak/x.py"),
                   ("python://lib/legacy.py#g", "tests/test_y.py", "tested_by", "lib/legacy.py"),
                   ("python://lost.py#h", "tests/test_z.py", "tested_by", "backup_lost.py"),
                   ("python://lib/real.py#f", "tests/test_r.py", "tested_by", "lib/real.py")],
            symbols=[("python://sync_global/backups/bak/x.py#f", "sync_global/backups/bak/x.py"),
                     ("python://lib/legacy.py#g", "lib/legacy.py"),
                     ("python://lib/real.py#f", "lib/real.py")])
        noisy, total = tested_by_noise(con)
        assert total == 4
>       assert noisy >= 3                       # 2 backup src_path + 1 missing src
        ^^^^^^^^^^^^^^^^^
E       assert 2 >= 3

tests\detectors\phase3_index_test.py:194: AssertionError
```

### Traceback
```
def test_f23_noise_detector_fires_on_broken_edges():
        # RECALL: the old heuristic emitted tested_by edges from backup-symbol
        # srcs and from src ids that no longer exist — the detector must count them.
        con = _make_db(
            edges=[("python://sync_global/backups/bak/x.py#f", "tests/test_x.py", "tested_by",
                    "sync_global/backups/bak/x.py"),
                   ("python://lib/legacy.py#g", "tests/test_y.py", "tested_by", "lib/legacy.py"),
                   ("python://lost.py#h", "tests/test_z.py", "tested_by", "backup_lost.py"),
                   ("python://lib/real.py#f", "tests/test_r.py", "tested_by", "lib/real.py")],
            symbols=[("python://sync_global/backups/bak/x.py#f", "sync_global/backups/bak/x.py"),
                     ("python://lib/legacy.py#g", "lib/legacy.py"),
                     ("python://lib/real.py#f", "lib/real.py")])
        noisy, total = tested_by_noise(con)
        assert total == 4
>       assert noisy >= 3                       # 2 backup src_path + 1 missing src
        ^^^^^^^^^^^^^^^^^
E       assert 2 >= 3

tests\detectors\phase3_index_test.py:194: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
