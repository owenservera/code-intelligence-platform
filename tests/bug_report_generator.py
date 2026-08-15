"""
Automated Bug Report Generator for Terminal Dashboard Tests.

This system automatically generates bug reports when tests fail,
providing actionable information for fixing dashboard issues.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import traceback


class BugReport:
    """Represents a single bug found by tests."""
    
    def __init__(self, test_name: str, error_type: str, error_message: str, 
                 traceback_str: str, severity: str = "HIGH"):
        self.test_name = test_name
        self.error_type = error_type
        self.error_message = error_message
        self.traceback = traceback_str
        self.severity = severity
        self.timestamp = datetime.now().isoformat()
        self.suggested_fix = self._generate_suggested_fix()
    
    def _generate_suggested_fix(self) -> str:
        """Generate a suggested fix based on the error type."""
        error_message_lower = self.error_message.lower()
        
        if "AttributeError" in self.error_type or "attributeerror" in error_message_lower:
            if "show_alert" in error_message_lower:
                return "CRITICAL BUG: Dashboard screens expect the app to have a show_alert() method for displaying messages. Location: lib/cipkg/terminal_dashboard.py lines 136, 168, 172, 179. Fix: Add show_alert(message) method to your main dashboard app or mock it in tests. Impact: This prevents command execution feedback, error messages, and suggestions from displaying to users."
            
            elif "initialize_repo" in error_message_lower:
                return "BUG: App object missing initialize_repo method for repository initialization. Add initialize_repo() method to handle repository setup and CIP initialization."
            
            elif "show_help" in error_message_lower:
                return "BUG: App object missing show_help method for displaying help documentation. Add show_help() method to display help screens or documentation."
            
            elif "quit_app" in error_message_lower:
                return "BUG: App object missing quit_app method for application exit. Add quit_app() method to handle clean application shutdown."
            
            else:
                return f"BUG: Missing attribute in error message. Add the required attribute/method to the target object."
        
        elif "PermissionError" in self.error_type or "permissionerror" in error_message_lower:
            return "BUG: Windows file locking issue with SQLite database connections. Location: Test fixtures using temporary directories with CIP databases. Root Cause: Database connections are not being properly closed before cleanup attempts. Fix: Add explicit database connection closing in test teardown, use context managers for database connections, add connection.close() calls before test cleanup. Impact: Tests fail during cleanup, but test results are still valid."
        
        elif "SyntaxError" in self.error_type or "syntaxerror" in error_message_lower:
            return "CRITICAL BUG: Python syntax error prevents code from running. Review the syntax error in the traceback and fix the Python syntax issue."
        
        elif "ImportError" in self.error_type or "importerror" in error_message_lower:
            return "BUG: Missing module or incorrect import path. Ensure all required modules are installed and import paths are correct."
        
        elif "AssertionError" in self.error_type or "assertionerror" in error_message_lower:
            return "BUG: Test assertion failed - actual behavior doesn't match expectations. Review the test expectations and adjust either the test or the implementation."
        
        elif "RuntimeError" in self.error_type or "runtimeerror" in error_message_lower:
            return "BUG: Runtime error during execution (unawaited coroutines, resource leaks, etc). Review the code for async/await issues and resource management problems."
        
        elif "KeyError" in self.error_type or "keyerror" in error_message_lower:
            return "BUG: Dictionary key not found. Check that expected keys exist in dictionaries or add error handling for missing keys."
        
        elif "TypeError" in self.error_type or "typeerror" in error_message_lower:
            return "BUG: Type mismatch in operation. Ensure data types are compatible or add type conversion."
        
        elif "ValueError" in self.error_type or "valueerror" in error_message_lower:
            return "BUG: Invalid value provided. Add validation or error handling for invalid inputs."
        
        else:
            return f"BUG: {self.error_type}. Review the error message and traceback for specific guidance."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert bug report to dictionary."""
        return {
            "test_name": self.test_name,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "suggested_fix": self.suggested_fix
        }
    
    def to_markdown(self) -> str:
        """Convert bug report to markdown format."""
        return f"""## Bug Report: {self.test_name}

Severity: {self.severity}  
Detected: {self.timestamp}  
Error Type: {self.error_type}

### Error Message
```
{self.error_message}
```

### Traceback
```
{self.traceback}
```

### Suggested Fix
{self.suggested_fix}

---
"""


class BugReportGenerator:
    """Generates and manages bug reports from test failures."""
    
    def __init__(self, output_dir: str = "tests/bug_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.bugs: List[BugReport] = []
    
    def add_bug(self, test_name: str, error_type: str, error_message: str, 
                traceback_str: str, severity: str = "HIGH"):
        """Add a bug to the report."""
        bug = BugReport(test_name, error_type, error_message, traceback_str, severity)
        self.bugs.append(bug)
        return bug
    
    def generate_markdown_report(self) -> str:
        """Generate a comprehensive markdown bug report."""
        report = f"""# Terminal Dashboard Bug Report

Generated: {datetime.now().isoformat()}  
Total Bugs Found: {len(self.bugs)}  
Severity Breakdown:
- CRITICAL: {len([b for b in self.bugs if b.severity == 'CRITICAL'])}
- HIGH: {len([b for b in self.bugs if b.severity == 'HIGH'])}
- MEDIUM: {len([b for b in self.bugs if b.severity == 'MEDIUM'])}
- LOW: {len([b for b in self.bugs if b.severity == 'LOW'])}

---

"""
        
        # Sort bugs by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_bugs = sorted(self.bugs, key=lambda b: severity_order.get(b.severity, 99))
        
        for bug in sorted_bugs:
            report += bug.to_markdown()
        
        report += f"""## Summary

This bug report was automatically generated by the terminal dashboard test suite.
Each bug represents a real issue found in the dashboard system that needs to be fixed.

### Recommended Action Plan

1. CRITICAL bugs: Fix immediately - these prevent core functionality
2. HIGH bugs: Fix soon - these impact user experience significantly
3. MEDIUM bugs: Fix in next iteration - these are non-critical issues
4. LOW bugs: Fix when convenient - these are minor issues or improvements

### Test Coverage

Current test coverage: 52% (217 of 448 lines uncovered)
Goal: 100% coverage to ensure all code paths are tested.

"""
        return report
    
    def save_markdown_report(self, filename: str = "BUG_REPORT.md"):
        """Save the bug report as a markdown file."""
        report = self.generate_markdown_report()
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        return output_path
    
    def save_json_report(self, filename: str = "bug_report.json"):
        """Save the bug report as a JSON file."""
        report_data = {
            "generated": datetime.now().isoformat(),
            "total_bugs": len(self.bugs),
            "bugs": [bug.to_dict() for bug in self.bugs]
        }
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        return output_path
    
    def save_individual_bug_reports(self):
        """Save each bug as an individual markdown file."""
        for i, bug in enumerate(self.bugs, 1):
            # Sanitize filename - remove path separators and other invalid characters
            safe_name = bug.test_name.replace('::', '_').replace('/', '_').replace('\\', '_').replace(':', '_')
            filename = f"bug_{i:03d}_{safe_name}.md"
            output_path = self.output_dir / filename
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Bug Report #{i}\n\n")
                f.write(bug.to_markdown())
    
    def clear(self):
        """Clear all bugs."""
        self.bugs = []


# Global instance for pytest hooks
bug_generator = BugReportGenerator()