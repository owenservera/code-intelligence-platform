# CIP - Agent Guidance

## Project Overview

CIP (Code Intelligence Platform) is a continuously updated model of your codebase — structure, history, tests, runtime health, and semantic audit. It helps AI agents and developers navigate complex codebases efficiently through intelligent indexing and retrieval.

### Key Components
- **Indexer**: Parses and chunks code files
- **Embedder**: Generates semantic embeddings (supports multiple backends)
- **Vector Store**: SQLite-based vector storage
- **Retriever**: Hybrid lexical + semantic search
- **Auditor**: Quality rule engine
- **Repo Settings System**: Automatic repo-specific configuration
- **Sync System**: Automated development-to-production synchronization

### Architecture Summary
```
index/
├── lib/cipkg/           # Core library
│   ├── base.py          # Core utilities with profile loading
│   ├── indexer.py       # Code parsing and indexing
│   ├── embed.py         # Embedding backends
│   ├── retrieve.py      # Search and retrieval
│   └── stack/           # Stack-specific analyzers
├── repo-settings/       # Repo-specific configuration system
│   ├── profiles/        # Modular repo profiles
│   │   ├── index/       # CIP core profile
│   │   ├── vivim-final/ # Vivim repo profile
│   │   └── generic.toml # Default profile
│   └── detectors.py     # Repo detection logic
├── sync_global/         # Global sync system
│   ├── core/            # Sync engine, validation, rollback
│   ├── tests/           # Sync system tests
│   └── config/          # Sync configuration
├── bin/                 # CLI executables
├── bootstrap/           # Bootstrap scripts
└── docs/                # Documentation
```

## Development Context

### Current State
- **Repo Settings System**: Fully implemented with folder-based profiles
- **Sync System**: Production-ready with validation and rollback
- **Profile Detection**: Automatic repo type detection
- **Global Integration**: Sync system updates global CIP installation

### Known Patterns
- **Profile-based configuration**: Each repo type gets modular TOML configs
- **Automatic detection**: No manual config.toml editing required
- **Safety-first sync**: Multiple validation gates and automatic rollback
- **Modular architecture**: Clean separation of concerns across systems

### Conventions Used
- **TOML for configuration**: All configs use TOML format
- **Folder-based profiles**: Complex repos use folder structure, simple repos use single file
- **Hybrid loading**: System supports both folder-based and single-file profiles
- **UTF-8 encoding**: All files use UTF-8 encoding with Windows compatibility

## Component Guide

### Repo Settings System

#### Architecture
- **Location**: `repo-settings/`
- **Purpose**: Centralized repo-specific CIP configurations
- **Detection**: Automatic repo type detection via file markers
- **Loading**: Hybrid system supports folder-based and single-file profiles

#### Profile Structure
```
repo-settings/profiles/<repo-type>/
├── main.toml           # Core profile settings
├── python.toml         # Python-specific config
├── typescript.toml     # TypeScript/React config
├── retrieval.toml      # Retrieval settings
├── stack.toml          # Stack-specific settings
└── custom_rules.toml   # Custom rules config
```

#### Detection Logic
- **Index repo**: Checks for `lib/cipkg` + "Code Intelligence Platform" in README
- **Vivim repo**: Checks for "vivim-final" or "13 engine layers" in AGENTS.md
- **Generic**: Default fallback for unrecognized repos

#### Adding New Profiles
1. Create profile folder: `repo-settings/profiles/<repo-name>/`
2. Add modular config files (main.toml, language-specific files, etc.)
3. Add detection logic to `detectors.py`
4. Test profile loading with sync system

### Sync System

#### Architecture
- **Location**: `sync_global/`
- **Purpose**: Safely sync development changes to global CIP installation
- **Components**: Sync engine, validator, rollback manager
- **Safety**: Pre/post validation, automatic backups, auto-rollback

#### Sync Process
1. **Pre-sync validation**: Source files exist, target accessible
2. **Backup creation**: Automatic backup before sync
3. **Sync operation**: Copy files/directories to target
4. **Post-sync validation**: Verify files copied correctly
5. **CIP validation**: Test synced installation works

#### Usage
```bash
# Preview sync
python sync_global/sync.py --dry-run
# or
sync --dry-run

# Sync with CIP testing
python sync_global/sync.py --test-cip
# or
sync --test-cip

# List backups
python sync_global/sync.py --list-backups
# or
sync --list-backups

# Rollback if needed
python sync_global/sync.py --rollback backup_20260815_174404
# or
sync --rollback backup_20260815_174404
```

#### Configuration
- **Location**: `sync_global/config/sync_config.toml`
- **Items to sync**: repo-settings, lib/cipkg/base.py, config.default.toml
- **Validation**: Pre-sync, post-sync, CIP tests
- **Rollback**: Auto-rollback on failure, max 5 backups

### Core CIP Components

#### Base System (`lib/cipkg/base.py`)
- **Profile loading**: Automatic repo detection and profile application
- **File iteration**: Optimized with include/exclude lists
- **Configuration**: Merges defaults, profiles, and local overrides
- **Token estimation**: Token counting for context management

#### Profile Integration
- **Detection**: Calls `detect_repo_type()` from repo-settings
- **Loading**: Uses `load_repo_profile()` with hybrid support
- **Merging**: Flattens profile structure into main config
- **Overrides**: Local `.cip/config.toml` can override profile settings

## Development Workflow

### Making Changes to CIP Core
1. **Modify core files** in `lib/cipkg/`
2. **Test locally** with current repo
3. **Update sync config** if new files need syncing
4. **Run sync**: `python sync_global/sync.py --test-cip`
5. **Verify global CIP** works correctly

### Adding New Repo Profiles
1. **Create profile folder**: `repo-settings/profiles/<repo-name>/`
2. **Add config files**: main.toml, language-specific files
3. **Add detection logic** to `detectors.py`
4. **Test profile loading**: Use sync system validation
5. **Sync to global**: `python sync_global/sync.py --test-cip`

### Modifying Sync System
1. **Update sync components** in `sync_global/core/`
2. **Run sync tests**: `python tests/sync-system/test_sync.py`
3. **Test validation**: `python tests/sync-system/test_validation.py`
4. **Dry-run sync**: `python sync_global/sync.py --dry-run`
5. **Full sync test**: `python sync_global/sync.py --test-cip`

### Updating Profile System
1. **Modify detectors** in `repo-settings/detectors.py`
2. **Update profile loading** if needed
3. **Test detection** with various repo types
4. **Sync changes**: `python sync_global/sync.py --test-cip`
5. **Verify profile loading** in global CIP

## Common Tasks

### Adding a New Repo Type
```python
# In repo-settings/detectors.py
def detect_repo_type(root):
    # Add new detection logic
    if some_condition:
        return "new-repo-type"
    # ... existing logic
```

```bash
# Create profile folder
mkdir repo-settings/profiles/new-repo-type

# Add config files
# main.toml, language-specific files, etc.

# Test and sync
python sync_global/sync.py --test-cip
```

### Updating Sync Items
```toml
# In sync_global/config/sync_config.toml
[items]
files = [
    "repo-settings",
    "lib/cipkg/base.py",
    "lib/cipkg/new_module.py",  # Add new items
    "config.default.toml"
]
```

### Testing Profile Loading
```python
# Test detection
python -c "import sys; sys.path.insert(0, 'repo-settings'); from detectors import detect_repo_type; print(detect_repo_type('.'))"

# Test profile loading
python -c "import sys; sys.path.insert(0, 'repo-settings'); from detectors import load_repo_profile; print(load_repo_profile('index'))"
```

### Running Sync System Tests
```bash
# All sync tests
python tests/sync-system/run_all_tests.py

# Specific test suites
python tests/sync-system/test_sync.py
python tests/sync-system/test_validation.py
python tests/sync-system/test_cip_global.py
```

## Known Issues

### Current Limitations
- **CIP command not in PATH**: Global CIP tests may fail if CIP not in system PATH
- **Profile overlap**: Multiple detection conditions could match same repo
- **Sync scope**: Currently only syncs specific files, not entire CIP installation

### Workarounds
- **PATH issues**: Use full path to CIP executable or add to PATH manually
- **Detection conflicts**: Order detection conditions by specificity
- **Limited sync**: Add more items to sync config as needed

### Future Improvements
- **Incremental sync**: Only sync changed files
- **Profile inheritance**: Allow profiles to inherit from base profiles
- **Remote sync**: Support for remote CIP installations
- **GUI interface**: Visual sync management

## File Organization

### Root Directory (Clean)
- **Essential files only**: AGENTS.md, README.md, LICENSE, config.default.toml, install.sh, ontology.json, .gitignore
- **Core directories**: bin/, bootstrap/, data/, docs/, lib/, repo-settings/, sync_global/, tests/

### Documentation Structure
- **Architecture**: System architecture and design docs
- **User Guide**: Installation, commands, configuration
- **API**: MCP server, HTTP API, Python API
- **Development**: Setup, testing, contributing
- **Sync System**: Sync system documentation
- **Repo Profiles**: Profile system documentation
- **Internal**: Integration plans, master plans

### Test Structure
- **Unit tests**: Core component tests
- **Integration tests**: System integration tests
- **Sync system tests**: Sync system validation
- **E2E tests**: End-to-end testing

## Contact/Support

### Issue Reporting
- **GitHub issues**: Use project issue tracker
- **Documentation**: Check docs/ for guidance
- **Logs**: Check sync_global/logs/ for sync issues

### Contribution Process
1. **Test changes** locally
2. **Run sync system tests**
3. **Sync to global** with validation
4. **Update documentation** as needed
5. **Submit issues** for bugs or improvements

### Getting Help
- **Architecture docs**: docs/architecture/
- **User guide**: docs/user-guide/
- **Sync system**: docs/sync-system/
- **Developer guide**: docs/development/

This guide provides comprehensive context for AI agents working on the CIP codebase, covering all major systems and providing clear development workflows.