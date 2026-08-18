"""init_flow — shared project onboarding used by CLI `cip init` and the web bridge.

Extracted from cli.cmd_init (PLAN-04 / SPEC-19 §6.3) so the CLI and the web console
run the SAME full-init code path. `init_project` performs the one-time setup:
.cip/data, AGENTS.md, git + agent hooks, detection, a full indexer.sync, and a
git-history index. Heavy work runs as a background job when driven from the web
(T4.2 in plan-04).
"""

import json
import os
import shutil

from .cli import _desc, _progress, _install_hooks, _ensure_gitignore
from .hooks import install_agent_hooks


def init_project(root, progress=None):
    """Full one-time project init (mirrors the former cli.cmd_init).

    Args:
        root: project directory to initialize.
        progress: optional indexer-style callback ``(phase, cur, total)`` forwarded
            to ``indexer.sync`` (e.g. the web bridge's ``_job_progress`` adapter).
            When ``None`` (CLI), the CLI progress bar is used.

    Returns:
        {"ok": True, "stats": <sync stats>, "detection": <detect result>,
         "warnings": <list of non-fatal init warnings>}
    """
    from .base import load_config
    from . import detect, indexer
    from .store import connect, set_meta

    warnings = []

    _desc("Setting up CIP for this project (one-time setup)")
    cipd = os.path.join(root, ".cip")
    os.makedirs(os.path.join(cipd, "data"), exist_ok=True)

    # Copy AGENTS.md template if it doesn't exist
    agents_src = os.path.join(os.path.dirname(__file__), "templates", "AGENTS.md")
    agents_dst = os.path.join(root, "AGENTS.md")
    if os.path.exists(agents_src) and not os.path.exists(agents_dst):
        shutil.copy(agents_src, agents_dst)
        print("created %s" % agents_dst)

    _install_hooks(root)
    _ensure_gitignore(root)

    # Install agent hooks for common agent types
    _desc("Installing agent integration hooks")
    for agent_type in ["claude-code", "opencode"]:
        result = install_agent_hooks(root, agent_type)
        if result.get("ok"):
            print("installed %s hooks: %s" % (agent_type, result.get("config_path")))
        else:
            print("skipped %s hooks: %s" % (agent_type, result.get("error", "unknown")))
    cfg = load_config(root, warnings=warnings)
    _desc("Detecting project type (languages, frameworks, stacks)")
    det = detect.detect(root, cfg)
    con = connect(root)
    set_meta(con, "detection", json.dumps(det))
    con.commit()
    print("detected: primary=%s stacks=%s langs=%s" % (
        det["primary"], det["stacks"], det["languages"]))
    _desc("Scanning every file to build the code map (symbols, imports, edges)")
    stats = indexer.sync(root, full=True, do_embed=False, progress=progress or _progress)
    print("structure: %d files, %d symbols, %d chunks, %d edges (%dms)" % (
        stats["files"], stats["symbols"], stats["chunks"], stats["edges"], stats["ms"]))
    _desc("Indexing git history for change-tracking")
    try:
        from . import gitindex
        g = gitindex.git_index(root, depth=int(cfg["git"]["depth"]))
        print("git index: %s" % g)
    except Exception as e:
        print("git index skipped: %s" % e)
    print("setup complete. Next steps:")
    print("  cip sync      -- update the index (run after any code change)")
    print("  cip daemon    -- start background watcher + HTTP server")
    print("  cip embed-ping -- test embedding latency")
    print("  cip doctor    -- check system health")
    return {"ok": True, "stats": stats, "detection": det, "warnings": warnings}
