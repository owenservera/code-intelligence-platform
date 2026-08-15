"""Core sync engine for CIP global synchronization."""
import os
import sys
import shutil
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import fnmatch

class SyncEngine:
    """Main sync orchestration engine."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.source_dir = Path(config['sync']['source']).resolve()
        self.target_dir = Path(config['sync']['target']).expanduser().resolve()
        self.backup_dir = Path(config['sync']['backup_location']).resolve()
        self.log_dir = Path('./sync_global/logs').resolve()
        
        # Expand patterns to actual file list
        self.items_to_sync = self._expand_patterns()
        
        # Ensure directories exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _expand_patterns(self) -> List[str]:
        """Expand glob patterns to actual file paths."""
        expanded_files = []
        
        # Get patterns from config, fallback to old 'files' key
        patterns = self.config['items'].get('patterns', [])
        explicit_files = self.config['items'].get('files', [])
        exclude_patterns = self.config['items'].get('exclude_patterns', [])
        
        # If no patterns, use old files list (backward compatibility)
        if not patterns:
            return explicit_files
        
        # Expand each pattern
        for pattern in patterns:
            pattern_path = self.source_dir / pattern
            
            # Handle directory patterns with **
            if '**' in pattern:
                # Recursive directory matching
                parts = pattern.split('**')
                base_dir = self.source_dir / parts[0] if parts[0] else self.source_dir
                suffix = parts[1] if len(parts) > 1 else ''
                
                if base_dir.exists() and base_dir.is_dir():
                    for root, dirs, files in os.walk(base_dir):
                        root_path = Path(root)
                        # Match files against suffix pattern
                        for file in files:
                            rel_path = root_path.relative_to(self.source_dir) / file
                            if suffix:
                                # Check if file matches the suffix pattern
                                if fnmatch.fnmatch(str(rel_path), pattern):
                                    expanded_files.append(str(rel_path))
                            else:
                                # Include all files in directory
                                expanded_files.append(str(rel_path))
            else:
                # Simple glob pattern
                if '*' in pattern:
                    matches = list(self.source_dir.glob(pattern))
                    for match in matches:
                        if match.exists():
                            rel_path = match.relative_to(self.source_dir)
                            expanded_files.append(str(rel_path))
                else:
                    # Exact path
                    if pattern_path.exists():
                        expanded_files.append(pattern)
        
        # Add any explicit files that don't match patterns
        expanded_files.extend(explicit_files)
        
        # Remove duplicates and sort
        expanded_files = sorted(list(set(expanded_files)))
        
        # Apply exclusion patterns
        if exclude_patterns:
            original_count = len(expanded_files)
            filtered_files = []
            for file_path in expanded_files:
                excluded = False
                for exclude_pattern in exclude_patterns:
                    if fnmatch.fnmatch(file_path, exclude_pattern):
                        excluded = True
                        break
                if not excluded:
                    filtered_files.append(file_path)
            expanded_files = filtered_files
            excluded_count = original_count - len(expanded_files)
            self.log("INFO", f"Excluded {excluded_count} files matching exclusion patterns")
        
        self.log("INFO", f"Expanded {len(patterns)} patterns to {len(expanded_files)} files")
        return expanded_files
        
    def get_file_hash(self, filepath: Path) -> str:
        """Calculate SHA256 hash of a file."""
        hasher = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""
    
    def create_backup(self) -> str:
        """Create backup of target directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        if not self.target_dir.exists():
            self.log("INFO", f"Target directory does not exist, skipping backup")
            return backup_name
        
        try:
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.copytree(self.target_dir, backup_path)
            self.log("INFO", f"Backup created: {backup_name}")
            return backup_name
        except Exception as e:
            self.log("ERROR", f"Backup failed: {e}")
            raise
    
    def sync_item(self, item: str, dry_run: bool = False) -> bool:
        """Sync a single item from source to target."""
        source_path = self.source_dir / item
        target_path = self.target_dir / item
        
        if not source_path.exists():
            self.log("ERROR", f"Source does not exist: {item}")
            return False
        
        if dry_run:
            self.log("DRY_RUN", f"Would sync: {item}")
            return True
        
        try:
            if source_path.is_dir():
                if target_path.exists():
                    shutil.rmtree(target_path)
                shutil.copytree(source_path, target_path)
                self.log("INFO", f"Synced directory: {item}")
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
                self.log("INFO", f"Synced file: {item}")
            return True
        except Exception as e:
            self.log("ERROR", f"Failed to sync {item}: {e}")
            return False
    
    def sync_all(self, dry_run: bool = False) -> Tuple[int, int]:
        """Sync all configured items."""
        success_count = 0
        total_count = len(self.items_to_sync)
        
        for item in self.items_to_sync:
            if self.sync_item(item, dry_run):
                success_count += 1
        
        return success_count, total_count
    
    def rollback(self, backup_name: str) -> bool:
        """Rollback to a specific backup."""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            self.log("ERROR", f"Backup not found: {backup_name}")
            return False
        
        try:
            # Create backup of current state before rollback
            current_backup = self.create_backup()
            
            # Remove current target
            if self.target_dir.exists():
                shutil.rmtree(self.target_dir)
            
            # Restore from backup
            shutil.copytree(backup_path, self.target_dir)
            self.log("INFO", f"Rollback complete: {backup_name}")
            return True
        except Exception as e:
            self.log("ERROR", f"Rollback failed: {e}")
            return False
    
    def cleanup_old_backups(self):
        """Remove old backups keeping only max_backups."""
        max_backups = self.config['rollback'].get('max_backups', 5)
        backups = sorted(self.backup_dir.glob("backup_*"), reverse=True)
        
        for old_backup in backups[max_backups:]:
            try:
                shutil.rmtree(old_backup)
                self.log("INFO", f"Removed old backup: {old_backup.name}")
            except Exception as e:
                self.log("ERROR", f"Failed to remove backup {old_backup.name}: {e}")
    
    def log(self, level: str, message: str):
        """Write to sync history log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        with open(self.log_dir / "sync_history.log", "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        print(f"[{level}] {message}")
    
    def get_available_backups(self) -> List[str]:
        """Get list of available backups."""
        backups = sorted(self.backup_dir.glob("backup_*"), reverse=True)
        return [b.name for b in backups]