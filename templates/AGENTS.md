# AGENTS.md - CIP Code Intelligence Platform

**Repository:** code-intelligence-platform
**Version:** 2.0
**Last Updated:** 2026

## Purpose

This file provides AI agents with the context, rules, and capabilities needed to effectively use and contribute to the CIP Code Intelligence Platform.

## Repository Overview

CIP is a code intelligence platform that provides:
- Semantic code search and navigation
- Impact analysis for code changes
- Quality auditing and gap detection
- Agent memory systems (temporal, episodic, procedural)
- MCP server for agent integration
- Repo-specific configuration profiles
- Automated sync to global CIP installation

## Architecture

### Core Components

```
lib/cipkg/
+-- indexer.py          # File parsing and indexing
+-- embed.py            # Embedding generation
+-- retrieve.py         # Search and retrieval
+-- store.py            # SQLite storage layer
+-- analysis.py         # Health and quality analysis
+-- context_manager.py  # Agent context management
+-- learning_system.py  # Agent learning
+-- memory/             # Memory subsystems
|   +-- temporal_graph.py  # Temporal Knowledge Graph
|   +-- episodic.py        # Episodic memory
|   +-- consolidation.py   # Memory consolidation
+-- stack/              # Stack-specific analyzers
+-- terminal_dashboard.py # TUI dashboard
+-- server.py           # MCP server
+-- cli.py              # Command-line interface
+-- repo-settings/      # Repo-specific configuration
+-- sync_global/        # Global sync system
```

### Data Flow

1. **Indexing**: Files -> Parser -> Symbols/Chunks -> Store
2. **Embedding**: Chunks -> Embedder -> Vectors -> Store
3. **Search**: Query -> Retriever -> Results -> Context Manager
4. **Memory**: Actions -> Learning System -> Memory Store

## Build & Test Commands

### Installation
```bash
pip install -r requirements.txt
cip init
```

### Testing
```bash
# Run all tests
cip selftest

# Run specific tests
python -m pytest tests/test_integration.py -v

# Run with coverage
python -m pytest tests/ --cov=cipkg --cov-report=term-missing
```

### Development
```bash
# Start development server
cip daemon start

# Start MCP server
cip mcp-server --port 8080

# Start dashboard
cip dashboard
```

## MCP Tools Available

Agents can use these tools via the MCP server:

### Search & Navigation
- `cip_search`: Hybrid semantic + lexical search
  - Parameters: `query` (string), `limit` (int, default 10)
  - Returns: List of code snippets with relevance scores

- `cip_symbol`: Find symbol definition
  - Parameters: `name` (string)
  - Returns: Symbol location and metadata

- `cip_refs`: Find all references to a symbol
  - Parameters: `symbol_id` (string)
  - Returns: List of referencing locations

### Analysis & Impact
- `cip_analyze`: Repository health analysis
  - Parameters: None
  - Returns: Health score, issues, recommendations

- `cip_impact`: Impact analysis for code changes
  - Parameters: `symbol_id` (string)
  - Returns: Affected files, test files, impact level

- `cip_audit`: Quality audit with custom rules
  - Parameters: `refresh` (bool, default false)
  - Returns: Findings by severity

### Context & Memory
- `cip_suggest_context`: Get context for editing a file
  - Parameters: `file` (string)
  - Returns: Symbols, dependencies, tests, gaps

- `cip_gap_fill`: Find knowledge gaps
  - Parameters: None
  - Returns: Missing docs, tests, type hints

- `cip_memory_recall`: Recall relevant past experiences
  - Parameters: `query` (string)
  - Returns: Relevant episodes and memories

### System Operations
- `cip_sync`: Sync index with repository
  - Parameters: None
  - Returns: Files updated, symbols added

- `cip_daemon_status`: Check daemon status
  - Parameters: None
  - Returns: Daemon state, uptime, cache stats

## Code Style & Conventions

### Python Style
- Follow PEP 8
- Use type hints for all function signatures
- Docstrings in Google style
- Maximum line length: 100 characters

### Naming Conventions
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

### Error Handling
- Use specific exceptions, not bare `except:`
- Log all swallowed exceptions with `log_swallowed()`
- Provide meaningful error messages

### Database Operations
- Use parameterized queries (never string interpolation)
- Batch operations for performance
- Always commit transactions
- Use context managers for connections

## Testing Requirements

### Test Coverage
- All new features must have tests
- Minimum 80% code coverage
- Integration tests for critical paths

### Test Structure
```python
def test_feature_name():
    """Test description."""
    # Arrange
    setup_test_data()

    # Act
    result = function_under_test()

    # Assert
    assert result == expected_value
```

### Running Tests
```bash
# Before committing
cip selftest

# Specific test file
python -m pytest tests/test_feature.py -v

# With coverage
python -m pytest tests/ --cov=cipkg --cov-report=term-missing
```

## Security Guidelines

### Never Commit
- API keys or secrets
- Database credentials
- Personal information
- Large binary files

### Code Security
- Validate all user inputs
- Sanitize file paths
- Use parameterized SQL queries
- Avoid `eval()` and `exec()`

## Deployment

### Production Checklist
- [ ] All tests passing
- [ ] Dependencies pinned in requirements.txt
- [ ] Configuration validated
- [ ] Logging configured
- [ ] Error handling comprehensive
- [ ] Documentation updated

### Environment Variables
```bash
CIP_ROOT=/path/to/repository
CIP_CONFIG=/path/to/config.toml
CIP_LOG_LEVEL=INFO
CIP_DAEMON_PORT=8765
CIP_MCP_PORT=8080
```

## Key Files to Know

| File | Purpose |
|------|---------|
| `lib/cipkg/cli.py` | CLI entry point and command dispatch |
| `lib/cipkg/indexer.py` | Core indexing logic |
| `lib/cipkg/retrieve.py` | Search and retrieval |
| `lib/cipkg/store.py` | Database operations |
| `lib/cipkg/server.py` | MCP server implementation |
| `lib/cipkg/context_manager.py` | Agent context building |
| `lib/cipkg/learning_system.py` | Agent learning and memory |
| `lib/cipkg/memory/temporal_graph.py` | Temporal Knowledge Graph |
| `lib/cipkg/memory/episodic.py` | Episodic memory system |
| `lib/cipkg/memory/consolidation.py` | Memory consolidation |
| `config.default.toml` | Default configuration |
| `AGENTS.md` | This file |

## Recent Changes (v2.0)

### New Features
- Temporal Knowledge Graph for agent memory
- Episodic Memory for learning from experiences
- AST-aware chunking for better semantics
- SCIP integration for precise symbol resolution
- Repository maps for token-efficient context
- Impact analysis engine
- Gap detection system
- Memory consolidation daemon
- Context management system
- Learning system for pattern detection

### Bug Fixes
- Fixed recursive loop in dashboard alerts
- Fixed missing CLI handlers
- Fixed embedder fallback chain
- Fixed silent exception handling
- Fixed batch indexing performance

### Breaking Changes
- `handle_suggest_context_command` now requires `--file` argument
- Memory system requires migration from JSONL to SQLite
- MCP server port changed from 8765 to 8080

## Agent Workflows

### Workflow 1: Understanding a Codebase
```
1. cip_analyze -> Get repository health overview
2. cip_search "main entry point" -> Find key files
3. cip_suggest_context --file src/main.py -> Understand structure
4. cip_gap_fill -> Identify areas needing attention
```

### Workflow 2: Making a Safe Change
```
1. cip_search "function to modify" -> Find target
2. cip_impact --symbol ID -> Understand blast radius
3. cip_suggest_context --file target.py -> Get editing context
4. Make changes
5. cip_sync -> Update index
6. cip_audit -> Verify quality
```

### Workflow 3: Debugging an Issue
```
1. cip_search "error message" -> Find related code
2. cip_memory_recall "similar error" -> Check past experiences
3. cip_refs "problematic_function" -> Find all usages
4. cip_impact --symbol ID -> Understand dependencies
```

### Workflow 4: Code Review
```
1. cip_suggest_context --file src/module.py -> Get file context
2. cip_gap_fill -> Check for gaps in the file
3. cip_audit -> Analyze quality
4. Generate review with context, gaps, and findings
```

## Support & Resources

- **Documentation**: `docs/` directory
- **Tests**: `tests/` directory
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## Agent Checklist

Before making changes:
- [ ] Read this AGENTS.md file
- [ ] Understand the architecture
- [ ] Check existing tests
- [ ] Follow code style guidelines
- [ ] Run tests before committing
- [ ] Update documentation if needed

After making changes:
- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No security issues introduced
- [ ] Performance not degraded

---

**Remember:** CIP is designed to help agents understand codebases deeply. Use its capabilities to make informed, safe, and effective changes.
