"""Core utilities: repo discovery, config, hashing, file iteration, tokenizing."""
import hashlib, os, re

CIP_DIRNAME = ".cip"

DEFAULT_EXCLUDES = {
    ".git", "node_modules", "dist", "build", "out", ".next", ".nuxt",
    "__pycache__", ".venv", "venv", "target", "vendor", "coverage",
    ".pytest_cache", ".mypy_cache", ".idea", ".vscode", ".turbo",
    ".cache", "tmp", ".cip",
}

DEFAULT_CONFIG = {
    "index": {"max_file_kb": 512, "exclude": [],
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
}

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

def load_config(root):
    import copy
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    path = os.path.join(cip_dir(root), "config.toml")
    if not os.path.exists(path):
        return cfg
    try:
        import tomllib
        with open(path, "rb") as f: data = tomllib.load(f)
    except ImportError:
        data = _parse_toml_naive(path)
    for section, kv in data.items():
        if isinstance(kv, dict):
            cfg.setdefault(section, {}).update(kv)
    return cfg

def _excluded(rel_dir, name, extra):
    rel = name if rel_dir in (".", "") else f"{rel_dir}/{name}"
    return any(pat in rel for pat in extra)

def iter_files(root, cfg):
    """Yield relative paths of indexable-size files. Uses os.scandir so the
    file size comes from the already-cached directory entry (one syscall per
    file instead of walk + a separate stat/getsize — important on Windows)."""
    maxb = int(cfg["index"]["max_file_kb"]) * 1024
    extra = list(cfg["index"]["exclude"])
    root = os.path.abspath(root)
    stack = [root]
    while stack:
        dirpath = stack.pop()
        try:
            with os.scandir(dirpath) as it:
                for e in it:
                    if e.is_dir(follow_symlinks=False):
                        if e.name in DEFAULT_EXCLUDES:
                            continue
                        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
                        if _excluded(rel_dir, e.name, extra):
                            continue
                        stack.append(e.path)
                    elif e.is_file(follow_symlinks=False):
                        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
                        if _excluded(rel_dir, e.name, extra):
                            continue
                        try:
                            sz = e.stat(follow_symlinks=False).st_size
                        except OSError:
                            continue
                        if sz > maxb:
                            continue
                        yield e.name if rel_dir == "." else f"{rel_dir}/{e.name}"
        except OSError:
            continue

def is_test_path(path, cfg):
    p = path.lower()
    return any(m in p for m in cfg["index"]["test_globs"])

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
