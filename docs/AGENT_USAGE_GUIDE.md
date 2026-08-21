# CIP Agent Usage Guide

This guide explains how AI agents can effectively use the CIP Code Intelligence Platform.

## Overview

CIP provides AI agents with deep code understanding capabilities through:
- Semantic code search
- Impact analysis
- Quality auditing
- Agent memory systems
- Context-aware suggestions

## Connection Methods

### Method 1: MCP Server (Recommended)

Start the MCP server:
```bash
cip mcp-server --port 8080
```

Configure your agent:
```json
{
  "mcpServers": {
    "cip": {
      "command": "cip",
      "args": ["mcp-server"],
      "env": {
        "CIP_ROOT": "/path/to/repo"
      }
    }
  }
}
```

### Method 2: CLI Commands

Agents can execute CLI commands:
```bash
cip search "authentication middleware"
cip impact --symbol "auth_function_id"
cip suggest-context --file "src/auth.py"
```

### Method 3: Python API

```python
from cipkg import retrieve, analysis, impact

# Search
results = retrieve.hybrid_search(root, "query")

# Analyze
health = analysis.repo_health_report(root)

# Impact
analyzer = impact.ImpactAnalyzer(con)
result = analyzer.analyze_impact(symbol_id)
```

## Common Agent Workflows

### Workflow 1: Understanding a New Codebase

```python
# Step 1: Get repository overview
health = cip_analyze()
print(f"Health Score: {health['score']}")
print(f"Issues: {health['issues']}")

# Step 2: Find key entry points
results = cip_search("main entry point", limit=5)
for result in results:
    print(f"{result['path']}:{result['start_line']}")

# Step 3: Get repository map
repo_map = cip_repo_map(max_tokens=2048)
print(repo_map)

# Step 4: Identify knowledge gaps
gaps = cip_gap_fill()
for gap in gaps:
    print(f"{gap['type']}: {gap['path']}")
```

### Workflow 2: Making a Safe Code Change

```python
# Step 1: Find the target code
results = cip_search("function to modify")
target = results[0]

# Step 2: Analyze impact
impact = cip_impact(symbol_id=target['symbol_id'])
print(f"Impact Level: {impact['impact_level']}")
print(f"Affected Files: {len(impact['affected_files'])}")

# Step 3: Get editing context
context = cip_suggest_context(file=target['path'])
print(f"Dependencies: {context['dependencies']}")
print(f"Tests: {context['test_files']}")

# Step 4: Make changes with full context
# ... agent makes changes ...

# Step 5: Verify changes
cip_sync()
audit = cip_audit(refresh=True)
print(f"New Issues: {audit['findings']}")
```

### Workflow 3: Debugging an Issue

```python
# Step 1: Search for error-related code
results = cip_search("error message or stack trace")

# Step 2: Check past experiences
memories = cip_memory_recall("similar error")
for memory in memories:
    print(f"Past solution: {memory['content']}")

# Step 3: Find all usages
refs = cip_refs(symbol_id="problematic_function")

# Step 4: Understand dependencies
impact = cip_impact(symbol_id="problematic_function")

# Step 5: Apply fix with confidence
```

### Workflow 4: Code Review

```python
# Step 1: Get file context
context = cip_suggest_context(file="src/module.py")

# Step 2: Check for gaps
gaps = [g for g in cip_gap_fill() if g['path'] == "src/module.py"]

# Step 3: Analyze quality
audit = cip_audit()
file_findings = [f for f in audit['findings'] if f['path'] == "src/module.py"]

# Step 4: Generate review
review = {
    'context': context,
    'gaps': gaps,
    'quality_issues': file_findings,
    'recommendations': generate_recommendations(gaps, file_findings)
}
```

## Using Agent Memory

### Storing Memories

```python
# Store a fact
cip_memory_store(
    key="user_preference:code_style",
    value="prefers functional programming",
    source="interaction"
)

# Store an episode
cip_memory_log_episode(
    episode_type="debug",
    context={
        "error": "NullPointerException",
        "file": "src/main.java",
        "resolution": "Added null check"
    },
    outcome="success"
)
```

### Recalling Memories

```python
# Recall relevant experiences
memories = cip_memory_recall("NullPointerException")
for memory in memories:
    if memory['type'] == 'episode':
        print(f"Past debug: {memory['content']['resolution']}")
    elif memory['type'] == 'memory':
        print(f"Stored fact: {memory['content']}")
```

## Performance Tips

### For Large Repositories

1. **Use incremental indexing**:
   ```bash
   cip index --incremental
   ```

2. **Enable daemon for warm cache**:
   ```bash
   cip daemon start
   ```

3. **Use batch operations**:
   ```python
   # Batch search
   results = cip_batch_search(["query1", "query2", "query3"])
   ```

### For Real-time Updates

1. **Enable file watcher**:
   ```toml
   [daemon]
   enable_watcher = true
   ```

2. **Use webhooks for CI/CD**:
   ```bash
   # Trigger re-index on git push
   git hook add post-commit "cip sync"
   ```

## Security Considerations

### For Agents

1. **Never expose sensitive data**:
   - Don't log API keys
   - Don't store credentials in memory
   - Sanitize file paths

2. **Validate inputs**:
   - Check file paths are within repository
   - Validate symbol IDs exist
   - Limit query lengths

3. **Rate limiting**:
   - Don't overwhelm the MCP server
   - Use batch operations when possible
   - Cache results locally

## Monitoring & Health Checks

### Check System Health

```bash
# Daemon status
cip daemon status

# Index freshness
cip analyze | grep "Index Freshness"

# Memory usage
cip memory stats
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Search returns no results | Run `cip sync` to update index |
| Daemon not responding | Run `cip daemon restart` |
| Memory full | Run `cip memory consolidate` |
| Slow performance | Enable daemon: `cip daemon start` |

## Best Practices

### For Code Understanding
1. Start with `cip_analyze` for overview
2. Use `cip_repo_map` for architecture
3. Search for specific components
4. Use `cip_suggest_context` before editing

### For Making Changes
1. Always run `cip_impact` first
2. Get context with `cip_suggest_context`
3. Check for gaps with `cip_gap_fill`
4. Verify with `cip_audit` after changes

### For Debugging
1. Search for error messages
2. Recall past experiences
3. Find all references
4. Analyze dependencies

## Support

- **Documentation**: `docs/` directory
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Examples**: `examples/` directory

---

**Remember:** CIP is designed to make agents more effective at understanding and modifying code. Use its capabilities to make informed, safe, and efficient changes.
