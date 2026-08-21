# Context-Aware Suggestion System Design

## Overview

The suggestion system is the intelligence engine that analyzes repository state, user patterns, and context to provide actionable recommendations. This document details the architecture, algorithms, and implementation of the suggestion system.

## Architecture

### Core Components

```
SuggestionEngine
├── Analyzers (Multi-factor analysis)
│   ├── HealthAnalyzer
│   ├── IndexAnalyzer
│   ├── GitAnalyzer
│   ├── StackAnalyzer
│   ├── PatternAnalyzer
│   └── CustomAnalyzer (extensible)
├── Ranking Engine (Score & prioritize)
├── Filter Engine (Relevance & quality)
├── Context Manager (State tracking)
└── Learning System (Pattern recognition)
```

## Analyzer Components

### 1. HealthAnalyzer

Analyzes repository health and suggests remediation actions.

```python
class HealthAnalyzer:
    """Analyze repository health and generate suggestions."""
    
    def analyze(self, root, config):
        suggestions = []
        health_score = self._get_health_score(root)
        
        # Critical health issues
        if health_score['score'] < 50:
            suggestions.append(Suggestion(
                priority='critical',
                action='cip analyze',
                reason=f'Critical health score: {health_score["score"]}/100',
                impact='Identify and fix critical repository issues',
                confidence=0.95,
                category='health'
            ))
        
        # Test failures
        if health_score.get('broken_tests', 0) > 0:
            suggestions.append(Suggestion(
                priority='high',
                action='cip broken',
                reason=f'{health_score["broken_tests"]} failing tests detected',
                impact='Fix failing tests to improve stability',
                confidence=0.90,
                category='testing'
            ))
        
        # Type errors
        if health_score.get('type_errors', 0) > 0:
            suggestions.append(Suggestion(
                priority='high',
                action='cip verify --typecheck',
                reason=f'{health_score["type_errors"]} type errors found',
                impact='Ensure type safety across the codebase',
                confidence=0.85,
                category='quality'
            ))
        
        # Lint issues
        if health_score.get('lint_issues', 0) > 10:
            suggestions.append(Suggestion(
                priority='medium',
                action='cip verify --lint',
                reason=f'{health_score["lint_issues"]} lint issues detected',
                impact='Improve code quality and consistency',
                confidence=0.80,
                category='quality'
            ))
        
        return suggestions
    
    def _get_health_score(self, root):
        """Get comprehensive health score."""
        from cipkg import gapfill
        return gapfill.score(root)
```

### 2. IndexAnalyzer

Monitors index state and suggests maintenance actions.

```python
class IndexAnalyzer:
    """Analyze index state and freshness."""
    
    def analyze(self, root, config):
        suggestions = []
        index_status = self._get_index_status(root)
        
        # Stale index
        if index_status.get('stale', False):
            suggestions.append(Suggestion(
                priority='medium',
                action='cip sync',
                reason='Index is out of date',
                impact='Update search results and analysis accuracy',
                confidence=0.95,
                category='maintenance'
            ))
        
        # Missing embeddings
        if index_status.get('embedding_coverage', 100) < 80:
            suggestions.append(Suggestion(
                priority='medium',
                action='cip embed',
                reason=f'Only {index_status["embedding_coverage"]}% of chunks embedded',
                impact='Improve semantic search quality',
                confidence=0.85,
                category='maintenance'
            ))
        
        # Large database size
        if index_status.get('db_size_mb', 0) > 500:
            suggestions.append(Suggestion(
                priority='low',
                action='cip vacuum --days 30',
                reason=f'Database size: {index_status["db_size_mb"]}MB',
                impact='Reduce database size and improve performance',
                confidence=0.75,
                category='maintenance'
            ))
        
        return suggestions
    
    def _get_index_status(self, root):
        """Get current index status."""
        from cipkg.store import connect
        from cipkg.base import data_dir
        import os
        
        con = connect(root)
        stats = con.execute("""
            SELECT 
                COUNT(*) as total_chunks,
                COUNT(v) as embedded_chunks,
                MAX(timestamp) as last_update
            FROM chunks
            LEFT JOIN vectors ON chunks.id = vectors.chunk_id
        """).fetchone()
        
        total = stats['total_chunks'] or 0
        embedded = stats['embedded_chunks'] or 0
        coverage = (embedded / total * 100) if total > 0 else 100
        
        # Check staleness (older than 1 hour)
        import time
        stale = (time.time() - stats['last_update']) > 3600 if stats['last_update'] else True
        
        # Database size
        db_path = os.path.join(data_dir(root), "index.db")
        db_size = os.path.getsize(db_path) / (1024 * 1024) if os.path.exists(db_path) else 0
        
        return {
            'total_chunks': total,
            'embedded_chunks': embedded,
            'embedding_coverage': coverage,
            'stale': stale,
            'db_size_mb': db_size
        }
```

### 3. GitAnalyzer

Analyzes git state and suggests context-aware actions.

```python
class GitAnalyzer:
    """Analyze git state and suggest actions."""
    
    def analyze(self, root, config):
        suggestions = []
        git_state = self._get_git_state(root)
        
        # Uncommitted changes
        if git_state.get('uncommitted_files', 0) > 0:
            suggestions.append(Suggestion(
                priority='medium',
                action='cip audit --diff',
                reason=f'{git_state["uncommitted_files"]} uncommitted files',
                impact='Review code quality before committing',
                confidence=0.85,
                category='git'
            ))
            
            # Suggest pre-commit workflow
            if git_state['uncommitted_files'] > 3:
                suggestions.append(Suggestion(
                    priority='high',
                    action='cip workflow pre-commit',
                    reason='Multiple files changed - comprehensive checks recommended',
                    impact='Run full pre-commit validation workflow',
                    confidence=0.90,
                    category='workflow'
                ))
        
        # Branching suggestions
        if git_state.get('on_main', False) and git_state.get('uncommitted_files', 0) > 0:
            suggestions.append(Suggestion(
                priority='low',
                action='git checkout -b feature/ descriptive-name',
                reason='Working directly on main branch',
                impact='Create feature branch for safer development',
                confidence=0.70,
                category='git'
            ))
        
        # Stashed changes
        if git_state.get('stashed_count', 0) > 0:
            suggestions.append(Suggestion(
                priority='low',
                action='git stash list',
                reason=f'{git_state["stashed_count"]} stashed changes',
                impact='Review and clean up stashed work',
                confidence=0.65,
                category='git'
            ))
        
        return suggestions
    
    def _get_git_state(self, root):
        """Get current git state."""
        import subprocess
        
        try:
            # Get current branch
            branch = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=root,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            
            # Get uncommitted files
            uncommitted = subprocess.check_output(
                ['git', 'status', '--porcelain'],
                cwd=root,
                stderr=subprocess.DEVNULL,
                text=True
            )
            uncommitted_count = len([line for line in uncommitted.split('\n') if line.strip()])
            
            # Get stashed count
            stashed = subprocess.check_output(
                ['git', 'stash', 'list'],
                cwd=root,
                stderr=subprocess.DEVNULL,
                text=True
            )
            stashed_count = len([line for line in stashed.split('\n') if line.strip()])
            
            return {
                'branch': branch,
                'on_main': branch in ['main', 'master', 'develop'],
                'uncommitted_files': uncommitted_count,
                'stashed_count': stashed_count
            }
        except subprocess.CalledProcessError:
            return {
                'branch': 'unknown',
                'on_main': False,
                'uncommitted_files': 0,
                'stashed_count': 0
            }
```

### 4. StackAnalyzer

Provides stack-specific suggestions based on detected technologies.

```python
class StackAnalyzer:
    """Analyze technology stack and provide stack-specific suggestions."""
    
    def analyze(self, root, config):
        suggestions = []
        stack_info = self._get_stack_info(root)
        
        # Next.js specific
        if 'nextjs' in stack_info.get('frameworks', []):
            suggestions.extend(self._nextjs_suggestions(stack_info))
        
        # Python specific
        if 'python' in stack_info.get('languages', []):
            suggestions.extend(self._python_suggestions(stack_info))
        
        # React specific
        if 'react' in stack_info.get('frameworks', []):
            suggestions.extend(self._react_suggestions(stack_info))
        
        # Database specific
        if stack_info.get('database'):
            suggestions.extend(self._database_suggestions(stack_info))
        
        return suggestions
    
    def _nextjs_suggestions(self, stack_info):
        """Next.js specific suggestions."""
        suggestions = []
        
        # Route analysis
        suggestions.append(Suggestion(
            priority='medium',
            action='cip routes',
            reason='Next.js project detected',
            impact='Analyze route structure and integrity',
            confidence=0.85,
            category='stack'
        ))
        
        # Model usage
        if 'prisma' in stack_info.get('orms', []):
            suggestions.append(Suggestion(
                priority='medium',
                action='cip models',
                reason='Prisma ORM detected',
                impact='Analyze Prisma model usage and relationships',
                confidence=0.90,
                category='stack'
            ))
        
        return suggestions
    
    def _python_suggestions(self, stack_info):
        """Python specific suggestions."""
        suggestions = []
        
        # Type checking
        if 'mypy' in stack_info.get('tools', []):
            suggestions.append(Suggestion(
                priority='medium',
                action='cip verify --typecheck',
                reason='MyPy detected in project',
                impact='Run type checking with MyPy',
                confidence=0.85,
                category='stack'
            ))
        
        # Test coverage
        if 'pytest' in stack_info.get('test_frameworks', []):
            suggestions.append(Suggestion(
                priority='low',
                action='cip coverage',
                reason='PyTest detected',
                impact='Analyze test coverage',
                confidence=0.75,
                category='stack'
            ))
        
        return suggestions
    
    def _get_stack_info(self, root):
        """Get detailed stack information."""
        from cipkg import detect
        from cipkg.base import load_config
        
        cfg = load_config(root)
        detection = detect.detect(root, cfg)
        
        return {
            'languages': detection.get('languages', []),
            'frameworks': detection.get('frameworks', []),
            'orms': detection.get('orms', []),
            'test_frameworks': detection.get('test_frameworks', []),
            'tools': detection.get('tools', []),
            'database': detection.get('database')
        }
```

### 5. PatternAnalyzer

Learns from user behavior and provides personalized suggestions.

```python
class PatternAnalyzer:
    """Analyze user patterns and provide personalized suggestions."""
    
    def analyze(self, root, config):
        suggestions = []
        user_patterns = self._load_user_patterns()
        
        # Time-based patterns
        current_hour = self._get_current_hour()
        if current_hour in user_patterns.get('peak_hours', []):
            # Suggest common workflows during peak hours
            common_workflow = user_patterns.get('peak_workflow')
            if common_workflow:
                suggestions.append(Suggestion(
                    priority='low',
                    action=f'cip workflow {common_workflow}',
                    reason=f'Common workflow during this time',
                    impact='Streamline your regular workflow',
                    confidence=0.70,
                    category='personal'
                ))
        
        # Command sequence patterns
        recent_commands = user_patterns.get('recent_commands', [])
        if len(recent_commands) >= 2:
            last_command = recent_commands[-1]
            if last_command == 'cip audit':
                suggestions.append(Suggestion(
                    priority='medium',
                    action='cip findings',
                    reason='You just ran audit - check findings',
                    impact='Review audit findings',
                    confidence=0.80,
                    category='personal'
                ))
        
        # Error recovery patterns
        if user_patterns.get('last_command_failed'):
            recovery_suggestion = user_patterns.get('common_recovery')
            if recovery_suggestion:
                suggestions.append(Suggestion(
                    priority='high',
                    action=recovery_suggestion,
                    reason='Last command failed - common recovery',
                    impact='Try common recovery action',
                    confidence=0.75,
                    category='personal'
                ))
        
        return suggestions
    
    def _load_user_patterns(self):
        """Load user behavior patterns."""
        # Implementation would load from pattern database
        return {
            'peak_hours': [9, 10, 14, 15],
            'peak_workflow': 'pre-commit',
            'recent_commands': ['cip sync', 'cip audit'],
            'last_command_failed': False,
            'common_recovery': 'cip doctor'
        }
    
    def _get_current_hour(self):
        """Get current hour (0-23)."""
        import datetime
        return datetime.datetime.now().hour
```

## Ranking Engine

### Multi-Factor Scoring

```python
class RankingEngine:
    """Rank suggestions by multiple factors."""
    
    def rank(self, suggestions):
        """Score and sort suggestions."""
        scored = []
        
        for suggestion in suggestions:
            score = self._calculate_score(suggestion)
            scored.append((score, suggestion))
        
        # Sort by score (descending)
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [suggestion for _, suggestion in scored]
    
    def _calculate_score(self, suggestion):
        """Calculate composite score for suggestion."""
        weights = {
            'priority': 0.40,
            'confidence': 0.30,
            'relevance': 0.20,
            'freshness': 0.10
        }
        
        priority_score = self._priority_score(suggestion.priority)
        confidence_score = suggestion.confidence
        relevance_score = self._relevance_score(suggestion)
        freshness_score = self._freshness_score(suggestion)
        
        total = (
            weights['priority'] * priority_score +
            weights['confidence'] * confidence_score +
            weights['relevance'] * relevance_score +
            weights['freshness'] * freshness_score
        )
        
        return total
    
    def _priority_score(self, priority):
        """Convert priority to numeric score."""
        priority_map = {
            'critical': 1.0,
            'high': 0.85,
            'medium': 0.70,
            'low': 0.55
        }
        return priority_map.get(priority, 0.50)
    
    def _relevance_score(self, suggestion):
        """Calculate relevance based on context."""
        # Would consider factors like:
        # - Current working directory
        # - Recent file access
        # - Current git state
        # - Time of day
        return 0.75  # Placeholder
    
    def _freshness_score(self, suggestion):
        """Calculate freshness score."""
        # Newer suggestions get higher scores
        # Recurring suggestions might get lower scores
        return 0.80  # Placeholder
```

## Filter Engine

### Relevance Filtering

```python
class FilterEngine:
    """Filter suggestions based on relevance and quality."""
    
    def filter(self, suggestions, context):
        """Apply filtering rules."""
        filtered = suggestions
        
        # Remove duplicates
        filtered = self._remove_duplicates(filtered)
        
        # Filter by category relevance
        filtered = self._filter_by_category(filtered, context)
        
        # Limit by priority
        filtered = self._limit_by_priority(filtered)
        
        # Apply user preferences
        filtered = self._apply_user_preferences(filtered, context)
        
        return filtered
    
    def _remove_duplicates(self, suggestions):
        """Remove duplicate suggestions."""
        seen = set()
        unique = []
        
        for suggestion in suggestions:
            key = (suggestion.action, suggestion.category)
            if key not in seen:
                seen.add(key)
                unique.append(suggestion)
        
        return unique
    
    def _filter_by_category(self, suggestions, context):
        """Filter based on category relevance."""
        # Would implement context-aware category filtering
        return suggestions
    
    def _limit_by_priority(self, suggestions):
        """Limit suggestions per priority level."""
        priority_limits = {
            'critical': 5,
            'high': 5,
            'medium': 3,
            'low': 2
        }
        
        filtered = []
        counts = {p: 0 for p in priority_limits}
        
        for suggestion in suggestions:
            if counts[suggestion.priority] < priority_limits[suggestion.priority]:
                filtered.append(suggestion)
                counts[suggestion.priority] += 1
        
        return filtered
    
    def _apply_user_preferences(self, suggestions, context):
        """Apply user preference filters."""
        # Would consider user-configured preferences
        return suggestions
```

## Data Structures

### Suggestion Model

```python
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class Suggestion:
    """Represents a single suggestion."""
    action: str                    # Command to run
    reason: str                    # Why this is suggested
    impact: str                    # Expected impact
    priority: str                  # critical, high, medium, low
    confidence: float              # 0.0 to 1.0
    category: str                  # health, git, stack, personal, etc.
    score: Optional[float] = None # Calculated score
    metadata: Optional[dict] = None # Additional context
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}
```

### Context Model

```python
@dataclass
class RepositoryContext:
    """Complete repository context for suggestions."""
    root: str
    repo_type: str
    health_score: dict
    index_status: dict
    git_state: dict
    stack_info: dict
    user_patterns: dict
    current_time: datetime
    working_directory: str
    recent_files: List[str]
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'root': self.root,
            'repo_type': self.repo_type,
            'health_score': self.health_score,
            'index_status': self.index_status,
            'git_state': self.git_state,
            'stack_info': self.stack_info,
            'user_patterns': self.user_patterns,
            'current_time': self.current_time.isoformat(),
            'working_directory': self.working_directory,
            'recent_files': self.recent_files
        }
```

## Integration Points

### CLI Integration

```python
# In lib/cipkg/cli.py

def handle_suggest_command(root, args):
    """Handle suggest command."""
    from cipkg.interactive import SuggestionEngine
    
    engine = SuggestionEngine(root, load_config(root))
    suggestions = engine.generate_suggestions()
    
    # Display suggestions
    _display_suggestions(suggestions)

def _display_suggestions(suggestions):
    """Display suggestions in a user-friendly format."""
    if not suggestions:
        print("No suggestions at this time. Repository looks good!")
        return
    
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║  Intelligent Suggestions                                       ║")
    print("╠═══════════════════════════════════════════════════════════════╣")
    
    for i, suggestion in enumerate(suggestions, 1):
        priority_icon = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }.get(suggestion.priority, '⚪')
        
        print(f"║  {priority_icon} {i}. {suggestion.action}")
        print(f"║     Reason: {suggestion.reason}")
        print(f"║     Impact: {suggestion.impact}")
        print(f"║     Confidence: {int(suggestion.confidence * 100)}%")
        print("║")
    
    print("╚═══════════════════════════════════════════════════════════════╝")
```

### Interactive Mode Integration

```python
# In lib/cipkg/interactive.py

class InteractiveEngine:
    """Main interactive engine."""
    
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.suggestion_engine = SuggestionEngine(root, config)
        self.context = self._build_context()
    
    def show_suggestions_menu(self):
        """Show suggestions in interactive menu."""
        suggestions = self.suggestion_engine.generate_suggestions()
        
        print("╔═══════════════════════════════════════════════════════════════╗")
        print("║  🎯 Suggested Actions                                         ║")
        print("╠═══════════════════════════════════════════════════════════════╣")
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"║  {i}) {suggestion.action}")
            print(f"║     {suggestion.reason}")
        
        print("║                                                                ║")
        print("║  Select action or press Enter to continue: _")
        
        choice = input().strip()
        if choice.isdigit() and 1 <= int(choice) <= len(suggestions):
            selected = suggestions[int(choice) - 1]
            self._execute_suggestion(selected)
```

## Performance Optimization

### Caching Strategy

```python
class CachedAnalyzer:
    """Analyzer with caching support."""
    
    def __init__(self, cache_ttl=300):
        self.cache = {}
        self.cache_ttl = cache_ttl
    
    def analyze(self, root, config):
        cache_key = self._get_cache_key(root, config)
        
        if cache_key in self.cache:
            cached, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached
        
        result = self._do_analyze(root, config)
        self.cache[cache_key] = (result, time.time())
        
        return result
```

### Lazy Loading

```python
class LazySuggestionEngine:
    """Suggestion engine with lazy analyzer loading."""
    
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self._analyzers = None
    
    @property
    def analyzers(self):
        """Lazy load analyzers."""
        if self._analyzers is None:
            self._analyzers = [
                HealthAnalyzer(),
                IndexAnalyzer(),
                GitAnalyzer(),
                StackAnalyzer(),
                PatternAnalyzer()
            ]
        return self._analyzers
```

## Testing Strategy

### Unit Tests

```python
def test_health_analyzer_critical():
    """Test health analyzer with critical issues."""
    analyzer = HealthAnalyzer()
    mock_health = {'score': 45, 'broken_tests': 5}
    
    suggestions = analyzer.analyze(mock_health)
    
    assert len(suggestions) > 0
    assert any(s.priority == 'critical' for s in suggestions)

def test_ranking_engine():
    """Test suggestion ranking."""
    engine = RankingEngine()
    suggestions = [
        Suggestion('action1', 'reason1', 'impact1', 'low', 0.5, 'test'),
        Suggestion('action2', 'reason2', 'impact2', 'high', 0.9, 'test'),
    ]
    
    ranked = engine.rank(suggestions)
    
    assert ranked[0].priority == 'high'
```

### Integration Tests

```python
def test_suggestion_engine_integration():
    """Test full suggestion engine integration."""
    engine = SuggestionEngine(test_repo, test_config)
    suggestions = engine.generate_suggestions()
    
    assert len(suggestions) > 0
    assert all(isinstance(s, Suggestion) for s in suggestions)
```

## Future Enhancements

### Machine Learning Integration

- Train models on successful suggestion acceptance
- Predict optimal suggestions based on complex patterns
- Implement reinforcement learning for continuous improvement

### Collaborative Filtering

- Learn from team patterns
- Suggest workflows based on team best practices
- Share successful patterns across teams

### Natural Language Processing

- Understand user intent from natural language
- Generate natural language explanations
- Enable conversational interaction

## Conclusion

The context-aware suggestion system provides the intelligence backbone for the CIP CLI v2.0 upgrade. By analyzing multiple factors—repository health, index state, git status, technology stack, and user patterns—it delivers actionable, relevant suggestions that significantly improve developer productivity.

The modular architecture allows for easy extension with new analyzers, while the ranking and filtering engines ensure users receive the most relevant and high-quality suggestions. The system is designed to learn and improve over time, making it increasingly valuable as users interact with it.
