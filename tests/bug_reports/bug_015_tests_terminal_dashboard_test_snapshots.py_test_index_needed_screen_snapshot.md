# Bug Report #15

## Bug Report: tests/terminal_dashboard/test_snapshots.py::test_index_needed_screen_snapshot

Severity: HIGH  
Detected: 2026-08-17T17:43:35.877115  
Error Type: failed

### Error Message
```
tests\terminal_dashboard\test_snapshots.py:50: in test_index_needed_screen_snapshot
    assert snap_compare(app)
E   AssertionError: assert False
E    +  where False = <function snap_compare.<locals>.compare at 0x00000204CB9AA1F0>(TestApp(title='TestApp', classes={'-dark-mode'}, pseudo_classes={'dark', 'focus'}))
```

### Traceback
```
tests\terminal_dashboard\test_snapshots.py:50: in test_index_needed_screen_snapshot
    assert snap_compare(app)
E   AssertionError: assert False
E    +  where False = <function snap_compare.<locals>.compare at 0x00000204CB9AA1F0>(TestApp(title='TestApp', classes={'-dark-mode'}, pseudo_classes={'dark', 'focus'}))
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
