# CIP Repository Profile System Architecture

## Problem Statement
CIP needs to work across multiple repositories with different project structures, but remain completely generic in its core functionality. Each repository should be able to define its own indexing preferences without modifying CIP's core code.

## Architectural Design

### Core Principles
1. **CIP Core = Completely Generic** - No project-specific defaults in core
2. **Repo-First Configuration** - Each repo owns its own CIP configuration
3. **Profile System = Extensible** - Clean interface for repo-specific customization
4. **Zero-Copy Setup** - Easy bootstrap for new repos

### System Components

#### 1. CIP Core (C:\0-BlackBoxProject-0\index)
- **Purpose**: Generic code intelligence engine
- **Configuration**: Default base settings only (no project-specific logic)
- **Profile Interface**: Standard profile structure that repos can implement

#### 2. Repository Profile (.cip/config.toml in each repo)
- **Purpose**: Repository-specific CIP configuration
- **Location**: `{repo_root}/.cip/config.toml`
- **Structure**: 
  ```toml
  profile = "myproject"
  
  [profile.myproject]
  include = ["src", "lib", "docs"]
  exclude = ["node_modules", "dist", "build"]
  
  [index]
  max_file_kb = 512
  
  [custom_rules]
  enabled = true
  rules_file = ".cip/rules.py"
  ```

#### 3. Profile Resolution Logic
1. Load base CIP defaults
2. Read repo's `.cip/config.toml`
3. Apply profile settings from repo config
4. Merge with any additional repo settings

### Vivim-Final as Reference Implementation

#### Vivim-Final Configuration
```toml
# vivim-final/.cip/config.toml
profile = "vivim"

[profile.vivim]
include = [
  "src",                    # Backend source (13 engine layers)
  "frontend/src",           # Frontend source only
  "prisma",                 # Database schema
  "seeds",                  # Data & provider manifests
  "devops",                 # Dev tools
  "scripts",                # Build scripts
  "shared"                  # Shared utilities
]
exclude = [
  "src/generated",          # Generated code (62MB)
  "frontend/node_modules",  # Dependencies
  "frontend/.next",         # Next.js cache
  "frontend/out",           # Build output
  "frontend/playwright-report",
  "frontend/test-results",
  "frontend/tool-results"
]

[external_search]
defer_to = "bun"
args = ["run", "devops", "code-index", "search", "{query}"]

[retrieval]
context_budget_tokens = 6000
lexical_k = 30
vector_k = 30

[stack]
prisma_store_contracts = true
tauri_enabled = true

[custom_rules]
enabled = true
rules_file = ".cip/rules.py"
```

### Future Repo Examples

#### Next.js Project Profile
```toml
profile = "nextjs-app"

[profile.nextjs-app]
include = ["src", "app", "components", "lib"]
exclude = ["node_modules", ".next", "out", "dist"]
```

#### Python Project Profile
```toml
profile = "python-lib"

[profile.python-lib]
include = ["src", "tests"]
exclude = ["venv", ".venv", "__pycache__", "*.egg-info"]
```

#### Monorepo Profile
```toml
profile = "monorepo"

[profile.monorepo]
include = ["packages/*/src", "apps/*/src"]
exclude = ["node_modules", "dist", "build"]
```

### Implementation Steps

1. **CIP Core Cleanup**
   - Remove project-specific patterns from DEFAULT_EXCLUDES (node_modules, .next, etc.)
   - Keep only truly universal excludes (.git, .cip)
   - Ensure profile resolution is generic

2. **Profile Resolution Logic**
   - Clean profile loading that works for any repo
   - Proper merge of include/exclude from profiles into index section
   - Support for profile inheritance (optional)
   - Clear error messages for invalid profiles

3. **File Iteration Logic**
   - Update iter_files to correctly handle include/exclude combination
   - Ensure proper precedence: include list > exclude list > default excludes

4. **Vivim-Final Setup**
   - Complete vivim-final/.cip/config.toml
   - Verify it works with generic CIP core
   - Document as reference implementation

5. **Bootstrap System** (Future)
   - Template generator for new repos
   - Profile templates for common project types
   - Interactive setup wizard

### Technical Adjustments Required

#### 1. DEFAULT_EXCLUDES Cleanup
Remove project-specific patterns from core:
```python
# Before (project-specific)
DEFAULT_EXCLUDES = {
    ".git", "node_modules", "dist", "build", "out", ".next", ".nuxt",
    "__pycache__", ".venv", "venv", "target", "vendor", "coverage",
    ".pytest_cache", ".mypy_cache", ".idea", ".vscode", ".turbo",
    ".cache", "tmp", ".cip",
}

# After (truly universal)
DEFAULT_EXCLUDES = {
    ".git", ".cip",  # Only truly universal excludes
}
```

#### 2. Profile Merge Logic
Update load_config to properly merge profile include/exclude:
```python
# Apply profile settings correctly
if profile_key in data:
    profile_cfg = data[profile_key]
    # Merge include/exclude into index section
    if "include" in profile_cfg:
        cfg.setdefault("index", {}).setdefault("include", []).extend(profile_cfg["include"])
    if "exclude" in profile_cfg:
        cfg.setdefault("index", {}).setdefault("exclude", []).extend(profile_cfg["exclude"])
```

#### 3. iter_files Validation
Ensure include/exclude logic correctly implements:
- Include list acts as whitelist when present
- Exclude list acts as blacklist for included directories
- Proper precedence handling

### Benefits
- **Reusable**: CIP works on any repo without code changes
- **Maintainable**: Each repo owns its configuration
- **Extensible**: Easy to add new project types
- **Clear**: Separation of concerns between core and project-specific logic
