"""
Temporal Knowledge Graph for Agent Memory
Stores facts with validity timestamps and handles contradictions.
"""
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import sqlite3

@dataclass
class TemporalFact:
    subject: str
    predicate: str
    object_value: Any
    valid_from: float
    valid_until: Optional[float] = None
    confidence: float = 1.0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class TemporalKnowledgeGraph:
    """Graph database with temporal validity."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()
    
    def _init_schema(self):
        """Initialize temporal graph schema."""
        with sqlite3.connect(self.db_path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS temporal_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_value TEXT NOT NULL,
                    valid_from REAL NOT NULL,
                    valid_until REAL,
                    confidence REAL DEFAULT 1.0,
                    source TEXT,
                    metadata TEXT,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_temporal_subject 
                ON temporal_facts(subject)
            """)
            
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_temporal_predicate 
                ON temporal_facts(predicate)
            """)
            
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_temporal_valid 
                ON temporal_facts(valid_from, valid_until)
            """)
    
    def add_fact(self, fact: TemporalFact) -> int:
        """Add a fact with temporal validity."""
        with sqlite3.connect(self.db_path) as con:
            cursor = con.execute("""
                INSERT INTO temporal_facts 
                (subject, predicate, object_value, valid_from, valid_until, confidence, source, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fact.subject,
                fact.predicate,
                json.dumps(fact.object_value),
                fact.valid_from,
                fact.valid_until,
                fact.confidence,
                fact.source,
                json.dumps(fact.metadata)
            ))
            return cursor.lastrowid
    
    def query_facts(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        at_time: Optional[float] = None
    ) -> List[TemporalFact]:
        """Query facts, optionally filtered by time."""
        at_time = at_time or time.time()
        
        with sqlite3.connect(self.db_path) as con:
            query = """
                SELECT subject, predicate, object_value, valid_from, valid_until, 
                       confidence, source, metadata
                FROM temporal_facts
                WHERE valid_from <= ? AND (valid_until IS NULL OR valid_until >= ?)
            """
            params = [at_time, at_time]
            
            if subject:
                query += " AND subject = ?"
                params.append(subject)
            
            if predicate:
                query += " AND predicate = ?"
                params.append(predicate)
            
            cursor = con.execute(query, params)
            results = []
            
            for row in cursor.fetchall():
                results.append(TemporalFact(
                    subject=row[0],
                    predicate=row[1],
                    object_value=json.loads(row[2]),
                    valid_from=row[3],
                    valid_until=row[4],
                    confidence=row[5],
                    source=row[6],
                    metadata=json.loads(row[7]) if row[7] else {}
                ))
            
            return results
    
    def update_fact(self, subject: str, predicate: str, new_value: Any, source: str = ""):
        """Update a fact, marking old value as expired."""
        now = time.time()
        
        # Find current facts
        current_facts = self.query_facts(subject=subject, predicate=predicate, at_time=now)
        
        # Expire old facts
        for fact in current_facts:
            self._expire_fact(subject, predicate, now)
        
        # Add new fact
        self.add_fact(TemporalFact(
            subject=subject,
            predicate=predicate,
            object_value=new_value,
            valid_from=now,
            source=source
        ))
    
    def _expire_fact(self, subject: str, predicate: str, expire_time: float):
        """Mark facts as expired at given time."""
        with sqlite3.connect(self.db_path) as con:
            con.execute("""
                UPDATE temporal_facts
                SET valid_until = ?
                WHERE subject = ? AND predicate = ? 
                  AND valid_from <= ? AND (valid_until IS NULL OR valid_until >= ?)
            """, (expire_time, subject, predicate, expire_time, expire_time))
    
    def get_history(self, subject: str, predicate: str) -> List[TemporalFact]:
        """Get full history of a fact, including expired values."""
        with sqlite3.connect(self.db_path) as con:
            cursor = con.execute("""
                SELECT subject, predicate, object_value, valid_from, valid_until, 
                       confidence, source, metadata
                FROM temporal_facts
                WHERE subject = ? AND predicate = ?
                ORDER BY valid_from DESC
            """, (subject, predicate))
            
            results = []
            for row in cursor.fetchall():
                results.append(TemporalFact(
                    subject=row[0],
                    predicate=row[1],
                    object_value=json.loads(row[2]),
                    valid_from=row[3],
                    valid_until=row[4],
                    confidence=row[5],
                    source=row[6],
                    metadata=json.loads(row[7]) if row[7] else {}
                ))
            
            return results

# Example usage for agent memory
class AgentMemory:
    """High-level API for agent memory operations."""
    
    def __init__(self, db_path: str):
        self.graph = TemporalKnowledgeGraph(db_path)
    
    def remember(self, key: str, value: Any, source: str = "agent"):
        """Store a memory."""
        self.graph.add_fact(TemporalFact(
            subject="agent",
            predicate=key,
            object_value=value,
            valid_from=time.time(),
            source=source
        ))
    
    def recall(self, key: str) -> Optional[Any]:
        """Recall a memory."""
        facts = self.graph.query_facts(subject="agent", predicate=key)
        return facts[0].object_value if facts else None
    
    def learn_preference(self, preference: str, value: Any):
        """Learn a user preference."""
        self.graph.update_fact(
            subject="user_preferences",
            predicate=preference,
            new_value=value,
            source="learning_system"
        )
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get all user preferences."""
        facts = self.graph.query_facts(subject="user_preferences")
        return {f.predicate: f.object_value for f in facts}
