"""
Interactive UI Components for CIP CLI v2.0

This module provides terminal-based UI components for the interactive mode,
including menus, progress bars, tables, and screen layouts.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import os
import time


class ColorPalette:
    """Color palette for terminal UI."""
    
    PRIMARY = "\033[94m"      # Blue
    PRIMARY_DARK = "\033[34m"  # Darker blue
    SUCCESS = "\033[92m"       # Green
    WARNING = "\033[93m"       # Amber
    ERROR = "\033[91m"         # Red
    INFO = "\033[96m"          # Cyan
    RESET = "\033[0m"          # Reset
    BOLD = "\033[1m"           # Bold


class Icons:
    """Unicode icons for terminal UI."""
    
    # Status icons
    SUCCESS = "✓"
    ERROR = "✗"
    WARNING = "⚠"
    INFO = "ℹ"
    QUESTION = "?"
    
    # Action icons
    ARROW_RIGHT = "→"
    ARROW_LEFT = "←"
    CHECK = "☑"
    CROSS = "☒"
    
    # Progress icons
    LOADING = "⏳"
    RUNNING = "🔄"
    COMPLETED = "✅"
    FAILED = "❌"
    SKIPPED = "⏭️"
    
    # Priority icons
    CRITICAL = "🔴"
    HIGH = "🟠"
    MEDIUM = "🟡"
    LOW = "🟢"
    
    # Category icons
    HEALTH = "🏥"
    GIT = "📦"
    STACK = "🔧"
    WORKFLOW = "⚙️"
    SEARCH = "🔍"
    SETTINGS = "⚙️"


class ProgressBar:
    """Progress bar component."""
    
    @staticmethod
    def render(current: int, total: int, width: int = 40, 
               show_percentage: bool = True) -> str:
        """Render progress bar."""
        if total == 0:
            percentage = 0
        else:
            percentage = min(100, (current / total) * 100)
        
        filled = int((width * percentage) / 100)
        empty = width - filled
        
        bar = "█" * filled + "░" * empty
        
        if show_percentage:
            return f"[{bar}] {percentage:.1f}%"
        else:
            return f"[{bar}]"
    
    @staticmethod
    def render_indeterminate(width: int = 40) -> str:
        """Render indeterminate progress bar."""
        offset = int(time.time() * 2) % width
        
        bar = "░" * width
        bar_list = list(bar)
        
        for i in range(3):
            pos = (offset + i) % width
            bar_list[pos] = "█"
        
        return f"[{''.join(bar_list)}]"


class StatusIndicator:
    """Status indicator component."""
    
    @staticmethod
    def render(status: str, label: str = "") -> str:
        """Render status indicator."""
        icons = {
            'success': Icons.SUCCESS,
            'error': Icons.ERROR,
            'warning': Icons.WARNING,
            'info': Icons.INFO,
            'loading': Icons.LOADING,
            'running': Icons.RUNNING,
            'pending': Icons.LOADING
        }
        
        icon = icons.get(status.lower(), Icons.INFO)
        
        if label:
            return f"{icon} {label}"
        else:
            return icon


class Menu:
    """Interactive menu component."""
    
    def __init__(self, title: str, options: List[Dict[str, Any]], 
                 multi_select: bool = False):
        self.title = title
        self.options = options
        self.multi_select = multi_select
        self.selected_indices = []
        self.current_index = 0
    
    def render(self, width: int = 80) -> str:
        """Render menu."""
        lines = []
        
        # Title
        lines.append(f"║  {self.title}")
        lines.append("║")
        
        # Options
        for i, option in enumerate(self.options):
            icon = option.get('icon', '•')
            label = option.get('label', '')
            description = option.get('description', '')
            
            # Highlight current selection
            if i == self.current_index:
                lines.append(f"║▶ {icon} {label}")
                if description:
                    lines.append(f"║   {description}")
            else:
                lines.append(f"║  {icon} {label}")
        
        # Instructions
        lines.append("║")
        if self.multi_select:
            lines.append("║  Use ↑↓ to navigate, SPACE to select, ENTER to confirm")
        else:
            lines.append("║  Use ↑↓ to navigate, ENTER to select")
        
        return '\n'.join(lines)
    
    def handle_input(self, key: str) -> Optional[Any]:
        """Handle keyboard input."""
        if key == 'UP':
            self.current_index = max(0, self.current_index - 1)
        elif key == 'DOWN':
            self.current_index = min(len(self.options) - 1, self.current_index + 1)
        elif key == 'ENTER':
            if self.multi_select:
                return [self.options[i] for i in self.selected_indices]
            else:
                return self.options[self.current_index]
        elif key == 'SPACE' and self.multi_select:
            if self.current_index in self.selected_indices:
                self.selected_indices.remove(self.current_index)
            else:
                self.selected_indices.append(self.current_index)
        
        return None


class Table:
    """Table component."""
    
    def __init__(self, headers: List[str], rows: List[List[str]], 
                 align: List[str] = None):
        self.headers = headers
        self.rows = rows
        self.align = align or ['left'] * len(headers)
    
    def render(self, width: int = 80) -> str:
        """Render table."""
        if not self.headers:
            return ""
        
        # Calculate column widths
        col_widths = self._calculate_column_widths(width)
        
        lines = []
        
        # Header row
        header_parts = []
        for i, header in enumerate(self.headers):
            aligned = self._align_text(header, col_widths[i], self.align[i])
            header_parts.append(aligned)
        
        lines.append("║  " + "  ".join(header_parts))
        lines.append("║  " + "  ".join(["─" * w for w in col_widths]))
        
        # Data rows
        for row in self.rows:
            row_parts = []
            for i, cell in enumerate(row):
                aligned = self._align_text(str(cell), col_widths[i], self.align[i])
                row_parts.append(aligned)
            lines.append("║  " + "  ".join(row_parts))
        
        return '\n'.join(lines)
    
    def _calculate_column_widths(self, total_width: int) -> List[int]:
        """Calculate column widths based on content."""
        available_width = total_width - 4
        num_cols = len(self.headers)
        
        if num_cols == 0:
            return []
        
        base_width = available_width // num_cols
        return [base_width] * num_cols
    
    def _align_text(self, text: str, width: int, align: str) -> str:
        """Align text within width."""
        if len(text) > width:
            return text[:width - 1] + "…"
        
        if align == 'center':
            return text.center(width)
        elif align == 'right':
            return text.rjust(width)
        else:  # left
            return text.ljust(width)


class AlertBox:
    """Alert box component."""
    
    @staticmethod
    def render(message: str, alert_type: str = "info", width: int = 80) -> str:
        """Render alert box."""
        icons = {
            'info': Icons.INFO,
            'success': Icons.SUCCESS,
            'warning': Icons.WARNING,
            'error': Icons.ERROR
        }
        
        icon = icons.get(alert_type.lower(), Icons.INFO)
        
        # Wrap message
        wrapped_lines = AlertBox._wrap_text(message, width - 6)
        
        lines = [f"║  {icon} {wrapped_lines[0]}"]
        
        for line in wrapped_lines[1:]:
            lines.append(f"║    {line}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def _wrap_text(text: str, width: int) -> List[str]:
        """Wrap text to fit width."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(' '.join(current_line + [word])) <= width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines


class WelcomeScreen:
    """Welcome screen for interactive mode."""
    
    @staticmethod
    def render(context, width: int = 80) -> str:
        """Render welcome screen."""
        lines = []
        
        # Header
        lines.append("╔═══════════════════════════════════════════════════════════════╗")
        lines.append(f"║  CIP v2.0 - {context.repository.repo_name:20}                      ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Context summary
        health = context.repository.health_score.get('score', 'N/A') if context.repository.health_score else 'N/A'
        index_status = 'Fresh' if not context.repository.index_status.get('stale') else 'Stale'
        git_status = f"{context.repository.git_state.get('uncommitted_files', 0)} changed" if context.repository.git_state else "Unknown"
        
        lines.append(f"║  Type: {context.repository.repo_type:12} Health: {str(health):3}/100  Index: {index_status:6} ║")
        lines.append(f"║  Git: {git_status:20} Files: {context.repository.file_count:6}              ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Quick actions
        lines.append("║  🔥 Quick Actions                                              ║")
        lines.append("║  1) 📊 Repository health check                                  ║")
        lines.append("║  2) 🔍 Search codebase                                         ║")
        lines.append("║  3) ⚙️  Run workflow                                           ║")
        lines.append("║  4) 🔧 Settings & configuration                               ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Suggestions
        lines.append("║  💡 Suggested based on current state:                          ║")
        lines.append("║  • cip audit --diff   Review uncommitted changes                ║")
        lines.append("║  • cip workflow pre-commit   Comprehensive pre-commit checks    ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Footer
        lines.append("║  Press ENTER to continue or type a command: _                   ║")
        lines.append("╚═══════════════════════════════════════════════════════════════╝")
        
        return '\n'.join(lines)


class WorkflowScreen:
    """Workflow execution screen."""
    
    def __init__(self, workflow, execution):
        self.workflow = workflow
        self.execution = execution
    
    def render(self, width: int = 80) -> str:
        """Render workflow execution screen."""
        lines = []
        
        # Header
        lines.append("╔═══════════════════════════════════════════════════════════════╗")
        lines.append(f"║  {self.workflow.name:50}                      ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Progress bar
        completed_steps = sum(1 for s in self.execution.steps.values() 
                            if s.status.value in ['completed', 'skipped'])
        total_steps = len(self.workflow.steps)
        progress = ProgressBar.render(completed_steps, total_steps, width - 10)
        
        lines.append(f"║  Progress: {progress:60} ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Steps
        for step in self.workflow.steps:
            step_exec = self.execution.steps[step.id]
            status_icon = self._get_status_icon(step_exec.status)
            
            lines.append(f"║  {status_icon} {step.name}")
            
            if step_exec.status.value == 'running':
                lines.append(f"║     {step.description}...")
            elif step_exec.status.value == 'completed':
                lines.append(f"║     ✓ {step.description}")
            elif step_exec.status.value == 'failed':
                lines.append(f"║     ✗ {step.description}")
                if step_exec.error:
                    lines.append(f"║     Error: {step_exec.error}")
            elif step_exec.status.value == 'skipped':
                lines.append(f"║     ⏭️  {step.description} (skipped)")
        
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Controls
        if self.execution.status.value == 'in_progress':
            lines.append("║  [P]ause  [C]ancel  [R]etry failed step                    ║")
        elif self.execution.status.value == 'paused':
            lines.append("║  [R]esume  [C]ancel                                         ║")
        elif self.execution.status.value == 'failed':
            lines.append("║  [R]etry  [C]ancel  [V]iew details                         ║")
        else:
            lines.append("║  [R]un again  [E]xit                                        ║")
        
        lines.append("╚═══════════════════════════════════════════════════════════════╝")
        
        return '\n'.join(lines)
    
    def _get_status_icon(self, status) -> str:
        """Get icon for step status."""
        icons = {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌',
            'skipped': '⏭️',
            'cancelled': '🚫'
        }
        return icons.get(status.value, '⏳')


class SearchResultsScreen:
    """Search results screen."""
    
    def __init__(self, query: str, results: List[Dict[str, Any]], context: Dict[str, Any]):
        self.query = query
        self.results = results
        self.context = context
        self.selected_index = 0
    
    def render(self, width: int = 80) -> str:
        """Render search results."""
        lines = []
        
        # Header
        lines.append("╔═══════════════════════════════════════════════════════════════╗")
        lines.append(f"║  Search Results: \"{self.query}\"                              ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Context info
        if self.context.get('working_directory'):
            lines.append(f"║  📁 Context: {self.context['working_directory']:40} ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Results
        if not self.results:
            lines.append("║  No results found                                            ║")
        else:
            lines.append(f"║  Found {len(self.results)} results                                          ║")
            lines.append("╠═══════════════════════════════════════════════════════════════╣")
            
            for i, result in enumerate(self.results[:10]):
                icon = "📄" if result.get('type') == 'file' else "📁"
                relevance = result.get('relevance', 0)
                
                prefix = "▶ " if i == self.selected_index else "  "
                
                lines.append(f"║{prefix} {icon} {result['path']}")
                lines.append(f"║     Relevance: {relevance:.1%}  Modified: {result.get('modified', 'Unknown')}")
                
                if result.get('excerpt'):
                    excerpt = result['excerpt'][:60] + "..." if len(result['excerpt']) > 60 else result['excerpt']
                    lines.append(f"║     {excerpt}")
                
                lines.append("║")
        
        # Actions
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        lines.append("║  [ENTER] Open  [G] Graph  [I] Impact  [C] Context  [Q] Quit   ║")
        lines.append("╚═══════════════════════════════════════════════════════════════╝")
        
        return '\n'.join(lines)


class SettingsScreen:
    """Settings screen."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.current_section = "general"
        self.selected_option = 0
    
    def render(self, width: int = 80) -> str:
        """Render settings screen."""
        lines = []
        
        # Header
        lines.append("╔═══════════════════════════════════════════════════════════════╗")
        lines.append("║  Settings & Configuration                                     ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Sections
        sections = ["general", "interactive", "learning", "sync"]
        section_icons = ["⚙️", "🎯", "🧠", "🔄"]
        
        for i, (section, icon) in enumerate(zip(sections, section_icons)):
            prefix = "▶ " if i == sections.index(self.current_section) else "  "
            lines.append(f"║{prefix} {icon} {section.capitalize()}")
        
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Current section options
        lines.append(f"║  {self.current_section.capitalize()} Settings:")
        lines.append("║")
        
        options = self._get_section_options(self.current_section)
        for i, option in enumerate(options):
            prefix = "▶ " if i == self.selected_option else "  "
            value = self.config.get(option['key'], option.get('default', ''))
            lines.append(f"║{prefix} {option['label']}: {value}")
        
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        lines.append("║  [ENTER] Edit  [TAB] Switch section  [S]ave  [Q] Quit         ║")
        lines.append("╚═══════════════════════════════════════════════════════════════╝")
        
        return '\n'.join(lines)
    
    def _get_section_options(self, section: str) -> List[Dict[str, Any]]:
        """Get options for a section."""
        options = {
            'general': [
                {'key': 'theme', 'label': 'Theme', 'default': 'dark'},
                {'key': 'language', 'label': 'Language', 'default': 'en'},
                {'key': 'timezone', 'label': 'Timezone', 'default': 'UTC'}
            ],
            'interactive': [
                {'key': 'enabled', 'label': 'Interactive Mode', 'default': True},
                {'key': 'suggestions_enabled', 'label': 'Suggestions', 'default': True},
                {'key': 'max_suggestions', 'label': 'Max Suggestions', 'default': 5}
            ],
            'learning': [
                {'key': 'enabled', 'label': 'Learning System', 'default': True},
                {'key': 'pattern_tracking', 'label': 'Pattern Tracking', 'default': True},
                {'key': 'retention_days', 'label': 'Data Retention (days)', 'default': 30}
            ],
            'sync': [
                {'key': 'auto_sync', 'label': 'Auto Sync', 'default': False},
                {'key': 'sync_interval', 'label': 'Sync Interval (min)', 'default': 60},
                {'key': 'sync_on_git_hook', 'label': 'Sync on Git Hook', 'default': True}
            ]
        }
        
        return options.get(section, [])


class InputField:
    """Input field component."""
    
    def __init__(self, label: str, placeholder: str = "", 
                 default: str = "", password: bool = False):
        self.label = label
        self.placeholder = placeholder
        self.default = default
        self.password = password
        self.value = default
    
    def render(self, width: int = 60) -> str:
        """Render input field."""
        display_value = self.value if not self.password else "*" * len(self.value)
        
        if not display_value and self.placeholder:
            display_value = f"[{self.placeholder}]"
        
        return f"{self.label}: {display_value}"
    
    def handle_input(self, char: str) -> Optional[str]:
        """Handle character input."""
        if char == '\r':  # Enter
            return self.value
        elif char == '\x1b':  # Escape
            return None
        elif char == '\b':  # Backspace
            self.value = self.value[:-1]
        elif len(char) == 1:  # Regular character
            self.value += char
        
        return None


class ConfirmationDialog:
    """Confirmation dialog component."""
    
    def __init__(self, message: str, default: bool = True):
        self.message = message
        self.default = default
        self.confirmed = default
    
    def render(self, width: int = 60) -> str:
        """Render confirmation dialog."""
        lines = []
        
        lines.append("╔═══════════════════════════════════════════════════════════════╗")
        lines.append("║  Confirmation                                                ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Wrap message
        wrapped = self._wrap_text(self.message, width - 6)
        for line in wrapped:
            lines.append(f"║  {line}")
        
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        yes_selected = "▶ " if self.confirmed else "  "
        no_selected = "▶ " if not self.confirmed else "  "
        
        lines.append(f"║  {yes_selected}Yes")
        lines.append(f"║  {no_selected}No")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        lines.append("║  Use ← → to select, ENTER to confirm                        ║")
        lines.append("╚═══════════════════════════════════════════════════════════════╝")
        
        return '\n'.join(lines)
    
    def handle_input(self, key: str) -> Optional[bool]:
        """Handle input."""
        if key == 'LEFT':
            self.confirmed = True
        elif key == 'RIGHT':
            self.confirmed = False
        elif key == 'ENTER':
            return self.confirmed
        return None
    
    def _wrap_text(self, text: str, width: int) -> List[str]:
        """Wrap text to fit width."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(' '.join(current_line + [word])) <= width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines


class NavigationPatterns:
    """Standard navigation patterns."""
    
    @staticmethod
    def handle_arrow_keys(current_index: int, max_index: int, key: str) -> int:
        """Handle arrow key navigation."""
        if key == 'UP':
            return max(0, current_index - 1)
        elif key == 'DOWN':
            return min(max_index, current_index + 1)
        elif key == 'HOME':
            return 0
        elif key == 'END':
            return max_index
        elif key == 'PAGE_UP':
            return max(0, current_index - 5)
        elif key == 'PAGE_DOWN':
            return min(max_index, current_index + 5)
        return current_index
    
    @staticmethod
    def handle_tab_navigation(current_section: str, sections: List[str], 
                             key: str) -> str:
        """Handle tab navigation between sections."""
        if key == 'TAB':
            current_index = sections.index(current_section)
            next_index = (current_index + 1) % len(sections)
            return sections[next_index]
        elif key == 'SHIFT_TAB':
            current_index = sections.index(current_section)
            prev_index = (current_index - 1) % len(sections)
            return sections[prev_index]
        return current_section


class KeyboardNavigation:
    """Keyboard navigation support."""
    
    @staticmethod
    def get_shortcuts() -> Dict[str, str]:
        """Get keyboard shortcuts."""
        return {
            'quit': 'q',
            'help': '?',
            'back': 'ESC',
            'confirm': 'ENTER',
            'navigate_up': '↑',
            'navigate_down': '↓',
            'navigate_left': '←',
            'navigate_right': '→',
            'select': 'SPACE',
            'search': '/',
            'settings': 's',
            'refresh': 'r'
        }
    
    @staticmethod
    def render_shortcuts_help() -> str:
        """Render shortcuts help."""
        shortcuts = KeyboardNavigation.get_shortcuts()
        
        lines = [
            "╔═══════════════════════════════════════════════════════════════╗",
            "║  Keyboard Shortcuts                                          ║",
            "╠═══════════════════════════════════════════════════════════════╣"
        ]
        
        for action, key in shortcuts.items():
            lines.append(f"║  {action.replace('_', ' ').title():20} : {key:15} ║")
        
        lines.append("╚═══════════════════════════════════════════════════════════════╝")
        
        return '\n'.join(lines)


class HighContrastTheme:
    """High contrast theme for accessibility."""
    
    @staticmethod
    def apply() -> Dict[str, str]:
        """Apply high contrast colors."""
        return {
            'TEXT_PRIMARY': '#FFFFFF',
            'TEXT_SECONDARY': '#E0E0E0',
            'BACKGROUND': '#000000',
            'BACKGROUND_ALT': '#1A1A1A',
            'BORDER': '#FFFFFF',
            'PRIMARY': '#FFFF00',
            'SUCCESS': '#00FF00',
            'WARNING': '#FFFF00',
            'ERROR': '#FF0000'
        }
