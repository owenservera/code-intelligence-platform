"""
Context-Aware Help System for CIP CLI v2.0

This module provides intelligent help generation based on repository context,
user patterns, and current state.
"""

from typing import Dict, List, Any, Optional
from cipkg.context_manager import UnifiedContext, ContextManager


class ContextAwareHelpGenerator:
    """Generate context-aware help content."""
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
    
    def generate_help(self, command: str = None, classic: bool = False) -> str:
        """Generate context-aware help."""
        if classic:
            return self._generate_classic_help(command)
        
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
    
    def _generate_classic_help(self, command: str = None) -> str:
        """Generate classic help without context awareness."""
        if command:
            return self._get_base_help(command)
        else:
            return self._get_classic_general_help()
    
    def _get_relevant_commands(self, repo_type: str) -> List[str]:
        """Get commands relevant to repository type."""
        command_sets = {
            'nextjs-app': ['routes', 'models', 'audit', 'findings', 'impact'],
            'python-lib': ['verify', 'coverage', 'audit', 'analyze', 'graph'],
            'vivim-final': ['sync', 'analyze', 'audit', 'doctor', 'index'],
            'index': ['sync', 'analyze', 'audit', 'doctor', 'index'],
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
        
        output.append(f"║  Type: {context.repository.repo_type:12} Health: {str(health):3}/100  Index: {index_status:6} ║")
        output.append(f"║  Git: {git_status:20} Files: {context.repository.file_count:6}              ║")
        output.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Suggestions
        if suggestions:
            output.append("║  🔥 Suggested Actions                                         ║")
            for i, suggestion in enumerate(suggestions[:3], 1):
                output.append(f"║  {i}. {suggestion[:55]} ║")
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
    
    def _get_base_help(self, command: str) -> str:
        """Get base help for command."""
        # This would call the existing help system
        # For now, return a placeholder
        return f"Help for {command}\n\nThis is a placeholder. The actual help system would be integrated here."
    
    def _get_classic_general_help(self) -> str:
        """Generate classic general help without context."""
        return """
CIP CLI v2.0 - Code Intelligence Platform

Available commands:
  cip audit          Run code quality audit
  cip search          Search codebase
  cip analyze         Analyze repository health
  cip sync            Sync repository index
  cip help            Show this help message
  cip interactive     Enter interactive mode
  cip workflow        Run guided workflow
  cip suggest         Get intelligent suggestions

For more information on a specific command, run:
  cip <command> --help

For classic help without context awareness, run:
  cip --help --classic
"""
    
    def _get_context_tips(self, command: str, context: UnifiedContext) -> List[str]:
        """Get context-specific tips for command."""
        tips = []
        
        if command == 'audit':
            if context.repository.git_state and context.repository.git_state.get('uncommitted_files', 0) > 0:
                tips.append("Use --diff to audit only changed files")
            if context.repository.repo_type == 'nextjs-app':
                tips.append("Use --framework=nextjs for Next.js specific rules")
        
        elif command == 'search':
            if context.session.current_directory:
                tips.append(f"Search is scoped to {context.session.current_directory}")
            if context.repository.repo_type == 'python-lib':
                tips.append("Use --file-types=py to focus on Python files")
        
        elif command == 'sync':
            if context.repository.git_state and context.repository.git_state.get('uncommitted_files', 0) > 0:
                tips.append("Use --include-uncommitted to include uncommitted files")
        
        return tips


def display_help(root: str, command: str = None, classic: bool = False):
    """Display help with context awareness."""
    from cipkg.context_manager import ContextManager
    
    context_manager = ContextManager(root)
    help_generator = ContextAwareHelpGenerator(context_manager)
    
    help_text = help_generator.generate_help(command, classic)
    print(help_text)


def display_suggestions(root: str, max_suggestions: int = 5):
    """Display intelligent suggestions."""
    from cipkg.context_manager import ContextManager
    from cipkg.suggestion_engine import SuggestionEngine
    from cipkg.base import load_config
    
    context_manager = ContextManager(root)
    config = load_config(root)
    
    context = context_manager.get_context()
    suggestion_engine = SuggestionEngine(root, config)
    
    suggestions = suggestion_engine.generate_suggestions(context, max_suggestions)
    
    if not suggestions:
        print("No suggestions at this time. Repository looks good!")
        return
    
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║  Intelligent Suggestions                                       ║")
    print("╠═══════════════════════════════════════════════════════════════╣")
    
    for i, suggestion in enumerate(suggestions, 1):
        priority_icon = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }.get(suggestion.priority.value, '⚪')
        
        print(f"║  {priority_icon} {i}. {suggestion.action}")
        print(f"║     Reason: {suggestion.reason}")
        print(f"║     Impact: {suggestion.impact}")
        print(f"║     Confidence: {int(suggestion.confidence * 100)}%")
        print("║")
    
    print("╚═══════════════════════════════════════════════════════════════╝")
