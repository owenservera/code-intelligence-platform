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
    for rel in iter_files(root, cfg):
        l = lang_for(rel)
        if l: counts[l] = counts.get(l, 0) + 1
        if os.path.dirname(rel) == "" and os.path.basename(rel) in MANIFESTS:
            stacks.append(MANIFESTS[os.path.basename(rel)])
    primary = max(counts, key=counts.get) if counts else "unknown"
    return {"languages": counts, "primary": primary, "stacks": sorted(set(stacks))}
