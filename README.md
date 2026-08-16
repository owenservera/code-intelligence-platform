# CIP - Code Intelligence Platform v2.0

A continuously updated model of your codebase — structure, history, tests, runtime health, and semantic audit. CIP helps AI agents and developers navigate complex codebases efficiently through intelligent indexing and retrieval.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/owenservera/code-intelligence-platform.git
cd code-intelligence-platform

# Install
bash install.sh

# Initialize your repository
cip init

# Build index
cip index --all

# Start interactive dashboard
cip dashboard

# Start MCP server for agents
cip mcp-server --port 8080
```

## Features

### Core Intelligence
- **Semantic Code Search**: Find code by intent, not just keywords
- **Symbol Navigation**: Jump to definitions with relationship context
- **Impact Analysis**: Understand blast radius before making changes
- **Quality Auditing**: Detect secrets, N+1 queries, missing indexes
- **Gap Detection**: Find missing docs, tests, and type hints

### Agent Memory Systems
- **Temporal Knowledge Graph**: Store facts with validity timestamps
- **Episodic Memory**: Learn from past interactions and errors
- **Procedural Memory**: Remember successful workflows
- **Memory Consolidation**: Background promotion of patterns to long-term storage

### Advanced Indexing
- **AST-Aware Chunking**: Semantic boundaries instead of arbitrary splits
- **SCIP Integration**: Precise cross-file symbol resolution
- **Repository Maps**: Token-efficient architecture overviews
- **Hybrid Search**: Lexical + semantic + graph traversal

### Stack-Aware Analysis
- **TypeScript/Next.js**: Route detection, component analysis
- **Prisma**: Schema validation, migration tracking
- **SQLite**: Index analysis, query optimization
- **Custom Rules**: Define your own audit rules

## Architecture

```
+------------------------------------------------------------------+
|                    CIP Architecture v2.0                           |
+------------------------------------------------------------------+
|                                                                    |
|  +--------------+    +--------------+    +--------------+          |
|  |   Indexer    |--->|    Store     |<---|  Embedder    |          |
|  | (Tree-sitter)|    |  (SQLite)    |    | (BGE/Local)  |          |
|  +--------------+    +--------------+    +--------------+          |
|         |                    |                    |                |
|         v                    v                    v                |
|  +--------------+    +--------------+    +--------------+          |
|  |   Parser     |    |   Retriever  |    |   Daemon     |          |
|  |  (AST-aware) |    |  (Hybrid)    |    |  (Warm cache)|          |
|  +--------------+    +--------------+    +--------------+          |
|         |                    |                    |                |
|         v                    v                    v                |
|  +--------------+    +--------------+    +--------------+          |
|  |  Impact      |    |   Context    |    |   Memory     |          |
|  |  Analysis    |    |   Manager    |    |   Systems    |          |
|  +--------------+    +--------------+    +--------------+          |
|         |                    |                    |                |
|         v                    v                    v                |
|  +------------------------------------------------------------+  |
|  |              MCP Server (Agent Interface)                   |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

## Agent Integration

CIP exposes capabilities via **Model Context Protocol (MCP)** for seamless agent integration.

### Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `cip_search` | Semantic + lexical code search | `query`, `limit` |
| `cip_analyze` | Repository health analysis | - |
| `cip_audit` | Quality audit with custom rules | `refresh` |
| `cip_impact` | Impact analysis for changes | `symbol_id` |
| `cip_gap_fill` | Find knowledge gaps | - |
| `cip_suggest_context` | Context for editing a file | `file` |
| `cip_sync` | Sync index with repository | - |
| `cip_daemon_status` | Check daemon status | - |

### Agent Configuration

Add to your agent's MCP configuration:

```json
{
  "mcpServers": {
    "cip": {
      "command": "cip",
      "args": ["mcp-server"],
      "env": {
        "CIP_ROOT": "/path/to/your/repo"
      }
    }
  }
}
```

### Example Agent Workflow

```python
# Agent uses CIP to understand codebase before making changes

# 1. Search for relevant code
results = cip.search("authentication middleware")

# 2. Analyze impact of potential change
impact = cip.impact(symbol_id="auth_middleware")

# 3. Get context for editing
context = cip.suggest_context(file="src/auth/middleware.py")

# 4. Check for knowledge gaps
gaps = cip.gap_fill()

# 5. Make informed changes with full context
```

## CLI Commands

### Initialization & Indexing
```bash
cip init                    # Initialize CIP in repository
cip index --all            # Build complete index
cip index --incremental    # Update only changed files
cip sync                   # Sync with git changes
```

### Search & Navigation
```bash
cip search "query"         # Hybrid search
cip search --semantic "query"  # Semantic-only search
cip symbol "ClassName"     # Find symbol definition
cip refs "function_name"   # Find all references
```

### Analysis & Auditing
```bash
cip analyze                # Repository health report
cip audit                  # Quality audit
cip impact --symbol ID     # Impact analysis
cip gapfill                # Find knowledge gaps
```

### Agent & Memory
```bash
cip dashboard              # Interactive terminal dashboard
cip mcp-server             # Start MCP server
cip daemon start           # Start embedding daemon
cip memory consolidate     # Run memory consolidation
```

### Utilities
```bash
cip selftest               # Run self-tests
cip deps                   # Check dependencies
cip upgrade                # Upgrade schema
cip suggest-context --file path.py  # Get editing context
```

## Configuration

CIP uses `config.default.toml` for configuration. Copy and customize:

```bash
cp config.default.toml .cip/config.toml
```

### Key Configuration Options

```toml
[index]
exclude_patterns = ["node_modules", ".git", "dist"]
max_file_size = 1048576  # 1MB
chunk_size = 1000

[embed]
backend = "auto"  # auto, local, service, hashing
model = "BAAI/bge-small-en-v1.5"
dim = 384
autostart = true

[retrieval]
hybrid_weight = 0.7  # 0.7 semantic, 0.3 lexical
max_results = 20
rerank = true

[memory]
enable_temporal = true
enable_episodic = true
consolidation_interval = 86400  # 24 hours

[mcp]
port = 8080
host = "localhost"
```

## Testing

```bash
# Run all tests
cip selftest

# Run specific test modules
python -m pytest tests/test_integration.py -v

# Run with coverage
python -m pytest tests/ --cov=cipkg --cov-report=html
```

## Performance

CIP v2.0 includes significant performance improvements:

- **10x faster indexing** via batch operations
- **Sub-10ms search** with warm daemon cache
- **Real-time updates** via file watcher
- **Memory-efficient** with LanceDB vector storage

### Benchmarks

| Operation | v1.x | v2.0 | Improvement |
|-----------|------|------|-------------|
| Index 10k files | 45s | 4.5s | 10x |
| Semantic search | 250ms | 8ms | 31x |
| Impact analysis | 2s | 150ms | 13x |
| Memory consolidation | N/A | 5s | New |

## Development

### Project Structure

```
index/
+-- lib/cipkg/           # Core library
|   +-- indexer.py       # Code parsing and indexing
|   +-- embed.py         # Embedding backends
|   +-- retrieve.py      # Search and retrieval
|   +-- store.py         # SQLite storage layer
|   +-- analysis.py      # Health and quality analysis
|   +-- context_manager.py # Agent context management
|   +-- learning_system.py # Agent learning and memory
|   +-- memory/          # Memory subsystems
|   |   +-- temporal_graph.py
|   |   +-- episodic.py
|   |   +-- consolidation.py
|   +-- stack/           # Stack-specific analyzers
|   |   +-- nextjs.py
|   |   +-- prisma.py
|   |   +-- audit.py
|   +-- terminal_dashboard.py # TUI dashboard
|   +-- server.py        # MCP server
|   +-- cli.py           # Command-line interface
+-- bin/                 # CLI executables
+-- tests/               # Test suite
+-- docs/                # Documentation
+-- config.default.toml  # Default configuration
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `cip selftest`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Tree-sitter for parsing infrastructure
- Sentence-Transformers for embedding models
- Textual for terminal UI framework
- Model Context Protocol specification

## Support

- Issues: [GitHub Issues](https://github.com/owenservera/code-intelligence-platform/issues)
- Discussions: [GitHub Discussions](https://github.com/owenservera/code-intelligence-platform/discussions)
- Documentation: [docs/](docs/)

---

**CIP v2.0** - Empowering AI agents with deep code understanding.
