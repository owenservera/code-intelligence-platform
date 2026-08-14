"""Self-updating loop: zero-dependency mtime polling with debounce."""
import os, time

def _snapshot(root):
    from .base import load_config, iter_files
    cfg = load_config(root)
    out = {}
    for rel in iter_files(root, cfg):
        try: out[rel] = os.path.getmtime(os.path.join(root, rel))
        except OSError: pass
    return out

def watch(root=None, interval=1.0, verbose=True):
    from .base import repo_root
    from .indexer import sync
    root = root or repo_root()
    seen = _snapshot(root)
    if verbose: print(f"cip: watching {root} (ctrl-c to stop)")
    while True:
        time.sleep(interval)
        snap = _snapshot(root)
        if snap == seen: continue
        time.sleep(0.4)                       # debounce write bursts
        seen = _snapshot(root)
        try:
            stats = sync(root)
            if verbose:
                print(f"cip: synced +{stats['dirty']} -{stats['deleted']} "
                      f"~{stats['embedded']} emb in {stats['ms']}ms")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"cip: sync error: {e}")
