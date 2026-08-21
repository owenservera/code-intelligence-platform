# Learning System Design

## Overview

The Learning System is responsible for capturing user behavior patterns, analyzing them, and using the insights to provide increasingly personalized and relevant suggestions. It transforms CIP from a static tool into an adaptive assistant that learns from user interactions.

## Architecture

### Core Components

```
LearningSystem
├── PatternCollector (Data collection)
├── PatternStorage (Persistence layer)
├── PatternAnalyzer (Analysis engine)
├── PersonalizationEngine (Personalization logic)
├── FeedbackProcessor (User feedback handling)
└── ModelTrainer (ML model training)
```

## Data Model

### User Action Model

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

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
    user_rating: Optional[int] = None  # 1-5 scale
    user_feedback: Optional[str] = None
    
    # Metadata
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Pattern:
    """Discovered user pattern."""
    pattern_id: str
    pattern_type: str
    confidence: float  # 0.0 to 1.0
    frequency: int
    last_seen: datetime
    
    # Pattern details
    trigger_conditions: Dict[str, Any]
    action_sequence: List[str]
    expected_outcome: str
    
    # Performance
    success_rate: float
    avg_execution_time: float
    
    # Metadata
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
```

## Pattern Collector

```python
class PatternCollector:
    """Collect user action data for pattern analysis."""
    
    def __init__(self, storage: PatternStorage):
        self.storage = storage
        self.session_actions: List[UserAction] = []
    
    def record_command(self, user_id: str, repo_id: str, command: str, 
                       arguments: Dict[str, Any], context: Dict[str, Any],
                       success: bool, execution_time: float, error: str = None):
        """Record a command execution."""
        import uuid
        from datetime import datetime
        
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
        import uuid
        from datetime import datetime
        
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
        import uuid
        from datetime import datetime
        
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
        import uuid
        from datetime import datetime
        
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
```

## Pattern Storage

```python
class PatternStorage:
    """Persistent storage for user actions and patterns."""
    
    def __init__(self, root: str):
        self.root = root
        self.storage_dir = self._get_storage_dir()
        self._ensure_storage_structure()
    
    def _get_storage_dir(self) -> str:
        """Get storage directory path."""
        from cipkg.base import data_dir
        import os
        
        storage_dir = os.path.join(data_dir(self.root), "learning_data")
        os.makedirs(storage_dir, exist_ok=True)
        return storage_dir
    
    def _ensure_storage_structure(self):
        """Create necessary directory structure."""
        import os
        
        directories = [
            'actions',
            'patterns',
            'profiles',
            'models'
        ]
        
        for directory in directories:
            dir_path = os.path.join(self.storage_dir, directory)
            os.makedirs(dir_path, exist_ok=True)
    
    def store_action(self, action: UserAction):
        """Store a user action."""
        import json
        import os
        from datetime import datetime
        
        # Store in daily files for efficiency
        date_str = action.timestamp.strftime('%Y-%m-%d')
        file_path = os.path.join(self.storage_dir, 'actions', f"{date_str}.jsonl")
        
        with open(file_path, 'a') as f:
            f.write(json.dumps(self._action_to_dict(action)) + '\n')
    
    def store_pattern(self, pattern: Pattern):
        """Store a discovered pattern."""
        import json
        import os
        
        file_path = os.path.join(self.storage_dir, 'patterns', f"{pattern.pattern_id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(self._pattern_to_dict(pattern), f, indent=2, default=str)
    
    def store_profile(self, profile: UserProfile):
        """Store user profile."""
        import json
        import os
        
        file_path = os.path.join(self.storage_dir, 'profiles', f"{profile.user_id}.json")
        
        with open(file_path, 'w') as f:
            json.dump(self._profile_to_dict(profile), f, indent=2, default=str)
    
    def load_profile(self, user_id: str) -> Optional[UserProfile]:
        """Load user profile."""
        import json
        import os
        
        file_path = os.path.join(self.storage_dir, 'profiles', f"{user_id}.json")
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return self._dict_to_profile(data)
    
    def get_recent_actions(self, user_id: str, days: int = 7) -> List[UserAction]:
        """Get recent actions for a user."""
        import json
        import os
        from datetime import datetime, timedelta
        
        actions = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Load daily files within range
        for i in range(days):
            date_str = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            file_path = os.path.join(self.storage_dir, 'actions', f"{date_str}.jsonl")
            
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    for line in f:
                        action_data = json.loads(line)
                        if action_data['user_id'] == user_id:
                            action = self._dict_to_action(action_data)
                            if action.timestamp >= cutoff_date:
                                actions.append(action)
        
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
        from datetime import datetime
        
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
    
    def _pattern_to_dict(self, pattern: Pattern) -> Dict[str, Any]:
        """Convert pattern to dictionary."""
        return {
            'pattern_id': pattern.pattern_id,
            'pattern_type': pattern.pattern_type,
            'confidence': pattern.confidence,
            'frequency': pattern.frequency,
            'last_seen': pattern.last_seen.isoformat(),
            'trigger_conditions': pattern.trigger_conditions,
            'action_sequence': pattern.action_sequence,
            'expected_outcome': pattern.expected_outcome,
            'success_rate': pattern.success_rate,
            'avg_execution_time': pattern.avg_execution_time,
            'metadata': pattern.metadata
        }
    
    def _dict_to_pattern(self, data: Dict[str, Any]) -> Pattern:
        """Convert dictionary to pattern."""
        from datetime import datetime
        
        return Pattern(
            pattern_id=data['pattern_id'],
            pattern_type=data['pattern_type'],
            confidence=data['confidence'],
            frequency=data['frequency'],
            last_seen=datetime.fromisoformat(data['last_seen']),
            trigger_conditions=data['trigger_conditions'],
            action_sequence=data['action_sequence'],
            expected_outcome=data['expected_outcome'],
            success_rate=data['success_rate'],
            avg_execution_time=data['avg_execution_time'],
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
        from datetime import datetime
        
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
```

## Pattern Analyzer

```python
class PatternAnalyzer:
    """Analyze user actions to discover patterns."""
    
    def __init__(self, storage: PatternStorage):
        self.storage = storage
    
    def analyze_user_patterns(self, user_id: str) -> List[Pattern]:
        """Analyze patterns for a specific user."""
        actions = self.storage.get_recent_actions(user_id, days=30)
        
        patterns = []
        
        # Analyze command sequences
        patterns.extend(self._analyze_command_sequences(actions, user_id))
        
        # Analyze time-based patterns
        patterns.extend(self._analyze_time_patterns(actions, user_id))
        
        # Analyze error recovery patterns
        patterns.extend(self._analyze_error_recovery(actions, user_id))
        
        # Analyze suggestion preferences
        patterns.extend(self._analyze_suggestion_preferences(actions, user_id))
        
        return patterns
    
    def _analyze_command_sequences(self, actions: List[UserAction], user_id: str) -> List[Pattern]:
        """Analyze recurring command sequences."""
        from collections import defaultdict
        import uuid
        
        # Extract command sequences
        sequences = []
        current_sequence = []
        
        for action in sorted(actions, key=lambda a: a.timestamp):
            if action.action_type == ActionType.COMMAND_EXECUTED and action.command:
                current_sequence.append(action.command)
                if len(current_sequence) >= 2:
                    sequences.append(tuple(current_sequence[-3:]))  # Look at last 3 commands
            else:
                current_sequence = []
        
        # Find frequent sequences
        sequence_counts = defaultdict(int)
        for seq in sequences:
            sequence_counts[seq] += 1
        
        # Convert to patterns
        patterns = []
        for sequence, count in sequence_counts.items():
            if count >= 3:  # Minimum frequency threshold
                confidence = min(count / len(actions), 1.0)
                
                pattern = Pattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type="command_sequence",
                    confidence=confidence,
                    frequency=count,
                    last_seen=max(a.timestamp for a in actions if a.command in sequence),
                    trigger_conditions={
                        'previous_commands': list(sequence[:-1])
                    },
                    action_sequence=list(sequence),
                    expected_outcome=sequence[-1],
                    success_rate=self._calculate_sequence_success_rate(actions, sequence),
                    avg_execution_time=self._calculate_sequence_avg_time(actions, sequence),
                    metadata={'sequence_length': len(sequence)}
                )
                patterns.append(pattern)
        
        return patterns
    
    def _analyze_time_patterns(self, actions: List[UserAction], user_id: str) -> List[Pattern]:
        """Analyze time-based usage patterns."""
        from collections import defaultdict
        import uuid
        from datetime import datetime
        
        # Analyze by hour of day
        hour_activity = defaultdict(list)
        for action in actions:
            hour = action.timestamp.hour
            hour_activity[hour].append(action)
        
        patterns = []
        for hour, hour_actions in hour_activity.items():
            if len(hour_actions) >= 5:  # Minimum activity threshold
                # Find most common command during this hour
                command_counts = defaultdict(int)
                for action in hour_actions:
                    if action.command:
                        command_counts[action.command] += 1
                
                if command_counts:
                    top_command = max(command_counts.items(), key=lambda x: x[1])
                    confidence = top_command[1] / len(hour_actions)
                    
                    pattern = Pattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type="time_based",
                        confidence=confidence,
                        frequency=len(hour_actions),
                        last_seen=max(a.timestamp for a in hour_actions),
                        trigger_conditions={'hour': hour},
                        action_sequence=[top_command[0]],
                        expected_outcome=f"Execute {top_command[0]}",
                        success_rate=sum(1 for a in hour_actions if a.command == top_command[0] and a.success) / len([a for a in hour_actions if a.command == top_command[0]]),
                        avg_execution_time=sum(a.execution_time for a in hour_actions if a.command == top_command[0]) / len([a for a in hour_actions if a.command == top_command[0]]),
                        metadata={'hour': hour, 'command': top_command[0]}
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _analyze_error_recovery(self, actions: List[UserAction], user_id: str) -> List[Pattern]:
        """Analyze error recovery patterns."""
        import uuid
        
        # Find error-recovery pairs
        error_recovery_pairs = []
        
        for i, action in enumerate(actions):
            if action.action_type == ActionType.ERROR_OCCURRED:
                # Look for subsequent recovery action
                for next_action in actions[i+1:i+5]:  # Look at next 4 actions
                    if next_action.action_type == ActionType.ERROR_RECOVERED:
                        if action.context.get('error_type') == next_action.context.get('error_type'):
                            error_recovery_pairs.append((
                                action.context.get('error_type'),
                                next_action.context.get('recovery_action'),
                                next_action.success
                            ))
                            break
        
        # Find common recovery strategies
        from collections import defaultdict
        recovery_counts = defaultdict(lambda: {'count': 0, 'success': 0})
        
        for error_type, recovery, success in error_recovery_pairs:
            key = (error_type, recovery)
            recovery_counts[key]['count'] += 1
            if success:
                recovery_counts[key]['success'] += 1
        
        patterns = []
        for (error_type, recovery), stats in recovery_counts.items():
            if stats['count'] >= 2:  # Minimum occurrences
                confidence = stats['count'] / len(error_recovery_pairs)
                success_rate = stats['success'] / stats['count']
                
                pattern = Pattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type="error_recovery",
                    confidence=confidence,
                    frequency=stats['count'],
                    last_seen=max(a.timestamp for a in actions if a.context.get('error_type') == error_type),
                    trigger_conditions={'error_type': error_type},
                    action_sequence=[recovery],
                    expected_outcome="Error resolved",
                    success_rate=success_rate,
                    avg_execution_time=0.0,  # Not applicable for error recovery
                    metadata={'error_type': error_type, 'recovery_action': recovery}
                )
                patterns.append(pattern)
        
        return patterns
    
    def _analyze_suggestion_preferences(self, actions: List[UserAction], user_id: str) -> List[Pattern]:
        """Analyze suggestion acceptance patterns."""
        import uuid
        
        suggestion_actions = [a for a in actions if a.action_type in [ActionType.SUGGESTION_ACCEPTED, ActionType.SUGGESTION_REJECTED]]
        
        if not suggestion_actions:
            return []
        
        # Calculate acceptance rates by category
        from collections import defaultdict
        category_stats = defaultdict(lambda: {'accepted': 0, 'total': 0})
        
        for action in suggestion_actions:
            category = action.context.get('category', 'general')
            category_stats[category]['total'] += 1
            if action.action_type == ActionType.SUGGESTION_ACCEPTED:
                category_stats[category]['accepted'] += 1
        
        patterns = []
        for category, stats in category_stats.items():
            if stats['total'] >= 3:  # Minimum suggestions
                acceptance_rate = stats['accepted'] / stats['total']
                
                pattern = Pattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type="suggestion_preference",
                    confidence=acceptance_rate,
                    frequency=stats['total'],
                    last_seen=max(a.timestamp for a in suggestion_actions if a.context.get('category') == category),
                    trigger_conditions={'category': category},
                    action_sequence=[],
                    expected_outcome=f"Suggestion from {category} category",
                    success_rate=acceptance_rate,
                    avg_execution_time=0.0,
                    metadata={'category': category, 'acceptance_rate': acceptance_rate}
                )
                patterns.append(pattern)
        
        return patterns
    
    def _calculate_sequence_success_rate(self, actions: List[UserAction], sequence: tuple) -> float:
        """Calculate success rate for a command sequence."""
        sequence_actions = []
        current_sequence = []
        
        for action in sorted(actions, key=lambda a: a.timestamp):
            if action.action_type == ActionType.COMMAND_EXECUTED and action.command:
                current_sequence.append(action.command)
                if len(current_sequence) >= len(sequence):
                    if tuple(current_sequence[-len(sequence):]) == sequence:
                        sequence_actions.extend([action] * len(sequence))
                        current_sequence = []
            else:
                current_sequence = []
        
        if not sequence_actions:
            return 0.0
        
        return sum(1 for a in sequence_actions if a.success) / len(sequence_actions)
    
    def _calculate_sequence_avg_time(self, actions: List[UserAction], sequence: tuple) -> float:
        """Calculate average execution time for a command sequence."""
        sequence_times = []
        current_sequence = []
        
        for action in sorted(actions, key=lambda a: a.timestamp):
            if action.action_type == ActionType.COMMAND_EXECUTED and action.command:
                current_sequence.append((action.command, action.execution_time))
                if len(current_sequence) >= len(sequence):
                    if tuple(cmd for cmd, _ in current_sequence[-len(sequence):]) == sequence:
                        total_time = sum(time for _, time in current_sequence[-len(sequence):])
                        sequence_times.append(total_time)
                        current_sequence = []
            else:
                current_sequence = []
        
        if not sequence_times:
            return 0.0
        
        return sum(sequence_times) / len(sequence_times)
```

## Personalization Engine

```python
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
        
        # Error recovery suggestions
        if context.get('recent_error'):
            recovery_suggestions = self._generate_recovery_suggestions(patterns, context)
            suggestions.extend(recovery_suggestions)
        
        return self._rank_suggestions(suggestions, profile)
    
    def _generate_time_suggestions(self, patterns: List[Pattern], current_hour: int, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions based on time patterns."""
        time_patterns = [p for p in patterns if p.pattern_type == "time_based"]
        
        suggestions = []
        for pattern in time_patterns:
            if pattern.trigger_conditions.get('hour') == current_hour:
                if pattern.confidence > 0.5:  # Only suggest if confident
                    suggestions.append({
                        'action': pattern.action_sequence[0],
                        'reason': f"Common action during this time",
                        'confidence': pattern.confidence,
                        'source': 'time_pattern',
                        'pattern_id': pattern.pattern_id
                    })
        
        return suggestions
    
    def _generate_sequence_suggestions(self, patterns: List[Pattern], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions based on command sequences."""
        sequence_patterns = [p for p in patterns if p.pattern_type == "command_sequence"]
        
        suggestions = []
        recent_commands = context.get('recent_commands', [])
        
        for pattern in sequence_patterns:
            # Check if recent commands match trigger conditions
            trigger_commands = pattern.trigger_conditions.get('previous_commands', [])
            if len(recent_commands) >= len(trigger_commands):
                if recent_commands[-len(trigger_commands):] == trigger_commands:
                    if pattern.confidence > 0.6:  # Higher threshold for sequences
                        suggestions.append({
                            'action': pattern.action_sequence[-1],
                            'reason': f"Typical next command in your workflow",
                            'confidence': pattern.confidence,
                            'source': 'sequence_pattern',
                            'pattern_id': pattern.pattern_id
                        })
        
        return suggestions
    
    def _generate_preference_suggestions(self, profile: UserProfile, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate suggestions based on user preferences."""
        suggestions = []
        
        # Suggest preferred commands
        for command, preference_score in profile.preferred_commands.items():
            if preference_score > 0.7:  # High preference
                suggestions.append({
                    'action': command,
                    'reason': f"Command you frequently use",
                    'confidence': preference_score,
                    'source': 'user_preference',
                    'preference_score': preference_score
                })
        
        # Suggest preferred workflows
        for workflow, preference_score in profile.preferred_workflows.items():
            if preference_score > 0.7:
                suggestions.append({
                    'action': f'cip workflow {workflow}',
                    'reason': f"Workflow you frequently run",
                    'confidence': preference_score,
                    'source': 'workflow_preference',
                    'preference_score': preference_score
                })
        
        return suggestions
    
    def _generate_recovery_suggestions(self, patterns: List[Pattern], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate error recovery suggestions."""
        error_type = context.get('recent_error')
        recovery_patterns = [p for p in patterns if p.pattern_type == "error_recovery"]
        
        suggestions = []
        for pattern in recovery_patterns:
            if pattern.trigger_conditions.get('error_type') == error_type:
                if pattern.success_rate > 0.6:  # Only suggest if it works
                    suggestions.append({
                        'action': pattern.action_sequence[0],
                        'reason': f"Recovery action that worked before",
                        'confidence': pattern.success_rate,
                        'source': 'error_recovery',
                        'pattern_id': pattern.pattern_id
                    })
        
        return suggestions
    
    def _rank_suggestions(self, suggestions: List[Dict[str, Any]], profile: UserProfile) -> List[Dict[str, Any]]:
        """Rank suggestions by relevance and user preferences."""
        for suggestion in suggestions:
            # Calculate composite score
            base_confidence = suggestion.get('confidence', 0.5)
            
            # Boost based on category preference
            source = suggestion.get('source', 'general')
            category_preference = profile.category_preferences.get(source, 0.5)
            
            # Calculate final score
            suggestion['score'] = (base_confidence * 0.7) + (category_preference * 0.3)
        
        # Sort by score
        suggestions.sort(key=lambda s: s['score'], reverse=True)
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _create_default_profile(self, user_id: str) -> UserProfile:
        """Create default user profile."""
        from datetime import datetime
        
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
            # Exponential moving average
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
            total_suggestions = profile.total_actions  # Simplified
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
```

## Feedback Processor

```python
class FeedbackProcessor:
    """Process user feedback to improve learning system."""
    
    def __init__(self, storage: PatternStorage):
        self.storage = storage
    
    def process_suggestion_feedback(self, user_id: str, suggestion_id: str, 
                                   accepted: bool, rating: int = None, 
                                   feedback: str = None):
        """Process feedback on a suggestion."""
        # Record the feedback as an action
        collector = PatternCollector(self.storage)
        collector.record_suggestion_response(user_id, "", suggestion_id, accepted, rating, feedback)
        
        # Update pattern confidence based on feedback
        self._update_pattern_confidence(suggestion_id, accepted, rating)
    
    def process_workflow_feedback(self, user_id: str, workflow_id: str, 
                                  rating: int, feedback: str = None):
        """Process feedback on a workflow."""
        # This could be used to improve workflow recommendations
        # and identify workflow issues
        pass
    
    def _update_pattern_confidence(self, pattern_id: str, accepted: bool, rating: int):
        """Update pattern confidence based on feedback."""
        # Load pattern
        # Adjust confidence based on feedback
        # Store updated pattern
        pass
```

## Learning System Integration

```python
class LearningSystem:
    """Main learning system orchestrator."""
    
    def __init__(self, root: str):
        self.root = root
        self.storage = PatternStorage(root)
        self.collector = PatternCollector(self.storage)
        self.analyzer = PatternAnalyzer(self.storage)
        self.personalization = PersonalizationEngine(self.storage)
        self.feedback_processor = FeedbackProcessor(self.storage)
    
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
        elif action_type == 'suggestion_response':
            self.collector.record_suggestion_response(
                user_id=action_data['user_id'],
                repo_id=action_data['repo_id'],
                suggestion_id=action_data['suggestion_id'],
                accepted=action_data['accepted'],
                rating=action_data.get('rating'),
                feedback=action_data.get('feedback')
            )
    
    def get_personalized_suggestions(self, user_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get personalized suggestions for user."""
        return self.personalization.get_personalized_suggestions(user_id, context)
    
    def update_user_profile(self, user_id: str, action: UserAction):
        """Update user profile based on action."""
        self.personalization.update_profile(user_id, action)
    
    def analyze_patterns(self, user_id: str) -> List[Pattern]:
        """Analyze patterns for a user."""
        return self.analyzer.analyze_user_patterns(user_id)
```

## Configuration

### Learning System Configuration

```toml
[learning]
enabled = true
data_retention_days = 90
min_pattern_frequency = 3
confidence_threshold = 0.6

[learning.patterns]
command_sequences = true
time_patterns = true
error_recovery = true
suggestion_preferences = true

[learning.personalization]
max_suggestions = 5
min_confidence = 0.5
boost_factor = 1.2

[learning.feedback]
collect_ratings = true
collect_comments = true
feedback_influence = 0.3
```

## Privacy and Security

### Data Anonymization

```python
class DataAnonymizer:
    """Anonymize user data for privacy."""
    
    def anonymize_action(self, action: UserAction) -> UserAction:
        """Anonymize a user action."""
        # Replace user_id with hash
        import hashlib
        action.user_id = hashlib.sha256(action.user_id.encode()).hexdigest()
        
        # Remove sensitive context data
        sensitive_keys = ['api_key', 'token', 'password', 'secret']
        for key in sensitive_keys:
            action.context.pop(key, None)
        
        return action
```

### Data Retention

```python
class DataRetentionManager:
    """Manage data retention policies."""
    
    def __init__(self, storage: PatternStorage, retention_days: int = 90):
        self.storage = storage
        self.retention_days = retention_days
    
    def cleanup_old_data(self):
        """Remove data older than retention period."""
        import os
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        # Clean up old action files
        actions_dir = os.path.join(self.storage.storage_dir, 'actions')
        for filename in os.listdir(actions_dir):
            if filename.endswith('.jsonl'):
                date_str = filename.replace('.jsonl', '')
                try:
                    file_date = datetime.strptime(date_str, '%Y-%m-%d')
                    if file_date < cutoff_date:
                        os.remove(os.path.join(actions_dir, filename))
                except ValueError:
                    continue
```

## Testing Strategy

### Unit Tests

```python
def test_pattern_collector():
    """Test pattern collection."""
    storage = PatternStorage(test_root)
    collector = PatternCollector(storage)
    
    collector.record_command(
        user_id="test_user",
        repo_id="test_repo",
        command="cip audit",
        arguments={},
        context={},
        success=True,
        execution_time=1.5
    )
    
    summary = collector.get_session_summary()
    assert summary['total_actions'] == 1
    assert summary['most_used_command'] == "cip audit"

def test_pattern_analyzer():
    """Test pattern analysis."""
    storage = PatternStorage(test_root)
    analyzer = PatternAnalyzer(storage)
    
    # Create test actions
    actions = [
        UserAction(action_id="1", action_type=ActionType.COMMAND_EXECUTED, 
                  timestamp=datetime.now(), user_id="test", repo_id="test", 
                  command="cip sync", success=True),
        UserAction(action_id="2", action_type=ActionType.COMMAND_EXECUTED, 
                  timestamp=datetime.now(), user_id="test", repo_id="test", 
                  command="cip audit", success=True),
        UserAction(action_id="3", action_type=ActionType.COMMAND_EXECUTED, 
                  timestamp=datetime.now(), user_id="test", repo_id="test", 
                  command="cip audit", success=True)
    ]
    
    patterns = analyzer._analyze_command_sequences(actions, "test")
    assert len(patterns) > 0
```

## Future Enhancements

### Machine Learning Integration

```python
class MLPatternLearner:
    """Use machine learning for pattern discovery."""
    
    def __init__(self):
        self.model = None
    
    def train_model(self, actions: List[UserAction]):
        """Train ML model on user actions."""
        # Convert actions to features
        # Train model
        # Save model
        pass
    
    def predict_next_action(self, context: Dict[str, Any]) -> str:
        """Predict next action based on context."""
        # Use trained model to predict
        pass
```

### Collaborative Filtering

```python
class CollaborativeFilter:
    """Learn from team patterns."""
    
    def get_team_patterns(self, team_id: str) -> List[Pattern]:
        """Get patterns from team members."""
        # Aggregate patterns from team
        # Find successful team workflows
        pass
```

## Conclusion

The Learning System provides a comprehensive framework for understanding user behavior and delivering personalized experiences. By collecting detailed action data, analyzing patterns, and continuously updating user profiles, it enables CIP CLI v2.0 to become increasingly helpful and tailored to individual users' needs and preferences.

The system is designed with privacy in mind, offering data anonymization and configurable retention policies. The modular architecture allows for easy extension with more sophisticated machine learning approaches while maintaining the core pattern-based functionality.
