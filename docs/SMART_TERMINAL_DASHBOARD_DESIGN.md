# Smart Terminal Dashboard Design

## Overview

The smart terminal dashboard is the primary interface for CIP v2.0, launched when a user types `cip` without arguments. It provides a comprehensive view of repository status, quick actions, and intelligent suggestions.

## Dashboard States

### State 1: Uninitialized Repository
**Trigger**: No `.cip/` directory found

**UI Components**:
```
╔═══════════════════════════════════════════════════════════════╗
║  CIP v2.0 - Repository Not Initialized                        ║
╠═══════════════════════════════════════════════════════════════╣
║  📁 Repository: /path/to/repo                                 ║
║  🔍 Detected: Python project with pytest                       ║
║  ⚠️  CIP not initialized                                       ║
╠═══════════════════════════════════════════════════════════════╣
║  🚀 Quick Start:                                               ║
║  [1] Initialize CIP (recommended)                              ║
║  [2] Initialize with custom settings                           ║
║  [3] Learn more about CIP                                      ║
║  [4] Exit                                                       ║
╠═══════════════════════════════════════════════════════════════╣
║  💡 What CIP will do:                                          ║
║  • Scan all files in repository                                ║
║  • Build code map (symbols, imports, relationships)             ║
║  • Index git history for change tracking                        ║
║  • Enable intelligent search and analysis                       ║
╚═══════════════════════════════════════════════════════════════╝
```

### State 2: Initialized But Not Indexed
**Trigger**: `.cip/` exists but no index.db or stale index

**UI Components**:
```
╔═══════════════════════════════════════════════════════════════╗
║  CIP v2.0 - Repository Ready                                  ║
╠═══════════════════════════════════════════════════════════════╣
║  📁 Repository: /path/to/repo                                 ║
║  🏷️  Type: Python project                                      ║
║  ✅ CIP initialized                                            ║
║  ⚠️  Index needs building                                      ║
╠═══════════════════════════════════════════════════════════════╣
║  🚀 Next Steps:                                                ║
║  [1] Build index (recommended)                                ║
║  [2] Build index with embeddings (slower)                      ║
║  [3] Skip and use basic features                               ║
║  [4] Exit                                                       ║
╠═══════════════════════════════════════════════════════════════╣
║  💡 Index enables:                                             ║
║  • Intelligent code search                                     ║
║  • Symbol navigation and graph traversal                       ║
║  • Impact analysis and change tracking                         ║
║  • Context-aware suggestions                                   ║
╚═══════════════════════════════════════════════════════════════╝
```

### State 3: Active Dashboard (Default)
**Trigger**: CIP initialized and index fresh

## Main Dashboard Layout

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CIP v2.0 - my-project                                          [Settings] [Help] ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Repository Status Card                                        ║ ║
║  ║ ╔════════════════════════════════════════════════════════════════════╗ ║ ║
║  ║ ║ 🏥 Health: 85/100 (Good)  🔄 Index: Fresh  📦 Git: 3 changed ║ ║ ║
║  ║ ║ 📊 Files: 1,234  🧩 Symbols: 8,567  🔗 Edges: 12,345          ║ ║ ║
║  ║ ║ 🧵 Branch: feature/auth  📅 Last sync: 2 hours ago           ║ ║ ║
║  ║ ╚════════════════════════════════════════════════════════════════════╝ ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Quick Actions Panel                                            ║ ║
║  ║ ╔════════════════════════════════════════════════════════════════════╗ ║ ║
║  ║ ║ 🔍 Search codebase     📊 Analyze health  ⚙️  Run workflow    ║ ║ ║
║  ║ ║ 🔧 Audit changes      📋 View findings    🚀 Sync index      ║ ║ ║
║  ║ ║ 📈 Check impact       🗺️  View map         💡 Get suggestions ║ ║ ║
║  ║ ╚════════════════════════════════════════════════════════════════════╝ ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Intelligent Suggestions (3)                                     ║ ║
║  ║ ╔════════════════════════════════════════════════════════════════════╗ ║ ║
║  ║ ║ 🔴 [1] cip audit --diff   Review uncommitted changes            ║ ║ ║
║  ║ ║     Reason: You have 3 uncommitted files                       ║ ║ ║
║  ║ ║                                                                ║ ║ ║
║  ║ ║ 🟠 [2] cip workflow pre-commit   Comprehensive pre-commit check ║ ║ ║
║  ║ ║     Reason: Common workflow before committing                  ║ ║ ║
║  ║ ║                                                                ║ ║ ║
║  ║ ║ 🟡 [3] cip sync   Update index to include recent changes       ║ ║ ║
║  ║ ║     Reason: Index is 2 hours old                              ║ ║ ║
║  ║ ╚════════════════════════════════════════════════════════════════════╝ ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Recent Activity Feed                                            ║ ║
║  ║ ╔════════════════════════════════════════════════════════════════════╗ ║ ║
║  ║ ║ ✅ 2h ago: Index synced (1,234 files)                           ║ ║ ║
║  ║ ║ 🔧 3h ago: Audit completed - 0 issues found                      ║ ║ ║
║  ║ ║ 📝 5h ago: Committed to feature/auth                            ║ ║ ║
║  ║ ║ ⚠️  1d ago: Health score dropped from 90 to 85                   ║ ║ ║
║  ║ ╚════════════════════════════════════════════════════════════════════╝ ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Navigation Bar                                                   ║ ║
║  ║ ╔════════════════════════════════════════════════════════════════════╗ ║ ║
║  ║ ║ [Dashboard] [Search] [Workflows] [Findings] [Settings] [Help]   ║ ║ ║
║  ║ ╚════════════════════════════════════════════════════════════════════╝ ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Command: _                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## Dashboard Components

### 1. Repository Status Card
**Purpose**: Show overall repository health and status at a glance

**Components**:
- Health score with color coding (green > 80, yellow 60-80, red < 60)
- Index freshness indicator
- Git state (branch, uncommitted files)
- File/symbol/edge counts
- Last sync timestamp

**Interactions**:
- Click health score to see detailed health report
- Click git state to see changed files
- Hover for more details

### 2. Quick Actions Panel
**Purpose**: Provide fast access to common operations

**Actions**:
- **Search**: Launch intelligent search
- **Analyze**: Run comprehensive health analysis
- **Workflow**: Run guided workflow
- **Audit**: Audit current changes
- **Findings**: View open findings
- **Sync**: Update index
- **Impact**: Check change impact
- **Map**: View repository map
- **Suggestions**: Get intelligent suggestions

**Context Awareness**:
- Actions adapt based on current state
- High-priority actions highlighted
- Recently used actions shown first

### 3. Intelligent Suggestions Panel
**Purpose**: Show context-aware suggestions

**Features**:
- Priority-based ordering (critical, high, medium, low)
- Color-coded priority indicators
- Actionable suggestions with one-click execution
- Confidence scores shown
- Dismiss suggestions

**Context Awareness**:
- Based on git state, health score, time patterns
- Personalized based on user behavior
- Updated in real-time

### 4. Activity Feed
**Purpose**: Show recent operations and changes

**Features**:
- Chronological activity log
- Different activity types (sync, audit, commit, etc.)
- Timestamps with relative time
- Color-coded activity types
- Click to see details

**Filtering**:
- Filter by activity type
- Filter by time range
- Search within activity

### 5. Navigation Bar
**Purpose**: Navigate between different views

**Views**:
- **Dashboard**: Main status view
- **Search**: Intelligent search interface
- **Workflows**: Workflow execution
- **Findings**: Audit findings
- **Settings**: Configuration
- **Help**: Documentation

**Keyboard Shortcuts**:
- Alt+1-6 for quick navigation
- Tab to cycle through views

### 6. Command Input
**Purpose**: Execute commands directly from dashboard

**Features**:
- Auto-completion for commands
- Command history
- Context-aware suggestions
- Syntax highlighting

## Dashboard Views

### Search View
```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CIP v2.0 - Search                                                [Dashboard] [Help] ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Search Input                                                    ║ ║
║  ║ ╔════════════════════════════════════════════════════════════════════╗ ║ ║
║  ║ ║ 🔍 Search: [____________________________] [Search] [Advanced]   ║ ║ ║
║  ║ ║ 📁 Context: [current directory ▼]  📄 File types: [*.py ▼]     ║ ║ ║
║  ║ ╚════════════════════════════════════════════════════════════════════╝ ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Search Results (10)                                             ║ ║
║  ║ ╔════════════════════════════════════════════════════════════════════╗ ║ ║
║  ║ ║ 📄 src/auth/login.py (98% relevance)                           ║ ║ ║
║  ║ ║     def authenticate_user(username, password):                ║ ║ ║
║  ║ ║     Modified today | 45 lines                                 ║ ║ ║
║  ║ ║                                                                ║ ║ ║
║  ║ ║ 📄 src/auth/models.py (85% relevance)                          ║ ║ ║
║  ║ ║     class User(BaseModel):                                    ║ ║ ║
║  ║ ║     Modified yesterday | 120 lines                             ║ ║ ║
║  ║ ╚════════════════════════════════════════════════════════════════════╝ ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Actions: [Open] [Graph] [Impact] [Context] [Copy Path]            ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Workflow View
```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CIP v2.0 - Workflows                                              [Dashboard] [Help] ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Available Workflows                                             ║ ║
║  ║ ╔════════════════════════════════════════════════════════════════════╗ ║ ║
║  ║ ║ ⚙️  Pre-Commit Workflow                                       ║ ║ ║
║  ║ ║     Comprehensive checks before committing changes             ║ ║ ║
║  ║ ║     [Run] [Configure]                                          ║ ║ ║
║  ║ ║                                                                ║ ║ ║
║  ║ ║ 🏥 Repository Diagnosis                                        ║ ║ ║
║  ║ ║     Diagnose repository issues and suggest fixes                ║ ║ ║
║  ║ ║     [Run] [Configure]                                          ║ ║ ║
║  ║ ╚════════════════════════════════════════════════════════════════════╝ ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Recent Workflow Executions                                      ║ ║
║  ║ ╔════════════════════════════════════════════════════════════════════╗ ║ ║
║  ║ ║ ✅ Pre-Commit - Completed 2h ago (5 steps)                       ║ ║ ║
║  ║ ║     [View Report] [Re-run]                                     ║ ║ ║
║  ║ ║                                                                ║ ║ ║
║  ║ ║ ✅ Diagnosis - Completed yesterday (4 steps)                   ║ ║ ║
║  ║ ║     [View Report] [Re-run]                                     ║ ║ ║
║  ║ ╚════════════════════════════════════════════════════════════════════╝ ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## Initialization UI

### Step-by-Step Initialization
```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CIP v2.0 - Initialization                                         [Cancel] [Help] ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Step 1/4: Repository Detection                                  ║ ║
║  ║ ╔════════════════════════════════════════════════════════════════════╗ ║ ║
║  ║ ║ ✅ Detected: Python project                                    ║ ║ ║
║  ║ ║ ✅ Found: pytest, requirements.txt, setup.cfg                   ║ ║ ║
║  ║ ║ ✅ Git repository detected                                     ║ ║ ║
║  ║ ╚════════════════════════════════════════════════════════════════════╝ ║ ║
║  ║                                                                ║ ║ ║
║  ║ [← Back] [Next →]                                               ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Progress Display
```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CIP v2.0 - Initializing Repository                                 [Cancel] ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Progress                                                        ║ ║
║  ║ ╔════════════════════════════════════════════════════════════════════╗ ║ ║
║  ║ ║ Scanning files... [████████████░░░░░░░░░░░░░░░] 40% (456/1,234) ║ ║ ║
║  ║ ║                                                                ║ ║ ║
║  ║ ║ ✅ Created .cip/ directory                                     ║ ║ ║
║  ║ ║ ✅ Installed git hooks                                         ║ ║ ║
║  ║ ║ ⏳ Building code map...                                        ║ ║ ║
║  ║ ║ ⏳ Indexing git history...                                     ║ ║ ║
║  ║ ╚════════════════════════════════════════════════════════════════════╝ ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ╔════════════════════════════════════════════════════════════════════════╗ ║
║  ║ Estimated time remaining: 2:30                                   ║ ║
║  ╚════════════════════════════════════════════════════════════════════════╝ ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## Keyboard Navigation

### Global Shortcuts
- `Ctrl+C` - Exit dashboard
- `Ctrl+L` - Clear command input
- `Ctrl+R` - Refresh dashboard
- `F1` - Show help
- `F2` - Open settings
- `Tab` - Cycle through views
- `Shift+Tab` - Cycle backwards through views

### Dashboard Shortcuts
- `1-9` - Execute quick action
- `s` - Focus search input
- `w` - Go to workflows
- `f` - Go to findings
- `d` - Return to dashboard
- `?` - Show keyboard shortcuts

### Navigation Shortcuts
- `Alt+1` - Dashboard
- `Alt+2` - Search
- `Alt+3` - Workflows
- `Alt+4` - Findings
- `Alt+5` - Settings
- `Alt+6` - Help

## Responsive Design

### Terminal Size Adaptation
- **Large terminals** (80+ columns): Full dashboard layout
- **Medium terminals** (60-79 columns): Simplified layout
- **Small terminals** (40-59 columns): Compact layout
- **Very small terminals** (< 40 columns): Minimal layout

### Adaptive Components
- Status card adapts to available width
- Quick actions wrap based on space
- Suggestions panel shows fewer items in small terminals
- Activity feed truncates in small terminals

## Accessibility

### High Contrast Mode
- Toggleable high contrast theme
- Color-blind friendly color palette
- Clear visual hierarchy

### Keyboard Navigation
- Full keyboard navigation support
- Screen reader compatibility
- Focus indicators

### Font Scaling
- Adjustable font sizes
- Large text mode
- Text-to-speech support

## Performance Considerations

### Lazy Loading
- Dashboard components load progressively
- Status indicators load first
- Activity feed loads last
- Suggestions load asynchronously

### Caching
- Dashboard state cached between sessions
- Status updates use incremental refresh
- Context data cached with TTL

### Background Updates
- Status updates run in background
- Suggestions refresh periodically
- Activity feed updates asynchronously

## Error Handling

### Dashboard Errors
- Graceful degradation on component failure
- Error messages in dedicated panel
- Retry mechanisms for transient failures
- Fallback to simplified view

### Initialization Errors
- Clear error messages
- Suggested fixes
- Retry options
- Partial initialization support

## Future Enhancements

### Planned Features
- Custom dashboard layouts
- Widget system for extensibility
- Real-time collaboration indicators
- Integration with external tools
- Mobile-friendly terminal interface

### Extension Points
- Custom dashboard widgets
- Custom quick actions
- Custom suggestion sources
- Custom activity feed items
- Custom navigation views
