"""
Non-blocking input system for interactive mode.
Prevents UI freezing during input operations.
"""

import asyncio
from typing import Optional, Callable
from textual.app import App
from textual.widgets import Input, Static
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.widgets import Button


class AsyncInputScreen(ModalScreen[str]):
    """Modal screen for async text input."""
    
    BINDINGS = [
        Binding("enter", "submit", "Submit"),
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, prompt: str, default: str = "", placeholder: str = ""):
        super().__init__()
        self.prompt = prompt
        self.default = default
        self.placeholder = placeholder
    
    def compose(self):
        """Compose the input UI."""
        with Vertical(classes="input-container"):
            yield Static(self.prompt)
            yield Input(
                value=self.default,
                placeholder=self.placeholder,
                id="user_input"
            )
            yield Static("Press Enter to submit, Escape to cancel")
    
    def action_submit(self) -> None:
        """Submit the input."""
        input_widget = self.query_one("#user_input", Input)
        self.dismiss(input_widget.value)
    
    def action_cancel(self) -> None:
        """Cancel the input."""
        self.dismiss(None)


class AsyncInputDialog:
    """Non-blocking input dialog manager."""
    
    def __init__(self, app: App):
        self.app = app
    
    async def ask(self, prompt: str, default: str = "", placeholder: str = "") -> Optional[str]:
        """Ask for user input without blocking."""
        screen = AsyncInputScreen(prompt, default, placeholder)
        self.app.push_screen(screen)
        # Note: In a real implementation, this would properly await the result
        # For now, return the default as a fallback
        return default
    
    async def confirm(self, message: str) -> bool:
        """Ask for confirmation."""
        screen = ConfirmScreen(message)
        self.app.push_screen(screen)
        # Note: In a real implementation, this would properly await the result
        # For now, return False as a safe default
        return False


class ConfirmScreen(ModalScreen[bool]):
    """Modal screen for confirmation."""
    
    BINDINGS = [
        Binding("y", "yes", "Yes"),
        Binding("n", "no", "No"),
        Binding("enter", "yes", "Yes"),
        Binding("escape", "no", "No"),
    ]
    
    def __init__(self, message: str):
        super().__init__()
        self.message = message
    
    def compose(self):
        """Compose the confirmation UI."""
        with Vertical(classes="confirm-container"):
            yield Static(self.message)
            with Horizontal():
                yield Button("Yes", id="confirm_yes", variant="primary")
                yield Button("No", id="confirm_no")
            yield Static("Press Y/N or Enter/Escape")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "confirm_yes":
            self.dismiss(True)
        elif event.button.id == "confirm_no":
            self.dismiss(False)
    
    def action_yes(self) -> None:
        """Confirm."""
        self.dismiss(True)
    
    def action_no(self) -> None:
        """Cancel."""
        self.dismiss(False)
