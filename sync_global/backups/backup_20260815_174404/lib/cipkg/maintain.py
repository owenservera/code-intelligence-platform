"""Durability: rebuild, verify (drift), vacuum, event pruning."""
import os, time
from .store import connect

def rebuild(root=None, progress=None):
    from .base import repo_root, data_dir
    from .indexer import sync
    root = root or repo_root()
    # delete DB files FIRST (don't connect to corrupted DB)
    db = os.path.join(data_dir(root), "index.db")
    for suffix in ("", "-wal", "-shm"):
        p = db + suffix
        if os.path.exists(p): os.remove(p)
    return sync(root, full=True, progress=progress)

def verify(root=None, repair=False):
    from .base import repo_root, sha
    root = root or repo_root()
    con = connect(root)
    drift, checked = [], 0
    for r in con.execute("SELECT path, hash FROM files"):
        checked += 1
        ap = os.path.join(root, r["path"])
        if not os.path.exists(ap):
            drift.append({"path": r["path"], "status": "missing"}); continue
        try:
            h = sha(open(ap, encoding="utf-8", errors="replace").read())
        except OSError:
            drift.append({"path": r["path"], "status": "unreadable"}); continue
        if h != r["hash"]:
            drift.append({"path": r["path"], "status": "changed"})
    result = {"checked": checked, "drift": drift}
    if repair and drift:
        from .indexer import sync
        sync(root, full=False)
        result["repaired"] = True
    return result

def vacuum(root=None, event_days=None):
    from .base import repo_root, load_config
    root = root or repo_root(); cfg = load_config(root)
    days = event_days or int(cfg.get("maintain", {}).get("event_days", 30))
    con = connect(root)
    cutoff = time.time() - days * 86400
    ev = con.execute("DELETE FROM events WHERE ts < ?", (cutoff,)).rowcount
    vecs = con.execute("DELETE FROM vectors WHERE id NOT IN (SELECT id FROM chunks)").rowcount
    con.commit()
    con.execute("VACUUM")
    return {"events_pruned": ev, "orphan_vectors": vecs}
