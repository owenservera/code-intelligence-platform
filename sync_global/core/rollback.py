"""Rollback system for CIP sync operations."""
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

class RollbackManager:
    """Manage rollback operations for sync."""
    
    def __init__(self, backup_dir: Path, target_dir: Path, log_dir: Path):
        self.backup_dir = backup_dir
        self.target_dir = target_dir
        self.log_dir = log_dir
        
    def list_backups(self) -> list:
        """List available backups."""
        backups = sorted(self.backup_dir.glob("backup_*"), reverse=True)
        return [{"name": b.name, "time": self._parse_backup_time(b.name)} for b in backups]
    
    def _parse_backup_time(self, backup_name: str) -> str:
        """Parse timestamp from backup name."""
        try:
            # Extract timestamp from backup_YYYYMMDD_HHMMSS
            timestamp_str = backup_name.replace("backup_", "")
            dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "Unknown"
    
    def restore_backup(self, backup_name: str) -> bool:
        """Restore from a specific backup."""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            print(f"[ERROR] Backup not found: {backup_name}")
            return False
        
        try:
            # Create emergency backup of current state
            emergency_backup = self._create_emergency_backup()
            print(f"[INFO] Emergency backup created: {emergency_backup}")
            
            # Remove current target
            if self.target_dir.exists():
                shutil.rmtree(self.target_dir)
            
            # Restore from backup
            shutil.copytree(backup_path, self.target_dir)
            print(f"[INFO] Rollback complete: {backup_name}")
            
            self._log_rollback(backup_name, True)
            return True
        except Exception as e:
            print(f"[ERROR] Rollback failed: {e}")
            self._log_rollback(backup_name, False, str(e))
            return False
    
    def _create_emergency_backup(self) -> str:
        """Create emergency backup before rollback."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"emergency_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        if self.target_dir.exists():
            shutil.copytree(self.target_dir, backup_path)
        
        return backup_name
    
    def _log_rollback(self, backup_name: str, success: bool, error: Optional[str] = None):
        """Log rollback operation."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "SUCCESS" if success else "FAILED"
        
        with open(self.log_dir / "sync_history.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] ROLLBACK: {backup_name} - {status}\n")
            if error:
                f.write(f"  ERROR: {error}\n")