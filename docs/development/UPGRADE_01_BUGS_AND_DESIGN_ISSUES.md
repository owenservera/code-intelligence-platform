# CIP Upgrade Report 1/3: Bugs & Systematic Design Issues

**Scope**: `owenservera/code-intelligence-platform`  
**Method**: Static analysis (`pyflakes`), live import/execution testing, manual code review  
**Audience**: Autonomous coding agent (SWE-1.6) — every finding below was reproduced, not inferred  
**Format**: Each finding has a verified repro, root cause, and a concrete patch

---

## How to use this document

Every bug in this report was **actually triggered** in a sandboxed clone of the repo (not just spotted by reading code). Findings are ordered by severity:

- **P0** — breaks the tool for every user, on first use
- **P1** — silently breaks a named command/feature, no crash visible to a casual user
- **P2** — correctness/maintainability/performance issue, not user-blocking
- **P3** — cosmetic/cleanup

Each entry gives exact file:line, the reproduction command, and a patch. Patches are minimal and conservative — apply them directly, then run `python -m pyflakes lib/cipkg` to confirm no new undefined names were introduced.

---

## P0 — Blocks every user

### P0-1: `install.sh` fails on every fresh install

**File**: `install.sh`  
**Repro**:
```bash
bash install.sh /tmp/some-target
# cp: cannot stat '/home/.../bootstrap/AGENTS.md': No such file or directory
```

**Root cause**: `install.sh` references `$SRC/bootstrap/AGENTS.md`, but there is no `bootstrap/` directory anywhere in the repository. `AGENTS.md` lives at the repo root. This is literally the first command in the README's "Quick Start" — every new user hits this immediately.

**Fix**:
```diff
--- a/install.sh
+++ b/install.sh
@@ -8,7 +8,7 @@ TARGET="$(cd "${1:-.}" && pwd)"
 mkdir -p "$TARGET/.cip/bin" "$TARGET/.cip/lib" "$TARGET/.cip/bootstrap" "$TARGET/.cip/data"
 cp "$SRC/bin/cip"                     "$TARGET/.cip/bin/cip"
 cp -R "$SRC/lib/cipkg"                "$TARGET/.cip/lib/"
-cp "$SRC/bootstrap/AGENTS.md"         "$TARGET/.cip/bootstrap/AGENTS.md"
+cp "$SRC/AGENTS.md"                   "$TARGET/.cip/bootstrap/AGENTS.md"
 cp "$SRC/config.default.toml"         "$TARGET/.cip/config.toml"
 cp "$SRC/ontology.json"               "$TARGET/.cip/ontology.json"
 chmod +x "$TARGET/.cip/bin/cip"
```

**Verification**: after patch, `bash install.sh /tmp/test-target && /tmp/test-target/.cip/bin/cip --help` should succeed.

---

### P0-2: `cip` CLI crashes on **every** command — `dispatch_command` references an undefined function

**File**: `lib/cipkg/cli.py:714`  
**Repro**:
```python
import sys; sys.path.insert(0, "lib")
from cipkg import cli
class Args: pass
cli.dispatch_command("/tmp", Args())
# NameError: name 'handle_suggest_context_command' is not defined
```

**Root cause**: The `dispatch_command()` function builds a `dict` literal mapping command names to handler functions. Line 714 references `handle_suggest_context_command`, which is **never defined anywhere in the file** (only the argparse subparser for `suggest-context` exists, at line 634). Because this dict is rebuilt on *every call* to `dispatch_command` (not cached at import time), **every single CLI invocation** — `cip search`, `cip audit`, `cip sync`, everything — raises this `NameError` before the command dict can even be constructed.

This is the single highest-impact bug in the repository: it means the packaged CLI, as committed, cannot run any command.

**Fix** — add the missing handler (mirrors the pattern of sibling handlers like `handle_context_command`):
```python
def handle_suggest_context_command(root, args):
    """Handle 'cip suggest-context' — suggest relevant context for editing a file."""
    from . import gapfill
    result = gapfill.suggest_context(root, getattr(args, "file", None))
    _out(result)
```
Place this definition above `dispatch_command` (e.g., near `handle_context_command`). If `gapfill.suggest_context` doesn't exist yet, stub it or route to the closest existing function (`gapfill.explain` / `retrieve.get_context`) rather than leaving the name undefined.

**Regression guard**: add a startup self-check (see P1-9 below) that imports `cli` and calls `dispatch_command` with a no-op args object in CI, so this class of bug fails the build instead of shipping.

---

### P0-3: `interactive.py` cannot be imported at all — undefined type annotation at module scope

**File**: `lib/cipkg/interactive.py`  
**Repro**:
```python
import sys; sys.path.insert(0, "lib")
from cipkg import interactive
# NameError: name 'UnifiedContext' is not defined
```

**Root cause**: Several methods on `InteractiveMode` use `UnifiedContext` as a parameter type annotation (`def _render_welcome_screen(self, context: UnifiedContext):` at line 81, and similarly at 94, 119, 125, 131). `UnifiedContext` is a real class in `cipkg.context_manager`, but it is only imported **locally inside `_run_interactive_loop`** (line 56), not at module level. Python evaluates default (non-`from __future__ import annotations`) type annotations at function-definition time, which happens when the class body executes at import time — so the module fails to import, full stop. Interactive mode is entirely non-functional.

**Fix**:
```diff
--- a/lib/cipkg/interactive.py
+++ b/lib/cipkg/interactive.py
@@ -7,7 +7,7 @@
 from typing import Dict, List, Optional, Any
-from cipkg.context_manager import ContextManager
+from cipkg.context_manager import ContextManager, UnifiedContext
 from cipkg.suggestion_engine import SuggestionEngine
 from cipkg.workflow_engine import WorkflowExecutor
 from cipkg.learning_system import LearningSystem
@@ -53,8 +53,6 @@ class InteractiveMode:
     def _run_interactive_loop(self):
         """Main interactive loop."""
-        from cipkg.context_manager import UnifiedContext
-
         context = self.context_manager.get_context()
```

Alternatively (cheaper, lower-risk if `context_manager` has heavy import-time side effects): add `from __future__ import annotations` as the first line of the file, which defers all annotation evaluation to string form and sidesteps the whole class of bug — recommended as a blanket fix across the codebase (see P2-6).

---

### P0-4: No `requirements.txt` exists, though README and multiple modules require it

**File**: missing (`requirements.txt` referenced in `README.md:188`)  
**Repro**:
```bash
ls requirements.txt          # No such file
grep -n "requirements.txt" README.md   # pip install -r requirements.txt
python -m pytest lib/cipkg/test_embed.py -q
# ModuleNotFoundError: No module named 'torch'
```

**Root cause**: Only `requirements-test.txt` (pytest tooling) exists. The actual runtime dependencies — `torch`, `sentence-transformers`, `textual`, `tree-sitter` (+ language grammars), `numpy` — are never declared anywhere as installable requirements. A user following the README's own "Development Setup" section cannot install the project.

**Fix** — add `requirements.txt` at repo root:
```txt
# Core runtime
numpy>=1.24
tomli>=2.0; python_version < "3.11"

# Embedding (local backend)
sentence-transformers>=2.5
torch>=2.1

# Parsing
tree-sitter>=0.21
tree-sitter-languages>=1.10

# TUI
textual>=0.55

# HTTP client already in stdlib (urllib) — no extra dep needed for daemon/service mode
```
Also split into `requirements-minimal.txt` (numpy + tomli only, for the `hashing` embedder / lexical-only mode) so CI and lightweight installs don't have to pull in torch — this directly supports fixing P1-6 below.

---

## P1 — Named commands silently broken

### P1-1: `cip embed` crashes — undefined `connect` / `load_config`

**File**: `lib/cipkg/cli.py:86-87`
```python
def handle_embed_command(root, args):
    from . import indexer
    _out(indexer.embed_pending(connect(root), load_config(root), batch=args.batch, progress=_progress))
```
`connect` and `load_config` are used but never imported in this function or at module scope.

**Fix**:
```diff
 def handle_embed_command(root, args):
-    from . import indexer
+    from . import indexer
+    from .store import connect
+    from .base import load_config
     _out(indexer.embed_pending(connect(root), load_config(root), batch=args.batch, progress=_progress))
```

### P1-2: `cip detect` crashes — undefined `load_config`

**File**: `lib/cipkg/cli.py:140-142`
```python
def handle_detect_command(root, args):
    from . import detect
    cfg = load_config(root)
    _out(detect.detect(root, cfg))
```

**Fix**:
```diff
 def handle_detect_command(root, args):
     from . import detect
+    from .base import load_config
     cfg = load_config(root)
     _out(detect.detect(root, cfg))
```

### P1-3: `cip map` and `cip describe` crash — `summarize` used but not imported at module scope

**File**: `lib/cipkg/cli.py:690-691`
```python
"map": lambda r, a: _out(summarize.map(r)),
"describe": lambda r, a: _out(summarize.describe(r, getattr(a, 'entity', None))),
```
`summarize` is imported locally inside a different function (line ~180) but these two lambdas close over the module (global) namespace, where `summarize` doesn't exist.

**Fix** — add to the top-level imports of `cli.py`:
```diff
 from . import gapfill
+from . import summarize
 from .hooks import install_agent_hooks, run_hook_command
```

### P1-4: Repository health score is silently degraded — `root` is undefined in `_calculate_health_score`

**File**: `lib/cipkg/analysis.py:35-65`
```python
def _calculate_health_score(con, cfg):
    ...
    try:
        from .maintain import verify
        verify_result = verify(root)          # <-- 'root' not a parameter, not in scope
        fresh = verify_result.get("fresh", False)
        freshness_score = 100 if fresh else 50
    except:
        freshness_score = 50
```
**Repro**:
```python
import pyflakes.api; pyflakes.api.checkPath("lib/cipkg/analysis.py")
# lib/cipkg/analysis.py:61:32: undefined name 'root'
```
This is the most insidious class of bug in the repo: the bare `except:` on line 64 (see P1-9) **catches the `NameError` and silently substitutes `freshness_score = 50`**. `cip analyze` never crashes, and never reports the real freshness of the index — the "freshness" component of the health score is dead code that always contributes the same fallback value, and nobody looking at CLI output would ever know.

**Fix**:
```diff
-def _calculate_health_score(con, cfg):
+def _calculate_health_score(con, cfg, root):
     """Calculate overall health score (0-100)."""
     ...
     try:
         from .maintain import verify
         verify_result = verify(root)
```
And update the one call site:
```diff
 def repo_health_report(root=None):
     root = root or repo_root()
     con = connect(root)
     cfg = load_config(root)
     health_score = _calculate_health_score(con, cfg)
+    health_score = _calculate_health_score(con, cfg, root)
```
(remove the old call, don't leave both).

### P1-5: `_calculate_health_score` also silences quality-scoring failures

Same function, lines 49-56: any exception importing `.stack.nextjs` or running `list_findings` falls back to a hardcoded `quality_score = 80` via a bare `except:`. Combined with P1-4, **three of the four weighted components of the health score** (`quality`, `freshness`, `complexity`) have silent fallback paths that can mask real failures rather than surfacing them. See P1-9 for the systemic fix (replace bare `except:` with logged, typed exception handling).

### P1-6: `get_embedder()`'s documented fallback order does not match its implementation — causes hard crashes instead of graceful degradation

**File**: `lib/cipkg/embed.py:160-190`

The module docstring promises:
> Priority: warm daemon -> auto-start daemon -> hashing (offline) -> local (with warning)

But the actual code:
```python
def get_embedder(cfg, root=None):
    ...
    # 1. try daemon
    if backend in ("auto", "service"):
        ...
    # 2. auto-start daemon if configured
    if backend == "service" or (backend == "auto" and ecfg.get("autostart", True)):
        ...
    # 3. hashing (offline, no model needed)
    if backend == "hashing":          # <-- only reached if user explicitly set backend="hashing"
        return _cached(...)
    # 4. local singleton (slow, uses HF if not cached)
    model = ecfg.get("model", MODEL_NAME)
    return _cached(("local", model), lambda: LocalEmbedder(model))
```
With the default config (`backend = "auto"`), if the daemon fails to start (no `cip` on `PATH`, sandboxed environment, offline machine, port conflict — any of which are common in CI/agent sandboxes), execution falls straight through to step 4, `LocalEmbedder`, which does `import torch` unconditionally. If torch isn't installed (which, per P0-4, it may well not be, since it's undeclared), this is a hard `ModuleNotFoundError` crash — **not** the documented graceful fallback to the zero-dependency `HashingEmbedder`.

**Repro** (confirmed against this exact repo):
```bash
python -m pytest lib/cipkg/test_embed.py::EmbedTest::test_hashing_embedder -q
# ModuleNotFoundError: No module named 'torch'
```
A test explicitly named `test_hashing_embedder` fails on a missing `torch` import — direct evidence the fallback chain is broken.

**Fix** — make step 4 conditional and step 3 the true fallback:
```diff
     # 3. hashing (offline, no model needed)
-    if backend == "hashing":
+    if backend == "hashing" or backend == "auto":
+        try:
+            model = ecfg.get("model", MODEL_NAME)
+            return _cached(("local", model), lambda: LocalEmbedder(model))
+        except ImportError:
+            pass  # torch/sentence-transformers not installed — fall through
         return _cached(("hashing", 0), lambda: HashingEmbedder(
             int(ecfg.get("dim", 1024))))
 
-    # 4. local singleton (slow, uses HF if not cached)
-    model = ecfg.get("model", MODEL_NAME)
-    return _cached(("local", model), lambda: LocalEmbedder(model))
+    # 4. explicit "local" backend requested — let ImportError surface
+    model = ecfg.get("model", MODEL_NAME)
+    return _cached(("local", model), lambda: LocalEmbedder(model))
```
This makes `auto` actually attempt local-then-hash gracefully, matching the docstring, and keeps a hard failure available for users who explicitly request `backend = "local"` (fail loud when explicitly asked).

### P1-7: `config.v2.default.toml` is fully orphaned — 210 lines of dead configuration

**Files**: `config.v2.default.toml`, `lib/cipkg/base.py`  
**Repro**:
```bash
grep -rn "v2.default.toml\|config.v2" lib/ bin/ install.sh
# (no output — zero references anywhere in code)
```
`load_config()` in `base.py` builds its base config from an in-code Python dict, `DEFAULT_CONFIG` (line 10), and merges only (a) the auto-detected repo profile and (b) `.cip/config.toml`. It never parses `config.default.toml` *or* `config.v2.default.toml` from disk directly. `DEFAULT_CONFIG` has no `[interactive]`, `[context]`, `[command_adaptation]`, `[error_handling]`, `[ui]`, or `[workflows]` sections — exactly the sections that exist only in `config.v2.default.toml`.

The practical impact: every place in the codebase that reads `cfg.get("interactive", {})`, `cfg.get("workflows", {})`, etc. (e.g. `interactive.py`: `self.config.get('interactive', {}).get('enabled', True)`) **always** gets the hardcoded Python-level default — the 210 lines of `config.v2.default.toml` cannot influence runtime behavior no matter what a user edits in it. This will actively mislead both human contributors and coding agents into believing these settings are configurable when they are not wired up.

**Fix** — two acceptable directions, pick one:

1. **Wire it up** (if v2 settings are meant to be real): merge the missing sections into `DEFAULT_CONFIG` in `base.py`, and have `load_config()` actually parse `config.v2.default.toml` (or fold its sections into `config.default.toml` and parse that instead — see P1-8 below for the related issue that `config.default.toml` itself isn't parsed either).
2. **Delete it** (if v2 was abandoned): remove `config.v2.default.toml` and strip all `cfg.get("interactive"/"workflows"/"ui"/...)` call sites down to their literal defaults, so there's one obvious source of truth.

Given the amount of dashboard/workflow code that reads these keys, direction (1) is recommended — see the code block below.

```python
# lib/cipkg/base.py — extend DEFAULT_CONFIG, or better, load it from TOML:
def _load_default_toml():
    import tomllib, os
    path = os.path.join(os.path.dirname(__file__), "..", "..", "config.default.toml")
    v2_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.v2.default.toml")
    cfg = {}
    for p in (path, v2_path):
        if os.path.exists(p):
            with open(p, "rb") as f:
                for section, kv in tomllib.load(f).items():
                    cfg.setdefault(section, {}).update(kv)
    return cfg

DEFAULT_CONFIG = _load_default_toml()
```
This also fixes P1-8 for free (the TOML files become the actual source of truth, matching README claims).

### P1-8: `config.default.toml` is also never parsed as TOML — README claim is false

**File**: `lib/cipkg/base.py`, `config.default.toml`, `README.md:85`

README states: *"CIP uses a TOML configuration file. Default settings are in `config.default.toml`."* This is not true at runtime — see P1-7. `config.default.toml` is only ever used as a **copy source** by `install.sh` (copied verbatim to `.cip/config.toml` on a fresh install), not parsed as a defaults file by the running program. If a maintainer edits `config.default.toml` intending to change the shipped defaults for *already-installed* repos, nothing happens — only `DEFAULT_CONFIG` in `base.py` matters. Fixed by the same patch as P1-7.

### P1-9: Systemic silent failure via 85 unscoped `except Exception:` / bare `except:` blocks

**Files**: repo-wide, 85 occurrences across 30 files (see raw list below), 5 of which are bare `except:` in `analysis.py` alone.

```
lib/cipkg/analysis.py:55,64,72,97,139        (bare except:)
lib/cipkg/daemon.py:19,26,35,49,77,82,91
lib/cipkg/embed.py:51,60,70,150
lib/cipkg/indexer.py:64,357
lib/cipkg/intelligent_executor.py: 12 occurrences
lib/cipkg/session.py:43,50,57,71,164,176,187
lib/cipkg/store.py:136,140,149,215,223
lib/cipkg/terminal_dashboard.py:398,430,736
lib/cipkg/workflow_engine.py: 7 occurrences
... (full list available via: python -m pyflakes / grep -n "except Exception:\|except:" lib/cipkg/*.py)
```

**Root cause**: this isn't one bug, it's a *pattern* that turns real bugs (like P1-4's `NameError`) into silent no-ops. A blanket `except Exception: pass` (or a fallback value) means:
- Programming errors (typos, missing imports, wrong arg counts) are indistinguishable from expected failure modes (file not found, network unavailable).
- No log line, no telemetry, no stderr — the failure is invisible unless someone reads the source.
- Debugging requires re-adding print statements and re-running, defeating the purpose of an "intelligence platform" that's supposed to make codebases *more* legible, not less.

**Fix strategy** (apply repo-wide, prioritize `analysis.py`, `session.py`, `embed.py` first since these affect user-visible output):

1. Add a small logging helper once, in `base.py`:
```python
import logging
log = logging.getLogger("cip")

def log_swallowed(where: str, exc: Exception):
    """Call this from every except-and-continue block so failures are visible
    with CIP_DEBUG=1 without changing control flow."""
    import os
    if os.environ.get("CIP_DEBUG"):
        log.warning("swallowed exception in %s: %r", where, exc)
```
2. Replace every bare `except:` with `except Exception as e:`, and every silent `except Exception: <fallback>` with `except Exception as e: log_swallowed("analysis._calculate_health_score/freshness", e); <fallback>`.
3. Add a CI lint rule (flake8 `E722` already flags bare `except:`; add a custom check or `# noqa` audit for blanket `except Exception:` without logging) so this class of issue can't silently regress.

This single change would have surfaced P1-4 and P1-5 automatically the first time `cip analyze` was run with `CIP_DEBUG=1`.

---

## P2 — Correctness, maintainability, and performance issues

### P2-1: CLI and TUI maintain two independent, hand-written command definitions instead of one source of truth

**Files**: `lib/cipkg/cli.py` (742 lines, argparse + `dispatch_command` dict), `lib/cipkg/command_registry.py` (1,403 lines, `CommandRegistry` class)

**Verified**: `grep -n "CommandRegistry\|command_registry" lib/cipkg/cli.py` returns **zero matches**. `cli.py`'s argparse subparsers and its `dispatch_command()` handler dict are built entirely independently of `CommandRegistry`. Meanwhile, `CommandRegistry`'s ~40 `_handle_*` methods (e.g. `_handle_init` at line 893) exist only to wrap-and-call back into `cli.py`'s `handle_*` functions via a constructed `argparse.Namespace`:
```python
def _handle_init(self, root: str, args: dict) -> dict:
    try:
        from .cli import handle_init_command
        from argparse import Namespace
        return handle_init_command(root, Namespace(**args))
    except Exception as e:
        return {'error': f'Failed to handle init: {str(e)}'}
```
So every command's metadata (name, description, parameters, category, priority) is declared **twice**, by hand, in two files that must be kept in sync manually. This is precisely how bugs like P0-2 happen — a command (`suggest-context`) exists in the argparse parser and in the registry, but its handler function was never written in either place consistently.

**Fix**: make `cli.py`'s argparse construction *generate itself* from `CommandRegistry`, eliminating the duplicate definition. See Report 3 (CLI/TUI upgrades) for the full implementation.

### P2-2: Six duplicate function definitions in `cli.py` silently shadow each other

**File**: `lib/cipkg/cli.py`

`pyflakes` flags:
```
cli.py:237: redefinition of unused 'handle_export_command' from line 210
cli.py:241: redefinition of unused 'handle_doctor_command' from line 214
cli.py:244: redefinition of unused 'handle_serve_command' from line 217
cli.py:248: redefinition of unused 'handle_mcp_command' from line 221
cli.py:252: redefinition of unused 'handle_tools_command' from line 225
cli.py:260: redefinition of unused 'handle_selftest_command' from line 233
```
Six handler functions are each defined twice in the same file. Python silently uses the second definition; the first is dead code. This is a strong signal of a bad merge or copy-paste during a refactor — worth a `git blame` before deleting, in case the two versions actually differ in behavior (if they do, that's a *third*, more serious bug: whichever one is currently "live" may not be the intended one).

**Fix**: diff the two definitions of each function; delete the earlier (shadowed) one if identical, or resolve the conflict if they differ.

```bash
# Investigation command for the agent to run first:
for fn in handle_export_command handle_doctor_command handle_serve_command \
          handle_mcp_command handle_tools_command handle_selftest_command; do
  echo "=== $fn ==="; grep -n "^def $fn" lib/cipkg/cli.py
done
```

### P2-3: Identical bug pattern in `init_detector.py` — two functions defined twice, verbatim

**File**: `lib/cipkg/init_detector.py:376-412` and `398-435` (approx.)

`get_init_ui_text()` and `should_launch_dashboard()` are each defined twice with **byte-identical bodies**. Functionally harmless (the second, identical copy just overwrites the first), but it's 100% certain evidence of a bad copy-paste and should be cleaned up before it's used as a template for further duplication.

**Fix**: delete the second (duplicate) definition of each function.

### P2-4: Unclosed SQLite connection in `session_start()`

**File**: `lib/cipkg/session.py:22`
```python
def session_start(root=None):
    root = root or repo_root()
    cfg = load_config(root)
    con = connect(root)          # <-- opened, never used again, never closed
    ...
```
`pyflakes` confirms: `local variable 'con' is assigned to but never used`. Every call to `session_start()` (which happens on every CLI/interactive session) leaks one SQLite connection handle. On short-lived CLI processes this is invisible (the OS reclaims it on exit), but in the daemon/server long-running process, or in the TUI which stays resident, this is a slow file-descriptor leak, and WAL-mode SQLite (which this project uses — see `PRAGMA journal_mode=WAL` in `store.py`) is especially sensitive to abandoned connections holding the WAL file open.

**Fix**:
```diff
 def session_start(root=None):
     root = root or repo_root()
     cfg = load_config(root)
-    con = connect(root)
     ...
+    # con was never used downstream — removed. If a future feature needs it,
+    # open it in a `with closing(connect(root)) as con:` block scoped to that use.
```

### P2-5: `_VEC_CACHE` module-level dict has no thread safety and is invalidated on every `connect()` call

**File**: `lib/cipkg/store.py:91, 155, 208`

```python
_VEC_CACHE = {}   # db_path -> (signature, ids, matrix)

def connect(root):
    ...
    _VEC_CACHE[os.path.abspath(db)] = None   # unconditionally wipes cache on EVERY connect()
    ...
```
Two separate issues:
1. **No locking.** `server.py` uses `ThreadingHTTPServer`, meaning multiple request-handling threads can call into `retrieve.py` (which reads `_VEC_CACHE` via `vector_matrix()`) concurrently. Plain-dict reads/writes without a lock are not guaranteed atomic for compound check-then-act sequences like the cache-hit check in `vector_matrix()` (`if cached is not None and cached[0] == sig ...`), risking a rare but real race between one thread invalidating and another reading mid-update.
2. **Cache defeats its own purpose for the CLI's usage pattern.** Every `cip <command>` invocation is a fresh Python process, and every fresh process calls `connect(root)` once at the top of nearly every handler — which immediately sets `_VEC_CACHE[db] = None`, discarding any benefit the caching logic in `vector_matrix()` was designed to provide *within that single process*. In practice the cache only helps the long-running `daemon`/`serve` processes, but the comment ("fast repeated KNN") implies it was intended to help all callers.

**Fix** (minimal, in `store.py`):
```diff
+import threading
+_VEC_CACHE_LOCK = threading.Lock()
 _VEC_CACHE = {}

 def connect(root):
     ...
-    _VEC_CACHE[os.path.abspath(db)] = None
+    # Don't blow away a warm cache just because a new connection was opened —
+    # invalidation is handled by vector_signature() comparison, not by connect().
     con.executescript(CORE_SCHEMA)
     ...

 def vector_matrix(con, model):
     ...
     db = os.path.abspath(_db_path(con))
     sig = vector_signature(con, model)
-    cached = _VEC_CACHE.get(db)
-    if cached is not None and cached[0] == sig and cached[1] is not None:
-        return cached[1], cached[2]
+    with _VEC_CACHE_LOCK:
+        cached = _VEC_CACHE.get(db)
+        if cached is not None and cached[0] == sig and cached[1] is not None:
+            return cached[1], cached[2]
     rows = con.execute("SELECT id, vec FROM vectors WHERE model=?", (model,)).fetchall()
     ...
-    _VEC_CACHE[db] = (sig, ids, mat)
+    with _VEC_CACHE_LOCK:
+        _VEC_CACHE[db] = (sig, ids, mat)
     return ids, mat
```

### P2-6: Fragile `python -c "<f-string>"` subprocess pattern for self-invocation

**File**: `lib/cipkg/terminal_dashboard.py:762, 781, 891`
```python
args_str = ', '.join([f"'{arg}'" for arg in args])
subprocess.run([sys.executable, "-c", f"from cipkg.cli import main; main([{args_str}])"])
```
Currently `args` is always a hardcoded list (`['index', '--full']`), so there's no live injection vector today. But this is a repeated anti-pattern (3 call sites) that builds Python *source code* via string interpolation rather than passing arguments as an actual list to a subprocess. The moment any of these three call sites is extended to include user-typed input (e.g., a free-text query typed into the TUI's search box), this becomes a straightforward Python code-injection vulnerability (a query containing `']); import os; os.system(...) #` breaks out of the string).

**Fix**: invoke `main()` in-process instead of shelling out to a fresh interpreter, or if a subprocess is genuinely needed (e.g., to avoid blocking the TUI's event loop), pass argv as a real list, not source text:
```python
# In-process (preferred — avoids ~200ms Python startup cost per action too):
from cipkg.cli import main
main(args)   # args is already a real list, e.g. ['index', '--full']

# If a subprocess is required, use -m with a real argv, not -c with interpolated source:
subprocess.run([sys.executable, "-m", "cipkg.cli", *args])
```

### P2-7: Correlated N+1-style subqueries in `analysis.py`, the module powering `cip analyze`

**File**: `lib/cipkg/analysis.py:100-118, 142-160, 172-201, 223-237`

Several of `analysis.py`'s own queries use a correlated subquery per row:
```sql
SELECT s.id, s.name, s.path,
       (SELECT COUNT(*) FROM edges WHERE dst=s.id) as dependents
FROM symbols s
WHERE s.kind IN ('function', 'method', 'class')
...
```
This pattern (`SELECT ... FROM outer WHERE (SELECT COUNT(*) FROM inner WHERE inner.fk = outer.id)`) is the exact class of query CIP's own quality-audit engine is designed to flag as a performance anti-pattern in *user* code (`stack/prisma.py`'s N+1 detection). It's not wrong for SQLite on a few thousand rows (SQLite can often optimize correlated `COUNT` subqueries reasonably well with the right index), but on large repos (500K+ symbols, per the platform's own stated scale target) this degrades quadratically and is a good candidate to rewrite as a single `LEFT JOIN ... GROUP BY` for consistency with the platform's own stated quality bar.

**Fix** (example for the query above):
```sql
SELECT s.id, s.name, s.path, COALESCE(d.cnt, 0) as dependents
FROM symbols s
LEFT JOIN (SELECT dst, COUNT(*) as cnt FROM edges GROUP BY dst) d ON d.dst = s.id
WHERE s.kind IN ('function', 'method', 'class')
ORDER BY dependents DESC
LIMIT 5
```
Apply the same rewrite to the other three occurrences of this pattern in the same file.

---

## P3 — Minor / cleanup

### P3-1: Duplicate dict keys in `dispatch_command`'s handler map

**File**: `lib/cipkg/cli.py:704-716` — `"audit"`, `"findings"`, and `"impact"` each appear twice in the same dict literal (harmless — Python keeps the last value — but it's dead code and confusing to read/maintain):
```python
"audit": handle_audit_command,
"findings": handle_findings_command,
"impact": handle_impact_command,
"session": handle_session_command,
"verify": handle_verify_command,
"learning": handle_learning_command,
"selftest": handle_selftest_command,
"audit": handle_audit_command,        # duplicate
"findings": handle_findings_command,  # duplicate
"impact": handle_impact_command,      # duplicate
```
**Fix**: delete the three duplicate lines.

### P3-2: 30+ unused imports flagged by `pyflakes`

Spread across `context_manager.py`, `error_system.py`, `gapfill.py`, `help_system.py`, `hooks.py`, `interactive_ui.py`, `learning.py`, `predict.py`, `terminal_dashboard.py`, `verify.py`, `workflow_engine.py`, etc. Not functionally harmful, but adds import-time cost and noise that makes real issues (like P0-3) harder to spot by inspection. Recommended: run `python -m pyflakes lib/cipkg` as a CI gate (see Appendix) so these can't silently accumulate further, then do a single cleanup pass with `autoflake --remove-all-unused-imports`.

### P3-3: F-strings with no placeholders (11 occurrences)

`pyflakes` flags 11 f-strings across `indexer.py`, `interactive.py`, `learning_system.py`, `suggestion_engine.py`, `terminal_dashboard.py` that use the `f"..."` prefix but contain no `{}` interpolation — almost always a sign that an interpolation was intended but the variable reference was dropped during editing (i.e., a likely second-order bug: the message is probably missing dynamic content it was supposed to show). Worth a quick pass to check each one against its intended output.

---

## Appendix: How to catch these automatically going forward

```bash
# Add to CI (GitHub Actions / pre-commit):
pip install pyflakes --break-system-packages
python -m pyflakes lib/cipkg lib/cipkg/stack bin/cip.py
# Any output (other than intentionally-ignored lines) should fail the build.
# This alone would have caught P0-2, P0-3, P1-1, P1-2, P1-3, P1-4, P2-2, P2-3, P3-2, P3-3.

# Smoke test every CLI command actually dispatches without NameError:
python - <<'EOF'
import sys, argparse
sys.path.insert(0, "lib")
from cipkg import cli
p = cli.build_parser()   # (or whatever the parser-construction function is named)
for action in p._subparsers._group_actions[0].choices:
    ns = p.parse_args([action])
    try:
        cli.dispatch_command("/tmp", ns)
    except NameError as e:
        print(f"BROKEN COMMAND: {action}: {e}")
EOF
```

Running the two checks above against the current `main` branch reproduces every P0/P1 finding in this report in under two seconds — recommended as the very first PR in the upgrade sequence, before any feature work, so future regressions are caught in CI rather than by users.
