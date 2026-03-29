"""
Gardener - Background AI processing logic
The AI Gardener tends to your notes by extracting titles, generating embeddings,
finding similar notes, and suggesting links and tags.
"""
import json
from typing import Optional

from perknow.config import settings
from perknow import database as db
from perknow import llm_client
from perknow import embeddings


class Gardener:
    """
    AI Gardener that processes notes in the background.
    Each operation is queued and executed separately for resilience.
    """
    
    def __init__(self):
        self.llm = llm_client.get_ollama_client()
    
    async def process_task(self, task: dict) -> dict:
        """
        Process a single gardening task.
        
        Args:
            task: Dict with task info from gardening_queue table
        
        Returns:
            Dict with operation result
        """
        operation = task["operation"]
        note_id = task["note_id"]
        
        # Get the note
        note = db.get_note(note_id)
        if not note:
            raise ValueError(f"Note {note_id} not found")
        
        # Dispatch to appropriate handler
        handlers = {
            "extract_title": self._extract_title,
            "generate_embedding": self._generate_embedding,
            "find_similar": self._find_similar,
            "suggest_links": self._suggest_links,
            "suggest_tags": self._suggest_tags,
        }
        
        handler = handlers.get(operation)
        if not handler:
            raise ValueError(f"Unknown operation: {operation}")
        
        return await handler(note)
    
    async def _extract_title(self, note: dict) -> dict:
        """
        Extract or generate a title for the note.
        Only runs if title is empty or looks like a placeholder.
        """
        current_title = note.get("title")
        content = note["content"]
        
        # Skip if title already exists and looks reasonable
        if current_title and len(current_title) > 3 and not current_title.startswith("Untitled"):
            return {"skipped": True, "reason": "Title already exists", "title": current_title}
        
        # Generate title using LLM
        try:
            title = await self.llm.generate_title(content)
            
            if title and len(title) > 0:
                # Update the note
                db.update_note(note["id"], title=title)
                return {"success": True, "title": title}
            else:
                # Fallback: use first line or truncated content
                fallback = content[:60].replace("\n", " ").strip()
                db.update_note(note["id"], title=fallback)
                return {"success": True, "title": fallback, "fallback": True}
                
        except Exception as e:
            # Fallback on error
            fallback = content[:60].replace("\n", " ").strip()
            db.update_note(note["id"], title=fallback)
            return {"success": True, "title": fallback, "fallback": True, "error": str(e)}
    
    async def _generate_embedding(self, note: dict) -> dict:
        """Generate and store embedding vector for the note"""
        content = note["content"]
        
        try:
            embedding = await self.llm.generate_embedding(content)
            
            if embedding:
                # Store in database
                embeddings.store_embedding(note["id"], embedding)
                return {
                    "success": True, 
                    "embedding_dim": len(embedding),
                    "sample": embedding[:5]  # First 5 values for debugging
                }
            else:
                return {"success": False, "error": "Empty embedding returned"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _find_similar(self, note: dict) -> dict:
        """Find similar notes based on embedding similarity"""
        note_id = note["id"]
        
        # Check if we have an embedding
        embedding = embeddings.get_embedding(note_id)
        if not embedding:
            return {"skipped": True, "reason": "No embedding available"}
        
        # Find similar notes
        similar = embeddings.find_similar_to_note(
            note_id=note_id,
            top_k=5,
            min_similarity=0.65  # Slightly lower threshold for suggestions
        )
        
        # Store suggestions as AI-suggested links
        created_links = []
        for sim in similar:
            link_id = db.create_link(
                from_note_id=note_id,
                to_note_id=sim["id"],
                link_type="related",
                confidence=sim["similarity"],
                ai_suggested=True
            )
            created_links.append({
                "link_id": link_id,
                "to_note_id": sim["id"],
                "to_title": sim["title"],
                "similarity": sim["similarity"]
            })
        
        return {
            "success": True,
            "similar_notes_found": len(similar),
            "links_created": created_links
        }
    
    async def _suggest_links(self, note: dict) -> dict:
        """
        Use LLM to suggest semantic links to other notes.
        This complements the embedding-based similarity search.
        """
        note_id = note["id"]
        content = note["content"]
        
        # Get candidate notes (notes with embeddings, excluding self)
        all_notes = embeddings.get_all_embeddings()
        candidates = [n for n in all_notes if n["id"] != note_id]
        
        if len(candidates) < 2:
            return {"skipped": True, "reason": "Not enough candidate notes"}
        
        try:
            suggested = await self.llm.suggest_links(content, candidates)
            
            created_links = []
            for suggestion in suggested:
                target_id = suggestion.get("note_id")
                confidence = suggestion.get("confidence", 0.7)
                
                # Validate the suggestion
                if not any(c["id"] == target_id for c in candidates):
                    continue
                
                # Check if link already exists
                with db.get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id FROM links WHERE from_note_id = ? AND to_note_id = ?",
                        (note_id, target_id)
                    )
                    if cursor.fetchone():
                        continue  # Skip existing links
                
                # Create the link
                link_id = db.create_link(
                    from_note_id=note_id,
                    to_note_id=target_id,
                    link_type="related",
                    confidence=confidence,
                    ai_suggested=True
                )
                created_links.append({
                    "link_id": link_id,
                    "to_note_id": target_id,
                    "confidence": confidence
                })
            
            return {
                "success": True,
                "suggestions_received": len(suggested),
                "links_created": len(created_links)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _suggest_tags(self, note: dict) -> dict:
        """Suggest tags for the note using LLM"""
        content = note["content"]
        
        # Get existing tags for context
        with db.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT tag FROM tags")
            existing_tags = [row["tag"] for row in cursor.fetchall()]
        
        try:
            suggested_tags = await self.llm.suggest_tags(content, existing_tags)
            
            created_tags = []
            for tag in suggested_tags:
                # Skip empty or too-long tags
                if not tag or len(tag) > 50:
                    continue
                
                # Check if tag already exists for this note
                with db.get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id FROM tags WHERE note_id = ? AND tag = ?",
                        (note["id"], tag)
                    )
                    if cursor.fetchone():
                        continue  # Skip duplicates
                
                # Create the tag
                tag_id = db.create_tag(
                    note_id=note["id"],
                    tag=tag,
                    ai_suggested=True
                )
                created_tags.append({"tag_id": tag_id, "tag": tag})
            
            # Update note status to processed
            db.update_note(note["id"], status="processed")
            
            return {
                "success": True,
                "tags_suggested": len(suggested_tags),
                "tags_created": len(created_tags),
                "tags": created_tags
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
_gardener: Optional[Gardener] = None


def get_gardener() -> Gardener:
    """Get or create Gardener singleton"""
    global _gardener
    if _gardener is None:
        _gardener = Gardener()
    return _gardener


async def process_single_task(task: dict) -> dict:
    """Process a single task - convenience function"""
    gardener = get_gardener()
    return await gardener.process_task(task)
