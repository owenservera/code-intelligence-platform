"""
LanceDB Integration - High-performance vector storage with hybrid search.
"""
import lancedb
import pyarrow as pa
import numpy as np
from typing import List, Dict, Optional
import os

class LanceDBVectorStore:
    """LanceDB-based vector store with hybrid search capabilities."""
    
    def __init__(self, db_path: str, table_name: str = "code_embeddings"):
        self.db_path = db_path
        self.table_name = table_name
        self.db = lancedb.connect(db_path)
        self.table = None
        self._init_table()
    
    def _init_table(self):
        """Initialize the vector table."""
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("path", pa.string()),
            pa.field("symbol_id", pa.string()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), 384)),  # Adjust dim as needed
            pa.field("metadata", pa.string())
        ])
        
        if self.table_name not in self.db.table_names():
            self.table = self.db.create_table(self.table_name, schema=schema)
        else:
            self.table = self.db.open_table(self.table_name)
    
    def add_embeddings(
        self,
        ids: List[str],
        paths: List[str],
        symbol_ids: List[str],
        texts: List[str],
        vectors: List[List[float]],
        metadata: Optional[List[Dict]] = None
    ):
        """Add embeddings to the store."""
        metadata = metadata or [{} for _ in ids]
        
        data = [
            {
                "id": id_,
                "path": path,
                "symbol_id": symbol_id,
                "text": text,
                "vector": vector,
                "metadata": json.dumps(meta)
            }
            for id_, path, symbol_id, text, vector, meta in 
            zip(ids, paths, symbol_ids, texts, vectors, metadata)
        ]
        
        self.table.add(data)
    
    def hybrid_search(
        self,
        query_vector: List[float],
        query_text: Optional[str] = None,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Perform hybrid search (vector + lexical)."""
        # Vector search
        results = self.table.search(query_vector).limit(top_k * 2).to_list()
        
        # If text query provided, boost with lexical similarity
        if query_text:
            for result in results:
                text = result.get('text', '')
                lexical_score = self._lexical_similarity(query_text, text)
                result['score'] = result.get('score', 0) + (lexical_score * 0.3)
            
            # Re-sort by combined score
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return results[:top_k]
    
    def _lexical_similarity(self, query: str, text: str) -> float:
        """Simple lexical similarity based on token overlap."""
        query_tokens = set(query.lower().split())
        text_tokens = set(text.lower().split())
        
        if not query_tokens:
            return 0.0
        
        overlap = len(query_tokens & text_tokens)
        return overlap / len(query_tokens)
    
    def delete_by_path(self, path: str):
        """Delete all embeddings for a given path."""
        self.table.delete(f"path = '{path}'")

# Migration helper
def migrate_sqlite_to_lancedb(sqlite_db: str, lancedb_path: str):
    """Migrate existing SQLite vectors to LanceDB."""
    import sqlite3
    from .store import vector_matrix
    
    con = sqlite3.connect(sqlite_db)
    
    # Get vectors from SQLite
    cursor = con.execute("SELECT id, vec FROM vectors")
    rows = cursor.fetchall()
    
    if not rows:
        print("No vectors to migrate")
        return
    
    # Initialize LanceDB
    store = LanceDBVectorStore(lancedb_path)
    
    # Convert and add
    ids = []
    vectors = []
    paths = []
    symbol_ids = []
    texts = []
    
    for row in rows:
        id_, vec_blob = row
        vector = np.frombuffer(vec_blob, dtype=np.float32).tolist()
        
        # Get metadata from chunks table
        meta_cursor = con.execute(
            "SELECT path, symbol_id, text FROM chunks WHERE id = ?",
            (id_,)
        )
        meta = meta_cursor.fetchone()
        
        if meta:
            path, symbol_id, text = meta
            ids.append(id_)
            vectors.append(vector)
            paths.append(path)
            symbol_ids.append(symbol_id or "")
            texts.append(text)
    
    # Add in batches
    batch_size = 1000
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        batch_vectors = vectors[i:i+batch_size]
        batch_paths = paths[i:i+batch_size]
        batch_symbol_ids = symbol_ids[i:i+batch_size]
        batch_texts = texts[i:i+batch_size]
        
        store.add_embeddings(
            batch_ids,
            batch_paths,
            batch_symbol_ids,
            batch_texts,
            batch_vectors
        )
    
    print(f"Migrated {len(ids)} vectors to LanceDB")
