"""Master test runner for sync system."""
import os
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def run_test_file(test_file: str) -> bool:
    """Run a single test file."""
    print(f"\n{'=' * 60}")
    print(f"Running: {test_file}")
    print('=' * 60)
    
    try:
        result = os.system(f'python "{test_file}"')
        return result == 0
    except Exception as e:
        print(f"[ERROR] Failed to run {test_file}: {e}")
        return False

def main():
    """Run all sync system tests."""
    tests_dir = Path(__file__).parent
    
    test_files = [
        tests_dir / "test_sync.py",
        tests_dir / "test_validation.py",
        tests_dir / "test_cip_global.py"
    ]
    
    print("=" * 60)
    print("SYNC SYSTEM - MASTER TEST RUNNER")
    print("=" * 60)
    
    results = []
    for test_file in test_files:
        if test_file.exists():
            result = run_test_file(str(test_file))
            results.append((test_file.name, result))
        else:
            print(f"[SKIP] Test file not found: {test_file}")
            results.append((test_file.name, None))
    
    print("\n" + "=" * 60)
    print("MASTER TEST RESULTS")
    print("=" * 60)
    
    for test_name, result in results:
        if result is True:
            print(f"[PASS] {test_name}")
        elif result is False:
            print(f"[FAIL] {test_name}")
        else:
            print(f"[SKIP] {test_name}")
    
    passed = sum(1 for _, result in results if result is True)
    total = len([r for _, r in results if r is not None])
    
    print(f"\nTotal: {passed}/{total} passed")
    
    return all(r for _, r in results if r is not None)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)