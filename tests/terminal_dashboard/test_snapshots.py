"""
Snapshot tests for terminal dashboard visual regression testing.

Uses pytest-textual-snapshot to detect visual changes in the UI.
"""
import pytest
from textual.app import App
import sys
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from cipkg.terminal_dashboard import (
    InitializationScreen,
    IndexNeededScreen,
    DashboardState
)


@pytest.mark.snapshot
def test_initialization_screen_snapshot(snap_compare):
    """Test InitializationScreen visual appearance."""
    import tempfile
    tmpdir = tempfile.mkdtemp()
    
    screen = InitializationScreen(tmpdir, DashboardState.INITIALIZATION_NEEDED)
    
    class TestApp(App):
        def compose(self):
            yield screen
    
    app = TestApp()
    assert snap_compare(app)


@pytest.mark.snapshot 
def test_index_needed_screen_snapshot(snap_compare):
    """Test IndexNeededScreen visual appearance."""
    import tempfile
    tmpdir = tempfile.mkdtemp()
    
    screen = IndexNeededScreen(tmpdir, DashboardState.INDEX_NEEDED)
    
    class TestApp(App):
        def compose(self):
            yield screen
    
    app = TestApp()
    assert snap_compare(app)