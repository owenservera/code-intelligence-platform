"""
Intelligent Command Execution Layer for CIP Terminal Dashboard

This module provides the core execution engine that integrates command registry,
learning system, suggestion engine, and workflow engine for intelligent command
execution with context awareness, progress tracking, and error recovery.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time
import queue


class ExecutionStatus(Enum):
    """Status of command execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ExecutionContext:
    """Execution context with repository and user information."""
    root: str
    user_id: str = "default"
    repo_type: str = "unknown"
    file_count: int = 0
    index_status: str = "unknown"
    git_state: Dict[str, Any] = field(default_factory=dict)
    health_score: int = 100
    recent_files: List[str] = field(default_factory=list)
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of command execution."""
    status: ExecutionStatus
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    adaptations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressUpdate:
    """Progress update for long-running operations."""
    phase: str
    current: int
    total: int
    message: str
    percentage: float = 0.0
    timestamp: float = field(default_factory=time.time)


class IntelligentCommandExecutor:
    """Intelligent command execution with full system integration."""
    
    def __init__(self, root: str):
        self.root = root
        self.command_registry = self._get_command_registry()
        
        # Try to initialize optional components gracefully
        try:
            self.context_manager = self._get_context_manager()
        except Exception:
            self.context_manager = None
        
        try:
            self.learning_system = self._get_learning_system()
        except Exception:
            self.learning_system = None
        
        try:
            self.suggestion_engine = self._get_suggestion_engine()
        except Exception:
            self.suggestion_engine = None
        
        try:
            self.workflow_executor = self._get_workflow_executor()
        except Exception:
            self.workflow_executor = None
        
        # Progress tracking
        self.progress_queue = queue.Queue()
        self.current_execution = None
        
        # User identification
        self.user_id = self._get_user_id()
    
    def _get_command_registry(self):
        """Get command registry instance."""
        from .command_registry import get_command_registry
        return get_command_registry()
    
    def _get_context_manager(self):
        """Get context manager instance."""
        try:
            from .context_manager import ContextManager
            return ContextManager(self.root)
        except Exception:
            # Return None if context manager fails to initialize
            return None
    
    def _get_learning_system(self):
        """Get learning system instance."""
        try:
            from .learning_system import LearningSystem
            return LearningSystem(self.root)
        except Exception:
            # Return None if learning system fails to initialize
            return None
    
    def _get_suggestion_engine(self):
        """Get suggestion engine instance."""
        from .suggestion_engine import SuggestionEngine
        from .base import load_config
        return SuggestionEngine(self.root, load_config(self.root))
    
    def _get_workflow_executor(self):
        """Get workflow executor instance."""
        try:
            from .workflow_engine import WorkflowExecutor
            from .base import load_config
            return WorkflowExecutor(self.root, load_config(self.root))
        except Exception:
            # Return None if workflow executor fails to initialize
            return None
    
    def _get_user_id(self) -> str:
        """Get or generate user ID."""
        import os
        import hashlib
        
        # Try to get from environment
        user_id = os.environ.get('CIP_USER_ID')
        if user_id:
            return user_id
        
        # Generate based on system user
        try:
            import getpass
            system_user = getpass.getuser()
            user_hash = hashlib.md5(system_user.encode()).hexdigest()[:8]
            return f"user_{user_hash}"
        except Exception:
            return "default_user"
    
    def execute_command(self, command: str, args: Dict[str, Any] = None, 
                      context: ExecutionContext = None) -> ExecutionResult:
        """Execute a command with full intelligence integration."""
        
        if args is None:
            args = {}
        
        if context is None:
            context = self._build_execution_context()
        
        # Get command card
        command_card = self.command_registry.get(command)
        if not command_card:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=f"Command not found: {command}"
            )
        
        # Record command start for learning
        self._record_command_start(command, args, context)
        
        # Validate preconditions
        validation = self._validate_preconditions(command_card, args, context)
        if not validation['valid']:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=f"Preconditions failed: {validation['error']}",
                warnings=validation.get('warnings', [])
            )
        
        # Adapt command based on context
        adapted_args, adaptations = self._adapt_command(command_card, args, context)
        
        # Set up progress tracking for long-running commands
        progress_tracker = None
        if command_card.long_running:
            progress_tracker = self._setup_progress_tracking(command)
        
        # Execute command
        start_time = time.time()
        try:
            if progress_tracker:
                self._emit_progress_update(ProgressUpdate(
                    phase="starting",
                    current=0,
                    total=100,
                    message=f"Starting {command_card.label}..."
                ))
            
            # Execute the command
            result = command_card.handler(self.root, adapted_args)
            
            execution_time = time.time() - start_time
            
            # Record successful execution for learning
            self._record_command_success(command, args, context, execution_time)
            
            # Generate follow-up suggestions
            suggestions = self._generate_follow_up_suggestions(command, context, result)
            
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                output=str(result) if result else None,
                execution_time=execution_time,
                adaptations=adaptations,
                suggestions=suggestions,
                metadata={'raw_result': result}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)
            
            # Record error for learning
            self._record_command_error(command, args, context, error_message)
            
            # Attempt error recovery
            recovery_result = self._attempt_error_recovery(
                command_card, args, context, e
            )
            
            if recovery_result['recovered']:
                return ExecutionResult(
                    status=ExecutionStatus.COMPLETED,
                    output=recovery_result['output'],
                    execution_time=execution_time,
                    adaptations=adaptations + [f"Applied recovery: {recovery_result['method']}"],
                    warnings=[f"Error recovered: {error_message}"]
                )
            else:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    error=error_message,
                    execution_time=execution_time,
                    adaptations=adaptations,
                    suggestions=recovery_result.get('suggestions', [])
                )
        
        finally:
            if progress_tracker:
                self._cleanup_progress_tracking()
    
    def _build_execution_context(self) -> ExecutionContext:
        """Build execution context from current repository state."""
        try:
            # Get unified context from context manager
            if self.context_manager:
                unified_context = self.context_manager.get_context()
            else:
                # Create minimal context if context manager unavailable
                class MinimalContext:
                    repository = type('obj', (object,), {
                        'repo_type': 'unknown',
                        'file_count': 0,
                        'index_status': 'unknown',
                        'recent_files': []
                    })
                unified_context = MinimalContext()
            
            # Get git state
            git_state = self._get_git_state()
            
            # Get health score
            health_score = self._get_health_score()
            
            return ExecutionContext(
                root=self.root,
                user_id=self.user_id,
                repo_type=unified_context.repository.repo_type,
                file_count=unified_context.repository.file_count,
                index_status=unified_context.repository.index_status,
                git_state=git_state,
                health_score=health_score,
                recent_files=unified_context.repository.recent_files,
                session_id=self._get_session_id()
            )
        except Exception:
            # Return minimal context on error
            return ExecutionContext(
                root=self.root,
                user_id=self.user_id,
                repo_type="unknown",
                file_count=0,
                index_status="unknown",
                git_state={},
                health_score=100
            )
    
    def _get_git_state(self) -> Dict[str, Any]:
        """Get current git state."""
        import subprocess
        
        try:
            # Get current branch
            branch = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=self.root,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            
            # Get uncommitted files
            uncommitted = subprocess.check_output(
                ['git', 'status', '--porcelain'],
                cwd=self.root,
                stderr=subprocess.DEVNULL,
                text=True
            )
            uncommitted_count = len([line for line in uncommitted.split('\n') if line.strip()])
            
            return {
                'branch': branch,
                'on_main': branch in ['main', 'master', 'develop'],
                'uncommitted_files': uncommitted_count
            }
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
                'branch': 'unknown',
                'on_main': False,
                'uncommitted_files': 0
            }
    
    def _get_health_score(self) -> int:
        """Get repository health score."""
        try:
            from . import gapfill
            health = gapfill.score(self.root)
            return health.get('score', 100)
        except Exception:
            return 100
    
    def _get_session_id(self) -> str:
        """Get or create session ID."""
        from .session import get_active_session
        session = get_active_session(self.root)
        return session.get('session_id') if session else None
    
    def _validate_preconditions(self, command_card, args: Dict[str, Any], 
                               context: ExecutionContext) -> Dict[str, Any]:
        """Validate command preconditions."""
        warnings = []
        
        # Check if repository is initialized
        if context.file_count == 0 and command_card.category.name != "repository":
            return {
                'valid': False,
                'error': 'Repository not initialized. Run "cip init" first.',
                'warnings': warnings
            }
        
        # Check if index is stale for commands that need fresh data
        if context.index_status == 'stale' and command_card.category.name in ['search', 'quality']:
            warnings.append('Index is stale. Consider running "cip sync" for better results.')
        
        # Check for uncommitted changes before critical operations
        if context.git_state.get('uncommitted_files', 0) > 0 and command_card.requires_confirmation:
            warnings.append(f'{context.git_state["uncommitted_files"]} uncommitted files detected.')
        
        # Validate required parameters
        for param in command_card.parameters:
            if param.required and param.name not in args:
                return {
                    'valid': False,
                    'error': f'Missing required parameter: {param.name}',
                    'warnings': warnings
                }
        
        return {'valid': True, 'warnings': warnings}
    
    def _adapt_command(self, command_card, args: Dict[str, Any], 
                      context: ExecutionContext) -> tuple:
        """Adapt command parameters based on context."""
        adapted_args = args.copy()
        adaptations = []
        
        # Repository size adaptation
        if context.file_count > 1000:
            if 'batch_size' in adapted_args:
                original_batch = adapted_args['batch_size']
                adapted_args['batch_size'] = min(original_batch * 2, 256)
                adaptations.append(f'Increased batch size for large repo: {original_batch} -> {adapted_args["batch_size"]}')
            
            if 'parallel' not in adapted_args:
                adapted_args['parallel'] = True
                adaptations.append('Enabled parallel processing for large repo')
        
        # Index status adaptation
        if context.index_status == 'stale' and command_card.category.name == 'search':
            adapted_args['force_refresh'] = True
            adaptations.append('Forced refresh due to stale index')
        
        # Git state adaptation
        if context.git_state.get('uncommitted_files', 0) > 5:
            if command_card.category.name == 'quality':
                adapted_args['include_uncommitted'] = True
                adaptations.append('Including uncommitted files in analysis')
        
        # User pattern adaptation
        user_patterns = self.learning_system.get_user_patterns()
        if command_card.command in user_patterns.get('frequent_commands', {}):
            adapted_args['optimized'] = True
            adaptations.append('Applied user-specific optimizations')
        
        return adapted_args, adaptations
    
    def _setup_progress_tracking(self, command: str):
        """Set up progress tracking for long-running commands."""
        def progress_updater(phase: str, current: int, total: int, message: str):
            self._emit_progress_update(ProgressUpdate(
                phase=phase,
                current=current,
                total=total,
                message=message,
                percentage=(current / total * 100) if total else 0
            ))
        
        return progress_updater
    
    def _emit_progress_update(self, update: ProgressUpdate):
        """Emit progress update to UI."""
        self.progress_queue.put(update)
    
    def _cleanup_progress_tracking(self):
        """Clean up progress tracking."""
        # Send completion signal
        self._emit_progress_update(ProgressUpdate(
            phase="complete",
            current=100,
            total=100,
            message="Operation complete",
            percentage=100.0
        ))
    
    def _record_command_start(self, command: str, args: Dict[str, Any], 
                            context: ExecutionContext):
        """Record command start for learning."""
        try:
            if self.learning_system:
                self.learning_system.record_command(
                    user_id=self.user_id,
                    repo_id=self._get_repo_id(),
                    command=command,
                    arguments=args,
                    context={
                        'repo_type': context.repo_type,
                        'file_count': context.file_count,
                        'index_status': context.index_status,
                        'git_state': context.git_state,
                        'health_score': context.health_score
                    },
                    success=False,  # Will update on completion
                    execution_time=0.0
                )
        except Exception:
            pass  # Don't fail if learning is unavailable
    
    def _record_command_success(self, command: str, args: Dict[str, Any],
                               context: ExecutionContext, execution_time: float):
        """Record successful command execution for learning."""
        try:
            if self.learning_system:
                self.learning_system.record_command(
                    user_id=self.user_id,
                    repo_id=self._get_repo_id(),
                    command=command,
                    arguments=args,
                    context={
                        'repo_type': context.repo_type,
                        'file_count': context.file_count,
                        'index_status': context.index_status,
                        'git_state': context.git_state,
                        'health_score': context.health_score
                    },
                    success=True,
                    execution_time=execution_time
                )
        except Exception:
            pass
    
    def _record_command_error(self, command: str, args: Dict[str, Any],
                             context: ExecutionContext, error_message: str):
        """Record command error for learning."""
        try:
            if self.learning_system:
                self.learning_system.record_command(
                    user_id=self.user_id,
                    repo_id=self._get_repo_id(),
                    command=command,
                    arguments=args,
                    context={
                        'repo_type': context.repo_type,
                        'file_count': context.file_count,
                        'index_status': context.index_status,
                        'git_state': context.git_state,
                        'health_score': context.health_score
                    },
                    success=False,
                    execution_time=0.0,
                    error=error_message
                )
        except Exception:
            pass
    
    def _get_repo_id(self) -> str:
        """Get repository identifier."""
        import os
        import hashlib
        
        repo_path = os.path.abspath(self.root)
        return hashlib.md5(repo_path.encode()).hexdigest()[:12]
    
    def _generate_follow_up_suggestions(self, command: str, context: ExecutionContext,
                                       result: Any) -> List[str]:
        """Generate intelligent follow-up suggestions."""
        suggestions = []
        
        try:
            if self.suggestion_engine and self.context_manager:
                # Get current context
                unified_context = self.context_manager.get_context()
                
                # Generate suggestions from suggestion engine
                engine_suggestions = self.suggestion_engine.generate_suggestions(
                    unified_context, max_suggestions=3
                )
                
                for suggestion in engine_suggestions:
                    if suggestion.action != f"cip {command}":  # Don't suggest the same command
                        suggestions.append(f"{suggestion.action}: {suggestion.reason}")
        except Exception:
            pass
        
        # Fallback suggestions based on command
        if not suggestions:
            if command == 'audit':
                suggestions.append("cip findings: Review audit findings in detail")
            elif command == 'sync':
                suggestions.append("cip analyze: Check repository health after sync")
            elif command == 'search':
                suggestions.append("cip context: Get detailed context for search results")
        
        return suggestions
    
    def _attempt_error_recovery(self, command_card, args: Dict[str, Any],
                              context: ExecutionContext, error: Exception) -> Dict[str, Any]:
        """Attempt intelligent error recovery."""
        error_type = type(error).__name__
        error_message = str(error)
        
        recovery_attempts = []
        
        # Check for index corruption
        if 'index' in error_message.lower() or 'database' in error_message.lower():
            recovery_attempts.append({
                'method': 'rebuild_index',
                'action': lambda: self.execute_command('rebuild', {}, context),
                'description': 'Rebuild corrupted index'
            })
        
        # Check for permission issues
        if 'permission' in error_message.lower() or 'access' in error_message.lower():
            recovery_attempts.append({
                'method': 'check_permissions',
                'action': lambda: {'suggestions': ['Check file permissions and try again']},
                'description': 'Check file permissions'
            })
        
        # Check for dependency issues
        if 'import' in error_message.lower() or 'module' in error_message.lower():
            recovery_attempts.append({
                'method': 'check_dependencies',
                'action': lambda: self.execute_command('deps', {}, context),
                'description': 'Check dependency issues'
            })
        
        # Try recovery attempts
        for attempt in recovery_attempts:
            try:
                result = attempt['action']()
                if result and result.status == ExecutionStatus.COMPLETED:
                    return {
                        'recovered': True,
                        'method': attempt['method'],
                        'output': result.output
                    }
            except Exception:
                continue
        
        # All recovery attempts failed
        suggestions = [
            f"Error type: {error_type}",
            f"Error message: {error_message}",
            "Try running 'cip doctor' to diagnose system issues"
        ]
        
        # Add specific suggestions based on error
        if 'index' in error_message.lower():
            suggestions.append("Consider running 'cip rebuild' to fix index issues")
        elif 'git' in error_message.lower():
            suggestions.append("Check git repository status and permissions")
        
        return {
            'recovered': False,
            'suggestions': suggestions
        }
    
    def get_progress_updates(self) -> List[ProgressUpdate]:
        """Get all pending progress updates."""
        updates = []
        try:
            while True:
                updates.append(self.progress_queue.get_nowait())
        except queue.Empty:
            pass
        return updates
    
    def get_intelligent_suggestions(self, max_suggestions: int = 5) -> List[Dict[str, Any]]:
        """Get intelligent suggestions based on current context."""
        try:
            if self.suggestion_engine and self.context_manager:
                context = self.context_manager.get_context()
                suggestions = self.suggestion_engine.generate_suggestions(
                    context, max_suggestions
                )
                
                # Convert to UI-friendly format
                ui_suggestions = []
                for suggestion in suggestions:
                    ui_suggestions.append({
                        'action': suggestion.action,
                        'reason': suggestion.reason,
                        'priority': suggestion.priority.value,
                        'confidence': suggestion.confidence,
                        'category': suggestion.category
                    })
                
                return ui_suggestions
        except Exception:
            pass
        
        return []
    
    def get_workflow_suggestions(self) -> List[Dict[str, Any]]:
        """Get workflow suggestions based on context."""
        try:
            if self.workflow_executor:
                workflows = self.workflow_executor.registry.list_all()
                
                # Filter and rank workflows based on context
                context = self._build_execution_context()
                workflow_suggestions = []
                
                for workflow in workflows:
                    relevance_score = self._calculate_workflow_relevance(workflow, context)
                    if relevance_score > 0.5:
                        workflow_suggestions.append({
                            'id': workflow.id,
                            'name': workflow.name,
                            'description': workflow.description,
                            'category': workflow.category,
                            'relevance': relevance_score
                        })
                
                # Sort by relevance
                workflow_suggestions.sort(key=lambda x: x['relevance'], reverse=True)
                
                return workflow_suggestions[:5]
        except Exception:
            pass
        
        return []
    
    def _calculate_workflow_relevance(self, workflow, context: ExecutionContext) -> float:
        """Calculate relevance score for a workflow based on context."""
        score = 0.0
        
        # Git-related workflows for repos with uncommitted changes
        if workflow.category == 'git' and context.git_state.get('uncommitted_files', 0) > 0:
            score += 0.8
        
        # Maintenance workflows for low health scores
        if workflow.category == 'maintenance' and context.health_score < 70:
            score += 0.7
        
        # Quality workflows for repos with quality issues
        if workflow.category == 'quality' and context.health_score < 80:
            score += 0.6
        
        # Base relevance for all workflows
        score += 0.3
        
        return min(score, 1.0)
    
    def execute_workflow(self, workflow_id: str, resume: bool = False) -> Dict[str, Any]:
        """Execute a workflow with full UI integration."""
        try:
            if self.workflow_executor:
                execution = self.workflow_executor.execute(workflow_id, resume)
                
                # Convert to UI-friendly format
                return {
                    'workflow_id': execution.workflow_id,
                    'execution_id': execution.execution_id,
                    'status': execution.status.value,
                    'started_at': execution.started_at,
                    'completed_at': execution.completed_at,
                    'steps': {
                        step_id: {
                            'status': step_exec.status.value,
                            'started_at': step_exec.started_at,
                            'completed_at': step_exec.completed_at,
                            'output': step_exec.output,
                            'error': step_exec.error
                        }
                        for step_id, step_exec in execution.steps.items()
                    },
                    'context': execution.context,
                    'report': execution.context.get('report')
                }
            else:
                return {
                    'error': 'Workflow executor not available',
                    'status': 'failed'
                }
        except Exception as e:
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    def get_user_patterns(self) -> Dict[str, Any]:
        """Get user behavior patterns for personalization."""
        try:
            if self.learning_system:
                return self.learning_system.get_user_patterns()
        except Exception:
            pass
        
        return {}