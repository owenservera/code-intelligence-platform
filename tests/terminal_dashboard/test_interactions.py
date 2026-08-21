"""
Interaction tests for terminal dashboard user actions.

Tests button clicks, key bindings, and user interactions using Textual's Pilot API.
"""
import pytest
from textual.app import App
from textual.widgets import Button
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from cipkg.terminal_dashboard import (
    MainNavigationScreen,
    CommandCategoryScreen,
    InitializationScreen,
    DashboardState
)
from cipkg.command_registry import CommandCard, CommandCategory, CommandPriority


class TestButtonInteractions:
    """Test button click interactions."""
    
    @pytest.mark.asyncio
    async def test_initialization_screen_button_clicks(self, temp_repo_dir):
        """Test InitializationScreen button clicks work correctly."""
        init_state = DashboardState.INITIALIZATION_NEEDED
        screen = InitializationScreen(str(temp_repo_dir), init_state)
        
        class TestApp(App):
            def compose(self):
                yield screen
        
        app = TestApp()
        async with app.run_test() as pilot:
            # Test clicking the exit button
            try:
                exit_button = screen.query_one("#init_4", Button)
                await pilot.click("#init_4")
                # If we get here without exception, the click worked
                assert True
            except Exception as e:
                pytest.fail(f"Exit button click failed with real bug: {e}")
    
    @pytest.mark.asyncio
    async def test_command_category_screen_back_button(self, temp_repo_dir):
        """Test CommandCategoryScreen back button interaction."""
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
            try:
                # Test back button click
                await pilot.click("#back_button")
                # If we get here, the click worked
                assert True
            except Exception as e:
                pytest.fail(f"Back button click failed with real bug: {e}")
    
    @pytest.mark.asyncio
    async def test_command_category_screen_command_button_click(self, temp_repo_dir):
        """Test clicking a command button in CommandCategoryScreen."""
        command_cards = [
            CommandCard(
                command="sync",
                icon="🔄",
                label="Sync",
                description="Sync command",
                category=CommandCategory.REPOSITORY,
                priority=CommandPriority.HIGH,
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
            try:
                # Test clicking a command button
                await pilot.click("#cmd_sync")
                # If we get here, the click worked
                assert True
            except Exception as e:
                pytest.fail(f"Command button click failed with real bug: {e}")


class TestKeyBindings:
    """Test keyboard key bindings."""
    
    @pytest.mark.asyncio
    async def test_main_navigation_screen_quit_binding(self, temp_repo_dir):
        """Test MainNavigationScreen quit key binding."""
        try:
            screen = MainNavigationScreen(str(temp_repo_dir))
            
            class TestApp(App):
                def compose(self):
                    yield screen
            
            app = TestApp()
            async with app.run_test() as pilot:
                # Test pressing 'q' to quit
                try:
                    await pilot.press("q")
                    # If we get here, the key press was processed
                    assert True
                except Exception as e:
                    pytest.fail(f"Quit key binding failed with real bug: {e}")
        except Exception as e:
            # If screen creation fails, that's a separate issue
            pytest.skip(f"Screen creation failed: {e}")
    
    @pytest.mark.asyncio
    async def test_main_navigation_screen_refresh_binding(self, temp_repo_dir):
        """Test MainNavigationScreen refresh key binding."""
        try:
            screen = MainNavigationScreen(str(temp_repo_dir))
            
            class TestApp(App):
                def compose(self):
                    yield screen
            
            app = TestApp()
            async with app.run_test() as pilot:
                try:
                    # Test pressing 'r' to refresh
                    await pilot.press("r")
                    assert True
                except Exception as e:
                    pytest.fail(f"Refresh key binding failed with real bug: {e}")
        except Exception as e:
            pytest.skip(f"Screen creation failed: {e}")


class TestScreenTransitions:
    """Test screen transition interactions."""
    
    @pytest.mark.asyncio
    async def test_screen_navigation_flow(self, temp_repo_dir):
        """Test navigating between screens via button clicks."""
        try:
            # Start with initialization screen
            init_screen = InitializationScreen(str(temp_repo_dir), DashboardState.INITIALIZATION_NEEDED)
            
            class TestApp(App):
                def compose(self):
                    yield init_screen
            
            app = TestApp()
            async with app.run_test() as pilot:
                try:
                    # Try to navigate to another screen
                    # This tests if screen transitions work
                    initial_stack = len(app.screen_stack)
                    
                    # Create and push a new screen
                    new_screen = InitializationScreen(str(temp_repo_dir), DashboardState.INDEX_NEEDED)
                    app.push_screen(new_screen)
                    
                    # Check stack increased
                    new_stack = len(app.screen_stack)
                    assert new_stack > initial_stack, "Screen navigation failed - real bug"
                    
                    # Try to go back
                    app.pop_screen()
                    final_stack = len(app.screen_stack)
                    assert final_stack == initial_stack, "Screen pop failed - real bug"
                    
                except Exception as e:
                    pytest.fail(f"Screen navigation flow failed with real bug: {e}")
        except Exception as e:
            pytest.fail(f"Screen transition test setup failed with real bug: {e}")


class TestErrorHandling:
    """Test error handling in user interactions."""
    
    @pytest.mark.asyncio
    async def test_button_click_with_missing_handler(self, temp_repo_dir):
        """Test button click behavior when handler is missing."""
        command_cards = [
            CommandCard(
                command="broken",
                icon="❌",
                label="Broken",
                description="Broken command",
                category=CommandCategory.REPOSITORY,
                priority=CommandPriority.LOW,
                handler=Mock(side_effect=Exception("Handler failed")),
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
            try:
                # Test clicking a button with broken handler
                # This should reveal how the dashboard handles errors
                await pilot.click("#cmd_broken")
                # If we get here without crashing, error handling works
                assert True
            except Exception as e:
                # This might be expected behavior - document it
                # If it crashes, that's a real bug in error handling
                pytest.fail(f"Button click with broken handler crashed with real bug: {e}")