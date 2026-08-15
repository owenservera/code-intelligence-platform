"""
Suggestion Engine for CIP CLI v2.0

This module provides intelligent suggestion generation based on repository state,
user patterns, and context analysis.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import os


class Priority(Enum):
    """Suggestion priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Suggestion:
    """Represents a single suggestion."""
    action: str
    reason: str
    impact: str
    priority: Priority
    confidence: float
    category: str
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class SuggestionAnalyzer:
    """Base class for suggestion analyzers."""
    
    def analyze(self, root: str, config: Dict[str, Any], context: Any = None) -> List[Suggestion]:
        """Analyze and generate suggestions."""
        raise NotImplementedError


class HealthAnalyzer(SuggestionAnalyzer):
    """Analyze repository health and generate suggestions."""
    
    def analyze(self, root: str, config: Dict[str, Any], context: Any = None) -> List[Suggestion]:
        """Analyze repository health and generate suggestions."""
        suggestions = []
        
        try:
            from cipkg import gapfill
            health_score = gapfill.score(root)
        except (ImportError, Exception):
            health_score = {'score': 100}  # Default if unavailable
        
        # Critical health issues
        if health_score.get('score', 100) < 50:
            suggestions.append(Suggestion(
                action='cip analyze',
                reason=f'Critical health score: {health_score["score"]}/100',
                impact='Identify and fix critical repository issues',
                priority=Priority.CRITICAL,
                confidence=0.95,
                category='health'
            ))
        
        # Test failures
        if health_score.get('broken_tests', 0) > 0:
            suggestions.append(Suggestion(
                action='cip broken',
                reason=f'{health_score["broken_tests"]} failing tests detected',
                impact='Fix failing tests to improve stability',
                priority=Priority.HIGH,
                confidence=0.90,
                category='testing'
            ))
        
        # Type errors
        if health_score.get('type_errors', 0) > 0:
            suggestions.append(Suggestion(
                action='cip verify --typecheck',
                reason=f'{health_score["type_errors"]} type errors found',
                impact='Ensure type safety across the codebase',
                priority=Priority.HIGH,
                confidence=0.85,
                category='quality'
            ))
        
        # Lint issues
        if health_score.get('lint_issues', 0) > 10:
            suggestions.append(Suggestion(
                action='cip verify --lint',
                reason=f'{health_score["lint_issues"]} lint issues detected',
                impact='Improve code quality and consistency',
                priority=Priority.MEDIUM,
                confidence=0.80,
                category='quality'
            ))
        
        return suggestions


class IndexAnalyzer(SuggestionAnalyzer):
    """Analyze index state and suggest maintenance actions."""
    
    def analyze(self, root: str, config: Dict[str, Any], context: Any = None) -> List[Suggestion]:
        """Analyze index state and generate suggestions."""
        suggestions = []
        index_status = self._get_index_status(root)
        
        # Stale index
        if index_status.get('stale', False):
            suggestions.append(Suggestion(
                action='cip sync',
                reason='Index is out of date',
                impact='Update search results and analysis accuracy',
                priority=Priority.MEDIUM,
                confidence=0.95,
                category='maintenance'
            ))
        
        # Missing embeddings
        if index_status.get('embedding_coverage', 100) < 80:
            suggestions.append(Suggestion(
                action='cip embed',
                reason=f'Only {index_status["embedding_coverage"]}% of chunks embedded',
                impact='Improve semantic search quality',
                priority=Priority.MEDIUM,
                confidence=0.85,
                category='maintenance'
            ))
        
        # Large database size
        if index_status.get('db_size_mb', 0) > 500:
            suggestions.append(Suggestion(
                action='cip vacuum --days 30',
                reason=f'Database size: {index_status["db_size_mb"]}MB',
                impact='Reduce database size and improve performance',
                priority=Priority.LOW,
                confidence=0.75,
                category='maintenance'
            ))
        
        return suggestions
    
    def _get_index_status(self, root: str) -> Dict[str, Any]:
        """Get current index status."""
        try:
            from cipkg.store import connect
            from cipkg.base import data_dir
            import time
            
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
        except Exception:
            return {
                'total_chunks': 0,
                'embedded_chunks': 0,
                'embedding_coverage': 100,
                'stale': False,
                'db_size_mb': 0
            }


class GitAnalyzer(SuggestionAnalyzer):
    """Analyze git state and suggest context-aware actions."""
    
    def analyze(self, root: str, config: Dict[str, Any], context: Any = None) -> List[Suggestion]:
        """Analyze git state and generate suggestions."""
        suggestions = []
        git_state = self._get_git_state(root)
        
        # Uncommitted changes
        if git_state.get('uncommitted_files', 0) > 0:
            suggestions.append(Suggestion(
                action='cip audit --diff',
                reason=f'{git_state["uncommitted_files"]} uncommitted files',
                impact='Review code quality before committing',
                priority=Priority.MEDIUM,
                confidence=0.85,
                category='git'
            ))
            
            # Suggest pre-commit workflow
            if git_state['uncommitted_files'] > 3:
                suggestions.append(Suggestion(
                    action='cip workflow pre-commit',
                    reason='Multiple files changed - comprehensive checks recommended',
                    impact='Run full pre-commit validation workflow',
                    priority=Priority.HIGH,
                    confidence=0.90,
                    category='workflow'
                ))
        
        # Branching suggestions
        if git_state.get('on_main', False) and git_state.get('uncommitted_files', 0) > 0:
            suggestions.append(Suggestion(
                action='git checkout -b feature/ descriptive-name',
                reason='Working directly on main branch',
                impact='Create feature branch for safer development',
                priority=Priority.LOW,
                confidence=0.70,
                category='git'
            ))
        
        # Stashed changes
        if git_state.get('stashed_count', 0) > 0:
            suggestions.append(Suggestion(
                action='git stash list',
                reason=f'{git_state["stashed_count"]} stashed changes',
                impact='Review and clean up stashed work',
                priority=Priority.LOW,
                confidence=0.65,
                category='git'
            ))
        
        return suggestions
    
    def _get_git_state(self, root: str) -> Dict[str, Any]:
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
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
                'branch': 'unknown',
                'on_main': False,
                'uncommitted_files': 0,
                'stashed_count': 0
            }


class StackAnalyzerFactory:
    """Factory to create appropriate stack analyzer based on repository type."""
    
    @staticmethod
    def create_analyzer(repo_type: str) -> SuggestionAnalyzer:
        """Create analyzer based on repository type."""
        if repo_type == 'nextjs-app':
            return NextJSAnalyzer()
        elif repo_type == 'python-lib':
            return PythonAnalyzer()
        else:
            return GenericStackAnalyzer()


class NextJSAnalyzer(SuggestionAnalyzer):
    """Next.js specific analyzer."""
    
    def analyze(self, root: str, config: Dict[str, Any], context: Any = None) -> List[Suggestion]:
        """Analyze Next.js repository and generate suggestions."""
        suggestions = []
        
        # Route analysis
        suggestions.append(Suggestion(
            action='cip routes',
            reason='Next.js project detected',
            impact='Analyze route structure and integrity',
            priority=Priority.MEDIUM,
            confidence=0.85,
            category='stack'
        ))
        
        # Check for Prisma
        if os.path.exists(os.path.join(root, 'prisma', 'schema.prisma')):
            suggestions.append(Suggestion(
                action='cip models',
                reason='Prisma ORM detected',
                impact='Analyze Prisma model usage and relationships',
                priority=Priority.MEDIUM,
                confidence=0.90,
                category='stack'
            ))
        
        return suggestions


class PythonAnalyzer(SuggestionAnalyzer):
    """Python specific analyzer."""
    
    def analyze(self, root: str, config: Dict[str, Any], context: Any = None) -> List[Suggestion]:
        """Analyze Python repository and generate suggestions."""
        suggestions = []
        
        # Type checking
        if os.path.exists(os.path.join(root, 'mypy.ini')) or os.path.exists(os.path.join(root, '.mypy.ini')):
            suggestions.append(Suggestion(
                action='cip verify --typecheck',
                reason='MyPy detected in project',
                impact='Run type checking with MyPy',
                priority=Priority.MEDIUM,
                confidence=0.85,
                category='stack'
            ))
        
        # Test coverage
        if os.path.exists(os.path.join(root, 'pytest.ini')) or os.path.exists(os.path.join(root, 'setup.cfg')):
            suggestions.append(Suggestion(
                action='cip coverage',
                reason='PyTest detected',
                impact='Analyze test coverage',
                priority=Priority.LOW,
                confidence=0.75,
                category='stack'
            ))
        
        return suggestions


class GenericStackAnalyzer(SuggestionAnalyzer):
    """Generic stack analyzer for unknown repository types."""
    
    def analyze(self, root: str, config: Dict[str, Any], context: Any = None) -> List[Suggestion]:
        """Analyze generic repository and generate suggestions."""
        suggestions = []
        
        # Generic suggestions
        suggestions.append(Suggestion(
            action='cip analyze',
            reason='General repository analysis recommended',
            impact='Get comprehensive repository health report',
            priority=Priority.MEDIUM,
            confidence=0.70,
            category='stack'
        ))
        
        return suggestions


class PatternAnalyzer(SuggestionAnalyzer):
    """Learn from user behavior and provide personalized suggestions."""
    
    def analyze(self, root: str, config: Dict[str, Any], context: Any = None) -> List[Suggestion]:
        """Analyze user patterns and generate personalized suggestions."""
        suggestions = []
        
        if context is None:
            return suggestions
        
        user_patterns = context.user.command_history if hasattr(context, 'user') else []
        
        # Time-based patterns
        current_hour = datetime.now().hour
        if user_patterns and len(user_patterns) > 0:
            time_patterns = self._analyze_time_patterns(user_patterns)
            if current_hour in time_patterns.get('peak_hours', []):
                common_workflow = time_patterns.get('peak_workflow')
                if common_workflow:
                    suggestions.append(Suggestion(
                        action=f'cip workflow {common_workflow}',
                        reason=f'Common workflow during this time',
                        impact='Streamline your regular workflow',
                        priority=Priority.LOW,
                        confidence=0.70,
                        category='personal'
                    ))
        
        # Command sequence patterns
        if len(user_patterns) >= 2:
            last_command = user_patterns[-1].get('command', '') if isinstance(user_patterns[-1], dict) else ''
            if 'audit' in last_command:
                suggestions.append(Suggestion(
                    action='cip findings',
                    reason='You just ran audit - check findings',
                    impact='Review audit findings',
                    priority=Priority.MEDIUM,
                    confidence=0.80,
                    category='personal'
                ))
            
            # Sync followed by audit pattern
            if len(user_patterns) >= 2:
                prev_command = user_patterns[-2].get('command', '') if isinstance(user_patterns[-2], dict) else ''
                if 'sync' in prev_command and 'audit' in last_command:
                    suggestions.append(Suggestion(
                        action='cip analyze',
                        reason='You synced and audited - check overall health',
                        impact='Get comprehensive repository health report',
                        priority=Priority.MEDIUM,
                        confidence=0.75,
                        category='personal'
                    ))
        
        # Error recovery patterns
        if context.user.error_recovery_patterns:
            recent_errors = self._get_recent_errors(root)
            if recent_errors:
                last_error = recent_errors[0]
                error_type = last_error.get('category', '')
                recovery = context.user.error_recovery_patterns.get(error_type)
                if recovery:
                    suggestions.append(Suggestion(
                        action=recovery,
                        reason=f'Common recovery for {error_type} errors',
                        impact='Try your usual recovery approach',
                        priority=Priority.HIGH,
                        confidence=0.75,
                        category='personal'
                    ))
        
        return suggestions
    
    def _analyze_time_patterns(self, command_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze time-based usage patterns."""
        if not command_history:
            return {'peak_hours': [9, 10, 14, 15], 'peak_workflow': 'pre-commit'}
        
        # Analyze command frequency by hour
        from collections import defaultdict
        hour_commands = defaultdict(list)
        
        for cmd in command_history:
            if isinstance(cmd, dict) and 'timestamp' in cmd:
                try:
                    timestamp = datetime.fromisoformat(cmd['timestamp'])
                    hour = timestamp.hour
                    command = cmd.get('command', '')
                    if command:
                        hour_commands[hour].append(command)
                except (ValueError, KeyError):
                    continue
        
        # Find peak hours
        hour_counts = {hour: len(commands) for hour, commands in hour_commands.items()}
        if hour_counts:
            sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
            peak_hours = [hour for hour, count in sorted_hours[:4]]
        else:
            peak_hours = [9, 10, 14, 15]
        
        # Find most common workflow during peak hours
        workflow_counts = defaultdict(int)
        for hour in peak_hours:
            for command in hour_commands.get(hour, []):
                if 'workflow' in command:
                    workflow_counts[command] += 1
        
        if workflow_counts:
            peak_workflow = max(workflow_counts.items(), key=lambda x: x[1])[0]
        else:
            peak_workflow = 'pre-commit'
        
        return {
            'peak_hours': peak_hours,
            'peak_workflow': peak_workflow.replace('cip workflow ', '') if 'cip workflow ' in peak_workflow else peak_workflow
        }
    
    def _get_recent_errors(self, root: str) -> List[Dict[str, Any]]:
        """Get recent errors from error logs."""
        try:
            from cipkg.error_system import ErrorLogger
            error_logger = ErrorLogger(root)
            return error_logger.get_recent_errors(limit=5)
        except Exception:
            return []


class RankingEngine:
    """Rank suggestions by multiple factors."""
    
    def rank(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """Score and sort suggestions."""
        scored = []
        
        for suggestion in suggestions:
            score = self._calculate_score(suggestion)
            suggestion.score = score
            scored.append((score, suggestion))
        
        # Sort by score (descending)
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [suggestion for _, suggestion in scored]
    
    def _calculate_score(self, suggestion: Suggestion) -> float:
        """Calculate composite score for suggestion."""
        weights = {
            'priority': 0.40,
            'confidence': 0.30,
            'relevance': 0.20,
            'freshness': 0.10
        }
        
        priority_score = self._priority_score(suggestion.priority)
        confidence_score = suggestion.confidence
        relevance_score = 0.75  # Placeholder - would be calculated from context
        freshness_score = 0.80  # Placeholder - would be calculated from recency
        
        total = (
            weights['priority'] * priority_score +
            weights['confidence'] * confidence_score +
            weights['relevance'] * relevance_score +
            weights['freshness'] * freshness_score
        )
        
        return total
    
    def _priority_score(self, priority: Priority) -> float:
        """Convert priority to numeric score."""
        priority_map = {
            Priority.CRITICAL: 1.0,
            Priority.HIGH: 0.85,
            Priority.MEDIUM: 0.70,
            Priority.LOW: 0.55
        }
        return priority_map.get(priority, 0.50)


class FilterEngine:
    """Filter suggestions based on relevance and quality."""
    
    def filter(self, suggestions: List[Suggestion], context: Any = None) -> List[Suggestion]:
        """Apply filtering rules."""
        filtered = suggestions
        
        # Remove duplicates
        filtered = self._remove_duplicates(filtered)
        
        # Limit by priority
        filtered = self._limit_by_priority(filtered)
        
        return filtered
    
    def _remove_duplicates(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """Remove duplicate suggestions."""
        seen = set()
        unique = []
        
        for suggestion in suggestions:
            key = (suggestion.action, suggestion.category)
            if key not in seen:
                seen.add(key)
                unique.append(suggestion)
        
        return unique
    
    def _limit_by_priority(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """Limit suggestions per priority level."""
        priority_limits = {
            Priority.CRITICAL: 5,
            Priority.HIGH: 5,
            Priority.MEDIUM: 3,
            Priority.LOW: 2
        }
        
        filtered = []
        counts = {p: 0 for p in priority_limits}
        
        for suggestion in suggestions:
            if counts[suggestion.priority] < priority_limits[suggestion.priority]:
                filtered.append(suggestion)
                counts[suggestion.priority] += 1
        
        return filtered


class SuggestionEngine:
    """Generate intelligent suggestions based on multiple factors."""
    
    def __init__(self, root: str, config: Dict[str, Any]):
        self.root = root
        self.config = config
        self.analyzers = [
            HealthAnalyzer(),
            IndexAnalyzer(),
            GitAnalyzer(),
        ]
        
        # Add stack analyzer based on repo type
        try:
            from repo_settings.detectors import detect_repo_type
            repo_type = detect_repo_type(root)
            self.analyzers.append(StackAnalyzerFactory.create_analyzer(repo_type))
        except ImportError:
            self.analyzers.append(GenericStackAnalyzer())
        
        # Add pattern analyzer
        self.analyzers.append(PatternAnalyzer())
        
        self.ranking_engine = RankingEngine()
        self.filter_engine = FilterEngine()
    
    def generate_suggestions(self, context: Any = None, max_suggestions: int = 5) -> List[Suggestion]:
        """Generate suggestions from all analyzers."""
        suggestions = []
        
        for analyzer in self.analyzers:
            try:
                analyzer_suggestions = analyzer.analyze(self.root, self.config, context)
                suggestions.extend(analyzer_suggestions)
            except Exception as e:
                # Log error but continue with other analyzers
                print(f"Warning: Analyzer {analyzer.__class__.__name__} failed: {e}")
        
        # Rank and filter suggestions
        ranked = self.ranking_engine.rank(suggestions)
        filtered = self.filter_engine.rank(ranked)
        
        return filtered[:max_suggestions]
