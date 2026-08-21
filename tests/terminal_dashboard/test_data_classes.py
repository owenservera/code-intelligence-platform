"""
Unit tests for terminal dashboard data classes.

Tests the core data structures: StatusCard, QuickAction, Suggestion
"""
import pytest
import sys
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from cipkg.terminal_dashboard import StatusCard, QuickAction, Suggestion, DashboardState


class TestStatusCard:
    """Test StatusCard dataclass."""
    
    def test_status_card_creation_with_all_fields(self):
        """Test creating StatusCard with all required fields."""
        card = StatusCard(
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
        
        assert card.health_score == 85
        assert card.health_status == "Good"
        assert card.index_fresh is True
        assert card.index_status == "Fresh"
        assert card.git_branch == "main"
        assert card.git_uncommitted == 0
        assert card.file_count == 150
        assert card.symbol_count == 2500
        assert card.edge_count == 5000
        assert card.last_sync == "2m ago"
    
    def test_status_card_with_critical_health(self):
        """Test StatusCard with critical health score."""
        card = StatusCard(
            health_score=45,
            health_status="Critical",
            index_fresh=False,
            index_status="Stale",
            git_branch="feature/test",
            git_uncommitted=5,
            file_count=200,
            symbol_count=3000,
            edge_count=6000,
            last_sync="1d ago"
        )
        
        assert card.health_score == 45
        assert card.health_status == "Critical"
        assert card.index_fresh is False
        assert card.git_uncommitted == 5
    
    def test_status_card_edge_cases(self):
        """Test StatusCard with edge case values."""
        # Zero values
        card = StatusCard(
            health_score=0,
            health_status="Unknown",
            index_fresh=False,
            index_status="Never",
            git_branch="unknown",
            git_uncommitted=0,
            file_count=0,
            symbol_count=0,
            edge_count=0,
            last_sync="Never"
        )
        
        assert card.health_score == 0
        assert card.file_count == 0
        assert card.symbol_count == 0
        
        # Maximum values
        card = StatusCard(
            health_score=100,
            health_status="Excellent",
            index_fresh=True,
            index_status="Fresh",
            git_branch="main",
            git_uncommitted=999,
            file_count=999999,
            symbol_count=9999999,
            edge_count=99999999,
            last_sync="0s ago"
        )
        
        assert card.health_score == 100
        assert card.git_uncommitted == 999


class TestQuickAction:
    """Test QuickAction dataclass."""
    
    def test_quick_action_creation_with_all_fields(self):
        """Test creating QuickAction with all fields."""
        action = QuickAction(
            icon="🔄",
            label="Sync Index",
            command="sync",
            description="Update index with latest changes",
            priority=1
        )
        
        assert action.icon == "🔄"
        assert action.label == "Sync Index"
        assert action.command == "sync"
        assert action.description == "Update index with latest changes"
        assert action.priority == 1
    
    def test_quick_action_with_default_priority(self):
        """Test QuickAction with default priority."""
        action = QuickAction(
            icon="🔍",
            label="Search",
            command="search",
            description="Search codebase"
        )
        
        assert action.priority == 0  # Default value
    
    def test_quick_action_different_priorities(self):
        """Test QuickAction with different priority levels."""
        high_priority = QuickAction(
            icon="✅",
            label="Verify",
            command="verify",
            description="Run quality checks",
            priority=10
        )
        
        low_priority = QuickAction(
            icon="📊",
            label="Stats",
            command="stats",
            description="Show statistics",
            priority=1
        )
        
        assert high_priority.priority > low_priority.priority


class TestSuggestion:
    """Test Suggestion dataclass."""
    
    def test_suggestion_creation_with_all_fields(self):
        """Test creating Suggestion with all fields."""
        suggestion = Suggestion(
            icon="💡",
            action="cip sync",
            reason="Index is stale, sync recommended",
            confidence=0.9,
            priority="high"
        )
        
        assert suggestion.icon == "💡"
        assert suggestion.action == "cip sync"
        assert suggestion.reason == "Index is stale, sync recommended"
        assert suggestion.confidence == 0.9
        assert suggestion.priority == "high"
    
    def test_suggestion_confidence_levels(self):
        """Test Suggestion with different confidence levels."""
        high_confidence = Suggestion(
            icon="🔥",
            action="cip verify",
            reason="Critical issues found",
            confidence=0.95,
            priority="critical"
        )
        
        low_confidence = Suggestion(
            icon="💭",
            action="cip analyze",
            reason="Consider analysis",
            confidence=0.3,
            priority="low"
        )
        
        assert high_confidence.confidence > low_confidence.confidence
        assert high_confidence.priority == "critical"
        assert low_confidence.priority == "low"
    
    def test_suggestion_edge_cases(self):
        """Test Suggestion with edge case values."""
        # Minimum confidence
        suggestion = Suggestion(
            icon="❓",
            action="cip status",
            reason="Optional check",
            confidence=0.0,
            priority="low"
        )
        
        assert suggestion.confidence == 0.0
        
        # Maximum confidence
        suggestion = Suggestion(
            icon="✅",
            action="cip init",
            reason="Highly recommended",
            confidence=1.0,
            priority="critical"
        )
        
        assert suggestion.confidence == 1.0


class TestDashboardState:
    """Test DashboardState enum."""
    
    def test_dashboard_state_values(self):
        """Test all DashboardState enum values."""
        assert DashboardState.INITIALIZATION_NEEDED.value == "initialization_needed"
        assert DashboardState.INDEX_NEEDED.value == "index_needed"
        assert DashboardState.ACTIVE.value == "active"
        assert DashboardState.ERROR.value == "error"
    
    def test_dashboard_state_comparison(self):
        """Test DashboardState comparison."""
        state1 = DashboardState.ACTIVE
        state2 = DashboardState.ACTIVE
        state3 = DashboardState.ERROR
        
        assert state1 == state2
        assert state1 != state3
    
    def test_dashboard_state_iteration(self):
        """Test iterating over DashboardState values."""
        states = list(DashboardState)
        
        assert len(states) == 4
        assert DashboardState.INITIALIZATION_NEEDED in states
        assert DashboardState.INDEX_NEEDED in states
        assert DashboardState.ACTIVE in states
        assert DashboardState.ERROR in states