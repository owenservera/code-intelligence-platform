"""Repository detection logic for CIP profile loading."""
import os
import sys
import re

def detect_repo_type(root):
    """Detect which repo type we're in based on project markers."""
    
    # Check for CIP index repo (this repo itself)
    lib_cipkg = os.path.join(root, "lib", "cipkg")
    readme_md = os.path.join(root, "README.md")
    if os.path.isdir(lib_cipkg) and os.path.exists(readme_md):
        try:
            with open(readme_md, 'r', encoding='utf-8') as f:
                content = f.read()
                if "Code Intelligence Platform" in content or "CIP" in content:
                    return "index"
        except (OSError, UnicodeDecodeError):
            pass
    
    # Check for Vivim-specific markers
    agents_md = os.path.join(root, "AGENTS.md")
    if os.path.exists(agents_md):
        try:
            with open(agents_md, 'r', encoding='utf-8') as f:
                content = f.read()
                if "vivim-final" in content.lower() or "13 engine layers" in content:
                    return "vivim-final"
        except (OSError, UnicodeDecodeError):
            pass
    
    # Check for package.json for JS projects
    package_json = os.path.join(root, "package.json")
    if os.path.exists(package_json):
        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                content = f.read()
                if '"next"' in content or '"react"' in content:
                    return "nextjs-app"
                if '"type": "module"' in content:
                    return "javascript-module"
        except (OSError, UnicodeDecodeError):
            pass
    
    # Check for pyproject.toml for Python projects
    pyproject = os.path.join(root, "pyproject.toml")
    if os.path.exists(pyproject):
        return "python-lib"
    
    # Check for Cargo.toml for Rust projects
    cargo = os.path.join(root, "Cargo.toml")
    if os.path.exists(cargo):
        return "rust-project"
    
    # Default to generic
    return "generic"

def load_repo_profile(repo_type):
    """Load profile from CIP repo-settings. Supports both folder-based and single-file profiles."""
    import copy
    
    # Get the repo-settings directory relative to this file
    settings_dir = os.path.dirname(os.path.abspath(__file__))
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
    import copy
    merged_config = {}
    
    # Get all .toml files in the folder
    toml_files = [f for f in os.listdir(folder_path) if f.endswith('.toml')]
    
    # Load and merge each file
    for toml_file in sorted(toml_files):  # Sort for consistent ordering
        file_path = os.path.join(folder_path, toml_file)
        file_config = _parse_toml_file(file_path)
        
        # Merge into main config
        for section, kv in file_config.items():
            if isinstance(kv, dict):
                if section in merged_config:
                    # Merge nested dictionaries
                    merged_config[section].update(kv)
                else:
                    merged_config[section] = copy.deepcopy(kv)
            elif isinstance(kv, list):
                if section in merged_config:
                    # Extend lists
                    if isinstance(merged_config[section], list):
                        merged_config[section].extend(kv)
                    else:
                        merged_config[section] = copy.deepcopy(kv)
                else:
                    merged_config[section] = copy.deepcopy(kv)
            else:
                merged_config[section] = kv
    
    return merged_config

def _parse_toml_file(path):
    """Parse a single TOML file."""
    try:
        import tomllib
        with open(path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        # Fallback to naive parser
        return _parse_toml_naive(path)

def _coerce(v):
    """Coerce string values to appropriate types."""
    if v.startswith('"') and v.endswith('"'): return v[1:-1]
    if v.startswith("["): return re.findall(r'"([^"]*)"', v)
    if v in ("true", "false"): return v == "true"
    try: return int(v)
    except ValueError:
        try: return float(v)
        except ValueError: return v

def _parse_toml_naive(path):
    """Simple TOML parser for Python versions without tomllib."""
    out, section = {}, None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if not line: continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip(); out.setdefault(section, {})
            elif "=" in line:
                k, v = (s.strip() for s in line.split("=", 1))
                out.setdefault(section or "_", {})[k] = _coerce(v)
    return out
