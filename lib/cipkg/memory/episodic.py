"""
Episodic Memory - Store agent experiences and interactions.
"""
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import sqlite3

@dataclass
class Episode:
    id: int
    timestamp: float
    episode_type: str  # 'interaction', 'error', 'success', 'debug'
    context: Dict[str, Any]
    outcome: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

class EpisodicMemory:
    """Store and retrieve agent experiences."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()
    
    def _init_schema(self):
        """Initialize episodic memory schema."""
        with sqlite3.connect(self.db_path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    episode_type TEXT NOT NULL,
                    context TEXT NOT NULL,
                    outcome TEXT,
                    metadata TEXT,
                    embedding BLOB
                )
            """)
            
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_episode_type 
                ON episodes(episode_type)
            """)
            
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_episode_timestamp 
                ON episodes(timestamp)
            """)
    
    def record_episode(
        self,
        episode_type: str,
        context: Dict[str, Any],
        outcome: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Record a new episode."""
        with sqlite3.connect(self.db_path) as con:
            cursor = con.execute("""
                INSERT INTO episodes (timestamp, episode_type, context, outcome, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                time.time(),
                episode_type,
                json.dumps(context),
                outcome,
                json.dumps(metadata or {})
            ))
            return cursor.lastrowid
    
    def query_episodes(
        self,
        episode_type: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 50
    ) -> List[Episode]:
        """Query episodes with filters."""
        with sqlite3.connect(self.db_path) as con:
            query = "SELECT * FROM episodes WHERE 1=1"
            params = []
            
            if episode_type:
                query += " AND episode_type = ?"
                params.append(episode_type)
            
            if since:
                query += " AND timestamp >= ?"
                params.append(since)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = con.execute(query, params)
            episodes = []
            
            for row in cursor.fetchall():
                episodes.append(Episode(
                    id=row[0],
                    timestamp=row[1],
                    episode_type=row[2],
                    context=json.loads(row[3]),
                    outcome=row[4],
                    metadata=json.loads(row[5]) if row[5] else {}
                ))
            
            return episodes
    
    def find_similar_episodes(self, context: Dict[str, Any], limit: int = 5) -> List[Episode]:
        """Find episodes with similar context (simple keyword matching)."""
        # Extract key terms from context
        key_terms = set()
        for value in context.values():
            if isinstance(value, str):
                key_terms.update(value.lower().split())
        
        # Search episodes
        all_episodes = self.query_episodes(limit=1000)
        
        # Score by keyword overlap
        scored = []
        for episode in all_episodes:
            episode_text = json.dumps(episode.context).lower()
            score = sum(1 for term in key_terms if term in episode_text)
            if score > 0:
                scored.append((score, episode))
        
        # Return top matches
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:limit]]

# Agent memory integration
class AgentExperienceLogger:
    """Log agent experiences for future learning."""
    
    def __init__(self, db_path: str):
        self.memory = EpisodicMemory(db_path)
    
    def log_interaction(self, query: str, result: Any, success: bool):
        """Log an agent interaction."""
        self.memory.record_episode(
            episode_type="interaction",
            context={
                "query": query,
                "result_summary": str(result)[:500]
            },
            outcome="success" if success else "failure"
        )
    
    def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log an error episode."""
        self.memory.record_episode(
            episode_type="error",
            context={
                "error_type": type(error).__name__,
                "error_message": str(error),
                **context
            },
            outcome="error"
        )
    
    def log_success(self, task: str, details: Dict[str, Any]):
        """Log a successful task completion."""
        self.memory.record_episode(
            episode_type="success",
            context={
                "task": task,
                **details
            },
            outcome="success"
        )
    
    def recall_similar(self, query: str) -> List[Episode]:
        """Recall similar past interactions."""
        return self.memory.find_similar_episodes({"query": query})
