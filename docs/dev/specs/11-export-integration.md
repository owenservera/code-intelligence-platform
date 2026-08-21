# SPEC-11 — Export & Integration (FR-11)

- **Requirement source:** `05-requirements.md` §2 FR-11, §7.1(15), ISSUE-105/111
- **Grounding verified:** 2026-08-15 against `lib/cipkg/{export,verify,scip_indexer,selftest}.py`
- **Build order dependency:** SPEC-01 (download UX), SPEC-07 (verify/findings), SPEC-06 (per-file).

---

## 1. Goal & owner intent

Export intelligence (json / lsif / markdown ARCHITECTURE.md) as browser downloads; tools schema
viewer (MCP tool list); ingest test/typecheck/lint results (paste or file upload for
vitest/jest/pytest/tsc/generic) into `signals`; run verification gate. §7.1(15): export artifacts
are NOT a v1 deliverable — this spec covers live download + ingest; generated artifact files
(deployable exports) stay out of scope until the report feature lands.

## 2. Truth-grounded core surface (verified 2026-08-15)

| Need | Core call (verified) | Returns |
|---|---|---|
| Export | `export.export(root, fmt="json|lsif|markdown", out=None)` `export.py:7` | JSON dump / LSIF (JSON-lines 0.4.3) / ARCHITECTURE.md text |
| JSON dump | `_json_dump(con)` `export.py:19` | `{protocol, version, files[], symbols[], edges[], summaries[], signals[]}` |
| LSIF | `_lsif(con)` `export.py:28` | vertices/edges metaData, project, document, range, resultSet, next, item |
| Markdown | `_markdown(con, root)` `export.py:62` | `summarize.summary` + `map_` subsystems + hotspots → ARCHITECTURE.md |
| Verify gate | `verify.verify(root, typecheck=False, lint=False, audit_check=True)` `verify.py:9` | combined check result |
| Typecheck | `_run_typecheck(root)` `verify.py:80` | subprocess runner |
| Lint | `_run_lint(root)` `verify.py:102` | subprocess runner |
| Gate | `verification_gate(root, blocking=True)` `verify.py:123` | pass/fail + why |
| Ingest signals | `signals` table (kind, path, symbol_id, name, payload, ts) `store.py:51` | test/typecheck/lint failures |
| SCIP | `scip_indexer.SCIPIndexer` `scip_indexer.py:19` + `handle_scip_command` `scip_indexer.py:131` | precise symbol index (optional, if scip binary present) |
| Self-test | `selftest.py` | `cip selftest` smoke suite |

**Signals schema (`store.py:51-55`):** `id TEXT PRIMARY KEY, kind TEXT, path TEXT, symbol_id TEXT,
name TEXT, payload TEXT, ts REAL`. F3 (SPEC-09) reads this over 14d.

## 3. UI/UX contract

- **Export view** (from command center):
  - **Download cards:** JSON (full dump), LSIF (tool interop), Markdown (ARCHITECTURE.md
    preview). Each: format description, size, "Preview" (modal, truncated), "Download"
    (`/api/export?fmt=` → attachment). Progress for large repos (stream).
  - **Ingest panel:** choose harness (vitest / jest / pytest / tsc / generic) + paste results or
    upload file → parse → write `signals` rows → show count + per-path failures (SPEC-06
    deep-link). Generic = line-based `path:line kind message`.
  - **Verification gate:** run `verify(typecheck/lint/audit)` as SPEC-02 job → gate result
    (pass/fail + why), findings summary, recommendations; failures link to file/finding.
  - **Tools schema viewer:** the MCP tool table (SPEC-02 dispatch model: `call_tool` list of
    tools + params) rendered as a schema browser — tool name, description, params, return type.
    This is the FR-11 "tools schema viewer" — surface the real bridge tool definitions.
- **States:** empty signals → "no ingested results yet"; typecheck/lint not configured → banner
  with config (SPEC-10) hint; SCIP absent → "precise indexing unavailable (scip not on PATH)".

## 4. API / WS contract

REST:
- `GET /api/export?fmt=json|lsif|markdown` → file download (Content-Disposition attachment;
  streamed). Optional `?out=` ignored for download (browser handles naming).
- `GET /api/export/preview?fmt=` → first N lines for modal.
- `POST /api/export/markdown` → write ARCHITECTURE.md into repo (opt-in, confirm) via
  `export(fmt="markdown", out=...)`.
- `POST /api/verify` `{typecheck?, lint?, audit?}` → `{job_id}` (SPEC-02; result = gate + findings).
- `POST /api/signals/ingest` `{harness, text}` or `multipart file` → parse → `{inserted,
  failures:[{path,line,kind,message}]}`.
- `GET /api/signals?kind=&days=` → signals query (SPEC-09 F3 reuse).
- `GET /api/tools` → bridge tool schema list (SPEC-02 command_table-derived).

WS (`/ws`, SPEC-14): `verify.done` (gate result), `signals.ingested` (count + per-path),
`vis.refresh {groups:[c4, f3]}` after ingest.

## 5. Data contract

- Reads all index tables for export; writes `signals` on ingest.
- No new tables. Signal rows get `ts=now`, stable id (kind:path:line hash).
- Download streaming: LSIF/markdown can be large — stream from core into HTTP response
  (chunked), not buffered whole in memory (SPEC-15).

## 6. Backend additions (lib/cipkg in scope)

1. **`web_bridge.export_stream(fmt)`** — generator over `export.export` output (or call core with
  an `out` to a temp file then stream; prefer generator to avoid disk).
2. **`web_bridge.parse_results(harness, text)`** — per-harness parser (regex/line-based) →
  normalized `{path,line,kind,message}`; upsert into `signals`; return summary. (Core has no
  parser — this is a bridge addition; keep harness parsers in one module.)
3. **`web_bridge.tools_schema()`** — derives the tools schema viewer payload from the
  SPEC-02 dispatch command_table (name/description/params/return).
4. **Verify-as-job adapter** — wrap `verify.verify` in SPEC-02 job (typecheck/lint subprocesses
  are slow — never in-request).
5. **Signal ingest hook** → snapshot writer (SPEC-04) so F3 trends include ingest events.

## 7. Core issues / risks (flagged, grounded)

- **CORE-43 — `export.export` writes via `print(text)` when `out` is None and returns only
  `{bytes}`** `export.py:16-17` — the bridge must capture output (redirect stdout or pass a
  temp `out`), not rely on return value, for streamed downloads. *(New issue.)*
- **CORE-44 — `_lsif`/`_json_dump` load all rows into memory** `export.py:19-60` — big repos →
  multi-MB strings; streaming only helps at response level, memory is still O(rows).
  → For v1, cap export size with a warning, or chunk LSIF per table. *(New issue.)*
- **CORE-45 — `verify._run_typecheck/_run_lint` use subprocess with whatever is on PATH**
  `verify.py:80,102` — harness detection is ad-hoc; a missing runner silently degrades.
  → Verify job must report "runner not found" explicitly, not fail silently. *(New issue.)*
- **CORE-46 — `signals` ingestion has no idempotency/dedupe on repeated ingests; same
  paste twice duplicates rows** `store.py:51` PK is caller-supplied id. → Bridge parser must
  generate stable ids (hash kind:path:line:message) so re-ingest upserts. *(New issue.)*
- **Watch: SCIP indexer (`scip_indexer.py`) requires the `scip` binary** — optional; expose as
  "precise indexing available/not" state, never block export/ingest.
- **Watch: LSIF export uses `languageId` from `files.language` which may be NULL
  (`export.py:41`) → falls back to `plaintext`; acceptable but note in UI tooltip.

## 8. Acceptance checks (from §6 / §7.5)

- [ ] JSON/LSIF/Markdown download via browser attachment; preview modal works.
- [ ] ARCHITECTURE.md write-back (opt-in) writes correct file (matches `cip export` output).
- [ ] Ingest (paste + upload) for all harnesses inserts signals; re-ingest upserts (no dupes).
- [ ] Verify gate runs as a job; pass/fail + why; runner-not-found reported.
- [ ] Tools schema viewer renders the real bridge tool definitions.
- [ ] Signals visible in F3 (SPEC-09) and SPEC-06 per-file sections.
