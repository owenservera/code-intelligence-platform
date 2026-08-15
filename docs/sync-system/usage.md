# CIP Global Sync System - Usage Guide

## Overview
The CIP Global Sync System provides a safe, automated way to sync development changes from the local CIP repository to the global CIP installation. It includes validation, backup, rollback, and comprehensive testing.

## Quick Start

### Basic Sync
```bash
cd C:\0-BlackBoxProject-0\index
python sync_global.py
```

### Dry Run (Preview Changes)
```bash
python sync_global.py --dry-run
```

### Sync with CIP Testing
```bash
python sync_global.py --test-cip
```

## Command Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be synced without making changes |
| `--verbose, -v` | Show detailed progress information |
| `--force` | Skip validation checks (not recommended) |
| `--test-cip` | Run CIP validation tests after sync |
| `--rollback NAME` | Rollback to specific backup |
| `--list-backups` | List available backups |
| `--validate-only` | Run validation without syncing |

## Usage Examples

### 1. Development Workflow
```bash
# Make changes to local CIP
# Preview what will be synced
python sync_global.py --dry-run

# Sync with full validation
python sync_global.py --test-cip
```

### 2. Safe Sync with Rollback
```bash
# Sync (automatically creates backup)
python sync_global.py

# If something goes wrong, rollback
python sync_global.py --rollback backup_20260815_174404
```

### 3. List Available Backups
```bash
python sync_global.py --list-backups
```

### 4. Validation Only
```bash
# Check if sync would be valid without actually syncing
python sync_global.py --validate-only
```

## Configuration

The sync system is configured in `sync_global/config/sync_config.toml`:

```toml
[sync]
source = "."                    # Local repo root
target = "~/.cip-global"        # Global CIP installation
backup_enabled = true
backup_location = "./sync_global/backups"
log_level = "INFO"

[items]
files = [
    "repo-settings",           # Profile system
    "lib/cipkg/base.py",      # Core utilities
    "config.default.toml"     # Default configuration
]

[validation]
pre_sync_checks = true        # Run validation before sync
post_sync_tests = true        # Run validation after sync
cip_command_tests = true      # Run CIP tests after sync

[rollback]
enabled = true
max_backups = 5               # Keep 5 most recent backups
auto_rollback_on_failure = true  # Auto-rollback on validation failure
```

## Sync Process

### 1. Pre-Sync Validation
- Verifies source files exist
- Checks target directory accessibility
- Validates write permissions
- Creates backup if enabled

### 2. Sync Operation
- Copies files/directories from source to target
- Handles both files and directories
- Preserves file metadata

### 3. Post-Sync Validation
- Verifies files were copied correctly
- Runs CIP-specific validation tests
- Tests repo detection
- Tests profile loading

### 4. Automatic Rollback
If validation fails and `auto_rollback_on_failure` is enabled:
- Automatically restores from backup
- Logs rollback operation
- Maintains system stability

## Safety Features

### Validation Gates
- **Pre-sync validation**: Must pass before sync begins
- **Post-sync validation**: Must pass for sync to be considered successful
- **CIP validation**: Ensures synced CIP installation works correctly

### Backup System
- **Automatic backups**: Created before each sync
- **Multiple versions**: Keeps N most recent backups
- **Emergency backups**: Created before rollback operations
- **Space management**: Automatically removes old backups

### Rollback Capabilities
- **Manual rollback**: Restore to any available backup
- **Auto-rollback**: Automatic rollback on validation failure
- **Emergency backup**: Protects current state before rollback

## Testing

### Run All Tests
```bash
python sync_global/tests/run_all_tests.py
```

### Run Specific Test Suites
```bash
# Sync system tests
python sync_global/tests/test_sync.py

# Validation tests
python sync_global/tests/test_validation.py

# CIP global verification tests
python sync_global/tests/test_cip_global.py
```

## Troubleshooting

### Sync Fails Validation
1. Check validation logs: `sync_global/logs/validation.log`
2. Review error messages
3. Fix issues in source files
4. Try sync again

### CIP Tests Fail After Sync
1. System auto-rolls back if enabled
2. Manual rollback: `python sync_global.py --rollback <backup_name>`
3. Investigate CIP issues
4. Fix and retry sync

### Permission Errors
1. Check write permissions to global CIP directory
2. Run with appropriate permissions
3. Verify target directory is accessible

### Configuration Issues
1. Verify `sync_config.toml` is valid TOML
2. Check paths are correct
3. Ensure source files exist

## Logs

### Sync History
Location: `sync_global/logs/sync_history.log`

Contains:
- Sync start/end timestamps
- Backup creation/deletion
- Sync operations
- Rollback operations

### Validation Log
Location: `sync_global/logs/validation.log`

Contains:
- Pre-sync validation results
- Post-sync validation results
- CIP validation results
- Specific error messages

## Best Practices

### Development Workflow
1. Make changes to local CIP repository
2. Test changes locally
3. Run dry-run to preview sync: `python sync_global.py --dry-run`
4. Sync with testing: `python sync_global.py --test-cip`
5. Verify CIP works globally

### Safety First
- Always use `--test-cip` for important changes
- Keep backups enabled
- Review validation logs if issues occur
- Test rollback procedure before critical deployments

### Configuration Management
- Keep `sync_config.toml` in version control
- Review items to sync regularly
- Adjust backup retention as needed
- Monitor log file sizes

## Advanced Usage

### Custom Items to Sync
Edit `sync_config.toml`:
```toml
[items]
files = [
    "repo-settings",
    "lib/cipkg/base.py",
    "lib/cipkg/custom_module.py",  # Add custom items
    "config.default.toml"
]
```

### Adjust Backup Retention
```toml
[rollback]
max_backups = 10  # Keep 10 backups instead of 5
```

### Disable Auto-Rollback
```toml
[rollback]
auto_rollback_on_failure = false  # Manual rollback only
```

## System Status

After successful sync, the system reports:
- ✅ Pre-sync validation: PASSED
- ✅ Backup created: backup_YYYYMMDD_HHMMSS
- ✅ Sync operation: 3/3 items synced
- ✅ Post-sync validation: PASSED
- ✅ CIP validation: PASSED
- ✅ Sync operation completed successfully

The global CIP installation is now updated with the latest development changes and fully validated.