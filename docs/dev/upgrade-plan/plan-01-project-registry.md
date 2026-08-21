# PLAN-01 — Global Project Registry (`project_registry.py` + `CIP_HOME` store)

**Phase 1 of 10.** Builds SPEC-19 §1/§5/§6.1. Grounded 2026-08-17.
**Depends on:** nothing (first phase).
**After this phase:** a disk store of known projects exists, usable by web_bridge and cli.

## Goal

Create the **registry**: a single global place (outside any project) that records every code folder
CIP manages. Today nothing tracks this — `sync_global/`,`repo-settings/`,`detectors` are referenced
in docs / `base.py:131` but **absent on disk**. This module is the new source of truth for the
multi-project console.

## Truth anchors (verified)

- `repo_root(start=None)` walks up from cwd for `.cip/` and raises `SystemExit` if none (`base.py:74-82`).
- Per-folder state lives in `<root>/.cip` (`cip_dir(root)` `base.py:84`, `data_dir(root)` `:86`, `load_config(root)` `:118`).
- No global CIP home exists today; `embed.py:110` uses `~` only for a model cache — no project list.

## Atomic tasks

### Task 1.1 — `lib/cipkg/project_registry.py` (new file)
- **Edit:** create `lib/cipkg/project_registry.py`.
- **Content:** a `ProjectRegistry` class + module-level `get_registry()` singleton:
  - `home()` → `os.environ.get("CIP_HOME") or Path.home() / ".cip"`; `mkdir(parents=True, exist_ok=True)`.
  - store path: `<home>/projects.json`; shape `{"version":1, "projects":[{id, root, added_ts,
    last_onboard_ts}]}`. `id` = normalized absolute root (`os.path.normcase(os.path.abspath(root))`)
    so it is stable across sessions and case-insensitive on Windows.
  - `list()` → dict `{id: {...}}`; `register(root)` idempotent (upsert `added_ts`); `unregister(id)`;
    `get(id)`; `has(root)`.
  - **Atomic write:** write tmp file in same dir → `os.replace()` → `fsync`; guard with a
    `threading.Lock` (single-writer; NFR-4 localhost). Corrupt JSON → rename to `projects.json.bak`
    and start fresh (never crash the web server on a bad file).
- **Style:** PEP-8, type hints, Google docstrings (AGENTS.md §Code Style).
- **Verify:** `python -c "from cipkg.project_registry import get_registry; r=get_registry(); print(r.home)"` from the repo `bin` (or with `lib/` on `PYTHONPATH`) prints a dir; `register/unregister/list` round-trip; corrupt-file path hand-tested.
- **Fail-state:** if `home()` dir unwritable → ValueError with message, not silent pass.

### Task 1.2 — CLI smoke adapter (optional this phase)
- **Edit:** `cli.py` — add hidden `cip projects ls`? **Not required for the upgrade**; skip to keep
  the phase atomic. Registry is consumed by PLAN-02/03. (Recorded as future nicety.)
- **Verify:** n/a.

## Acceptance (this phase ends green)

- [ ] `get_registry().home` resolves (env override respected); `projects.json` created on first write.
- [ ] register same root twice → one entry (idempotent); unregister removes only that entry.
- [ ] Windows case-normalization: `C:\A\B` and `c:\a\b` map to one id.
- [ ] Simulated corrupt `projects.json` → registry recovers (`.bak` kept), no exception.
- [ ] Full `pip install -r requirements.txt && cip selftest` still green (new module import-safe).

**Next:** PLAN-02 (request-scoped root sweep in web_bridge) consumes `registry.get(id)` to resolve roots.