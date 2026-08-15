# CIP Agent Integration Guidelines

## CIP Usage for AI Agents

When working with this repository, CIP (Code Intelligence Protocol) provides enhanced code understanding capabilities. Use these tools instead of basic grep/find operations:

### Primary Rules

**NEVER grep for symbol definitions or call sites** — use `cip symbol` and `cip impact` instead:
- ❌ `grep -r "functionName" src/`
- ✅ `cip symbol functionName`
- ✅ `cip impact target src/file.ts`

**NEVER open a file cold to understand it** — use `cip context` first:
- ❌ Open file and read from scratch
- ✅ `cip context "what does this function do?"`
- ✅ `cip context symbol=symbol_id`

### CIP Tool Priority

1. **Route questions first**: `cip route "your question"` — tells you the best CIP tools to use
2. **Symbol lookup**: `cip symbol SymbolName` — find definitions with relationship counts
3. **Impact analysis**: `cip impact target src/file.ts` — understand blast radius before editing
4. **Context packs**: `cip context "your question"` — token-budgeted context with code + tests + failures
5. **Search**: `cip search "your query"` — hybrid lexical + semantic search with reranking

### Verification Workflow

Before declaring a task complete:
1. Run `cip broken` — check for failing tests and type errors
2. Run `cip impact target src/edited-file.ts` — verify no unexpected downstream effects
3. Run `cip findings severity=critical` — check for critical audit findings

### Session Start

At the beginning of a session, run:
```bash
cip session start
```
This provides:
- Architecture map and subsystem overview
- Currently broken tests
- Recently co-changed files (hotspots)
- High-severity open audit findings

### Common Patterns

**Understanding a function:**
```bash
cip route "what does functionX do"
cip symbol functionX
cip context symbol=functionX_id
```

**Planning a change:**
```bash
cip impact target src/file.ts
cip context "what are the dependencies of file.ts"
cip findings path=src/file.ts
```

**Post-edit verification:**
```bash
cip impact target src/edited-file.ts
cip broken
cip findings severity=critical
```

### Tool Reference

- `cip search <query>` — Hybrid search with intent routing
- `cip symbol <name>` — Find symbol definitions with relationships
- `cip graph <id>` — Traverse relationships around a symbol/file
- `cip context <query>` — Token-budgeted context pack
- `cip impact <target>` — Blast radius analysis
- `cip broken` — Current failures (tests + type errors)
- `cip findings` — Query audit findings by severity/rule/path
- `cip route <query>` — Intent analysis for tool selection
- `cip session start` — Initialize session with repo context
- `cip session end` — End session with learning loop

### Why This Matters

CIP provides:
- **Structural understanding**: Symbol relationships, import graphs, dependency maps
- **Impact awareness**: Blast radius analysis before making changes
- **Quality gates**: Audit rules for security, performance, architecture
- **Git intelligence**: Co-change analysis, hotspots, history context
- **Context efficiency**: Token-budgeted packs that maximize signal per token

Using CIP prevents common agentic coding failures:
- Missing downstream dependencies
- Introducing regressions
- Breaking architectural invariants
- Inefficient context gathering
- False completion claims