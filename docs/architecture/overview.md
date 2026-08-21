# Architecture Overview

## System Components

CIP (Code Intelligence Platform) consists of several interconnected components that work together to provide intelligent code analysis and retrieval.

## Core Components

### 1. Indexer (`indexer.py`)

The indexer is responsible for parsing and chunking code files into searchable units.

**Responsibilities:**
- File discovery and filtering
- Language detection
- Symbol extraction (functions, classes, variables)
- Code chunking for semantic analysis
- Import/dependency tracking

**Supported Languages:**
- TypeScript/JavaScript (via tree-sitter or regex)
- Python (via tree-sitter or regex)
- Rust, Go, and others (regex-based)

### 2. Embedder (`embed.py`)

The embedder generates semantic vector representations of code chunks.

**Backends:**
- **Auto**: Automatically selects best available backend
- **Service**: External embedding service (OpenAI, etc.)
- **Local**: Local sentence-transformers models
- **Hashing**: Deterministic hash-based fallback (no ML)

**Models:**
- Default: BAAI/bge-small-en-v1.5 (384 dimensions)
- Configurable to any sentence-transformers model

### 3. Vector Store (`vecstore.py`)

Manages vector storage and similarity search.

**Storage Backends:**
- **SQLite**: Default, uses BLOB storage with numpy acceleration
- **sqlite-vec**: Extension for very large repositories (>100k chunks)

**Search Algorithm:**
- Cosine similarity search
- Optional numpy acceleration for O(1) repeated KNN
- Hybrid lexical + vector ranking

### 4. Retriever (`retrieve.py`)

Handles search queries and result ranking.

**Features:**
- Hybrid lexical (FTS) + semantic search
- Reciprocal Rank Fusion (RRF) for result combination
- Context budget management
- Intent-based query routing

### 5. Parser System

**Tree-sitter Parser (`tree_parser.py`):**
- Accurate symbol extraction
- Real call graph construction
- Support for TS/TSX/JS/Python
- Graceful fallback to regex parser

**Regex Parser (`parsers.py`):**
- Universal language support
- Pattern-based symbol detection
- Import extraction
- Comment and docstring handling

### 6. Git Integration (`gitindex.py`)

Tracks code evolution and relationships over time.

**Features:**
- Commit history indexing
- Co-change detection (files changed together)
- Hotspot identification (recently changed, high-impact files)
- Author and timestamp tracking

### 7. Stack Analyzers (`stack/`)

Specialized analyzers for specific technology stacks.

**Next.js Analyzer (`stack/nextjs.py`):**
- Route detection (API and page routes)
- Component analysis
- "use client" directive tracking
- Server/client boundary detection

**Prisma Analyzer (`stack/prisma.py`):**
- Schema validation
- Model usage tracking
- Query pattern analysis
- Migration drift detection

**Common Utilities (`stack/common.py`):**
- Shared analysis patterns
- Rule engine framework
- Finding generation

### 8. Quality Auditor (`stack/audit.py`)

Implements semantic code quality rules.

**Rule Categories:**
- **Security**: Hardcoded secrets, SQL injection risks
- **Database**: N+1 queries, missing indexes, schema drift
- **Environment**: Undefined env vars, unread env vars
- **Architecture**: Layer violations, orphan files, circular imports
- **Testing**: Untested hotspots, test coverage gaps
- **Code Quality**: Duplicates, god modules, complexity

### 9. Runtime Adapters (`runtime_adapters.py`)

Integrates with external tooling for quality signals.

**Supported Tools:**
- Vitest (JavaScript/TypeScript testing)
- Jest (JavaScript testing)
- Pytest (Python testing)
- TypeScript Compiler (type errors)
- Generic JSON-based tools

### 10. Daemon (`daemon.py`)

Background service for long-running operations.

**Responsibilities:**
- File watching and automatic reindexing
- Embedding service (single-writer pattern)
- Lock management for concurrent access
- Health monitoring

### 11. Server (`server.py`)

HTTP API for external integration.

**Endpoints:**
- Search and retrieval
- Index management
- Audit operations
- Health checks

### 12. MCP Integration

Model Context Protocol server for AI agent integration.

**Features:**
- Standardized tool interface
- Streaming support for long operations
- Context-aware responses
- Agent-optimized workflow

## Data Flow

### Indexing Flow

```
File Discovery → Language Detection → Parsing → Symbol Extraction → 
Chunking → Embedding → Vector Storage → Index Update
```

### Search Flow

```
Query → Intent Analysis → Lexical Search → Vector Search → 
Result Fusion → Ranking → Context Assembly → Response
```

### Audit Flow

```
Rule Selection → Code Analysis → Pattern Matching → 
Finding Generation → Severity Assessment → Storage/Reporting
```

## Storage Schema

### Core Tables

- **files**: File metadata and paths
- **symbols**: Code symbols (functions, classes, etc.)
- **chunks**: Text chunks for search
- **vectors**: Embedding vectors
- **edges**: Relationships (imports, calls, extends, etc.)
- **findings**: Quality audit results
- **commits**: Git history
- **signals**: Runtime tool results

## Configuration System

### Configuration Hierarchy

1. `config.default.toml` - Default settings
2. `.cip/config.toml` - Repository-specific overrides
3. Environment variables - Runtime overrides

### Key Configuration Sections

- `[index]`: File handling and discovery
- `[embed]`: Embedding backend and model selection
- `[retrieval]`: Search parameters and limits
- `[audit]`: Quality rule configuration
- `[git]`: History indexing parameters
- `[serve]`: HTTP server settings

## Extension Points

### Custom Parsers

Add language support by implementing the parser interface:

```python
def parse(path, source, language):
    # Return symbols, imports, chunks, calls
    return {"symbols": [...], "imports": [...], "chunks": [...], "calls": [...]}
```

### Custom Rules

Add audit rules by extending the rule engine:

```python
class CustomRule(Rule):
    def check(self, context):
        # Implementation
        pass
```

### Custom Embedders

Add embedding backends by implementing the embedder interface:

```python
class CustomEmbedder:
    def embed(self, texts):
        # Return vectors
        return [vector1, vector2, ...]
```

## Performance Considerations

### Optimization Strategies

- **Incremental Indexing**: Only reindex changed files
- **Vector Caching**: Cache embedding vectors for repeated access
- **Lazy Loading**: Load heavy components on demand
- **Connection Pooling**: Reuse database connections
- **Parallel Processing**: Multi-worker support for large repos

### Scaling Limits

- **Small Repos** (<10k files): Default configuration
- **Medium Repos** (10k-100k files): Consider numpy acceleration
- **Large Repos** (>100k files): Use sqlite-vec extension

## Security Considerations

### Data Privacy

- All indexing happens locally
- No external API calls by default
- Configurable external embedding services
- No code sent to external services unless explicitly configured

### Access Control

- File system permissions respected
- Configuration files can restrict access
- Daemon runs with user permissions
- No privilege escalation

## Monitoring & Observability

### Health Checks

- `cip selftest` - Verify core functionality
- `cip index-status` - Check index freshness
- `cip daemon status` - Daemon health

### Logging

- Configurable log levels
- Structured logging for debugging
- Performance metrics collection
- Error tracking and reporting