"""
Learning System for CIP CLI v2.0

This module provides pattern collection, analysis, and personalization
to learn from user behavior and improve suggestions over time.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import os
import json
import uuid


class ActionType(Enum):
    """Types of user actions."""
    COMMAND_EXECUTED = "command_executed"
    SUGGESTION_ACCEPTED = "suggestion_accepted"
    SUGGESTION_REJECTED = "suggestion_rejected"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    ERROR_OCCURRED = "error_occurred"
    ERROR_RECOVERED = "error_recovered"


@dataclass
class UserAction:
    """Record of a single user action."""
    action_id: str
    action_type: ActionType
    timestamp: datetime
    user_id: str
    repo_id: str
    
    # Action details
    command: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Outcome
    success: bool = True
    execution_time: float = 0.0
    error_message: Optional[str] = None
    
    # Feedback
    user_rating: Optional[int] = None
    user_feedback: Optional[str] = None
    
    # Metadata
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserProfile:
    """User profile and preferences."""
    user_id: str
    created_at: datetime
    last_updated: datetime
    
    # Preferences
    preferred_commands: Dict[str, float] = field(default_factory=dict)
    preferred_workflows: Dict[str, float] = field(default_factory=dict)
    time_preferences: Dict[str, List[int]] = field(default_factory=dict)
    
    # Skill level
    expertise_areas: Dict[str, str] = field(default_factory=dict)
    learning_progress: Dict[str, float] = field(default_factory=dict)
    
    # Behavior patterns
    common_sequences: List[List[str]] = field(default_factory=list)
    error_recovery_strategies: Dict[str, str] = field(default_factory=dict)
    
    # Suggestion preferences
    suggestion_acceptance_rate: float = 0.0
    category_preferences: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    total_actions: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class PatternStorage:
    """Persistent storage for user actions and patterns."""
    
    def __init__(self, root: str):
        self.root = root
        self.storage_dir = self._get_storage_dir()
        self._ensure_storage_structure()
    
    def _get_storage_dir(self) -> str:
        """Get storage directory path."""
        from cipkg.base import data_dir
        
        storage_dir = os.path.join(data_dir(self.root), "learning_data")
        os.makedirs(storage_dir, exist_ok=True)
        return storage_dir
    
    def _ensure_storage_structure(self):
        """Create necessary directory structure."""
        directories = ['actions', 'patterns', 'profiles', 'models']
        for directory in directories:
            dir_path = os.path.join(self.storage_dir, directory)
            os.makedirs(dir_path, exist_ok=True)
    
    def store_action(self, action: UserAction):
        """Store a user action."""
        date_str = action.timestamp.strftime('%Y-%m-%d')
        file_path = os.path.join(self.storage_dir, 'actions', f"{date_str}.jsonl")
        
        with open(file_path, 'a') as f:
            f.write(json.dumps(self._action_to_dict(action)) + '\n')
    
    def store_profile(self, profile: UserProfile):
        """Store user profile."""
        file_path = os.path.join(self.storage_dir, 'profiles', f"{profile.user_id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(self._profile_to_dict(profile), f, indent=2, default=str)
    
    def load_profile(self, user_id: str) -> Optional[UserProfile]:
        """Load user profile."""
        file_path = os.path.join(self.storage_dir, 'profiles', f"{user_id}.json")
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return self._dict_to_profile(data)
    
    def get_recent_actions(self, user_id: str, days: int = 7) -> List[UserAction]:
        """Get recent actions for a user."""
        import datetime as dt
        
        actions = []
        cutoff_date = dt.datetime.now() - dt.timedelta(days=days)
        
        for i in range(days):
            date_str = (dt.datetime.now() - dt.timedelta(days=i)).strftime('%Y-%m-%d')
            file_path = os.path.join(self.storage_dir, 'actions', f"{date_str}.jsonl")
            
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    for line in f:
                        try:
                            action_data = json.loads(line)
                            if action_data['user_id'] == user_id:
                                action = self._dict_to_action(action_data)
                                if action.timestamp >= cutoff_date:
                                    actions.append(action)
                        except json.JSONDecodeError:
                            continue
        
        return actions
    
    def _action_to_dict(self, action: UserAction) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            'action_id': action.action_id,
            'action_type': action.action_type.value,
            'timestamp': action.timestamp.isoformat(),
            'user_id': action.user_id,
            'repo_id': action.repo_id,
            'command': action.command,
            'arguments': action.arguments,
            'context': action.context,
            'success': action.success,
            'execution_time': action.execution_time,
            'error_message': action.error_message,
            'user_rating': action.user_rating,
            'user_feedback': action.user_feedback,
            'session_id': action.session_id,
            'metadata': action.metadata
        }
    
    def _dict_to_action(self, data: Dict[str, Any]) -> UserAction:
        """Convert dictionary to action."""
        return UserAction(
            action_id=data['action_id'],
            action_type=ActionType(data['action_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            user_id=data['user_id'],
            repo_id=data['repo_id'],
            command=data.get('command'),
            arguments=data.get('arguments', {}),
            context=data.get('context', {}),
            success=data['success'],
            execution_time=data.get('execution_time', 0.0),
            error_message=data.get('error_message'),
            user_rating=data.get('user_rating'),
            user_feedback=data.get('user_feedback'),
            session_id=data.get('session_id'),
            metadata=data.get('metadata', {})
        )
    
    def _profile_to_dict(self, profile: UserProfile) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            'user_id': profile.user_id,
            'created_at': profile.created_at.isoformat(),
            'last_updated': profile.last_updated.isoformat(),
            'preferred_commands': profile.preferred_commands,
            'preferred_workflows': profile.preferred_workflows,
            'time_preferences': profile.time_preferences,
            'expertise_areas': profile.expertise_areas,
            'learning_progress': profile.learning_progress,
            'common_sequences': profile.common_sequences,
            'error_recovery_strategies': profile.error_recovery_strategies,
            'suggestion_acceptance_rate': profile.suggestion_acceptance_rate,
            'category_preferences': profile.category_preferences,
            'total_actions': profile.total_actions,
            'metadata': profile.metadata
        }
    
    def _dict_to_profile(self, data: Dict[str, Any]) -> UserProfile:
        """Convert dictionary to profile."""
        return UserProfile(
            user_id=data['user_id'],
            created_at=datetime.fromisoformat(data['created_at']),
            last_updated=datetime.fromisoformat(data['last_updated']),
            preferred_commands=data.get('preferred_commands', {}),
            preferred_workflows=data.get('preferred_workflows', {}),
            time_preferences=data.get('time_preferences', {}),
            expertise_areas=data.get('expertise_areas', {}),
            learning_progress=data.get('learning_progress', {}),
            common_sequences=data.get('common_sequences', []),
            error_recovery_strategies=data.get('error_recovery_strategies', {}),
            suggestion_acceptance_rate=data.get('suggestion_acceptance_rate', 0.0),
            category_preferences=data.get('category_preferences', {}),
            total_actions=data.get('total_actions', 0),
            metadata=data.get('metadata', {})
        )


class PatternCollector:
    """Collect user action data for pattern analysis."""
    
    def __init__(self, storage: PatternStorage):
        self.storage = storage
        self.session_actions: List[UserAction] = []
    
    def record_command(self, user_id: str, repo_id: str, command: str,
                       arguments: Dict[str, Any], context: Dict[str, Any],
                       success: bool, execution_time: float, error: str = None):
        """Record a command execution."""
        action = UserAction(
            action_id=str(uuid.uuid4()),
            action_type=ActionType.COMMAND_EXECUTED,
            timestamp=datetime.now(),
            user_id=user_id,
            repo_id=repo_id,
            command=command,
            arguments=arguments,
            context=context,
            success=success,
            execution_time=execution_time,
            error_message=error
        )
        
        self._add_action(action)
    
    def record_suggestion_response(self, user_id: str, repo_id: str,
                                  suggestion_id: str, accepted: bool,
                                  rating: int = None, feedback: str = None):
        """Record user response to a suggestion."""
        action = UserAction(
            action_id=str(uuid.uuid4()),
            action_type=ActionType.SUGGESTION_ACCEPTED if accepted else ActionType.SUGGESTION_REJECTED,
            timestamp=datetime.now(),
            user_id=user_id,
            repo_id=repo_id,
            context={'suggestion_id': suggestion_id},
            success=accepted,
            user_rating=rating,
            user_feedback=feedback
        )
        
        self._add_action(action)
    
    def record_workflow_event(self, user_id: str, repo_id: str,
                              workflow_id: str, event_type: str,
                              success: bool = True, error: str = None):
        """Record workflow lifecycle events."""
        action_type_map = {
            'started': ActionType.WORKFLOW_STARTED,
            'completed': ActionType.WORKFLOW_COMPLETED,
            'failed': ActionType.WORKFLOW_FAILED
        }
        
        action = UserAction(
            action_id=str(uuid.uuid4()),
            action_type=action_type_map.get(event_type, ActionType.WORKFLOW_STARTED),
            timestamp=datetime.now(),
            user_id=user_id,
            repo_id=repo_id,
            context={'workflow_id': workflow_id},
            success=success,
            error_message=error
        )
        
        self._add_action(action)
    
    def record_error_recovery(self, user_id: str, repo_id: str,
                             error_type: str, recovery_action: str,
                             success: bool):
        """Record error recovery attempts."""
        action = UserAction(
            action_id=str(uuid.uuid4()),
            action_type=ActionType.ERROR_RECOVERED if success else ActionType.ERROR_OCCURRED,
            timestamp=datetime.now(),
            user_id=user_id,
            repo_id=repo_id,
            context={'error_type': error_type, 'recovery_action': recovery_action},
            success=success
        )
        
        self._add_action(action)
    
    def _add_action(self, action: UserAction):
        """Add action to storage and session buffer."""
        self.storage.store_action(action)
        self.session_actions.append(action)
        
        # Keep session buffer manageable
        if len(self.session_actions) > 1000:
            self.session_actions = self.session_actions[-1000:]
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session actions."""
        if not self.session_actions:
            return {}
        
        from collections import Counter
        
        command_counts = Counter(a.command for a in self.session_actions if a.command)
        success_rate = sum(1 for a in self.session_actions if a.success) / len(self.session_actions)
        
        return {
            'total_actions': len(self.session_actions),
            'command_distribution': dict(command_counts.most_common(10)),
            'success_rate': success_rate,
            'most_used_command': command_counts.most_common(1)[0][0] if command_counts else None
        }


class PatternAnalyzer:
    """Analyze user actions to discover patterns."""
    
    def __init__(self, storage: PatternStorage):
        self.storage = storage
    
    def analyze_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analyze patterns for a specific user."""
        actions = self.storage.get_recent_actions(user_id, days=30)
        
        # Analyze command sequences
        command_sequences = self._analyze_command_sequences(actions)
        
        # Analyze time-based patterns
        time_patterns = self._analyze_time_patterns(actions)
        
        # Analyze error recovery patterns
        error_recovery = self._analyze_error_recovery(actions)
        
        # Analyze suggestion preferences
        suggestion_preferences = self._analyze_suggestion_preferences(actions)
        
        return {
            'command_sequences': command_sequences,
            'time_patterns': time_patterns,
            'error_recovery': error_recovery,
            'suggestion_preferences': suggestion_preferences
        }
    
    def _analyze_command_sequences(self, actions: List[UserAction]) -> List[Dict[str, Any]]:
        """Analyze recurring command sequences."""
        from collections import defaultdict
        
        # Extract adjacent command pairs
        command_pairs = defaultdict(int)
        command_triples = defaultdict(int)
        
        for i in range(len(actions) - 1):
            if actions[i].command and actions[i + 1].command:
                pair = (actions[i].command, actions[i + 1].command)
                command_pairs[pair] += 1
        
        for i in range(len(actions) - 2):
            if actions[i].command and actions[i + 1].command and actions[i + 2].command:
                triple = (actions[i].command, actions[i + 1].command, actions[i + 2].command)
                command_triples[triple] += 1
        
        # Find frequent sequences
        frequent_pairs = [(pair, count) for pair, count in command_pairs.items() if count >= 2]
        frequent_triples = [(triple, count) for triple, count in command_triples.items() if count >= 2]
        
        return {
            'frequent_pairs': [{'sequence': list(pair), 'count': count} for pair, count in frequent_pairs],
            'frequent_triples': [{'sequence': list(triple), 'count': count} for triple, count in frequent_triples]
        }
    
    def _analyze_time_patterns(self, actions: List[UserAction]) -> Dict[str, Any]:
        """Analyze time-based usage patterns."""
        from collections import defaultdict
        
        hour_activity = defaultdict(list)
        day_activity = defaultdict(list)
        
        for action in actions:
            hour = action.timestamp.hour
            day = action.timestamp.strftime('%A')
            
            if action.command:
                hour_activity[hour].append(action.command)
                day_activity[day].append(action.command)
        
        # Find peak hours and days
        hour_counts = {hour: len(cmds) for hour, cmds in hour_activity.items()}
        day_counts = {day: len(cmds) for day, cmds in day_activity.items()}
        
        peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            'peak_hours': [hour for hour, count in peak_hours],
            'peak_days': [day for day, count in peak_days],
            'hour_activity': dict(hour_counts),
            'day_activity': dict(day_counts)
        }
    
    def _analyze_error_recovery(self, actions: List[UserAction]) -> Dict[str, str]:
        """Analyze error recovery patterns."""
        from collections import defaultdict
        
        recovery_map = defaultdict(lambda: {'count': 0, 'success': 0})
        
        for i, action in enumerate(actions):
            if action.action_type == ActionType.ERROR_OCCURRED:
                # Look for subsequent recovery action
                for next_action in actions[i+1:i+5]:
                    if next_action.action_type == ActionType.ERROR_RECOVERED:
                        error_type = action.context.get('error_type', 'unknown')
                        recovery = next_action.context.get('recovery_action', 'unknown')
                        
                        if action.context.get('error_type') == next_action.context.get('error_type'):
                            key = (error_type, recovery)
                            recovery_map[key]['count'] += 1
                            if next_action.success:
                                recovery_map[key]['success'] += 1
                        break
        
        # Get most successful recovery for each error type
        best_recoveries = {}
        for (error_type, recovery), stats in recovery_map.items():
            if stats['count'] >= 2:
                success_rate = stats['success'] / stats['count']
                if error_type not in best_recoveries or success_rate > best_recoveries[error_type]['success_rate']:
                    best_recoveries[error_type] = {
                        'recovery': recovery,
                        'success_rate': success_rate,
                        'count': stats['count']
                    }
        
        return {error_type: data['recovery'] for error_type, data in best_recoveries.items()}
    
    def _analyze_suggestion_preferences(self, actions: List[UserAction]) -> Dict[str, float]:
        """Analyze suggestion acceptance patterns."""
        from collections import defaultdict
        
        category_stats = defaultdict(lambda: {'accepted': 0, 'total': 0})
        
        for action in actions:
            if action.action_type in [ActionType.SUGGESTION_ACCEPTED, ActionType.SUGGESTION_REJECTED]:
                category = action.context.get('category', 'general')
                category_stats[category]['total'] += 1
                if action.action_type == ActionType.SUGGESTION_ACCEPTED:
                    category_stats[category]['accepted'] += 1
        
        acceptance_rates = {}
        for category, stats in category_stats.items():
            if stats['total'] >= 3:
                acceptance_rates[category] = stats['accepted'] / stats['total']
        
        return acceptance_rates


class PersonalizationEngine:
    """Generate personalized suggestions based on user patterns."""
    
    def __init__(self, storage: PatternStorage):
        self.storage = storage
        self.analyzer = PatternAnalyzer(storage)
    
    def get_personalized_suggestions(self, user_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get personalized suggestions based on user patterns and current context."""
        profile = self.storage.load_profile(user_id)
        if not profile:
            profile = self._create_default_profile(user_id)
        
        patterns = self.analyzer.analyze_user_patterns(user_id)
        
        suggestions = []
        
        # Time-based suggestions
        current_hour = datetime.now().hour
        time_suggestions = self._generate_time_suggestions(patterns, current_hour, context)
        suggestions.extend(time_suggestions)
        
        # Sequence-based suggestions
        sequence_suggestions = self._generate_sequence_suggestions(patterns, context)
        suggestions.extend(sequence_suggestions)
        
        # Preference-based suggestions
        preference_suggestions = self._generate_preference_suggestions(profile, context)
        suggestions.extend(preference_suggestions)
        
        return self._rank_suggestions(suggestions, profile)
    
    def _generate_time_suggestions(self, patterns: Dict[str, Any], current_hour: int, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions based on time patterns."""
        time_patterns = patterns.get('time_patterns', {})
        peak_hours = time_patterns.get('peak_hours', [])
        
        suggestions = []
        if current_hour in peak_hours:
            # Suggest common workflows during peak hours
            common_workflow = self._get_common_workflow_for_hour(patterns, current_hour)
            if common_workflow:
                suggestions.append({
                    'action': f'cip workflow {common_workflow}',
                    'reason': f'Common workflow during this time',
                    'confidence': 0.70,
                    'source': 'time_pattern'
                })
        
        return suggestions
    
    def _get_common_workflow_for_hour(self, patterns: Dict[str, Any], hour: int) -> str:
        """Get common workflow for specific hour."""
        # Simplified - would analyze actual patterns
        return 'pre-commit'
    
    def _generate_sequence_suggestions(self, patterns: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions based on command sequences."""
        command_sequences = patterns.get('command_sequences', {})
        recent_commands = context.get('recent_commands', [])
        
        suggestions = []
        if len(recent_commands) >= 1:
            last_command = recent_commands[-1]
            
            # Check for frequent pairs
            for pair_data in command_sequences.get('frequent_pairs', []):
                sequence = pair_data['sequence']
                if sequence[0] == last_command:
                    suggestions.append({
                        'action': sequence[1],
                        'reason': f'Typical next command after {last_command}',
                        'confidence': 0.75,
                        'source': 'sequence_pattern'
                    })
        
        return suggestions
    
    def _generate_preference_suggestions(self, profile: UserProfile, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions based on user preferences."""
        suggestions = []
        
        # Suggest preferred commands
        for command, preference_score in profile.preferred_commands.items():
            if preference_score > 0.7:
                suggestions.append({
                    'action': command,
                    'reason': f'Command you frequently use',
                    'confidence': preference_score,
                    'source': 'user_preference'
                })
        
        # Suggest preferred workflows
        for workflow, preference_score in profile.preferred_workflows.items():
            if preference_score > 0.7:
                suggestions.append({
                    'action': f'cip workflow {workflow}',
                    'reason': f"Workflow you frequently run",
                    'confidence': preference_score,
                    'source': 'workflow_preference'
                })
        
        return suggestions
    
    def _rank_suggestions(self, suggestions: List[Dict[str, Any]], profile: UserProfile) -> List[Dict[str, Any]]:
        """Rank suggestions by relevance and user preferences."""
        for suggestion in suggestions:
            base_confidence = suggestion.get('confidence', 0.5)
            
            # Boost based on category preference
            source = suggestion.get('source', 'general')
            category_preference = profile.category_preferences.get(source, 0.5)
            
            # Calculate final score
            suggestion['score'] = (base_confidence * 0.7) + (category_preference * 0.3)
        
        # Sort by score
        suggestions.sort(key=lambda s: s['score'], reverse=True)
        
        return suggestions[:5]
    
    def _create_default_profile(self, user_id: str) -> UserProfile:
        """Create default user profile."""
        return UserProfile(
            user_id=user_id,
            created_at=datetime.now(),
            last_updated=datetime.now(),
            preferred_commands={},
            preferred_workflows={},
            time_preferences={},
            expertise_areas={},
            learning_progress={},
            common_sequences=[],
            error_recovery_strategies={},
            suggestion_acceptance_rate=0.0,
            category_preferences={},
            total_actions=0
        )
    
    def update_profile(self, user_id: str, action: UserAction):
        """Update user profile based on new action."""
        profile = self.storage.load_profile(user_id)
        if not profile:
            profile = self._create_default_profile(user_id)
        
        # Update total actions
        profile.total_actions += 1
        profile.last_updated = datetime.now()
        
        # Update command preferences
        if action.command:
            current_pref = profile.preferred_commands.get(action.command, 0.5)
            new_pref = (current_pref * 0.9) + (1.0 if action.success else 0.0) * 0.1
            profile.preferred_commands[action.command] = new_pref
        
        # Update workflow preferences
        if action.context.get('workflow_id'):
            workflow_id = action.context['workflow_id']
            current_pref = profile.preferred_workflows.get(workflow_id, 0.5)
            new_pref = (current_pref * 0.9) + (1.0 if action.success else 0.0) * 0.1
            profile.preferred_workflows[workflow_id] = new_pref
        
        # Update suggestion acceptance rate
        if action.action_type in [ActionType.SUGGESTION_ACCEPTED, ActionType.SUGGESTION_REJECTED]:
            total_suggestions = profile.total_actions
            accepted = 1 if action.action_type == ActionType.SUGGESTION_ACCEPTED else 0
            profile.suggestion_acceptance_rate = (
                (profile.suggestion_acceptance_rate * (total_suggestions - 1) + accepted) / total_suggestions
            )
        
        # Update category preferences
        if action.action_type in [ActionType.SUGGESTION_ACCEPTED, ActionType.SUGGESTION_REJECTED]:
            category = action.context.get('category', 'general')
            current_pref = profile.category_preferences.get(category, 0.5)
            new_pref = (current_pref * 0.9) + (1.0 if action.action_type == ActionType.SUGGESTION_ACCEPTED else 0.0) * 0.1
            profile.category_preferences[category] = new_pref
        
        # Store updated profile
        self.storage.store_profile(profile)


class LearningSystem:
    """Main learning system orchestrator."""
    
    def __init__(self, root: str):
        self.root = root
        self.storage = PatternStorage(root)
        self.collector = PatternCollector(self.storage)
        self.analyzer = PatternAnalyzer(self.storage)
        self.personalization = PersonalizationEngine(self.storage)
        
        # Memory integration
        self._memory = None
        self._episodic = None
    
    @property
    def memory(self):
        """Lazy-load memory subsystem."""
        if self._memory is None:
            try:
                from .memory.temporal_graph import AgentMemory
                memory_dir = os.path.join(self.storage.storage_dir, 'memory.db')
                self._memory = AgentMemory(memory_dir)
            except Exception:
                self._memory = None
        return self._memory
    
    @property
    def episodic(self):
        """Lazy-load episodic memory."""
        if self._episodic is None:
            try:
                from .memory.episodic import AgentExperienceLogger
                episodic_dir = os.path.join(self.storage.storage_dir, 'episodes.db')
                self._episodic = AgentExperienceLogger(episodic_dir)
            except Exception:
                self._episodic = None
        return self._episodic
    
    def record_action(self, action_data: Dict[str, Any]):
        """Record a user action."""
        action_type = action_data.get('action_type')
        
        if action_type == 'command':
            self.collector.record_command(
                user_id=action_data['user_id'],
                repo_id=action_data['repo_id'],
                command=action_data['command'],
                arguments=action_data.get('arguments', {}),
                context=action_data.get('context', {}),
                success=action_data.get('success', True),
                execution_time=action_data.get('execution_time', 0.0),
                error=action_data.get('error')
            )
            
            # Log to episodic memory
            if self.episodic:
                try:
                    self.episodic.log_interaction(
                        query=action_data.get('command', ''),
                        result=action_data.get('context', {}),
                        success=action_data.get('success', True)
                    )
                except Exception:
                    pass
            
            # Store in semantic memory
            if self.memory:
                try:
                    self.memory.remember(
                        key=f"command:{action_data.get('command', '')}",
                        value={
                            'command': action_data.get('command'),
                            'success': action_data.get('success', True),
                            'timestamp': datetime.now().isoformat()
                        },
                        source="learning_system"
                    )
                except Exception:
                    pass
        
        elif action_type == 'suggestion_response':
            self.collector.record_suggestion_response(
                user_id=action_data['user_id'],
                repo_id=action_data['repo_id'],
                suggestion_id=action_data['suggestion_id'],
                accepted=action_data['accepted'],
                rating=action_data.get('rating'),
                feedback=action_data.get('feedback')
            )
            
            # Store preference in memory
            if self.memory:
                try:
                    self.memory.learn_preference(
                        preference=f"suggestion:{action_data.get('suggestion_id', '')}",
                        value=action_data.get('accepted', False)
                    )
                except Exception:
                    pass
    
    def get_personalized_suggestions(self, user_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get personalized suggestions for user."""
        return self.personalization.get_personalized_suggestions(user_id, context)
    
    def update_user_profile(self, user_id: str, action: UserAction):
        """Update user profile based on action."""
        self.personalization.update_profile(user_id, action)
    
    def analyze_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analyze patterns for a user."""
        return self.analyzer.analyze_user_patterns(user_id)
    
    def recall_relevant(self, query: str) -> List[Dict[str, Any]]:
        """Recall relevant past experiences for a query.
        
        Args:
            query: Query to find relevant experiences for
        
        Returns:
            List of relevant experiences sorted by relevance
        """
        results = []
        
        # Recall from episodic memory
        if self.episodic:
            try:
                episodes = self.episodic.recall_similar(query)
                for episode in episodes:
                    results.append({
                        'type': 'episode',
                        'content': episode.context,
                        'timestamp': episode.timestamp,
                        'outcome': episode.outcome
                    })
            except Exception:
                pass
        
        # Recall from semantic memory
        if self.memory:
            try:
                memories = self.memory.graph.query_facts(
                    subject="agent",
                    predicate=f"command:{query[:50]}"
                )
                for memory in memories:
                    results.append({
                        'type': 'memory',
                        'content': memory.object_value,
                        'timestamp': memory.valid_from
                    })
            except Exception:
                pass
        
        # Sort by recency
        results.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        return results[:10]


def record_user_action(root: str, action_type: str, **kwargs):
    """Convenience function to record user actions."""
    learning_system = LearningSystem(root)
    
    action_data = {'action_type': action_type, **kwargs}
    
    # Add default user_id if not provided
    if 'user_id' not in action_data:
        action_data['user_id'] = 'default'
    
    # Add default repo_id if not provided
    if 'repo_id' not in action_data:
        action_data['repo_id'] = os.path.basename(root)
    
    learning_system.record_action(action_data)


def get_personalized_suggestions(root: str, user_id: str = 'default', context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Convenience function to get personalized suggestions."""
    if context is None:
        context = {}
    
    learning_system = LearningSystem(root)
    return learning_system.get_personalized_suggestions(user_id, context)
