# AGENTS.md — Code Intelligence Bootstrap (CIP v1.0)

This repository runs **CIP**: a continuously updated, machine-readable model of
the codebase — structure, history, tests, and runtime health. Do NOT read the
whole repo. Interrogate the index.

## Workflow (before any change)
1. `cip search "<intent>"`    → candidates (lexical + semantic + graph + rerank); response includes detected intent
2. `cip symbol <Name>`        → definition + relationship counts
3. `cip context "<intent>"`   → budgeted pack: code + summary + relations + tests + known failures
4. Read exact source only at the lines the index points to.
5. After edits the index self-updates (hooks / daemon); `cip sync` to force.

## Architecture-first questions
- `cip map`                → subsystems, sizes, hotspots
- `cip summary [path]`     → repo / directory / file summary
- `cip hotspots`           → what changed most recently

## Health questions ("is this safe to refactor?")
- `cip broken`             → failing tests + type errors in the last 14 days
- `cip history <path>`     → why this code exists

## Rules
- Index = authoritative for STRUCTURE. Source files = authoritative for IMPLEMENTATION.
- If a response says `"fresh": false`, run `cip sync` first.
- Prefer `cip context` over opening files > 300 lines.
- Self-introspection: `cip describe <Entity>` or GET `/ontology.json`.

## Tools
CLI: `cip search | symbol | graph | context | summary | map | broken | hotspots | history | route | describe | doctor`
MCP: `cip mcp` · HTTP: `cip serve` (`POST /rpc`, `GET /ontology.json`)
Every response includes `next_ops` — follow them.
