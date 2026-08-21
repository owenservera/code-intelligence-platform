# Audit — Web Console & Multi-Project Upgrade (2026-08-17)

**Audited folders:** `docs/dev/web-console/` (SPEC-01–15) and `docs/dev/upgrade-plan/` (SPEC-16/17/18/19)
**Verdict at a glance:**

| Area | Docs claim | Verified reality | Confidence |
|------|-----------|-----------------|------------|
| **web-console backend** (SPEC-01–15) | all 15 specs done | **DONE** — 92 routes, every endpoint group present | high (route list + import) |
| **web-console frontend** (SPEC-01–15) | all 15 specs done | **DONE** — all views real, `tsc` clean, 0 placeholders | high (file inspection) |
| **upgrade-plan backend** (SPEC-16/19) | P1–P3 done, P4–P10 pending | **ACCURATE** — P1–P3 done; P4–P10 absent (incl. security bug) | high (grep + import) |
| **upgrade-plan frontend** (SPEC-16/17/18/19) | P6–P10 pending | **ACCURATE** — none of it exists; `tsc` green only because no code added | high (file inspection) |

**Bottom line:** The *web-console* (the original SPEC-01–15 product) is **fully and genuinely implemented** — both backend and frontend — with only minor polish/bugs. The *upgrade-plan* (the multi-project console: global registry + `_root()` scoping + switcher + explorer/review/history features) is **only ~30% done**: the foundation (registry, `_root()` sweep, `/api/projects`) landed, but **Phases 4–10 — the entire feature surface — are NOT implemented**, including a path-traversal security hole that is live today via the existing `/api/file` endpoint.

This directly contradicts the assumption that "they should fully be implemented." The web-console is; the upgrade-plan is not.

**Progress (2026-08-17):** both **P0** items are now **FIXED and verified** — path-traversal guard added in `web_bridge.py` (`_safe_join`), and the `SearchView.tsx` no-arg `invalidateQueries()` crash removed. See `gaps-and-enhancements.md` §P0. The remaining P1/P2 backlog (upgrade-plan P4–P10, tests, lint hygiene) is open.

---

## How this audit was run
- Read the plan/build docs (acceptance criteria, claimed status).
- Verified against source of truth: `lib/cipkg/web_bridge.py` (3521 lines), `lib/cipkg/project_registry.py`, `lib/cipkg/cli.py`, `web/src/**`.
- Ran verification commands: `python -c "from cipkg.web_bridge import app; print(len(app.routes))"` → **92**; `npx tsc --noEmit` → exit 0.
- Per the 120K context rule, deep code-grepping was delegated to parallel auditors; this file synthesizes their evidence-backed reports plus first-hand checks.

## Files in this folder
- `00-AUDIT-INDEX.md` — this file (summary + consolidated gap list + next steps)
- `upgrade-plan-backend.md` — phase-by-phase backend findings (P1–P10)
- `upgrade-plan-frontend.md` — frontend findings (switcher/explorer/review/history)
- `web-console-backend.md` — SPEC-01–15 endpoint verification
- `web-console-frontend.md` — SPEC-01–15 view verification + bugs

## Consolidated "missing / should-fix" list (all areas)
See `gaps-and-enhancements.md` for the full prioritized backlog. Top items:

1. **[SECURITY] Path traversal in `file_bundle`** — `web_bridge.py:2069` builds `Path(root)/path` with no `.resolve()`/containment check. `GET /api/file?path=../../etc/passwd` reads above root. Live today. Blocks P7 T7.4. **P0.**
2. **[upgrade] P4–P10 entirely absent** — onboard POST, per-project WS, frontend switcher, `/api/tree`, explorer/review/history — none implemented.
3. **[upgrade] `cip web --project`/`--root` flags missing** — only `CIP_WEB_ROOT` env works (cli.py:723-726).
4. **[upgrade] Registry written at import time** — `web_bridge.py:56-63` calls `register()` on module import (violates "import-safe" claim; read-only import now writes to `~/.cip`).
5. **[web-console] SearchView.tsx:281** — `qc.invalidateQueries()` with no argument throws in React Query v5 (latent crash on prediction button).
6. **[both] Zero automated tests** for any new surface (registry, `/api/projects`, all SPEC endpoints, frontend).
