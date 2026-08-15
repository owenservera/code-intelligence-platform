"""
Shared pytest configuration and fixtures for terminal dashboard tests.
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass
import sys

# Import dashboard components
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

# Import bug report generator for automated bug detection
sys.path.insert(0, str(Path(__file__).parent))
from bug_report_generator import bug_generator

from cipkg.terminal_dashboard import (
    StatusCard,
    QuickAction,
    Suggestion,
    DashboardState,
    StatusCardWidget,
    QuickActionsWidget,
    MainNavigationScreen,
    CommandCategoryScreen,
    InitializationScreen,
    IndexNeededScreen
)


@pytest.fixture
def temp_repo_dir():
    """Create a temporary directory for testing repository operations."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    # Clean up manually to avoid Windows file locking issues
    import shutil
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception:
        pass  # Best effort cleanup


@pytest.fixture
def mock_status_card():
    """Create a mock StatusCard for testing."""
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
        last_sync="2m ago"
    )


@pytest.fixture
def mock_quick_actions():
    """Create mock QuickAction items for testing."""
    return [
        QuickAction(
            icon="🔄",
            label="Sync Index",
            command="sync",
            description="Update index with latest changes",
            priority=1
        ),
        QuickAction(
            icon="🔍",
            label="Search",
            command="search",
            description="Search codebase",
            priority=2
        ),
        QuickAction(
            icon="✅",
            label="Verify",
            command="verify",
            description="Run quality checks",
            priority=3
        )
    ]


@pytest.fixture
def mock_suggestions():
    """Create mock Suggestion items for testing."""
    return [
        Suggestion(
            icon="💡",
            action="cip sync",
            reason="Index is stale, sync recommended",
            confidence=0.9,
            priority="high"
        ),
        Suggestion(
            icon="🔧",
            action="cip verify",
            reason="Recent changes detected, verification recommended",
            confidence=0.75,
            priority="medium"
        )
    ]


@pytest.fixture
def mock_command_registry():
    """Create a mock command registry for testing."""
    from cipkg.command_registry import CommandRegistry, CommandCard, CommandCategory, CommandPriority
    
    registry = Mock(spec=CommandRegistry)
    
    # Mock some common commands
    mock_init_card = CommandCard(
        command="init",
        icon="🚀",
        label="Initialize Repository",
        description="Set up CIP for new project",
        category=CommandCategory.REPOSITORY,
        priority=CommandPriority.CRITICAL,
        handler=Mock(return_value={"status": "success"}),
        has_form=False,
        long_running=True,
        requires_confirmation=True
    )
    
    mock_sync_card = CommandCard(
        command="sync",
        icon="🔄",
        label="Sync Index",
        description="Update index with latest changes",
        category=CommandCategory.REPOSITORY,
        priority=CommandPriority.HIGH,
        handler=Mock(return_value={"status": "success"}),
        has_form=False,
        long_running=True
    )
    
    registry.get = Mock(side_effect=lambda cmd: {
        "init": mock_init_card,
        "sync": mock_sync_card
    }.get(cmd))
    
    registry.get_by_category = Mock(return_value=[mock_sync_card])
    
    return registry


@pytest.fixture
def mock_executor():
    """Create a mock intelligent executor for testing."""
    from cipkg.intelligent_executor import IntelligentCommandExecutor, ExecutionResult, ExecutionStatus
    
    executor = Mock(spec=IntelligentCommandExecutor)
    
    # Mock successful execution
    executor.execute_command = Mock(return_value=ExecutionResult(
        status=ExecutionStatus.COMPLETED,
        output="Command completed successfully",
        execution_time=1.5
    ))
    
    # Mock intelligent suggestions
    executor.get_intelligent_suggestions = Mock(return_value=[
        {
            "action": "cip sync",
            "reason": "Index is stale",
            "confidence": 0.9,
            "priority": "high"
        }
    ])
    
    # Mock workflow suggestions
    executor.get_workflow_suggestions = Mock(return_value=[
        {
            "id": "daily_sync",
            "name": "Daily Sync Workflow",
            "description": "Sync and verify repository"
        }
    ])
    
    return executor


@pytest.fixture 
def mock_git_state():
    """Create mock git state for testing."""
    return {
        "branch": "main",
        "on_main": True,
        "uncommitted_files": 0
    }


@pytest.fixture
def sample_dashboard_state():
    """Provide sample dashboard states for testing."""
    return {
        "initialization_needed": DashboardState.INITIALIZATION_NEEDED,
        "index_needed": DashboardState.INDEX_NEEDED,
        "active": DashboardState.ACTIVE,
        "error": DashboardState.ERROR
    }


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls for git and other external commands."""
    with pytest.mock.patch("subprocess.run") as mock_run:
        # Mock successful git branch command
        mock_run.return_value = Mock(
            returncode=0,
            stdout="main\n",
            stderr=""
        )
        yield mock_run


# Pytest hooks for automated bug report generation
def pytest_runtest_logreport(report):
    """Pytest hook to capture test failures and generate bug reports."""
    if report.when == "call" and report.failed:
        test_name = f"{report.module.__name__}::{report.nodeid}" if hasattr(report, 'module') else report.nodeid
        error_type = report.outcome
        error_message = str(report.longrepr) if report.longrepr else "Unknown error"
        traceback_str = report.longreprtext if report.longreprtext else "No traceback"
        
        # Determine severity based on error type
        severity = "HIGH"
        if "AttributeError" in error_message and "show_alert" in error_message:
            severity = "CRITICAL"  # Missing core app methods are critical
        elif "PermissionError" in error_message:
            severity = "MEDIUM"  # File locking is important but not critical
        elif "SyntaxError" in error_message:
            severity = "CRITICAL"  # Syntax errors prevent code from running
        
        bug_generator.add_bug(test_name, error_type, error_message, traceback_str, severity)


def pytest_sessionfinish(session, exitstatus):
    """Pytest hook to generate bug reports at the end of the test session."""
    if bug_generator.bugs:
        print("\n" + "="*80)
        print("🐛 BUGS DETECTED - GENERATING BUG REPORTS")
        print("="*80)
        
        # Save reports
        md_path = bug_generator.save_markdown_report()
        json_path = bug_generator.save_json_report()
        bug_generator.save_individual_bug_reports()
        
        print(f"\n📄 Bug reports generated:")
        print(f"   - Main report: {md_path}")
        print(f"   - JSON report: {json_path}")
        print(f"   - Individual bugs: {bug_generator.output_dir}/bug_*.md")
        
        print(f"\n📊 Summary: {len(bug_generator.bugs)} bugs found")
        print(f"   - CRITICAL: {len([b for b in bug_generator.bugs if b.severity == 'CRITICAL'])}")
        print(f"   - HIGH: {len([b for b in bug_generator.bugs if b.severity == 'HIGH'])}")
        print(f"   - MEDIUM: {len([b for b in bug_generator.bugs if b.severity == 'MEDIUM'])}")
        print(f"   - LOW: {len([b for b in bug_generator.bugs if b.severity == 'LOW'])}")
        
        print("\n💡 Review the bug reports to fix the dashboard system issues.")
        print("="*80 + "\n")
    else:
        print("\n✅ No bugs detected - all tests passed!")