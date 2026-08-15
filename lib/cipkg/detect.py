"""Language/framework detection — the repo-agnostic cold start."""
import os

EXT_LANG = {
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".py": "python", ".rs": "rust", ".go": "go", ".java": "java", ".kt": "kotlin",
    ".rb": "ruby", ".cs": "csharp", ".cpp": "cpp", ".cc": "cpp", ".c": "c", ".h": "c",
    ".swift": "swift", ".php": "php", ".scala": "scala", ".zig": "zig", ".lua": "lua",
    ".sh": "shell", ".sql": "sql", ".vue": "vue", ".svelte": "svelte",
}

MANIFESTS = {
    "package.json": "node", "pyproject.toml": "python", "setup.py": "python",
    "Cargo.toml": "rust", "go.mod": "go", "pom.xml": "java",
    "build.gradle": "java", "Gemfile": "ruby", "composer.json": "php",
}

def lang_for(path):
    return EXT_LANG.get(os.path.splitext(path)[1].lower(), "")

def detect(root, cfg):
    from .base import iter_files
    counts, stacks = {}, []
    multi_roots = []
    
    # Detect multi-root workspaces (e.g., monorepos with multiple apps)
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        if rel.count("/") > 1:  # Only check top-level directories
            dirnames[:] = []
            continue
        
        # Check for independent package roots
        if any(f in filenames for f in ["package.json", "Cargo.toml", "go.mod"]):
            if rel != ".":
                multi_roots.append(rel)
    
    for rel in iter_files(root, cfg):
        l = lang_for(rel)
        if l: counts[l] = counts.get(l, 0) + 1
        if os.path.dirname(rel) == "" and os.path.basename(rel) in MANIFESTS:
            stacks.append(MANIFESTS[os.path.basename(rel)])
    primary = max(counts, key=counts.get) if counts else "unknown"
    return {"languages": counts, "primary": primary, "stacks": sorted(set(stacks)), "multi_roots": multi_roots}
