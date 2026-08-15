"""Tauri stack pack: indexes Tauri commands, capability manifests, and IPC surface.
Powers security analysis for Tauri desktop applications (like Vivim)."""
import os, re, json
from .common import ensure

COMMAND_RE = re.compile(r'#\[tauri::command\]\s*(?:#\[.*?\]\s*)*fn\s+(\w+)\s*\(([^)]*)\)')
CAPABILITY_RE = re.compile(r'"allow":\s*\[\s*\{[^}]*"cmd":\s*"([^"]+)"')

def find_tauri_root(root):
    """Find the Tauri source directory (typically src-tauri/)."""
    for candidate in ["src-tauri", "tauri", ".tauri"]:
        path = os.path.join(root, candidate)
        if os.path.isdir(path):
            return candidate
    return None

def find_capabilities(root, tauri_dir):
    """Find Tauri capability manifest files."""
    caps_dir = os.path.join(root, tauri_dir, "capabilities")
    if not os.path.isdir(caps_dir):
        return []
    
    capability_files = []
    for filename in os.listdir(caps_dir):
        if filename.endswith(".json"):
            capability_files.append(os.path.join(caps_dir, filename))
    
    return capability_files

def parse_capabilities(capability_files):
    """Parse Tauri capability manifests to extract allowed commands."""
    allowed_commands = set()
    
    for cap_file in capability_files:
        try:
            with open(cap_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all "cmd" entries in "allow" sections
            for match in CAPABILITY_RE.finditer(content):
                allowed_commands.add(match.group(1))
                
        except (OSError, json.JSONDecodeError):
            continue
    
    return allowed_commands

def index_commands(root, tauri_dir):
    """Index all Tauri commands defined in Rust source files."""
    commands = []
    src_dir = os.path.join(root, tauri_dir, "src")
    
    if not os.path.isdir(src_dir):
        return commands
    
    for dirpath, dirnames, filenames in os.walk(src_dir):
        for filename in filenames:
            if not filename.endswith(".rs"):
                continue
                
            file_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(file_path, root).replace(os.sep, "/")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except OSError:
                continue
            
            # Find Tauri command definitions
            for match in COMMAND_RE.finditer(content):
                command_name = match.group(1)
                args = match.group(2)
                line_num = content.count('\n', 0, match.start()) + 1
                
                commands.append({
                    "name": command_name,
                    "args": args,
                    "file": rel_path,
                    "line": line_num
                })
    
    return commands

def index_stack(con, root):
    """Persist Tauri commands and capability mappings. Returns stats."""
    from .common import ensure
    ensure(con)
    
    tauri_dir = find_tauri_root(root)
    if not tauri_dir:
        return {"commands": 0, "capabilities": 0, "tauri_dir": None}
    
    # Index commands
    commands = index_commands(root, tauri_dir)
    
    # Index capabilities
    capability_files = find_capabilities(root, tauri_dir)
    allowed_commands = parse_capabilities(capability_files)
    
    # Store in database
    con.execute("DELETE FROM tauri_commands")
    con.execute("DELETE FROM tauri_capabilities")
    
    for cmd in commands:
        is_allowed = cmd["name"] in allowed_commands
        con.execute(
            "INSERT INTO tauri_commands(name, args, file, line, is_allowed) VALUES(?,?,?,?,?)",
            (cmd["name"], cmd["args"], cmd["file"], cmd["line"], is_allowed)
        )
    
    for cap_cmd in allowed_commands:
        con.execute(
            "INSERT OR IGNORE INTO tauri_capabilities(command) VALUES(?)",
            (cap_cmd,)
        )
    
    con.commit()
    
    return {
        "commands": len(commands),
        "capabilities": len(allowed_commands),
        "tauri_dir": tauri_dir
    }

def commands_report(root=None):
    """Generate a report of Tauri commands and their capability status."""
    from ..base import repo_root
    from ..store import connect
    
    root = root or repo_root()
    con = connect(root)
    ensure(con)
    
    # Ensure tables exist
    con.execute("""
        CREATE TABLE IF NOT EXISTS tauri_commands (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            args TEXT,
            file TEXT,
            line INTEGER,
            is_allowed INTEGER DEFAULT 0
        )
    """)
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS tauri_capabilities (
            id INTEGER PRIMARY KEY,
            command TEXT NOT NULL UNIQUE
        )
    """)
    
    if con.execute("SELECT COUNT(*) c FROM tauri_commands").fetchone()["c"] == 0:
        index_stack(con, root)
    
    # Get all commands with their capability status
    commands = []
    for row in con.execute("SELECT name, args, file, line, is_allowed FROM tauri_commands ORDER BY name"):
        commands.append({
            "name": row["name"],
            "args": row["args"],
            "file": row["file"],
            "line": row["line"],
            "is_allowed": bool(row["is_allowed"])
        })
    
    # Count ungated commands
    ungated_count = sum(1 for cmd in commands if not cmd["is_allowed"])
    
    return {
        "commands": commands,
        "total": len(commands),
        "ungated": ungated_count,
        "gated": len(commands) - ungated_count
    }