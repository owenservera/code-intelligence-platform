# Bug Report #2

## Bug Report: tests/terminal_dashboard/test_snapshots.py::test_index_needed_screen_snapshot

Severity: HIGH  
Detected: 2026-08-16T17:34:06.792703  
Error Type: failed

### Error Message
```
snap_compare = <function snap_compare.<locals>.compare at 0x00000191DAA7B3D0>

    @pytest.mark.snapshot
    def test_index_needed_screen_snapshot(snap_compare):
        """Test IndexNeededScreen visual appearance."""
        import tempfile
        tmpdir = tempfile.mkdtemp()
    
        screen = IndexNeededScreen(tmpdir, DashboardState.INDEX_NEEDED)
    
        class TestApp(App):
            def compose(self):
                yield screen
    
        app = TestApp()
>       assert snap_compare(app)
E       AssertionError: assert False
E        +  where False = <function snap_compare.<locals>.compare at 0x00000191DAA7B3D0>(TestApp(title='TestApp', classes={'-dark-mode'}, pseudo_classes={'focus', 'dark'}))

tests\terminal_dashboard\test_snapshots.py:50: AssertionError
```

### Traceback
```
snap_compare = <function snap_compare.<locals>.compare at 0x00000191DAA7B3D0>

    @pytest.mark.snapshot
    def test_index_needed_screen_snapshot(snap_compare):
        """Test IndexNeededScreen visual appearance."""
        import tempfile
        tmpdir = tempfile.mkdtemp()
    
        screen = IndexNeededScreen(tmpdir, DashboardState.INDEX_NEEDED)
    
        class TestApp(App):
            def compose(self):
                yield screen
    
        app = TestApp()
>       assert snap_compare(app)
E       AssertionError: assert False
E        +  where False = <function snap_compare.<locals>.compare at 0x00000191DAA7B3D0>(TestApp(title='TestApp', classes={'-dark-mode'}, pseudo_classes={'focus', 'dark'}))

tests\terminal_dashboard\test_snapshots.py:50: AssertionError
```

### Suggested Fix
BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation.

---
