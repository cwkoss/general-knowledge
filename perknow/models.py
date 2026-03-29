"""
Pydantic models for request/response validation
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# Note Models

class NoteCreate(BaseModel):
    """Request model for creating a new note"""
    content: str = Field(..., min_length=1, description="Raw content of the note")
    title: Optional[str] = Field(None, description="Optional title (will be AI-generated if not provided)")


class NoteUpdate(BaseModel):
    """Request model for updating a note"""
    title: Optional[str] = None
    content: Optional[str] = None


class NoteResponse(BaseModel):
    """Response model for a note"""
    id: int
    title: Optional[str]
    content: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NoteDetailResponse(NoteResponse):
    """Detailed note response including links and tags"""
    tags: list[dict] = []
    outgoing_links: list[dict] = []
    incoming_links: list[dict] = []


# Tag Models

class TagCreate(BaseModel):
    """Request model for creating a tag"""
    tag: str = Field(..., min_length=1, max_length=50)
    note_id: int


class TagResponse(BaseModel):
    """Response model for a tag"""
    id: int
    note_id: int
    tag: str
    ai_suggested: bool
    user_approved: Optional[bool]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TagApprovalRequest(BaseModel):
    """Request to approve or reject a tag"""
    approved: bool


# Link Models

class LinkCreate(BaseModel):
    """Request model for creating a link"""
    from_note_id: int
    to_note_id: int
    link_type: str = Field(default="related", pattern="^(related|parent|child|reference)$")


class LinkResponse(BaseModel):
    """Response model for a link"""
    id: int
    from_note_id: int
    to_note_id: int
    from_title: Optional[str] = None
    to_title: Optional[str] = None
    link_type: str
    confidence: float
    ai_suggested: bool
    user_approved: Optional[bool]
    created_at: datetime
    
    class Config:
        from_attributes = True


class LinkApprovalRequest(BaseModel):
    """Request to approve or reject a link"""
    approved: bool


# Gardening Queue Models

class QueueOperation(BaseModel):
    """Model for queue operations"""
    id: int
    note_id: int
    operation: str
    priority: int
    status: str
    result: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Review Models

class PendingSuggestions(BaseModel):
    """Response model for pending AI suggestions"""
    links: list[LinkResponse]
    tags: list[TagResponse]


# Search Models

class SearchRequest(BaseModel):
    """Request model for searching notes"""
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=100)


class SearchResult(BaseModel):
    """Single search result"""
    note: NoteResponse
    similarity: float


class SearchResponse(BaseModel):
    """Response model for search"""
    results: list[SearchResult]


# Export Models

class ExportStatus(BaseModel):
    """Status of export operation"""
    note_id: int
    exported: bool
    path: Optional[str] = None
    error: Optional[str] = None
