# RUNBOOK — CIP Web Console Build (survival discipline)

**Folder:** `docs/dev/web-console/` · **Date:** 2026-08-16
**Purpose:** canonical anti-erasure discipline for the full frontend build (AGENTS.md 120K rule,
RUNBOOK §6 pattern from the bug-fix campaign). If autocompaction fires, `BUILD.md` + `CHECKPOINT.md`
are the ONLY truth a fresh agent needs to resume. **Docs win over memory.**

---

## 1. What this build IS

A **fresh React + TypeScript + Vite frontend** (`web/`) served by a new FastAPI backend
(`lib/cipkg/web_bridge.py`) on port 8090, replacing the legacy `web_server.py` / `dashboard-web`
surfaces. Building order follows `docs/dev/specs/` (SPEC-01 → SPEC-15). Every spec renders a real
view; nothing ships as a placeholder.

## 2. Mandatory todo-list structure (anti-erasure anchor)

Every todo list for this build MUST have:
1. **FIRST item:** `[restore] Read BUILD.md + CHECKPOINT.md + RUNBOOK.md` — the very first executed
   action on any session (including right after compaction). Never skip.
2. **LAST item:** `[checkpoint] Update BUILD.md + CHECKPOINT.md`.
3. **Every work-item todo cites its spec** (e.g. `SPEC-05 search — docs/dev/specs/05-search-navigation.md`).
   No bare todos — a standalone todo is un-resumable after compaction.

## 3. Work rules

- **One unit per turn, bounded.** Each unit = one spec (or one spec slice). After each completed unit,
  the LAST todo runs: write BUILD.md status + CHECKPOINT.md narrative.
- **Re-anchor before work.** After compaction, the first action is the `[restore]` read, then continue
  at the next `pending` row in BUILD.md.
- **Verify, then mark done.** A spec is `done` only when: `npx tsc --noEmit` is clean in `web/`, the
  Vite build passes, the backend imports, and (where feasible) the endpoint is exercised with a live
  server smoke test. Never mark from memory — verify from command output.
- **Never derive progress from memory.** Progress comes ONLY from BUILD.md (status) + CHECKPOINT.md
  (narrative). If a question of state arises, read BUILD.md.
- **Track every backend gap.** New lib additions beyond `web_bridge.py` (e.g. `daemon.start_daemon`,
  `daemon.read_log`, snapshots table) are recorded in BUILD.md §Backend so nothing is lost.
- **Preserve comments.** Never strip comments from files I edit (CLAUDE.md rule).

## 4. Verification commands

```powershell
cd web; npx tsc --noEmit          # type check (must be silent)
cd web; bun run build             # vite production build
cd lib; python -c "import sys; sys.path.insert(0,'.'); from cipkg.web_bridge import app; print(len(app.routes))"
# live smoke test (Opt-in, session-local):
#   cd lib; python -m uvicorn cipkg.web_bridge:app --port 8090
```

## 5. Status vocabulary

- Spec row: `todo → in_progress → done` (+ `blocked(reason)`).
- Build phases (BUILD.md §1 milestone table): each lists start/end rows.

## 6. Cold hand-off

The end-of-session/checkpoint checkpoint must let a fresh agent with zero prior context resume the
next unit: BUILD.md last unfinished row (§, file list, exact backend calls, acceptance checks) + the
exact next command.