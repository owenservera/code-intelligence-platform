# Command Reference

## Core Commands

### `cip sync`

Initialize or update the code index.

```bash
cip sync              # Full sync
cip sync --incremental # Incremental update
```

### `cip search <query>`

Search code by semantic intent.

```bash
cip search "user authentication"
cip search "how to handle errors"
cip search "database connection"
```

### `cip symbol <name>`

Find symbol definitions and relationships.

```bash
cip symbol UserProfile
cip symbol authenticate
cip symbol MyComponent
```

### `cip impact <file|symbol>`

Analyze the blast radius of changes.

```bash
cip impact lib/routes/auth.ts
cip impact UserProfile
cip impact --ref origin/main  # Impact of entire diff
```

### `cip context "<intent>"`

Get a contextual code pack with related code, tests, and documentation.

```bash
cip context "how to validate user input"
cip context "error handling patterns"
```

## Quality & Auditing

### `cip audit`

Run quality audit and generate findings.

```bash
cip audit                                    # Run audit
cip audit --md REPORT.md                     # Generate markdown report
cip audit --severity critical                # Show only critical findings
```

### `cip findings`

Query and filter audit findings.

```bash
cip findings --severity high                 # High severity findings
cip findings --rule DB-N1                    # Specific rule findings
cip findings --path lib/routes/              # Findings in specific path
```

### `cip refactors`

Get ranked refactoring suggestions.

```bash
cip refactors  # Quick wins ranked by severity ÷ effort
```

### `cip gate`

Quality gate for CI/CD - exits with error on critical issues.

```bash
cip gate  # Exits 1 if critical findings or broken signals exist
```

### `cip broken`

Show failing tests and type errors.

```bash
cip broken  # Failing tests + type errors (14d window)
```

## Architecture & Navigation

### `cip map`

Display hierarchical subsystem map with hotspots.

```bash
cip map              # Repository map
cip map lib/         # Directory map
```

### `cip summary [path]`

Generate structural summaries.

```bash
cip summary           # Repository summary
cip summary lib/      # Directory summary
cip summary file.py   # File summary
```

### `cip describe [Entity]`

Ontology self-introspection.

```bash
cip describe File
cip describe Symbol
cip describe tools
```

### `cip hotspots`

Show recently changed files ranked by impact.

```bash
cip hotspots  # Recent-change ranking
```

### `cip history <path>`

Show git history for a file or symbol.

```bash
cip history lib/routes/auth.ts
```

## Stack-Specific Commands

### `cip routes`

Route inventory for Next.js applications.

```bash
cip routes  # Every API/page route + called-or-orphan status
```

### `cip models`

Prisma model intelligence.

```bash
cip models  # Usage per model, orphans, schema analysis
```

## Operations

### `cip daemon`

Start the background daemon for embedding service.

```bash
cip daemon start    # Start daemon
cip daemon stop     # Stop daemon
cip daemon status   # Check status
```

### `cip serve`

Start HTTP server for API access.

```bash
cip serve --port 8787
```

### `cip mcp`

Start MCP (Model Context Protocol) server.

```bash
cip mcp  # Start MCP server for AI agent integration
```

### `cip selftest`

Run verification tests.

```bash
cip selftest  # Verify installation and core functionality
```

### `cip upgrade`

Upgrade CIP to the latest version.

```bash
cip upgrade  # Schema migration + reindex
```

## Data Management

### `cp git-index`

Index git history for co-change analysis.

```bash
cip git-index --depth 500
```

### `cip ingest`

Ingest external tool results.

```bash
# Vitest results
cip ingest --kind vitest --file results.json

# TypeScript errors
cip ingest --kind tsc --file <(npx tsc --noEmit --pretty false)

# Pytest results
cip ingest --kind pytest --file junit.xml
```

### `cip export`

Export index data in various formats.

```bash
cip export --format markdown --out ARCHITECTURE.md
cip export --format json --out index.json
cip export --format lsif --out index.lsif
```

## Configuration

### `cip config`

View or edit configuration.

```bash
cip config                    # Show current config
cip config --edit             # Open config in editor
cip config --set embed.backend=local
```

## Index Management

### `cp index-status`

Check index freshness and status.

```bash
cip index-status
```

### `cp rebuild`

Force complete reindex.

```bash
cip rebuild
```

### `cp vacuum`

Optimize and clean up index database.

```bash
cip vacuum
```