"""
Pytest configuration and fixtures for terminal dashboard testing.

This module provides reusable fixtures and utilities for testing the Textual-based
terminal dashboard including mocks for external dependencies and test data.
"""

import pytest
import asyncio
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Optional
from dataclasses import dataclass

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from cipkg.terminal_dashboard import (
    StatusCard,
    QuickAction,
    Suggestion,
    StatusCardWidget,
    CommandCategoryScreen,
    MainNavigationScreen,
    InitializationScreen,
    IndexNeededScreen,
    DashboardScreen,
    CIPDashboardApp,
    ErrorScreen,
    HelpScreen,
    DashboardState
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_repo_dir():
    """Create a temporary repository directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        # Create basic repo structure
        (repo_path / ".git").mkdir(exist_ok=True)
        (repo_path / "src").mkdir(exist_ok=True)
        (repo_path / "lib").mkdir(exist_ok=True)
        yield str(repo_path)


@pytest.fixture
def mock_status_card():
    """Provide a mock status card for testing."""
    return StatusCard(
        health_score=85,
        health_status="Good",
        index_fresh=True,
        index_status="Fresh",
        git_branch="main",
        git_uncommitted=0,
        file_count=150,
        symbol_count=2500,
        edge_count=5000,
        last_sync="5m ago"
    )


@pytest.fixture
def mock_quick_actions():
    """Provide mock quick actions for testing."""
    return [
        QuickAction(
            icon="🚀",
            label="Quick Search",
            command="search",
            description="Search code intelligently",
            priority=1
        ),
        QuickAction(
            icon="📊",
            label="Analyze",
            command="analyze",
            description="Get repository health report",
            priority=2
        )
    ]


@pytest.fixture
def mock_suggestions():
    """Provide mock intelligent suggestions for testing."""
    return [
        Suggestion(
            icon="🔴",
            action="cip sync",
            reason="Index is stale, needs refresh",
            confidence=0.9,
            priority="critical"
        ),
        Suggestion(
            icon="🟡",
            action="cip audit",
            reason="Quality checks not run recently",
            confidence=0.7,
            priority="medium"
        )
    ]


@pytest.fixture
def mock_workflow_suggestions():
    """Provide mock workflow suggestions for testing."""
    return [
        {
            "id": "daily_sync",
            "name": "Daily Sync Workflow",
            "description": "Sync index and run quick health check"
        },
        {
            "id": "full_audit",
            "name": "Full Audit Workflow",
            "description": "Comprehensive code quality audit"
        }
    ]


@pytest.fixture
def mock_command_cards():
    """Provide mock command cards for testing."""
    @dataclass
    class CommandCard:
        icon: str
        label: str
        command: str
        description: str
        requires_confirmation: bool = False
        has_form: bool = False

    return [
        CommandCard(
            icon="🔍",
            label="Search",
            command="search",
            description="Search code intelligently"
        ),
        CommandCard(
            icon="📊",
            label="Analyze",
            command="analyze",
            description="Get repository health report"
        )
    ]


@pytest.fixture
def mock_intelligent_executor():
    """Provide a mock intelligent command executor."""
    executor = MagicMock()
    executor.get_intelligent_suggestions = Mock(return_value=[
        {
            "action": "cip sync",
            "reason": "Index is stale",
            "confidence": 0.9,
            "priority": "critical"
        }
    ])
    executor.get_workflow_suggestions = Mock(return_value=[
        {
            "id": "daily_sync",
            "name": "Daily Sync",
            "description": "Sync and health check"
        }
    ])
    executor.execute_command = Mock(return_value=MagicMock(
        status=MagicMock(value="completed"),
        error=None,
        suggestions=["Run audit"]
    ))
    executor.execute_workflow = Mock(return_value={
        "status": "completed",
        "report": "Workflow completed successfully"
    })
    return executor


@pytest.fixture
def mock_command_registry():
    """Provide a mock command registry."""
    registry = MagicMock()
    
    @dataclass
    class CommandCard:
        icon: str
        label: str
        command: str
        description: str
        requires_confirmation: bool = False
        has_form: bool = False

    # Mock get method
    def mock_get(command: str):
        commands = {
            "search": CommandCard("🔍", "Search", "search", "Search code"),
            "analyze": CommandCard("📊", "Analyze", "analyze", "Health report")
        }
        return commands.get(command)

    registry.get = mock_get
    
    # Mock get_by_category method
    def mock_get_by_category(category):
        return [
            CommandCard("🔍", "Search", "search", "Search code"),
            CommandCard("📊", "Analyze", "analyze", "Health report")
        ]

    registry.get_by_category = mock_get_by_category
    
    return registry


@pytest.fixture
def mock_init_state():
    """Provide mock initialization state."""
    return {
        "initialized": True,
        "indexed": True,
        "healthy": True,
        "git_available": True
    }


# ============================================================================
# Mock Patches
# ============================================================================

@pytest.fixture
def mock_cipkg_dependencies():
    """Mock all cipkg dependencies for isolated testing."""
    with patch('cipkg.terminal_dashboard.IntelligentCommandExecutor') as mock_executor_class, \
         patch('cipkg.terminal_dashboard.get_command_registry') as mock_registry_get, \
         patch('cipkg.terminal_dashboard.detect_init_status') as mock_detect, \
         patch('cipkg.terminal_dashboard.should_show_init_ui', return_value=False), \
         patch('cipkg.terminal_dashboard.should_show_index_ui', return_value=False), \
         patch('cipkg.terminal_dashboard.should_launch_dashboard', return_value=True):
        
        # Setup mock executor
        mock_executor = MagicMock()
        mock_executor.get_intelligent_suggestions = Mock(return_value=[])
        mock_executor.get_workflow_suggestions = Mock(return_value=[])
        mock_executor_class.return_value = mock_executor
        
        # Setup mock registry
        registry = MagicMock()
        registry.get = Mock(return_value=None)
        registry.get_by_category = Mock(return_value=[])
        mock_registry_get.return_value = registry
        
        # Setup mock detect
        mock_detect.return_value = {
            "initialized": True,
            "indexed": True,
            "healthy": True
        }
        
        yield {
            "executor": mock_executor,
            "registry": registry,
            "detect": mock_detect
        }


@pytest.fixture
def mock_git_operations():
    """Mock git operations for testing."""
    with patch('subprocess.run') as mock_run:
        def mock_subprocess_run(args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            
            if 'branch' in args and 'show-current' in args:
                result.stdout = "main"
            elif 'diff' in args and 'name-only' in args:
                result.stdout = ""
            
            return result

        mock_run.side_effect = mock_subprocess_run
        yield mock_run


@pytest.fixture
def mock_database_operations():
    """Mock database operations for testing."""
    with patch('cipkg.terminal_dashboard.connect') as mock_connect, \
         patch('cipkg.terminal_dashboard.get_meta') as mock_get_meta, \
         patch('cipkg.terminal_dashboard.indexer') as mock_indexer, \
         patch('cipkg.terminal_dashboard.gapfill') as mock_gapfill:
        
        # Setup mock database connection
        mock_con = MagicMock()
        mock_connect.return_value = mock_con
        
        # Setup mock metadata
        mock_get_meta.return_value = "1692134567.0"  # timestamp
        
        # Setup mock indexer
        mock_indexer.compute_stats = Mock(return_value={
            "files": 150,
            "symbols": 2500,
            "edges": 5000
        })
        
        # Setup mock gapfill
        mock_gapfill.score = Mock(return_value={
            "score": 85,
            "grade": "Good"
        })
        
        yield {
            "connect": mock_connect,
            "get_meta": mock_get_meta,
            "indexer": mock_indexer,
            "gapfill": mock_gapfill
        }


# ============================================================================
# Test Utilities
# ============================================================================

class DashboardTestHelper:
    """Helper class for common dashboard testing operations."""
    
    @staticmethod
    async def wait_for_mount(app, timeout: float = 2.0):
        """Wait for app to be fully mounted."""
        await asyncio.sleep(0.1)  # Small delay for mount to complete
    
    @staticmethod
    def get_widget_by_id(screen, widget_id: str):
        """Get a widget by its ID from a screen."""
        return screen.query_one(f"#{widget_id}")
    
    @staticmethod
    def get_all_buttons(screen):
        """Get all buttons from a screen."""
        return screen.query(Button)
    
    @staticmethod
    def assert_button_exists(screen, button_id: str):
        """Assert that a button with given ID exists."""
        button = screen.query_one(f"#{button_id}")
        assert button is not None, f"Button {button_id} not found"
        return button
    
    @staticmethod
    def assert_screen_is_current(app, screen_class):
        """Assert that a specific screen class is currently active."""
        assert isinstance(app.screen, screen_class), \
            f"Expected {screen_class.__name__}, got {type(app.screen).__name__}"


@pytest.fixture
def dashboard_helper():
    """Provide the dashboard test helper utility."""
    return DashboardTestHelper()


# ============================================================================
# Async Test Support
# ============================================================================

@pytest.fixture(scope="session")
def event_loop_policy():
    """Set up event loop policy for async tests."""
    policy = asyncio.WindowsProactorEventLoopPolicy() if sys.platform == "win32" else asyncio.DefaultEventLoopPolicy()
    asyncio.set_event_loop_policy(policy)
    yield policy
    asyncio.set_event_loop_policy(None)