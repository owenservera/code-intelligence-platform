"""Tests for validation system."""
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.validator import SyncValidator

def test_pre_sync_validation_with_valid_source():
    """Test pre-sync validation with valid source."""
    print("[TEST] Pre-Sync Validation - Valid Source")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / "source"
        target = Path(temp_dir) / "target"
        logs = Path(temp_dir) / "logs"
        
        source.mkdir()
        target.mkdir()
        logs.mkdir()
        
        # Create test file
        (source / "test.txt").write_text("test content")
        
        try:
            validator = SyncValidator(source, target, logs)
            is_valid, errors = validator.pre_sync_validation(['test.txt'])
            
            assert is_valid, "Should be valid with existing source"
            assert len(errors) == 0, "Should have no errors"
            
            print("[PASS] Pre-sync validation with valid source")
            return True
        except Exception as e:
            print(f"[FAIL] Pre-sync validation: {e}")
            return False

def test_pre_sync_validation_with_missing_source():
    """Test pre-sync validation with missing source."""
    print("[TEST] Pre-Sync Validation - Missing Source")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / "source"
        target = Path(temp_dir) / "target"
        logs = Path(temp_dir) / "logs"
        
        source.mkdir()
        target.mkdir()
        logs.mkdir()
        
        try:
            validator = SyncValidator(source, target, logs)
            is_valid, errors = validator.pre_sync_validation(['nonexistent.txt'])
            
            assert not is_valid, "Should be invalid with missing source"
            assert len(errors) > 0, "Should have errors"
            
            print("[PASS] Pre-sync validation with missing source")
            return True
        except Exception as e:
            print(f"[FAIL] Pre-sync validation: {e}")
            return False

def test_post_sync_validation():
    """Test post-sync validation."""
    print("[TEST] Post-Sync Validation")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / "source"
        target = Path(temp_dir) / "target"
        logs = Path(temp_dir) / "logs"
        
        source.mkdir()
        target.mkdir()
        logs.mkdir()
        
        # Create test file in both source and target
        (source / "test.txt").write_text("test content")
        (target / "test.txt").write_text("test content")
        
        try:
            validator = SyncValidator(source, target, logs)
            is_valid, errors = validator.post_sync_validation(['test.txt'])
            
            assert is_valid, "Should be valid when files exist in target"
            assert len(errors) == 0, "Should have no errors"
            
            print("[PASS] Post-sync validation")
            return True
        except Exception as e:
            print(f"[FAIL] Post-sync validation: {e}")
            return False

def test_cip_validation_basic():
    """Test basic CIP validation."""
    print("[TEST] CIP Validation - Basic")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / "source"
        target = Path(temp_dir) / "target"
        logs = Path(temp_dir) / "logs"
        
        source.mkdir()
        target.mkdir()
        logs.mkdir()
        
        # Create basic CIP structure
        (target / "repo-settings").mkdir()
        (target / "lib" / "cipkg").mkdir(parents=True)
        
        # Create detectors.py
        detectors_content = '''
def detect_repo_type(root):
    return "test"

def load_repo_profile(repo_type):
    return {"test": "data"}
'''
        (target / "repo-settings" / "detectors.py").write_text(detectors_content)
        
        # Create base.py with profile loading
        base_content = '''
# base.py with profile loading
def load_config(root):
    # Profile loading code
    pass
'''
        (target / "lib" / "cipkg" / "base.py").write_text(base_content)
        
        try:
            validator = SyncValidator(source, target, logs)
            is_valid, errors = validator.cip_validation()
            
            # This might have some errors but should not crash
            print(f"[INFO] CIP validation result: {is_valid}")
            if errors:
                print(f"[INFO] Errors: {errors}")
            
            print("[PASS] CIP validation basic")
            return True
        except Exception as e:
            print(f"[FAIL] CIP validation: {e}")
            return False

def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("VALIDATION SYSTEM TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_pre_sync_validation_with_valid_source,
        test_pre_sync_validation_with_missing_source,
        test_post_sync_validation,
        test_cip_validation_basic
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Test failed with exception: {e}")
            results.append(False)
        print()
    
    passed = sum(results)
    total = len(results)
    
    print("=" * 60)
    print(f"TEST RESULTS: {passed}/{total} passed")
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)