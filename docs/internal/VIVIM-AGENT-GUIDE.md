# CIP Guide for Vivim-Final Agents

## Overview

This guide explains how to use CIP (Code Intelligence Protocol) effectively when working on **vivim-final**, a local-first AI conversation platform built with Bun + Prisma + TypeScript + Tauri.

**Key Principle**: CIP complements Vivim's existing tools rather than replacing them. Vivim's `devops/code-index.ts` handles fast lexical/semantic search, while CIP provides audit, schema, impact, and Git-history analysis.

## Vivim Architecture Context

### Tech Stack
- **Runtime**: Bun
- **Language**: TypeScript (strict mode, ESNext target)
- **ORM**: Prisma v6.5
- **Desktop**: Tauri (Rust + Next.js frontend)
- **Linter/Formatter**: Biome
- **Testing**: Bun test runner
- **Build**: tsup (ESM + DTS)

### Engine Architecture (13 Layers)
- **L0-L1**: Provider Knowledge Graph (ProviderRegistrar, ProviderHealthKernel)
- **L2-L3**: Capability System (CapabilityResolutionEngine, CapabilityEngine)
- **L4**: Session & State (ConversationManager, StreamBlockStore)
- **Chrome Layer**: ChromeGovernor (CDP proxy, lifecycle, trace, health)
- **Cross-cutting**: CapabilityEventBus, ConfigManager, StreamParserEngine
- **Lifecycle**: RegistrationAuditor, VersionManager, TelemetryAggregator

### Key Architectural Invariants
- **B1 (Governor Canon)**: No direct Chrome/CDP transport imports from engines - ChromeGovernor is the sole owner
- **B2 (Store Contract Isolation)**: Storage accessed through contracts, not direct Prisma calls
- **B3 (Provider Configuration)**: Provider manifests in `seeds/providers/manifests.ts`, not hardcoded
- **B4 (Relational-First Schema)**: Prisma schema follows relational patterns

## CIP + Vivim Integration

### What CIP Does vs Vivim Tools

| Capability | Vivim Tool | CIP Tool | Integration |
|------------|------------|----------|-------------|
| Fast lexical/semantic search | `code-index.ts` | External search | CIP layers annotations on top |
| Architectural invariants | `devops/invariants.ts` | Custom rules | Optional reporting integration |
| Code audit | `devops/audit-code/` | `cip audit` | Different scopes, complementary |
| Schema analysis | None | Prisma pack | CIP exclusive |
| Impact analysis | None | `cip impact` | CIP exclusive |
| Git co-change | None | `cip git` | CIP exclusive |
| Tauri security | None | Tauri pack | CIP exclusive |
| Capability routing | CapabilityResolutionEngine | `route_for_agent()` | Compatible output format |

### Vivim-Specific CIP Configuration

CIP is configured for Vivim via `.cip/config.toml`:

```toml
profile = "vivim"

[external_search]
defer_to = "bun"
args = ["run", "devops", "code-index", "search", "{query}"]

[retrieval]
context_budget_tokens = 6000
lexical_k = 30
vector_k = 30

[stack]
prisma_store_contracts = true
tauri_enabled = true

[custom_rules]
enabled = true
rules_file = ".cip/rules.py"
```

### Vivim-Specific Excludes

CIP automatically excludes Vivim-specific noise:
- `src/generated` - Generated code (62MB)
- `seeds/taxonomy` - Taxonomy data (7.9MB)
- `devops/opencode` - Third-party code
- `context-pack-md`, `context-pack.zip` - Context packs
- `prisma/migrations.bak` - Backup migrations
- Test artifacts and build outputs

## Agent Workflow for Vivim

### 1. Session Start

At the beginning of a Vivim work session:

```bash
cd C:\0-BlackBoxProject-0\vivim-final
cip session start
```

This provides:
- Architecture map of 13 engines
- Currently broken tests
- Recently co-changed files (hotspots)
- High-severity open audit findings
- Context budget (6000 tokens)

### 2. Before Making Changes

**Never grep for symbol definitions** - use CIP instead:

```bash
# WRONG
grep -r "ProviderRegistrar" src/

# CORRECT
cip symbol ProviderRegistrar
cip context symbol=provider_registrar_id
```

**Never open a file cold** - get context first:

```bash
# WRONG
Open src/engines/provider-selectors.ts and read from scratch

# CORRECT
cip context "what does ProviderRegistrar do"
cip impact target src/engines/provider-selectors.ts
```

### 3. Understanding Architecture

When exploring Vivim's architecture:

```bash
# Get architecture map
cip map

# Route your question to the right tool
cip route "how does the capability system work"

# Understand engine relationships
cip graph id=CapabilityResolutionEngine direction=both depth=2
```

### 4. Schema Work (Prisma)

When working with Prisma schema:

```bash
# Prisma model usage report
cip models

# Check for missing indexes
cip findings rule=DB-MISSING-INDEX

# Schema/index drift detection
cip findings rule=DB-MIGRATION-INDEX-DRIFT
```

CIP's Prisma pack detects:
- Direct Prisma usage (direct calls to `prisma.model.operation`)
- Store contract usage (via `src/storage/` abstractions)
- Heuristic model inference from contract method names
- Missing indexes on `where` clauses
- Migration drift (schema changes without corresponding index changes)

### 5. Provider System Work

When working on the provider system:

```bash
# Check provider manifest structure
cip context "provider manifests structure"

# Impact of changing provider manifests
cip impact target seeds/providers/manifests.ts

# Verify no hardcoded provider configuration
cip findings rule=PROVIDER-MANIFEST-DRIFT
```

**Key Vivim Provider Rules**:
- Provider manifests live in `seeds/providers/manifests.ts`
- Provider capability verification uses the interpreter
- Parsers are DB-driven (inline `logic_code`)
- 16 registered providers: chatgpt, claude, gemini, deepseek, qwen, grok, and framework aliases

### 6. Chrome/CDP Work

When working with Chrome integration:

```bash
# Check ChromeGovernor usage
cip context "ChromeGovernor responsibilities"

# Verify no direct CDP transport imports
cip findings rule=NO-DIRECT-CHROME

# Impact of Chrome-related changes
cip impact target src/engines/chrome-governor.ts
```

**Key Vivim Chrome Rule (B1 Invariant)**:
- ChromeGovernor is the sole documented CDP transport owner
- No engine code should directly import CDP transport
- This is enforced by Vivim's `devops/invariants.ts` - CIP provides optional reporting

### 7. Tauri Desktop Work

When working on Tauri/desktop:

```bash
# Tauri command detection
cip context "Tauri commands in src-tauri"

# Check for ungated commands
cip findings rule=TAURI-UNGATED-COMMAND

# Impact of Tauri changes
cip impact target src-tauri/src
```

**Tauri Stack Pack Detects**:
- `#[tauri::command]` functions
- Capability manifests in `src-tauri/capabilities/*.json`
- Ungated commands (security risk)
- Frontend-to-Rust integration boundaries

### 8. Post-Edit Verification

After making changes, run verification:

```bash
# File-scoped audit (fast)
cip audit --file src/engines/your-changed-file.ts

# Impact analysis
cip impact target src/engines/your-changed-file.ts

# Full verification gate
cip verify --blocking
```

### 9. Session End

At the end of your work session:

```bash
cip session end
```

This:
- Runs verification gate
- Archives session data for learning loop
- Updates prediction confidence based on your patterns
- Generates learning report

## Vivim-Specific Capabilities

### Custom Rules

Vivim can add custom rules via `.cip/rules.py`:

```python
# .cip/rules.py (Vivim-specific)
from lib.cipkg.stack.rules import register_custom_rule

@register_custom_rule(
    rule_id="VIVIM-PROVIDER-HARDCODED",
    severity="high",
    title="Provider configuration hardcoded in engine code",
    suggestion="Move to seeds/providers/manifests.ts"
)
def check_provider_hardcoded(path, content):
    # Check for hardcoded provider configuration
    pass
```

**Note**: Vivim's primary enforcement remains via `devops/invariants.ts`. CIP custom rules are for reporting consistency, not duplicate enforcement.

### Store Contract Resolution

CIP's Prisma pack can resolve Vivim's storage layer abstractions:

- Direct Prisma: `prisma.user.findMany()` → detected directly
- Store contract: `storage.findUsers()` → heuristic inference to `User.findMany`
- Model names inferred from method patterns (e.g., `findUsers` → `User`)

### External Search Integration

CIP can delegate raw retrieval to Vivim's `code-index.ts`:

```bash
# Triggered automatically when configured
bun run devops code-index search "your query"
```

CIP then layers its audit/impact annotations on top of code-index results.

## Common Vivim Workflows

### Adding a New Provider

1. **Understand existing structure**:
   ```bash
   cip context "provider system architecture"
   cip impact target seeds/providers/manifests.ts
   ```

2. **Check manifest requirements**:
   ```bash
   cip context "provider manifest structure"
   ```

3. **Edit manifest**:
   - Add to `seeds/providers/manifests.ts`
   - Follow existing patterns

4. **Verify no hardcoding**:
   ```bash
   cip audit --file seeds/providers/manifests.ts
   cip findings rule=PROVIDER-MANIFEST-DRIFT
   ```

5. **Test capability resolution**:
   - Use interpreter for capability verification
   - Don't invent per-provider capability slugs

### Adding a New Engine

1. **Understand architecture**:
   ```bash
   cip map
   cip graph id=ProviderRegistrar direction=out depth=2
   ```

2. **Check architectural invariants**:
   ```bash
   cip context "architectural invariants for engines"
   ```

3. **Impact analysis**:
   ```bash
   cip impact target src/engines/your-new-engine.ts
   ```

4. **Verify no CDP violations** (if Chrome-related):
   ```bash
   cip findings rule=NO-DIRECT-CHROME
   ```

5. **Post-edit verification**:
   ```bash
   cip verify --blocking
   ```

### Schema Changes (Prisma)

1. **Understand current usage**:
   ```bash
   cip models
   cip findings rule=DB-MISSING-INDEX
   ```

2. **Impact of schema change**:
   ```bash
   cip impact target prisma/schema.prisma
   ```

3. **Check for store contract usage**:
   ```bash
   cip context "storage layer abstractions"
   ```

4. **Post-change verification**:
   ```bash
   cip findings rule=DB-MIGRATION-INDEX-DRIFT
   cip verify --blocking
   ```

### Tauri Desktop Changes

1. **Understand Tauri structure**:
   ```bash
   cip context "Tauri architecture"
   ```

2. **Check command gating**:
   ```bash
   cip findings rule=TAURI-UNGATED-COMMAND
   ```

3. **Impact analysis**:
   ```bash
   cip impact target src-tauri/src
   ```

4. **Use devops/desktop toolkit**:
   ```bash
   bun run devops desktop-loop run --version <x.y.z>
   ```

## Agent Integration Features

### Auto-Invoke Hooks

CIP automatically fires on file edits:

- **Post-edit**: Runs `cip impact` + `cip audit --file` after every edit
- **Pre-edit**: Validates changes against rules before write (non-blocking warnings)

These are configured in `.cip/hooks/claude-code.json` and `.cip/hooks/opencode.json`.

### Session Management

- **Session start**: Provides compact repo context (architecture, broken tests, hotspots, findings)
- **Session end**: Runs verification, archives session, updates learning loop

### Verification Gate

```bash
cip verify --blocking
```

Checks:
- Broken tests and type errors
- Critical audit findings
- Optional typecheck and lint

### Learning Loop

CIP learns from your sessions:
- Tracks verification pass/fail rates
- Identifies risky files (high failure rate)
- Adjusts prediction confidence based on patterns
- Generates learning reports

```bash
cip learning report
```

## Troubleshooting

### CIP Not Finding Symbols

**Problem**: CIP can't find a symbol you know exists.

**Solution**:
1. Check if the file is excluded: `config.default.toml` or `.cip/config.toml`
2. Re-index: `cd C:\0-BlackBoxProject-0\index && python -m lib.cipkg.cli sync --root ../vivim-final`
3. Check Vivim-specific excludes in the profile

### Verification Failing Unexpectedly

**Problem**: `cip verify --blocking` fails but you don't know why.

**Solution**:
1. Run without blocking: `cip verify`
2. Check what's blocking: Look at `blocked_by` field
3. Run targeted audit: `cip audit --file <your-file>`
4. Check broken tests: `cip broken`

### Learning Loop Not Updating

**Problem**: Learning loop isn't improving predictions.

**Solution**:
1. Check if sessions are being archived: `.cip/data/learning/session_*.json`
2. Manually trigger update: `cip learning update`
3. Generate report: `cip learning report`
4. Check confidence file: `.cip/data/learning/confidence_adjustments.json`

## Best Practices

### DO ✅

- Use `cip session start` at the beginning of work
- Use `cip route` to find the right tool for your question
- Use `cip impact` before making changes to understand blast radius
- Use `cip verify --blocking` before declaring work complete
- Use `cip session end` to trigger learning loop
- Check Vivim's invariants via `devops/invariants.ts` for architectural rules
- Use the interpreter for provider capability verification

### DON'T ❌

- Grep for symbol definitions - use `cip symbol` instead
- Open files cold - use `cip context` first
- Hardcode provider configuration - use manifests
- Import CDP transport directly in engines - use ChromeGovernor
- Skip verification on risky changes
- Duplicate Vivim's invariant enforcement in CIP

## Vivim-Specific Quick Reference

### Key Files
- `src/engines/` - 13 engine layers
- `src-tauri/` - Tauri desktop shell
- `prisma/schema.prisma` - Database schema
- `seeds/providers/manifests.ts` - Provider manifests
- `devops/invariants.ts` - Architectural invariants
- `devops/code-index.ts` - Fast lexical/semantic search
- `devops/audit-code/` - Vivim's audit system

### Key Directories to Understand
- `src/engines/` - Engine architecture
- `src/storage/` - Storage layer abstractions
- `src-tauri/capabilities/` - Tauri capability manifests
- `seeds/providers/` - Provider system
- `devops/desktop/` - Desktop build toolkit

### Key Architectural Rules
- **B1**: ChromeGovernor owns CDP transport - no direct imports
- **B2**: Storage accessed through contracts
- **B3**: Provider configuration in manifests, not hardcoded
- **B4**: Relational-first schema patterns

## Summary

CIP enhances Vivim development by providing:
- **Schema intelligence**: Prisma model usage, missing indexes, migration drift
- **Impact analysis**: Blast radius before making changes
- **Git intelligence**: Co-change analysis, hotspots, history
- **Agent integration**: Auto-hooks, session management, verification gates
- **Learning loop**: Improves predictions based on your patterns

CIP complements Vivim's existing tools rather than competing with them. Use CIP for the capabilities Vivim doesn't have (schema, impact, git-history), and rely on Vivim's tools for what it already does well (fast search, architectural invariants, audit).