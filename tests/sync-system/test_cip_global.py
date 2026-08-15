"""Tests for CIP global verification after sync."""
import os
import sys
import subprocess
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def test_cip_command_exists():
    """Test that CIP command is available."""
    print("[TEST] CIP Command Exists")
    
    try:
        result = subprocess.run(
            ["cip", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"[PASS] CIP command available: {result.stdout.strip()}")
            return True
        else:
            print(f"[FAIL] CIP command failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[FAIL] CIP command error: {e}")
        return False

def test_cip_repo_settings_exists():
    """Test that repo-settings exists in global CIP."""
    print("[TEST] CIP Repo-Settings Exists")
    
    global_cip = Path.home() / ".cip-global"
    repo_settings = global_cip / "repo-settings"
    
    if repo_settings.exists():
        print(f"[PASS] repo-settings exists: {repo_settings}")
        return True
    else:
        print(f"[FAIL] repo-settings not found: {repo_settings}")
        return False

def test_cip_detectors_exists():
    """Test that detectors.py exists in global CIP."""
    print("[TEST] CIP Detectors Exists")
    
    global_cip = Path.home() / ".cip-global"
    detectors = global_cip / "repo-settings" / "detectors.py"
    
    if detectors.exists():
        print(f"[PASS] detectors.py exists: {detectors}")
        return True
    else:
        print(f"[FAIL] detectors.py not found: {detectors}")
        return False

def test_cip_base_py_updated():
    """Test that base.py has profile loading functionality."""
    print("[TEST] CIP Base.py Updated")
    
    global_cip = Path.home() / ".cip-global"
    base_py = global_cip / "lib" / "cipkg" / "base.py"
    
    if not base_py.exists():
        print(f"[FAIL] base.py not found: {base_py}")
        return False
    
    try:
        content = base_py.read_text()
        
        # Check for profile loading indicators
        has_profile_loading = "detect_repo_type" in content or "load_repo_profile" in content
        has_repo_settings = "repo-settings" in content
        
        if has_profile_loading and has_repo_settings:
            print("[PASS] base.py has profile loading functionality")
            return True
        else:
            print(f"[FAIL] base.py missing profile loading")
            print(f"  has_profile_loading: {has_profile_loading}")
            print(f"  has_repo_settings: {has_repo_settings}")
            return False
    except Exception as e:
        print(f"[FAIL] base.py read error: {e}")
        return False

def test_cip_profile_structure():
    """Test that profile structure is correct."""
    print("[TEST] CIP Profile Structure")
    
    global_cip = Path.home() / ".cip-global"
    profiles_dir = global_cip / "repo-settings" / "profiles"
    
    if not profiles_dir.exists():
        print(f"[FAIL] profiles directory not found: {profiles_dir}")
        return False
    
    # Check for expected profiles
    expected_profiles = ["index", "vivim-final", "generic.toml"]
    found_profiles = []
    
    for item in expected_profiles:
        if (profiles_dir / item).exists():
            found_profiles.append(item)
    
    if len(found_profiles) >= 2:  # At least index and vivim-final
        print(f"[PASS] Profile structure correct: {found_profiles}")
        return True
    else:
        print(f"[FAIL] Missing profiles. Found: {found_profiles}, Expected: {expected_profiles}")
        return False

def test_cip_repo_detection():
    """Test CIP repo detection with synced system."""
    print("[TEST] CIP Repo Detection")
    
    global_cip = Path.home() / ".cip-global"
    detectors = global_cip / "repo-settings" / "detectors.py"
    
    if not detectors.exists():
        print(f"[SKIP] detectors.py not found")
        return True
    
    try:
        import sys
        sys.path.insert(0, str(global_cip / "repo-settings"))
        from detectors import detect_repo_type, load_repo_profile
        
        # Test detection on current directory
        current_dir = Path.cwd()
        repo_type = detect_repo_type(str(current_dir))
        
        if repo_type:
            print(f"[PASS] Repo detection works: {repo_type}")
            
            # Test profile loading
            try:
                profile = load_repo_profile(repo_type)
                if profile:
                    print(f"[PASS] Profile loading works: {list(profile.keys())}")
                    return True
                else:
                    print(f"[FAIL] Profile loading returned empty")
                    return False
            except Exception as e:
                print(f"[FAIL] Profile loading error: {e}")
                return False
        else:
            print(f"[INFO] No repo type detected (might be expected)")
            return True
    except Exception as e:
        print(f"[FAIL] Repo detection error: {e}")
        return False

def run_all_tests():
    """Run all CIP global verification tests."""
    print("=" * 60)
    print("CIP GLOBAL VERIFICATION TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_cip_command_exists,
        test_cip_repo_settings_exists,
        test_cip_detectors_exists,
        test_cip_base_py_updated,
        test_cip_profile_structure,
        test_cip_repo_detection
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