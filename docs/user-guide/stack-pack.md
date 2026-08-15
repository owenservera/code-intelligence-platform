# CIP v1.1 — STACK PACK (TypeScript / Next.js / Prisma / SQLite)

A dev-cycle intelligence layer: it audits the codebase like a staff engineer,
finds hidden features, predicts blast radius, and gates merges.

## New capabilities

| Capability | Command / Tool | What it answers |
|---|---|---|
| Auto-issue detection | `cip audit` / `audit` | 24 semantic rules → findings store |
| Refactor triage | `cip refactors` / `refactors` | quick wins ranked by severity ÷ effort |
| Findings query | `cip findings --severity high` / `findings` | slice by rule/severity/path |
| Blast radius | `cip impact <file\|symbol>` / `impact` | dependents, routes, tests, risk level |
| PR risk | `cip impact --ref origin/main` | union impact of the whole diff |
| Route inventory | `cip routes` / `routes` | every API/page route + called-or-orphan |
| DB model intel | `cip models` / `models` | Prisma usage per model, orphans |
| Quality gate | `cip gate` | exit 1 on critical findings / broken signals |
| Reports | `cip audit --md REPORT.md` | human/PR-ready markdown |
| Lint unification | `cip ingest --kind eslint --file r.json` | eslint → same findings stream |

## Rule catalog

| ID | Sev | Detects |
|---|---|---|
| SEC-HARDCODED-SECRET | critical | live keys, conn strings w/ password, private keys |
| SEC-SQL-RAW | high | `$queryRawUnsafe` / `$executeRawUnsafe` |
| ENV-UNDEFINED | high | `process.env.X` used but in no `.env*` |
| NEXT-CLIENT-LEAK | high | `"use client"` file importing prisma/fs/server modules |
| DB-N1 | high | awaited prisma query inside loop/map/forEach |
| DB-NO-AWAIT | high | prisma call with no await/return/assignment |
| DB-DESTRUCTIVE-MIGRATION | high | DROP TABLE / DROP COLUMN in migrations |
| DB-MISSING-INDEX | medium | fields used in `where:` with no @id/@unique/@@index (SQLite full scan) |
| DB-SCHEMA-DRIFT | medium | schema.prisma newer than last migration |
| HIDDEN-ROUTE | medium | API route never referenced anywhere |
| HIDDEN-MODEL | medium | Prisma model with zero code usage |
| NEXT-ROUTE-NO-ERROR | medium | API route handler without try/catch |
| NEXT-ACTION-NO-VALIDATE | medium | `"use server"` fn with no schema validation |
| QA-CIRCULAR | medium | circular import chains |
| QA-GOD-MODULE | medium | huge high-fan-in files |
| QA-UNTESTED-HOT | medium | heavily-used symbols with no tests |
| ARCH-LAYER-VIOLATION | medium | lib layer importing UI layer |
| HIDDEN-EXPORT | low | exported TS symbols never referenced (hidden features) |
| ARCH-ORPHAN-FILE | low | files nothing imports |
| ENV-UNREAD | low | `.env` vars never read |
| QA-DUP | low | identical function bodies in multiple places |
| QA-ANY / QA-TSIGNORE / QA-CONSOLE | low | hygiene thresholds exceeded |

## Dev-cycle workflows

**Morning triage (2 commands):**
```bash
cip audit && cip refactors
```

**Before opening a PR:**
```bash
cip impact --ref origin/main     # what does my diff touch, transitively?
cip gate                         # hard gate: criticals + broken signals
```

**Hidden-feature hunt:**
```bash
cip findings --rule HIDDEN-ROUTE
cip findings --rule HIDDEN-EXPORT
cip models                        # orphan models = buried backend features
```

**DB health (SQLite-specific):**
```bash
cip models                        # usage per model
cip findings --rule DB-MISSING-INDEX
```

**CI (GitHub Actions):**
```yaml
- run: |
    ./install.sh .
    .cip/bin/cip upgrade
    npx vitest run --reporter=json > vt.json || true
    .cip/bin/cip ingest --kind vitest --file vt.json
    .cip/bin/cip gate
```

Findings are **idempotent** (stable IDs) and track status: `open → fixed` happens
automatically when the condition disappears. `dismiss` by deleting the rule from
config: `[audit] ignore_rules = ["QA-CONSOLE"]`.
