# Installation Guide

## Prerequisites

- Python 3.8 or higher
- SQLite3
- Git (for git integration features)

## Quick Installation

### Using the Installer Script

```bash
# Clone the repository
git clone https://github.com/owenservera/code-intelligence-platform.git
cd code-intelligence-platform

# Run the installer
bash install.sh

# Initialize the index
cip sync
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/owenservera/code-intelligence-platform.git
cd code-intelligence-platform

# Install Python dependencies
pip install -r requirements.txt

# Add to PATH (optional)
export PATH="$PATH:$(pwd)/bin"
```

## Optional Dependencies

### Tree-sitter Parsers (Enhanced Symbol Extraction)

For more accurate symbol extraction and call graph analysis:

```bash
pip install tree-sitter
pip install tree-sitter-typescript tree-sitter-python tree-sitter-javascript
pip install tree-sitter-rust tree-sitter-go
```

### Real Embeddings

For better semantic search quality:

```bash
# Option 1: Sentence Transformers
pip install sentence-transformers

# Option 2: OpenAI (set OPENAI_API_KEY environment variable)
export OPENAI_API_KEY="your-api-key"
```

### High-Performance Vector Storage

For very large repositories (>100k chunks):

```bash
pip install sqlite-vec
```

Then update your config:

```toml
[vector]
backend = "sqlite-vec"
```

## Configuration

CIP uses a TOML configuration file. The default configuration is in `config.default.toml`. You can create a custom configuration by creating `.cip/config.toml` in your repository.

### Basic Configuration

```toml
[index]
max_file_kb = 512
exclude = []
test_globs = ["test_", "_test.", ".test.", ".spec.", "/tests/", "__tests__"]

[embed]
backend = "auto"  # auto | service | local | hashing
model = "BAAI/bge-small-en-v1.5"
dim = 384
service_port = 8787
autostart = true

[retrieval]
lexical_k = 30
vector_k = 30
context_budget_tokens = 6000
```

## Verification

After installation, verify everything works:

```bash
# Run self-test
cip selftest

# Check index status
cip index-status

# Test basic search
cip search "import"
```

## Troubleshooting

### Python Path Issues

If you get "command not found" errors, ensure the `bin` directory is in your PATH:

```bash
export PATH="$PATH:/path/to/code-intelligence-platform/bin"
```

### Permission Issues

On some systems, you may need to make the scripts executable:

```bash
chmod +x bin/cip
```

### Dependency Conflicts

If you encounter dependency conflicts, consider using a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```