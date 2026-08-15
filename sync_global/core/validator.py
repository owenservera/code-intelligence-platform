"""Validation system for CIP sync operations."""
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

class SyncValidator:
    """Validation system for sync operations."""
    
    def __init__(self, source_dir: Path, target_dir: Path, log_dir: Path):
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.log_dir = log_dir
        
    def pre_sync_validation(self, items: List[str]) -> Tuple[bool, List[str]]:
        """Run pre-sync validation checks."""
        errors = []
        
        # Check source files exist
        for item in items:
            source_path = self.source_dir / item
            if not source_path.exists():
                errors.append(f"Source does not exist: {item}")
        
        # Check target directory is accessible
        if not self.target_dir.parent.exists():
            errors.append(f"Target parent directory does not exist: {self.target_dir.parent}")
        
        # Check write permissions
        try:
            test_file = self.target_dir.parent / ".sync_test"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            errors.append(f"No write permission to target directory: {e}")
        
        is_valid = len(errors) == 0
        self.log_validation("PRE_SYNC", is_valid, errors)
        return is_valid, errors
    
    def post_sync_validation(self, items: List[str]) -> Tuple[bool, List[str]]:
        """Run post-sync validation checks."""
        errors = []
        
        # Check files were copied correctly
        for item in items:
            target_path = self.target_dir / item
            if not target_path.exists():
                errors.append(f"Target was not created: {item}")
        
        is_valid = len(errors) == 0
        self.log_validation("POST_SYNC", is_valid, errors)
        return is_valid, errors
    
    def cip_validation(self) -> Tuple[bool, List[str]]:
        """Run CIP-specific validation tests."""
        errors = []
        
        # Test 1: Repo detection (using synced detectors)
        try:
            import sys
            repo_settings_path = self.target_dir / "repo-settings"
            if repo_settings_path.exists():
                sys.path.insert(0, str(repo_settings_path))
                from detectors import detect_repo_type, load_repo_profile
                
                test_dir = Path.cwd()
                repo_type = detect_repo_type(str(test_dir))
                if not repo_type:
                    errors.append("Repo detection returned empty")
                
                # Test profile loading
                profile = load_repo_profile("index")
                if not profile:
                    errors.append("Profile loading returned empty")
            else:
                errors.append("repo-settings not found in target")
        except Exception as e:
            errors.append(f"Repo detection error: {e}")
        
        # Test 2: Check base.py has profile loading
        try:
            base_py = self.target_dir / "lib" / "cipkg" / "base.py"
            if base_py.exists():
                content = base_py.read_text()
                if "detect_repo_type" not in content:
                    errors.append("base.py missing profile loading functionality")
            else:
                errors.append("base.py not found in target")
        except Exception as e:
            errors.append(f"base.py check error: {e}")
        
        is_valid = len(errors) == 0
        self.log_validation("CIP_VALIDATION", is_valid, errors)
        return is_valid, errors
    
    def log_validation(self, phase: str, is_valid: bool, errors: List[str]):
        """Log validation results."""
        timestamp = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "PASSED" if is_valid else "FAILED"
        
        with open(self.log_dir / "validation.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {phase}: {status}\n")
            for error in errors:
                f.write(f"  ERROR: {error}\n")
        
        print(f"[VALIDATION] {phase}: {status}")
        for error in errors:
            print(f"  ERROR: {error}")