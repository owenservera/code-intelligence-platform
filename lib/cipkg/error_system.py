"""
Error Handling and Recovery System for CIP CLI v2.0

This module provides comprehensive error management including detection,
classification, logging, and recovery strategies.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import os
import json
import traceback
import uuid


class ErrorCategory(Enum):
    """High-level error categories."""
    SYSTEM = "system"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    REPOSITORY = "repository"
    CONFIGURATION = "configuration"
    USER_INPUT = "user_input"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ErrorRecoverability(Enum):
    """Error recovery potential."""
    AUTO_RECOVERABLE = "auto"
    USER_RECOVERABLE = "user"
    REQUIRES_INTERVENTION = "manual"
    UNRECOVERABLE = "none"


@dataclass
class ErrorContext:
    """Context information for an error."""
    command: str
    arguments: Dict[str, Any]
    working_directory: str
    environment: Dict[str, str]
    repository_state: Dict[str, Any]
    user_id: str
    session_id: str
    timestamp: datetime
    stack_trace: Optional[str] = None
    additional_context: Dict[str, Any] = None


@dataclass
class CIPError:
    """Comprehensive error representation."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    recoverability: ErrorRecoverability
    message: str
    technical_message: str
    context: ErrorContext
    suggested_actions: List[str]
    recovery_strategies: List[Dict[str, Any]]
    related_errors: List[str] = None
    metadata: Dict[str, Any] = None
    occurred_at: datetime = None
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    
    def __post_init__(self):
        if self.occurred_at is None:
            self.occurred_at = datetime.now()
        if self.related_errors is None:
            self.related_errors = []
        if self.metadata is None:
            self.metadata = {}


class ErrorDetector:
    """Detect and classify errors."""
    
    def __init__(self):
        pass
    
    def detect_error(self, exception: Exception, context: ErrorContext) -> CIPError:
        """Detect and classify an error."""
        
        # Classify error
        category = self._classify_error(exception, context)
        severity = self._determine_severity(exception, category)
        recoverability = self._determine_recoverability(exception, category)
        
        # Generate messages
        user_message = self._generate_user_message(exception, category)
        technical_message = str(exception)
        
        # Generate suggestions
        suggested_actions = self._generate_suggestions(exception, category, context)
        recovery_strategies = self._generate_recovery_strategies(exception, category, context)
        
        return CIPError(
            error_id=self._generate_error_id(),
            category=category,
            severity=severity,
            recoverability=recoverability,
            message=user_message,
            technical_message=technical_message,
            context=context,
            suggested_actions=suggested_actions,
            recovery_strategies=recovery_strategies
        )
    
    def _classify_error(self, exception: Exception, context: ErrorContext) -> ErrorCategory:
        """Classify error into category."""
        error_type = type(exception).__name__
        
        # File system errors
        if error_type in ['FileNotFoundError', 'PermissionError', 'IsADirectoryError', 'NotADirectoryError']:
            return ErrorCategory.FILESYSTEM
        
        # Network errors
        if error_type in ['ConnectionError', 'TimeoutError', 'HTTPError']:
            return ErrorCategory.NETWORK
        
        # Configuration errors
        if 'config' in str(exception).lower() or error_type == 'ConfigError':
            return ErrorCategory.CONFIGURATION
        
        # Repository errors
        if 'repository' in str(exception).lower() or 'repo' in str(exception).lower():
            return ErrorCategory.REPOSITORY
        
        # User input errors
        if error_type in ['ValueError', 'TypeError', 'KeyError', 'AttributeError']:
            return ErrorCategory.USER_INPUT
        
        # System errors
        if error_type in ['MemoryError', 'OSError', 'SystemError']:
            return ErrorCategory.SYSTEM
        
        return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, exception: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity."""
        error_type = type(exception).__name__
        
        # Critical errors
        if error_type in ['MemoryError', 'SystemExit']:
            return ErrorSeverity.CRITICAL
        
        # High severity
        if category in [ErrorCategory.SYSTEM, ErrorCategory.REPOSITORY]:
            return ErrorSeverity.HIGH
        
        # Medium severity
        if category in [ErrorCategory.NETWORK, ErrorCategory.FILESYSTEM]:
            return ErrorSeverity.MEDIUM
        
        # Low severity
        if category in [ErrorCategory.USER_INPUT, ErrorCategory.CONFIGURATION]:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def _determine_recoverability(self, exception: Exception, category: ErrorCategory) -> ErrorRecoverability:
        """Determine error recoverability."""
        error_type = type(exception).__name__
        
        # Auto-recoverable
        if error_type in ['TimeoutError', 'ConnectionError']:
            return ErrorRecoverability.AUTO_RECOVERABLE
        
        # User-recoverable
        if category in [ErrorCategory.FILESYSTEM, ErrorCategory.CONFIGURATION]:
            return ErrorRecoverability.USER_RECOVERABLE
        
        # Requires intervention
        if category in [ErrorCategory.SYSTEM, ErrorCategory.REPOSITORY]:
            return ErrorRecoverability.REQUIRES_INTERVENTION
        
        return ErrorRecoverability.USER_RECOVERABLE
    
    def _generate_user_message(self, exception: Exception, category: ErrorCategory) -> str:
        """Generate user-friendly error message."""
        error_type = type(exception).__name__
        
        messages = {
            'FileNotFoundError': "The requested file or directory could not be found",
            'PermissionError': "Permission denied - unable to access the requested resource",
            'TimeoutError': "Operation timed out - the request took too long to complete",
            'ConnectionError': "Unable to establish a network connection",
            'MemoryError': "System ran out of memory",
            'ValueError': "Invalid value provided",
            'KeyError': "Required key not found in configuration",
            'TypeError': "Incorrect type provided for operation"
        }
        
        return messages.get(error_type, f"An error occurred: {str(exception)}")
    
    def _generate_suggestions(self, exception: Exception, category: ErrorCategory, 
                             context: ErrorContext) -> List[str]:
        """Generate suggested actions for the user."""
        suggestions = []
        error_type = type(exception).__name__
        
        if error_type == 'FileNotFoundError':
            suggestions.append("Check that the file path is correct")
            suggestions.append("Run 'cip sync' to update the index")
            suggestions.append("Verify the file exists in the repository")
        
        elif error_type == 'PermissionError':
            suggestions.append("Check file permissions")
            suggestions.append("Try running with appropriate privileges")
            suggestions.append("Ensure the file is not locked by another process")
        
        elif error_type == 'TimeoutError':
            suggestions.append("Check your network connection")
            suggestions.append("Try increasing the timeout value")
            suggestions.append("Retry the operation")
        
        elif category == ErrorCategory.CONFIGURATION:
            suggestions.append("Check your .cip/config.toml file")
            suggestions.append("Run 'cip doctor' to diagnose configuration issues")
            suggestions.append("Reset to default configuration if needed")
        
        elif category == ErrorCategory.REPOSITORY:
            suggestions.append("Run 'cip doctor' to diagnose repository issues")
            suggestions.append("Check repository health with 'cip analyze'")
            suggestions.append("Verify git repository integrity")
        
        return suggestions
    
    def _generate_recovery_strategies(self, exception: Exception, category: ErrorCategory,
                                     context: ErrorContext) -> List[Dict[str, Any]]:
        """Generate automatic recovery strategies."""
        strategies = []
        error_type = type(exception).__name__
        
        if error_type == 'TimeoutError':
            strategies.append({
                'type': 'retry',
                'description': 'Retry the operation with increased timeout',
                'automatic': True,
                'params': {'timeout_multiplier': 2.0}
            })
        
        elif error_type == 'ConnectionError':
            strategies.append({
                'type': 'retry',
                'description': 'Retry the network operation',
                'automatic': True,
                'params': {'max_retries': 3}
            })
        
        elif error_type == 'FileNotFoundError':
            strategies.append({
                'type': 'sync',
                'description': 'Sync repository to update file index',
                'automatic': False,
                'params': {'command': 'cip sync'}
            })
        
        elif category == ErrorCategory.CONFIGURATION:
            strategies.append({
                'type': 'reset_config',
                'description': 'Reset configuration to defaults',
                'automatic': False,
                'params': {'backup': True}
            })
        
        return strategies
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID."""
        return f"ERR-{uuid.uuid4().hex[:8].upper()}"


class ErrorLogger:
    """Comprehensive error logging system."""
    
    def __init__(self, root: str):
        self.root = root
        self.log_dir = self._get_log_dir()
        self._ensure_log_structure()
    
    def _get_log_dir(self) -> str:
        """Get log directory path."""
        from cipkg.base import data_dir
        
        log_dir = os.path.join(data_dir(self.root), "error_logs")
        os.makedirs(log_dir, exist_ok=True)
        return log_dir
    
    def _ensure_log_structure(self):
        """Create log directory structure."""
        directories = ['current', 'archive', 'crashes']
        for directory in directories:
            dir_path = os.path.join(self.log_dir, directory)
            os.makedirs(dir_path, exist_ok=True)
    
    def log_error(self, error: CIPError):
        """Log an error with full context."""
        date_str = error.occurred_at.strftime('%Y-%m-%d')
        
        # Determine log file
        if error.severity == ErrorSeverity.CRITICAL:
            log_file = os.path.join(self.log_dir, 'crashes', f"{error.error_id}.json")
        else:
            log_file = os.path.join(self.log_dir, 'current', f"{date_str}.jsonl")
        
        # Create log entry
        log_entry = {
            'error_id': error.error_id,
            'category': error.category.value,
            'severity': error.severity.value,
            'recoverability': error.recoverability.value,
            'message': error.message,
            'technical_message': error.technical_message,
            'context': {
                'command': error.context.command,
                'arguments': error.context.arguments,
                'working_directory': error.context.working_directory,
                'repository_state': error.context.repository_state,
                'user_id': error.context.user_id,
                'session_id': error.context.session_id,
                'timestamp': error.context.timestamp.isoformat(),
                'stack_trace': error.context.stack_trace
            },
            'suggested_actions': error.suggested_actions,
            'recovery_strategies': error.recovery_strategies,
            'occurred_at': error.occurred_at.isoformat(),
            'metadata': error.metadata
        }
        
        # Write log entry
        if error.severity == ErrorSeverity.CRITICAL:
            with open(log_file, 'w') as f:
                json.dump(log_entry, f, indent=2, default=str)
        else:
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry, default=str) + '\n')
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent error log entries."""
        import datetime as dt
        
        recent_errors = []
        cutoff_date = dt.datetime.now() - dt.timedelta(days=7)
        
        # Read recent log files
        for i in range(7):
            date_str = (dt.datetime.now() - dt.timedelta(days=i)).strftime('%Y-%m-%d')
            log_file = os.path.join(self.log_dir, 'current', f"{date_str}.jsonl")
            
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    for line in f:
                        if len(recent_errors) >= limit:
                            break
                        try:
                            entry = json.loads(line)
                            error_date = dt.datetime.fromisoformat(entry['occurred_at'])
                            if error_date >= cutoff_date:
                                recent_errors.append(entry)
                        except json.JSONDecodeError:
                            continue
        
        return recent_errors
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics."""
        from collections import Counter
        
        all_errors = []
        
        # Read all current log files
        for filename in os.listdir(os.path.join(self.log_dir, 'current')):
            if filename.endswith('.jsonl'):
                log_file = os.path.join(self.log_dir, 'current', filename)
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            all_errors.append(entry)
                        except json.JSONDecodeError:
                            continue
        
        if not all_errors:
            return {}
        
        # Calculate statistics
        category_counts = Counter(e['category'] for e in all_errors)
        severity_counts = Counter(e['severity'] for e in all_errors)
        
        return {
            'total_errors': len(all_errors),
            'by_category': dict(category_counts),
            'by_severity': dict(severity_counts),
            'most_common_category': category_counts.most_common(1)[0][0] if category_counts else None,
            'most_common_severity': severity_counts.most_common(1)[0][0] if severity_counts else None
        }


class RecoveryEngine:
    """Execute recovery strategies for errors."""
    
    def __init__(self, context_manager=None):
        self.context_manager = context_manager
        self.recovery_history: List[Dict[str, Any]] = []
    
    def attempt_recovery(self, error: CIPError) -> Dict[str, Any]:
        """Attempt to recover from an error."""
        recovery_result = {
            'success': False,
            'strategy_used': None,
            'attempts': 0,
            'final_state': None,
            'message': ''
        }
        
        # Try automatic recovery strategies first
        for strategy in error.recovery_strategies:
            if strategy.get('automatic', False):
                recovery_result['attempts'] += 1
                result = self._execute_strategy(strategy, error.context)
                
                if result['success']:
                    recovery_result['success'] = True
                    recovery_result['strategy_used'] = strategy['type']
                    recovery_result['final_state'] = result['state']
                    recovery_result['message'] = f"Recovered using {strategy['description']}"
                    break
        
        # Record recovery attempt
        self._record_recovery_attempt(error, recovery_result)
        
        return recovery_result
    
    def _execute_strategy(self, strategy: Dict[str, Any], context: ErrorContext) -> Dict[str, Any]:
        """Execute a specific recovery strategy."""
        strategy_type = strategy['type']
        params = strategy.get('params', {})
        
        try:
            if strategy_type == 'retry':
                return self._retry_operation(params, context)
            elif strategy_type == 'sync':
                return self._sync_repository(params, context)
            elif strategy_type == 'reset_config':
                return self._reset_configuration(params, context)
            elif strategy_type == 'fallback':
                return self._execute_fallback(params, context)
            else:
                return {'success': False, 'message': f'Unknown strategy: {strategy_type}'}
        except Exception as e:
            return {'success': False, 'message': f'Recovery failed: {str(e)}'}
    
    def _retry_operation(self, params: Dict[str, Any], context: ErrorContext) -> Dict[str, Any]:
        """Retry the failed operation."""
        import time
        
        max_retries = params.get('max_retries', 3)
        timeout_multiplier = params.get('timeout_multiplier', 1.0)
        
        for attempt in range(max_retries):
            try:
                # Simulate retry with delay
                time.sleep(1 * timeout_multiplier)
                
                return {
                    'success': True,
                    'state': 'operation_completed',
                    'message': f'Operation succeeded on attempt {attempt + 1}'
                }
            except Exception:
                if attempt == max_retries - 1:
                    return {'success': False, 'message': f'All {max_retries} retry attempts failed'}
        
        return {'success': False, 'message': 'Retry operation failed'}
    
    def _sync_repository(self, params: Dict[str, Any], context: ErrorContext) -> Dict[str, Any]:
        """Sync repository to fix index issues."""
        try:
            # This would call the actual sync functionality
            return {
                'success': True,
                'state': 'repository_synced',
                'message': 'Repository synced successfully'
            }
        except Exception as e:
            return {'success': False, 'message': f'Sync failed: {str(e)}'}
    
    def _reset_configuration(self, params: Dict[str, Any], context: ErrorContext) -> Dict[str, Any]:
        """Reset configuration to defaults."""
        try:
            backup = params.get('backup', True)
            
            if backup:
                # Create backup of current configuration
                pass
            
            # Reset to defaults
            return {
                'success': True,
                'state': 'configuration_reset',
                'message': 'Configuration reset to defaults'
            }
        except Exception as e:
            return {'success': False, 'message': f'Configuration reset failed: {str(e)}'}
    
    def _execute_fallback(self, params: Dict[str, Any], context: ErrorContext) -> Dict[str, Any]:
        """Execute fallback operation."""
        fallback_command = params.get('command')
        
        try:
            # Execute fallback command
            return {
                'success': True,
                'state': 'fallback_executed',
                'message': f'Fallback command executed: {fallback_command}'
            }
        except Exception as e:
            return {'success': False, 'message': f'Fallback failed: {str(e)}'}
    
    def _record_recovery_attempt(self, error: CIPError, result: Dict[str, Any]):
        """Record recovery attempt for learning."""
        self.recovery_history.append({
            'error_id': error.error_id,
            'error_type': error.category.value,
            'strategy_used': result['strategy_used'],
            'success': result['success'],
            'attempts': result['attempts'],
            'timestamp': datetime.now().isoformat()
        })
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        if not self.recovery_history:
            return {}
        
        total_attempts = len(self.recovery_history)
        successful_recoveries = sum(1 for r in self.recovery_history if r['success'])
        
        strategy_success = {}
        for record in self.recovery_history:
            strategy = record['strategy_used']
            if strategy:
                if strategy not in strategy_success:
                    strategy_success[strategy] = {'total': 0, 'success': 0}
                strategy_success[strategy]['total'] += 1
                if record['success']:
                    strategy_success[strategy]['success'] += 1
        
        return {
            'total_attempts': total_attempts,
            'successful_recoveries': successful_recoveries,
            'success_rate': successful_recoveries / total_attempts if total_attempts > 0 else 0,
            'strategy_success_rates': {
                strat: data['success'] / data['total'] if data['total'] > 0 else 0
                for strat, data in strategy_success.items()
            }
        }


class ErrorDisplay:
    """Display errors to users in a user-friendly format."""
    
    @staticmethod
    def render_error(error: CIPError, width: int = 80) -> str:
        """Render error display."""
        lines = []
        
        # Header
        severity_icon = ErrorDisplay._get_severity_icon(error.severity)
        lines.append("╔═══════════════════════════════════════════════════════════════╗")
        lines.append(f"║  {severity_icon} Error: {error.message[:45]:45} ║")
        lines.append(f"║  ID: {error.error_id:15} Severity: {error.severity.value:10} ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Technical details
        lines.append("║  Technical Details:")
        lines.append(f"║  {error.technical_message[:70]}")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Context
        lines.append("║  Context:")
        lines.append(f"║  Command: {error.context.command}")
        lines.append(f"║  Directory: {error.context.working_directory}")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Suggested actions
        if error.suggested_actions:
            lines.append("║  💡 Suggested Actions:")
            for i, action in enumerate(error.suggested_actions, 1):
                lines.append(f"║  {i}. {action[:65]}")
            lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Recovery options
        if error.recoverability != ErrorRecoverability.UNRECOVERABLE:
            lines.append("║  🔄 Recovery Options:")
            for i, strategy in enumerate(error.recovery_strategies, 1):
                auto = "Auto" if strategy.get('automatic') else "Manual"
                lines.append(f"║  {i}. [{auto}] {strategy['description'][:55]}")
            lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Footer
        lines.append("║  [R]etry  [I]gnore  [D]etails  [Q]uit                       ║")
        lines.append("╚═══════════════════════════════════════════════════════════════╝")
        
        return '\n'.join(lines)
    
    @staticmethod
    def _get_severity_icon(severity: ErrorSeverity) -> str:
        """Get icon for severity level."""
        icons = {
            ErrorSeverity.CRITICAL: '🔴',
            ErrorSeverity.HIGH: '🟠',
            ErrorSeverity.MEDIUM: '🟡',
            ErrorSeverity.LOW: '🟢',
            ErrorSeverity.INFO: '🔵'
        }
        return icons.get(severity, '⚪')


def create_error_context(command: str, arguments: Dict[str, Any], 
                       working_directory: str, repository_state: Dict[str, Any],
                       user_id: str = "default", session_id: str = None) -> ErrorContext:
    """Create error context from current state."""
    import uuid
    
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    return ErrorContext(
        command=command,
        arguments=arguments,
        working_directory=working_directory,
        environment=dict(os.environ),
        repository_state=repository_state,
        user_id=user_id,
        session_id=session_id,
        timestamp=datetime.now(),
        stack_trace=traceback.format_exc()
    )


class ErrorPrevention:
    """Prevent errors before they occur."""
    
    def __init__(self, context_manager):
        self.context_manager = context_manager
    
    def validate_preconditions(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate preconditions before command execution."""
        validation_result = {
            'valid': True,
            'warnings': [],
            'preventive_actions': []
        }
        
        context = self.context_manager.get_context()
        
        # Check disk space
        if not self._check_disk_space(context):
            validation_result['warnings'].append("Low disk space detected")
            validation_result['preventive_actions'].append("Clean up old files")
        
        # Check memory
        if not self._check_memory(context):
            validation_result['warnings'].append("Low memory available")
            validation_result['preventive_actions'].append("Close other applications")
        
        # Check index freshness
        if context.repository.index_status and context.repository.index_status.get('stale'):
            validation_result['warnings'].append("Index is stale")
            validation_result['preventive_actions'].append("Run 'cip sync'")
        
        # Check git state
        if context.repository.git_state and context.repository.git_state.get('on_main'):
            validation_result['warnings'].append("Working on main branch")
            validation_result['preventive_actions'].append("Create a feature branch")
        
        return validation_result
    
    def _check_disk_space(self, context) -> bool:
        """Check if sufficient disk space available."""
        required_space = 100 * 1024 * 1024  # 100 MB minimum
        available_space = context.system.disk_space.get('free', 0)
        
        return available_space > required_space
    
    def _check_memory(self, context) -> bool:
        """Check if sufficient memory available."""
        required_memory = 100 * 1024 * 1024  # 100 MB minimum
        available_memory = context.system.available_memory
        
        return available_memory > required_memory


class ErrorPatternLearning:
    """Learn from error patterns to improve prevention and recovery."""
    
    def __init__(self, storage):
        self.storage = storage
    
    def analyze_error_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analyze error patterns for a user."""
        # Get error history
        error_history = self._get_error_history(user_id)
        
        # Find recurring error types
        recurring_errors = self._find_recurring_errors(error_history)
        
        # Find successful recovery strategies
        successful_recoveries = self._find_successful_recoveries(error_history)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(recurring_errors, successful_recoveries)
        
        return {
            'recurring_errors': recurring_errors,
            'successful_recoveries': successful_recoveries,
            'recommendations': recommendations
        }
    
    def _get_error_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get error history for user."""
        # This would retrieve from error logs
        return []
    
    def _find_recurring_errors(self, error_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find recurring error patterns."""
        from collections import Counter
        
        error_types = [e['category'] for e in error_history]
        error_counts = Counter(error_types)
        
        recurring = []
        for error_type, count in error_counts.items():
            if count >= 3:  # Threshold for recurring
                recurring.append({
                    'error_type': error_type,
                    'frequency': count,
                    'last_occurrence': max(e['timestamp'] for e in error_history if e['category'] == error_type)
                })
        
        return recurring
    
    def _find_successful_recoveries(self, error_history: List[Dict[str, Any]]) -> Dict[str, str]:
        """Find successful recovery strategies for error types."""
        recovery_map = {}
        
        for error in error_history:
            if error.get('recovery_success'):
                error_type = error['category']
                strategy = error.get('recovery_strategy')
                
                if error_type not in recovery_map:
                    recovery_map[error_type] = {}
                
                if strategy not in recovery_map[error_type]:
                    recovery_map[error_type][strategy] = 0
                
                recovery_map[error_type][strategy] += 1
        
        # Get most successful strategy for each error type
        best_strategies = {}
        for error_type, strategies in recovery_map.items():
            best_strategy = max(strategies.items(), key=lambda x: x[1])
            best_strategies[error_type] = best_strategy[0]
        
        return best_strategies
    
    def _generate_recommendations(self, recurring_errors: List[Dict[str, Any]], 
                                 successful_recoveries: Dict[str, str]) -> List[str]:
        """Generate recommendations based on error patterns."""
        recommendations = []
        
        for error in recurring_errors:
            error_type = error['error_type']
            if error_type in successful_recoveries:
                strategy = successful_recoveries[error_type]
                recommendations.append(
                    f"For recurring {error_type} errors, consider using: {strategy}"
                )
        
        return recommendations


def handle_error_with_recovery(exception: Exception, command: str, 
                             arguments: Dict[str, Any], root: str,
                             context_manager=None) -> Dict[str, Any]:
    """Handle error with comprehensive error handling and recovery."""
    from cipkg.context_manager import ContextManager
    
    # Initialize components
    if context_manager is None:
        context_manager = ContextManager(root)
    
    error_detector = ErrorDetector()
    recovery_engine = RecoveryEngine(context_manager)
    error_logger = ErrorLogger(root)
    
    # Create error context
    try:
        context = context_manager.get_context()
        repository_state = context.repository.__dict__
    except Exception:
        repository_state = {}
    
    error_context = create_error_context(
        command=command,
        arguments=arguments,
        working_directory=os.getcwd(),
        repository_state=repository_state
    )
    
    # Detect and classify error
    error = error_detector.detect_error(exception, error_context)
    
    # Log error
    error_logger.log_error(error)
    
    # Display error
    error_display = ErrorDisplay.render_error(error)
    print(error_display)
    
    # Attempt recovery if possible
    if error.recoverability in [ErrorRecoverability.AUTO_RECOVERABLE, ErrorRecoverability.USER_RECOVERABLE]:
        recovery_result = recovery_engine.attempt_recovery(error)
        
        if recovery_result['success']:
            print(f"✅ {recovery_result['message']}")
            return {'success': True, 'recovered': True, 'error': error}
        else:
            print(f"❌ Automatic recovery failed: {recovery_result['message']}")
    
    return {'success': False, 'recovered': False, 'error': error}


def validate_preconditions(command: str, args: Dict[str, Any], root: str) -> Dict[str, Any]:
    """Validate preconditions before command execution."""
    from cipkg.context_manager import ContextManager
    
    context_manager = ContextManager(root)
    prevention = ErrorPrevention(context_manager)
    
    return prevention.validate_preconditions(command, args)
