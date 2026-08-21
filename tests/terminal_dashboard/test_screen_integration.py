"""
Integration tests for terminal dashboard screen composition.

Tests screen navigation, composition, and interaction using Textual's Pilot API.
"""
import pytest
from textual.app import App
from textual.widgets import Button, Static
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from cipkg.terminal_dashboard import (
    MainNavigationScreen,
    CommandCategoryScreen,
    InitializationScreen,
    IndexNeededScreen,
    StatusCard,
    DashboardState
)
from cipkg.command_registry import CommandCard, CommandCategory, CommandPriority


class TestMainNavigationScreen:
    """Test MainNavigationScreen integration."""
    
    @pytest.mark.asyncio
    async def test_main_navigation_screen_basic_compose(self, temp_repo_dir):
        """Test MainNavigationScreen basic composition without dependencies."""
        # Create screen but expect it might fail due to missing dependencies
        # This test will help identify what's actually broken
        try:
            screen = MainNavigationScreen(str(temp_repo_dir))
            
            class TestApp(App):
                def compose(self):
                    yield screen
            
            app = TestApp()
            async with app.run_test() as pilot:
                # If we get here, screen composition worked
                assert screen is not None
        except Exception as e:
            # If screen composition fails, that's a real bug to document
            pytest.fail(f"MainNavigationScreen composition failed with real bug: {e}")
    
    @pytest.mark.asyncio
    async def test_main_navigation_screen_category_buttons_exist(self, temp_repo_dir):
        """Test that MainNavigationScreen has category buttons when it works."""
        try:
            screen = MainNavigationScreen(str(temp_repo_dir))
            
            class TestApp(App):
                def compose(self):
                    yield screen
            
            app = TestApp()
            async with app.run_test() as pilot:
                # Look for category buttons
                category_buttons = [
                    child for child in screen.walk_children()
                    if isinstance(child, Button) and child.id and child.id.startswith("category_")
                ]
                
                # This should reveal if buttons are actually being created
                assert len(category_buttons) > 0, "No category buttons found - this is a real bug"
        except Exception as e:
            # Document the real bug
            pytest.fail(f"Category button test revealed real bug: {e}")


class TestCommandCategoryScreen:
    """Test CommandCategoryScreen integration."""
    
    @pytest.mark.asyncio
    async def test_command_category_screen_basic_compose(self, temp_repo_dir):
        """Test CommandCategoryScreen basic composition."""
        try:
            # Create simple mock command cards
            command_cards = [
                CommandCard(
                    command="test",
                    icon="🧪",
                    label="Test",
                    description="Test command",
                    category=CommandCategory.REPOSITORY,
                    priority=CommandPriority.MEDIUM,
                    handler=Mock(return_value={"status": "success"}),
                    has_form=False
                )
            ]
            
            screen = CommandCategoryScreen(
                str(temp_repo_dir),
                "Test Category",
                command_cards
            )
            
            class TestApp(App):
                def compose(self):
                    yield screen
            
            app = TestApp()
            async with app.run_test() as pilot:
                # Screen should be composed
                assert screen is not None
        except Exception as e:
            # Document real bug
            pytest.fail(f"CommandCategoryScreen composition failed with real bug: {e}")
    
    @pytest.mark.asyncio
    async def test_command_category_screen_has_back_button(self, temp_repo_dir):
        """Test CommandCategoryScreen has back button."""
        try:
            command_cards = [
                CommandCard(
                    command="test",
                    icon="🧪",
                    label="Test",
                    description="Test command",
                    category=CommandCategory.REPOSITORY,
                    priority=CommandPriority.MEDIUM,
                    handler=Mock(return_value={"status": "success"}),
                    has_form=False
                )
            ]
            
            screen = CommandCategoryScreen(
                str(temp_repo_dir),
                "Test Category",
                command_cards
            )
            
            class TestApp(App):
                def compose(self):
                    yield screen
            
            app = TestApp()
            async with app.run_test() as pilot:
                # Should have back button
                try:
                    back_button = screen.query_one("#back_button", Button)
                    assert back_button is not None
                except Exception as e:
                    pytest.fail(f"Back button not found - real bug: {e}")
        except Exception as e:
            pytest.fail(f"Back button test failed with real bug: {e}")


class TestInitializationScreen:
    """Test InitializationScreen integration."""
    
    @pytest.mark.asyncio
    async def test_initialization_screen_compose(self, temp_repo_dir):
        """Test InitializationScreen composition."""
        init_state = DashboardState.INITIALIZATION_NEEDED
        screen = InitializationScreen(str(temp_repo_dir), init_state)
        
        class TestApp(App):
            def compose(self):
                yield screen
        
        app = TestApp()
        async with app.run_test() as pilot:
            # Screen should be composed
            assert screen is not None
            
            # Should have initialization buttons
            buttons = list(screen.query(Button))
            assert len(buttons) > 0
    
    @pytest.mark.asyncio
    async def test_initialization_screen_buttons_exist(self, temp_repo_dir):
        """Test InitializationScreen has expected buttons."""
        init_state = DashboardState.INITIALIZATION_NEEDED
        screen = InitializationScreen(str(temp_repo_dir), init_state)
        
        class TestApp(App):
            def compose(self):
                yield screen
        
        app = TestApp()
        async with app.run_test() as pilot:
            # Check for specific buttons
            init_button = screen.query_one("#init_1", Button)
            assert init_button is not None
            
            custom_button = screen.query_one("#init_2", Button)
            assert custom_button is not None
            
            help_button = screen.query_one("#init_3", Button)
            assert help_button is not None
            
            exit_button = screen.query_one("#init_4", Button)
            assert exit_button is not None


class TestIndexNeededScreen:
    """Test IndexNeededScreen integration."""
    
    @pytest.mark.asyncio
    async def test_index_needed_screen_compose(self, temp_repo_dir):
        """Test IndexNeededScreen composition."""
        init_state = DashboardState.INDEX_NEEDED
        screen = IndexNeededScreen(str(temp_repo_dir), init_state)
        
        class TestApp(App):
            def compose(self):
                yield screen
        
        app = TestApp()
        async with app.run_test() as pilot:
            # Screen should be composed
            assert screen is not None


class TestScreenNavigation:
    """Test screen navigation and transitions."""
    
    @pytest.mark.asyncio
    async def test_basic_screen_navigation(self, temp_repo_dir):
        """Test basic screen push and pop functionality."""
        try:
            class TestApp(App):
                def __init__(self):
                    super().__init__()
                    self.initial_screen = InitializationScreen(str(temp_repo_dir), DashboardState.INITIALIZATION_NEEDED)
                
                def compose(self):
                    yield self.initial_screen
            
            app = TestApp()
            async with app.run_test() as pilot:
                # Start with one screen
                initial_stack_length = len(app.screen_stack)
                
                # Try to push another screen
                try:
                    app.push_screen(InitializationScreen(str(temp_repo_dir), DashboardState.INDEX_NEEDED))
                    new_stack_length = len(app.screen_stack)
                    
                    # Should have increased stack size
                    assert new_stack_length > initial_stack_length, "Screen push didn't work - real bug"
                    
                    # Try to pop
                    app.pop_screen()
                    final_stack_length = len(app.screen_stack)
                    
                    # Should be back to original
                    assert final_stack_length == initial_stack_length, "Screen pop didn't work - real bug"
                except Exception as e:
                    pytest.fail(f"Screen navigation failed with real bug: {e}")
        except Exception as e:
            pytest.fail(f"Basic navigation test failed with real bug: {e}")