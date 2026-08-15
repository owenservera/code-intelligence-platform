"""
Command Adaptation System for CIP CLI v2.0

This module provides context-aware command adaptation, allowing existing
CLI commands to dynamically modify their behavior based on repository state
and user patterns.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import os


class AdaptationType(Enum):
    """Types of command adaptations."""
    FLAG_INJECTION = "flag_injection"
    ARGUMENT_MODIFICATION = "argument_modification"
    COMMAND_SUBSTITUTION = "command_substitution"
    PRE_EXECUTION_HOOK = "pre_execution_hook"
    POST_EXECUTION_HOOK = "post_execution_hook"


@dataclass
class Adaptation:
    """Single command adaptation."""
    adaptation_type: AdaptationType
    description: str
    condition: Callable[[Dict[str, Any]], bool]
    transformation: Callable[[List[str]], List[str]]
    priority: int = 0
    metadata: Dict[str, Any] = None


class CommandAdapter(ABC):
    """Base class for command adapters."""
    
    def __init__(self, root: str, config: Dict[str, Any]):
        self.root = root
        self.config = config
        self.adaptations: List[Adaptation] = []
        self._register_adaptations()
    
    @abstractmethod
    def _register_adaptations(self):
        """Register command-specific adaptations."""
        pass
    
    def adapt(self, args: List[str], context: Dict[str, Any]) -> List[str]:
        """Apply adaptations to command arguments."""
        adapted_args = args.copy()
        
        # Sort adaptations by priority
        sorted_adaptations = sorted(self.adaptations, key=lambda a: a.priority, reverse=True)
        
        for adaptation in sorted_adaptations:
            try:
                if adaptation.condition(context):
                    adapted_args = adaptation.transformation(adapted_args)
            except Exception as e:
                # Log error but continue with other adaptations
                print(f"Warning: Adaptation failed: {e}")
        
        return adapted_args
    
    def get_adaptation_info(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get information about applicable adaptations."""
        applicable = []
        
        for adaptation in self.adaptations:
            if adaptation.condition(context):
                applicable.append({
                    'type': adaptation.adaptation_type.value,
                    'description': adaptation.description,
                    'priority': adaptation.priority
                })
        
        return applicable


class AuditAdapter(CommandAdapter):
    """Adapter for the audit command."""
    
    def _register_adaptations(self):
        """Register audit command adaptations."""
        # Auto-add --diff flag when there are uncommitted changes
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.FLAG_INJECTION,
            description="Auto-add --diff flag for uncommitted changes",
            condition=lambda ctx: self._has_uncommitted_changes(ctx),
            transformation=lambda args: self._inject_flag(args, '--diff'),
            priority=10
        ))
        
        # Auto-add --framework flag for known frameworks
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.FLAG_INJECTION,
            description="Auto-add --framework flag for Next.js projects",
            condition=lambda ctx: self._is_nextjs_project(ctx),
            transformation=lambda args: self._inject_flag(args, '--framework', 'nextjs'),
            priority=8
        ))
        
        # Auto-add --comprehensive flag for large changes
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.FLAG_INJECTION,
            description="Auto-add --comprehensive flag for large changes",
            condition=lambda ctx: self._has_large_changes(ctx),
            transformation=lambda args: self._inject_flag(args, '--comprehensive'),
            priority=6
        ))
    
    def _has_uncommitted_changes(self, context: Dict[str, Any]) -> bool:
        """Check if there are uncommitted changes."""
        git_state = context.get('git_state', {})
        return git_state.get('uncommitted_files', 0) > 0
    
    def _is_nextjs_project(self, context: Dict[str, Any]) -> bool:
        """Check if this is a Next.js project."""
        repo_type = context.get('repo_type', '')
        return repo_type == 'nextjs-app'
    
    def _has_large_changes(self, context: Dict[str, Any]) -> bool:
        """Check if there are large changes."""
        git_state = context.get('git_state', {})
        return git_state.get('uncommitted_files', 0) > 5
    
    def _inject_flag(self, args: List[str], flag: str, value: str = None) -> List[str]:
        """Inject a flag into arguments."""
        if flag in args:
            return args  # Flag already present
        
        if value:
            return args + [flag, value]
        return args + [flag]


class SearchAdapter(CommandAdapter):
    """Adapter for the search command."""
    
    def _register_adaptations(self):
        """Register search command adaptations."""
        # Auto-set context path to current directory
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.ARGUMENT_MODIFICATION,
            description="Auto-set search context to current directory",
            condition=lambda ctx: self._has_current_directory(ctx),
            transformation=lambda args: self._set_context_path(args),
            priority=10
        ))
        
        # Auto-filter by file types for known projects
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.FLAG_INJECTION,
            description="Auto-filter by Python files for Python projects",
            condition=lambda ctx: self._is_python_project(ctx),
            transformation=lambda args: self._inject_flag(args, '--file-types', 'py'),
            priority=8
        ))
        
        # Boost recent files in results
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.FLAG_INJECTION,
            description="Boost recent files in search results",
            condition=lambda ctx: self._has_recent_files(ctx),
            transformation=lambda args: self._inject_flag(args, '--boost-recent'),
            priority=6
        ))
    
    def _has_current_directory(self, context: Dict[str, Any]) -> bool:
        """Check if current directory is available."""
        return bool(context.get('current_directory'))
    
    def _is_python_project(self, context: Dict[str, Any]) -> bool:
        """Check if this is a Python project."""
        repo_type = context.get('repo_type', '')
        return repo_type == 'python-lib'
    
    def _has_recent_files(self, context: Dict[str, Any]) -> bool:
        """Check if there are recent files."""
        recent_files = context.get('recent_files', [])
        return len(recent_files) > 0
    
    def _set_context_path(self, args: List[str]) -> List[str]:
        """Set context path to current directory."""
        # This would add --context-path flag with current directory
        return args  # Simplified for now
    
    def _inject_flag(self, args: List[str], flag: str, value: str = None) -> List[str]:
        """Inject a flag into arguments."""
        if flag in args:
            return args  # Flag already present
        
        if value:
            return args + [flag, value]
        return args + [flag]


class IndexAdapter(CommandAdapter):
    """Adapter for the index command."""
    
    def _register_adaptations(self):
        """Register index command adaptations."""
        # Auto-add --force flag for stale index
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.FLAG_INJECTION,
            description="Auto-add --force flag for stale index",
            condition=lambda ctx: self._is_index_stale(ctx),
            transformation=lambda args: self._inject_flag(args, '--force'),
            priority=10
        ))
        
        # Auto-add --embed flag for missing embeddings
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.FLAG_INJECTION,
            description="Auto-add --embed flag for missing embeddings",
            condition=lambda ctx: self._has_missing_embeddings(ctx),
            transformation=lambda args: self._inject_flag(args, '--embed'),
            priority=8
        ))
        
        # Auto-add --parallel flag for large repositories
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.FLAG_INJECTION,
            description="Auto-add --parallel flag for large repositories",
            condition=lambda ctx: self._is_large_repository(ctx),
            transformation=lambda args: self._inject_flag(args, '--parallel'),
            priority=6
        ))
    
    def _is_index_stale(self, context: Dict[str, Any]) -> bool:
        """Check if index is stale."""
        index_status = context.get('index_status', {})
        return index_status.get('stale', False)
    
    def _has_missing_embeddings(self, context: Dict[str, Any]) -> bool:
        """Check if there are missing embeddings."""
        index_status = context.get('index_status', {})
        coverage = index_status.get('embedding_coverage', 100)
        return coverage < 80
    
    def _is_large_repository(self, context: Dict[str, Any]) -> bool:
        """Check if repository is large."""
        file_count = context.get('file_count', 0)
        return file_count > 1000
    
    def _inject_flag(self, args: List[str], flag: str, value: str = None) -> List[str]:
        """Inject a flag into arguments."""
        if flag in args:
            return args  # Flag already present
        
        if value:
            return args + [flag, value]
        return args + [flag]


class SyncAdapter(CommandAdapter):
    """Adapter for the sync command."""
    
    def _register_adaptations(self):
        """Register sync command adaptations."""
        # Auto-add --include-uncommitted flag when there are uncommitted changes
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.FLAG_INJECTION,
            description="Auto-add --include-uncommitted flag",
            condition=lambda ctx: self._has_uncommitted_changes(ctx),
            transformation=lambda args: self._inject_flag(args, '--include-uncommitted'),
            priority=10
        ))
        
        # Auto-add --verbose flag for debugging
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.FLAG_INJECTION,
            description="Auto-add --verbose flag for debugging",
            condition=lambda ctx: self._is_debug_mode(ctx),
            transformation=lambda args: self._inject_flag(args, '--verbose'),
            priority=5
        ))
    
    def _has_uncommitted_changes(self, context: Dict[str, Any]) -> bool:
        """Check if there are uncommitted changes."""
        git_state = context.get('git_state', {})
        return git_state.get('uncommitted_files', 0) > 0
    
    def _is_debug_mode(self, context: Dict[str, Any]) -> bool:
        """Check if debug mode is enabled."""
        return context.get('debug_mode', False)
    
    def _inject_flag(self, args: List[str], flag: str, value: str = None) -> List[str]:
        """Inject a flag into arguments."""
        if flag in args:
            return args  # Flag already present
        
        if value:
            return args + [flag, value]
        return args + [flag]


class RoutesAdapter(CommandAdapter):
    """Adapter for the routes command."""
    
    def _register_adaptations(self):
        """Register routes command adaptations."""
        # Auto-add --graph flag for visualization
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.FLAG_INJECTION,
            description="Auto-add --graph flag for route visualization",
            condition=lambda ctx: self._is_nextjs_project(ctx),
            transformation=lambda args: self._inject_flag(args, '--graph'),
            priority=10
        ))
        
        # Auto-add --check flag for integrity checking
        self.adaptations.append(Adaptation(
            adaptation_type=AdaptationType.FLAG_INJECTION,
            description="Auto-add --check flag for integrity checking",
            condition=lambda ctx: self._has_uncommitted_changes(ctx),
            transformation=lambda args: self._inject_flag(args, '--check'),
            priority=8
        ))
    
    def _is_nextjs_project(self, context: Dict[str, Any]) -> bool:
        """Check if this is a Next.js project."""
        repo_type = context.get('repo_type', '')
        return repo_type == 'nextjs-app'
    
    def _has_uncommitted_changes(self, context: Dict[str, Any]) -> bool:
        """Check if there are uncommitted changes."""
        git_state = context.get('git_state', {})
        return git_state.get('uncommitted_files', 0) > 0
    
    def _inject_flag(self, args: List[str], flag: str, value: str = None) -> List[str]:
        """Inject a flag into arguments."""
        if flag in args:
            return args  # Flag already present
        
        if value:
            return args + [flag, value]
        return args + [flag]


class AdapterFactory:
    """Factory for creating command adapters."""
    
    @staticmethod
    def create_adapter(command: str, root: str, config: Dict[str, Any]) -> Optional[CommandAdapter]:
        """Create appropriate adapter for command."""
        adapter_map = {
            'audit': AuditAdapter,
            'search': SearchAdapter,
            'index': IndexAdapter,
            'sync': SyncAdapter,
            'routes': RoutesAdapter
        }
        
        adapter_class = adapter_map.get(command.lower())
        if adapter_class:
            return adapter_class(root, config)
        
        return None


class ContextAwareCommand:
    """Wrapper for context-aware command execution."""
    
    def __init__(self, root: str, config: Dict[str, Any]):
        self.root = root
        self.config = config
        self.adaptation_enabled = config.get('command_adaptation', {}).get('enabled', True)
        self.show_adaptations = config.get('command_adaptation', {}).get('show_adaptations', True)
        self.require_confirmation = config.get('command_adaptation', {}).get('require_confirmation', False)
    
    def execute(self, command: str, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute command with context-aware adaptations."""
        original_args = args.copy()
        
        if not self.adaptation_enabled:
            return self._execute_original(command, args)
        
        # Get adapter for command
        adapter = AdapterFactory.create_adapter(command, self.root, self.config)
        
        if not adapter:
            return self._execute_original(command, args)
        
        # Get applicable adaptations
        adaptation_info = adapter.get_adaptation_info(context)
        
        if adaptation_info:
            # Show adaptations if enabled
            if self.show_adaptations:
                print(f"🔧 Applying {len(adaptation_info)} adaptation(s) to '{command}':")
                for info in adaptation_info:
                    print(f"  • {info['description']} (priority: {info['priority']})")
            
            # Require confirmation if enabled
            if self.require_confirmation:
                if not self._confirm_adaptations(adaptation_info):
                    print("❌ Adaptations cancelled by user")
                    return self._execute_original(command, args)
        
        # Apply adaptations
        adapted_args = adapter.adapt(args, context)
        
        # Execute with adapted arguments
        result = self._execute_original(command, adapted_args)
        
        # Record adaptation for learning
        self._record_adaptation(command, original_args, adapted_args, adaptation_info)
        
        return result
    
    def _execute_original(self, command: str, args: List[str]) -> Dict[str, Any]:
        """Execute original command without adaptations."""
        # This would call the actual command implementation
        # For now, return a placeholder result
        return {
            'command': command,
            'args': args,
            'adapted': False,
            'success': True
        }
    
    def _confirm_adaptations(self, adaptation_info: List[Dict[str, str]]) -> bool:
        """Confirm adaptations with user."""
        print("Apply these adaptations? [Y/n]: ", end='')
        response = input().strip().lower()
        return response in ['', 'y', 'yes']
    
    def _record_adaptation(self, command: str, original_args: List[str], 
                          adapted_args: List[str], adaptation_info: List[Dict[str, str]]):
        """Record adaptation for learning system."""
        try:
            from cipkg.learning_system import record_user_action
            
            record_user_action(
                root=self.root,
                action_type='command',
                user_id='default',
                repo_id=os.path.basename(self.root),
                command=command,
                arguments={'original': original_args, 'adapted': adapted_args},
                context={'adaptations': adaptation_info},
                success=True
            )
        except Exception:
            # Don't fail if learning system is unavailable
            pass


def adapt_command(root: str, command: str, args: List[str], 
                 context: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Convenience function to adapt and execute a command."""
    if config is None:
        from cipkg.base import load_config
        config = load_config(root)
    
    context_aware = ContextAwareCommand(root, config)
    return context_aware.execute(command, args, context)


def get_adaptation_info(root: str, command: str, context: Dict[str, Any], 
                      config: Dict[str, Any] = None) -> List[Dict[str, str]]:
    """Get information about applicable adaptations for a command."""
    if config is None:
        from cipkg.base import load_config
        config = load_config(root)
    
    adapter = AdapterFactory.create_adapter(command, root, config)
    
    if not adapter:
        return []
    
    return adapter.get_adaptation_info(context)
