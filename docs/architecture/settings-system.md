# CIP Repository Settings System Architecture

## Problem Statement
Hardcoding project-specific settings in `.cip/config.toml` for each repo is not scalable. Need a centralized settings system where CIP automatically detects the repo and applies the appropriate configuration.

## Architectural Design

### Core Principles
1. **Repo Detection** - CIP automatically identifies which repo it's running in
2. **Centralized Settings** - Common settings stored in CIP, repo-specific in their locations
3. **Automatic Configuration** - No manual config.toml editing required per repo
4. **Extensible** - Easy to add new repo types

### System Components

#### 1. CIP Settings Repository (C:\0-BlackBoxProject-0\index\repo-settings)
- **Purpose**: Central repository of all repo-specific CIP configurations
- **Structure**:
  ```
  repo-settings/
  ├── profiles/              # Individual repo profiles
  │   ├── vivim-final/       # Complex profiles use folder structure
  │   │   ├── main.toml      # Core profile settings
  │   │   ├── python.toml    # Python-specific config
  │   │   ├── typescript.toml# TypeScript/React config
  │   │   ├── retrieval.toml # Retrieval settings
  │   │   ├── stack.toml     # Stack-specific settings
  │   │   ├── external_search.toml
  │   │   └── custom_rules.toml
  │   ├── nextjs-app/        # Next.js profile folder
  │   ├── python-lib/        # Python library profile folder
  │   └── generic.toml       # Simple profiles use single file
  ├── common/               # Shared configuration snippets (optional)
  │   ├── typescript.toml
  │   ├── python.toml
  │   └── frontend.toml
  └── detectors.py           # Repo detection logic
  ```

#### 2. Repo Detection System
- **Purpose**: Automatically identify which repo CIP is running in
- **Methods**:
  - File fingerprinting (package.json, Cargo.toml, pyproject.toml)
  - Directory structure patterns
  - Known file markers (AGENTS.md, vivim-specific files)
  - Git remote URL parsing

#### 3. Configuration Loading Pipeline
1. CIP starts in a directory
2. Detector identifies repo type
3. Loads appropriate profile from repo-settings/
4. Merges with local overrides (if any)
5. Applies configuration

### Implementation

#### Repo Detection Logic
```python
def detect_repo_type(root):
    """Detect which repo type we're in."""
    # Check for Vivim-specific markers
    if os.path.exists(os.path.join(root, "AGENTS.md")):
        with open(os.path.join(root, "AGENTS.md")) as f:
            content = f.read()
            if "vivim-final" in content or "13 engine layers" in content:
                return "vivim-final"
    
    # Check for package.json for JS projects
    if os.path.exists(os.path.join(root, "package.json")):
        # Could detect Next.js, React, etc.
        return "nextjs-app"
    
    # Check for pyproject.toml for Python projects
    if os.path.exists(os.path.join(root, "pyproject.toml")):
        return "python-lib"
    
    # Default to generic
    return "generic"
```

#### Profile Loading
```python
def load_repo_profile(repo_type):
    """Load profile from CIP repo-settings. Supports both folder-based and single-file profiles."""
    settings_dir = os.path.join(os.path.dirname(__file__), "..", "repo-settings")
    profiles_dir = os.path.join(settings_dir, "profiles")
    
    # Check if it's a folder-based profile (new structure)
    profile_folder = os.path.join(profiles_dir, repo_type)
    if os.path.isdir(profile_folder):
        return _load_folder_profile(profile_folder)
    
    # Fallback to single-file profile (old structure, e.g., generic.toml)
    profile_path = os.path.join(profiles_dir, f"{repo_type}.toml")
    if os.path.exists(profile_path):
        return _parse_toml_file(profile_path)
    
    return {}

def _load_folder_profile(folder_path):
    """Load all .toml files from a profile folder and merge them."""
    merged_config = {}
    toml_files = [f for f in os.listdir(folder_path) if f.endswith('.toml')]
    
    for toml_file in sorted(toml_files):
        file_path = os.path.join(folder_path, toml_file)
        file_config = _parse_toml_file(file_path)
        # Merge into main config
        for section, kv in file_config.items():
            if isinstance(kv, dict):
                if section in merged_config:
                    merged_config[section].update(kv)
                else:
                    merged_config[section] = copy.deepcopy(kv)
            elif isinstance(kv, list):
                if section in merged_config:
                    if isinstance(merged_config[section], list):
                        merged_config[section].extend(kv)
                    else:
                        merged_config[section] = copy.deepcopy(kv)
                else:
                    merged_config[section] = copy.deepcopy(kv)
            else:
                merged_config[section] = kv
    
    return merged_config
```

#### Directory Structure
```
C:\0-BlackBoxProject-0\index\
├── repo-settings/
│   ├── profiles/
│   │   ├── vivim-final/
│   │   │   ├── main.toml
│   │   │   ├── python.toml
│   │   │   ├── typescript.toml
│   │   │   ├── retrieval.toml
│   │   │   ├── stack.toml
│   │   │   ├── external_search.toml
│   │   │   └── custom_rules.toml
│   │   ├── nextjs-app/
│   │   ├── python-lib/
│   │   └── generic.toml
│   ├── common/
│   │   ├── typescript.toml
│   │   └── python.toml
│   └── detectors.py
├── lib/cipkg/
│   ├── base.py
│   └── ...
└── config.default.toml
```

### Vivim-Final Profile Example
```toml
# repo-settings/profiles/vivim-final/main.toml
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
  "src/generated", "seeds/taxonomy", "devops/opencode",
  "context-pack-md", "context-pack.zip",
  "prisma/migrations.bak", "frontend/node_modules", "frontend/.next", "frontend/out",
  "frontend/playwright-report", "frontend/test-results", "frontend/tool-results",
  "frontend/download", "claude-investigate", "intelligence-pack-acu-dcb-storage",
]

# repo-settings/profiles/vivim-final/retrieval.toml
[retrieval]
context_budget_tokens = 6000
lexical_k = 30
vector_k = 30

# repo-settings/profiles/vivim-final/stack.toml
[stack]
prisma_store_contracts = true
tauri_enabled = true

# repo-settings/profiles/vivim-final/external_search.toml
[external_search]
defer_to = "bun"
args = ["run", "devops", "code-index", "search", "{query}"]

# repo-settings/profiles/vivim-final/custom_rules.toml
[custom_rules]
enabled = true
rules_file = ".cip/rules.py"

# repo-settings/profiles/vivim-final/python.toml
[language.python]
max_file_kb = 512
test_globs = ["test_", "_test.", ".test.", "/tests/", "__tests__"]
ignore_dirs = ["__pycache__", ".venv", "venv", ".pytest_cache", ".mypy_cache"]
extensions = [".py", ".pyx"]

# repo-settings/profiles/vivim-final/typescript.toml
[language.typescript]
max_file_kb = 512
test_globs = [".test.", ".spec.", "/tests/", "__tests__"]
ignore_dirs = ["node_modules", ".next", "out", "dist", "build"]
extensions = [".ts", ".tsx", ".js", ".jsx"]
```

### Generic Profile Example
```toml
# repo-settings/profiles/generic.toml (single file for simple profiles)
[profile.generic]
# No specific includes/excludes - uses defaults
exclude = [
  "node_modules", "dist", "build", "out", ".next", ".nuxt",
  "__pycache__", ".venv", "venv", "target", "vendor", "coverage",
  ".pytest_cache", ".mypy_cache", ".idea", ".vscode", ".turbo",
  ".cache", "tmp",
]
```

### Implementation Steps

1. **Create repo-settings directory structure**
2. **Implement repo detection logic**
3. **Create Vivim-Final profile folder** with modular config files:
   - main.toml (core profile settings)
   - python.toml (Python-specific config)
   - typescript.toml (TypeScript/React config)
   - retrieval.toml (retrieval settings)
   - stack.toml (stack-specific settings)
   - external_search.toml (external search config)
   - custom_rules.toml (custom rules config)
4. **Update load_repo_profile to handle folder-based profiles**
5. **Test with vivim-final**
6. **Add other repo profiles as needed**

### Benefits
- **Automatic**: No manual config.toml editing per repo
- **Centralized**: All repo configs in one place
- **Maintainable**: Easy to update profiles across repos
- **Extensible**: Simple to add new repo types
- **Clean**: .cip/config.toml only for local overrides
