"""
Interactive Mode Orchestrator for CIP CLI v2.0

This module provides the main entry point for interactive mode, integrating
all v2.0 features including context management, suggestions, workflows, learning,
and UI components.
"""
from __future__ import annotations

from cipkg.context_manager import ContextManager, UnifiedContext
from cipkg.suggestion_engine import SuggestionEngine
from cipkg.workflow_engine import WorkflowExecutor
from cipkg.learning_system import LearningSystem
from cipkg.command_adapter import ContextAwareCommand
from cipkg.help_system import ContextAwareHelpGenerator
from cipkg.error_system import handle_error_with_recovery, validate_preconditions
from cipkg.interactive_ui import (
    WelcomeScreen, SettingsScreen
)
from cipkg.base import load_config


class InteractiveMode:
    """Main interactive mode orchestrator."""
    
    def __init__(self, root: str):
        self.root = root
        self.config = load_config(root)
        self.context_manager = ContextManager(root)
        self.suggestion_engine = SuggestionEngine(root, self.config)
        self.workflow_executor = WorkflowExecutor(root, self.config)
        self.learning_system = LearningSystem(root)
        self.help_generator = ContextAwareHelpGenerator(self.context_manager)
        self.context_aware_command = ContextAwareCommand(root, self.config)
        
        # Check if interactive mode is enabled
        self.enabled = self.config.get('interactive', {}).get('enabled', True)
        self.mode = self.config.get('interactive', {}).get('mode', 'hybrid')
        
        # Current state
        self.current_screen = 'welcome'
        self.running = False
    
    def start(self):
        """Start interactive mode."""
        if not self.enabled:
            print("Interactive mode is disabled. Enable it in config.toml")
            return
        
        self.running = True
        self._run_interactive_loop()
    
    def _run_interactive_loop(self):
        """Main interactive loop."""
        context = self.context_manager.get_context()
        
        while self.running:
            try:
                if self.current_screen == 'welcome':
                    self._render_welcome_screen(context)
                    self._handle_welcome_input(context)
                elif self.current_screen == 'workflow':
                    self._render_workflow_screen(context)
                elif self.current_screen == 'search':
                    self._render_search_screen(context)
                elif self.current_screen == 'settings':
                    self._render_settings_screen(context)
                else:
                    self._render_welcome_screen(context)
                    
            except KeyboardInterrupt:
                print("\nExiting interactive mode...")
                self.running = False
            except Exception as e:
                print(f"Error: {e}")
                self.current_screen = 'welcome'
    
    def _render_welcome_screen(self, context: UnifiedContext):
        """Render welcome screen."""
        screen = WelcomeScreen.render(context)
        print(screen)
        
        # Show suggestions
        suggestions = self.suggestion_engine.generate_suggestions(context, max_suggestions=3)
        if suggestions:
            print("\n💡 Intelligent Suggestions:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion.action}")
                print(f"     {suggestion.reason}")
    
    def _handle_welcome_input(self, context: UnifiedContext):
        """Handle welcome screen input."""
        print("\nSelect an option or type a command: ", end='')
        user_input = input().strip()
        
        if user_input == '1':
            # Repository health check
            self._run_health_check()
        elif user_input == '2':
            # Search codebase
            self._run_search()
        elif user_input == '3':
            # Run workflow
            self._run_workflow_selection()
        elif user_input == '4':
            # Settings
            self.current_screen = 'settings'
        elif user_input.startswith('cip '):
            # Execute command
            self._execute_command(user_input[4:])
        elif user_input in ['q', 'quit', 'exit']:
            self.running = False
        else:
            print("Invalid option. Please try again.")
    
    def _render_workflow_screen(self, context: UnifiedContext):
        """Render workflow execution screen."""
        # This would show active workflow execution
        print("Workflow execution screen - to be implemented")
        self.current_screen = 'welcome'
    
    def _render_search_screen(self, context: UnifiedContext):
        """Render search results screen."""
        # This would show search results
        print("Search screen - to be implemented")
        self.current_screen = 'welcome'
    
    def _render_settings_screen(self, context: UnifiedContext):
        """Render settings screen."""
        settings_screen = SettingsScreen(self.config)
        print(settings_screen.render())
        print("\nPress ENTER to return to main menu: ", end='')
        input()
        self.current_screen = 'welcome'
    
    def _run_health_check(self):
        """Run repository health check."""
        print("\n🏥 Running repository health check...")
        
        try:
            from cipkg import gapfill
            health_score = gapfill.score(self.root)
            
            print(f"Health Score: {health_score.get('score', 'N/A')}/100")
            print(f"Broken Tests: {health_score.get('broken_tests', 0)}")
            print(f"Type Errors: {health_score.get('type_errors', 0)}")
            print(f"Lint Issues: {health_score.get('lint_issues', 0)}")
            
        except Exception as e:
            print(f"Health check failed: {e}")
    
    def _run_search(self):
        """Run intelligent search."""
        print("\n🔍 Enter search query: ", end='')
        query = input().strip()
        
        if query:
            print(f"Searching for: {query}")
            # This would integrate with the actual search functionality
            print("Search integration - to be implemented")
    
    def _run_workflow_selection(self):
        """Show workflow selection menu."""
        workflows = self.workflow_executor.registry.list_all()
        
        if not workflows:
            print("No workflows available")
            return
        
        print("\n⚙️  Available Workflows:")
        for i, workflow in enumerate(workflows, 1):
            print(f"  {i}. {workflow.name}")
            print(f"     {workflow.description}")
        
        print("\nSelect workflow number: ", end='')
        selection = input().strip()
        
        try:
            index = int(selection) - 1
            if 0 <= index < len(workflows):
                self._execute_workflow(workflows[index].id)
            else:
                print("Invalid selection")
        except ValueError:
            print("Invalid input")
    
    def _execute_workflow(self, workflow_id: str):
        """Execute a workflow."""
        print(f"\n⚙️  Executing workflow: {workflow_id}")
        
        try:
            execution = self.workflow_executor.execute(workflow_id)
            
            print(f"Workflow status: {execution.status.value}")
            
            # Show step results
            for step_id, step_exec in execution.steps.items():
                status_icon = "✅" if step_exec.status.value == "completed" else "❌"
                print(f"  {status_icon} {step_id}: {step_exec.status.value}")
            
            # Show final report if available
            if execution.context.get('report'):
                print(f"\n{execution.context['report']}")
                
        except Exception as e:
            print(f"Workflow execution failed: {e}")
    
    def _execute_command(self, command_str: str):
        """Execute a command with context awareness."""
        parts = command_str.split()
        if not parts:
            return
        
        command = parts[0]
        args = parts[1:]
        
        # Get current context
        context = self.context_manager.get_context()
        context_dict = {
            'repo_type': context.repository.repo_type,
            'git_state': context.repository.git_state,
            'index_status': context.repository.index_status,
            'file_count': context.repository.file_count,
            'recent_files': context.repository.recent_files
        }
        
        # Validate preconditions
        validation = validate_preconditions(command, {'args': args}, self.root)
        if validation['warnings']:
            print("\n⚠️  Warnings:")
            for warning in validation['warnings']:
                print(f"  • {warning}")
            
            if validation['preventive_actions']:
                print("\n💡 Suggested actions:")
                for action in validation['preventive_actions']:
                    print(f"  • {action}")
            
            print("\nContinue? [Y/n]: ", end='')
            response = input().strip().lower()
            if response in ['n', 'no']:
                print("Command cancelled")
                return
        
        # Apply command adaptations
        try:
            adapted_result = self.context_aware_command.execute(command, args, context_dict)
            
            if adapted_result.get('adapted'):
                print("✅ Command executed with adaptations")
            else:
                print("✅ Command executed")
                
        except Exception as e:
            # Handle error with recovery
            result = handle_error_with_recovery(e, command, {'args': args}, self.root, self.context_manager)
            
            if not result.get('recovered'):
                print(f"❌ Command failed: {e}")
        
        # Record action for learning
        try:
            self.learning_system.record_action({
                'action_type': 'command',
                'user_id': 'default',
                'repo_id': context.repository.repo_name,
                'command': command,
                'arguments': {'args': args},
                'context': context_dict,
                'success': True
            })
        except Exception:
            pass  # Don't fail if learning is unavailable


def start_interactive_mode(root: str):
    """Start interactive mode for the given repository."""
    interactive = InteractiveMode(root)
    interactive.start()


def show_context_aware_help(root: str, command: str = None, classic: bool = False):
    """Show context-aware help."""
    from cipkg.help_system import display_help
    display_help(root, command, classic)


def show_suggestions(root: str, max_suggestions: int = 5):
    """Show intelligent suggestions."""
    from cipkg.help_system import display_suggestions
    display_suggestions(root, max_suggestions)


def execute_workflow_cli(root: str, workflow_id: str, resume: bool = False):
    """Execute a workflow from CLI."""
    from cipkg.workflow_engine import execute_workflow
    from cipkg.base import load_config
    
    config = load_config(root)
    execution = execute_workflow(root, workflow_id, config, resume)
    
    print(f"Workflow {workflow_id} completed with status: {execution.status.value}")
    
    # Show step results
    for step_id, step_exec in execution.steps.items():
        status_icon = "✅" if step_exec.status.value == "completed" else "❌"
        print(f"  {status_icon} {step_id}: {step_exec.status.value}")
    
    # Show final report if available
    if execution.context.get('report'):
        print(f"\n{execution.context['report']}")


def list_available_workflows(root: str):
    """List available workflows."""
    from cipkg.workflow_engine import list_workflows
    from cipkg.base import load_config
    
    config = load_config(root)
    workflows = list_workflows(root, config)
    
    print("Available Workflows:")
    for workflow in workflows:
        print(f"  • {workflow.id}: {workflow.name}")
        print(f"    {workflow.description}")
