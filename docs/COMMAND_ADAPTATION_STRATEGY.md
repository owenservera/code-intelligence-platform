# Command Adaptation Strategy

## Overview

The Command Adaptation Strategy defines how existing CIP commands will evolve from static, one-size-fits-all tools to context-aware, intelligent operations that adapt based on repository state, user patterns, and environmental context. This ensures backward compatibility while delivering enhanced functionality.

## Core Principles

1. **Backward Compatibility**: All existing commands continue to work with their original behavior
2. **Opt-In Intelligence**: Enhanced features are opt-in via flags or configuration
3. **Progressive Enhancement**: Commands gain intelligence gradually without breaking changes
4. **Context Awareness**: Commands adapt based on repo type, state, and user patterns
5. **Graceful Degradation**: Enhanced features fall back gracefully when context unavailable

## Adaptation Framework

### Command Adaptation Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class CommandContext:
    """Context for command execution."""
    repo_type: str
    repo_state: Dict[str, Any]
    user_patterns: Dict[str, Any]
    git_state: Dict[str, Any]
    current_directory: str
    environment: Dict[str, str]

@dataclass
class AdaptedCommand:
    """Adapted command with context-aware modifications."""
    original_command: str
    adapted_command: str
    adaptations: Dict[str, Any]
    reasoning: str
    confidence: float

class CommandAdapter(ABC):
    """Base class for command adapters."""
    
    @abstractmethod
    def can_adapt(self, command: str, context: CommandContext) -> bool:
        """Check if this adapter can handle the command."""
        pass
    
    @abstractmethod
    def adapt(self, command: str, context: CommandContext) -> AdaptedCommand:
        """Adapt the command based on context."""
        pass
    
    @abstractmethod
    def get_original_behavior(self, command: str) -> str:
        """Get original command behavior for fallback."""
        pass
```

### Context-Aware Command Wrapper

```python
class ContextAwareCommand:
    """Wrapper that adds context awareness to existing commands."""
    
    def __init__(self, original_handler, context_manager: ContextManager):
        self.original_handler = original_handler
        self.context_manager = context_manager
        self.adapters = self._load_adapters()
    
    def _load_adapters(self) -> Dict[str, CommandAdapter]:
        """Load available command adapters."""
        return {
            'audit': AuditCommandAdapter(),
            'search': SearchCommandAdapter(),
            'index': IndexCommandAdapter(),
            'sync': SyncCommandAdapter(),
            'analyze': AnalyzeCommandAdapter(),
            'routes': RoutesCommandAdapter(),
            'models': ModelsCommandAdapter(),
            'findings': FindingsCommandAdapter()
        }
    
    def execute(self, command: str, args: Dict[str, Any], 
                use_adaptation: bool = True) -> Any:
        """Execute command with optional adaptation."""
        if not use_adaptation:
            return self.original_handler(command, args)
        
        # Get current context
        context = self.context_manager.get_context()
        command_context = self._build_command_context(context)
        
        # Check if adaptation available
        command_name = command.split()[0]
        adapter = self.adapters.get(command_name)
        
        if adapter and adapter.can_adapt(command, command_context):
            try:
                adapted = adapter.adapt(command, command_context)
                return self._execute_adapted(adapted, args)
            except Exception as e:
                # Fall back to original behavior on adaptation failure
                print(f"Adaptation failed, using original behavior: {e}")
                return self.original_handler(command, args)
        else:
            return self.original_handler(command, args)
    
    def _build_command_context(self, unified_context: UnifiedContext) -> CommandContext:
        """Build command context from unified context."""
        return CommandContext(
            repo_type=unified_context.repository.repo_type,
            repo_state={
                'health': unified_context.repository.health_score,
                'index': unified_context.repository.index_status,
                'file_count': unified_context.repository.file_count
            },
            user_patterns=unified_context.user.command_history,
            git_state=unified_context.repository.git_state,
            current_directory=unified_context.session.current_directory,
            environment=unified_context.session.environment_vars
        )
    
    def _execute_adapted(self, adapted: AdaptedCommand, args: Dict[str, Any]) -> Any:
        """Execute adapted command."""
        # Merge adapted arguments with user arguments
        merged_args = {**args, **adapted.adaptations}
        
        # Execute with adapted command
        return self.original_handler(adapted.adapted_command, merged_args)
```

## Command-Specific Adapters

### Audit Command Adapter

```python
class AuditCommandAdapter(CommandAdapter):
    """Adapt audit command based on context."""
    
    def can_adapt(self, command: str, context: CommandContext) -> bool:
        """Can adapt if audit command and context available."""
        return command.startswith('cip audit') and context.repo_state
    
    def adapt(self, command: str, context: CommandContext) -> AdaptedCommand:
        """Adapt audit command based on repository state."""
        adaptations = {}
        reasoning_parts = []
        
        # Adapt based on git state
        if context.git_state and context.git_state.get('uncommitted_files', 0) > 0:
            adaptations['diff'] = True
            reasoning_parts.append("Uncommitted changes detected - adding diff analysis")
        
        # Adapt based on repo type
        if context.repo_type == 'nextjs-app':
            adaptations['framework'] = 'nextjs'
            reasoning_parts.append("Next.js repository detected - adding framework-specific rules")
        elif context.repo_type == 'python-lib':
            adaptations['framework'] = 'python'
            reasoning_parts.append("Python repository detected - adding Python-specific rules")
        
        # Adapt based on health score
        if context.repo_state.get('health', {}).get('score', 100) < 70:
            adaptations['severity'] = 'all'
            reasoning_parts.append("Low health score - including all severity levels")
        
        # Adapt based on user patterns
        recent_audits = [c for c in context.user_patterns if 'audit' in c.get('command', '')]
        if recent_audits and len(recent_audits) > 3:
            # User frequently runs audits - suggest comprehensive mode
            adaptations['comprehensive'] = True
            reasoning_parts.append("Frequent audit user - enabling comprehensive mode")
        
        adapted_command = command
        for flag, value in adaptations.items():
            if value is True:
                adapted_command += f" --{flag}"
            elif value:
                adapted_command += f" --{flag}={value}"
        
        return AdaptedCommand(
            original_command=command,
            adapted_command=adapted_command,
            adaptations=adaptations,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No adaptations applied",
            confidence=0.8 if reasoning_parts else 0.0
        )
    
    def get_original_behavior(self, command: str) -> str:
        """Get original audit command."""
        return command
```

### Search Command Adapter

```python
class SearchCommandAdapter(CommandAdapter):
    """Adapt search command based on context."""
    
    def can_adapt(self, command: str, context: CommandContext) -> bool:
        """Can adapt if search command and context available."""
        return command.startswith('cip search') and context.current_directory
    
    def adapt(self, command: str, context: CommandContext) -> AdaptedCommand:
        """Adapt search command based on context."""
        adaptations = {}
        reasoning_parts = []
        
        # Adapt based on current directory
        if context.current_directory:
            adaptations['context_path'] = context.current_directory
            reasoning_parts.append(f"Context-aware search in {context.current_directory}")
        
        # Adapt based on repo type
        if context.repo_type == 'nextjs-app':
            adaptations['file_types'] = ['ts', 'tsx', 'js', 'jsx']
            reasoning_parts.append("Next.js repository - focusing on TypeScript/JavaScript files")
        elif context.repo_type == 'python-lib':
            adaptations['file_types'] = ['py']
            reasoning_parts.append("Python repository - focusing on Python files")
        
        # Adapt based on recent files
        if context.repo_state.get('recent_files'):
            adaptations['boost_recent'] = True
            reasoning_parts.append("Boosting recently modified files in results")
        
        # Adapt based on user patterns
        recent_searches = [c for c in context.user_patterns if 'search' in c.get('command', '')]
        if recent_searches:
            # Learn from user's search patterns
            common_extensions = self._extract_common_extensions(recent_searches)
            if common_extensions:
                adaptations['file_types'] = common_extensions
                reasoning_parts.append(f"Based on your patterns - focusing on {common_extensions} files")
        
        adapted_command = command
        for flag, value in adaptations.items():
            if isinstance(value, bool) and value:
                adapted_command += f" --{flag}"
            elif isinstance(value, list):
                adapted_command += f" --{flag}={','.join(value)}"
            else:
                adapted_command += f" --{flag}={value}"
        
        return AdaptedCommand(
            original_command=command,
            adapted_command=adapted_command,
            adaptations=adaptations,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No adaptations applied",
            confidence=0.75 if reasoning_parts else 0.0
        )
    
    def _extract_common_extensions(self, recent_searches: List[Dict]) -> List[str]:
        """Extract common file extensions from recent searches."""
        from collections import Counter
        
        extensions = []
        for search in recent_searches:
            args = search.get('arguments', {})
            if 'file_types' in args:
                extensions.extend(args['file_types'])
        
        if extensions:
            counter = Counter(extensions)
            return [ext for ext, count in counter.most_common(3)]
        return []
    
    def get_original_behavior(self, command: str) -> str:
        """Get original search command."""
        return command
```

### Index Command Adapter

```python
class IndexCommandAdapter(CommandAdapter):
    """Adapt index command based on context."""
    
    def can_adapt(self, command: str, context: CommandContext) -> bool:
        """Can adapt if index command and context available."""
        return command.startswith('cip index') and context.repo_state
    
    def adapt(self, command: str, context: CommandContext) -> AdaptedCommand:
        """Adapt index command based on repository state."""
        adaptations = {}
        reasoning_parts = []
        
        # Adapt based on index status
        index_status = context.repo_state.get('index', {})
        if index_status.get('stale', True):
            adaptations['force'] = True
            reasoning_parts.append("Index is stale - forcing reindex")
        
        # Adapt based on embedding coverage
        if index_status.get('embedding_coverage', 100) < 80:
            adaptations['embed'] = True
            reasoning_parts.append(f"Low embedding coverage ({index_status['embedding_coverage']}%) - generating embeddings")
        
        # Adapt based on file count
        file_count = context.repo_state.get('file_count', 0)
        if file_count > 1000:
            adaptations['parallel'] = True
            reasoning_parts.append(f"Large repository ({file_count} files) - enabling parallel indexing")
        
        # Adapt based on repo type
        if context.repo_type == 'nextjs-app':
            adaptations['include_patterns'] = ['**/*.ts', '**/*.tsx', '**/*.js', '**/*.jsx']
            reasoning_parts.append("Next.js repository - including web framework files")
        elif context.repo_type == 'python-lib':
            adaptations['include_patterns'] = ['**/*.py']
            reasoning_parts.append("Python repository - including Python files")
        
        adapted_command = command
        for flag, value in adaptations.items():
            if isinstance(value, bool) and value:
                adapted_command += f" --{flag}"
            elif isinstance(value, list):
                adapted_command += f" --{flag}={','.join(value)}"
            else:
                adapted_command += f" --{flag}={value}"
        
        return AdaptedCommand(
            original_command=command,
            adapted_command=adapted_command,
            adaptations=adaptations,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No adaptations applied",
            confidence=0.85 if reasoning_parts else 0.0
        )
    
    def get_original_behavior(self, command: str) -> str:
        """Get original index command."""
        return command
```

### Sync Command Adapter

```python
class SyncCommandAdapter(CommandAdapter):
    """Adapt sync command based on context."""
    
    def can_adapt(self, command: str, context: CommandContext) -> bool:
        """Can adapt if sync command and context available."""
        return command.startswith('cip sync') and context.git_state
    
    def adapt(self, command: str, context: CommandContext) -> AdaptedCommand:
        """Adapt sync command based on git state."""
        adaptations = {}
        reasoning_parts = []
        
        # Adapt based on git state
        if context.git_state and context.git_state.get('uncommitted_files', 0) > 0:
            adaptations['include_uncommitted'] = True
            reasoning_parts.append("Uncommitted changes detected - including uncommitted files")
        
        # Adapt based on branch
        if context.git_state and context.git_state.get('on_main', False):
            adaptations['safe_mode'] = True
            reasoning_parts.append("On main branch - enabling safe mode")
        
        # Adapt based on repo type
        if context.repo_type == 'vivim-final':
            adaptations['profile'] = 'vivim-final'
            reasoning_parts.append("Vivim repository - using Vivim-specific sync profile")
        
        adapted_command = command
        for flag, value in adaptations.items():
            if isinstance(value, bool) and value:
                adapted_command += f" --{flag}"
            else:
                adapted_command += f" --{flag}={value}"
        
        return AdaptedCommand(
            original_command=command,
            adapted_command=adapted_command,
            adaptations=adaptations,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No adaptations applied",
            confidence=0.8 if reasoning_parts else 0.0
        )
    
    def get_original_behavior(self, command: str) -> str:
        """Get original sync command."""
        return command
```

### Routes Command Adapter (Next.js Specific)

```python
class RoutesCommandAdapter(CommandAdapter):
    """Adapt routes command for Next.js repositories."""
    
    def can_adapt(self, command: str, context: CommandContext) -> bool:
        """Can adapt if routes command in Next.js repo."""
        return (command.startswith('cip routes') and 
                context.repo_type == 'nextjs-app')
    
    def adapt(self, command: str, context: CommandContext) -> AdaptedCommand:
        """Adapt routes command for Next.js."""
        adaptations = {}
        reasoning_parts = []
        
        # Next.js specific adaptations
        adaptations['format'] = 'tree'
        reasoning_parts.append("Next.js repository - using tree format for route visualization")
        
        # Adapt based on git state
        if context.git_state and context.git_state.get('uncommitted_files', 0) > 0:
            adaptations['highlight_changes'] = True
            reasoning_parts.append("Uncommitted changes - highlighting modified routes")
        
        # Adapt based on user patterns
        recent_routes = [c for c in context.user_patterns if 'routes' in c.get('command', '')]
        if recent_routes:
            # Check if user prefers detailed output
            for route_cmd in recent_routes:
                if route_cmd.get('arguments', {}).get('verbose'):
                    adaptations['verbose'] = True
                    reasoning_parts.append("Based on your preference - showing verbose output")
                    break
        
        adapted_command = command
        for flag, value in adaptations.items():
            if isinstance(value, bool) and value:
                adapted_command += f" --{flag}"
            else:
                adapted_command += f" --{flag}={value}"
        
        return AdaptedCommand(
            original_command=command,
            adapted_command=adapted_command,
            adaptations=adaptations,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No adaptations applied",
            confidence=0.9 if reasoning_parts else 0.0
        )
    
    def get_original_behavior(self, command: str) -> str:
        """Get original routes command."""
        return command
```

## Help System Adaptation

### Context-Aware Help Generator

```python
class ContextAwareHelpGenerator:
    """Generate context-aware help content."""
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
    
    def generate_help(self, command: str = None) -> str:
        """Generate context-aware help."""
        context = self.context_manager.get_context()
        
        if command:
            return self._generate_command_help(command, context)
        else:
            return self._generate_general_help(context)
    
    def _generate_general_help(self, context: UnifiedContext) -> str:
        """Generate general help with context awareness."""
        repo_type = context.repository.repo_type
        
        # Get relevant commands based on repo type
        relevant_commands = self._get_relevant_commands(repo_type)
        
        # Get suggestions based on current state
        suggestions = self._get_state_suggestions(context)
        
        return self._format_help(context, relevant_commands, suggestions)
    
    def _get_relevant_commands(self, repo_type: str) -> List[str]:
        """Get commands relevant to repository type."""
        command_sets = {
            'nextjs-app': ['routes', 'models', 'audit', 'findings', 'impact'],
            'python-lib': ['verify', 'coverage', 'audit', 'analyze', 'graph'],
            'vivim-final': ['sync', 'analyze', 'audit', 'doctor', 'index'],
            'generic': ['audit', 'search', 'analyze', 'sync', 'help']
        }
        
        return command_sets.get(repo_type, command_sets['generic'])
    
    def _get_state_suggestions(self, context: UnifiedContext) -> List[str]:
        """Get suggestions based on current repository state."""
        suggestions = []
        
        # Health-based suggestions
        if context.repository.health_score and context.repository.health_score.get('score', 100) < 70:
            suggestions.append("cip analyze - Check repository health")
        
        # Index-based suggestions
        if context.repository.index_status and context.repository.index_status.get('stale', True):
            suggestions.append("cip sync - Update index")
        
        # Git-based suggestions
        if context.repository.git_state and context.repository.git_state.get('uncommitted_files', 0) > 0:
            suggestions.append("cip audit --diff - Review changes")
        
        return suggestions
    
    def _format_help(self, context: UnifiedContext, commands: List[str], 
                    suggestions: List[str]) -> str:
        """Format help output with context information."""
        output = []
        
        # Header with context
        output.append("╔═══════════════════════════════════════════════════════════════╗")
        output.append(f"║  CIP v2.0 - {context.repository.repo_name:20}                      ║")
        output.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Context summary
        health = context.repository.health_score.get('score', 'N/A') if context.repository.health_score else 'N/A'
        index_status = 'Fresh' if not context.repository.index_status.get('stale') else 'Stale'
        git_status = f"{context.repository.git_state.get('uncommitted_files', 0)} changed" if context.repository.git_state else "Unknown"
        
        output.append(f"║  Type: {context.repository.repo_type:12} Health: {health:3}/100  Index: {index_status:6} ║")
        output.append(f"║  Git: {git_status:20} Files: {context.repository.file_count:6}              ║")
        output.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Suggestions
        if suggestions:
            output.append("║  🔥 Suggested Actions                                         ║")
            for i, suggestion in enumerate(suggestions[:3], 1):
                output.append(f"║  {i}. {suggestion:55} ║")
            output.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Relevant commands
        output.append(f"║  📚 Relevant Commands for {context.repository.repo_type:12}              ║")
        for command in commands[:5]:
            output.append(f"║  cip {command:15} - {self._get_command_description(command):30} ║")
        
        output.append("╠═══════════════════════════════════════════════════════════════╣")
        output.append("║  💡 Run 'cip interactive' for guided workflows                   ║")
        output.append("║  💡 Run 'cip --help --classic' for traditional help              ║")
        output.append("╚═══════════════════════════════════════════════════════════════╝")
        
        return '\n'.join(output)
    
    def _get_command_description(self, command: str) -> str:
        """Get short description for command."""
        descriptions = {
            'routes': 'Analyze Next.js routes',
            'models': 'Analyze Prisma models',
            'audit': 'Run code quality audit',
            'findings': 'Query open findings',
            'impact': 'Check change impact',
            'verify': 'Verify code quality',
            'coverage': 'Analyze test coverage',
            'analyze': 'Analyze repository health',
            'graph': 'Show code relationships',
            'sync': 'Sync repository index',
            'search': 'Search codebase',
            'doctor': 'Diagnose issues',
            'index': 'Manage code index'
        }
        return descriptions.get(command, 'Command description')
    
    def _generate_command_help(self, command: str, context: UnifiedContext) -> str:
        """Generate help for specific command with context."""
        # Get base help for command
        base_help = self._get_base_help(command)
        
        # Add context-specific tips
        context_tips = self._get_context_tips(command, context)
        
        if context_tips:
            return f"{base_help}\n\n💡 Context Tips:\n" + "\n".join(f"  • {tip}" for tip in context_tips)
        else:
            return base_help
    
    def _get_base_help(self, command: str) -> str:
        """Get base help for command."""
        # This would call the existing help system
        return f"Help for {command}"
    
    def _get_context_tips(self, command: str, context: UnifiedContext) -> List[str]:
        """Get context-specific tips for command."""
        tips = []
        
        if command == 'audit':
            if context.repository.git_state and context.repository.git_state.get('uncommitted_files', 0) > 0:
                tips.append("Use --diff to audit only changed files")
            if context.repository.repo_type == 'nextjs-app':
                tips.append("Use --framework=nextjs for Next.js specific rules")
        
        elif command == 'search':
            if context.current_directory:
                tips.append(f"Search is scoped to {context.current_directory}")
            if context.repository.repo_type == 'python-lib':
                tips.append("Use --file-types=py to focus on Python files")
        
        return tips
```

## Configuration

### Command Adaptation Configuration

```toml
[command_adaptation]
enabled = true
fallback_on_error = true
show_adaptations = true
require_confirmation = false

[command_adaptation.audit]
auto_diff = true
auto_framework = true
auto_comprehensive = false

[command_adaptation.search]
auto_context_path = true
auto_file_types = true
auto_boost_recent = true

[command_adaptation.index]
auto_force = true
auto_embed = true
auto_parallel = true

[command_adaptation.help]
context_aware = true
show_suggestions = true
relevant_commands = true
```

## CLI Integration

### Modified CLI Handler

```python
def handle_command(root: str, command: str, args: Dict[str, Any]):
    """Handle command with context awareness."""
    from cipkg.base import load_config
    from cipkg.interactive import ContextManager, ContextAwareCommand
    
    config = load_config(root)
    
    # Check if adaptation is enabled
    adaptation_enabled = config.get('command_adaptation', {}).get('enabled', True)
    use_adaptation = args.pop('adapt', adaptation_enabled)
    
    # Create context-aware wrapper
    context_manager = ContextManager(root)
    original_handler = get_original_handler(command)
    
    if original_handler and use_adaptation:
        wrapped_handler = ContextAwareCommand(original_handler, context_manager)
        result = wrapped_handler.execute(command, args, use_adaptation=True)
        
        # Show adaptation info if configured
        if config.get('command_adaptation', {}).get('show_adaptations', True):
            show_adaptation_info(result)
        
        return result
    else:
        # Use original handler
        return original_handler(command, args)

def show_adaptation_info(result):
    """Show information about command adaptations."""
    if hasattr(result, 'adaptations') and result.adaptations:
        print(f"🔄 Command adapted: {result.reasoning}")
        if result.adaptations:
            print("   Applied adaptations:")
            for key, value in result.adaptations.items():
                print(f"   • {key}: {value}")
```

### Command Line Flags

```bash
# Enable/disable adaptation for specific command
cip audit --adapt=true    # Force adaptation
cip audit --adapt=false   # Disable adaptation

# Show what would be adapted without executing
cip audit --adapt-dry-run

# Use classic help
cip --help --classic

# Show adaptation reasoning
cip audit --adapt-verbose
```

## Migration Strategy

### Phase 1: Backward Compatible Rollout

1. **Add adaptation framework** without enabling by default
2. **Implement core adapters** for most common commands
3. **Add configuration flags** for opt-in testing
4. **Gather user feedback** on adaptation quality

### Phase 2: Gradual Enablement

1. **Enable adaptation by default** for new installations
2. **Keep existing installations** with adaptation disabled
3. **Add migration guide** for existing users
4. **Monitor adaptation success rates**

### Phase 3: Full Integration

1. **Make adaptation default** for all users
2. **Add --classic flag** for original behavior
3. **Deprecate --adapt flags** (keep for compatibility)
4. **Focus on improving adaptation quality**

## Testing Strategy

### Adaptation Testing

```python
def test_audit_adapter():
    """Test audit command adaptation."""
    adapter = AuditCommandAdapter()
    context = CommandContext(
        repo_type='nextjs-app',
        repo_state={'health': {'score': 65}},
        user_patterns=[],
        git_state={'uncommitted_files': 5},
        current_directory='/app/src',
        environment={}
    )
    
    adapted = adapter.adapt('cip audit', context)
    
    assert '--diff' in adapted.adapted_command
    assert '--framework=nextjs' in adapted.adapted_command
    assert adapted.confidence > 0.5

def test_adapter_fallback():
    """Test adapter fallback on error."""
    context_manager = ContextManager(test_root)
    original_handler = lambda cmd, args: "original result"
    
    wrapped = ContextAwareCommand(original_handler, context_manager)
    
    # Test with failing adapter
    result = wrapped.execute('cip test', {}, use_adaptation=True)
    
    # Should fall back to original behavior
    assert result == "original result"
```

## Performance Considerations

### Adaptation Caching

```python
class AdaptationCache:
    """Cache command adaptations."""
    
    def __init__(self, ttl: int = 60):
        self.cache: Dict[str, tuple] = {}
        self.ttl = ttl
    
    def get_adaptation(self, command: str, context_key: str) -> Optional[AdaptedCommand]:
        """Get cached adaptation."""
        cache_key = f"{command}:{context_key}"
        
        if cache_key in self.cache:
            adapted, timestamp = self.cache[cache_key]
            import time
            if time.time() - timestamp < self.ttl:
                return adapted
        
        return None
    
    def set_adaptation(self, command: str, context_key: str, adapted: AdaptedCommand):
        """Cache adaptation."""
        import time
        cache_key = f"{command}:{context_key}"
        self.cache[cache_key] = (adapted, time.time())
```

## Future Enhancements

### Machine Learning Adaptation

```python
class MLCommandAdapter(CommandAdapter):
    """Use ML for command adaptation."""
    
    def __init__(self, model_path: str):
        self.model = self._load_model(model_path)
    
    def adapt(self, command: str, context: CommandContext) -> AdaptedCommand:
        """Use ML model to predict optimal adaptations."""
        features = self._extract_features(command, context)
        adaptations = self.model.predict(features)
        
        return AdaptedCommand(
            original_command=command,
            adapted_command=self._apply_adaptations(command, adaptations),
            adaptations=adaptations,
            reasoning="ML-based adaptation",
            confidence=adaptations.get('confidence', 0.5)
        )
```

### User Feedback Integration

```python
class FeedbackAwareAdapter(CommandAdapter):
    """Adapter that learns from user feedback."""
    
    def record_feedback(self, command: str, adaptation: AdaptedCommand, 
                      was_helpful: bool):
        """Record user feedback on adaptation."""
        # Use feedback to improve future adaptations
        pass
```

## Conclusion

The Command Adaptation Strategy provides a systematic approach to evolving CIP commands from static tools to context-aware, intelligent operations. By maintaining backward compatibility while progressively adding intelligence, the system ensures a smooth transition for users while delivering enhanced functionality.

The modular adapter architecture allows for easy extension with new adaptations and supports both rule-based and machine learning approaches. The configuration system gives users control over adaptation behavior, while the fallback mechanisms ensure reliability even when adaptations fail.
