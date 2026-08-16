"""
Repository Map Generator - Token-budgeted architecture overview.
Inspired by Aider's repo map for LLM context optimization.
"""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from .parsers import parse_file
from .detect import lang_for
from .base import tokenize

@dataclass
class RepoMapConfig:
    max_tokens: int = 4096
    include_signatures: bool = True
    include_docstrings: bool = False
    group_by_directory: bool = True

def generate_repo_map(root: str, config: Optional[RepoMapConfig] = None) -> str:
    """Generate a token-efficient map of the entire repository."""
    config = config or RepoMapConfig()
    
    symbols_by_file = {}
    all_files = _collect_source_files(root)
    
    for file_path in all_files:
        rel_path = os.path.relpath(file_path, root)
        language = lang_for(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source = f.read()
            
            parsed = parse_file(rel_path, language, source)
            if parsed and 'symbols' in parsed:
                symbols_by_file[rel_path] = parsed['symbols']
        except Exception:
            continue
    
    # Build tree-sitter style signature map
    map_lines = []
    current_tokens = 0
    
    for file_path in sorted(symbols_by_file.keys()):
        symbols = symbols_by_file[file_path]
        
        if config.group_by_directory:
            map_lines.append(f"\n{file_path}:")
            current_tokens += len(tokenize(file_path)) + 1
        
        for symbol in symbols:
            if symbol.get('kind') in ('function', 'method', 'class', 'interface'):
                signature = _format_signature(symbol, config)
                if signature:
                    sig_tokens = len(tokenize(signature))
                    
                    if current_tokens + sig_tokens > config.max_tokens:
                        map_lines.append(f"  ... ({len(symbols_by_file[file_path]) - len(map_lines)} more symbols)")
                        break
                    
                    map_lines.append(f"  {signature}")
                    current_tokens += sig_tokens
    
    return '\n'.join(map_lines)

def _format_signature(symbol: Dict, config: RepoMapConfig) -> str:
    """Format a symbol as a compact signature."""
    kind = symbol.get('kind', '')
    name = symbol.get('name', '')
    signature = symbol.get('signature', '')
    
    if kind == 'class':
        return f"class {name}"
    elif kind in ('function', 'method'):
        if signature:
            return signature
        return f"def {name}()"
    elif kind == 'interface':
        return f"interface {name}"
    
    return None

def _collect_source_files(root: str) -> List[str]:
    """Collect all source files, excluding common build/dependency dirs."""
    exclude_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build'}
    include_exts = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', '.cpp', '.c', '.h'}
    
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in include_exts:
                files.append(os.path.join(dirpath, filename))
    
    return files

# CLI command handler
def handle_map_command(root, args):
    """Generate repository map."""
    max_tokens = getattr(args, 'max_tokens', 4096)
    config = RepoMapConfig(max_tokens=max_tokens)
    
    repo_map = generate_repo_map(root, config)
    print(repo_map)
