"""Global project registry: a single disk store of every code folder CIP manages.

SPEC-19 §1/§5. Before this module, no global place recorded CIP's managed folders —
per-folder state lived only in ``<root>/.cip`` and ``sync_global/``/``repo-settings/``
were referenced in docs but absent on disk. This registry is the new source of truth
for the multi-project console.

The registry lives OUTSIDE any project (``$CIP_HOME`` or ``~/.cip``) so it survives
project deletion and is shared by the CLI, the web console, and the daemon.
"""

import json
import logging
import os
import threading
import time
from pathlib import Path

log = logging.getLogger("cip")

REGISTRY_VERSION = 1


class ProjectRegistry:
    """Thread-safe, atomically-written JSON store of known projects.

    ``id`` is the normalized absolute root (``os.path.normcase(os.path.abspath(root))``)
    so it is stable across sessions and case-insensitive on Windows. All writes go
    through a temp-file + ``os.replace`` so a crash never leaves a half-written store.
    """

    def __init__(self, home: str | os.PathLike[str] | None = None):
        self._home = Path(home) if home is not None else self.default_home()
        self._lock = threading.Lock()
        self._store_path = self._home / "projects.json"
        self._cache: dict[str, dict] | None = None

    @staticmethod
    def default_home() -> Path:
        """Resolve the registry home: ``$CIP_HOME`` or ``~/.cip``.

        Raises ValueError (never a silent pass, plan-01 fail-state) if the directory
        cannot be created or is not writable.
        """
        raw = os.environ.get("CIP_HOME")
        home = Path(raw) if raw else Path.home() / ".cip"
        try:
            home.mkdir(parents=True, exist_ok=True)
            if not os.access(home, os.W_OK):
                raise ValueError(f"registry home not writable: {home}")
        except OSError as exc:
            raise ValueError(f"registry home unusable: {home}: {exc}") from exc
        return home

    # ── path helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def project_id(root: str | os.PathLike[str]) -> str:
        """Stable id for a root: normalized absolute path, case-insensitive on Windows."""
        return os.path.normcase(os.path.abspath(os.fspath(root)))

    # ── read path ───────────────────────────────────────────────────────────────
    def _load(self) -> dict[str, dict]:
        """Load the store, tolerating a missing or corrupt file (backup + fresh start).

        Corrupt JSON never crashes the web server: the bad file is renamed to
        ``projects.json.bak`` and an empty store is returned (plan-01 acceptance).
        """
        if not self._store_path.exists():
            return {}
        try:
            data = json.loads(self._store_path.read_text(encoding="utf-8"))
            projects = data.get("projects", {})
            return projects if isinstance(projects, dict) else {}
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            log.warning("cip.registry: corrupt store at %s (%r); backing up and starting fresh",
                        self._store_path, exc)
            try:
                backup = self._store_path.with_suffix(".json.bak")
                os.replace(self._store_path, backup)
            except OSError:
                pass
            return {}

    def _all(self) -> dict[str, dict]:
        """Cached view of every project, keyed by id."""
        with self._lock:
            if self._cache is None:
                self._cache = self._load()
            return self._cache

    def list(self) -> dict[str, dict]:
        """Return ``{id: {...}}`` for every registered project (live, uncached copy)."""
        return {k: dict(v) for k, v in self._all().items()}

    def get(self, project_id: str) -> dict | None:
        """Return one project entry or None. Exact id match (caller must normalize)."""
        entry = self._all().get(project_id)
        return dict(entry) if entry else None

    def has(self, root: str | os.PathLike[str]) -> bool:
        """True if ``root`` (normalized) is already registered."""
        return self.project_id(root) in self._all()

    # ── write path ──────────────────────────────────────────────────────────────
    def _save(self, projects: dict[str, dict]) -> None:
        """Atomic write: tmp file in the same dir → fsync → os.replace (plan-01)."""
        payload = {"version": REGISTRY_VERSION, "projects": projects}
        tmp = self._store_path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self._store_path)

    def register(self, root: str | os.PathLike[str]) -> dict:
        """Register ``root`` idempotently (upsert). Returns the entry.

        Re-registering an existing root keeps its original ``added_ts`` and returns the
        same entry — the console's list never grows duplicates (SPEC-19 §6.1).
        """
        root_path = os.path.abspath(os.fspath(root))
        if not os.path.isdir(root_path):
            raise ValueError(f"not a directory: {root_path}")
        pid = self.project_id(root_path)
        now = int(time.time())
        with self._lock:
            projects = self._load()
            entry = projects.get(pid)
            if entry is None:
                entry = {"id": pid, "root": root_path, "added_ts": now,
                         "last_onboard_ts": None}
                projects[pid] = entry
                self._save(projects)
            self._cache = projects
            return dict(entry)

    def unregister(self, project_id: str) -> bool:
        """Remove a project by id. Returns True if it existed. Never touches files."""
        with self._lock:
            projects = self._load()
            if project_id not in projects:
                return False
            del projects[project_id]
            self._save(projects)
            self._cache = projects
            return True

    def touch_onboard(self, project_id: str) -> dict | None:
        """Record a successful onboarding for a project (updates ``last_onboard_ts``)."""
        with self._lock:
            projects = self._load()
            entry = projects.get(project_id)
            if entry is None:
                return None
            entry["last_onboard_ts"] = int(time.time())
            self._save(projects)
            self._cache = projects
            return dict(entry)

    @property
    def home(self) -> Path:
        return self._home

    @property
    def store_path(self) -> Path:
        return self._store_path


_registry: ProjectRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> ProjectRegistry:
    """Module-level singleton, built lazily so importing this module has no side
    effects (the web bridge and CLI both import it; plan-01 import-safe acceptance)."""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = ProjectRegistry()
    return _registry
