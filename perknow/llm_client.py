"""
LLM Client - Ollama integration for embeddings and chat
"""
import json
import asyncio
from typing import Optional
import httpx

from perknow.config import settings


class OllamaClient:
    """Client for Ollama API operations"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.embedding_model = settings.EMBEDDING_MODEL
        self.chat_model = settings.CHAT_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS
        self.embedding_timeout = settings.EMBEDDING_TIMEOUT_SECONDS
    
    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text using nomic-embed-text"""
        url = f"{self.base_url}/api/embeddings"
        
        payload = {
            "model": self.embedding_model,
            "prompt": text
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, 
                    json=payload, 
                    timeout=self.embedding_timeout
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", [])
            except httpx.TimeoutException:
                raise TimeoutError(f"Embedding generation timed out after {self.embedding_timeout}s")
            except httpx.HTTPError as e:
                raise ConnectionError(f"Failed to generate embedding: {e}")
    
    async def generate_title(self, content: str, max_length: int = 60) -> str:
        """Generate a concise title for note content"""
        url = f"{self.base_url}/api/generate"
        
        prompt = f"""Generate a concise, descriptive title for the following note.
The title should be no more than {max_length} characters.
Return ONLY the title, no quotes or additional text.

Note content:
{content[:2000]}  # Limit content to avoid token limits

Title:"""
        
        payload = {
            "model": self.chat_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": max_length
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                title = data.get("response", "").strip()
                # Remove quotes if present
                title = title.strip('"\'')
                return title[:max_length]
            except httpx.TimeoutException:
                # Fallback: use first line or truncated content
                return content[:max_length].replace("\n", " ")
            except httpx.HTTPError as e:
                raise ConnectionError(f"Failed to generate title: {e}")
    
    async def suggest_tags(self, content: str, existing_tags: list[str] = None) -> list[str]:
        """Suggest relevant tags for note content"""
        url = f"{self.base_url}/api/generate"
        
        existing = ", ".join(existing_tags) if existing_tags else "none"
        
        prompt = f"""Suggest 3-5 relevant tags for the following note.
Tags should be lowercase, single words or hyphenated phrases.
Avoid generic tags like "note" or "document".
Return as a JSON array of strings.

Existing tags in system: {existing}

Note content:
{content[:2000]}

Tags (JSON array):"""
        
        payload = {
            "model": self.chat_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.5
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                response_text = data.get("response", "[]")
                
                # Parse JSON response
                try:
                    tags = json.loads(response_text)
                    if isinstance(tags, list):
                        return [str(t).lower().strip() for t in tags[:5]]
                    elif isinstance(tags, dict) and "tags" in tags:
                        return [str(t).lower().strip() for t in tags["tags"][:5]]
                except json.JSONDecodeError:
                    pass
                
                # Fallback: parse as comma-separated
                return [t.strip().lower() for t in response_text.split(",")[:5] if t.strip()]
                
            except httpx.TimeoutException:
                return []
            except httpx.HTTPError as e:
                raise ConnectionError(f"Failed to suggest tags: {e}")
    
    async def suggest_links(
        self, 
        note_content: str, 
        candidate_notes: list[dict]
    ) -> list[dict]:
        """Suggest links to related notes based on content similarity"""
        url = f"{self.base_url}/api/generate"
        
        if not candidate_notes:
            return []
        
        # Format candidate notes for the prompt
        candidates_text = "\n".join([
            f"ID {n['id']}: {n.get('title', 'Untitled')[:50]}"
            for n in candidate_notes[:20]  # Limit candidates
        ])
        
        prompt = f"""Analyze the following note and identify which existing notes it is related to.
For each related note, provide the ID and a confidence score (0.0-1.0).
Return as a JSON array of objects with "id" and "confidence" fields.
Only include notes with confidence >= 0.6.

Current note:
{note_content[:1500]}

Candidate notes:
{candidates_text}

Related notes (JSON array):"""
        
        payload = {
            "model": self.chat_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.3
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                response_text = data.get("response", "[]")
                
                # Parse JSON response
                try:
                    links = json.loads(response_text)
                    if isinstance(links, list):
                        return [
                            {"note_id": int(l["id"]), "confidence": float(l.get("confidence", 0.7))}
                            for l in links if isinstance(l, dict) and "id" in l
                        ]
                    elif isinstance(links, dict) and "links" in links:
                        return [
                            {"note_id": int(l["id"]), "confidence": float(l.get("confidence", 0.7))}
                            for l in links["links"] if isinstance(l, dict) and "id" in l
                        ]
                except (json.JSONDecodeError, ValueError, KeyError):
                    pass
                
                return []
                
            except httpx.TimeoutException:
                return []
            except httpx.HTTPError as e:
                raise ConnectionError(f"Failed to suggest links: {e}")
    
    async def health_check(self) -> bool:
        """Check if Ollama is reachable"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags", 
                    timeout=5
                )
                return response.status_code == 200
        except Exception:
            return False


# Singleton instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create Ollama client singleton"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


async def generate_embedding(text: str) -> list[float]:
    """Convenience function to generate embedding"""
    client = get_ollama_client()
    return await client.generate_embedding(text)


async def generate_title(content: str) -> str:
    """Convenience function to generate title"""
    client = get_ollama_client()
    return await client.generate_title(content)


async def suggest_tags(content: str, existing_tags: list[str] = None) -> list[str]:
    """Convenience function to suggest tags"""
    client = get_ollama_client()
    return await client.suggest_tags(content, existing_tags)


async def suggest_links(note_content: str, candidate_notes: list[dict]) -> list[dict]:
    """Convenience function to suggest links"""
    client = get_ollama_client()
    return await client.suggest_links(note_content, candidate_notes)
