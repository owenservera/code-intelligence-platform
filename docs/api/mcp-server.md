# MCP Server API

CIP provides a Model Context Protocol (MCP) server for seamless integration with AI agents and development tools.

## Starting the MCP Server

```bash
cip mcp
```

The MCP server communicates via stdio (standard input/output) and follows the MCP protocol specification.

## Available Tools

### search

Search code by semantic intent.

**Parameters:**
- `query` (string): The search query
- `k` (number, optional): Number of results to return (default: 10)
- `tier` (string, optional): Filter by tier (code|doc|config)

**Returns:**
- Array of search results with file paths, line numbers, and relevance scores

**Example:**
```json
{
  "name": "search",
  "arguments": {
    "query": "user authentication flow",
    "k": 5
  }
}
```

### symbol

Find symbol definitions and relationships.

**Parameters:**
- `name` (string): Symbol name to search for
- `include_relationships` (boolean, optional): Include relationship counts

**Returns:**
- Symbol definition with location, signature, and relationship information

**Example:**
```json
{
  "name": "symbol",
  "arguments": {
    "name": "UserProfile",
    "include_relationships": true
  }
}
```

### impact

Analyze the blast radius of changes.

**Parameters:**
- `target` (string): File path or symbol name
- `ref` (string, optional): Git reference for diff analysis

**Returns:**
- Impact analysis including dependents, routes, tests, and risk level

**Example:**
```json
{
  "name": "impact",
  "arguments": {
    "target": "lib/routes/auth.ts"
  }
}
```

### context

Get a contextual code pack with related code, tests, and documentation.

**Parameters:**
- `query` (string): Intent description
- `budget` (number, optional): Context budget in tokens (default: 6000)

**Returns:**
- Structured context pack with code snippets, tests, and related files

**Example:**
```json
{
  "name": "context",
  "arguments": {
    "query": "how to handle database errors",
    "budget": 4000
  }
}
```

### summary

Generate structural summaries.

**Parameters:**
- `path` (string, optional): Path to summarize (default: repository root)

**Returns:**
- Structural summary with key components and relationships

**Example:**
```json
{
  "name": "summary",
  "arguments": {
    "path": "lib/routes"
  }
}
```

### map

Display hierarchical subsystem map with hotspots.

**Parameters:**
- `path` (string, optional): Path to map (default: repository root)

**Returns:**
- Hierarchical map with hotspot indicators

**Example:**
```json
{
  "name": "map",
  "arguments": {}
}
```

### describe

Ontology self-introspection.

**Parameters:**
- `entity` (string, optional): Entity to describe (default: all)

**Returns:**
- Ontology description with entity definitions and relationships

**Example:**
```json
{
  "name": "describe",
  "arguments": {
    "entity": "File"
  }
}
```

### broken

Show failing tests and type errors.

**Parameters:**
- `window_days` (number, optional): Time window in days (default: 14)

**Returns:**
- List of failing tests and type errors with locations

**Example:**
```json
{
  "name": "broken",
  "arguments": {
    "window_days": 7
  }
}
```

### hotspots

Show recently changed files ranked by impact.

**Parameters:**
- `limit` (number, optional): Number of hotspots to return (default: 20)

**Returns:**
- Ranked list of recently changed files with impact scores

**Example:**
```json
{
  "name": "hotspots",
  "arguments": {
    "limit": 10
  }
}
```

### history

Show git history for a file or symbol.

**Parameters:**
- `path` (string): File path to analyze
- `limit` (number, optional): Number of commits to show (default: 10)

**Returns:**
- Git history with commit metadata and change statistics

**Example:**
```json
{
  "name": "history",
  "arguments": {
    "path": "lib/routes/auth.ts",
    "limit": 5
  }
}
```

### route

Intent analysis and routing.

**Parameters:**
- `query` (string): Intent description

**Returns:**
- Routed tool suggestion with confidence score

**Example:**
```json
{
  "name": "route",
  "arguments": {
    "query": "find where user authentication is implemented"
  }
}
```

### git_index

Index git history for co-change analysis.

**Parameters:**
- `depth` (number, optional): Commit depth (default: 500)

**Returns:**
- Indexing status and statistics

**Example:**
```json
{
  "name": "git_index",
  "arguments": {
    "depth": 1000
  }
}
```

### index_status

Check index freshness and status.

**Parameters:** None

**Returns:**
- Index status including freshness, file count, and last update time

**Example:**
```json
{
  "name": "index_status",
  "arguments": {}
}
```

### audit

Run quality audit and generate findings.

**Parameters:**
- `severity` (string, optional): Minimum severity level (critical|high|medium|low)
- `rule` (string, optional): Specific rule to check

**Returns:**
- Audit findings with severity, locations, and descriptions

**Example:**
```json
{
  "name": "audit",
  "arguments": {
    "severity": "high"
  }
}
```

### findings

Query and filter audit findings.

**Parameters:**
- `severity` (string, optional): Filter by severity
- `rule` (string, optional): Filter by rule ID
- `path` (string, optional): Filter by file path

**Returns:**
- Filtered list of findings

**Example:**
```json
{
  "name": "findings",
  "arguments": {
    "rule": "DB-N1"
  }
}
```

### refactors

Get ranked refactoring suggestions.

**Parameters:** None

**Returns:**
- Ranked refactoring suggestions with effort and severity estimates

**Example:**
```json
{
  "name": "refactors",
  "arguments": {}
}
```

### impact

Blast radius analysis for files and symbols.

**Parameters:**
- `target` (string): File path or symbol name
- `ref` (string, optional): Git reference for diff analysis

**Returns:**
- Impact analysis with dependents, risk level, and affected areas

**Example:**
```json
{
  "name": "impact",
  "arguments": {
    "target": "lib/database.ts"
  }
}
```

### routes

Route inventory for Next.js applications.

**Parameters:** None

**Returns:**
- Complete route inventory with orphan detection

**Example:**
```json
{
  "name": "routes",
  "arguments": {}
}
```

### models

Prisma model intelligence.

**Parameters:** None

**Returns:**
- Model usage statistics and orphan detection

**Example:**
```json
{
  "name": "models",
  "arguments": {}
}
```

### rebuild

Force complete reindex.

**Parameters:** None

**Returns:**
- Reindexing status and statistics

**Example:**
```json
{
  "name": "rebuild",
  "arguments": {}
}
```

### verify

Verify index integrity.

**Parameters:** None

**Returns:**
- Verification results with any issues found

**Example:**
```json
{
  "name": "verify",
  "arguments": {}
}
```

### vacuum

Optimize and clean up index database.

**Parameters:** None

**Returns:**
- Database optimization statistics

**Example:**
```json
{
  "name": "vacuum",
  "arguments": {}
}
```

## Protocol Details

### Message Format

The MCP server uses JSON-RPC 2.0 protocol for communication. All messages follow this format:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 1,
  "params": {
    "name": "search",
    "arguments": {
      "query": "example"
    }
  }
}
```

### Error Handling

Errors follow the JSON-RPC error format:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": {
      "details": "The requested tool does not exist"
    }
  },
  "id": 1
}
```

### Streaming Support

For long-running operations, the server supports streaming responses via Server-Sent Events (SSE). Enable streaming by:

```json
{
  "name": "search",
  "arguments": {
    "query": "large repository search",
    "stream": true
  }
}
```

## Configuration

The MCP server respects the same configuration as the CLI:

- Reads from `.cip/config.toml`
- Respects environment variables
- Uses default configuration from `config.default.toml`

## Integration Examples

### Claude Desktop Integration

Add to Claude Desktop configuration:

```json
{
  "mcpServers": {
    "cip": {
      "command": "cip",
      "args": ["mcp"]
    }
  }
}
```

### Custom Agent Integration

```python
import subprocess
import json

def call_cip_tool(tool_name, arguments):
    """Call CIP MCP tool programmatically."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 1,
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    process = subprocess.Popen(
        ["cip", "mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(json.dumps(request))
    response = json.loads(stdout)
    
    return response.get("result", response.get("error"))
```

## Performance Considerations

- First search may be slower due to daemon warmup
- Index is cached for subsequent operations
- Large context requests may take longer to process
- Consider using `k` parameter to limit result size

## Troubleshooting

### Server Not Responding

Check if CIP is properly installed:

```bash
cip selftest
```

### Permission Errors

Ensure the repository is accessible and configuration files exist:

```bash
ls -la .cip/
```

### Index Not Found

Initialize the index:

```bash
cip sync
```