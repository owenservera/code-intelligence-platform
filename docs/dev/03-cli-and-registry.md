# CLI Surface, Command Registry, and Tool Bridge

**Status:** Draft — source review
**Date:** 2026-08-15
**Purpose:** Enumerate the full command/tool surface so the web console can expose
*every* capability, and define how to bridge it without subprocess shelling.

---

## 1. Three surfaces that must unify in the web console

| Surface | Implementer | Consumer |
|---|---|---|
| CLI commands | `cli.py` argparse + `dispatch_command` | humans/agents (subprocess `cip …`) |
| Tool registry | `command_registry.py` `CommandRegistry` | TUI + (new) web UI |
| RPC/MCP tools | `server.py` `TOOLS` + `call_tool` | agents via JSON-RPC / MCP stdio |

The web layer should present **one** capability model. The natural source of truth is
`command_registry.py` (metadata: command, description, category, priority, parameters)
augmented with parameter definitions from the argparse parser and result shapes from the
lib functions.

## 2. Registered commands (command_registry.py)

54 commands across 11 categories. From a live dump:

```
REPOSITORY:  init upgrade sync index rebuild vacuum
SERVICES:    daemon_start daemon_status daemon_stop serve mcp
SEARCH:      search symbol graph context suggest_context summary
QUALITY:     analyze audit findings gate refactors verify
IMPACT:      impact predict
GAPFILLER:   coverage dead circular blame score migrations env logs metrics features deps api
GIT:         git_index history hotspots broken
INTEGRATION: export ingest tools
AGENT:       hook session_start session_end session_status learning_analyze
             learning_patterns learning_report learning_update
SYSTEM:      selftest doctor embedder embed_ping
```

Categories enum: REPOSITORY, SERVICES, SEARCH, QUALITY, IMPACT, GAPFILLER, GIT,
INTEGRATION, AGENT, LEARNING, SYSTEM.

`CommandCard` fields: command, title, description, category, priority, parameters
(`CommandParameter`: name, type, description, required, default).

## 3. CLI argparse surface (cli.py) — parameters not in registry

The registry has metadata but not full parameter detail for every command. The argparse
`setup_argument_parser()` is the authority for flags. Key commands and their flags:

| Command | Flags |
|---|---|
| `index` | `--full`, `--reembed` |
| `embed` | `--batch 64` |
| `watch` | `--interval 1.0` |
| `daemon start/status/stop` | `--port 8787`, `--interval` |
| `search <query>` | `-k 10` |
| `graph <id>` | `--direction`, `--depth 1` |
| `context [query]` | `--symbol`, `--budget` |
| `summary [path]`; `describe [entity]`; `map` | — |
| `history <path>`; `route <query>` | `--agent` |
| `git-index` | `--depth` |
| `ingest` | `--kind (vitest|jest|pytest|tsc|generic|eslint)`, `--file -` |
| `export` | `--format (json|lsif|markdown)`, `--out` |
| `serve` | `--port`; `tools` | `--schema` |
| `audit` | `--file`, `--diff` |
| `findings` | `--severity`, `--rule`, `--path`, `--limit 100`, `--structured` |
| `impact <target>` | `--ref`, `--depth 2`, `--structured` |
| `dashboard` | `--port 8790`; `dashboard-web` | `--port 8090`, `--host` |
| `admission` | `--path` |
| `embedder`; `embed-ping [count]` | — |
| `blame <path> [line]` | — |
| `predict` | `--operation (required)`, `--symbol`, `--query` |
| `suggest-context <path>` | `--line` |
| `hook <post-edit|pre-edit> <args…>` | — |
| `session start/end/status` | — |
| `verify` | `--typecheck`, `--lint`, `--no-audit`, `--blocking` |
| `learning analyze/update/report/patterns` | — |
| `verify-index` | `--repair` |
| `vacuum` | `--days` |

## 4. RPC/MCP tool surface (server.py TOOLS)

20 tools: search, symbol, graph, context, summary, map, describe, broken, hotspots,
history, route, route_for_agent, git_index, index_status, audit, findings, refactors,
impact, routes, models. Each with `inputSchema` (JSON Schema) — good reference for the
new REST/WS schema style.

`call_tool` dispatches to lib functions directly (e.g. `retrieve.search`,
`stack_audit.audit`, `stack_impact.impact_diff`, `summarize.map_`). Result envelope:
`{ok, tool, result, next_ops, index_stats}`.

## 5. Important dispatch gaps (cli.py)

`dispatch_command` maps only a subset of argparse commands to handlers. Commands
**defined in argparse but missing from dispatch** include (verify against handlers dict):
- `refactors`, `routes`, `models`, `gate`, `admission`, `embedder`, `embed-ping`,
  `coverage`, `dead`, `circular`, `blame`, `score`, `migrations`, `env`, `logs`,
  `metrics`, `features`, `deps`, `api`, `watch`, `verify-index`(mapped to wrong handler),
  `daemon`(subcommands).

Some are lambdas in dispatch (`map` → `summarize.map(r)`), others fall to `unknown
command`. **The web layer must NOT depend on CLI dispatch correctness** — call lib
functions directly (the same functions server.py's `call_tool` uses).

## 6. Bridge strategy for the web console

**Do not shell out to `cip`.** Use the same direct lib calls as `server.py:call_tool`.
The new FastAPI layer should:

1. **Catalog**: serve the full `CommandRegistry` (categories, cards, parameters) from
   `get_command_registry()` + argparse-derived param metadata → drive dynamic UI forms.
2. **Execute**: POST `/api/commands/{name}` → map command name to a lib call (a
   command→callable table like `server.py`'s, extended to all 54), validate params,
   run in a worker, stream stdout/progress + result over WS.
3. **Status**: long-running ops (sync, embed, audit, consolidate, rebuild, export) get
   job IDs with live progress events; UI shows spinners + logs + result.
4. **Safe ops only**: destructive commands (rebuild, vacuum, export overwrite) require
   confirmation flag in the UI; server-side still executes (no auth in scope unless asked).

## 7. Command-to-lib-function mapping (initial table for the bridge)

| Registry cmd | Lib call |
|---|---|
| sync / index / rebuild | `indexer.sync(root, full=…)`, `maintain.rebuild(root)` |
| analyze | `analysis.repo_health_report(root)` |
| audit | `stack_audit.audit(root, refresh=True)` |
| findings | `stack_audit.findings(root, severity=…, rule=…, path=…, limit=…)` |
| refactors | `stack_audit.quick_wins(root, limit=…)` |
| gate | `stack_audit.gate(root)` |
| impact | `stack_impact.impact(root, target=…, depth=…)` / `impact_diff(root, ref=…)` |
| search/symbol/graph/context/history | `retrieve.*` |
| routes/models | `stack_nextjs.list_routes`, `stack_prisma.models_report` |
| broken/hotspots | `runtime_adapters.broken`, `gitindex.hotspots` |
| git_index | `gitindex.git_index(root, depth=…)` |
| coverage/dead/circular/score/… | `gapfill.*` |
| deps | `dependency_checker.handle_deps_command` / report |
| memory ops | `memory.temporal_graph.*`, `memory.episodic.*`, `memory.consolidation.*` |
| export | `export.py` |
| selftest / doctor | `selftest.*`, `cli.cmd_doctor` |
| daemon status | `daemon.daemon_status(root)` |
| index_status | `server.index_status(root)` / `indexer.compute_stats(con)` |
| ingest | `runtime_adapters.ingest(root, kind, file)` |
| suggest-context | `context_manager` / `retrieve.context` |
| predict / learning / session | `predict.*`, `learning_system.*`, `session.py` |

> `gapfill.*` commands are under the owner's scrutiny ("might be junk"). The bridge
> should list them but we validate value before highlighting them in the UI.
