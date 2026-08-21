# Bug Report #2

## Bug Report: tests/detectors/s5_doctor_skeleton_test.py::test_s5_runtime_only_reports_measured_state

Severity: MEDIUM  
Detected: 2026-08-16T03:09:27.039030  
Error Type: failed

### Error Message
```
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\shutil.py:701: in _rmtree_unsafe
    os.unlink(fullname)
E   PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\tmprz229wts\\.cip\\data\\index.db'

During handling of the above exception, another exception occurred:
tests\detectors\s5_doctor_skeleton_test.py:109: in test_s5_runtime_only_reports_measured_state
    with tempfile.TemporaryDirectory() as tmp:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\tempfile.py:971: in __exit__
    self.cleanup()
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\tempfile.py:975: in cleanup
    self._rmtree(self.name, ignore_errors=self._ignore_cleanup_errors)
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\tempfile.py:955: in _rmtree
    _shutil.rmtree(name, onexc=onexc)
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\shutil.py:852: in rmtree
    _rmtree_impl(path, dir_fd, onexc)
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\shutil.py:705: in _rmtree_unsafe
    onexc(os.unlink, fullname, err)
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\tempfile.py:930: in onexc
    _os.unlink(path)
E   PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\tmprz229wts\\.cip\\data\\index.db'
```

### Traceback
```
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\shutil.py:701: in _rmtree_unsafe
    os.unlink(fullname)
E   PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\tmprz229wts\\.cip\\data\\index.db'

During handling of the above exception, another exception occurred:
tests\detectors\s5_doctor_skeleton_test.py:109: in test_s5_runtime_only_reports_measured_state
    with tempfile.TemporaryDirectory() as tmp:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\tempfile.py:971: in __exit__
    self.cleanup()
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\tempfile.py:975: in cleanup
    self._rmtree(self.name, ignore_errors=self._ignore_cleanup_errors)
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\tempfile.py:955: in _rmtree
    _shutil.rmtree(name, onexc=onexc)
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\shutil.py:852: in rmtree
    _rmtree_impl(path, dir_fd, onexc)
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\shutil.py:705: in _rmtree_unsafe
    onexc(os.unlink, fullname, err)
C:\Users\VIVIM.inc\AppData\Local\Python\pythoncore-3.14-64\Lib\tempfile.py:930: in onexc
    _os.unlink(path)
E   PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: 'C:\\Users\\VIVIM.inc\\AppData\\Local\\Temp\\tmprz229wts\\.cip\\data\\index.db'
```

### Suggested Fix
BUG: Windows file locking issue with SQLite database connections. Location: Test fixtures using temporary directories with CIP databases. Root Cause: Database connections are not being properly closed before cleanup attempts. Fix: Add explicit database connection closing in test teardown, use context managers for database connections, add connection.close() calls before test cleanup. Impact: Tests fail during cleanup, but test results are still valid.

---
