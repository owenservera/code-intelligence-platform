"""
Command Registry System for CIP Terminal Dashboard

This module provides a centralized registry for all CLI commands with metadata,
categorization, and UI integration capabilities.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class CommandCategory(Enum):
    """Command categories for UI organization."""
    REPOSITORY = "repository"
    SERVICES = "services"
    SEARCH = "search"
    QUALITY = "quality"
    REFACTORING = "refactoring"
    GAPFILLERS = "gapfillers"
    GIT = "git"
    INTEGRATION = "integration"
    AGENT = "agent"
    LEARNING = "learning"
    SYSTEM = "system"


class CommandPriority(Enum):
    """Command priority levels for UI ordering."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CommandParameter:
    """Represents a command parameter."""
    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None
    choices: Optional[List[str]] = None
    flag: bool = False


@dataclass
class CommandCard:
    """UI card representation of a command."""
    command: str
    icon: str
    label: str
    description: str
    category: CommandCategory
    priority: CommandPriority
    handler: Callable
    parameters: List[CommandParameter] = field(default_factory=list)
    has_form: bool = False
    long_running: bool = False
    requires_confirmation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class CommandRegistry:
    """Central registry for all CLI commands with UI metadata."""
    
    def __init__(self):
        self.commands: Dict[str, CommandCard] = {}
        self.categories: Dict[CommandCategory, List[str]] = {}
        self._initialize_commands()
    
    def _initialize_commands(self):
        """Initialize all CLI commands with UI metadata."""
        
        # Repository Management Commands
        self._register_repository_commands()
        
        # Daemon Services Commands
        self._register_service_commands()
        
        # Search & Analysis Commands
        self._register_search_commands()
        
        # Quality & Audit Commands
        self._register_quality_commands()
        
        # Impact & Refactoring Commands
        self._register_refactoring_commands()
        
        # Gap-Filler Commands
        self._register_gapfiller_commands()
        
        # Git Commands
        self._register_git_commands()
        
        # Integration Commands
        self._register_integration_commands()
        
        # Agent Commands
        self._register_agent_commands()
        
        # Learning Commands
        self._register_learning_commands()
        
        # System Commands
        self._register_system_commands()

        # Master Data Model Commands
        self._register_mdm_commands()
    
    def _register_repository_commands(self):
        """Register repository management commands."""
        
        self.register(CommandCard(
            command="init",
            icon="🚀",
            label="Initialize Repository",
            description="Set up CIP for new project",
            category=CommandCategory.REPOSITORY,
            priority=CommandPriority.CRITICAL,
            handler=self._handle_init,
            has_form=False,
            long_running=True,
            requires_confirmation=True
        ))
        
        self.register(CommandCard(
            command="upgrade",
            icon="⬆️",
            label="Upgrade Schema",
            description="Migrate schema + full reindex",
            category=CommandCategory.REPOSITORY,
            priority=CommandPriority.HIGH,
            handler=self._handle_upgrade,
            has_form=False,
            long_running=True,
            requires_confirmation=True
        ))
        
        self.register(CommandCard(
            command="sync",
            icon="🔄",
            label="Sync Index",
            description="Update index with latest changes",
            category=CommandCategory.REPOSITORY,
            priority=CommandPriority.HIGH,
            handler=self._handle_sync,
            has_form=False,
            long_running=True
        ))
        
        self.register(CommandCard(
            command="index",
            icon="📇",
            label="Build Index",
            description="Build or rebuild code index",
            category=CommandCategory.REPOSITORY,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_index,
            parameters=[
                CommandParameter("full", "bool", "Full reindex", False, False),
                CommandParameter("reembed", "bool", "Re-embed chunks", False, False)
            ],
            has_form=True,
            long_running=True
        ))
        
        self.register(CommandCard(
            command="rebuild",
            icon="🔨",
            label="Rebuild Index",
            description="Wipe and fully reindex",
            category=CommandCategory.REPOSITORY,
            priority=CommandPriority.LOW,
            handler=self._handle_rebuild,
            has_form=False,
            long_running=True,
            requires_confirmation=True
        ))
        
        self.register(CommandCard(
            command="vacuum",
            icon="🧹",
            label="Vacuum Database",
            description="Compact DB, prune old events",
            category=CommandCategory.REPOSITORY,
            priority=CommandPriority.LOW,
            handler=self._handle_vacuum,
            parameters=[
                CommandParameter("days", "int", "Days to keep", False, 30)
            ],
            has_form=True
        ))
    
    def _register_service_commands(self):
        """Register daemon and service commands."""
        
        self.register(CommandCard(
            command="daemon_start",
            icon="▶️",
            label="Start Daemon",
            description="Start background watcher + HTTP server",
            category=CommandCategory.SERVICES,
            priority=CommandPriority.HIGH,
            handler=self._handle_daemon_start,
            parameters=[
                CommandParameter("port", "int", "Port number", False, 8787),
                CommandParameter("interval", "float", "Watch interval", False, 1.0)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="daemon_stop",
            icon="⏹️",
            label="Stop Daemon",
            description="Stop background daemon",
            category=CommandCategory.SERVICES,
            priority=CommandPriority.HIGH,
            handler=self._handle_daemon_stop,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="daemon_status",
            icon="📊",
            label="Daemon Status",
            description="Check daemon health and status",
            category=CommandCategory.SERVICES,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_daemon_status,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="embed_ping",
            icon="🏓",
            label="Test Embeddings",
            description="Test daemon embedding latency",
            category=CommandCategory.SERVICES,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_embed_ping,
            parameters=[
                CommandParameter("count", "int", "Number of pings", False, 5)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="embedder",
            icon="🧠",
            label="Embedder Status",
            description="Embedding engine status + benchmark",
            category=CommandCategory.SERVICES,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_embedder,
            has_form=False
        ))
    
    def _register_search_commands(self):
        """Register search and analysis commands."""
        
        self.register(CommandCard(
            command="search",
            icon="🔍",
            label="Search Codebase",
            description="Intelligent code search",
            category=CommandCategory.SEARCH,
            priority=CommandPriority.HIGH,
            handler=self._handle_search,
            parameters=[
                CommandParameter("query", "str", "Search query", True),
                CommandParameter("k", "int", "Result count", False, 10)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="symbol",
            icon="🏷️",
            label="Find Symbol",
            description="Find symbol definitions and references",
            category=CommandCategory.SEARCH,
            priority=CommandPriority.HIGH,
            handler=self._handle_symbol,
            parameters=[
                CommandParameter("name", "str", "Symbol name", True)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="graph",
            icon="🔗",
            label="Code Graph",
            description="Visualize code relationships",
            category=CommandCategory.SEARCH,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_graph,
            parameters=[
                CommandParameter("id", "str", "Symbol ID", True),
                CommandParameter("direction", "str", "Graph direction", False, "both", 
                              choices=["both", "in", "out"]),
                CommandParameter("depth", "int", "Graph depth", False, 1)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="context",
            icon="📝",
            label="Get Context",
            description="Retrieve contextual information",
            category=CommandCategory.SEARCH,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_context,
            parameters=[
                CommandParameter("query", "str", "Query string", False),
                CommandParameter("symbol", "str", "Symbol name", False),
                CommandParameter("budget", "int", "Token budget", False)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="summary",
            icon="📄",
            label="Summarize",
            description="Generate code summaries",
            category=CommandCategory.SEARCH,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_summary,
            parameters=[
                CommandParameter("path", "str", "File path", False)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="analyze",
            icon="🔬",
            label="Analyze Repository",
            description="Comprehensive repository analysis",
            category=CommandCategory.SEARCH,
            priority=CommandPriority.HIGH,
            handler=self._handle_analyze,
            has_form=False,
            long_running=True
        ))
    
    def _register_quality_commands(self):
        """Register quality and audit commands."""
        
        self.register(CommandCard(
            command="audit",
            icon="🔍",
            label="Run Audit",
            description="Audit code quality and compliance",
            category=CommandCategory.QUALITY,
            priority=CommandPriority.HIGH,
            handler=self._handle_audit,
            parameters=[
                CommandParameter("file", "str", "Specific file", False),
                CommandParameter("diff", "bool", "Audit git diff", False, False)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="findings",
            icon="📋",
            label="View Findings",
            description="View audit findings and issues",
            category=CommandCategory.QUALITY,
            priority=CommandPriority.HIGH,
            handler=self._handle_findings,
            parameters=[
                CommandParameter("severity", "str", "Filter by severity", False),
                CommandParameter("rule", "str", "Filter by rule", False),
                CommandParameter("path", "str", "Filter by path", False),
                CommandParameter("limit", "int", "Result limit", False, 100),
                CommandParameter("structured", "bool", "Structured output", False, False)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="score",
            icon="📊",
            label="Health Score",
            description="Overall repository health score 0-100",
            category=CommandCategory.QUALITY,
            priority=CommandPriority.HIGH,
            handler=self._handle_score,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="verify",
            icon="✅",
            label="Verify",
            description="Verification gate: tests + typecheck + lint",
            category=CommandCategory.QUALITY,
            priority=CommandPriority.HIGH,
            handler=self._handle_verify,
            parameters=[
                CommandParameter("typecheck", "bool", "Run typecheck", False, False),
                CommandParameter("lint", "bool", "Run lint", False, False),
                CommandParameter("no_audit", "bool", "Skip audit", False, False),
                CommandParameter("blocking", "bool", "Exit 1 on failure", False, False)
            ],
            has_form=True,
            long_running=True
        ))
        
        self.register(CommandCard(
            command="gate",
            icon="🚪",
            label="Quality Gate",
            description="Quality gate: exit 1 on critical findings",
            category=CommandCategory.QUALITY,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_gate,
            has_form=False
        ))
    
    def _register_refactoring_commands(self):
        """Register impact and refactoring commands."""
        
        self.register(CommandCard(
            command="impact",
            icon="💥",
            label="Impact Analysis",
            description="Analyze change impact across codebase",
            category=CommandCategory.REFACTORING,
            priority=CommandPriority.HIGH,
            handler=self._handle_impact,
            parameters=[
                CommandParameter("target", "str", "Target file/symbol", False),
                CommandParameter("ref", "str", "Git reference", False),
                CommandParameter("depth", "int", "Analysis depth", False, 2),
                CommandParameter("structured", "bool", "Structured output", False, False)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="refactors",
            icon="🔧",
            label="Quick Refactors",
            description="Top quick-win refactoring suggestions",
            category=CommandCategory.REFACTORING,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_refactors,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="dead",
            icon="💀",
            label="Dead Code",
            description="Dead code / unused symbol detection",
            category=CommandCategory.REFACTORING,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_dead,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="circular",
            icon="🔄",
            label="Circular Dependencies",
            description="Circular dependency detection",
            category=CommandCategory.REFACTORING,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_circular,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="deps",
            icon="📦",
            label="Dependency Graph",
            description="Dependency graph + audit",
            category=CommandCategory.REFACTORING,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_deps,
            has_form=False
        ))
    
    def _register_gapfiller_commands(self):
        """Register gap-filler analysis commands."""
        
        self.register(CommandCard(
            command="coverage",
            icon="📈",
            label="Test Coverage",
            description="Test coverage signals analysis",
            category=CommandCategory.GAPFILLERS,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_coverage,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="migrations",
            icon="🔄",
            label="DB Migrations",
            description="Database migration inventory",
            category=CommandCategory.GAPFILLERS,
            priority=CommandPriority.LOW,
            handler=self._handle_migrations,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="env",
            icon="🔧",
            label="Environment Variables",
            description="Environment variable inventory",
            category=CommandCategory.GAPFILLERS,
            priority=CommandPriority.LOW,
            handler=self._handle_env,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="logs",
            icon="📝",
            label="Logging Patterns",
            description="Logging pattern analysis",
            category=CommandCategory.GAPFILLERS,
            priority=CommandPriority.LOW,
            handler=self._handle_logs,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="metrics",
            icon="📊",
            label="Metrics Status",
            description="Metrics/observability status",
            category=CommandCategory.GAPFILLERS,
            priority=CommandPriority.LOW,
            handler=self._handle_metrics,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="features",
            icon="🚩",
            label="Feature Flags",
            description="Feature flag inventory",
            category=CommandCategory.GAPFILLERS,
            priority=CommandPriority.LOW,
            handler=self._handle_features,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="api",
            icon="🔌",
            label="API Contracts",
            description="API contract inventory",
            category=CommandCategory.GAPFILLERS,
            priority=CommandPriority.LOW,
            handler=self._handle_api,
            has_form=False
        ))
    
    def _register_git_commands(self):
        """Register git integration commands."""
        
        self.register(CommandCard(
            command="git_index",
            icon="📚",
            label="Git Index",
            description="Index git history for change tracking",
            category=CommandCategory.GIT,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_git_index,
            parameters=[
                CommandParameter("depth", "int", "Commit depth", False)
            ],
            has_form=True,
            long_running=True
        ))
        
        self.register(CommandCard(
            command="hotspots",
            icon="🔥",
            label="Hotspots",
            description="Identify frequently changed files",
            category=CommandCategory.GIT,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_hotspots,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="history",
            icon="📜",
            label="File History",
            description="View file change history",
            category=CommandCategory.GIT,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_history,
            parameters=[
                CommandParameter("path", "str", "File path", True)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="blame",
            icon="👤",
            label="Git Blame",
            description="Git blame for file + line",
            category=CommandCategory.GIT,
            priority=CommandPriority.LOW,
            handler=self._handle_blame,
            parameters=[
                CommandParameter("path", "str", "File path", True),
                CommandParameter("line", "int", "Line number", False)
            ],
            has_form=True
        ))
    
    def _register_integration_commands(self):
        """Register integration and export commands."""
        
        self.register(CommandCard(
            command="ingest",
            icon="📥",
            label="Ingest Results",
            description="Ingest test results and other data",
            category=CommandCategory.INTEGRATION,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_ingest,
            parameters=[
                CommandParameter("kind", "str", "Data type", True, 
                              choices=["vitest", "jest", "pytest", "tsc", "generic", "eslint"]),
                CommandParameter("file", "str", "Input file", False, "-")
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="export",
            icon="📤",
            label="Export Data",
            description="Export index data in various formats",
            category=CommandCategory.INTEGRATION,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_export,
            parameters=[
                CommandParameter("format", "str", "Export format", False, "json",
                              choices=["json", "lsif", "markdown"]),
                CommandParameter("out", "str", "Output file", False)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="serve",
            icon="🌐",
            label="Start Server",
            description="Start HTTP API server",
            category=CommandCategory.INTEGRATION,
            priority=CommandPriority.HIGH,
            handler=self._handle_serve,
            parameters=[
                CommandParameter("port", "int", "Server port", False)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="mcp",
            icon="🔌",
            label="MCP Server",
            description="Start MCP server for AI integration",
            category=CommandCategory.INTEGRATION,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_mcp,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="tools",
            icon="🛠️",
            label="Available Tools",
            description="List available MCP tools",
            category=CommandCategory.INTEGRATION,
            priority=CommandPriority.LOW,
            handler=self._handle_tools,
            parameters=[
                CommandParameter("schema", "bool", "Show schema", False, False)
            ],
            has_form=True
        ))
    
    def _register_agent_commands(self):
        """Register agent integration commands."""
        
        self.register(CommandCard(
            command="session_start",
            icon="▶️",
            label="Start Session",
            description="Start agent session with repo context",
            category=CommandCategory.AGENT,
            priority=CommandPriority.HIGH,
            handler=self._handle_session_start,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="session_end",
            icon="⏹️",
            label="End Session",
            description="End session and collect learning data",
            category=CommandCategory.AGENT,
            priority=CommandPriority.HIGH,
            handler=self._handle_session_end,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="session_status",
            icon="📊",
            label="Session Status",
            description="Show active session status",
            category=CommandCategory.AGENT,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_session_status,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="predict",
            icon="🔮",
            label="Predict Context",
            description="Predict next context based on operation",
            category=CommandCategory.AGENT,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_predict,
            parameters=[
                CommandParameter("operation", "str", "Current operation", True),
                CommandParameter("symbol", "str", "Symbol name", False),
                CommandParameter("query", "str", "Query string", False)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="suggest_context",
            icon="💡",
            label="Suggest Context",
            description="Suggest context for file editing",
            category=CommandCategory.AGENT,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_suggest_context,
            parameters=[
                CommandParameter("path", "str", "File path", True),
                CommandParameter("line", "int", "Line number", False)
            ],
            has_form=True
        ))
        
        self.register(CommandCard(
            command="hook",
            icon="🪝",
            label="Agent Hooks",
            description="Manage agent integration hooks",
            category=CommandCategory.AGENT,
            priority=CommandPriority.LOW,
            handler=self._handle_hook,
            parameters=[
                CommandParameter("hook_type", "str", "Hook type", True,
                              choices=["post-edit", "pre-edit"]),
                CommandParameter("args", "list", "Hook arguments", False, [])
            ],
            has_form=True
        ))
    
    def _register_learning_commands(self):
        """Register learning loop commands."""
        
        self.register(CommandCard(
            command="learning_analyze",
            icon="📊",
            label="Analyze Sessions",
            description="Analyze recent sessions for patterns",
            category=CommandCategory.LEARNING,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_learning_analyze,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="learning_update",
            icon="🔄",
            label="Update Predictions",
            description="Update prediction confidence",
            category=CommandCategory.LEARNING,
            priority=CommandPriority.LOW,
            handler=self._handle_learning_update,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="learning_report",
            icon="📋",
            label="Learning Report",
            description="Generate comprehensive learning report",
            category=CommandCategory.LEARNING,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_learning_report,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="learning_patterns",
            icon="🔍",
            label="Detect Patterns",
            description="Detect agent-specific patterns",
            category=CommandCategory.LEARNING,
            priority=CommandPriority.LOW,
            handler=self._handle_learning_patterns,
            has_form=False
        ))
    
    def _register_system_commands(self):
        """Register system diagnostic commands."""
        
        self.register(CommandCard(
            command="doctor",
            icon="🏥",
            label="System Doctor",
            description="Check system health and diagnostics",
            category=CommandCategory.SYSTEM,
            priority=CommandPriority.HIGH,
            handler=self._handle_doctor,
            has_form=False
        ))
        
        self.register(CommandCard(
            command="selftest",
            icon="🧪",
            label="Self Test",
            description="Run system self-diagnostic tests",
            category=CommandCategory.SYSTEM,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_selftest,
            has_form=False
        ))
    
    def register(self, command_card: CommandCard):
        """Register a command card."""
        self.commands[command_card.command] = command_card
        
        # Update category index
        if command_card.category not in self.categories:
            self.categories[command_card.category] = []
        self.categories[command_card.category].append(command_card.command)
    
    def get(self, command: str) -> Optional[CommandCard]:
        """Get command card by command name."""
        return self.commands.get(command)
    
    def get_by_category(self, category: CommandCategory) -> List[CommandCard]:
        """Get all commands in a category."""
        command_ids = self.categories.get(category, [])
        return [self.commands[cid] for cid in command_ids if cid in self.commands]
    
    def list_all(self) -> List[CommandCard]:
        """List all registered commands."""
        return list(self.commands.values())
    
    def search(self, query: str) -> List[CommandCard]:
        """Search commands by label, description, or command."""
        query = query.lower()
        results = []
        
        for command_card in self.commands.values():
            if (query in command_card.command.lower() or
                query in command_card.label.lower() or
                query in command_card.description.lower()):
                results.append(command_card)
        
        return results
    
    # Command handlers - these will be implemented to call the actual CLI handlers
    def _handle_init(self, root: str, args: dict) -> dict:
        """Handle init command."""
        try:
            from .cli import handle_init_command
            from argparse import Namespace
            return handle_init_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle init: {str(e)}'}
    
    def _handle_upgrade(self, root: str, args: dict) -> dict:
        """Handle upgrade command."""
        try:
            from .cli import handle_upgrade_command
            from argparse import Namespace
            return handle_upgrade_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle upgrade: {str(e)}'}
    
    def _handle_sync(self, root: str, args: dict) -> dict:
        """Handle sync command."""
        try:
            from .cli import handle_sync_command
            from argparse import Namespace
            return handle_sync_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle sync: {str(e)}'}
    
    def _handle_index(self, root: str, args: dict) -> dict:
        """Handle index command."""
        try:
            from .cli import handle_index_command
            from argparse import Namespace
            return handle_index_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle index: {str(e)}'}
    
    def _handle_rebuild(self, root: str, args: dict) -> dict:
        """Handle rebuild command."""
        try:
            from .cli import handle_rebuild_command
            from argparse import Namespace
            return handle_rebuild_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle rebuild: {str(e)}'}
    
    def _handle_vacuum(self, root: str, args: dict) -> dict:
        """Handle vacuum command."""
        try:
            from .cli import handle_vacuum_command
            from argparse import Namespace
            return handle_vacuum_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle vacuum: {str(e)}'}
    
    def _handle_daemon_start(self, root: str, args: dict) -> dict:
        """Handle daemon start command."""
        try:
            from .cli import handle_daemon_command
            from argparse import Namespace
            args['daemon_cmd'] = 'start'
            return handle_daemon_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle daemon start: {str(e)}'}
    
    def _handle_daemon_stop(self, root: str, args: dict) -> dict:
        """Handle daemon stop command."""
        try:
            from .cli import handle_daemon_command
            from argparse import Namespace
            args['daemon_cmd'] = 'stop'
            return handle_daemon_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle daemon stop: {str(e)}'}
    
    def _handle_daemon_status(self, root: str, args: dict) -> dict:
        """Handle daemon status command."""
        try:
            from .cli import handle_daemon_command
            from argparse import Namespace
            args['daemon_cmd'] = 'status'
            return handle_daemon_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle daemon status: {str(e)}'}
    
    def _handle_embed_ping(self, root: str, args: dict) -> dict:
        """Handle embed-ping command."""
        try:
            from .cli import cmd_embed_ping
            return cmd_embed_ping(root, args.get('count', 5))
        except Exception as e:
            return {'error': f'Failed to handle embed-ping: {str(e)}'}
    
    def _handle_embedder(self, root: str, args: dict) -> dict:
        """Handle embedder command."""
        try:
            from .cli import cmd_embedder
            return cmd_embedder(root)
        except Exception as e:
            return {'error': f'Failed to handle embedder: {str(e)}'}
    
    def _handle_search(self, root: str, args: dict) -> dict:
        """Handle search command."""
        try:
            from .cli import handle_search_command
            from argparse import Namespace
            return handle_search_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle search: {str(e)}'}
    
    def _handle_symbol(self, root: str, args: dict) -> dict:
        """Handle symbol command."""
        try:
            from .cli import handle_symbol_command
            from argparse import Namespace
            return handle_symbol_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle symbol: {str(e)}'}
    
    def _handle_graph(self, root: str, args: dict) -> dict:
        """Handle graph command."""
        try:
            from .cli import handle_graph_command
            from argparse import Namespace
            return handle_graph_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle graph: {str(e)}'}
    
    def _handle_context(self, root: str, args: dict) -> dict:
        """Handle context command."""
        try:
            from .cli import handle_context_command
            from argparse import Namespace
            return handle_context_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle context: {str(e)}'}
    
    def _handle_summary(self, root: str, args: dict) -> dict:
        """Handle summary command."""
        try:
            from .cli import handle_summary_command
            from argparse import Namespace
            return handle_summary_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle summary: {str(e)}'}
    
    def _handle_analyze(self, root: str, args: dict) -> dict:
        """Handle analyze command."""
        try:
            from .cli import handle_analyze_command
            from argparse import Namespace
            return handle_analyze_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle analyze: {str(e)}'}
    
    def _handle_audit(self, root: str, args: dict) -> dict:
        """Handle audit command."""
        try:
            from .cli import handle_audit_command
            from argparse import Namespace
            return handle_audit_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle audit: {str(e)}'}
    
    def _handle_findings(self, root: str, args: dict) -> dict:
        """Handle findings command."""
        try:
            from .cli import handle_findings_command
            from argparse import Namespace
            return handle_findings_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle findings: {str(e)}'}
    
    def _handle_score(self, root: str, args: dict) -> dict:
        """Handle score command."""
        try:
            from . import gapfill
            return gapfill.score(root)
        except Exception as e:
            return {'error': f'Failed to handle score: {str(e)}'}
    
    def _handle_verify(self, root: str, args: dict) -> dict:
        """Handle verify command."""
        try:
            from .cli import handle_verify_command
            from argparse import Namespace
            return handle_verify_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle verify: {str(e)}'}
    
    def _handle_gate(self, root: str, args: dict) -> dict:
        """Handle gate command."""
        try:
            from .cli import handle_gate_command
            from argparse import Namespace
            return handle_gate_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle gate: {str(e)}'}
    
    def _handle_impact(self, root: str, args: dict) -> dict:
        """Handle impact command."""
        try:
            from .cli import handle_impact_command
            from argparse import Namespace
            return handle_impact_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle impact: {str(e)}'}
    
    def _handle_refactors(self, root: str, args: dict) -> dict:
        """Handle refactors command."""
        try:
            from .cli import handle_refactors_command
            from argparse import Namespace
            return handle_refactors_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle refactors: {str(e)}'}
    
    def _handle_dead(self, root: str, args: dict) -> dict:
        """Handle dead command."""
        try:
            from .cli import handle_dead_command
            from argparse import Namespace
            return handle_dead_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle dead: {str(e)}'}
    
    def _handle_circular(self, root: str, args: dict) -> dict:
        """Handle circular command."""
        try:
            from .cli import handle_circular_command
            from argparse import Namespace
            return handle_circular_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle circular: {str(e)}'}
    
    def _handle_deps(self, root: str, args: dict) -> dict:
        """Handle deps command."""
        try:
            from .cli import handle_deps_command
            from argparse import Namespace
            return handle_deps_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle deps: {str(e)}'}
    
    def _handle_coverage(self, root: str, args: dict) -> dict:
        """Handle coverage command."""
        try:
            from .cli import handle_coverage_command
            from argparse import Namespace
            return handle_coverage_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle coverage: {str(e)}'}
    
    def _handle_migrations(self, root: str, args: dict) -> dict:
        """Handle migrations command."""
        try:
            from .cli import handle_migrations_command
            from argparse import Namespace
            return handle_migrations_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle migrations: {str(e)}'}
    
    def _handle_env(self, root: str, args: dict) -> dict:
        """Handle env command."""
        try:
            from .cli import handle_env_command
            from argparse import Namespace
            return handle_env_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle env: {str(e)}'}
    
    def _handle_logs(self, root: str, args: dict) -> dict:
        """Handle logs command."""
        try:
            from .cli import handle_logs_command
            from argparse import Namespace
            return handle_logs_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle logs: {str(e)}'}
    
    def _handle_metrics(self, root: str, args: dict) -> dict:
        """Handle metrics command."""
        try:
            from .cli import handle_metrics_command
            from argparse import Namespace
            return handle_metrics_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle metrics: {str(e)}'}
    
    def _handle_features(self, root: str, args: dict) -> dict:
        """Handle features command."""
        try:
            from .cli import handle_features_command
            from argparse import Namespace
            return handle_features_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle features: {str(e)}'}
    
    def _handle_api(self, root: str, args: dict) -> dict:
        """Handle api command."""
        try:
            from .cli import handle_api_command
            from argparse import Namespace
            return handle_api_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle api: {str(e)}'}
    
    def _handle_git_index(self, root: str, args: dict) -> dict:
        """Handle git-index command."""
        try:
            from .cli import handle_git_index_command
            from argparse import Namespace
            return handle_git_index_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle git-index: {str(e)}'}
    
    def _handle_hotspots(self, root: str, args: dict) -> dict:
        """Handle hotspots command."""
        try:
            from .cli import handle_hotspots_command
            from argparse import Namespace
            return handle_hotspots_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle hotspots: {str(e)}'}
    
    def _handle_history(self, root: str, args: dict) -> dict:
        """Handle history command."""
        try:
            from .cli import handle_history_command
            from argparse import Namespace
            return handle_history_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle history: {str(e)}'}
    
    def _handle_blame(self, root: str, args: dict) -> dict:
        """Handle blame command."""
        try:
            from .cli import handle_blame_command
            from argparse import Namespace
            return handle_blame_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle blame: {str(e)}'}
    
    def _handle_ingest(self, root: str, args: dict) -> dict:
        """Handle ingest command."""
        try:
            from .cli import handle_ingest_command
            from argparse import Namespace
            return handle_ingest_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle ingest: {str(e)}'}
    
    def _handle_export(self, root: str, args: dict) -> dict:
        """Handle export command."""
        try:
            from .cli import handle_export_command
            from argparse import Namespace
            return handle_export_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle export: {str(e)}'}
    
    def _handle_serve(self, root: str, args: dict) -> dict:
        """Handle serve command."""
        try:
            from .cli import handle_serve_command
            from argparse import Namespace
            return handle_serve_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle serve: {str(e)}'}
    
    def _handle_mcp(self, root: str, args: dict) -> dict:
        """Handle mcp command."""
        try:
            from .cli import handle_mcp_command
            from argparse import Namespace
            return handle_mcp_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle mcp: {str(e)}'}
    
    def _handle_tools(self, root: str, args: dict) -> dict:
        """Handle tools command."""
        try:
            from .cli import handle_tools_command
            from argparse import Namespace
            return handle_tools_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle tools: {str(e)}'}
    
    def _handle_session_start(self, root: str, args: dict) -> dict:
        """Handle session start command."""
        try:
            from .cli import handle_session_command
            from argparse import Namespace
            args['session_cmd'] = 'start'
            return handle_session_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle session start: {str(e)}'}
    
    def _handle_session_end(self, root: str, args: dict) -> dict:
        """Handle session end command."""
        try:
            from .cli import handle_session_command
            from argparse import Namespace
            args['session_cmd'] = 'end'
            return handle_session_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle session end: {str(e)}'}
    
    def _handle_session_status(self, root: str, args: dict) -> dict:
        """Handle session status command."""
        try:
            from .cli import handle_session_command
            from argparse import Namespace
            args['session_cmd'] = 'status'
            return handle_session_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle session status: {str(e)}'}
    
    def _handle_predict(self, root: str, args: dict) -> dict:
        """Handle predict command."""
        try:
            from .cli import handle_predict_command
            from argparse import Namespace
            return handle_predict_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle predict: {str(e)}'}
    
    def _handle_suggest_context(self, root: str, args: dict) -> dict:
        """Handle suggest-context command."""
        try:
            from .cli import handle_suggest_context_command
            from argparse import Namespace
            return handle_suggest_context_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle suggest-context: {str(e)}'}
    
    def _handle_hook(self, root: str, args: dict) -> dict:
        """Handle hook command."""
        try:
            from .cli import handle_hook_command
            from argparse import Namespace
            return handle_hook_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle hook: {str(e)}'}
    
    def _handle_learning_analyze(self, root: str, args: dict) -> dict:
        """Handle learning analyze command."""
        try:
            from .cli import handle_learning_command
            from argparse import Namespace
            args['learning_cmd'] = 'analyze'
            return handle_learning_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle learning analyze: {str(e)}'}
    
    def _handle_learning_update(self, root: str, args: dict) -> dict:
        """Handle learning update command."""
        try:
            from .cli import handle_learning_command
            from argparse import Namespace
            args['learning_cmd'] = 'update'
            return handle_learning_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle learning update: {str(e)}'}
    
    def _handle_learning_report(self, root: str, args: dict) -> dict:
        """Handle learning report command."""
        try:
            from .cli import handle_learning_command
            from argparse import Namespace
            args['learning_cmd'] = 'report'
            return handle_learning_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle learning report: {str(e)}'}
    
    def _handle_learning_patterns(self, root: str, args: dict) -> dict:
        """Handle learning patterns command."""
        try:
            from .cli import handle_learning_command
            from argparse import Namespace
            args['learning_cmd'] = 'patterns'
            return handle_learning_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle learning patterns: {str(e)}'}
    
    def _handle_doctor(self, root: str, args: dict) -> dict:
        """Handle doctor command."""
        try:
            from .cli import handle_doctor_command
            from argparse import Namespace
            return handle_doctor_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle doctor: {str(e)}'}
    
    def _handle_selftest(self, root: str, args: dict) -> dict:
        """Handle selftest command."""
        try:
            from .cli import handle_selftest_command
            from argparse import Namespace
            return handle_selftest_command(root, Namespace(**args))
        except Exception as e:
            return {'error': f'Failed to handle selftest: {str(e)}'}

    def _register_mdm_commands(self):
        """Register Master Data Model (L0-LA) commands."""
        self.register(CommandCard(
            command="mdm_scan",
            icon="🧬",
            label="MDM Full Scan (L0-LA)",
            description="Run complete L0-LA extraction and synthesis",
            category=CommandCategory.QUALITY,
            priority=CommandPriority.HIGH,
            handler=self._handle_mdm_scan,
            has_form=False
        ))

        self.register(CommandCard(
            command="mdm_report",
            icon="📊",
            label="MDM Executive Report",
            description="Generate comprehensive forensic scorecard and dossier",
            category=CommandCategory.QUALITY,
            priority=CommandPriority.HIGH,
            handler=self._handle_mdm_report,
            parameters=[
                CommandParameter("markdown", "bool", "Output in markdown", False, False, flag=True)
            ],
            has_form=True
        ))

        self.register(CommandCard(
            command="mdm_gaps",
            icon="🗺️",
            label="MDM Wiring Gaps",
            description="Scan silent IPC and event wiring gaps",
            category=CommandCategory.QUALITY,
            priority=CommandPriority.HIGH,
            handler=self._handle_mdm_gaps,
            has_form=False
        ))

        self.register(CommandCard(
            command="mdm_trace",
            icon="🔍",
            label="MDM Explainability Trace",
            description="View step-by-step evidence chain for a finding",
            category=CommandCategory.QUALITY,
            priority=CommandPriority.MEDIUM,
            handler=self._handle_mdm_trace,
            parameters=[
                CommandParameter("finding_id", "str", "Finding ID (e.g. LA-GAP-...)", True)
            ],
            has_form=True
        ))

    def _handle_mdm_scan(self, root: str, args: dict) -> dict:
        """Handle MDM scan."""
        try:
            from .mdm_engine import run_mdm_extraction
            from .mdm_synthesis import synthesize_la_findings
            from .store import connect
            con = connect(root)
            ext = run_mdm_extraction(root)
            syn = synthesize_la_findings(con, root)
            return {"extraction": ext, "findings_count": len(syn)}
        except Exception as e:
            return {"error": f"Failed to run MDM scan: {str(e)}"}

    def _handle_mdm_report(self, root: str, args: dict) -> dict:
        """Handle MDM report."""
        try:
            from .mdm_synthesis import generate_full_mdm_report
            return generate_full_mdm_report(root)
        except Exception as e:
            return {"error": f"Failed to generate MDM report: {str(e)}"}

    def _handle_mdm_gaps(self, root: str, args: dict) -> dict:
        """Handle MDM gaps."""
        try:
            from .mdm_engine import scan_l4_flow_and_wiring
            from .store import connect
            con = connect(root)
            return scan_l4_flow_and_wiring(con, root)
        except Exception as e:
            return {"error": f"Failed to scan MDM gaps: {str(e)}"}

    def _handle_mdm_trace(self, root: str, args: dict) -> dict:
        """Handle MDM trace."""
        try:
            from .mdm_schema import get_explainability_trace
            from .store import connect
            con = connect(root)
            fid = args.get("finding_id", "")
            return {"finding_id": fid, "trace": get_explainability_trace(con, fid)}
        except Exception as e:
            return {"error": f"Failed to fetch MDM trace: {str(e)}"}


# Global registry instance
_global_registry = None

def get_command_registry() -> CommandRegistry:
    """Get the global command registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = CommandRegistry()
    return _global_registry