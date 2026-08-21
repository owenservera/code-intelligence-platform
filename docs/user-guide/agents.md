# AGENTS.md — Code Intelligence Bootstrap (CIP v1.2 + Stack Pack)

This repository runs **CIP**: a continuously updated model of the codebase —
structure, history, tests, runtime health, and a semantic audit layer for the
TS/Next.js/Prisma/SQLite stack. Do NOT read the whole repo. Interrogate the index.

## Workflow (before any change)
1. `cip search "<intent>"`  → candidates + detected intent
2. `cip symbol <Name>`      → definition + relationship counts
3. `cip impact <file>`      → blast radius BEFORE editing (dependents, routes, tests, risk)
4. `cip context "<intent>"` → budgeted pack: code + summary + relations + tests + failures
5. Read exact source only where the index points.
- Identifier search is camelCase-aware: `cip search Transport` matches MCPTransportManager.
- Results carry a `tier` (code|doc|config) — docs answer "why/how", code answers "where".

## Quality & DevOps (this repo is stack-audited)
- `cip audit`      → refresh findings (secrets, N+1, missing indexes, client leaks…)
- `cip refactors`  → ranked quick wins (fix these first)
- `cip findings --severity critical` → must-fix list
- `cip broken`     → failing tests + type errors right now
- `cip gate`       → merge gate; if it fails, fix before committing
- `cip routes` / `cip models` → route inventory, Prisma usage, orphans (hidden features)
- After your change: re-run `cip audit`; findings that disappeared auto-close as `fixed`.

## Architecture-first questions
`cip map` · `cip summary [path]` · `cip hotspots` · `cip history <path>`

## Rules
- Index = authoritative for STRUCTURE. Source = authoritative for IMPLEMENTATION.
- If `"fresh": false` → `cip sync` first.
- Never delete a `HIDDEN-*` finding's target without checking `cip impact` and git history.
- Self-introspection: `cip describe <Entity>` · `cip tools --schema`.

## Tools
CLI/MCP (`cip mcp`) / HTTP (`cip serve`): search, symbol, graph, context, summary, map,
describe, broken, hotspots, history, route, git_index, index_status, audit, findings,
refactors, impact, routes, models. Every response includes `next_ops` — follow them.
