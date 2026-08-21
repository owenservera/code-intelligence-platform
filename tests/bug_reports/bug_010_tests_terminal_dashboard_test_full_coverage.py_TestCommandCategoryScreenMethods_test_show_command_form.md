# Bug Report #10

## Bug Report: tests/terminal_dashboard/test_full_coverage.py::TestCommandCategoryScreenMethods::test_show_command_form

Severity: HIGH  
Detected: 2026-08-17T17:43:14.216949  
Error Type: failed

### Error Message
```
tests\terminal_dashboard\test_full_coverage.py:114: in test_show_command_form
    screen._show_command_form(command_cards[0])
lib\cipkg\terminal_dashboard.py:178: in _show_command_form
    self._show_command_result(result)
lib\cipkg\terminal_dashboard.py:187: in _show_command_result
    self._show_alert(f"❌ Command failed: {result.error}")
lib\cipkg\terminal_dashboard.py:158: in _show_alert
    print(f"🔔 {message}")
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\textual\app.py:279: in write
    self.app._print(text, stderr=self.stderr)
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\textual\app.py:2069: in _print
    target_stream.write(text)
E   OSError: [WinError 6] The handle is invalid
```

### Traceback
```
tests\terminal_dashboard\test_full_coverage.py:114: in test_show_command_form
    screen._show_command_form(command_cards[0])
lib\cipkg\terminal_dashboard.py:178: in _show_command_form
    self._show_command_result(result)
lib\cipkg\terminal_dashboard.py:187: in _show_command_result
    self._show_alert(f"❌ Command failed: {result.error}")
lib\cipkg\terminal_dashboard.py:158: in _show_alert
    print(f"🔔 {message}")
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\textual\app.py:279: in write
    self.app._print(text, stderr=self.stderr)
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\textual\app.py:2069: in _print
    target_stream.write(text)
E   OSError: [WinError 6] The handle is invalid
```

### Suggested Fix
BUG: failed. Review the error message and traceback for specific guidance.

---
