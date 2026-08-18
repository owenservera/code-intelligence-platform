"""Self-updating loop: zero-dependency mtime polling with debounce."""
import os, time, threading

def _snapshot(root):
    from .base import load_config
    from .gatekeeper import iter_files_smart
    cfg = load_config(root)
    out = {}
    for rel, _tier, _why in iter_files_smart(root, cfg):
        try: out[rel] = os.path.getmtime(os.path.join(root, rel))
        except OSError: pass
    return out

def watch(root=None, interval=1.0, verbose=True, stop_event=None, progress=None, on_change=None):
    """mtime-snapshot watch loop with debounce; calls `sync` on change.

    Args:
        root: repository root (default: auto-detect)
        interval: poll interval in seconds
        verbose: print status lines to stdout
        stop_event: threading.Event — when set, the loop exits at the next
            tick instead of running forever (CORE-16: stop mechanism for the
            web WatchManager; the CLI path passes None and keeps blocking).
        progress: optional callable(kind, cur, tot) forwarded to sync (used by
            the web worker to surface `sync` phases over WS).
        on_change: optional callable(list[str]) invoked with the relative paths
            of files that changed since the last snapshot (P5 T5.2: the web
            WatchManager uses this to emit project-scoped `file.changed`
            events for the realtime-history surface, SPEC-18 §4).
    """
    from .base import repo_root
    from .indexer import sync
    root = root or repo_root()
    seen = _snapshot(root)
    if verbose: print(f"cip: watching {root} (ctrl-c to stop)")
    while True:
        if stop_event is not None and stop_event.is_set():
            if verbose: print("cip: watch stopped")
            return
        time.sleep(interval)
        snap = _snapshot(root)
        if snap == seen: continue
        time.sleep(0.4)                       # debounce write bursts
        seen = _snapshot(root)
        if on_change:
            # Report files whose mtime moved across the debounce window
            # (added, modified, or removed) as a compact list.
            changed = [rel for rel in seen if seen[rel] != snap.get(rel)]
            changed += [rel for rel in snap if rel not in seen]
            if changed:
                try:
                    on_change(changed[:200])
                except Exception:
                    pass
        try:
            stats = sync(root, progress=progress)
            if verbose:
                print(f"cip: synced +{stats['dirty']} -{stats['deleted']} "
                      f"~{stats['embedded']} emb in {stats['ms']}ms")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"cip: sync error: {e}")
