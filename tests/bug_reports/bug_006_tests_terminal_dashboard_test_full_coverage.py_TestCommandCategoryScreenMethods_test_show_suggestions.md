# Bug Report #6

## Bug Report: tests/terminal_dashboard/test_full_coverage.py::TestCommandCategoryScreenMethods::test_show_suggestions

Severity: CRITICAL  
Detected: 2026-08-15T19:53:36.174759  
Error Type: failed

### Error Message
```
E   AttributeError: 'TestApp' object has no attribute 'show_alert'
```

### Traceback
```
E   AttributeError: 'TestApp' object has no attribute 'show_alert'
```

### Suggested Fix
CRITICAL BUG: Dashboard screens expect the app to have a show_alert() method for displaying messages. Location: lib/cipkg/terminal_dashboard.py lines 136, 168, 172, 179. Fix: Add show_alert(message) method to your main dashboard app or mock it in tests. Impact: This prevents command execution feedback, error messages, and suggestions from displaying to users.

---
