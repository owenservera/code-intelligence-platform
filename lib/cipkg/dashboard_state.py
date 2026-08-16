"""
Reactive State Management for Dashboard
Enables real-time updates without full screen refreshes.
"""

from typing import Optional, Dict, Any
import threading
import time


class DashboardState:
    """Reactive state container for dashboard."""
    
    def __init__(self):
        self._health_score = 100
        self._index_fresh = False
        self._git_branch = "unknown"
        self._uncommitted_files = 0
        self._last_sync = "Never"
        self._listeners = []
        self._lock = threading.Lock()
    
    @property
    def health_score(self) -> int:
        return self._health_score
    
    @health_score.setter
    def health_score(self, value: int):
        with self._lock:
            if self._health_score != value:
                self._health_score = value
                self._notify_listeners('health_score', value)
    
    @property
    def index_fresh(self) -> bool:
        return self._index_fresh
    
    @index_fresh.setter
    def index_fresh(self, value: bool):
        with self._lock:
            if self._index_fresh != value:
                self._index_fresh = value
                self._notify_listeners('index_fresh', value)
    
    @property
    def git_branch(self) -> str:
        return self._git_branch
    
    @git_branch.setter
    def git_branch(self, value: str):
        with self._lock:
            if self._git_branch != value:
                self._git_branch = value
                self._notify_listeners('git_branch', value)
    
    @property
    def uncommitted_files(self) -> int:
        return self._uncommitted_files
    
    @uncommitted_files.setter
    def uncommitted_files(self, value: int):
        with self._lock:
            if self._uncommitted_files != value:
                self._uncommitted_files = value
                self._notify_listeners('uncommitted_files', value)
    
    def add_listener(self, callback):
        """Add a state change listener."""
        with self._lock:
            self._listeners.append(callback)
    
    def remove_listener(self, callback):
        """Remove a state change listener."""
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)
    
    def _notify_listeners(self, property_name: str, value: Any):
        """Notify all listeners of state change."""
        for listener in self._listeners:
            try:
                listener(property_name, value)
            except Exception as e:
                print(f"Warning: Listener failed: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            'health_score': self._health_score,
            'index_fresh': self._index_fresh,
            'git_branch': self._git_branch,
            'uncommitted_files': self._uncommitted_files,
            'last_sync': self._last_sync
        }


class StateUpdater:
    """Background thread that updates state periodically."""
    
    def __init__(self, root: str, state: DashboardState, interval: int = 30):
        self.root = root
        self.state = state
        self.interval = interval
        self._running = False
        self._thread = None
    
    def start(self):
        """Start the updater thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the updater thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def _update_loop(self):
        """Main update loop."""
        while self._running:
            try:
                self._update_state()
            except Exception as e:
                print(f"State updater error: {e}")
            
            time.sleep(self.interval)
    
    def _update_state(self):
        """Update state from repository."""
        try:
            from cipkg.store import connect, get_meta
            from cipkg import indexer
            import subprocess
            
            con = connect(self.root)
            
            # Update health score
            try:
                from cipkg import gapfill
                health = gapfill.score(self.root)
                self.state.health_score = health.get('score', 100)
            except Exception:
                pass
            
            # Update index freshness
            last_sync = float(get_meta(con, "last_sync", 0) or 0)
            lag = time.time() - last_sync if last_sync else None
            self.state.index_fresh = bool(lag is not None and lag < 3600)
            
            # Update git state
            try:
                result = subprocess.run(
                    ['git', 'branch', '--show-current'],
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.state.git_branch = result.stdout.strip()
                
                result = subprocess.run(
                    ['git', 'diff', '--name-only'],
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    uncommitted = len([f for f in result.stdout.split('\n') if f.strip()])
                    self.state.uncommitted_files = uncommitted
            except Exception:
                pass
            
        except Exception as e:
            print(f"State update failed: {e}")
