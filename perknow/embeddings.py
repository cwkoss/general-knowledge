"""
Embeddings - Vector operations and similarity search
"""
import json
import math
from typing import Optional
import numpy as np

from perknow.config import settings
from perknow.database import get_db_connection


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    Returns a value between -1 and 1, where 1 means identical direction.
    """
    if not v1 or not v2:
        return 0.0
    
    vec1 = np.array(v1, dtype=np.float32)
    vec2 = np.array(v2, dtype=np.float32)
    
    # Handle zero vectors
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def store_embedding(note_id: int, embedding: list[float]) -> bool:
    """Store embedding vector for a note"""
    embedding_json = json.dumps(embedding)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notes SET embedding = ? WHERE id = ?",
            (embedding_json, note_id)
        )
        return cursor.rowcount > 0


def get_embedding(note_id: int) -> Optional[list[float]]:
    """Get embedding vector for a note"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT embedding FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        
        if row and row["embedding"]:
            try:
                return json.loads(row["embedding"])
            except json.JSONDecodeError:
                return None
        return None


def find_similar_notes(
    query_embedding: list[float],
    exclude_note_id: Optional[int] = None,
    top_k: int = 5,
    min_similarity: float = 0.7
) -> list[dict]:
    """
    Find notes with similar embeddings using cosine similarity.
    
    Args:
        query_embedding: The embedding vector to compare against
        exclude_note_id: Optional note ID to exclude from results
        top_k: Maximum number of results to return
        min_similarity: Minimum similarity threshold (0.0 to 1.0)
    
    Returns:
        List of dicts with note info and similarity scores
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, content, embedding FROM notes WHERE embedding IS NOT NULL"
        )
        
        similarities = []
        
        for row in cursor.fetchall():
            note_id = row["id"]
            
            # Skip excluded note
            if exclude_note_id and note_id == exclude_note_id:
                continue
            
            # Parse stored embedding
            try:
                note_embedding = json.loads(row["embedding"])
            except (json.JSONDecodeError, TypeError):
                continue
            
            # Calculate similarity
            similarity = cosine_similarity(query_embedding, note_embedding)
            
            if similarity >= min_similarity:
                similarities.append({
                    "id": note_id,
                    "title": row["title"],
                    "content": row["content"][:200],  # Preview only
                    "similarity": round(similarity, 4)
                })
        
        # Sort by similarity (highest first) and return top_k
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_k]


def find_similar_to_note(
    note_id: int,
    top_k: int = 5,
    min_similarity: float = 0.7
) -> list[dict]:
    """
    Find notes similar to a specific note.
    
    Args:
        note_id: The note ID to find similarities for
        top_k: Maximum number of results to return
        min_similarity: Minimum similarity threshold
    
    Returns:
        List of similar notes with similarity scores
    """
    embedding = get_embedding(note_id)
    if not embedding:
        return []
    
    return find_similar_notes(
        query_embedding=embedding,
        exclude_note_id=note_id,
        top_k=top_k,
        min_similarity=min_similarity
    )


def get_all_embeddings() -> list[dict]:
    """Get all notes with embeddings (for link suggestions)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, content FROM notes WHERE embedding IS NOT NULL"
        )
        return [dict(row) for row in cursor.fetchall()]


def compute_similarity_matrix(note_ids: list[int]) -> dict:
    """
    Compute pairwise similarity matrix for a list of notes.
    Useful for visualization or clustering.
    
    Returns dict of {(id1, id2): similarity}
    """
    embeddings = {}
    for note_id in note_ids:
        emb = get_embedding(note_id)
        if emb:
            embeddings[note_id] = emb
    
    similarities = {}
    ids = list(embeddings.keys())
    
    for i, id1 in enumerate(ids):
        for id2 in ids[i+1:]:
            sim = cosine_similarity(embeddings[id1], embeddings[id2])
            similarities[(id1, id2)] = sim
            similarities[(id2, id1)] = sim  # Symmetric
    
    return similarities
