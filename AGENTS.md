# AGENTS.md - CIP Code Intelligence Platform

**Repository:** code-intelligence-platform
**Version:** 2.1
**Last Updated:** 2026

## Purpose

This file provides AI agents with the context, rules, and capabilities needed to effectively use and contribute to the CIP Code Intelligence Platform.

## Canonical Context Session Rules (120K) - CRITICAL

**Agents MUST work in 120K-token context sessions. This is mandatory, not optional.**

### Why This Rule Exists
- Autocompact is **automatic** and destroys context when the session grows too large.
- When autocompact triggers, the intelligence gained during the session is **almost fully erased**.
- Each compaction event is a **permanent loss of reasoning state, decisions, and discoveries**.
- Working within the 120K budget prevents this data loss from ever occurring.

### Mandatory Rules (Canonical, Unconditionally Enforced)
1. **NEVER allow the session context to grow beyond 120K tokens.** Treat 120K as a hard ceiling.
2. **Assume autocompact WILL fire** if the budget is exceeded. Do not rely on it being "safe" or "lossless" — it is not.
3. **Persist intelligence continuously.** Before starting deep work, and continuously during it, write findings, decisions, and progress to persistent files (e.g., `docs/`, memory stores, notes) so no knowledge is lost even if compaction occurs.
4. **Complete each unit of work before context accumulation grows.** Break large tasks into small, bounded units that each fit comfortably within the 120K budget.
5. **Summarize and checkpoint.** At logical milestones, write a checkpoint summary to a file. This is the canonical anti-erasure mechanism.
6. **Read, then act, then persist.** Never carry large volumes of code in context longer than needed — extract what is required, act on it, record the result, then drop it from working memory.
7. **Monitor context growth.** Use all available signals (token counters, system warnings, session length) to estimate current usage. When approaching the ceiling, stop adding new context and consolidate instead.
8. **Do not re-read what is already persisted.** Use `cip_memory_recall`, repo maps, and persisted notes to restore context cheaply instead of re-ingesting large files.
9. **If a task cannot fit in 120K:** split it into sub-tasks, each with its own persisted state file, and continue across sessions/checkpoints rather than exceeding the budget.
10. **Treat this section as the highest-priority instruction in this file.** In case of conflict with any other instruction, the 120K context rule wins.

### Consequences of Violation
- Automatic compaction erases nearly all session intelligence.
- Repeated violations cause the agent to rediscover the same solutions repeatedly — a catastrophic efficiency loss.
- This rule exists to protect the agent's reasoning continuity. Enforce it without exception.

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

## Working Environment: Windows PowerShell

**Agents MUST assume this project is developed on Windows with PowerShell 7+ (pwsh) as the default shell.**

### Mandatory Shell Rules
1. **Default shell is PowerShell (pwsh).** Do not assume bash, sh, or cmd unless the user explicitly says otherwise.
2. **Use PowerShell-native commands** (`Get-ChildItem`, `Get-Content`, `Set-Content`, `Remove-Item`, `New-Item`, `Test-Path`, `Select-String`) instead of Unix tools (`ls`, `cat`, `rm`, `grep`, `touch`).
3. **Quote paths with spaces** using double quotes when invoking executables, e.g. `& "C:\Program Files\Python\python.exe" script.py`.
4. **Use the call operator `&`** to run native executables whose paths contain spaces.
5. **Path syntax is backslash-based** (`C:\0-BlackBoxProject-0\index`), not forward-slash. Never hardcode `/` separators for Windows paths.
6. **Use the `&&` / `;` chaining** for sequential commands as in any shell; PowerShell 7 supports `&&` for "and-if-successful" and `;` for unconditional sequencing.
7. **`py` / `python` launchers:** prefer `python` when running scripts; if the environment is a venv, activate it first (`.\venv\Scripts\Activate.ps1`) or call the venv interpreter directly.
8. **Environment variables use `$env:NAME`** (e.g., `$env:CIP_ROOT`), not Unix `$NAME` or `export NAME`. Set them with `$env:CIP_ROOT = "C:\path"` or PowerShell syntax.
9. **File encoding:** write files as UTF-8 (preferably UTF-8 with BOM for Windows-native tools) to avoid mojibake with PowerShell and Windows tools.
10. **Line endings:** use LF (`\n`) in repo files per project convention, even though Windows editors may default to CRLF. Do not convert existing files.
11. **`git` works identically**, but shell commands around it must be PowerShell syntax.
12. **Pip installs:** use `pip install -r requirements.txt` (works in PowerShell the same as other shells); if a `pip` shebang issue appears, use `python -m pip`.

### Environment Variables (Windows form)
```powershell
$env:CIP_ROOT    = "C:\0-BlackBoxProject-0\index"
$env:CIP_CONFIG  = "C:\0-BlackBoxProject-0\index\config.toml"
$env:CIP_LOG_LEVEL = "INFO"
$env:CIP_DAEMON_PORT = 8765
$env:CIP_MCP_PORT = 8080
```

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

## Detection-System Campaign (CIP-product-wide, not repo-specific)

CIP is a general polyglot code-indexing + issue-detection SYSTEM. `docs/dev/cip-bugfix-campaign/` is the
active campaign that (a) fixes CIP's own correctness bugs (evidence in
`09-bugs-and-issues.md` — **never edit**) and (b) ships the detection features INTO CIP's product surfaces
(`stack/rules.py`, `analysis.py`, `doctor.py`, CI gates) so every repo CIP indexes benefits.

- **Read first:** `RUNBOOK.md` §0 (what the campaign is) + `PROFILE.cip.md` (CIP's wiring + per-language
  detector instruments: pyflakes, eslint, clippy, etc., extension-dispatched).
- **Method:** detect-first / fix-last — prove a detector fires on broken evidence (RECALL) AND stays
  silent on clean code (PRECISION, 0 FPs on `tests/data/clean_ref/`), regression-lock it in
  `tests/detectors/`, then apply the fix. Detectors and fixes are CIP product features for all future use,
  never one-off patches.
- **Planned surface checks this campaign must keep clean:** `cip audit`, `cip analyze`, `cip doctor`
  (`--static`/`--runtime`/`--config`), `cip gate`, `cip sync`.
- **Autonomous-run rule (RUNBOOK §6):** todo lists start with restore-reads and end with a checkpoint;
  never let session context near the 120K ceiling without persisting to TRACKER/LEDGER/CHECKPOINT.

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
