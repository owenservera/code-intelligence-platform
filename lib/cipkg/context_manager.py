"""
Context Management System for CIP CLI v2.0

This module provides comprehensive context management including repository,
user, session, and system context with caching and provider architecture.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import os
import json
import hashlib


class ContextScope(Enum):
    """Context scope levels."""
    GLOBAL = "global"
    REPOSITORY = "repository"
    SESSION = "session"
    COMMAND = "command"


@dataclass
class RepositoryContext:
    """Repository-specific context."""
    root: str
    repo_type: str
    repo_name: str
    repo_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # State information
    health_score: Optional[Dict[str, Any]] = None
    index_status: Optional[Dict[str, Any]] = None
    git_state: Optional[Dict[str, Any]] = None
    
    # Stack information
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    
    # File system
    file_count: int = 0
    directory_structure: Dict[str, Any] = field(default_factory=dict)
    recent_files: List[str] = field(default_factory=list)
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    profile_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserContext:
    """User-specific context and patterns."""
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Usage patterns
    command_history: List[Dict[str, Any]] = field(default_factory=list)
    workflow_preferences: Dict[str, str] = field(default_factory=dict)
    time_patterns: Dict[str, Any] = field(default_factory=dict)
    
    # Learning data
    suggestion_acceptance: Dict[str, float] = field(default_factory=dict)
    error_recovery_patterns: Dict[str, str] = field(default_factory=dict)
    
    # Environment
    shell: str = ""
    editor: str = ""
    os_info: Dict[str, str] = field(default_factory=dict)


@dataclass
class SessionContext:
    """Current CLI session context."""
    session_id: str
    started_at: datetime
    commands_run: List[str] = field(default_factory=list)
    current_directory: str = ""
    environment_vars: Dict[str, str] = field(default_factory=dict)
    
    # Session state
    workflow_state: Dict[str, Any] = field(default_factory=dict)
    pending_operations: List[str] = field(default_factory=list)
    user_inputs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemContext:
    """System-level context."""
    cip_version: str
    python_version: str
    available_memory: int = 0
    cpu_count: int = 0
    disk_space: Dict[str, int] = field(default_factory=dict)
    
    # CIP-specific
    index_size: int = 0
    embedding_backend: str = ""
    feature_flags: Dict[str, bool] = field(default_factory=dict)


@dataclass
class UnifiedContext:
    """Unified context combining all context types."""
    repository: RepositoryContext
    user: UserContext
    session: SessionContext
    system: SystemContext
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_context_for_scope(self, scope: ContextScope) -> Any:
        """Get context for specific scope."""
        scope_map = {
            ContextScope.REPOSITORY: self.repository,
            ContextScope.SESSION: self.session,
            ContextScope.COMMAND: None,
            ContextScope.GLOBAL: self.user
        }
        return scope_map.get(scope)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'repository': self.repository.__dict__,
            'user': self.user.__dict__,
            'session': self.session.__dict__,
            'system': self.system.__dict__,
            'last_updated': self.last_updated.isoformat(),
            'version': self.version,
            'metadata': self.metadata
        }


class ContextProvider:
    """Base class for context providers."""
    
    def provide(self, root: str) -> Dict[str, Any]:
        """Provide context data."""
        raise NotImplementedError


class RepositoryProvider(ContextProvider):
    """Provide repository-specific context."""
    
    def provide(self, root: str) -> Dict[str, Any]:
        """Provide repository context data."""
        try:
            from repo_settings.detectors import detect_repo_type
            from cipkg.base import load_config
        except ImportError:
            # Fallback if repo_settings not available
            return self._fallback_provide(root)
        
        repo_type = detect_repo_type(root)
        config = load_config(root)
        
        return {
            'repo_type': repo_type,
            'repo_name': os.path.basename(root),
            'repo_metadata': {
                'has_readme': os.path.exists(os.path.join(root, 'README.md')),
                'has_license': os.path.exists(os.path.join(root, 'LICENSE')),
                'has_git': os.path.exists(os.path.join(root, '.git'))
            },
            'config': config,
            'profile_settings': config.get('profiles', {}).get(repo_type, {})
        }
    
    def _fallback_provide(self, root: str) -> Dict[str, Any]:
        """Fallback provider when repo_settings not available."""
        return {
            'repo_type': 'generic',
            'repo_name': os.path.basename(root),
            'repo_metadata': {
                'has_readme': os.path.exists(os.path.join(root, 'README.md')),
                'has_license': os.path.exists(os.path.join(root, 'LICENSE')),
                'has_git': os.path.exists(os.path.join(root, '.git'))
            },
            'config': {},
            'profile_settings': {}
        }


class GitProvider(ContextProvider):
    """Provide git-related context."""
    
    def provide(self, root: str) -> Dict[str, Any]:
        """Provide git context data."""
        import subprocess
        
        try:
            # Get current branch
            branch = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=root,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            
            # Get commit info
            commit_hash = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                cwd=root,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            
            # Get status
            status = subprocess.check_output(
                ['git', 'status', '--porcelain'],
                cwd=root,
                stderr=subprocess.DEVNULL,
                text=True
            )
            
            uncommitted_files = len([line for line in status.split('\n') if line.strip()])
            
            return {
                'git_state': {
                    'branch': branch,
                    'commit_hash': commit_hash,
                    'uncommitted_files': uncommitted_files,
                    'on_main': branch in ['main', 'master', 'develop'],
                    'is_clean': uncommitted_files == 0
                }
            }
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
                'git_state': {
                    'branch': 'unknown',
                    'commit_hash': None,
                    'uncommitted_files': 0,
                    'on_main': False,
                    'is_clean': True
                }
            }


class FileSystemProvider(ContextProvider):
    """Provide file system context."""
    
    def provide(self, root: str) -> Dict[str, Any]:
        """Provide file system context data."""
        file_count = 0
        recent_files = []
        directory_structure = {}
        
        try:
            import time
            
            # Count files and get recent files
            for dirpath, dirnames, filenames in os.walk(root):
                # Skip hidden directories and common exclusions
                dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git']]
                
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    file_count += 1
                    
                    # Track recent files (modified in last 24 hours)
                    try:
                        mtime = os.path.getmtime(file_path)
                        if time.time() - mtime < 86400:  # 24 hours
                            recent_files.append(file_path)
                    except (OSError, IOError):
                        pass
            
            # Build directory structure (simplified)
            directory_structure = self._build_directory_structure(root)
            
        except Exception as e:
            # Fallback on any error
            pass
        
        return {
            'file_count': file_count,
            'recent_files': recent_files[:20],  # Limit to 20 most recent
            'directory_structure': directory_structure
        }
    
    def _build_directory_structure(self, root: str, max_depth: int = 3) -> Dict[str, Any]:
        """Build simplified directory structure."""
        structure = {}
        
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                # Calculate depth
                rel_path = os.path.relpath(dirpath, root)
                depth = rel_path.count(os.sep) if rel_path != '.' else 0
                
                if depth > max_depth:
                    continue
                
                # Skip hidden directories
                dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git']]
                
                if rel_path == '.':
                    structure['files'] = filenames[:10]  # Limit files
                    structure['dirs'] = dirnames
                else:
                    parts = rel_path.split(os.sep)
                    current = structure
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = {
                        'files': filenames[:10],
                        'dirs': dirnames
                    }
        except Exception:
            pass
        
        return structure


class SystemProvider(ContextProvider):
    """Provide system-level context."""
    
    def provide(self, root: str) -> Dict[str, Any]:
        """Provide system context data."""
        import platform
        
        try:
            from cipkg import __version__ as cip_version
        except ImportError:
            cip_version = "unknown"
        
        system_info = {
            'cip_version': cip_version,
            'python_version': platform.python_version(),
            'available_memory': 0,
            'cpu_count': 0,
            'disk_space': {}
        }
        
        # Try to get more detailed system info
        try:
            import psutil
            system_info['available_memory'] = psutil.virtual_memory().available
            system_info['cpu_count'] = psutil.cpu_count()
            system_info['disk_space'] = {
                'total': psutil.disk_usage(root).total,
                'free': psutil.disk_usage(root).free,
                'used': psutil.disk_usage(root).used
            }
        except ImportError:
            # psutil not available, use basic info
            pass
        
        return system_info


class ContextCache:
    """Cache context data to avoid expensive recomputation."""
    
    def __init__(self, ttl: int = 300):  # 5 minutes default TTL
        self.cache: Dict[str, tuple] = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached context data."""
        if key not in self.cache:
            return None
        
        data, timestamp = self.cache[key]
        import time
        if time.time() - timestamp > self.ttl:
            # Cache expired
            del self.cache[key]
            return None
        
        return data
    
    def set(self, key: str, data: Any):
        """Cache context data."""
        import time
        self.cache[key] = (data, time.time())
    
    def invalidate(self, key: str = None):
        """Invalidate cache entry or entire cache."""
        if key:
            self.cache.pop(key, None)
        else:
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        import time
        return {
            'size': len(self.cache),
            'keys': list(self.cache.keys()),
            'oldest_entry': min((ts for _, ts in self.cache.values()), default=None),
            'newest_entry': max((ts for _, ts in self.cache.values()), default=None)
        }


class ContextSerializer:
    """Serialize and deserialize context data."""
    
    def __init__(self, root: str):
        self.root = root
        self.context_dir = self._get_context_dir()
    
    def _get_context_dir(self) -> str:
        """Get context storage directory."""
        from cipkg.base import data_dir
        
        context_dir = os.path.join(data_dir(self.root), "context")
        os.makedirs(context_dir, exist_ok=True)
        return context_dir
    
    def serialize(self, context: UnifiedContext):
        """Serialize context to disk."""
        context_file = os.path.join(self.context_dir, "current_context.json")
        
        with open(context_file, 'w') as f:
            json.dump(context.to_dict(), f, indent=2, default=str)
    
    def deserialize(self) -> Optional[UnifiedContext]:
        """Deserialize context from disk."""
        context_file = os.path.join(self.context_dir, "current_context.json")
        
        if not os.path.exists(context_file):
            return None
        
        with open(context_file, 'r') as f:
            data = json.load(f)
        
        # Reconstruct context objects
        return self._reconstruct_context(data)
    
    def _reconstruct_context(self, data: Dict[str, Any]) -> UnifiedContext:
        """Reconstruct UnifiedContext from dictionary."""
        repository = RepositoryContext(**data['repository'])
        user = UserContext(**data['user'])
        session = SessionContext(**data['session'])
        system = SystemContext(**data['system'])
        
        return UnifiedContext(
            repository=repository,
            user=user,
            session=session,
            system=system,
            last_updated=datetime.fromisoformat(data['last_updated']),
            version=data['version'],
            metadata=data['metadata']
        )


class ContextBuilder:
    """Build comprehensive context from multiple sources."""
    
    def __init__(self, root: str):
        self.root = root
        self.providers = [
            RepositoryProvider(),
            GitProvider(),
            FileSystemProvider(),
            SystemProvider()
        ]
    
    def build(self, include_user: bool = True) -> UnifiedContext:
        """Build complete unified context."""
        import uuid
        
        # Build repository context
        repository = self._build_repository_context()
        
        # Build system context
        system = self._build_system_context()
        
        # Build session context
        session = self._build_session_context()
        
        # Build user context (if enabled)
        if include_user:
            user = self._build_user_context()
        else:
            user = UserContext(user_id="anonymous")
        
        return UnifiedContext(
            repository=repository,
            user=user,
            session=session,
            system=system
        )
    
    def _build_repository_context(self) -> RepositoryContext:
        """Build repository context from providers."""
        context_data = {}
        
        for provider in self.providers:
            try:
                provider_data = provider.provide(self.root)
                context_data.update(provider_data)
            except Exception as e:
                # Log error but continue with other providers
                print(f"Warning: Provider {provider.__class__.__name__} failed: {e}")
        
        return RepositoryContext(
            root=self.root,
            repo_type=context_data.get('repo_type', 'generic'),
            repo_name=context_data.get('repo_name', 'unknown'),
            repo_metadata=context_data.get('repo_metadata', {}),
            health_score=context_data.get('health_score'),
            index_status=context_data.get('index_status'),
            git_state=context_data.get('git_state'),
            languages=context_data.get('languages', []),
            frameworks=context_data.get('frameworks', []),
            tools=context_data.get('tools', []),
            dependencies=context_data.get('dependencies', {}),
            file_count=context_data.get('file_count', 0),
            directory_structure=context_data.get('directory_structure', {}),
            recent_files=context_data.get('recent_files', []),
            config=context_data.get('config', {}),
            profile_settings=context_data.get('profile_settings', {})
        )
    
    def _build_system_context(self) -> SystemContext:
        """Build system context."""
        system_provider = SystemProvider()
        system_data = system_provider.provide(self.root)
        
        return SystemContext(
            cip_version=system_data.get('cip_version', 'unknown'),
            python_version=system_data.get('python_version', 'unknown'),
            available_memory=system_data.get('available_memory', 0),
            cpu_count=system_data.get('cpu_count', 0),
            disk_space=system_data.get('disk_space', {})
        )
    
    def _build_session_context(self) -> SessionContext:
        """Build session context."""
        import uuid
        
        return SessionContext(
            session_id=str(uuid.uuid4()),
            started_at=datetime.now(),
            current_directory=os.getcwd(),
            environment_vars=dict(os.environ)
        )
    
    def _build_user_context(self) -> UserContext:
        """Build user context from stored patterns."""
        from cipkg.base import data_dir
        
        user_data_file = os.path.join(data_dir(self.root), "user_context.json")
        
        if os.path.exists(user_data_file):
            try:
                with open(user_data_file, 'r') as f:
                    user_data = json.load(f)
                
                return UserContext(
                    user_id=user_data.get('user_id', 'default'),
                    preferences=user_data.get('preferences', {}),
                    command_history=user_data.get('command_history', []),
                    workflow_preferences=user_data.get('workflow_preferences', {}),
                    time_patterns=user_data.get('time_patterns', {}),
                    suggestion_acceptance=user_data.get('suggestion_acceptance', {}),
                    error_recovery_patterns=user_data.get('error_recovery_patterns', {}),
                    shell=user_data.get('shell', ''),
                    editor=user_data.get('editor', ''),
                    os_info=user_data.get('os_info', {})
                )
            except (json.JSONDecodeError, IOError):
                pass
        
        return UserContext(user_id='default')


class ContextManager:
    """Central context management system."""
    
    def __init__(self, root: str):
        self.root = root
        self.builder = ContextBuilder(root)
        self.cache = ContextCache(ttl=300)
        self.serializer = ContextSerializer(root)
        self.current_context: Optional[UnifiedContext] = None
    
    def get_context(self, force_refresh: bool = False) -> UnifiedContext:
        """Get current context, with caching."""
        cache_key = f"context_{self.root}"
        
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        # Build fresh context
        context = self.builder.build()
        self.current_context = context
        self.cache.set(cache_key, context)
        
        return context
    
    def update_context(self, updates: Dict[str, Any]):
        """Update context with incremental changes."""
        if not self.current_context:
            self.current_context = self.get_context()
        
        # Apply updates to appropriate context sections
        for scope, data in updates.items():
            if hasattr(self.current_context, scope):
                current = getattr(self.current_context, scope)
                for key, value in data.items():
                    if hasattr(current, key):
                        setattr(current, key, value)
        
        # Invalidate cache
        self.cache.invalidate(f"context_{self.root}")
    
    def get_repository_context(self) -> RepositoryContext:
        """Get repository-specific context."""
        context = self.get_context()
        return context.repository
    
    def get_user_context(self) -> UserContext:
        """Get user-specific context."""
        context = self.get_context()
        return context.user
    
    def save_context(self):
        """Persist current context to disk."""
        if self.current_context:
            self.serializer.serialize(self.current_context)
    
    def load_context(self) -> Optional[UnifiedContext]:
        """Load persisted context from disk."""
        context = self.serializer.deserialize()
        if context:
            self.current_context = context
            self.cache.set(f"context_{self.root}", context)
        return context
    
    def invalidate_cache(self):
        """Invalidate all cached context data."""
        self.cache.invalidate()
