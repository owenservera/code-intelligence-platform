#!/usr/bin/env python3
"""Universal CIP wrapper — works from any directory on the machine."""
import os, sys, shutil

# Try local lib first, then global
LOCAL_LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
if os.path.isdir(LOCAL_LIB):
    sys.path.insert(0, LOCAL_LIB)

GLOBAL_HUB = os.path.join(os.path.expanduser("~"), ".cip-global")
GLOBAL_LIB = os.path.join(GLOBAL_HUB, "lib")
GLOBAL_TEMPLATES = os.path.join(GLOBAL_HUB, "templates")

if os.path.isdir(GLOBAL_LIB):
    sys.path.insert(0, GLOBAL_LIB)

GIT_HOOKS = ("post-commit", "post-merge", "post-checkout")
HOOK_MARK = "# >>> cip >>>"


def init_repo():
    """Initialize CIP in the current directory."""
    root = os.getcwd()
    cip_dir = os.path.join(root, ".cip")
    data_dir = os.path.join(cip_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # Load config to show profile settings
    try:
        from cipkg.base import load_config
        cfg = load_config(root)
        
        # Show repo profile settings
        print("╔═══════════════════════════════════════════════════════════════╗")
        print("║  CIP v2.0 - Repository Profile Settings                       ║")
        print("╠═══════════════════════════════════════════════════════════════╣")
        print(f"║  📁 Repository: {root:50} ║")
        
        # Detect and show repo type
        try:
            import sys
            cip_base_dir = os.path.dirname(os.path.dirname(__file__))
            repo_settings_dir = os.path.join(cip_base_dir, "repo-settings")
            if repo_settings_dir not in sys.path:
                sys.path.insert(0, repo_settings_dir)
            
            from detectors import detect_repo_type
            repo_type = detect_repo_type(root)
            print(f"║  🏷️  Repo Type: {repo_type:45} ║")
        except Exception:
            print(f"║  🏷️  Repo Type: {'generic':45} ║")
        
        # Show include/exclude settings
        include_list = cfg.get("index", {}).get("include", [])
        exclude_list = cfg.get("index", {}).get("exclude", [])
        
        print("╠═══════════════════════════════════════════════════════════════╣")
        print("║  📂 Included Directories:                                    ║")
        if include_list:
            for inc in include_list:
                print(f"║  • {inc:55} ║")
        else:
            print("║  • (all directories)                                      ║")
        
        print("╠═══════════════════════════════════════════════════════════════╣")
        print("║  🚫 Excluded Paths:                                           ║")
        if exclude_list:
            for exc in exclude_list:
                print(f"║  • {exc:55} ║")
        else:
            print("║  • (none)                                                 ║")
        
        print("╚═══════════════════════════════════════════════════════════════╝")
        print()
        
    except Exception as e:
        print(f"Note: Could not load profile settings: {e}")
        print("Proceeding with default settings...\n")

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


def launch_smart_dashboard(root, init_state):
    """Launch the smart terminal dashboard."""
    from cipkg.terminal_dashboard import launch_interactive_dashboard
    launch_interactive_dashboard(root)


def main():
    args = sys.argv[1:]

    # Handle help flag
    if args and args[0] in ("-h", "--help"):
        print("Usage: cip <command> [args]")
        print()
        print("Smart Terminal (v2.0):")
        print("  cip                  Launch intelligent dashboard (default)")
        print("  cip i                 Launch web dashboard (alias)")
        print("  cip --no-dashboard    Use traditional command-line interface")
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

    # Check for --no-dashboard flag
    use_dashboard = True
    if "--no-dashboard" in args:
        use_dashboard = False
        args = [a for a in args if a != "--no-dashboard"]

    # Handle explicit commands
    if args:
        if args[0] == "init":
            init_repo()
            return 0
        elif args[0] == "i":
            # Launch web dashboard (alias for cip dashboard)
            root = find_repo_root()
            if not root:
                print("Error: No .cip/ found here or above. Run 'cip init' first.")
                return 1
            os.chdir(root)
            from cipkg.cli import main as cli_main
            return cli_main(['dashboard'])
        
        # For other commands, use traditional CLI
        root = find_repo_root()
        if not root:
            print("Error: No .cip/ found here or above. Run 'cip init' first.")
            return 1

        os.chdir(root)
        from cipkg.cli import main as cli_main
        return cli_main(args)

    # No arguments - launch smart based on initialization status
    root = os.getcwd()
    
    # Check initialization status
    try:
        from cipkg.init_detector import detect_init_status, should_launch_dashboard, should_show_init_ui, should_show_index_ui
        init_state = detect_init_status(root)
    except ImportError:
        # Fallback to traditional help if v2.0 modules not available
        print("Usage: cip <command> [args]")
        print("Run 'cip --help' for more information")
        return 0
    except Exception as e:
        # Handle detection errors gracefully
        print(f"Error detecting repository status: {e}")
        print("Usage: cip <command> [args]")
        print("Run 'cip --help' for more information")
        return 1
    
    if not use_dashboard:
        # User explicitly requested no dashboard, show help
        print("Usage: cip <command> [args]")
        print("Run 'cip --help' for more information")
        return 0
    
    if should_show_init_ui(init_state):
        # Show initialization options
        show_init_ui(root, init_state)
        return 0
    elif should_show_index_ui(init_state):
        # Show index building options
        show_index_ui(root, init_state)
        return 0
    elif should_launch_dashboard(init_state):
        # Launch smart dashboard
        launch_smart_dashboard(root, init_state)
        return 0
    else:
        # Fallback to help
        print("Usage: cip <command> [args]")
        print("Run 'cip --help' for more information")
        return 0


def show_init_ui(root, init_state):
    """Show initialization options for uninitialized repository."""
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║  CIP v2.0 - Repository Not Initialized                        ║")
    print("╠═══════════════════════════════════════════════════════════════╣")
    print(f"║  📁 Repository: {root:50} ║")
    
    if init_state.detection:
        detection = init_state.detection
        print(f"║  🔍 Detected: {detection.repo_type:20} {', '.join(detection.languages[:3]):20} ║")
        if detection.has_git:
            print(f"║  ✅ Git repository detected                                 ║")
    
    print("╠═══════════════════════════════════════════════════════════════╣")
    print("║  🚀 Quick Start:                                               ║")
    print("║  [1] Initialize CIP (recommended)                              ║")
    print("║  [2] Initialize with custom settings                           ║")
    print("║  [3] Learn more about CIP                                      ║")
    print("║  [4] Exit                                                       ║")
    print("╠═══════════════════════════════════════════════════════════════╣")
    print("║  💡 What CIP will do:                                          ║")
    print("║  • Scan all files in repository                                ║")
    print("║  • Build code map (symbols, imports, relationships)             ║")
    print("║  • Index git history for change tracking                        ║")
    print("║  • Enable intelligent search and analysis                       ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    
    print("\nSelect an option: ", end='')
    choice = input().strip()
    
    if choice == '1':
        print("\nInitializing CIP...")
        init_repo()
    elif choice == '2':
        print("\nCustom initialization not yet implemented")
        print("Running standard initialization...")
        init_repo()
    elif choice == '3':
        print("\nLearn more at: https://github.com/cip/cip")
    elif choice == '4':
        print("Exiting...")
    else:
        print("Invalid option")


def show_index_ui(root, init_state):
    """Show index building options for repository without index."""
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║  CIP v2.0 - Repository Ready                                  ║")
    print("╠═══════════════════════════════════════════════════════════════╣")
    print(f"║  📁 Repository: {root:50} ║")
    
    if init_state.detection:
        detection = init_state.detection
        print(f"║  🏷️  Type: {detection.repo_type:20}                              ║")
    
    print("║  ✅ CIP initialized                                            ║")
    print("║  ⚠️  Index needs building                                      ║")
    print("╠═══════════════════════════════════════════════════════════════╣")
    print("║  🚀 Next Steps:                                                ║")
    print("║  [1] Build index (recommended)                                ║")
    print("║  [2] Build index with embeddings (slower)                      ║")
    print("║  [3] Skip and use basic features                               ║")
    print("║  [4] Exit                                                       ║")
    print("╠═══════════════════════════════════════════════════════════════╣")
    print("║  💡 Index enables:                                             ║")
    print("║  • Intelligent code search                                     ║")
    print("║  • Symbol navigation and graph traversal                       ║")
    print("║  • Impact analysis and change tracking                         ║")
    print("║  • Context-aware suggestions                                   ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    
    print("\nSelect an option: ", end='')
    choice = input().strip()
    
    if choice == '1':
        print("\nBuilding index...")
        os.chdir(root)
        from cipkg.cli import main as cli_main
        cli_main(['index', '--full'])
    elif choice == '2':
        print("\nBuilding index with embeddings...")
        os.chdir(root)
        from cipkg.cli import main as cli_main
        cli_main(['index', '--full', '--reembed'])
    elif choice == '3':
        print("Skipping index build. Basic features available.")
    elif choice == '4':
        print("Exiting...")
    else:
        print("Invalid option")


if __name__ == "__main__":
    sys.exit(main())
