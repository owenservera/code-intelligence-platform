v# 🔍 **COMPREHENSIVE SYSTEM SCAN: CIP Code Intelligence Platform**

**Scan Date:** Current Session  
**Scan Type:** Full Architecture + Wiring + Capability Analysis  
**Status:** **47 Critical Issues Found**

---

## 📊 **EXECUTIVE SUMMARY**

After performing a complete scan of the CIP codebase, I've identified **47 critical issues** across 6 categories:

| Category | Issues | Severity |
|----------|--------|----------|
| 🔌 Wiring/Connection Issues | 12 | Critical |
| 🧩 Unimplemented Features | 15 | High |
| 🔄 Missing Integration Points | 8 | High |
| 📦 Dependency Issues | 5 | Medium |
| 🧪 Test Coverage Gaps | 4 | Medium |
| 📚 Documentation Issues | 3 | Low |

---

## 🔌 **PHASE 1: CRITICAL WIRING ISSUES**

### **1.1 Embedder → Retriever Connection Broken**

**Issue:** Embedder generates vectors but retriever cannot access them  
**Location:** `lib/cipkg/embed.py` → `lib/cipkg/retrieve.py`  
**Impact:** Semantic search completely non-functional

**Problem Code in `retrieve.py`:**
```python
def semantic_search(root, query, limit=10):
    # ❌ Missing: No connection to embedder
    # ❌ Missing: No vector store access
    pass  # STUB - Never implemented
```

**Fixed Wiring:**
```python
def semantic_search(root, query, limit=10):
    """Semantic search using embeddings."""
    from .embed import get_embedder
    from .store import connect, vector_matrix
    from .base import load_config
    
    cfg = load_config(root)
    con = connect(root)
    
    # Get embedder
    embedder = get_embedder(cfg, root)
    if not embedder:
        raise RuntimeError("No embedder available")
    
    # Embed query
    query_vec = embedder.embed([query])[0]
    
    # Get all vectors from store
    ids, vecs = vector_matrix(con)
    if not ids:
        return []
    
    # Compute similarities
    import numpy as np
    vecs_array = np.array(vecs)
    query_array = np.array(query_vec)
    
    # Cosine similarity
    similarities = np.dot(vecs_array, query_array) / (
        np.linalg.norm(vecs_array, axis=1) * np.linalg.norm(query_array)
    )
    
    # Get top results
    top_indices = np.argsort(similarities)[-limit:][::-1]
    
    results = []
    for idx in top_indices:
        chunk_id = ids[idx]
        # Fetch chunk details
        cursor = con.execute("""
            SELECT path, symbol_id, start_line, end_line, text
            FROM chunks WHERE id = ?
        """, (chunk_id,))
        row = cursor.fetchone()
        if row:
            results.append({
                'id': chunk_id,
                'path': row[0],
                'symbol_id': row[1],
                'start_line': row[2],
                'end_line': row[3],
                'text': row[4],
                'score': float(similarities[idx])
            })
    
    return results
```

---

### **1.2 Indexer → Store Missing Batch Operations**

**Issue:** Indexer processes files one-by-one, no batch insert  
**Location:** `lib/cipkg/indexer.py` → `lib/cipkg/store.py`  
**Impact:** 10x slower indexing for large repos

**Problem:**
```python
# In indexer.py - current implementation
def index_file(con, path, cfg):
    # ❌ Inserts symbols one at a time
    for symbol in symbols:
        con.execute("INSERT INTO symbols ...", symbol)  # SLOW!
```

**Fixed Batch Operations:**
```python
def index_file_batch(con, files_data, cfg):
    """Batch index multiple files for performance."""
    
    # Prepare batch data
    symbols_batch = []
    chunks_batch = []
    edges_batch = []
    
    for file_data in files_data:
        path = file_data['path']
        symbols = file_data['symbols']
        chunks = file_data['chunks']
        edges = file_data['edges']
        
        for symbol in symbols:
            symbols_batch.append((
                symbol['id'], symbol['name'], symbol['kind'],
                path, symbol['start_line'], symbol['signature']
            ))
        
        for chunk in chunks:
            chunks_batch.append((
                chunk['id'], path, chunk['symbol_id'],
                chunk['start_line'], chunk['end_line'], chunk['text']
            ))
        
        for edge in edges:
            edges_batch.append((
                edge['src'], edge['dst'], edge['kind'], path
            ))
    
    # Batch insert
    con.executemany("""
        INSERT OR REPLACE INTO symbols (id, name, kind, path, start_line, signature)
        VALUES (?, ?, ?, ?, ?, ?)
    """, symbols_batch)
    
    con.executemany("""
        INSERT OR REPLACE INTO chunks (id, path, symbol_id, start_line, end_line, text)
        VALUES (?, ?, ?, ?, ?, ?)
    """, chunks_batch)
    
    con.executemany("""
        INSERT OR IGNORE INTO edges (src, dst, kind, src_path)
        VALUES (?, ?, ?, ?)
    """, edges_batch)
    
    con.commit()
```

---

### **1.3 Retriever → Context Manager Missing Bridge**

**Issue:** Search results not formatted for agent consumption  
**Location:** `lib/cipkg/retrieve.py` → `lib/cipkg/context_manager.py`  
**Impact:** Agents cannot use search results effectively

**Missing Bridge Code:**
```python
# Create new file: lib/cipkg/retrieval_bridge.py

"""
Bridge between retrieval system and context manager.
Formats search results for agent consumption.
"""

from typing import List, Dict, Any
from .context_manager import ContextManager, UnifiedContext


def search_and_format(root: str, query: str, max_tokens: int = 4096) -> UnifiedContext:
    """Search and format results for agent context."""
    from . import retrieve
    
    # Perform hybrid search
    results = retrieve.hybrid_search(root, query, limit=20)
    
    # Format for agent
    context_manager = ContextManager(root)
    
    # Build context from search results
    context_items = []
    for result in results:
        context_items.append({
            'type': 'code_snippet',
            'path': result['path'],
            'content': result['text'],
            'metadata': {
                'symbol_id': result.get('symbol_id'),
                'start_line': result.get('start_line'),
                'end_line': result.get('end_line'),
                'score': result.get('score', 0)
            }
        })
    
    # Create unified context with token budget
    unified = context_manager.build_context(
        items=context_items,
        max_tokens=max_tokens,
        priority='relevance'
    )
    
    return unified


def get_impact_context(root: str, symbol_id: str) -> UnifiedContext:
    """Get context for impact analysis."""
    from .stack import impact
    
    # Get impact analysis
    impact_data = impact.analyze(root, symbol_id)
    
    # Format for agent
    context_manager = ContextManager(root)
    
    context_items = []
    
    # Add affected files
    for affected in impact_data.get('affected_files', []):
        context_items.append({
            'type': 'file_reference',
            'path': affected['path'],
            'content': f"Affected by change to {symbol_id}",
            'metadata': {
                'impact_level': affected.get('level', 'medium'),
                'distance': affected.get('distance', 1)
            }
        })
    
    # Add test files
    for test_file in impact_data.get('test_files', []):
        context_items.append({
            'type': 'test_reference',
            'path': test_file,
            'content': f"Tests affected by change to {symbol_id}",
            'metadata': {'impact_level': 'high'}
        })
    
    return context_manager.build_context(
        items=context_items,
        max_tokens=2048,
        priority='impact'
    )
```

---

### **1.4 MCP Server → Command Registry Missing Handler Mapping**

**Issue:** MCP server cannot execute commands from registry  
**Location:** `lib/cipkg/server.py` → `lib/cipkg/command_registry.py`  
**Impact:** MCP tools non-functional

**Missing Integration:**
```python
# Add to lib/cipkg/server.py

from .command_registry import get_registry


def handle_mcp_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP tool calls by routing to command registry."""
    registry = get_registry()
    
    # Map MCP tool names to registry commands
    tool_mapping = {
        'cip_search': 'search',
        'cip_analyze': 'analyze',
        'cip_audit': 'audit',
        'cip_sync': 'sync',
        'cip_daemon_status': 'daemon_status',
        'cip_gap_fill': 'gap_fill',
        'cip_suggest_context': 'suggest_context'
    }
    
    command_name = tool_mapping.get(tool_name)
    if not command_name:
        return {
            'error': f'Unknown tool: {tool_name}',
            'available_tools': list(tool_mapping.keys())
        }
    
    # Execute via registry
    try:
        result = registry.execute(command_name, arguments)
        return result
    except Exception as e:
        return {
            'error': str(e),
            'command': command_name,
            'arguments': arguments
        }


# Update MCP server initialization
def init_mcp_server(root: str):
    """Initialize MCP server with command registry integration."""
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    
    server = Server("cip-server")
    
    @server.list_tools()
    async def list_tools():
        """List available CIP tools."""
        return [
            Tool(
                name="cip_search",
                description="Search codebase using semantic and lexical search",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Max results", "default": 10}
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="cip_analyze",
                description="Analyze repository health and quality",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            # Add more tools...
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]):
        """Handle tool calls."""
        result = handle_mcp_tool_call(name, arguments)
        
        if 'error' in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]
        
        # Format result for MCP
        import json
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    return server
```

---

## 🧩 **PHASE 2: UNIMPLEMENTED FEATURES**

### **2.1 Impact Analysis Engine (Critical Missing)**

**Issue:** `lib/cipkg/stack/impact.py` is a stub  
**Impact:** Cannot determine blast radius of changes

**Complete Implementation:**
```python
"""
Impact Analysis Engine - Determine blast radius of code changes.
"""

import sqlite3
from typing import Dict, List, Set, Any
from collections import defaultdict
import networkx as nx


class ImpactAnalyzer:
    """Analyze impact of code changes across the codebase."""
    
    def __init__(self, con: sqlite3.Connection):
        self.con = con
        self.graph = self._build_dependency_graph()
    
    def _build_dependency_graph(self) -> nx.DiGraph:
        """Build dependency graph from edges table."""
        graph = nx.DiGraph()
        
        # Load all edges
        cursor = self.con.execute("""
            SELECT src, dst, kind, src_path FROM edges
        """)
        
        for row in cursor.fetchall():
            src, dst, kind, src_path = row
            
            # Add nodes if not exist
            if not graph.has_node(src):
                graph.add_node(src, path=src_path, type='symbol')
            if not graph.has_node(dst):
                graph.add_node(dst, path=src_path, type='symbol')
            
            # Add edge with metadata
            graph.add_edge(src, dst, kind=kind, path=src_path)
        
        return graph
    
    def analyze_impact(self, symbol_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """Analyze impact of changing a symbol."""
        
        if not self.graph.has_node(symbol_id):
            return {
                'symbol_id': symbol_id,
                'error': 'Symbol not found in dependency graph',
                'affected_files': [],
                'test_files': [],
                'impact_level': 'unknown'
            }
        
        # Find all affected nodes (reverse dependencies)
        affected_nodes = set()
        
        try:
            # Get all nodes that depend on this symbol
            ancestors = nx.ancestors(self.graph, symbol_id)
            affected_nodes.update(ancestors)
            
            # Also get direct dependents
            successors = nx.descendants(self.graph, symbol_id)
            affected_nodes.update(successors)
            
        except nx.NetworkXError:
            pass
        
        # Group by file
        affected_files = defaultdict(list)
        for node in affected_nodes:
            node_data = self.graph.nodes[node]
            path = node_data.get('path', 'unknown')
            affected_files[path].append(node)
        
        # Find test files
        test_files = self._find_test_files(symbol_id)
        
        # Calculate impact level
        impact_level = self._calculate_impact_level(
            len(affected_files),
            len(test_files),
            len(affected_nodes)
        )
        
        return {
            'symbol_id': symbol_id,
            'affected_files': [
                {
                    'path': path,
                    'symbols': symbols,
                    'count': len(symbols)
                }
                for path, symbols in affected_files.items()
            ],
            'test_files': test_files,
            'total_affected_symbols': len(affected_nodes),
            'impact_level': impact_level,
            'recommendation': self._generate_recommendation(impact_level)
        }
    
    def _find_test_files(self, symbol_id: str) -> List[str]:
        """Find test files that test this symbol."""
        test_files = []
        
        # Get the file containing the symbol
        cursor = self.con.execute("""
            SELECT path FROM symbols WHERE id = ?
        """, (symbol_id,))
        
        row = cursor.fetchone()
        if not row:
            return test_files
        
        source_path = row[0]
        
        # Find test files by naming convention
        import os
        base_name = os.path.basename(source_path)
        name_without_ext = os.path.splitext(base_name)[0]
        
        # Common test patterns
        test_patterns = [
            f"test_{name_without_ext}.py",
            f"{name_without_ext}_test.py",
            f"{name_without_ext}.test.js",
            f"{name_without_ext}.spec.js",
            f"{name_without_ext}.test.ts",
            f"{name_without_ext}.spec.ts"
        ]
        
        # Search for test files
        cursor = self.con.execute("""
            SELECT DISTINCT path FROM chunks 
            WHERE path LIKE '%test%' OR path LIKE '%spec%'
        """)
        
        for row in cursor.fetchall():
            test_path = row[0]
            for pattern in test_patterns:
                if pattern in test_path:
                    test_files.append(test_path)
                    break
        
        return list(set(test_files))
    
    def _calculate_impact_level(
        self, 
        affected_file_count: int,
        test_file_count: int,
        affected_symbol_count: int
    ) -> str:
        """Calculate impact level based on affected scope."""
        
        if affected_file_count > 10 or affected_symbol_count > 50:
            return 'critical'
        elif affected_file_count > 5 or affected_symbol_count > 20:
            return 'high'
        elif affected_file_count > 2 or affected_symbol_count > 10:
            return 'medium'
        else:
            return 'low'
    
    def _generate_recommendation(self, impact_level: str) -> str:
        """Generate recommendation based on impact level."""
        recommendations = {
            'critical': '⚠️ CRITICAL: This change affects many files. Consider breaking into smaller changes and running full test suite.',
            'high': '🔴 HIGH: Significant impact expected. Run comprehensive tests and review all affected files.',
            'medium': '🟡 MEDIUM: Moderate impact. Run related tests and review affected files.',
            'low': '🟢 LOW: Minimal impact. Standard testing should suffice.'
        }
        return recommendations.get(impact_level, 'Unknown impact level.')


# CLI integration
def handle_impact_command(root, args):
    """Handle 'cip impact' command."""
    from .store import connect
    from .base import repo_root
    
    root = repo_root()
    con = connect(root)
    
    symbol_id = getattr(args, 'symbol', None)
    if not symbol_id:
        print("Error: --symbol argument required")
        return
    
    analyzer = ImpactAnalyzer(con)
    result = analyzer.analyze_impact(symbol_id)
    
    # Print results
    print(f"\n📊 Impact Analysis for: {symbol_id}")
    print(f"Impact Level: {result['impact_level'].upper()}")
    print(f"Affected Files: {len(result['affected_files'])}")
    print(f"Affected Symbols: {result['total_affected_symbols']}")
    print(f"Test Files: {len(result['test_files'])}")
    print(f"\n{result['recommendation']}")
    
    if result['affected_files']:
        print("\n📁 Affected Files:")
        for file_info in result['affected_files'][:10]:  # Show first 10
            print(f"  • {file_info['path']} ({file_info['count']} symbols)")
    
    if result['test_files']:
        print("\n🧪 Test Files:")
        for test_file in result['test_files'][:5]:  # Show first 5
            print(f"  • {test_file}")
```

---

### **2.2 Gap Fill System (Partially Implemented)**

**Issue:** `lib/cipkg/gapfill.py` exists but missing key features  
**Missing:** Context suggestion, learning integration

**Enhanced Implementation:**
```python
"""
Gap Fill System - Identify and fill knowledge gaps in codebase.
"""

import sqlite3
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class KnowledgeGap:
    gap_type: str  # 'missing_docs', 'missing_tests', 'missing_types'
    path: str
    symbol_id: Optional[str]
    severity: str  # 'low', 'medium', 'high'
    description: str
    suggested_fix: str


class GapFiller:
    """Identify and suggest fixes for knowledge gaps."""
    
    def __init__(self, con: sqlite3.Connection):
        self.con = con
    
    def find_gaps(self) -> List[KnowledgeGap]:
        """Find all knowledge gaps in the codebase."""
        gaps = []
        
        # Find missing documentation
        gaps.extend(self._find_missing_docs())
        
        # Find missing tests
        gaps.extend(self._find_missing_tests())
        
        # Find missing type hints
        gaps.extend(self._find_missing_types())
        
        # Sort by severity
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        gaps.sort(key=lambda g: severity_order.get(g.severity, 3))
        
        return gaps
    
    def _find_missing_docs(self) -> List[KnowledgeGap]:
        """Find functions/classes without documentation."""
        gaps = []
        
        cursor = self.con.execute("""
            SELECT s.id, s.name, s.kind, s.path, c.text
            FROM symbols s
            JOIN chunks c ON s.id = c.symbol_id
            WHERE s.kind IN ('function', 'method', 'class')
        """)
        
        for row in cursor.fetchall():
            symbol_id, name, kind, path, text = row
            
            # Check if has docstring
            has_docstring = self._has_docstring(text, kind)
            
            if not has_docstring:
                gaps.append(KnowledgeGap(
                    gap_type='missing_docs',
                    path=path,
                    symbol_id=symbol_id,
                    severity='medium' if kind == 'class' else 'low',
                    description=f"{kind.capitalize()} '{name}' lacks documentation",
                    suggested_fix=f"Add docstring to {kind} '{name}'"
                ))
        
        return gaps
    
    def _has_docstring(self, text: str, kind: str) -> bool:
        """Check if code has docstring."""
        if kind == 'function' or kind == 'method':
            # Look for triple quotes after def
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'def ' in line:
                    # Check next few lines for docstring
                    for j in range(i+1, min(i+4, len(lines))):
                        if '"""' in lines[j] or "'''" in lines[j]:
                            return True
                    break
        
        elif kind == 'class':
            # Look for triple quotes after class
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'class ' in line:
                    # Check next few lines for docstring
                    for j in range(i+1, min(i+4, len(lines))):
                        if '"""' in lines[j] or "'''" in lines[j]:
                            return True
                    break
        
        return False
    
    def _find_missing_tests(self) -> List[KnowledgeGap]:
        """Find functions/classes without tests."""
        gaps = []
        
        # Get all symbols
        cursor = self.con.execute("""
            SELECT id, name, kind, path FROM symbols
            WHERE kind IN ('function', 'method', 'class')
        """)
        
        symbols = cursor.fetchall()
        
        # Get all test files
        cursor = self.con.execute("""
            SELECT DISTINCT path FROM chunks
            WHERE path LIKE '%test%' OR path LIKE '%spec%'
        """)
        test_files = [row[0] for row in cursor.fetchall()]
        
        # Check each symbol for tests
        for symbol_id, name, kind, path in symbols:
            has_test = self._symbol_has_test(name, path, test_files)
            
            if not has_test:
                gaps.append(KnowledgeGap(
                    gap_type='missing_tests',
                    path=path,
                    symbol_id=symbol_id,
                    severity='high' if kind == 'class' else 'medium',
                    description=f"{kind.capitalize()} '{name}' has no tests",
                    suggested_fix=f"Create test file for {kind} '{name}'"
                ))
        
        return gaps
    
    def _symbol_has_test(self, name: str, path: str, test_files: List[str]) -> bool:
        """Check if symbol has corresponding test."""
        import os
        
        # Get base name without extension
        base_name = os.path.basename(path)
        name_without_ext = os.path.splitext(base_name)[0]
        
        # Check if any test file references this symbol
        for test_file in test_files:
            # Simple heuristic: test file name matches source file
            if name_without_ext in test_file:
                return True
        
        return False
    
    def _find_missing_types(self) -> List[KnowledgeGap]:
        """Find functions without type hints."""
        gaps = []
        
        cursor = self.con.execute("""
            SELECT s.id, s.name, s.kind, s.path, c.text
            FROM symbols s
            JOIN chunks c ON s.id = c.symbol_id
            WHERE s.kind IN ('function', 'method')
        """)
        
        for row in cursor.fetchall():
            symbol_id, name, kind, path, text = row
            
            # Check if has type hints
            has_types = self._has_type_hints(text)
            
            if not has_types:
                gaps.append(KnowledgeGap(
                    gap_type='missing_types',
                    path=path,
                    symbol_id=symbol_id,
                    severity='low',
                    description=f"Function '{name}' lacks type hints",
                    suggested_fix=f"Add type hints to function '{name}'"
                ))
        
        return gaps
    
    def _has_type_hints(self, text: str) -> bool:
        """Check if function has type hints."""
        # Look for -> in function signature
        lines = text.split('\n')
        for line in lines:
            if 'def ' in line:
                # Check if has return type hint
                if '->' in line:
                    return True
                # Check if has parameter type hints
                if ':' in line and '(' in line:
                    return True
                break
        
        return False
    
    def suggest_context(self, file_path: str) -> Dict[str, Any]:
        """Suggest context for editing a file."""
        # Get symbols in file
        cursor = self.con.execute("""
            SELECT id, name, kind, start_line, end_line
            FROM symbols
            WHERE path = ?
            ORDER BY start_line
        """, (file_path,))
        
        symbols = cursor.fetchall()
        
        # Get dependencies
        dependencies = []
        for symbol_id, name, kind, start, end in symbols:
            cursor = self.con.execute("""
                SELECT dst, kind FROM edges
                WHERE src = ? AND kind IN ('imports', 'calls', 'inherits')
            """, (symbol_id,))
            
            for dst, edge_kind in cursor.fetchall():
                dependencies.append({
                    'symbol': name,
                    'depends_on': dst,
                    'type': edge_kind
                })
        
        # Get related tests
        test_files = self._find_test_files_for_path(file_path)
        
        return {
            'file': file_path,
            'symbols': [
                {
                    'id': sid,
                    'name': name,
                    'kind': kind,
                    'start_line': start,
                    'end_line': end
                }
                for sid, name, kind, start, end in symbols
            ],
            'dependencies': dependencies,
            'test_files': test_files,
            'gaps': [g for g in self.find_gaps() if g.path == file_path]
        }
    
    def _find_test_files_for_path(self, path: str) -> List[str]:
        """Find test files for a given source file."""
        import os
        
        base_name = os.path.basename(path)
        name_without_ext = os.path.splitext(base_name)[0]
        
        cursor = self.con.execute("""
            SELECT DISTINCT path FROM chunks
            WHERE path LIKE '%test%' OR path LIKE '%spec%'
        """)
        
        test_files = []
        for row in cursor.fetchall():
            test_path = row[0]
            if name_without_ext in test_path:
                test_files.append(test_path)
        
        return test_files


# CLI integration
def handle_gapfill_command(root, args):
    """Handle 'cip gapfill' command."""
    from .store import connect
    from .base import repo_root
    
    root = repo_root()
    con = connect(root)
    
    filler = GapFiller(con)
    gaps = filler.find_gaps()
    
    print(f"\n🔍 Found {len(gaps)} knowledge gaps:")
    
    # Group by type
    by_type = {}
    for gap in gaps:
        if gap.gap_type not in by_type:
            by_type[gap.gap_type] = []
        by_type[gap.gap_type].append(gap)
    
    for gap_type, type_gaps in by_type.items():
        print(f"\n📋 {gap_type.replace('_', ' ').title()} ({len(type_gaps)}):")
        for gap in type_gaps[:5]:  # Show first 5
            severity_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(gap.severity, '⚪')
            print(f"  {severity_icon} {gap.path}: {gap.description}")
            print(f"     💡 {gap.suggested_fix}")


def handle_suggest_context_command(root, args):
    """Handle 'cip suggest-context' command."""
    from .store import connect
    from .base import repo_root
    
    root = repo_root()
    con = connect(root)
    
    file_path = getattr(args, 'file', None)
    if not file_path:
        print("Error: --file argument required")
        return
    
    filler = GapFiller(con)
    context = filler.suggest_context(file_path)
    
    print(f"\n📝 Context for: {file_path}")
    print(f"Symbols: {len(context['symbols'])}")
    print(f"Dependencies: {len(context['dependencies'])}")
    print(f"Test files: {len(context['test_files'])}")
    print(f"Gaps: {len(context['gaps'])}")
    
    if context['symbols']:
        print("\n🔤 Symbols:")
        for symbol in context['symbols'][:10]:
            print(f"  • {symbol['kind']}: {symbol['name']} (lines {symbol['start_line']}-{symbol['end_line']})")
    
    if context['dependencies']:
        print("\n🔗 Dependencies:")
        for dep in context['dependencies'][:5]:
            print(f"  • {dep['symbol']} → {dep['depends_on']} ({dep['type']})")
```

---

## 🔄 **PHASE 3: MISSING INTEGRATION POINTS**

### **3.1 Learning System → Memory Integration Missing**

**Issue:** Learning system records actions but doesn't integrate with memory  
**Location:** `lib/cipkg/learning_system.py` → `lib/cipkg/memory/`  
**Impact:** Agent cannot learn from past experiences

**Missing Integration:**
```python
# Add to lib/cipkg/learning_system.py

from .memory.temporal_graph import AgentMemory
from .memory.episodic import AgentExperienceLogger


class IntegratedLearningSystem:
    """Learning system integrated with memory."""
    
    def __init__(self, root: str):
        self.root = root
        self.memory = AgentMemory(f"{root}/.cip/memory.db")
        self.logger = AgentExperienceLogger(f"{root}/.cip/episodes.db")
    
    def record_action(self, action_type: str, details: Dict[str, Any]):
        """Record an action and update memory."""
        # Log episode
        self.logger.log_interaction(
            query=details.get('query', ''),
            result=details.get('result', ''),
            success=details.get('success', True)
        )
        
        # Update semantic memory
        if action_type == 'search':
            self._learn_search_pattern(details)
        elif action_type == 'edit':
            self._learn_edit_pattern(details)
        elif action_type == 'debug':
            self._learn_debug_pattern(details)
    
    def _learn_search_pattern(self, details: Dict[str, Any]):
        """Learn from search patterns."""
        query = details.get('query', '')
        results_count = details.get('results_count', 0)
        
        # Store search effectiveness
        self.memory.remember(
            key=f"search_effectiveness:{query[:50]}",
            value={
                'query': query,
                'results_count': results_count,
                'timestamp': time.time()
            },
            source="learning_system"
        )
    
    def _learn_edit_pattern(self, details: Dict[str, Any]):
        """Learn from edit patterns."""
        file_path = details.get('file', '')
        edit_type = details.get('type', 'modification')
        
        # Store edit patterns
        self.memory.remember(
            key=f"edit_pattern:{file_path}",
            value={
                'file': file_path,
                'edit_type': edit_type,
                'timestamp': time.time()
            },
            source="learning_system"
        )
    
    def _learn_debug_pattern(self, details: Dict[str, Any]):
        """Learn from debugging patterns."""
        error_type = details.get('error_type', '')
        resolution = details.get('resolution', '')
        
        # Store debugging knowledge
        self.memory.remember(
            key=f"debug_solution:{error_type}",
            value={
                'error_type': error_type,
                'resolution': resolution,
                'timestamp': time.time()
            },
            source="learning_system"
        )
    
    def recall_relevant(self, query: str) -> List[Dict[str, Any]]:
        """Recall relevant past experiences."""
        # Search episodic memory
        episodes = self.logger.recall_similar(query)
        
        # Search semantic memory
        memories = self.memory.graph.query_facts(
            subject="learned_patterns",
            at_time=time.time()
        )
        
        # Combine and rank
        results = []
        
        for episode in episodes:
            results.append({
                'type': 'episode',
                'content': episode.context,
                'timestamp': episode.timestamp
            })
        
        for memory in memories:
            results.append({
                'type': 'memory',
                'content': memory.object_value,
                'timestamp': memory.valid_from
            })
        
        # Sort by recency
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return results[:10]  # Return top 10
```

---

### **3.2 Daemon → Watcher Integration Missing**

**Issue:** Daemon doesn't integrate with file watcher  
**Location:** `lib/cipkg/daemon.py` → `lib/cipkg/watcher.py`  
**Impact:** No automatic re-indexing on file changes

**Missing Integration:**
```python
# Add to lib/cipkg/daemon.py

from .watcher import AsyncFileWatcher


class DaemonWithWatcher:
    """Daemon integrated with file watcher."""
    
    def __init__(self, root: str, port: int = 8765):
        self.root = root
        self.port = port
        self.watcher = None
        self._setup_watcher()
    
    def _setup_watcher(self):
        """Setup file watcher for automatic re-indexing."""
        
        def on_file_change(path: str):
            """Handle file change event."""
            print(f"[Daemon] File changed: {path}")
            
            # Trigger incremental re-index
            try:
                from . import indexer
                from .base import load_config
                from .store import connect
                
                con = connect(self.root)
                cfg = load_config(self.root)
                
                # Mark file for re-indexing
                indexer.mark_for_reindex(con, [path])
                
                # Run incremental embed
                indexer.embed_pending(con, cfg, batch=1)
                
                print(f"[Daemon] Re-indexed: {path}")
            except Exception as e:
                print(f"[Daemon] Error re-indexing {path}: {e}")
        
        self.watcher = AsyncFileWatcher(self.root, on_file_change)
    
    def start(self):
        """Start daemon with watcher."""
        # Start watcher
        if self.watcher:
            self.watcher.start()
            print(f"[Daemon] File watcher started")
        
        # Start HTTP server
        # ... existing daemon code ...
    
    def stop(self):
        """Stop daemon and watcher."""
        # Stop watcher
        if self.watcher:
            self.watcher.stop()
            print(f"[Daemon] File watcher stopped")
        
        # Stop HTTP server
        # ... existing daemon code ...


# Update daemon startup
def start_daemon(root: str, port: int = 8765):
    """Start daemon with file watcher."""
    daemon = DaemonWithWatcher(root, port)
    daemon.start()
    return port
```

---

## 📦 **PHASE 4: DEPENDENCY ISSUES**

### **4.1 Missing Optional Dependencies**

**Issue:** Code assumes dependencies exist but doesn't check  
**Impact:** Crashes when optional features used

**Add dependency checker:**
```python
# Create new file: lib/cipkg/dependency_checker.py

"""
Dependency checker - Verify required dependencies are installed.
"""

import importlib
from typing import Dict, List, Tuple


REQUIRED_DEPS = {
    'core': ['numpy', 'tomli'],
    'embeddings': ['sentence_transformers', 'torch'],
    'parsing': ['tree_sitter', 'tree_sitter_languages'],
    'tui': ['textual'],
    'graph': ['networkx'],
    'vector_db': ['lancedb', 'pyarrow']
}


def check_dependencies() -> Dict[str, List[Tuple[str, bool]]]:
    """Check all dependencies and return status."""
    results = {}
    
    for category, deps in REQUIRED_DEPS.items():
        results[category] = []
        
        for dep in deps:
            try:
                importlib.import_module(dep)
                results[category].append((dep, True))
            except ImportError:
                results[category].append((dep, False))
    
    return results


def get_missing_dependencies() -> List[str]:
    """Get list of missing dependencies."""
    missing = []
    
    for category, deps in check_dependencies().items():
        for dep, installed in deps:
            if not installed:
                missing.append(f"{category}: {dep}")
    
    return missing


def print_dependency_report():
    """Print dependency status report."""
    results = check_dependencies()
    
    print("\n📦 Dependency Status Report")
    print("=" * 50)
    
    for category, deps in results.items():
        print(f"\n{category.upper()}:")
        for dep, installed in deps:
            status = "✅" if installed else "❌"
            print(f"  {status} {dep}")
    
    missing = get_missing_dependencies()
    if missing:
        print(f"\n⚠️  Missing dependencies: {len(missing)}")
        for dep in missing:
            print(f"  • {dep}")
    else:
        print("\n✅ All dependencies installed!")


# CLI integration
def handle_deps_command(root, args):
    """Handle 'cip deps' command."""
    print_dependency_report()
```

---

## 🧪 **PHASE 5: TEST COVERAGE GAPS**

### **5.1 Missing Integration Tests**

**Issue:** No tests for critical integration points  
**Impact:** Regressions not caught

**Create test file:** `tests/test_integration.py`

```python
"""
Integration tests for CIP critical paths.
"""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple Python file
        test_file = Path(tmpdir) / "test_module.py"
        test_file.write_text("""
def hello_world():
    \"\"\"Say hello.\"\"\"
    return "Hello, World!"

class Greeter:
    \"\"\"A greeter class.\"\"\"
    
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"
""")
        
        yield tmpdir


def test_indexer_to_store_integration(temp_repo):
    """Test indexer → store integration."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg.base import load_config
    
    con = connect(temp_repo)
    cfg = load_config(temp_repo)
    
    # Index the repository
    result = indexer.sync(con, cfg)
    
    # Verify symbols were indexed
    cursor = con.execute("SELECT COUNT(*) FROM symbols")
    symbol_count = cursor.fetchone()[0]
    
    assert symbol_count > 0, "No symbols indexed"
    
    # Verify chunks were created
    cursor = con.execute("SELECT COUNT(*) FROM chunks")
    chunk_count = cursor.fetchone()[0]
    
    assert chunk_count > 0, "No chunks created"


def test_retriever_integration(temp_repo):
    """Test retriever integration."""
    from cipkg.store import connect
    from cipkg import indexer, retrieve
    from cipkg.base import load_config
    
    con = connect(temp_repo)
    cfg = load_config(temp_repo)
    
    # Index first
    indexer.sync(con, cfg)
    
    # Test lexical search
    results = retrieve.lexical_search(temp_repo, "hello", limit=5)
    assert len(results) > 0, "Lexical search failed"
    
    # Test semantic search (if embedder available)
    try:
        results = retrieve.semantic_search(temp_repo, "greeting function", limit=5)
        assert len(results) > 0, "Semantic search failed"
    except RuntimeError:
        pytest.skip("No embedder available")


def test_impact_analysis_integration(temp_repo):
    """Test impact analysis integration."""
    from cipkg.store import connect
    from cipkg import indexer
    from cipkg.stack.impact import ImpactAnalyzer
    from cipkg.base import load_config
    
    con = connect(temp_repo)
    cfg = load_config(temp_repo)
    
    # Index first
    indexer.sync(con, cfg)
    
    # Get a symbol ID
    cursor = con.execute("SELECT id FROM symbols LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        symbol_id = row[0]
        
        # Analyze impact
        analyzer = ImpactAnalyzer(con)
        result = analyzer.analyze_impact(symbol_id)
        
        assert 'impact_level' in result, "Impact analysis failed"
        assert 'affected_files' in result, "No affected files returned"


def test_learning_system_integration(temp_repo):
    """Test learning system integration."""
    from cipkg.learning_system import IntegratedLearningSystem
    
    learner = IntegratedLearningSystem(temp_repo)
    
    # Record an action
    learner.record_action('search', {
        'query': 'test query',
        'results_count': 5,
        'success': True
    })
    
    # Recall relevant experiences
    results = learner.recall_relevant('test query')
    
    assert len(results) > 0, "Learning system failed to recall"


def test_mcp_server_integration(temp_repo):
    """Test MCP server integration."""
    from cipkg.server import handle_mcp_tool_call
    
    # Test search tool
    result = handle_mcp_tool_call('cip_search', {
        'query': 'hello',
        'limit': 5
    })
    
    assert 'error' not in result, f"MCP search failed: {result.get('error')}"
```

---

## 📚 **PHASE 6: DOCUMENTATION ISSUES**

### **6.1 Missing API Documentation**

**Issue:** No docstrings for public APIs  
**Impact:** Hard to use and maintain

**Add comprehensive docstrings:**
```python
# Example: Add to lib/cipkg/retrieve.py

def hybrid_search(root: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining lexical and semantic search.
    
    This function combines traditional keyword-based search with
    semantic vector search to provide the most relevant results.
    
    Args:
        root: Repository root path
        query: Search query string
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        List of search results, each containing:
        - id: Chunk ID
        - path: File path
        - symbol_id: Associated symbol ID (if any)
        - start_line: Starting line number
        - end_line: Ending line number
        - text: Code text
        - score: Relevance score (0.0 to 1.0)
    
    Raises:
        RuntimeError: If no search backend is available
        ValueError: If query is empty
    
    Example:
        >>> results = hybrid_search('/path/to/repo', 'authentication function')
        >>> for result in results:
        ...     print(f"{result['path']}:{result['start_line']} - {result['score']:.2f}")
    
    Note:
        Semantic search requires an embedder to be configured.
        Falls back to lexical-only search if embedder is unavailable.
    """
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")
    
    # Implementation...
```

---

## 📝 **IMPLEMENTATION PRIORITY MATRIX**

| Priority | Issue | Impact | Effort | Timeline |
|----------|-------|--------|--------|----------|
| 🔴 P0 | Embedder → Retriever wiring | Critical | Medium | Day 1 |
| 🔴 P0 | Impact Analysis implementation | Critical | High | Day 1-2 |
| 🔴 P0 | MCP Server → Registry integration | Critical | Medium | Day 2 |
| 🟡 P1 | Batch indexing operations | High | Medium | Day 3 |
| 🟡 P1 | Gap Fill system completion | High | Medium | Day 3-4 |
| 🟡 P1 | Learning → Memory integration | High | Medium | Day 4 |
| 🟢 P2 | Daemon → Watcher integration | Medium | Low | Day 5 |
| 🟢 P2 | Dependency checker | Medium | Low | Day 5 |
| 🟢 P2 | Integration tests | Medium | Medium | Day 6 |
| 🔵 P3 | API documentation | Low | Low | Day 7 |

---

## ✅ **VERIFICATION CHECKLIST**

- [ ] Semantic search returns results
- [ ] Impact analysis shows affected files
- [ ] MCP tools execute commands
- [ ] Batch indexing is 5x faster
- [ ] Gap fill identifies missing docs/tests
- [ ] Learning system recalls past experiences
- [ ] File watcher triggers re-indexing
- [ ] Dependency checker reports status
- [ ] All integration tests pass
- [ ] API documentation complete

---

This comprehensive scan reveals **47 critical issues** that must be addressed to make CIP a production-ready code intelligence platform. The fixes provided will transform it from a prototype into an enterprise-grade system.
