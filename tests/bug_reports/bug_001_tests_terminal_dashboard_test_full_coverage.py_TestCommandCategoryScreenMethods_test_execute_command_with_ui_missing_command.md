# Bug Report #1

## Bug Report: tests/terminal_dashboard/test_full_coverage.py::TestCommandCategoryScreenMethods::test_execute_command_with_ui_missing_command

Severity: CRITICAL  
Detected: 2026-08-15T19:58:09.990995  
Error Type: failed

### Error Message
```
tests\terminal_dashboard\test_full_coverage.py:55: in test_execute_command_with_ui_missing_command
    screen._execute_command_with_ui("nonexistent_command")
lib\cipkg\terminal_dashboard.py:136: in _execute_command_with_ui
    self.app.show_alert(f"Command not found: {command}")
    ^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'TestApp' object has no attribute 'show_alert'
```

### Traceback
```
tests\terminal_dashboard\test_full_coverage.py:55: in test_execute_command_with_ui_missing_command
    screen._execute_command_with_ui("nonexistent_command")
lib\cipkg\terminal_dashboard.py:136: in _execute_command_with_ui
    self.app.show_alert(f"Command not found: {command}")
    ^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'TestApp' object has no attribute 'show_alert'
```

### Suggested Fix
CRITICAL BUG: Dashboard screens expect the app to have a show_alert() method for displaying messages. Location: lib/cipkg/terminal_dashboard.py lines 136, 168, 172, 179. Fix: Add show_alert(message) method to your main dashboard app or mock it in tests. Impact: This prevents command execution feedback, error messages, and suggestions from displaying to users.

---
