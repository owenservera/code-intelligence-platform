"""Single-writer daemon: watcher thread + CIP HTTP server, guarded by a lockfile.
One `cip daemon` per repo — the fully self-updating production mode."""
import os, threading
from .base import repo_root, data_dir
from .watch import watch
from .server import serve

def daemon(root=None, port=None, interval=1.0):
    root = root or repo_root()
    lock = os.path.join(data_dir(root), "daemon.lock")
    if os.path.exists(lock):
        try:
            pid = int(open(lock).read().strip())
            os.kill(pid, 0)
            print(f"cip: daemon already running (pid {pid})")
            return
        except Exception:
            pass
    with open(lock, "w") as f:
        f.write(str(os.getpid()))
    try:
        t = threading.Thread(target=watch,
                             kwargs={"root": root, "interval": interval}, daemon=True)
        t.start()
        serve(root, port)          # blocks
    finally:
        try: os.remove(lock)
        except OSError: pass
