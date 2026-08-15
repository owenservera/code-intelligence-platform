#!/usr/bin/env python3
"""
CIP Global Sync Command
Syncs local CIP development changes to global installation with validation and rollback.

Usage:
    python sync_global.py [options]

Options:
    --dry-run              Show what would be synced without making changes
    --verbose, -v          Show detailed progress
    --force                Skip validation checks
    --test-cip             Run CIP validation tests after sync
    --rollback NAME        Rollback to specific backup
    --list-backups         List available backups
    --validate-only        Run validation without syncing
"""

import os
import sys
import argparse
from pathlib import Path
import re

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add sync_global to path
sys.path.insert(0, str(Path(__file__).parent / "sync_global"))

from core import SyncEngine, SyncValidator, RollbackManager

def load_config():
    """Load sync configuration."""
    config_path = Path(__file__).parent / "config" / "sync_config.toml"
    try:
        return _parse_toml_naive(config_path)
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def _parse_toml_naive(path):
    """Simple TOML parser."""
    out, section = {}, None
    in_array = False
    array_key = None
    array_items = []
    
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if not line: continue
            
            if line.startswith("[") and line.endswith("]"):
                # Handle previous array if we were in one
                if in_array and array_key:
                    out.setdefault(section or "_", {})[array_key] = array_items
                    in_array = False
                    array_key = None
                    array_items = []
                
                section = line[1:-1].strip()
                out.setdefault(section, {})
            elif "=" in line and not in_array:
                k, v = (s.strip() for s in line.split("=", 1))
                if v.startswith("["):
                    # Start of array
                    in_array = True
                    array_key = k
                    # Parse items on this line
                    array_content = v[1:].strip()
                    if array_content.endswith("]"):
                        # Single line array
                        array_content = array_content[:-1].strip()
                        if array_content:
                            items = [item.strip().strip('"').strip("'") for item in array_content.split(',')]
                            out.setdefault(section or "_", {})[k] = items
                            in_array = False
                            array_key = None
                    else:
                        # Multi-line array, collect items
                        if array_content:
                            items = [item.strip().strip('"').strip("'") for item in array_content.split(',')]
                            array_items.extend(items)
                else:
                    out.setdefault(section or "_", {})[k] = _coerce(v)
            elif in_array:
                # Collect array items
                if line.startswith("]"):
                    # End of array
                    out.setdefault(section or "_", {})[array_key] = array_items
                    in_array = False
                    array_key = None
                    array_items = []
                elif line:
                    items = [item.strip().strip('"').strip("'") for item in line.split(',') if item.strip()]
                    array_items.extend(items)
    
    return out

def _coerce(v):
    """Coerce string values to appropriate types."""
    v = v.strip()
    if v.startswith('"') and v.endswith('"'): return v[1:-1]
    if v.startswith("'") and v.endswith("'"): return v[1:-1]
    if v.startswith("["): 
        # Parse array
        content = v[1:-1].strip()
        if not content:
            return []
        items = [item.strip().strip('"').strip("'") for item in content.split(',')]
        return items
    if v in ("true", "false"): return v == "true"
    try: return int(v)
    except ValueError:
        try: return float(v)
        except ValueError: return v

def main():
    parser = argparse.ArgumentParser(
        description="Sync local CIP development changes to global installation"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed progress")
    parser.add_argument("--force", action="store_true", help="Skip validation checks")
    parser.add_argument("--test-cip", action="store_true", help="Run CIP validation tests after sync")
    parser.add_argument("--rollback", metavar="NAME", help="Rollback to specific backup")
    parser.add_argument("--list-backups", action="store_true", help="List available backups")
    parser.add_argument("--validate-only", action="store_true", help="Run validation without syncing")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Initialize components
    engine = SyncEngine(config)
    validator = SyncValidator(engine.source_dir, engine.target_dir, engine.log_dir)
    rollback_mgr = RollbackManager(engine.backup_dir, engine.target_dir, engine.log_dir)
    
    print("[SYNC] CIP Global Sync System")
    print(f"  Source: {engine.source_dir}")
    print(f"  Target: {engine.target_dir}")
    print()
    
    # Handle rollback operation
    if args.rollback:
        print(f"[ROLLBACK] Restoring to: {args.rollback}")
        success = rollback_mgr.restore_backup(args.rollback)
        return 0 if success else 1
    
    # Handle list backups
    if args.list_backups:
        print("[BACKUPS] Available backups:")
        backups = rollback_mgr.list_backups()
        if not backups:
            print("  No backups available")
        else:
            for backup in backups:
                print(f"  {backup['name']} ({backup['time']})")
        return 0
    
    # Handle validate-only
    if args.validate_only:
        print("[VALIDATION] Running validation checks")
        is_valid, errors = validator.pre_sync_validation(config['items']['files'])
        if is_valid:
            print("[VALIDATION] Pre-sync validation: PASSED")
        else:
            print("[VALIDATION] Pre-sync validation: FAILED")
            for error in errors:
                print(f"  ERROR: {error}")
        return 0 if is_valid else 1
    
    # Main sync operation
    if args.dry_run:
        print("[DRY RUN] No changes will be made")
        print()
    
    # Pre-sync validation
    if not args.force:
        print("[VALIDATION] Running pre-sync checks")
        is_valid, errors = validator.pre_sync_validation(config['items']['files'])
        if not is_valid:
            print("[VALIDATION] Pre-sync validation FAILED")
            for error in errors:
                print(f"  ERROR: {error}")
            print("[SYNC] Aborted due to validation errors")
            return 1
        print("[VALIDATION] Pre-sync validation: PASSED")
        print()
    
    # Create backup
    if config['sync']['backup_enabled'] and not args.dry_run:
        print("[BACKUP] Creating backup...")
        backup_name = engine.create_backup()
        print()
    
    # Perform sync
    print("[SYNC] Starting sync operation")
    success_count, total_count = engine.sync_all(args.dry_run)
    print(f"[SYNC] Synced {success_count}/{total_count} items")
    print()
    
    if args.dry_run:
        print("[SYNC] Dry run complete")
        return 0
    
    # Post-sync validation
    if not args.force:
        print("[VALIDATION] Running post-sync checks")
        is_valid, errors = validator.post_sync_validation(config['items']['files'])
        if not is_valid:
            print("[VALIDATION] Post-sync validation FAILED")
            for error in errors:
                print(f"  ERROR: {error}")
            
            # Auto-rollback if enabled
            if config['rollback']['auto_rollback_on_failure']:
                print("[ROLLBACK] Auto-rollback triggered")
                rollback_mgr.restore_backup(backup_name)
                return 1
        print("[VALIDATION] Post-sync validation: PASSED")
        print()
    
    # CIP validation
    if args.test_cip or config['validation']['cip_command_tests']:
        print("[CIP_VALIDATION] Running CIP tests")
        is_valid, errors = validator.cip_validation()
        if not is_valid:
            print("[CIP_VALIDATION] CIP tests FAILED")
            for error in errors:
                print(f"  ERROR: {error}")
            
            # Auto-rollback if enabled
            if config['rollback']['auto_rollback_on_failure']:
                print("[ROLLBACK] Auto-rollback triggered")
                rollback_mgr.restore_backup(backup_name)
                return 1
        print("[CIP_VALIDATION] CIP tests: PASSED")
        print()
    
    # Cleanup old backups
    engine.cleanup_old_backups()
    
    print("[SYNC] Sync operation completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())