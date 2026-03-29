"""
FastAPI Application - Main entry point
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from perknow.config import settings
from perknow import database as db
from perknow import models
from perknow.exporter import export_note_to_markdown

# Create FastAPI app
app = FastAPI(
    title="Perknow",
    description="Personal Knowledge Management with AI Assistance",
    version="0.1.0"
)

# Setup templates
templates = Jinja2Templates(directory="perknow/templates")


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    db.init_database()
    # Ensure export directory exists
    settings.EXPORT_PATH.mkdir(parents=True, exist_ok=True)


# Helper function for template context

def get_base_context(request: Request, **kwargs) -> dict:
    """Get base template context with request"""
    context = {"request": request}
    context.update(kwargs)
    return context


# Routes

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to inbox"""
    return RedirectResponse(url="/inbox", status_code=302)


@app.get("/inbox", response_class=HTMLResponse)
async def inbox(request: Request, success: Optional[str] = None):
    """Inbox page - capture new ideas"""
    return templates.TemplateResponse(
        "inbox.html",
        get_base_context(request, success=success)
    )


@app.post("/api/plant")
async def plant_note(content: str = Form(...), title: Optional[str] = Form(None)):
    """
    Plant a new note:
    1. Save to database
    2. Export raw capture to markdown
    3. Queue for AI processing
    """
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Content is required")
    
    content = content.strip()
    title = title.strip() if title else None
    
    # 1. Create note in database
    note_id = db.create_note(content=content, title=title)
    
    # 2. Export raw capture immediately
    try:
        export_note_to_markdown(note_id, subdir=settings.EXPORT_INBOX_SUBDIR)
    except Exception as e:
        # Log error but don't fail - we can re-export later
        print(f"Warning: Failed to export note {note_id}: {e}")
    
    # 3. Queue AI processing tasks
    # Priority: 1 = title extraction, 2 = embedding, 3 = similar notes, 4 = links, 5 = tags
    db.queue_operation(note_id, "extract_title", priority=1)
    db.queue_operation(note_id, "generate_embedding", priority=2)
    db.queue_operation(note_id, "find_similar", priority=3)
    db.queue_operation(note_id, "suggest_links", priority=4)
    db.queue_operation(note_id, "suggest_tags", priority=5)
    
    # Update note status
    db.update_note(note_id, status="processing")
    
    return RedirectResponse(
        url=f"/inbox?success=Note planted successfully! (ID: {note_id})",
        status_code=302
    )


@app.get("/browse", response_class=HTMLResponse)
async def browse(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None
):
    """Browse all notes"""
    limit = per_page
    offset = (page - 1) * per_page
    
    notes = db.list_notes(limit=limit, offset=offset, status=status)
    
    # Get total count for pagination
    with db.get_db_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT COUNT(*) FROM notes WHERE status = ?", (status,))
        else:
            cursor.execute("SELECT COUNT(*) FROM notes")
        total = cursor.fetchone()[0]
    
    total_pages = (total + per_page - 1) // per_page
    
    return templates.TemplateResponse(
        "browse.html",
        get_base_context(
            request=request,
            notes=notes,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total,
            current_status=status
        )
    )


@app.get("/note/{note_id}", response_class=HTMLResponse)
async def view_note(request: Request, note_id: int):
    """View a single note with links and tags"""
    note = db.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Get tags and links
    tags = db.get_note_tags(note_id, include_unapproved=True)
    links = db.get_note_links(note_id)
    
    return templates.TemplateResponse(
        "note.html",
        get_base_context(
            request=request,
            note=note,
            tags=tags,
            outgoing_links=links["outgoing"],
            incoming_links=links["incoming"]
        )
    )


@app.get("/review", response_class=HTMLResponse)
async def review_suggestions(request: Request):
    """Review pending AI suggestions (links and tags)"""
    suggestions = db.get_pending_suggestions()
    
    return templates.TemplateResponse(
        "review.html",
        get_base_context(
            request=request,
            pending_links=suggestions["links"],
            pending_tags=suggestions["tags"]
        )
    )


# API Routes for Review Actions

@app.post("/api/approve-link/{link_id}")
async def approve_link(link_id: int):
    """Approve an AI-suggested link"""
    success = db.update_link_approval(link_id, approved=True)
    if not success:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"success": True, "action": "approved", "link_id": link_id}


@app.post("/api/reject-link/{link_id}")
async def reject_link(link_id: int):
    """Reject an AI-suggested link"""
    success = db.update_link_approval(link_id, approved=False)
    if not success:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"success": True, "action": "rejected", "link_id": link_id}


@app.post("/api/approve-tag/{tag_id}")
async def approve_tag(tag_id: int):
    """Approve an AI-suggested tag"""
    success = db.update_tag_approval(tag_id, approved=True)
    if not success:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"success": True, "action": "approved", "tag_id": tag_id}


@app.post("/api/reject-tag/{tag_id}")
async def reject_tag(tag_id: int):
    """Reject an AI-suggested tag"""
    success = db.update_tag_approval(tag_id, approved=False)
    if not success:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"success": True, "action": "rejected", "tag_id": tag_id}


# API Routes for Notes

@app.get("/api/notes")
async def api_list_notes(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None
):
    """API endpoint to list notes"""
    notes = db.list_notes(limit=limit, offset=offset, status=status)
    return {"notes": notes, "count": len(notes)}


@app.get("/api/notes/{note_id}")
async def api_get_note(note_id: int):
    """API endpoint to get a single note"""
    note = db.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.post("/api/notes/{note_id}/export")
async def api_export_note(note_id: int):
    """Manually trigger export of a note"""
    note = db.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    try:
        path = export_note_to_markdown(note_id)
        return {"success": True, "path": str(path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Health check

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": str(settings.DATABASE_PATH),
        "export_path": str(settings.EXPORT_PATH)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
