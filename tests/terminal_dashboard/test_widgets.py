"""
Unit tests for terminal dashboard widgets.

Tests the UI widgets: StatusCardWidget, QuickActionsWidget
"""
import pytest
from textual.app import App
from textual.widgets import Static
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from cipkg.terminal_dashboard import (
    StatusCard,
    QuickAction,
    StatusCardWidget,
    QuickActionsWidget
)


class TestStatusCardWidget:
    """Test StatusCardWidget widget."""
    
    @pytest.fixture
    def sample_status_card(self):
        """Create sample status card for testing."""
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
    
    @pytest.mark.asyncio
    async def test_status_card_widget_compose(self, sample_status_card):
        """Test StatusCardWidget composition."""
        widget = StatusCardWidget(sample_status_card)
        
        # Create a minimal app to host the widget
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            # Widget should be composed
            assert widget is not None
            
            # Check that widget has children (Static widgets)
            children = list(widget.children)
            assert len(children) == 3  # Three Static widgets for health, stats, git
    
    @pytest.mark.asyncio
    async def test_status_card_widget_high_health(self):
        """Test StatusCardWidget with high health score displays green emoji."""
        status_card = StatusCard(
            health_score=90,
            health_status="Excellent",
            index_fresh=True,
            index_status="Fresh",
            git_branch="main",
            git_uncommitted=0,
            file_count=100,
            symbol_count=1000,
            edge_count=2000,
            last_sync="1m ago"
        )
        
        widget = StatusCardWidget(status_card)
        
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            # Get the first child (health line)
            health_line = list(widget.children)[0]
            content = health_line.render()
            # Should contain green emoji for high health
            assert "🟢" in str(content)
    
    @pytest.mark.asyncio
    async def test_status_card_widget_medium_health(self):
        """Test StatusCardWidget with medium health score displays yellow emoji."""
        status_card = StatusCard(
            health_score=65,
            health_status="Fair",
            index_fresh=True,
            index_status="Fresh",
            git_branch="main",
            git_uncommitted=0,
            file_count=100,
            symbol_count=1000,
            edge_count=2000,
            last_sync="1m ago"
        )
        
        widget = StatusCardWidget(status_card)
        
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            health_line = list(widget.children)[0]
            content = health_line.render()
            # Should contain yellow emoji for medium health
            assert "🟡" in str(content)
    
    @pytest.mark.asyncio
    async def test_status_card_widget_low_health(self):
        """Test StatusCardWidget with low health score displays red emoji."""
        status_card = StatusCard(
            health_score=45,
            health_status="Poor",
            index_fresh=True,
            index_status="Fresh",
            git_branch="main",
            git_uncommitted=0,
            file_count=100,
            symbol_count=1000,
            edge_count=2000,
            last_sync="1m ago"
        )
        
        widget = StatusCardWidget(status_card)
        
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            health_line = list(widget.children)[0]
            content = health_line.render()
            # Should contain red emoji for low health
            assert "🔴" in str(content)
    
    @pytest.mark.asyncio
    async def test_status_card_widget_fresh_index(self):
        """Test StatusCardWidget with fresh index displays checkmark."""
        status_card = StatusCard(
            health_score=85,
            health_status="Good",
            index_fresh=True,
            index_status="Fresh",
            git_branch="main",
            git_uncommitted=0,
            file_count=100,
            symbol_count=1000,
            edge_count=2000,
            last_sync="1m ago"
        )
        
        widget = StatusCardWidget(status_card)
        
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            health_line = list(widget.children)[0]
            content = health_line.render()
            # Should contain checkmark for fresh index
            assert "✅" in str(content)
    
    @pytest.mark.asyncio
    async def test_status_card_widget_stale_index(self):
        """Test StatusCardWidget with stale index displays warning."""
        status_card = StatusCard(
            health_score=85,
            health_status="Good",
            index_fresh=False,
            index_status="Stale",
            git_branch="main",
            git_uncommitted=0,
            file_count=100,
            symbol_count=1000,
            edge_count=2000,
            last_sync="1h ago"
        )
        
        widget = StatusCardWidget(status_card)
        
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            health_line = list(widget.children)[0]
            content = health_line.render()
            # Should contain warning for stale index
            assert "⚠️" in str(content)
    
    @pytest.mark.asyncio
    async def test_status_card_widget_clean_git(self):
        """Test StatusCardWidget with clean git state."""
        status_card = StatusCard(
            health_score=85,
            health_status="Good",
            index_fresh=True,
            index_status="Fresh",
            git_branch="main",
            git_uncommitted=0,
            file_count=100,
            symbol_count=1000,
            edge_count=2000,
            last_sync="1m ago"
        )
        
        widget = StatusCardWidget(status_card)
        
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            health_line = list(widget.children)[0]
            content = health_line.render()
            # Should show package emoji without count for clean git
            assert "📦" in str(content)
    
    @pytest.mark.asyncio
    async def test_status_card_widget_dirty_git(self):
        """Test StatusCardWidget with uncommitted changes."""
        status_card = StatusCard(
            health_score=85,
            health_status="Good",
            index_fresh=True,
            index_status="Fresh",
            git_branch="main",
            git_uncommitted=5,
            file_count=100,
            symbol_count=1000,
            edge_count=2000,
            last_sync="1m ago"
        )
        
        widget = StatusCardWidget(status_card)
        
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            health_line = list(widget.children)[0]
            content = health_line.render()
            # Should show package emoji with count for dirty git
            assert "📦 5" in str(content)


class TestQuickActionsWidget:
    """Test QuickActionsWidget widget."""
    
    @pytest.fixture
    def sample_quick_actions(self):
        """Create sample quick actions for testing."""
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
    
    @pytest.mark.asyncio
    async def test_quick_actions_widget_compose(self, sample_quick_actions):
        """Test QuickActionsWidget composition."""
        widget = QuickActionsWidget(sample_quick_actions)
        
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            # Widget should be composed
            assert widget is not None
            
            # Check that widget has children (Buttons)
            children = list(widget.children)
            assert len(children) == 3  # Three buttons for three actions
    
    @pytest.mark.asyncio
    async def test_quick_actions_widget_button_ids(self, sample_quick_actions):
        """Test QuickActionsWidget buttons have correct IDs."""
        widget = QuickActionsWidget(sample_quick_actions)
        
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            children = list(widget.children)
            
            # Check button IDs correspond to commands
            assert children[0].id == "action_sync"
            assert children[1].id == "action_search"
            assert children[2].id == "action_verify"
    
    @pytest.mark.asyncio
    async def test_quick_actions_widget_button_labels(self, sample_quick_actions):
        """Test QuickActionsWidget buttons have correct labels."""
        widget = QuickActionsWidget(sample_quick_actions)
        
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            children = list(widget.children)
            
            # Check button labels contain icon and label
            assert "🔄" in str(children[0].label)
            assert "Sync Index" in str(children[0].label)
            assert "🔍" in str(children[1].label)
            assert "Search" in str(children[1].label)
    
    @pytest.mark.asyncio
    async def test_quick_actions_widget_empty_list(self):
        """Test QuickActionsWidget with empty actions list."""
        widget = QuickActionsWidget([])
        
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            # Widget should compose but have no children
            children = list(widget.children)
            assert len(children) == 0
    
    @pytest.mark.asyncio
    async def test_quick_actions_widget_single_action(self):
        """Test QuickActionsWidget with single action."""
        single_action = [
            QuickAction(
                icon="🔄",
                label="Sync",
                command="sync",
                description="Sync index",
                priority=1
            )
        ]
        
        widget = QuickActionsWidget(single_action)
        
        class TestApp(App):
            def compose(self):
                yield widget
        
        app = TestApp()
        async with app.run_test() as pilot:
            children = list(widget.children)
            assert len(children) == 1
            assert children[0].id == "action_sync"