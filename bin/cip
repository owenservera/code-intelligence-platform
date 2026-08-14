#!/usr/bin/env python3
"""Universal CIP wrapper — works from any directory on the machine."""
import os, sys, shutil

GLOBAL_HUB = os.path.join(os.path.expanduser("~"), ".cip-global")
GLOBAL_LIB = os.path.join(GLOBAL_HUB, "lib")
GLOBAL_TEMPLATES = os.path.join(GLOBAL_HUB, "templates")

sys.path.insert(0, GLOBAL_LIB)

GIT_HOOKS = ("post-commit", "post-merge", "post-checkout")
HOOK_MARK = "# >>> cip >>>"


def init_repo():
    """Initialize CIP in the current directory."""
    root = os.getcwd()
    cip_dir = os.path.join(root, ".cip")
    data_dir = os.path.join(cip_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    for f in ("config.toml", "ontology.json"):
        src = os.path.join(GLOBAL_TEMPLATES, f)
        dst = os.path.join(cip_dir, f)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy(src, dst)
            print(f"  created {os.path.relpath(dst, root)}")

    agents_src = os.path.join(GLOBAL_TEMPLATES, "AGENTS.md")
    agents_dst = os.path.join(root, "AGENTS.md")
    if os.path.exists(agents_src) and not os.path.exists(agents_dst):
        shutil.copy(agents_src, agents_dst)
        print(f"  created AGENTS.md")

    git_dir = os.path.join(root, ".git", "hooks")
    if os.path.isdir(git_dir):
        hook_py = os.path.join(GLOBAL_HUB, "bin", "cip.py").replace(os.sep, "/")
        block = f"{HOOK_MARK}\npython \"{hook_py}\" sync 2>/dev/null || true\n# <<< cip <<<\n"
        for h in GIT_HOOKS:
            h_path = os.path.join(git_dir, h)
            existing = ""
            if os.path.exists(h_path):
                existing = open(h_path, encoding="utf-8", errors="replace").read()
            if HOOK_MARK in existing:
                continue
            with open(h_path, "a", newline="\n") as f:
                f.write(existing.rstrip("\n") + "\n\n" + block)
            if sys.platform != "win32":
                os.chmod(h_path, 0o755)
        print(f"  installed git hooks")

    print(f"\nIndexing {root}...")
    from cipkg.indexer import sync
    stats = sync(root, full=True)
    print(f"  indexed: {stats['files']} files, {stats['symbols']} symbols, "
          f"{stats['chunks']} chunks, {stats['edges']} edges, "
          f"{stats['embedded']} vectors in {stats['ms']}ms")

    try:
        from cipkg import gitindex
        from cipkg.base import load_config
        cfg = load_config(root)
        g = gitindex.git_index(root, depth=int(cfg["git"]["depth"]))
        print(f"  git index: {g}")
    except Exception as e:
        print(f"  git index skipped: {e}")

    print(f"\nCIP is active for this repo. Try: cip search \"<query>\"")


def find_repo_root():
    """Walk up from cwd looking for .cip/ directory."""
    p = os.getcwd()
    while True:
        if os.path.isdir(os.path.join(p, ".cip")):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print("Usage: cip <command> [args]")
        print()
        print("Setup:")
        print("  cip init              Initialize CIP in the current repo (fast, no embedding)")
        print("  cip embed             Embed chunks for semantic search (slow, CPU)")
        print()
        print("Intelligence:")
        print("  cip search <query>    Hybrid search (lexical+semantic+graph)")
        print("  cip symbol <name>     Find symbol definitions")
        print("  cip graph <id>        Traverse relationships")
        print("  cip context <query>   Token-budgeted context pack")
        print("  cip summary [path]    Repo/directory/file summary")
        print("  cip map               Repository map")
        print()
        print("Stack Audit:")
        print("  cip audit             Run TS/Next/Prisma audit rules")
        print("  cip findings          Query open findings")
        print("  cip refactors         Quick-win refactors")
        print("  cip impact <file>     Blast radius analysis")
        print("  cip routes            Next.js route inventory")
        print("  cip models            Prisma model usage")
        print("  cip gate              Quality gate")
        print()
        print("DevOps:")
        print("  cip sync              Incremental index update")
        print("  cip broken            Failing tests + type errors")
        print("  cip hotspots          Most-changed files")
        print("  cip dashboard         Open Mission Control UI")
        print("  cip mcp               Start MCP stdio server")
        return 0

    if args[0] == "init":
        init_repo()
        return 0

    root = find_repo_root()
    if not root:
        print("Error: No .cip/ found here or above. Run 'cip init' first.")
        return 1

    os.chdir(root)

    from cipkg.cli import main as cli_main
    return cli_main(args)


if __name__ == "__main__":
    sys.exit(main())
