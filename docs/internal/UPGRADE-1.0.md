# CIP v1.0 — Upgrade Notes

## What changed since v0.9
| Area | v0.9 | v1.0 |
|---|---|---|
| Parsing | regex only | tree-sitter when grammars installed, regex fallback |
| Graph | calls/refs/imports/tests | + `extends`, `implements`, `modified_by`, `co_change` |
| History | ad-hoc `git log` | commit index, hotspots, co-change |
| Runtime | none | signal adapters: vitest/jest/pytest/tsc/generic → `broken` |
| Summaries | none | repo/dir/file, hash-cached, structural or LLM |
| Retrieval | FTS+vec+RRF | + feature reranker + intent router |
| Vectors | SQLite only | numpy acceleration + sqlite-vec hook |
| Interop | none | LSIF / JSON / Markdown(ARCHITECTURE.md) export |
| Ops | watch/serve | `daemon` (single-writer), `selftest`, `upgrade` |
| Schema | 3 | 4 (auto-migrates) |

## Upgrade procedure (existing v0.9 repo)
```bash
./install.sh /path/to/repo     # copies v1.0 bundle over .cip/ (config preserved)
cd /path/to/repo
cip upgrade                    # schema migration + full reindex + git index
cip selftest                   # verify
cip doctor
```

## New commands
```bash
cip summary [path]            # repo | dir | file summary
cip map                       # hierarchical subsystem map + hotspots
cip describe [Entity]         # ontology self-introspection
cip broken                    # failing tests + type errors (14d window)
cip hotspots                  # recent-change ranking
cip route "query"             # intent analysis
cip git-index --depth 500     # commit/co-change/hotspot index
cip ingest --kind vitest --file results.json
cip ingest --kind tsc --file <(npx tsc --noEmit --pretty false)
cip ingest --kind pytest --file junit.xml
cip export --format markdown --out ARCHITECTURE.md
cip daemon --port 8787        # watcher + server, single writer
```

## Optional upgrades (all zero-config-safe)
- `pip install tree-sitter tree-sitter-typescript tree-sitter-python tree-sitter-javascript tree-sitter-rust tree-sitter-go`
- `pip install sentence-transformers` (real embeddings) or set `OPENAI_API_KEY`
- `[summary] backend = "llm"` for LLM-written summaries
- `[vector] backend = "sqlite-vec"` for very large repos

## Deferred to v1.1
SCIP protobuf export, cross-encoder reranker as first-class backend, multi-repo federation, coverage-percentage edges.
