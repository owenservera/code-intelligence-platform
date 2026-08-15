"""CIP daemon — single-writer watcher + HTTP server + warm model.
Lifecycle:  cip daemon          start
            cip daemon status   check if running
            cip daemon stop     kill cleanly"""
import json, os, signal, subprocess, sys, threading, time, urllib.request
from .base import repo_root, data_dir

def _paths(root):
    d = data_dir(root)
    return {
        "lock":  os.path.join(d, "daemon.lock"),
        "port":  os.path.join(d, "daemon.port"),
        "log":   os.path.join(d, "daemon.log"),
    }

def _read_pid(lock_path):
    try:
        return int(open(lock_path).read().strip())
    except Exception:
        return None

def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False

def _health(port, timeout=0.5):
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:%d/embed/health" % port)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None

# ── subcommands ──────────────────────────────────────────────────────────────

def daemon_status(root=None):
    """Print daemon status, return dict."""
    root = root or repo_root()
    p = _paths(root)
    pid = _read_pid(p["lock"])
    port = None
    if os.path.exists(p["port"]):
        try:
            port = int(open(p["port"]).read().strip())
        except Exception:
            pass

    info = {"pid": pid, "port": port, "alive": False, "warm": False, "health": None}
    if pid and _alive(pid):
        info["alive"] = True
        if port:
            h = _health(port)
            if h:
                info["warm"] = h.get("warm", False)
                info["health"] = h
    return info

def daemon_stop(root=None):
    """Stop the daemon cleanly (Windows-safe: SIGKILL is not supported on
    Win32, so we use `taskkill /F /T` which tears down the whole process tree)."""
    root = root or repo_root()
    p = _paths(root)
    pid = _read_pid(p["lock"])
    if not pid or not _alive(pid):
        print("daemon: not running")
        _cleanup(p)
        return
    print("daemon: stopping pid %d..." % pid)
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True, timeout=10)
        except Exception:
            pass
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        for _ in range(50):
            if not _alive(pid):
                break
            time.sleep(0.1)
        if _alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
    # wait up to 5s for the process to release the lock
    for _ in range(50):
        if not (pid and _alive(pid)):
            break
        time.sleep(0.1)
    _cleanup(p)
    print("daemon: stopped")

def _cleanup(p):
    for k in ("lock", "port"):
        try:
            os.remove(p[k])
        except OSError:
            pass

# ── main daemon ──────────────────────────────────────────────────────────────

class _Tee:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, data):
        for s in self.streams:
            s.write(data)
            s.flush()
    def flush(self):
        for s in self.streams:
            s.flush()

def daemon(root=None, port=None, interval=1.0):
    root = root or repo_root()
    port = port or 8787
    p = _paths(root)

    # check if already running
    if os.path.exists(p["lock"]):
        pid = _read_pid(p["lock"])
        if pid and _alive(pid):
            print("daemon: already running (pid %d)" % pid)
            print("  stop:  cip daemon stop")
            return

    _cleanup(p)

    print("daemon starting...")
    print("  repo: %s" % root)
    print("  port: %d" % port)
    print("  log:  %s" % p["log"])
    print("  pid:  %d" % os.getpid())
    print()

    # write lock + port files
    with open(p["lock"], "w") as f:
        f.write(str(os.getpid()))
    with open(p["port"], "w") as f:
        f.write(str(port))

    log_f = open(p["log"], "w", encoding="utf-8")
    tee = _Tee(sys.stdout, log_f)
    sys.stdout = tee

    try:
        from .watch import watch
        from .server import serve

        print("[%s] daemon: starting watcher..." % time.strftime("%H:%M:%S"))
        t = threading.Thread(
            target=watch, kwargs={"root": root, "interval": interval}, daemon=True)
        t.start()
        print("[%s] daemon: watcher active (%ss interval)" % (
            time.strftime("%H:%M:%S"), interval))
        print("[%s] daemon: starting HTTP server on :%d..." % (
            time.strftime("%H:%M:%S"), port))
        print("[%s] daemon: model loads on first /embed request" % time.strftime("%H:%M:%S"))
        print("[%s] daemon: READY" % time.strftime("%H:%M:%S"))
        serve(root, port)
    finally:
        sys.stdout = sys.__stdout__
        log_f.close()
        _cleanup(p)
