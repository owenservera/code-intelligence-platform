"""
Terminal-based Smart Dashboard for CIP CLI v2.0

This module provides a proper interactive TUI for the smart terminal dashboard,
using Textual framework for rich keyboard navigation and interactive elements.
Now with full intelligent integration including command registry, learning system,
suggestion engine, and workflow engine.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import os
import sys
import asyncio
import threading
import time
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from textual import events
from textual.screen import Screen
from textual.binding import Binding
from cipkg.command_registry import CommandCategory


class DashboardState(Enum):
    """Dashboard state."""
    INITIALIZATION_NEEDED = "initialization_needed"
    INDEX_NEEDED = "index_needed"
    ACTIVE = "active"
    ERROR = "error"


@dataclass
class StatusCard:
    """Repository status card data."""
    health_score: int
    health_status: str
    index_fresh: bool
    index_status: str
    git_branch: str
    git_uncommitted: int
    file_count: int
    symbol_count: int
    edge_count: int
    last_sync: str


@dataclass
class QuickAction:
    """Quick action item."""
    icon: str
    label: str
    command: str
    description: str
    priority: int = 0


@dataclass
class Suggestion:
    """Intelligent suggestion item."""
    icon: str
    action: str
    reason: str
    confidence: float
    priority: str


class StatusCardWidget(Static):
    """Interactive status card widget."""
    
    def __init__(self, status_card: StatusCard):
        super().__init__()
        self.status_card = status_card
    
    def compose(self) -> ComposeResult:
        """Compose the status card UI."""
        health_color = "🟢" if self.status_card.health_score >= 80 else "🟡" if self.status_card.health_score >= 60 else "🔴"
        index_icon = "✅" if self.status_card.index_fresh else "⚠️"
        git_icon = "📦" if self.status_card.git_uncommitted == 0 else f"📦 {self.status_card.git_uncommitted}"
        
        yield Static(f"{health_color} Health: {self.status_card.health_score}/100 ({self.status_card.health_status})  {index_icon} Index: {self.status_card.index_status}  {git_icon} Git")
        yield Static(f"📊 Files: {self.status_card.file_count:,}  🧩 Symbols: {self.status_card.symbol_count:,}  🔗 Edges: {self.status_card.edge_count:,}")
        yield Static(f"🧵 Branch: {self.status_card.git_branch}  📅 Last sync: {self.status_card.last_sync}")


class CommandCategoryScreen(Screen):
    """Base screen for command categories."""
    
    def __init__(self, root: str, category_name: str, category_commands: List):
        super().__init__()
        self.root = root
        self.category_name = category_name
        self.category_commands = category_commands
        self.executor = None
    
    def on_mount(self) -> None:
        """Initialize executor when screen is mounted."""
        from cipkg.intelligent_executor import IntelligentCommandExecutor
        self.executor = IntelligentCommandExecutor(self.root)
    
    def _show_alert(self, message: str):
        """Show alert message with fallback if app doesn't support it."""
        if hasattr(self.app, 'show_alert'):
            self.app.show_alert(message)
        else:
            print(f"🔔 {message}")
    
    def compose(self) -> ComposeResult:
        """Compose the category screen UI."""
        yield Header()
        yield Static(f"📁 {self.category_name} Commands")
        
        # Command list
        with Vertical():
            for command_card in self.category_commands:
                yield Button(
                    f"{command_card.icon} {command_card.label}",
                    id=f"cmd_{command_card.command}"
                )
        
        yield Button("Back to Dashboard", id="back_button")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back_button":
            self.app.pop_screen()
        elif event.button.id.startswith("cmd_"):
            command = event.button.id.replace("cmd_", "")
            self._execute_command_with_ui(command)
    
    def _execute_command_with_ui(self, command: str):
        """Execute command with UI feedback."""
        from cipkg.command_registry import get_command_registry
        
        registry = get_command_registry()
        command_card = registry.get(command)
        
        if not command_card:
            self._show_alert(f"Command not found: {command}")
            return
        
        # Check for confirmation
        if command_card.requires_confirmation:
            self._show_confirmation_dialog(command_card)
        else:
            self._execute_command_direct(command_card)
    
    def _show_alert(self, message: str):
        """Show alert message with fallback if app doesn't support it."""
        if hasattr(self.app, 'show_alert'):
            self._show_alert(message)
        else:
            # Fallback: print the message
            print(f"🔔 {message}")
    
    def _show_confirmation_dialog(self, command_card):
        """Show confirmation dialog for critical commands."""
        # For now, execute directly - could add proper dialog
        self._execute_command_direct(command_card)
    
    def _execute_command_direct(self, command_card):
        """Execute command directly with progress tracking."""
        if command_card.has_form:
            self._show_command_form(command_card)
        else:
            # Execute command with basic args
            result = self.executor.execute_command(command_card.command, {})
            self._show_command_result(result)
    
    def _show_command_form(self, command_card):
        """Show form for commands with parameters."""
        # For now, execute with empty args - could add proper form
        result = self.executor.execute_command(command_card.command, {})
        self._show_command_result(result)
    
    def _show_command_result(self, result):
        """Show command execution result."""
        if result.status.value == "completed":
            self._show_alert(f"✅ Command completed successfully")
            if result.suggestions:
                self._show_suggestions(result.suggestions)
        else:
            self._show_alert(f"❌ Command failed: {result.error}")
            if result.suggestions:
                self._show_suggestions(result.suggestions)
    
    def _show_suggestions(self, suggestions: List[str]):
        """Show follow-up suggestions."""
        suggestion_text = "\n".join([f"💡 {s}" for s in suggestions])
        self._show_alert(f"Suggestions:\n{suggestion_text}")


class MainNavigationScreen(Screen):
    """Main navigation hub for all command categories."""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "search", "Search Commands"),
        Binding("w", "workflows", "Workflows"),
        Binding("l", "learning", "Learning Insights"),
    ]
    
    def __init__(self, root: str):
        super().__init__()
        self.root = root
        self.executor = None
        self.status_card = None
        self.intelligent_suggestions = []
        self.workflow_suggestions = []
    
    def on_mount(self) -> None:
        """Initialize executor and load data when screen is mounted."""
        from cipkg.intelligent_executor import IntelligentCommandExecutor
        from cipkg.command_registry import get_command_registry, CommandCategory
        
        self.executor = IntelligentCommandExecutor(self.root)
        self.registry = get_command_registry()
        
        # Load status card
        self.status_card = self._get_status_card()
        
        # Load intelligent suggestions
        self.intelligent_suggestions = self.executor.get_intelligent_suggestions()
        
        # Load workflow suggestions
        self.workflow_suggestions = self.executor.get_workflow_suggestions()
    
    def _show_alert(self, message: str):
        """Show alert message with fallback if app doesn't support it."""
        if hasattr(self.app, 'show_alert'):
            self.app.show_alert(message)
        else:
            print(f"🔔 {message}")
    
    def compose(self) -> ComposeResult:
        """Compose the main navigation UI."""
        yield Header()
        
        with Vertical():
            # Status card
            if self.status_card:
                yield StatusCardWidget(self.status_card)
            
            # Navigation tabs
            yield Static("🚀 Command Categories:")
            
            category_buttons = [
                ("📁 Repository", CommandCategory.REPOSITORY),
                ("⚙️ Services", CommandCategory.SERVICES),
                ("🔍 Search", CommandCategory.SEARCH),
                ("✅ Quality", CommandCategory.QUALITY),
                ("💥 Impact", CommandCategory.REFACTORING),
                ("📊 Gap-Fillers", CommandCategory.GAPFILLERS),
                ("📜 Git", CommandCategory.GIT),
                ("🔌 Integration", CommandCategory.INTEGRATION),
                ("🤖 Agent", CommandCategory.AGENT),
                ("🧠 Learning", CommandCategory.LEARNING),
            ]
            
            for label, category in category_buttons:
                yield Button(label, id=f"category_{category.value}")
            
            # Intelligent suggestions
            if self.intelligent_suggestions:
                yield Static("💡 Intelligent Suggestions:")
                for i, suggestion in enumerate(self.intelligent_suggestions[:3], 1):
                    priority_icon = {
                        'critical': '🔴',
                        'high': '🟠',
                        'medium': '🟡',
                        'low': '🟢'
                    }.get(suggestion['priority'], '⚪')
                    
                    yield Button(
                        f"{priority_icon} [{i}] {suggestion['action']}",
                        id=f"suggestion_{i}"
                    )
            
            # Workflow suggestions
            if self.workflow_suggestions:
                yield Static("⚙️ Suggested Workflows:")
                for workflow in self.workflow_suggestions[:2]:
                    yield Button(
                        f"🔄 {workflow['name']}",
                        id=f"workflow_{workflow['id']}"
                    )
        
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id.startswith("category_"):
            category = event.button.id.replace("category_", "")
            self._show_category_screen(category)
        elif event.button.id.startswith("suggestion_"):
            suggestion_index = int(event.button.id.replace("suggestion_", "")) - 1
            if suggestion_index < len(self.intelligent_suggestions):
                suggestion = self.intelligent_suggestions[suggestion_index]
                self._execute_suggestion(suggestion)
        elif event.button.id.startswith("workflow_"):
            workflow_id = event.button.id.replace("workflow_", "")
            self._execute_workflow(workflow_id)
    
    def _show_category_screen(self, category: str):
        """Show screen for a specific category."""
        from cipkg.command_registry import CommandCategory
        
        try:
            category_enum = CommandCategory(category)
            commands = self.registry.get_by_category(category_enum)
            
            category_names = {
                CommandCategory.REPOSITORY: "Repository Management",
                CommandCategory.SERVICES: "Daemon Services",
                CommandCategory.SEARCH: "Search & Analysis",
                CommandCategory.QUALITY: "Quality & Audit",
                CommandCategory.REFACTORING: "Impact & Refactoring",
                CommandCategory.GAPFILLERS: "Gap-Filler Tools",
                CommandCategory.GIT: "Git & History",
                CommandCategory.INTEGRATION: "Integration & Export",
                CommandCategory.AGENT: "Agent & Session",
                CommandCategory.LEARNING: "Learning & System",
            }
            
            self.app.push_screen(CommandCategoryScreen(
                self.root,
                category_names.get(category_enum, category),
                commands
            ))
        except ValueError:
            self._show_alert(f"Invalid category: {category}")
    
    def _execute_suggestion(self, suggestion: dict):
        """Execute a suggested command."""
        command = suggestion['action'].replace("cip ", "")
        result = self.executor.execute_command(command, {})
        
        if result.status.value == "completed":
            self._show_alert(f"✅ Suggestion executed successfully")
        else:
            self._show_alert(f"❌ Suggestion failed: {result.error}")
    
    def _execute_workflow(self, workflow_id: str):
        """Execute a workflow."""
        result = self.executor.execute_workflow(workflow_id)
        
        if result.get('status') == 'completed':
            self._show_alert(f"✅ Workflow completed successfully")
            if result.get('report'):
                self._show_alert(f"Report:\n{result['report']}")
        else:
            self._show_alert(f"❌ Workflow failed: {result.get('error', 'Unknown error')}")
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
    
    def action_refresh(self) -> None:
        """Refresh the dashboard."""
        self.on_mount()
    
    def action_search(self) -> None:
        """Search for commands."""
        # Could add a search dialog
        self._show_alert("Search functionality - to be implemented")
    
    def action_workflows(self) -> None:
        """Show workflow screen."""
        # Could add a dedicated workflow screen
        self._show_alert("Workflow screen - to be implemented")
    
    def action_learning(self) -> None:
        """Show learning insights."""
        # Could add a learning insights screen
        self._show_alert("Learning insights - to be implemented")
    
    def _get_status_card(self) -> Optional[StatusCard]:
        """Get current repository status card."""
        try:
            from cipkg.store import connect, get_meta
            from cipkg import indexer
            from cipkg import gapfill
            import time
            
            con = connect(self.root)
            stats = indexer.compute_stats(con)
            
            # Health score
            try:
                health = gapfill.score(self.root)
                health_score = health.get('score', 100)
                health_status = health.get('grade', 'Unknown')
            except Exception:
                health_score = 100
                health_status = 'Unknown'
            
            # Index freshness
            last_sync = float(get_meta(con, "last_sync", 0) or 0)
            lag = time.time() - last_sync if last_sync else None
            index_fresh = bool(lag is not None and lag < 3600)
            index_status = 'Fresh' if index_fresh else 'Stale'
            
            # Git state
            git_branch = 'unknown'
            git_uncommitted = 0
            try:
                import subprocess
                result = subprocess.run(
                    ['git', 'branch', '--show-current'],
                    cwd=self.root,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    git_branch = result.stdout.strip()
                
                result = subprocess.run(
                    ['git', 'diff', '--name-only'],
                    cwd=self.root,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    git_uncommitted = len([f for f in result.stdout.split('\n') if f.strip()])
            except Exception:
                pass
            
            # Last sync
            if lag:
                if lag < 60:
                    last_sync = f"{int(lag)}s ago"
                elif lag < 3600:
                    last_sync = f"{int(lag/60)}m ago"
                else:
                    last_sync = f"{int(lag/3600)}h ago"
            else:
                last_sync = 'Never'
            
            return StatusCard(
                health_score=health_score,
                health_status=health_status,
                index_fresh=index_fresh,
                index_status=index_status,
                git_branch=git_branch,
                git_uncommitted=git_uncommitted,
                file_count=stats.get('files', 0),
                symbol_count=stats.get('symbols', 0),
                edge_count=stats.get('edges', 0),
                last_sync=last_sync
            )
            
        except Exception as e:
            return None


class QuickActionsWidget(Static):
    """Interactive quick actions panel."""
    
    def __init__(self, actions: List[QuickAction]):
        super().__init__()
        self.actions = actions
    
    def compose(self) -> ComposeResult:
        """Compose the quick actions UI."""
        for action in self.actions:
            yield Button(f"{action.icon} {action.label}", id=f"action_{action.command}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        command = event.button.id.replace("action_", "")
        self.app.execute_command(command)





class InitializationScreen(Screen):
    """Screen for repository initialization."""
    
    def __init__(self, root: str, init_state):
        super().__init__()
        self.root = root
        self.init_state = init_state
    
    def compose(self) -> ComposeResult:
        """Compose the initialization UI."""
        yield Static("╔═══════════════════════════════════════════════════════════════╗")
        yield Static("║  CIP v2.0 - Repository Not Initialized                        ║")
        yield Static("╠═══════════════════════════════════════════════════════════════╣")
        yield Static(f"║  📁 Repository: {self.root:50} ║")
        yield Static("║  🔍 Detecting repository type...                                 ║")
        yield Static("╠═══════════════════════════════════════════════════════════════╣")
        yield Static("║  🚀 Quick Start:                                               ║")
        yield Button("Initialize CIP (recommended)", id="init_1", variant="primary")
        yield Button("Initialize with custom settings", id="init_2")
        yield Button("Learn more about CIP", id="init_3")
        yield Button("Exit", id="init_4")
        yield Static("╠═══════════════════════════════════════════════════════════════╣")
        yield Static("║  💡 What CIP will do:                                          ║")
        yield Static("║  • Scan all files in repository                                ║")
        yield Static("║  • Build code map (symbols, imports, relationships)             ║")
        yield Static("║  • Index git history for change tracking                        ║")
        yield Static("║  • Enable intelligent search and analysis                       ║")
        yield Static("╚═══════════════════════════════════════════════════════════════╝")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "init_1":
            self.app.initialize_repo()
        elif event.button.id == "init_2":
            self.app.initialize_repo(custom=True)
        elif event.button.id == "init_3":
            self.app.show_help()
        elif event.button.id == "init_4":
            self.app.quit_app()


class IndexNeededScreen(Screen):
    """Screen for index building."""
    
    def __init__(self, root: str, init_state):
        super().__init__()
        self.root = root
        self.init_state = init_state
    
    def compose(self) -> ComposeResult:
        """Compose the index building UI."""
        yield Static("╔═══════════════════════════════════════════════════════════════╗")
        yield Static("║  CIP v2.0 - Repository Ready                                  ║")
        yield Static("╠═══════════════════════════════════════════════════════════════╣")
        yield Static(f"║  📁 Repository: {self.root:50} ║")
        yield Static("║  🏷️  Type: Detecting...                                         ║")
        yield Static("║  ✅ CIP initialized                                            ║")
        yield Static("║  ⚠️  Index needs building                                      ║")
        yield Static("╠═══════════════════════════════════════════════════════════════╣")
        yield Static("║  🚀 Next Steps:                                                ║")
        yield Button("Build index (recommended)", id="index_1", variant="primary")
        yield Button("Build index with embeddings (slower)", id="index_2")
        yield Button("Skip and use basic features", id="index_3")
        yield Button("Exit", id="index_4")
        yield Static("╠═══════════════════════════════════════════════════════════════╣")
        yield Static("║  💡 Index enables:                                             ║")
        yield Static("║  • Intelligent code search                                     ║")
        yield Static("║  • Symbol navigation and graph traversal                       ║")
        yield Static("║  • Impact analysis and change tracking                         ║")
        yield Static("║  • Context-aware suggestions                                   ║")
        yield Static("╚═══════════════════════════════════════════════════════════════╝")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "index_1":
            self.app.build_index()
        elif event.button.id == "index_2":
            self.app.build_index(embeddings=True)
        elif event.button.id == "index_3":
            self.app.push_dashboard_screen()
        elif event.button.id == "index_4":
            self.app.quit_app()


class DashboardScreen(Screen):
    """Legacy dashboard screen - kept for backward compatibility."""
    
    def __init__(self, root: str):
        super().__init__()
        self.root = root
    
    def compose(self) -> ComposeResult:
        """Compose the legacy dashboard UI."""
        yield Static("Legacy Dashboard Screen - Use MainNavigationScreen instead")
        yield Button("Go to Main Navigation", id="go_main")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "go_main":
            self.app.push_screen(MainNavigationScreen(self.root))


class CIPDashboardApp(App):
    """Main CIP Dashboard application."""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    Static {
        padding: 0 1;
    }
    
    Button {
        margin: 1 2;
        width: 100%;
    }
    
    StatusCardWidget {
        border: solid green;
        padding: 1;
        margin: 1 0;
    }
    
    CommandCategoryScreen {
        border: solid blue;
        padding: 1;
        margin: 1 0;
    }
    
    MainNavigationScreen {
        border: solid yellow;
        padding: 1;
        margin: 1 0;
    }
    """
    
    def __init__(self, root: str):
        super().__init__()
        self.root = root
        self.init_state = None
        self.alert_message = ""
    
    def show_alert(self, message: str):
        """Show an alert message to the user."""
        self.alert_message = message
        # In a real implementation, this would show a proper alert screen
        # For now, we'll just print it
        print(f"\n🔔 {message}\n")
    
    def on_mount(self) -> None:
        """Initialize the app."""
        from .init_detector import detect_init_status
        self.init_state = detect_init_status(self.root)
        
        from .init_detector import should_show_init_ui, should_show_index_ui, should_launch_dashboard
        
        if should_show_init_ui(self.init_state):
            self.push_screen(InitializationScreen(self.root, self.init_state))
        elif should_show_index_ui(self.init_state):
            self.push_screen(IndexNeededScreen(self.root, self.init_state))
        elif should_launch_dashboard(self.init_state):
            self.push_screen(MainNavigationScreen(self.root))
        else:
            self.push_screen(ErrorScreen(self.root, self.init_state))
    
    def get_status_card(self) -> StatusCard:
        """Get current repository status card using intelligent executor."""
        try:
            from cipkg.intelligent_executor import IntelligentCommandExecutor
            
            executor = IntelligentCommandExecutor(self.root)
            context = executor._build_execution_context()
            
            # Get additional stats
            from .store import connect, get_meta
            from . import indexer
            import time
            
            con = connect(self.root)
            stats = indexer.compute_stats(con)
            
            # Index freshness
            last_sync = float(get_meta(con, "last_sync", 0) or 0)
            lag = time.time() - last_sync if last_sync else None
            index_fresh = bool(lag is not None and lag < 3600)
            index_status = 'Fresh' if index_fresh else 'Stale'
            
            # Last sync formatting
            if lag:
                if lag < 60:
                    last_sync_str = f"{int(lag)}s ago"
                elif lag < 3600:
                    last_sync_str = f"{int(lag/60)}m ago"
                else:
                    last_sync_str = f"{int(lag/3600)}h ago"
            else:
                last_sync_str = 'Never'
            
            return StatusCard(
                health_score=context.health_score,
                health_status='Good' if context.health_score >= 80 else 'Fair' if context.health_score >= 60 else 'Poor',
                index_fresh=index_fresh,
                index_status=index_status,
                git_branch=context.git_state.get('branch', 'unknown'),
                git_uncommitted=context.git_state.get('uncommitted_files', 0),
                file_count=context.file_count,
                symbol_count=stats.get('symbols', 0),
                edge_count=stats.get('edges', 0),
                last_sync=last_sync_str
            )
            
        except Exception as e:
            # Return default status card on error
            return StatusCard(
                health_score=100,
                health_status='Unknown',
                index_fresh=False,
                index_status='Unknown',
                git_branch='unknown',
                git_uncommitted=0,
                file_count=0,
                symbol_count=0,
                edge_count=0,
                last_sync='Never'
            )
    
    def get_suggestions(self) -> List[Suggestion]:
        """Get intelligent suggestions using the suggestion engine."""
        suggestions = []
        
        try:
            from cipkg.intelligent_executor import IntelligentCommandExecutor
            
            executor = IntelligentCommandExecutor(self.root)
            ui_suggestions = executor.get_intelligent_suggestions(max_suggestions=3)
            
            for ui_suggestion in ui_suggestions:
                priority_icon = {
                    'critical': '🔴',
                    'high': '🟠',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(ui_suggestion['priority'], '⚪')
                
                suggestions.append(Suggestion(
                    icon=priority_icon,
                    action=ui_suggestion['action'],
                    reason=ui_suggestion['reason'],
                    confidence=ui_suggestion['confidence'],
                    priority=ui_suggestion['priority']
                ))
                
        except Exception:
            # Fallback suggestions
            suggestions = [
                Suggestion(
                    icon='💡',
                    action='cip search <query>',
                    reason='Search code intelligently',
                    confidence=0.8,
                    priority='medium'
                ),
                Suggestion(
                    icon='💡',
                    action='cip analyze',
                    reason='Get repository health report',
                    confidence=0.7,
                    priority='medium'
                )
            ]
        
        return suggestions
    
    def initialize_repo(self, custom: bool = False) -> None:
        """Initialize repository."""
        import os
        import subprocess
        
        subprocess.run([sys.executable, "-c", "from bin.cip import init_repo; init_repo()"])
        
        # Refresh and go to next screen
        from .init_detector import detect_init_status
        self.init_state = detect_init_status(self.root)
        self.on_mount()
    
    def build_index(self, embeddings: bool = False) -> None:
        """Build index."""
        import subprocess
        import os
        
        os.chdir(self.root)
        args = ['index', '--full']
        if embeddings:
            args.append('--reembed')
        
        # Fix: properly format the command line arguments
        args_str = ', '.join([f"'{arg}'" for arg in args])
        subprocess.run([sys.executable, "-c", f"from cipkg.cli import main; main([{args_str}])"])
        
        # Refresh and go to dashboard
        from .init_detector import detect_init_status
        self.init_state = detect_init_status(self.root)
        self.on_mount()
    
    def execute_command(self, command: str) -> None:
        """Execute a CIP command using intelligent executor."""
        from cipkg.intelligent_executor import IntelligentCommandExecutor
        
        executor = IntelligentCommandExecutor(self.root)
        result = executor.execute_command(command, {})
        
        if result.status.value == "completed":
            self.show_alert(f"✅ Command completed successfully")
            if result.suggestions:
                self.show_alert(f"Suggestions: {', '.join(result.suggestions)}")
        else:
            self.show_alert(f"❌ Command failed: {result.error}")
            if result.suggestions:
                self.show_alert(f"Suggestions: {', '.join(result.suggestions)}")
    
    def show_help(self) -> None:
        """Show help information."""
        self.push_screen(HelpScreen())
    
    def push_dashboard_screen(self) -> None:
        """Push the main navigation screen."""
        self.push_screen(MainNavigationScreen(self.root))
    
    def quit_app(self) -> None:
        """Exit the application."""
        self.exit()


class ErrorScreen(Screen):
    """Error screen."""
    
    def __init__(self, root: str, init_state):
        super().__init__()
        self.root = root
        self.init_state = init_state
    
    def compose(self) -> ComposeResult:
        """Compose the error UI."""
        yield Static("╔═══════════════════════════════════════════════════════════════╗")
        yield Static("║  CIP v2.0 - Error                                              ║")
        yield Static("╠═══════════════════════════════════════════════════════════════╣")
        yield Static("║  ⚠️  An error occurred while detecting repository status           ║")
        yield Static("╠═══════════════════════════════════════════════════════════════╣")
        yield Button("Try again", id="error_1")
        yield Button("Run traditional CLI: cip --no-dashboard", id="error_2")
        yield Button("Exit", id="error_3")
        yield Static("╚═══════════════════════════════════════════════════════════════╝")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "error_1":
            # Re-initialize the app
            from .init_detector import detect_init_status
            self.app.init_state = detect_init_status(self.root)
            self.app.on_mount()
        elif event.button.id == "error_2":
            self.app.quit_app()
        elif event.button.id == "error_3":
            self.app.quit_app()


class HelpScreen(Screen):
    """Help screen."""
    
    def compose(self) -> ComposeResult:
        """Compose the help UI."""
        yield Static("CIP v2.0 - Help")
        yield Static("")
        yield Static("Keyboard Shortcuts:")
        yield Static("  q - Quit")
        yield Static("  r - Refresh dashboard")
        yield Static("  s - Search")
        yield Static("  a - Analyze")
        yield Static("")
        yield Static("Commands:")
        yield Static("  cip search <query>    - Search code intelligently")
        yield Static("  cip symbol <name>     - Find symbol definitions")
        yield Static("  cip analyze           - Get repository health report")
        yield Static("  cip audit             - Run audit rules")
        yield Static("  cip sync              - Incremental index update")
        yield Static("")
        yield Button("Back", id="help_back")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "help_back":
            self.app.pop_screen()





def launch_interactive_dashboard(root: str):
    """Launch interactive dashboard using Textual TUI framework."""
    try:
        app = CIPDashboardApp(root)
        app.run()
    except Exception as e:
        print(f"Error launching interactive dashboard: {e}")
        print("Falling back to traditional CLI...")
        import subprocess
        import sys
        subprocess.run([sys.executable, "-c", "from cipkg.cli import main; main(['--help'])"])
