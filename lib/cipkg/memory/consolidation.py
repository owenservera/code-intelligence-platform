"""
Memory Consolidation - Background process to promote patterns to long-term memory.
Inspired by human sleep cycles for memory consolidation.
"""
import json
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta
from .temporal_graph import TemporalKnowledgeGraph, TemporalFact
from .episodic import EpisodicMemory

class MemoryConsolidator:
    """Consolidate episodic memories into semantic knowledge."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.graph = TemporalKnowledgeGraph(db_path)
        self.episodic = EpisodicMemory(db_path)
    
    def consolidate(self, lookback_days: int = 7):
        """Run consolidation process."""
        since = time.time() - (lookback_days * 24 * 60 * 60)
        
        # Get recent episodes
        episodes = self.episodic.query_episodes(since=since, limit=1000)
        
        if not episodes:
            return
        
        # Analyze patterns
        patterns = self._extract_patterns(episodes)
        
        # Promote strong patterns to semantic memory
        for pattern in patterns:
            if pattern['confidence'] > 0.7:
                self._promote_to_semantic(pattern)
    
    def _extract_patterns(self, episodes: List) -> List[Dict[str, Any]]:
        """Extract recurring patterns from episodes."""
        patterns = []
        
        # Count episode types frequencies
        type_counts = {}
        for ep in episodes:
            type_counts[ep.episode_type] = type_counts.get(ep.episode_type, 0) + 1
        
        # Identify common error patterns
        error_episodes = [ep for ep in episodes if ep.episode_type == "error"]
        error_patterns = self._analyze_errors(error_episodes)
        patterns.extend(error_patterns)
        
        # Identify successful task patterns
        success_episodes = [ep for ep in episodes if ep.episode_type == "success"]
        success_patterns = self._analyze_successes(success_episodes)
        patterns.extend(success_patterns)
        
        return patterns
    
    def _analyze_errors(self, episodes: List) -> List[Dict[str, Any]]:
        """Analyze error episodes to find common issues."""
        error_types = {}
        
        for ep in episodes:
            error_type = ep.context.get('error_type', 'Unknown')
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(ep)
        
        patterns = []
        for error_type, eps in error_types.items():
            if len(eps) >= 3:  # At least 3 occurrences
                patterns.append({
                    'type': 'error_pattern',
                    'key': f'error:{error_type}',
                    'value': {
                        'count': len(eps),
                        'common_context': self._find_common_context(eps)
                    },
                    'confidence': min(1.0, len(eps) / 10)
                })
        
        return patterns
    
    def _analyze_successes(self, episodes: List) -> List[Dict[str, Any]]:
        """Analyze successful episodes to find effective strategies."""
        task_counts = {}
        
        for ep in episodes:
            task = ep.context.get('task', 'unknown')
            task_counts[task] = task_counts.get(task, 0) + 1
        
        patterns = []
        for task, count in task_counts.items():
            if count >= 3:
                patterns.append({
                    'type': 'success_pattern',
                    'key': f'task:{task}',
                    'value': {
                        'success_count': count,
                        'effectiveness': 'high'
                    },
                    'confidence': min(1.0, count / 10)
                })
        
        return patterns
    
    def _find_common_context(self, episodes: List) -> Dict[str, Any]:
        """Find common context across episodes."""
        if not episodes:
            return {}
        
        # Simple approach: find keys that appear in all episodes
        common_keys = set(episodes[0].context.keys())
        for ep in episodes[1:]:
            common_keys &= set(ep.context.keys())
        
        return {key: episodes[0].context[key] for key in common_keys}
    
    def _promote_to_semantic(self, pattern: Dict[str, Any]):
        """Promote a pattern to semantic memory."""
        self.graph.add_fact(TemporalFact(
            subject="learned_patterns",
            predicate=pattern['key'],
            object_value=pattern['value'],
            valid_from=time.time(),
            confidence=pattern['confidence'],
            source="consolidation",
            metadata={"pattern_type": pattern['type']}
        ))

# Background daemon
def run_consolidation_daemon(db_path: str, interval_hours: int = 24):
    """Run consolidation as a background process."""
    consolidator = MemoryConsolidator(db_path)
    
    while True:
        try:
            consolidator.consolidate(lookback_days=7)
            print(f"[Consolidation] Completed at {datetime.now()}")
        except Exception as e:
            print(f"[Consolidation] Error: {e}")
        
        time.sleep(interval_hours * 60 * 60)
