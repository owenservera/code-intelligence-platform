"""Core utilities: repo discovery, config, hashing, file iteration, tokenizing."""
import hashlib, os, re, logging

log = logging.getLogger("cip")

def log_swallowed(where: str, exc: Exception):
    """Call this from every except-and-continue block so failures are visible
    with CIP_DEBUG=1 without changing control flow."""
    if os.environ.get("CIP_DEBUG"):
        log.warning("swallowed exception in %s: %r", where, exc)

def _load_default_toml():
    """Load default configuration from TOML files."""
    import tomllib
    cfg = {}
    # Try to load from both config.default.toml and config.v2.default.toml
    for filename in ["config.default.toml", "config.v2.default.toml"]:
        try:
            # Try relative to this file (lib/cipkg/base.py -> repo root)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            path = os.path.join(base_dir, filename)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    for section, kv in tomllib.load(f).items():
                        cfg.setdefault(section, {}).update(kv)
        except Exception as e:
            # If TOML loading fails, continue with defaults
            log_swallowed(f"base._load_default_toml/{filename}", e)
    return cfg

CIP_DIRNAME = ".cip"

DEFAULT_EXCLUDES = {
    ".git", ".cip",  # Only truly universal excludes
    # Generated / dependency / backup trees (F-42): these poison the index with
    # duplicate symbols and are never first-class source. Kept in the hard set so
    # they stay excluded even when repo config excludes are empty/unloaded.
    "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv",
    "backups", "htmlcov", "dist", "build", ".tox",
}

# Directory-name prefixes that mark a tree as an automated backup/emergency
# snapshot (e.g. sync_global/backups/backup_20260815_...). Excluded always.
BACKUP_DIR_PREFIXES = ("backup_", "emergency_")

# Load defaults from TOML files, falling back to hardcoded defaults
_toml_defaults = _load_default_toml()

DEFAULT_CONFIG = {
    # Hardcoded fallback defaults (used if TOML files don't exist or are incomplete)
    "index": {"max_file_kb": 512, "exclude": [], "include": [],
              "test_globs": ["test_", "_test.", ".test.", ".spec.", "/tests/", "__tests__"]},
    "embed": {"backend": "auto", "model": "BAAI/bge-small-en-v1.5", "dim": 384,
              "service_port": 8787, "autostart": True},
    "retrieval": {"lexical_k": 30, "vector_k": 30, "context_budget_tokens": 6000},
    "serve": {"port": 8787},
    # ---- v1.0 additions ----
    "summary": {"backend": "structural", "llm_model": "gpt-4o-mini", "max_llm_per_sync": 20},
    "git": {"depth": 500, "co_change_min": 2},
    "rerank": {"enabled": True},
    "vector": {"backend": "sqlite"},        # sqlite | sqlite-vec
    # ---- v2 performance ----
    "perf": {"workers": 0},                 # 0=auto (cpu_count); 1=serial; N=explicit
    "maintain": {"event_days": 30},
    # ---- stack and repo profiles ----
    "stack": {"prisma_store_contracts": False, "tauri_enabled": False},
    "language": {},
    # Core CIP has no default profiles - repos define their own in .cip/config.toml
    "profile": {}
}

# Merge TOML defaults on top of hardcoded defaults
for section, kv in _toml_defaults.items():
    DEFAULT_CONFIG.setdefault(section, {}).update(kv)

def repo_root(start=None):
    p = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(p, CIP_DIRNAME)):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            raise SystemExit("cip: no .cip/ found here or above. Install the bundle first.")
        p = parent

def cip_dir(root):  return os.path.join(root, CIP_DIRNAME)

def data_dir(root):
    d = os.path.join(cip_dir(root), "data")
    os.makedirs(d, exist_ok=True)
    return d

def sha(x):
    h = hashlib.sha256()
    h.update(x if isinstance(x, bytes) else x.encode("utf-8", "replace"))
    return h.hexdigest()

def _coerce(v):
    if v.startswith('"') and v.endswith('"'): return v[1:-1]
    if v.startswith("["): return re.findall(r'"([^"]*)"', v)
    if v in ("true", "false"): return v == "true"
    try: return int(v)
    except ValueError:
        try: return float(v)
        except ValueError: return v

def _parse_toml_naive(path):
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

def load_config(root, warnings=None):
    import copy
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    
    # Auto-detect repo type and load profile
    try:
        # Import from repo_settings relative to CIP installation
        import sys
        cip_base_dir = os.path.dirname(os.path.dirname(__file__))
        repo_settings_dir = os.path.join(cip_base_dir, "repo-settings")
        if repo_settings_dir not in sys.path:
            sys.path.insert(0, repo_settings_dir)
        
        from detectors import detect_repo_type, load_repo_profile
        repo_type = detect_repo_type(root)
        profile_cfg = load_repo_profile(repo_type)
        
        # Apply profile settings to main config sections
        for section, kv in profile_cfg.items():
            if section == "profile":
                # Handle profile nesting - flatten profile.vivim to index level
                for profile_name, profile_data in kv.items():
                    if isinstance(profile_data, dict):
                        for sub_section, sub_kv in profile_data.items():
                            if sub_section in ("include", "exclude"):
                                # These go into index section
                                cfg.setdefault("index", {}).setdefault(sub_section, []).extend(sub_kv)
                            elif isinstance(sub_kv, dict):
                                cfg.setdefault(sub_section, {}).update(sub_kv)
                            elif isinstance(sub_kv, list):
                                cfg.setdefault(sub_section, {}).setdefault(sub_section, []).extend(sub_kv)
            elif isinstance(kv, dict):
                cfg.setdefault(section, {}).update(kv)
            elif isinstance(kv, list):
                cfg.setdefault(section, {}).setdefault(section, []).extend(kv)
    except Exception as e:
        # F-11/CORE-41: repo-settings profile load failed — surface instead of swallowing.
        log_swallowed("base.load_config.repo_settings", e)
        if warnings is not None:
            warnings.append("repo-settings profile load failed: %s" % e)
        # Fallback to basic config if detection fails
    
    # Load local repo config for overrides
    path = os.path.join(cip_dir(root), "config.toml")
    if os.path.exists(path):
        try:
            import tomllib
            with open(path, "rb") as f: data = tomllib.load(f)
        except ImportError:
            data = _parse_toml_naive(path)
        
        # Merge local overrides (lowest priority)
        for section, kv in data.items():
            if isinstance(kv, dict):
                cfg.setdefault(section, {}).update(kv)
    
    return cfg

def _excluded(rel_dir, name, extra):
    rel = name if rel_dir in (".", "") else f"{rel_dir}/{name}"
    # Check for substring matches (handles patterns like "__pycache__" anywhere in path)
    return any(pat in rel for pat in extra)

def iter_files(root, cfg):
    """Yield relative paths of indexable-size files. Uses os.scandir so the
    file size comes from the already-cached directory entry (one syscall per
    file instead of walk + a separate stat/getsize — important on Windows)."""
    maxb = int(cfg["index"]["max_file_kb"]) * 1024
    extra = list(cfg["index"]["exclude"])
    include_list = cfg.get("index", {}).get("include", [])
    root = os.path.abspath(root)
    
    # If include list is specified, start from those directories instead of root
    if include_list:
        stack = [os.path.join(root, inc) for inc in include_list if os.path.isdir(os.path.join(root, inc))]
    else:
        stack = [root]
    
    while stack:
        dirpath = stack.pop()
        try:
            with os.scandir(dirpath) as it:
                for e in it:
                    if e.is_dir(follow_symlinks=False):
                        if e.name in DEFAULT_EXCLUDES:
                            continue
                        if e.name.startswith(BACKUP_DIR_PREFIXES):
                            continue
                        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
                        if _excluded(rel_dir, e.name, extra):
                            continue
                        stack.append(e.path)
                    elif e.is_file(follow_symlinks=False):
                        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
                        file_rel_path = e.name if rel_dir == "." else f"{rel_dir}/{e.name}"
                        if _excluded(rel_dir, e.name, extra):
                            continue
                        try:
                            sz = e.stat(follow_symlinks=False).st_size
                        except OSError:
                            continue
                        if sz > maxb:
                            continue
                        yield file_rel_path
        except OSError:
            continue

def is_test_path(path, cfg=None):
    p = path.lower()
    globs = (cfg or {}).get("index", {}).get("test_globs", DEFAULT_CONFIG["index"]["test_globs"])
    return any(m in p for m in globs)

_IDENT_SPLIT = re.compile(r"[^0-9A-Za-z_$]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

def tokenize(text):
    out = []
    for part in _IDENT_SPLIT.split(text):
        if not part: continue
        for piece in part.replace("_", " ").split():
            for tok in _CAMEL.split(piece):
                t = tok.lower()
                if len(t) > 1: out.append(t)
    return out

def est_tokens(text):
    return max(1, len(text) // 4)
