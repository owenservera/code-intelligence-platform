"""Tests for sync system operations."""
import os
import sys
import shutil
import tempfile
from pathlib import Path

# Add project root and sync_global to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sync_global"))

from sync_global.core.sync_engine import SyncEngine
from sync_global.core.validator import SyncValidator
from sync_global.core.rollback import RollbackManager

def test_sync_engine_initialization():
    """Test sync engine initialization."""
    print("[TEST] Sync Engine Initialization")
    
    config = {
        'sync': {
            'source': '.',
            'target': '~/.cip-global',
            'backup_location': './sync_global/backups'
        },
        'items': {
            'files': ['repo-settings', 'lib/cipkg/base.py']
        },
        'rollback': {
            'max_backups': 5
        }
    }
    
    try:
        engine = SyncEngine(config)
        assert engine.source_dir.exists(), "Source directory should exist"
        assert engine.backup_dir.exists(), "Backup directory should be created"
        print("[PASS] Sync engine initialization")
        return True
    except Exception as e:
        print(f"[FAIL] Sync engine initialization: {e}")
        return False

def test_file_hash_calculation():
    """Test file hash calculation."""
    print("[TEST] File Hash Calculation")
    
    config = {
        'sync': {
            'source': '.',
            'target': '~/.cip-global',
            'backup_location': './sync_global/backups'
        },
        'items': {'files': []},
        'rollback': {'max_backups': 5}
    }
    
    try:
        engine = SyncEngine(config)
        # Test with a known file
        test_file = Path(__file__)
        if test_file.exists():
            hash_value = engine.get_file_hash(test_file)
            assert len(hash_value) == 64, "SHA256 hash should be 64 characters"
            print(f"[PASS] File hash calculation: {hash_value[:16]}...")
            return True
        else:
            print("[SKIP] Test file not found")
            return True
    except Exception as e:
        print(f"[FAIL] File hash calculation: {e}")
        return False

def test_backup_creation():
    """Test backup creation."""
    print("[TEST] Backup Creation")
    
    # Create temporary test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        test_source = Path(temp_dir) / "source"
        test_target = Path(temp_dir) / "target"
        test_backup = Path(temp_dir) / "backups"
        
        test_source.mkdir()
        test_target.mkdir()
        test_backup.mkdir()
        
        # Create test file
        (test_source / "test.txt").write_text("test content")
        
        config = {
            'sync': {
                'source': str(test_source),
                'target': str(test_target),
                'backup_location': str(test_backup)
            },
            'items': {'files': ['test.txt']},
            'rollback': {'max_backups': 5}
        }
        
        try:
            engine = SyncEngine(config)
            backup_name = engine.create_backup()
            
            assert backup_name.startswith("backup_"), "Backup name should start with backup_"
            assert (test_backup / backup_name).exists(), "Backup directory should be created"
            
            print(f"[PASS] Backup creation: {backup_name}")
            return True
        except Exception as e:
            print(f"[FAIL] Backup creation: {e}")
            return False

def test_validator_pre_sync():
    """Test pre-sync validation."""
    print("[TEST] Pre-Sync Validation")
    
    config = {
        'sync': {
            'source': '.',
            'target': '~/.cip-global',
            'backup_location': './sync_global/backups'
        },
        'items': {'files': ['repo-settings']},
        'rollback': {'max_backups': 5}
    }
    
    try:
        engine = SyncEngine(config)
        validator = SyncValidator(engine.source_dir, engine.target_dir, engine.log_dir)
        
        is_valid, errors = validator.pre_sync_validation(['repo-settings'])
        
        if is_valid:
            print("[PASS] Pre-sync validation")
        else:
            print(f"[FAIL] Pre-sync validation: {errors}")
        
        return is_valid
    except Exception as e:
        print(f"[FAIL] Pre-sync validation: {e}")
        return False

def test_rollback_manager():
    """Test rollback manager."""
    print("[TEST] Rollback Manager")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_backup = Path(temp_dir) / "backups"
        test_target = Path(temp_dir) / "target"
        test_log = Path(temp_dir) / "logs"
        
        test_backup.mkdir()
        test_target.mkdir()
        test_log.mkdir()
        
        # Create test backup
        test_backup_dir = test_backup / "backup_20260815_120000"
        test_backup_dir.mkdir()
        (test_backup_dir / "test.txt").write_text("backup content")
        
        try:
            rollback_mgr = RollbackManager(test_backup, test_target, test_log)
            backups = rollback_mgr.list_backups()
            
            assert len(backups) == 1, "Should have one backup"
            assert backups[0]['name'] == "backup_20260815_120000", "Backup name should match"
            
            print(f"[PASS] Rollback manager: {backups[0]['name']}")
            return True
        except Exception as e:
            print(f"[FAIL] Rollback manager: {e}")
            return False

def run_all_tests():
    """Run all sync system tests."""
    print("=" * 60)
    print("SYNC SYSTEM TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_sync_engine_initialization,
        test_file_hash_calculation,
        test_backup_creation,
        test_validator_pre_sync,
        test_rollback_manager
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