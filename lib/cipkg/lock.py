"""Cross-process write lock (Windows + POSIX) so daemon/watch/hooks/CLI never collide."""
import os, time
try:
    import msvcrt; _WIN = True
except ImportError:
    import fcntl; _WIN = False

class WriteLock:
    def __init__(self, root, timeout=30):
        from .base import data_dir
        self.path = os.path.join(data_dir(root), "write.lock")
        self.timeout = timeout
        self.fh = None
    def __enter__(self):
        self.fh = open(self.path, "a+")
        start = time.time()
        while True:
            try:
                if _WIN: msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
                else: fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (OSError, IOError):
                if time.time() - start > self.timeout:
                    raise TimeoutError("cip: index busy (another sync is running)")
                time.sleep(0.2)
    def __exit__(self, *a):
        try:
            if _WIN:
                self.fh.seek(0); msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
        finally:
            self.fh.close()
