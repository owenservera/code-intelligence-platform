# CIP - Code Intelligence Platform

A continuously updated model of your codebase — structure, history, tests, runtime health, and semantic audit. CIP helps AI agents and developers navigate complex codebases efficiently through intelligent indexing and retrieval.

## Features

- **Semantic Code Search**: Find code by intent, not just keywords
- **Symbol Navigation**: Jump to definitions with relationship context
- **Impact Analysis**: Understand blast radius before making changes
- **Quality Auditing**: Detect secrets, N+1 queries, missing indexes, and more
- **Stack-Aware**: Specialized support for TypeScript/Next.js/Prisma/SQLite
- **Git Integration**: History tracking and co-change analysis
- **MCP Server**: Expose index capabilities via Model Context Protocol
- **HTTP API**: REST endpoints for integration with tools

## Installation

### Prerequisites

- Python 3.8+
- SQLite3

### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd index

# Run the installer
bash install.sh

# Initialize the index
cip sync

# Start the daemon (optional, for embedding service)
cip daemon start
```

## Usage

### Basic Commands

```bash
# Search for code by intent
cip search "user authentication flow"

# Find symbol definitions
cip symbol UserProfile

# Check impact of changing a file
cip impact lib/routes/auth.ts

# Get contextual code pack
cip context "how to handle errors"

# Run quality audit
cip audit

# View critical findings
cip findings --severity critical

# Check for broken tests/errors
cip broken
```

### MCP Server

```bash
# Start MCP server
cip mcp

# Or run as HTTP service
cip serve
```

## Configuration

CIP uses a TOML configuration file. Default settings are in `config.default.toml`. You can create a custom `config.toml` in the `.cip/` directory.

### Key Configuration Options

```toml
[index]
max_file_kb = 512
exclude = []
test_globs = ["test_", "_test.", ".test.", ".spec.", "/tests/", "__tests__"]

[embed]
backend = "auto"  # auto | service | local | hashing
model = "BAAI/bge-small-en-v1.5"
dim = 384

[retrieval]
lexical_k = 30
vector_k = 30
context_budget_tokens = 6000
```

## Architecture

CIP consists of several components:

- **Indexer**: Parses and chunks code files
- **Embedder**: Generates semantic embeddings (supports multiple backends)
- **Vector Store**: SQLite-based vector storage
- **Retriever**: Hybrid lexical + semantic search
- **Auditor**: Quality rule engine
- **Daemon**: Background service for embedding operations

## Development

### Project Structure

```
index/
├── lib/cipkg/           # Core library
│   ├── indexer.py       # Code parsing and indexing
│   ├── embed.py         # Embedding backends
│   ├── retrieve.py      # Search and retrieval
│   ├── stack/           # Stack-specific analyzers
│   └── ...
├── bin/                 # CLI executables
├── bootstrap/          # Bootstrap scripts
└── config.default.toml  # Default configuration
```

### Testing

```bash
# Run self-tests
cip selftest

# Run specific test modules
python -m pytest lib/cipkg/test_*.py
```

## Stack Pack

CIP includes specialized analyzers for:

- **Next.js**: Route detection, component analysis
- **Prisma**: Schema validation, query analysis
- **TypeScript**: Type tracking, import graph
- **SQLite**: Query optimization, index detection

## License

[Specify your license here - e.g., MIT, Apache-2.0, etc.]

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## Support

For issues and questions, please use the GitHub issue tracker.