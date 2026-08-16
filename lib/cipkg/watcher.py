"""
Async File Watcher - Real-time index updates on file changes.
"""
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable, Set
import threading

class CodeChangeHandler(FileSystemEventHandler):
    """Handle file system changes and trigger re-indexing."""
    
    def __init__(self, on_change: Callable[[str], None]):
        self.on_change = on_change
        self._ignore_patterns = {
            '.git', 'node_modules', '__pycache__', '.venv', 'venv',
            '.cip', '.DS_Store', '*.pyc'
        }
    
    def on_modified(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self.on_change(event.src_path)
    
    def on_created(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self.on_change(event.src_path)
    
    def on_deleted(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            self.on_change(event.src_path)
    
    def _should_process(self, path: str) -> bool:
        """Check if path should be processed."""
        # Skip ignored patterns
        for pattern in self._ignore_patterns:
            if pattern in path:
                return False
        
        # Only process source files
        ext = os.path.splitext(path)[1].lower()
        return ext in {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java'}

class AsyncFileWatcher:
    """Watch files and trigger re-indexing in background thread."""
    
    def __init__(self, root: str, on_change: Callable[[str], None]):
        self.root = root
        self.on_change = on_change
        self.observer = None
        self._running = False
    
    def start(self):
        """Start watching in background thread."""
        if self._running:
            return
        
        event_handler = CodeChangeHandler(self.on_change)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.root, recursive=True)
        
        thread = threading.Thread(target=self._run_observer, daemon=True)
        thread.start()
        
        self._running = True
        print(f"[Watcher] Started watching {self.root}")
    
    def _run_observer(self):
        """Run observer in thread."""
        self.observer.start()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop watching."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self._running = False
        print("[Watcher] Stopped")

# Integration with indexer
def setup_watcher(root: str):
    """Setup file watcher for automatic re-indexing."""
    from . import indexer
    
    def on_file_change(path: str):
        """Handle file change event."""
        print(f"[Watcher] Detected change: {path}")
        
        # Trigger incremental re-index
        try:
            # Re-index just this file
            from .base import load_config
            from .store import connect
            
            con = connect(root)
            cfg = load_config(root)
            
            # Mark file for re-indexing
            indexer.mark_for_reindex(con, [path])
            
            # Run incremental embed
            indexer.embed_pending(con, cfg, batch=1)
            
            print(f"[Watcher] Re-indexed: {path}")
        except Exception as e:
            print(f"[Watcher] Error re-indexing {path}: {e}")
    
    watcher = AsyncFileWatcher(root, on_file_change)
    return watcher
