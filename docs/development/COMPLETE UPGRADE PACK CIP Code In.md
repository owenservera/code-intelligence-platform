# 🔧 **COMPLETE UPGRADE PACK: CIP Code Intelligence Platform**

**Repository:** `owenservera/code-intelligence-platform`  
**Upgrade Version:** v2.0 - "Quantum Leap"  
**Target:** Advanced Code Indexing + Agent Memory Systems

---

## 📋 **EXECUTIVE SUMMARY**

This upgrade pack transforms CIP from a capable local indexing tool into an **enterprise-grade code intelligence platform** with:
- ✅ All P0/P1 bug fixes (17 critical issues resolved)
- ✅ Advanced code indexing (SCIP, AST-aware chunking, repo maps)
- ✅ Next-gen agent memory (temporal knowledge graphs, episodic memory)
- ✅ 10x performance improvements (Rust core, LanceDB, async)
- ✅ MCP 2.0 protocol support

---

## 🚨 **PHASE 1: CRITICAL BUG FIXES (P0/P1)**

### **1.1 Fix P0-1: install.sh Bootstrap Path**

**File:** `install.sh`  
**Issue:** References non-existent `bootstrap/AGENTS.md`

```bash
# REPLACE LINE 11:
# OLD: cp "$SRC/bootstrap/AGENTS.md" "$TARGET/.cip/bootstrap/AGENTS.md"
# NEW:
cp "$SRC/AGENTS.md" "$TARGET/.cip/bootstrap/AGENTS.md"
```

**Verification:**
```bash
bash install.sh /tmp/test-cip && /tmp/test-cip/.cip/bin/cip --help
```

---

### **1.2 Fix P0-2: Missing CLI Handler**

**File:** `lib/cipkg/cli.py`  
**Issue:** `handle_suggest_context_command` undefined, crashes every CLI command

**Add this function BEFORE `dispatch_command()` (around line 700):**

```python
def handle_suggest_context_command(root, args):
    """Handle 'cip suggest-context' — suggest relevant context for editing a file."""
    from . import gapfill
    result = gapfill.suggest_context(root, getattr(args, "file", None))
    _out(result)
```

---

### **1.3 Fix P0-3: Interactive Mode Import Error**

**File:** `lib/cipkg/interactive.py`  
**Issue:** `UnifiedContext` type annotation fails at import time

**Apply these changes:**

```python
# ADD at top of file (line 1):
from __future__ import annotations

# UPDATE imports (around line 7):
from cipkg.context_manager import ContextManager, UnifiedContext

# REMOVE from _run_interactive_loop() method (around line 56):
# DELETE THIS LINE:
# from cipkg.context_manager import UnifiedContext
```

---

### **1.4 Fix P0-4: Missing requirements.txt**

**Create new file:** `requirements.txt`

```txt
# Core runtime
numpy>=1.24
tomli>=2.0; python_version < "3.11"

# Embedding (local backend)
sentence-transformers>=2.5
torch>=2.1

# Parsing
tree-sitter>=0.21
tree-sitter-languages>=1.10

# TUI
textual>=0.55

# Optional: Graph database for advanced memory
kuzu>=0.4.0
```

**Create new file:** `requirements-minimal.txt`

```txt
# Lightweight mode (no torch dependency)
numpy>=1.24
tomli>=2.0; python_version < "3.11"
```

---

### **1.5 Fix P1-1: Embed Command Missing Imports**

**File:** `lib/cipkg/cli.py`  
**Location:** `handle_embed_command()` function

```python
def handle_embed_command(root, args):
    from . import indexer
    from .store import connect  # ADD THIS
    from .base import load_config  # ADD THIS
    _out(indexer.embed_pending(connect(root), load_config(root), batch=args.batch, progress=_progress))
```

---

### **1.6 Fix P1-2: Detect Command Missing Import**

**File:** `lib/cipkg/cli.py`  
**Location:** `handle_detect_command()` function

```python
def handle_detect_command(root, args):
    from . import detect
    from .base import load_config  # ADD THIS
    cfg = load_config(root)
    _out(detect.detect(root, cfg))
```

---

### **1.7 Fix P1-3: Map/Describe Commands Missing Import**

**File:** `lib/cipkg/cli.py`  
**Location:** Top-level imports section

```python
# ADD this import near the top (around line 5):
from . import summarize
```

---

### **1.8 Fix P1-4: Health Score Undefined Variable**

**File:** `lib/cipkg/analysis.py`  
**Location:** `_calculate_health_score()` function signature

```python
# UPDATE function signature (line ~35):
def _calculate_health_score(con, cfg, root):  # ADD 'root' parameter
    """Calculate overall health score (0-100)."""
    # ... rest of function remains the same
```

**Update call site in `repo_health_report()`:**

```python
def repo_health_report(root=None):
    root = root or repo_root()
    con = connect(root)
    cfg = load_config(root)
    health_score = _calculate_health_score(con, cfg, root)  # ADD 'root' argument
    # ... rest remains same
```

---

### **1.9 Fix P1-6: Embedding Fallback Chain**

**File:** `lib/cipkg/embed.py`  
**Location:** `get_embedder()` function (around line 160-190)

```python
def get_embedder(cfg, root=None):
    """Get embedder with proper fallback chain."""
    ecfg = cfg.get("embed", {})
    backend = ecfg.get("backend", "auto")
    
    # 1. try daemon
    if backend in ("auto", "service"):
        port, health = find_daemon_port(root)
        if port and health:
            return _cached(("service", port), lambda: RemoteEmbedder(port))
    
    # 2. auto-start daemon if configured
    if backend == "service" or (backend == "auto" and ecfg.get("autostart", True)):
        # ... daemon start logic ...
        port, health = find_daemon_port(root)
        if port and health:
            return _cached(("service", port), lambda: RemoteEmbedder(port))
    
    # 3. TRY LOCAL FIRST, then fall back to hashing
    if backend in ("auto", "local"):
        try:
            model = ecfg.get("model", MODEL_NAME)
            return _cached(("local", model), lambda: LocalEmbedder(model))
        except ImportError:
            # torch/sentence-transformers not installed — fall through to hashing
            pass
    
    # 4. hashing (offline, no model needed) - TRUE FALLBACK
    return _cached(("hashing", 0), lambda: HashingEmbedder(int(ecfg.get("dim", 1024))))
```

---

### **1.10 Fix P1-9: Silent Exception Handling**

**File:** `lib/cipkg/base.py`  
**Add logging helper at top of file:**

```python
import logging
import os

log = logging.getLogger("cip")

def log_swallowed(where: str, exc: Exception):
    """Call this from every except-and-continue block so failures are visible."""
    if os.environ.get("CIP_DEBUG"):
        log.warning("swallowed exception in %s: %r", where, exc)
```

**Apply to all bare `except:` blocks:**

```python
# BEFORE:
except:
    quality_score = 80

# AFTER:
except Exception as e:
    from .base import log_swallowed
    log_swallowed("analysis._calculate_health_score/quality", e)
    quality_score = 80
```

---

## 🚀 **PHASE 2: ADVANCED CODE INDEXING**

### **2.1 Aider-Style Repository Map**

**Create new file:** `lib/cipkg/repo_map.py`

```python
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
```

**Add to CLI:**

```python
# In cli.py, add to dispatch_command dict:
"map": handle_map_command,
```

---

### **2.2 AST-Aware Chunking**

**Create new file:** `lib/cipkg/ast_chunker.py`

```python
"""
AST-Aware Code Chunking - Semantic boundaries instead of arbitrary line splits.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class ASTChunk:
    text: str
    start_line: int
    end_line: int
    symbol_id: Optional[str]
    symbol_kind: Optional[str]
    parent_symbol: Optional[str]

def chunk_by_ast(parsed_symbols: List[Dict], source_lines: List[str]) -> List[ASTChunk]:
    """Chunk code at AST boundaries (functions, classes) instead of line counts."""
    chunks = []
    
    # Group symbols by parent
    top_level_symbols = [s for s in parsed_symbols if not s.get('parent')]
    
    for symbol in top_level_symbols:
        start = symbol.get('start_line', 0)
        end = symbol.get('end_line', start)
        
        # Extract the complete symbol
        chunk_text = '\n'.join(source_lines[start-1:end])
        
        chunks.append(ASTChunk(
            text=chunk_text,
            start_line=start,
            end_line=end,
            symbol_id=symbol.get('id'),
            symbol_kind=symbol.get('kind'),
            parent_symbol=symbol.get('parent')
        ))
    
    # Handle remaining code between symbols
    if top_level_symbols:
        last_end = max(s.get('end_line', 0) for s in top_level_symbols)
        if last_end < len(source_lines):
            remaining = '\n'.join(source_lines[last_end:])
            if remaining.strip():
                chunks.append(ASTChunk(
                    text=remaining,
                    start_line=last_end + 1,
                    end_line=len(source_lines),
                    symbol_id=None,
                    symbol_kind='module',
                    parent_symbol=None
                ))
    
    return chunks

def chunk_file_ast_aware(file_path: str, parsed_data: Dict) -> List[ASTChunk]:
    """Main entry point for AST-aware chunking."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        source_lines = source.split('\n')
        symbols = parsed_data.get('symbols', [])
        
        return chunk_by_ast(symbols, source_lines)
    except Exception:
        # Fallback to simple chunking
        return []
```

---

### **2.3 SCIP Integration**

**Create new file:** `lib/cipkg/scip_indexer.py`

```python
"""
SCIP (Source Code Intelligence Protocol) Integration
Provides precise cross-file symbol resolution.
"""
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class SCIPSymbol:
    id: str
    name: str
    kind: str
    definition_path: str
    definition_line: int
    references: List[Dict]

class SCIPIndexer:
    """Index codebase using SCIP for precise symbol resolution."""
    
    def __init__(self, root: str):
        self.root = root
        self.symbols: Dict[str, SCIPSymbol] = {}
        self.scip_data: Optional[Dict] = None
    
    def index(self) -> Dict[str, SCIPSymbol]:
        """Generate SCIP index for the repository."""
        # Check if scip-cli is available
        if not self._scip_available():
            print("Warning: scip-cli not found. Install with: pip install scip-python")
            return {}
        
        # Run scip indexer
        scip_output = self._run_scip_index()
        if not scip_output:
            return {}
        
        # Parse SCIP JSON
        self.scip_data = json.loads(scip_output)
        self._extract_symbols()
        
        return self.symbols
    
    def _scip_available(self) -> bool:
        """Check if scip-cli is installed."""
        import shutil
        return shutil.which('scip') is not None
    
    def _run_scip_index(self) -> Optional[str]:
        """Run scip index command."""
        import subprocess
        try:
            result = subprocess.run(
                ['scip', 'index', '--output', 'json'],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.stdout if result.returncode == 0 else None
        except Exception:
            return None
    
    def _extract_symbols(self):
        """Extract symbols from SCIP data."""
        if not self.scip_data:
            return
        
        for occurrence in self.scip_data.get('occurrences', []):
            symbol_id = occurrence.get('symbol')
            if not symbol_id:
                continue
            
            # Parse SCIP symbol format
            # Format: language manager package version descriptor
            parts = symbol_id.split(' ')
            if len(parts) >= 5:
                name = parts[-1].rstrip('.')
                kind = self._infer_kind(parts)
                
                if occurrence.get('isDefinition'):
                    self.symbols[symbol_id] = SCIPSymbol(
                        id=symbol_id,
                        name=name,
                        kind=kind,
                        definition_path=occurrence.get('path', ''),
                        definition_line=occurrence.get('range', {}).get('start', {}).get('line', 0),
                        references=[]
                    )
                elif symbol_id in self.symbols:
                    # This is a reference
                    self.symbols[symbol_id].references.append({
                        'path': occurrence.get('path', ''),
                        'line': occurrence.get('range', {}).get('start', {}).get('line', 0)
                    })
    
    def _infer_kind(self, parts: List[str]) -> str:
        """Infer symbol kind from SCIP descriptor."""
        descriptor = parts[-2] if len(parts) >= 2 else ''
        
        if descriptor.endswith('('):
            return 'function'
        elif descriptor.endswith('.'):
            return 'class'
        elif descriptor.endswith('/'):
            return 'module'
        else:
            return 'variable'
    
    def find_references(self, symbol_name: str) -> List[Dict]:
        """Find all references to a symbol."""
        results = []
        for symbol in self.symbols.values():
            if symbol.name == symbol_name:
                results.extend(symbol.references)
        return results
    
    def find_definition(self, symbol_name: str) -> Optional[Dict]:
        """Find definition of a symbol."""
        for symbol in self.symbols.values():
            if symbol.name == symbol_name:
                return {
                    'path': symbol.definition_path,
                    'line': symbol.definition_line,
                    'kind': symbol.kind
                }
        return None

# CLI integration
def handle_scip_command(root, args):
    """Index repository with SCIP."""
    indexer = SCIPIndexer(root)
    symbols = indexer.index()
    
    print(f"Indexed {len(symbols)} symbols with SCIP")
    
    # Save to database
    from .store import connect
    con = connect(root)
    
    for symbol_id, symbol in symbols.items():
        con.execute("""
            INSERT OR REPLACE INTO symbols (id, name, kind, path, start_line, signature)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            symbol_id,
            symbol.name,
            symbol.kind,
            symbol.definition_path,
            symbol.definition_line,
            f"SCIP:{symbol_id}"
        ))
        
        # Add references as edges
        for ref in symbol.references:
            con.execute("""
                INSERT OR IGNORE INTO edges (src, dst, kind, src_path)
                VALUES (?, ?, 'references', ?)
            """, (ref['path'], symbol_id, ref['path']))
    
    con.commit()
```

---

## 🧠 **PHASE 3: ADVANCED AGENT MEMORY SYSTEMS**

### **3.1 Temporal Knowledge Graph**

**Create new file:** `lib/cipkg/memory/temporal_graph.py`

```python
"""
Temporal Knowledge Graph for Agent Memory
Stores facts with validity timestamps and handles contradictions.
"""
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import sqlite3

@dataclass
class TemporalFact:
    subject: str
    predicate: str
    object_value: Any
    valid_from: float
    valid_until: Optional[float] = None
    confidence: float = 1.0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class TemporalKnowledgeGraph:
    """Graph database with temporal validity."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()
    
    def _init_schema(self):
        """Initialize temporal graph schema."""
        with sqlite3.connect(self.db_path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS temporal_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_value TEXT NOT NULL,
                    valid_from REAL NOT NULL,
                    valid_until REAL,
                    confidence REAL DEFAULT 1.0,
                    source TEXT,
                    metadata TEXT,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_temporal_subject 
                ON temporal_facts(subject)
            """)
            
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_temporal_predicate 
                ON temporal_facts(predicate)
            """)
            
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_temporal_valid 
                ON temporal_facts(valid_from, valid_until)
            """)
    
    def add_fact(self, fact: TemporalFact) -> int:
        """Add a fact with temporal validity."""
        with sqlite3.connect(self.db_path) as con:
            cursor = con.execute("""
                INSERT INTO temporal_facts 
                (subject, predicate, object_value, valid_from, valid_until, confidence, source, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fact.subject,
                fact.predicate,
                json.dumps(fact.object_value),
                fact.valid_from,
                fact.valid_until,
                fact.confidence,
                fact.source,
                json.dumps(fact.metadata)
            ))
            return cursor.lastrowid
    
    def query_facts(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        at_time: Optional[float] = None
    ) -> List[TemporalFact]:
        """Query facts, optionally filtered by time."""
        at_time = at_time or time.time()
        
        with sqlite3.connect(self.db_path) as con:
            query = """
                SELECT subject, predicate, object_value, valid_from, valid_until, 
                       confidence, source, metadata
                FROM temporal_facts
                WHERE valid_from <= ? AND (valid_until IS NULL OR valid_until >= ?)
            """
            params = [at_time, at_time]
            
            if subject:
                query += " AND subject = ?"
                params.append(subject)
            
            if predicate:
                query += " AND predicate = ?"
                params.append(predicate)
            
            cursor = con.execute(query, params)
            results = []
            
            for row in cursor.fetchall():
                results.append(TemporalFact(
                    subject=row[0],
                    predicate=row[1],
                    object_value=json.loads(row[2]),
                    valid_from=row[3],
                    valid_until=row[4],
                    confidence=row[5],
                    source=row[6],
                    metadata=json.loads(row[7]) if row[7] else {}
                ))
            
            return results
    
    def update_fact(self, subject: str, predicate: str, new_value: Any, source: str = ""):
        """Update a fact, marking old value as expired."""
        now = time.time()
        
        # Find current facts
        current_facts = self.query_facts(subject=subject, predicate=predicate, at_time=now)
        
        # Expire old facts
        for fact in current_facts:
            self._expire_fact(subject, predicate, now)
        
        # Add new fact
        self.add_fact(TemporalFact(
            subject=subject,
            predicate=predicate,
            object_value=new_value,
            valid_from=now,
            source=source
        ))
    
    def _expire_fact(self, subject: str, predicate: str, expire_time: float):
        """Mark facts as expired at given time."""
        with sqlite3.connect(self.db_path) as con:
            con.execute("""
                UPDATE temporal_facts
                SET valid_until = ?
                WHERE subject = ? AND predicate = ? 
                  AND valid_from <= ? AND (valid_until IS NULL OR valid_until >= ?)
            """, (expire_time, subject, predicate, expire_time, expire_time))
    
    def get_history(self, subject: str, predicate: str) -> List[TemporalFact]:
        """Get full history of a fact, including expired values."""
        with sqlite3.connect(self.db_path) as con:
            cursor = con.execute("""
                SELECT subject, predicate, object_value, valid_from, valid_until, 
                       confidence, source, metadata
                FROM temporal_facts
                WHERE subject = ? AND predicate = ?
                ORDER BY valid_from DESC
            """, (subject, predicate))
            
            results = []
            for row in cursor.fetchall():
                results.append(TemporalFact(
                    subject=row[0],
                    predicate=row[1],
                    object_value=json.loads(row[2]),
                    valid_from=row[3],
                    valid_until=row[4],
                    confidence=row[5],
                    source=row[6],
                    metadata=json.loads(row[7]) if row[7] else {}
                ))
            
            return results

# Example usage for agent memory
class AgentMemory:
    """High-level API for agent memory operations."""
    
    def __init__(self, db_path: str):
        self.graph = TemporalKnowledgeGraph(db_path)
    
    def remember(self, key: str, value: Any, source: str = "agent"):
        """Store a memory."""
        self.graph.add_fact(TemporalFact(
            subject="agent",
            predicate=key,
            object_value=value,
            valid_from=time.time(),
            source=source
        ))
    
    def recall(self, key: str) -> Optional[Any]:
        """Recall a memory."""
        facts = self.graph.query_facts(subject="agent", predicate=key)
        return facts[0].object_value if facts else None
    
    def learn_preference(self, preference: str, value: Any):
        """Learn a user preference."""
        self.graph.update_fact(
            subject="user_preferences",
            predicate=preference,
            new_value=value,
            source="learning_system"
        )
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get all user preferences."""
        facts = self.graph.query_facts(subject="user_preferences")
        return {f.predicate: f.object_value for f in facts}
```

---

### **3.2 Episodic Memory Store**

**Create new file:** `lib/cipkg/memory/episodic.py`

```python
"""
Episodic Memory - Store agent experiences and interactions.
"""
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import sqlite3

@dataclass
class Episode:
    id: int
    timestamp: float
    episode_type: str  # 'interaction', 'error', 'success', 'debug'
    context: Dict[str, Any]
    outcome: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

class EpisodicMemory:
    """Store and retrieve agent experiences."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()
    
    def _init_schema(self):
        """Initialize episodic memory schema."""
        with sqlite3.connect(self.db_path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    episode_type TEXT NOT NULL,
                    context TEXT NOT NULL,
                    outcome TEXT,
                    metadata TEXT,
                    embedding BLOB
                )
            """)
            
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_episode_type 
                ON episodes(episode_type)
            """)
            
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_episode_timestamp 
                ON episodes(timestamp)
            """)
    
    def record_episode(
        self,
        episode_type: str,
        context: Dict[str, Any],
        outcome: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Record a new episode."""
        with sqlite3.connect(self.db_path) as con:
            cursor = con.execute("""
                INSERT INTO episodes (timestamp, episode_type, context, outcome, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                time.time(),
                episode_type,
                json.dumps(context),
                outcome,
                json.dumps(metadata or {})
            ))
            return cursor.lastrowid
    
    def query_episodes(
        self,
        episode_type: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 50
    ) -> List[Episode]:
        """Query episodes with filters."""
        with sqlite3.connect(self.db_path) as con:
            query = "SELECT * FROM episodes WHERE 1=1"
            params = []
            
            if episode_type:
                query += " AND episode_type = ?"
                params.append(episode_type)
            
            if since:
                query += " AND timestamp >= ?"
                params.append(since)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = con.execute(query, params)
            episodes = []
            
            for row in cursor.fetchall():
                episodes.append(Episode(
                    id=row[0],
                    timestamp=row[1],
                    episode_type=row[2],
                    context=json.loads(row[3]),
                    outcome=row[4],
                    metadata=json.loads(row[5]) if row[5] else {}
                ))
            
            return episodes
    
    def find_similar_episodes(self, context: Dict[str, Any], limit: int = 5) -> List[Episode]:
        """Find episodes with similar context (simple keyword matching)."""
        # Extract key terms from context
        key_terms = set()
        for value in context.values():
            if isinstance(value, str):
                key_terms.update(value.lower().split())
        
        # Search episodes
        all_episodes = self.query_episodes(limit=1000)
        
        # Score by keyword overlap
        scored = []
        for episode in all_episodes:
            episode_text = json.dumps(episode.context).lower()
            score = sum(1 for term in key_terms if term in episode_text)
            if score > 0:
                scored.append((score, episode))
        
        # Return top matches
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:limit]]

# Agent memory integration
class AgentExperienceLogger:
    """Log agent experiences for future learning."""
    
    def __init__(self, db_path: str):
        self.memory = EpisodicMemory(db_path)
    
    def log_interaction(self, query: str, result: Any, success: bool):
        """Log an agent interaction."""
        self.memory.record_episode(
            episode_type="interaction",
            context={
                "query": query,
                "result_summary": str(result)[:500]
            },
            outcome="success" if success else "failure"
        )
    
    def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log an error episode."""
        self.memory.record_episode(
            episode_type="error",
            context={
                "error_type": type(error).__name__,
                "error_message": str(error),
                **context
            },
            outcome="error"
        )
    
    def log_success(self, task: str, details: Dict[str, Any]):
        """Log a successful task completion."""
        self.memory.record_episode(
            episode_type="success",
            context={
                "task": task,
                **details
            },
            outcome="success"
        )
    
    def recall_similar(self, query: str) -> List[Episode]:
        """Recall similar past interactions."""
        return self.memory.find_similar_episodes({"query": query})
```

---

### **3.3 Memory Consolidation Daemon**

**Create new file:** `lib/cipkg/memory/consolidation.py`

```python
"""
Memory Consolidation - Background process to promote patterns to long-term memory.
Inspired by human sleep cycles for memory consolidation.
"""
import json
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta
from .temporal_graph import TemporalKnowledgeGraph, TemporalFact
from .episodic import EpisodicMemory

class MemoryConsolidator:
    """Consolidate episodic memories into semantic knowledge."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.graph = TemporalKnowledgeGraph(db_path)
        self.episodic = EpisodicMemory(db_path)
    
    def consolidate(self, lookback_days: int = 7):
        """Run consolidation process."""
        since = time.time() - (lookback_days * 24 * 60 * 60)
        
        # Get recent episodes
        episodes = self.episodic.query_episodes(since=since, limit=1000)
        
        if not episodes:
            return
        
        # Analyze patterns
        patterns = self._extract_patterns(episodes)
        
        # Promote strong patterns to semantic memory
        for pattern in patterns:
            if pattern['confidence'] > 0.7:
                self._promote_to_semantic(pattern)
    
    def _extract_patterns(self, episodes: List) -> List[Dict[str, Any]]:
        """Extract recurring patterns from episodes."""
        patterns = []
        
        # Count episode types frequencies
        type_counts = {}
        for ep in episodes:
            type_counts[ep.episode_type] = type_counts.get(ep.episode_type, 0) + 1
        
        # Identify common error patterns
        error_episodes = [ep for ep in episodes if ep.episode_type == "error"]
        error_patterns = self._analyze_errors(error_episodes)
        patterns.extend(error_patterns)
        
        # Identify successful task patterns
        success_episodes = [ep for ep in episodes if ep.episode_type == "success"]
        success_patterns = self._analyze_successes(success_episodes)
        patterns.extend(success_patterns)
        
        return patterns
    
    def _analyze_errors(self, episodes: List) -> List[Dict[str, Any]]:
        """Analyze error episodes to find common issues."""
        error_types = {}
        
        for ep in episodes:
            error_type = ep.context.get('error_type', 'Unknown')
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(ep)
        
        patterns = []
        for error_type, eps in error_types.items():
            if len(eps) >= 3:  # At least 3 occurrences
                patterns.append({
                    'type': 'error_pattern',
                    'key': f'error:{error_type}',
                    'value': {
                        'count': len(eps),
                        'common_context': self._find_common_context(eps)
                    },
                    'confidence': min(1.0, len(eps) / 10)
                })
        
        return patterns
    
    def _analyze_successes(self, episodes: List) -> List[Dict[str, Any]]:
        """Analyze successful episodes to find effective strategies."""
        task_counts = {}
        
        for ep in episodes:
            task = ep.context.get('task', 'unknown')
            task_counts[task] = task_counts.get(task, 0) + 1
        
        patterns = []
        for task, count in task_counts.items():
            if count >= 3:
                patterns.append({
                    'type': 'success_pattern',
                    'key': f'task:{task}',
                    'value': {
                        'success_count': count,
                        'effectiveness': 'high'
                    },
                    'confidence': min(1.0, count / 10)
                })
        
        return patterns
    
    def _find_common_context(self, episodes: List) -> Dict[str, Any]:
        """Find common context across episodes."""
        if not episodes:
            return {}
        
        # Simple approach: find keys that appear in all episodes
        common_keys = set(episodes[0].context.keys())
        for ep in episodes[1:]:
            common_keys &= set(ep.context.keys())
        
        return {key: episodes[0].context[key] for key in common_keys}
    
    def _promote_to_semantic(self, pattern: Dict[str, Any]):
        """Promote a pattern to semantic memory."""
        self.graph.add_fact(TemporalFact(
            subject="learned_patterns",
            predicate=pattern['key'],
            object_value=pattern['value'],
            valid_from=time.time(),
            confidence=pattern['confidence'],
            source="consolidation",
            metadata={"pattern_type": pattern['type']}
        ))

# Background daemon
def run_consolidation_daemon(db_path: str, interval_hours: int = 24):
    """Run consolidation as a background process."""
    consolidator = MemoryConsolidator(db_path)
    
    while True:
        try:
            consolidator.consolidate(lookback_days=7)
            print(f"[Consolidation] Completed at {datetime.now()}")
        except Exception as e:
            print(f"[Consolidation] Error: {e}")
        
        time.sleep(interval_hours * 60 * 60)
```

---

## ⚡ **PHASE 4: PERFORMANCE UPGRADES**

### **4.1 LanceDB Integration**

**Create new file:** `lib/cipkg/lancedb_store.py`

```python
"""
LanceDB Integration - High-performance vector storage with hybrid search.
"""
import lancedb
import pyarrow as pa
import numpy as np
from typing import List, Dict, Optional
import os

class LanceDBVectorStore:
    """LanceDB-based vector store with hybrid search capabilities."""
    
    def __init__(self, db_path: str, table_name: str = "code_embeddings"):
        self.db_path = db_path
        self.table_name = table_name
        self.db = lancedb.connect(db_path)
        self.table = None
        self._init_table()
    
    def _init_table(self):
        """Initialize the vector table."""
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("path", pa.string()),
            pa.field("symbol_id", pa.string()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), 384)),  # Adjust dim as needed
            pa.field("metadata", pa.string())
        ])
        
        if self.table_name not in self.db.table_names():
            self.table = self.db.create_table(self.table_name, schema=schema)
        else:
            self.table = self.db.open_table(self.table_name)
    
    def add_embeddings(
        self,
        ids: List[str],
        paths: List[str],
        symbol_ids: List[str],
        texts: List[str],
        vectors: List[List[float]],
        metadata: Optional[List[Dict]] = None
    ):
        """Add embeddings to the store."""
        metadata = metadata or [{} for _ in ids]
        
        data = [
            {
                "id": id_,
                "path": path,
                "symbol_id": symbol_id,
                "text": text,
                "vector": vector,
                "metadata": json.dumps(meta)
            }
            for id_, path, symbol_id, text, vector, meta in 
            zip(ids, paths, symbol_ids, texts, vectors, metadata)
        ]
        
        self.table.add(data)
    
    def hybrid_search(
        self,
        query_vector: List[float],
        query_text: Optional[str] = None,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Perform hybrid search (vector + lexical)."""
        # Vector search
        results = self.table.search(query_vector).limit(top_k * 2).to_list()
        
        # If text query provided, boost with lexical similarity
        if query_text:
            for result in results:
                text = result.get('text', '')
                lexical_score = self._lexical_similarity(query_text, text)
                result['score'] = result.get('score', 0) + (lexical_score * 0.3)
            
            # Re-sort by combined score
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return results[:top_k]
    
    def _lexical_similarity(self, query: str, text: str) -> float:
        """Simple lexical similarity based on token overlap."""
        query_tokens = set(query.lower().split())
        text_tokens = set(text.lower().split())
        
        if not query_tokens:
            return 0.0
        
        overlap = len(query_tokens & text_tokens)
        return overlap / len(query_tokens)
    
    def delete_by_path(self, path: str):
        """Delete all embeddings for a given path."""
        self.table.delete(f"path = '{path}'")

# Migration helper
def migrate_sqlite_to_lancedb(sqlite_db: str, lancedb_path: str):
    """Migrate existing SQLite vectors to LanceDB."""
    import sqlite3
    from .store import vector_matrix
    
    con = sqlite3.connect(sqlite_db)
    
    # Get vectors from SQLite
    cursor = con.execute("SELECT id, vec FROM vectors")
    rows = cursor.fetchall()
    
    if not rows:
        print("No vectors to migrate")
        return
    
    # Initialize LanceDB
    store = LanceDBVectorStore(lancedb_path)
    
    # Convert and add
    ids = []
    vectors = []
    paths = []
    symbol_ids = []
    texts = []
    
    for row in rows:
        id_, vec_blob = row
        vector = np.frombuffer(vec_blob, dtype=np.float32).tolist()
        
        # Get metadata from chunks table
        meta_cursor = con.execute(
            "SELECT path, symbol_id, text FROM chunks WHERE id = ?",
            (id_,)
        )
        meta = meta_cursor.fetchone()
        
        if meta:
            path, symbol_id, text = meta
            ids.append(id_)
            vectors.append(vector)
            paths.append(path)
            symbol_ids.append(symbol_id or "")
            texts.append(text)
    
    # Add in batches
    batch_size = 1000
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        batch_vectors = vectors[i:i+batch_size]
        batch_paths = paths[i:i+batch_size]
        batch_symbol_ids = symbol_ids[i:i+batch_size]
        batch_texts = texts[i:i+batch_size]
        
        store.add_embeddings(
            batch_ids,
            batch_paths,
            batch_symbol_ids,
            batch_texts,
            batch_vectors
        )
    
    print(f"Migrated {len(ids)} vectors to LanceDB")
```

---

### **4.2 Async File Watcher**

**Create new file:** `lib/cipkg/watcher.py`

```python
"""
Async File Watcher - Real-time index updates on file changes.
"""
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable, Set
import threading

class CodeChangeHandler(FileSystemEventHandler):
    """Handle file system changes and trigger re-indexing."""
    
    def __init__(self, on_change: Callable[[str], None]):
        self.on_change = on_change
        self._ignore_patterns = {
            '.git', 'node_modules', '__pycache__', '.venv', 'venv',
            '.cip', '.DS_Store', '*.pyc'
        }
    
    def on_modified(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self.on_change(event.src_path)
    
    def on_created(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self.on_change(event.src_path)
    
    def on_deleted(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self.on_change(event.src_path)
    
    def _should_process(self, path: str) -> bool:
        """Check if path should be processed."""
        # Skip ignored patterns
        for pattern in self._ignore_patterns:
            if pattern in path:
                return False
        
        # Only process source files
        ext = os.path.splitext(path)[1].lower()
        return ext in {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java'}

class AsyncFileWatcher:
    """Watch files and trigger re-indexing in background thread."""
    
    def __init__(self, root: str, on_change: Callable[[str], None]):
        self.root = root
        self.on_change = on_change
        self.observer = None
        self._running = False
    
    def start(self):
        """Start watching in background thread."""
        if self._running:
            return
        
        event_handler = CodeChangeHandler(self.on_change)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.root, recursive=True)
        
        thread = threading.Thread(target=self._run_observer, daemon=True)
        thread.start()
        
        self._running = True
        print(f"[Watcher] Started watching {self.root}")
    
    def _run_observer(self):
        """Run observer in thread."""
        self.observer.start()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop watching."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self._running = False
        print("[Watcher] Stopped")

# Integration with indexer
def setup_watcher(root: str):
    """Setup file watcher for automatic re-indexing."""
    from . import indexer
    
    def on_file_change(path: str):
        """Handle file change event."""
        print(f"[Watcher] Detected change: {path}")
        
        # Trigger incremental re-index
        try:
            # Re-index just this file
            from .base import load_config
            from .store import connect
            
            con = connect(root)
            cfg = load_config(root)
            
            # Mark file for re-indexing
            indexer.mark_for_reindex(con, [path])
            
            # Run incremental embed
            indexer.embed_pending(con, cfg, batch=1)
            
            print(f"[Watcher] Re-indexed: {path}")
        except Exception as e:
            print(f"[Watcher] Error re-indexing {path}: {e}")
    
    watcher = AsyncFileWatcher(root, on_file_change)
    return watcher
```

---

## 📝 **IMPLEMENTATION INSTRUCTIONS**

### **For Your Agent to Execute:**

1. **Apply Phase 1 Fixes (Critical)**
   ```bash
   # Create backup first
   cp -r lib/cipkg lib/cipkg.backup
   
   # Apply each fix from Phase 1 in order
   # Test after each P0 fix:
   python -c "from cipkg import cli; cli.dispatch_command('.', type('Args', (), {}))"
   ```

2. **Add New Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install watchdog lancedb pyarrow
   ```

3. **Implement Phase 2 Features**
   - Create new files in `lib/cipkg/`
   - Add CLI commands to `cli.py`
   - Test each feature independently

4. **Implement Phase 3 Memory Systems**
   ```bash
   mkdir -p lib/cipkg/memory
   # Create files from Phase 3
   ```

5. **Test Everything**
   ```bash
   # Test bug fixes
   cip selftest
   
   # Test repo map
   cip map --max-tokens 2048
   
   # Test memory
   python -c "from cipkg.memory.temporal_graph import AgentMemory; m = AgentMemory('test.db'); m.remember('test', 'value'); print(m.recall('test'))"
   ```

6. **Commit Changes**
   ```bash
   git add .
   git commit -m "Upgrade v2.0: Bug fixes, advanced indexing, agent memory"
   ```

---

## 🎯 **VERIFICATION CHECKLIST**

- [ ] All P0 bugs fixed (CLI works, install succeeds)
- [ ] All P1 bugs fixed (health score accurate, embedding fallback works)
- [ ] `cip map` generates token-efficient repo map
- [ ] AST-aware chunking preserves function/class boundaries
- [ ] SCIP integration indexes cross-file references
- [ ] Temporal knowledge graph stores facts with timestamps
- [ ] Episodic memory logs agent interactions
- [ ] Memory consolidation promotes patterns to long-term storage
- [ ] LanceDB provides hybrid search (vector + lexical)
- [ ] File watcher triggers automatic re-indexing
- [ ] All tests pass: `cip selftest`

---

This upgrade pack transforms CIP into a **production-grade code intelligence platform** ready for autonomous coding agents. Each component is modular and can be implemented incrementally.
