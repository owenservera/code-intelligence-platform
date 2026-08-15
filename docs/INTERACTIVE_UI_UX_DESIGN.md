# Interactive Mode UI/UX Design

## Overview

This document defines the systematic approach for designing the user interface and user experience for CIP CLI v2.0's interactive mode. It establishes design principles, component systems, interaction patterns, and visual guidelines to ensure a consistent, intuitive, and delightful user experience.

## Design Principles

### Core Principles

1. **Clarity First**: Information hierarchy makes the most important actions obvious
2. **Progressive Disclosure**: Show complexity only when needed, hide by default
3. **Context Awareness**: UI adapts based on repository state and user patterns
4. **Efficiency**: Minimize keystrokes and cognitive load for common tasks
5. **Forgiveness**: Easy undo/redo and clear error recovery paths
6. **Accessibility**: High contrast, clear typography, keyboard navigation
7. **Performance**: Instant feedback, no perceived lag

### Anti-Patterns to Avoid

- **Information Overload**: Don't show all options at once
- **Hidden Complexity**: Don't bury important features in sub-menus
- **Inconsistent Terminology**: Use the same terms throughout
- **Unclear Actions**: Always make it clear what will happen
- **No Way Back**: Always provide escape routes

## Visual Design System

### Color Palette

```python
class ColorPalette:
    """CIP v2.0 color palette."""
    
    # Primary colors
    PRIMARY = "#3B82F6"      # Blue for primary actions
    PRIMARY_DARK = "#2563EB"  # Darker blue for hover states
    PRIMARY_LIGHT = "#93C5FD" # Light blue for backgrounds
    
    # Semantic colors
    SUCCESS = "#10B981"      # Green for success states
    WARNING = "#F59E0B"      # Amber for warnings
    ERROR = "#EF4444"        # Red for errors
    INFO = "#6366F1"         # Indigo for information
    
    # Neutral colors
    TEXT_PRIMARY = "#1F2937"     # Dark gray for primary text
    TEXT_SECONDARY = "#6B7280"   # Medium gray for secondary text
    TEXT_MUTED = "#9CA3AF"       # Light gray for muted text
    BACKGROUND = "#FFFFFF"       # White background
    BACKGROUND_ALT = "#F3F4F6"   # Light gray for alternate backgrounds
    BORDER = "#E5E7EB"           # Gray for borders
    
    # Status colors
    STATUS_CRITICAL = "#DC2626"  # Red for critical issues
    STATUS_HIGH = "#F97316"      # Orange for high priority
    STATUS_MEDIUM = "#EAB308"    # Yellow for medium priority
    STATUS_LOW = "#22C55E"       # Green for low priority
    
    # Accent colors
    ACCENT_PURPLE = "#8B5CF6"
    ACCENT_PINK = "#EC4899"
    ACCENT_CYAN = "#06B6D4"
```

### Typography System

```python
class Typography:
    """Typography scale and hierarchy."""
    
    # Font families
    FONT_FAMILY = "Consolas, Monaco, 'Courier New', monospace"
    FONT_FAMILY_HEADER = "Consolas, Monaco, 'Courier New', monospace"
    
    # Font sizes (in terminal cells)
    SIZE_XL = 2      # Extra large headers
    SIZE_L = 1.5      # Large headers
    SIZE_M = 1.25     # Medium text
    SIZE_BASE = 1     # Base text
    SIZE_S = 0.875    # Small text
    SIZE_XS = 0.75    # Extra small text
    
    # Font weights
    WEIGHT_BOLD = "bold"
    WEIGHT_SEMIBOLD = "semibold"
    WEIGHT_NORMAL = "normal"
    WEIGHT_LIGHT = "light"
    
    # Line heights
    LEADING_TIGHT = 1.25
    LEADING_NORMAL = 1.5
    LEADING_RELAXED = 1.75
```

### Spacing System

```python
class Spacing:
    """Consistent spacing scale."""
    
    # Base unit (terminal cells)
    UNIT = 1
    
    # Spacing scale
    XS = 0.5    # 0.5 units
    SM = 1      # 1 unit
    MD = 2      # 2 units
    LG = 3      # 3 units
    XL = 4      # 4 units
    XXL = 6     # 6 units
    
    # Component-specific spacing
    PADDING_SM = (1, 2)      # Vertical, horizontal
    PADDING_MD = (2, 3)
    PADDING_LG = (3, 4)
    
    MARGIN_SM = 1
    MARGIN_MD = 2
    MARGIN_LG = 3
```

### Icon System

```python
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
    ARROW_UP = "↑"
    ARROW_DOWN = "↓"
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
    
    # UI icons
    HOME = "🏠"
    BACK = "⬅️"
    FORWARD = "➡️"
    REFRESH = "🔄"
    MENU = "☰"
    CLOSE = "✕"
    MINIMIZE = "−"
    MAXIMIZE = "□"
```

## Component System

### Layout Components

#### Main Container

```python
class MainContainer:
    """Main container for interactive mode."""
    
    @staticmethod
    def render(width: int = 80) -> str:
        """Render main container frame."""
        border = "═" * (width - 2)
        
        return [
            f"╔{border}╗",
            f"║{' ' * (width - 2)}║",
            f"╚{border}╝"
        ]
    
    @staticmethod
    def render_content(content: str, width: int = 80) -> str:
        """Render content within container."""
        lines = content.split('\n')
        border = "═" * (width - 2)
        
        output = [f"╔{border}╗"]
        
        for line in lines:
            # Pad line to width
            padded_line = line.ljust(width - 2)
            output.append(f"║{padded_line}║")
        
        output.append(f"╚{border}╝")
        
        return '\n'.join(output)
```

#### Section Divider

```python
class SectionDivider:
    """Visual section divider."""
    
    @staticmethod
    def render(title: str = "", width: int = 80) -> str:
        """Render section divider with optional title."""
        border = "═" * (width - 2)
        
        if title:
            # Center title in divider
            title_space = len(title)
            left_border = "═" * ((width - title_space - 4) // 2)
            right_border = "═" * (width - title_space - 4 - len(left_border))
            return f"╠{left_border} {title} {right_border}╣"
        else:
            return f"╠{border}╣"
```

### Interactive Components

#### Menu Component

```python
class Menu:
    """Interactive menu component."""
    
    def __init__(self, title: str, options: List[Dict[str, Any]], 
                 multi_select: bool = False):
        self.title = title
        self.options = options  # List of {'id': str, 'label': str, 'icon': str, 'description': str}
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
```

#### Progress Bar

```python
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
        import time
        offset = int(time.time() * 2) % width
        
        bar = "░" * width
        bar_list = list(bar)
        
        # Create moving indicator
        for i in range(3):
            pos = (offset + i) % width
            bar_list[pos] = "█"
        
        return f"[{''.join(bar_list)}]"
```

#### Status Indicator

```python
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
```

#### Input Field

```python
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
    
    def handle_input(self, char: str) -> str:
        """Handle character input."""
        if char == '\b':  # Backspace
            self.value = self.value[:-1]
        elif char == '\r':  # Enter
            return self.value
        elif len(char) == 1:  # Regular character
            self.value += char
        
        return None
```

### Information Components

#### Info Card

```python
class InfoCard:
    """Information card component."""
    
    @staticmethod
    def render(title: str, content: List[str], icon: str = "", 
               width: int = 80) -> str:
        """Render info card."""
        lines = []
        
        # Header
        if icon:
            header = f"{icon} {title}"
        else:
            header = title
        
        lines.append(f"║  {header}")
        lines.append("║  " + "─" * (width - 4))
        
        # Content
        for line in content:
            lines.append(f"║  {line}")
        
        return '\n'.join(lines)
```

#### Table

```python
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
        # Simple equal-width distribution
        available_width = total_width - 4  # Account for borders and padding
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
```

#### Alert Box

```python
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
```

## Screen Designs

### Welcome Screen

```python
class WelcomeScreen:
    """Welcome screen for interactive mode."""
    
    @staticmethod
    def render(context: UnifiedContext, width: int = 80) -> str:
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
```

### Workflow Execution Screen

```python
class WorkflowScreen:
    """Workflow execution screen."""
    
    def __init__(self, workflow: WorkflowDefinition, execution: WorkflowExecution):
        self.workflow = workflow
        self.execution = execution
    
    def render(self, width: int = 80) -> str:
        """Render workflow execution screen."""
        lines = []
        
        #Header
        lines.append("╔═══════════════════════════════════════════════════════════════╗")
        lines.append(f"║  {self.workflow.name:50}                      ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Progress bar
        completed_steps = sum(1 for s in self.execution.steps.values() 
                            if s.status in [StepStatus.COMPLETED, StepStatus.SKIPPED])
        total_steps = len(self.workflow.steps)
        progress = ProgressBar.render(completed_steps, total_steps, width - 10)
        
        lines.append(f"║  Progress: {progress:60} ║")
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Steps
        for step in self.workflow.steps:
            step_exec = self.execution.steps[step.id]
            status_icon = self._get_status_icon(step_exec.status)
            
            lines.append(f"║  {status_icon} {step.name}")
            
            if step_exec.status == StepStatus.RUNNING:
                lines.append(f"║     {step.description}...")
            elif step_exec.status == StepStatus.COMPLETED:
                lines.append(f"║     ✓ {step.description}")
            elif step_exec.status == StepStatus.FAILED:
                lines.append(f"║     ✗ {step.description}")
                if step_exec.error:
                    lines.append(f"║     Error: {step_exec.error}")
            elif step_exec.status == StepStatus.SKIPPED:
                lines.append(f"║     ⏭️  {step.description} (skipped)")
        
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        
        # Controls
        if self.execution.status == WorkflowStatus.IN_PROGRESS:
            lines.append("║  [P]ause  [C]ancel  [R]etry failed step                    ║")
        elif self.execution.status == WorkflowStatus.PAUSED:
            lines.append("║  [R]esume  [C]ancel                                         ║")
        elif self.execution.status == WorkflowStatus.FAILED:
            lines.append("║  [R]etry  [C]ancel  [V]iew details                         ║")
        else:
            lines.append("║  [R]un again  [E]xit                                        ║")
        
        lines.append("╚═══════════════════════════════════════════════════════════════╝")
        
        return '\n'.join(lines)
    
    def _get_status_icon(self, status: StepStatus) -> str:
        """Get icon for step status."""
        icons = {
            StepStatus.PENDING: '⏳',
            StepStatus.RUNNING: '🔄',
            StepStatus.COMPLETED: '✅',
            StepStatus.FAILED: '❌',
            StepStatus.SKIPPED: '⏭️',
            StepStatus.CANCELLED: '🚫'
        }
        return icons.get(status, '⏳')
```

### Search Results Screen

```python
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
            
            for i, result in enumerate(self.results[:10]):  # Show top 10
                icon = "📄" if result.get('type') == 'file' else "📁"
                relevance = result.get('relevance', 0)
                
                # Highlight selected
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
```

### Settings Screen

```python
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
        
        # Section navigation
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
```

## Interaction Patterns

### Navigation Patterns

```python
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
```

### Confirmation Dialogs

```python
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
```

### Input Prompts

```python
class InputPrompt:
    """Input prompt component."""
    
    def __init__(self, message: str, default: str = "", 
                 validator: Callable = None, password: bool = False):
        self.message = message
        self.default = default
        self.validator = validator
        self.password = password
        self.value = default
        self.error = None
    
    def render(self, width: int = 80) -> str:
        """Render input prompt."""
        lines = []
        
        lines.append("╔═══════════════════════════════════════════════════════════════╗")
        lines.append(f"║  {self.message}")
        
        if self.default:
            lines.append(f"║  Default: {self.default}")
        
        display_value = self.value if not self.password else "*" * len(self.value)
        lines.append(f"║  > {display_value}_")
        
        if self.error:
            lines.append("╠═══════════════════════════════════════════════════════════════╣")
            lines.append(f"║  ⚠ {self.error}")
        
        lines.append("╠═══════════════════════════════════════════════════════════════╣")
        lines.append("║  [ENTER] Submit  [ESC] Cancel                                 ║")
        lines.append("╚═══════════════════════════════════════════════════════════════╝")
        
        return '\n'.join(lines)
    
    def handle_input(self, char: str) -> Optional[str]:
        """Handle character input."""
        if char == '\r':  # Enter
            if self.validator:
                try:
                    if self.validator(self.value):
                        return self.value
                    else:
                        self.error = "Invalid input"
                        return None
                except Exception as e:
                    self.error = str(e)
                    return None
            return self.value
        elif char == '\x1b':  # Escape
            return None
        elif char == '\b':  # Backspace
            self.value = self.value[:-1]
            self.error = None
        elif len(char) == 1:  # Regular character
            self.value += char
            self.error = None
        
        return None
```

## Accessibility

### High Contrast Mode

```python
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
```

### Keyboard Navigation

```python
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
```

## Configuration

### UI Configuration

```toml
[ui]
theme = "dark"
width = 80
height = 24
enable_animations = true
enable_sounds = false

[ui.accessibility]
high_contrast = false
large_text = false
screen_reader_mode = false
keyboard_navigation = true

[ui.interactive]
show_suggestions = true
show_context = true
show_progress = true
auto_refresh = true

[ui.colors]
primary = "#3B82F6"
success = "#10B981"
warning = "#F59E0B"
error = "#EF4444"
```

## Testing Strategy

### UI Component Testing

```python
def test_menu_rendering():
    """Test menu component rendering."""
    menu = Menu(
        title="Test Menu",
        options=[
            {'id': '1', 'label': 'Option 1', 'icon': '📄'},
            {'id': '2', 'label': 'Option 2', 'icon': '📁'}
        ]
    )
    
    output = menu.render(width=60)
    
    assert "Test Menu" in output
    assert "Option 1" in output
    assert "Option 2" in output

def test_progress_bar():
    """Test progress bar rendering."""
    progress = ProgressBar.render(50, 100, width=40)
    
    assert "[" in progress
    assert "]" in progress
    assert "50.0%" in progress

def test_confirmation_dialog():
    """Test confirmation dialog."""
    dialog = ConfirmationDialog("Are you sure?", default=True)
    
    output = dialog.render(width=60)
    
    assert "Confirmation" in output
    assert "Are you sure?" in output
    assert "Yes" in output
    assert "No" in output
```

## Future Enhancements

### Rich Terminal Support

```python
class RichTerminal:
    """Rich terminal with colors and formatting."""
    
    @staticmethod
    def render_colored(text: str, color: str) -> str:
        """Render text with color."""
        # ANSI color codes
        colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'reset': '\033[0m'
        }
        
        return f"{colors.get(color, '')}{text}{colors['reset']}"
```

### Mouse Support

```python
class MouseNavigation:
    """Mouse navigation support."""
    
    @staticmethod
    def handle_click(x: int, y: int, component_bounds: Dict) -> Optional[str]:
        """Handle mouse click."""
        # Determine which component was clicked
        # Return component ID or action
        pass
```

## Conclusion

The Interactive Mode UI/UX Design provides a comprehensive system for creating consistent, accessible, and delightful terminal interfaces. By establishing clear design principles, reusable components, and standardized interaction patterns, it ensures that all interactive features in CIP CLI v2.0 provide a cohesive user experience.

The component-based architecture allows for rapid development of new screens while maintaining consistency, and the accessibility features ensure that the interface is usable by all developers regardless of their individual needs or preferences.
