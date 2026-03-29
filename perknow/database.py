"""
Database Layer - SQLite connection and schema
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from contextlib import contextmanager

from perknow.config import settings


def init_database(db_path: Optional[Path] = None) -> None:
    """Initialize SQLite database with all required tables"""
    db_path = db_path or settings.DATABASE_PATH
    
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        
        # Notes table - stores all captured ideas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT NOT NULL,
                embedding TEXT,  -- JSON serialized vector
                status TEXT DEFAULT 'raw',  -- raw, processing, processed
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Links table - connections between notes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_note_id INTEGER NOT NULL,
                to_note_id INTEGER NOT NULL,
                link_type TEXT DEFAULT 'related',  -- related, parent, child, reference
                confidence REAL DEFAULT 1.0,
                ai_suggested BOOLEAN DEFAULT FALSE,
                user_approved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_note_id) REFERENCES notes(id) ON DELETE CASCADE,
                FOREIGN KEY (to_note_id) REFERENCES notes(id) ON DELETE CASCADE
            )
        """)
        
        # Tags table - labels for notes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                ai_suggested BOOLEAN DEFAULT FALSE,
                user_approved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            )
        """)
        
        # Gardening queue - background AI processing tasks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gardening_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                operation TEXT NOT NULL,  -- extract_title, generate_embedding, find_similar, suggest_links, suggest_tags
                priority INTEGER DEFAULT 5,  -- 1 (highest) to 10 (lowest)
                status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
                result TEXT,  -- JSON serialized result
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_status ON notes(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_from_note ON links(from_note_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_to_note ON links(to_note_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_note ON tags(note_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON gardening_queue(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_priority ON gardening_queue(priority)")
        
        conn.commit()


@contextmanager
def get_db_connection(db_path: Optional[Path] = None):
    """Context manager for database connections"""
    db_path = db_path or settings.DATABASE_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db():
    """Generator for FastAPI dependency injection"""
    with get_db_connection() as conn:
        yield conn


# Note operations

def create_note(content: str, title: Optional[str] = None) -> int:
    """Create a new note, return the note ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notes (content, title, status) VALUES (?, ?, ?)",
            (content, title, "raw")
        )
        return cursor.lastrowid


def get_note(note_id: int) -> Optional[dict]:
    """Get a single note by ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def update_note(note_id: int, **fields) -> bool:
    """Update note fields"""
    allowed_fields = {"title", "content", "embedding", "status", "updated_at"}
    update_fields = {k: v for k, v in fields.items() if k in allowed_fields}
    
    if not update_fields:
        return False
    
    # Always update the updated_at timestamp
    update_fields["updated_at"] = datetime.now().isoformat()
    
    set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
    values = list(update_fields.values()) + [note_id]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE notes SET {set_clause} WHERE id = ?", values)
        return cursor.rowcount > 0


def list_notes(limit: int = 100, offset: int = 0, status: Optional[str] = None) -> list[dict]:
    """List notes with optional filtering"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute(
                "SELECT * FROM notes WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset)
            )
        else:
            cursor.execute(
                "SELECT * FROM notes ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        return [dict(row) for row in cursor.fetchall()]


# Gardening queue operations

def queue_operation(note_id: int, operation: str, priority: int = 5) -> int:
    """Add an operation to the gardening queue"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO gardening_queue (note_id, operation, priority) VALUES (?, ?, ?)",
            (note_id, operation, priority)
        )
        return cursor.lastrowid


def get_pending_task() -> Optional[dict]:
    """Get the highest priority pending task"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM gardening_queue 
            WHERE status = 'pending' 
            ORDER BY priority ASC, created_at ASC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def update_task_status(
    task_id: int, 
    status: str, 
    result: Optional[Any] = None, 
    error_message: Optional[str] = None
) -> bool:
    """Update task status and optionally store result"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if status == "processing":
            cursor.execute(
                "UPDATE gardening_queue SET status = ?, started_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, task_id)
            )
        elif status in ("completed", "failed"):
            result_json = json.dumps(result) if result is not None else None
            cursor.execute(
                """UPDATE gardening_queue 
                   SET status = ?, result = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (status, result_json, error_message, task_id)
            )
        else:
            cursor.execute(
                "UPDATE gardening_queue SET status = ? WHERE id = ?",
                (status, task_id)
            )
        
        return cursor.rowcount > 0


# Link operations

def create_link(
    from_note_id: int, 
    to_note_id: int, 
    link_type: str = "related",
    confidence: float = 1.0,
    ai_suggested: bool = False
) -> int:
    """Create a link between notes"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO links (from_note_id, to_note_id, link_type, confidence, ai_suggested) 
               VALUES (?, ?, ?, ?, ?)""",
            (from_note_id, to_note_id, link_type, confidence, ai_suggested)
        )
        return cursor.lastrowid


def get_note_links(note_id: int) -> dict:
    """Get all links for a note (outgoing and incoming)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Outgoing links
        cursor.execute("""
            SELECT l.*, n.title as to_title 
            FROM links l 
            JOIN notes n ON l.to_note_id = n.id 
            WHERE l.from_note_id = ?
        """, (note_id,))
        outgoing = [dict(row) for row in cursor.fetchall()]
        
        # Incoming links (backlinks)
        cursor.execute("""
            SELECT l.*, n.title as from_title 
            FROM links l 
            JOIN notes n ON l.from_note_id = n.id 
            WHERE l.to_note_id = ?
        """, (note_id,))
        incoming = [dict(row) for row in cursor.fetchall()]
        
        return {"outgoing": outgoing, "incoming": incoming}


def update_link_approval(link_id: int, approved: bool) -> bool:
    """Approve or reject an AI-suggested link"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE links SET user_approved = ? WHERE id = ?",
            (approved, link_id)
        )
        return cursor.rowcount > 0


# Tag operations

def create_tag(note_id: int, tag: str, ai_suggested: bool = False) -> int:
    """Create a tag for a note"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tags (note_id, tag, ai_suggested) VALUES (?, ?, ?)",
            (note_id, tag.lower().strip(), ai_suggested)
        )
        return cursor.lastrowid


def get_note_tags(note_id: int, include_unapproved: bool = False) -> list[dict]:
    """Get tags for a note"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if include_unapproved:
            cursor.execute("SELECT * FROM tags WHERE note_id = ?", (note_id,))
        else:
            cursor.execute(
                "SELECT * FROM tags WHERE note_id = ? AND (ai_suggested = 0 OR user_approved = 1)",
                (note_id,)
            )
        return [dict(row) for row in cursor.fetchall()]


def update_tag_approval(tag_id: int, approved: bool) -> bool:
    """Approve or reject an AI-suggested tag"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tags SET user_approved = ? WHERE id = ?",
            (approved, tag_id)
        )
        return cursor.rowcount > 0


def get_pending_suggestions() -> dict:
    """Get all pending AI suggestions for review"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Pending links (AI suggested but not reviewed)
        cursor.execute("""
            SELECT l.*, n1.title as from_title, n2.title as to_title 
            FROM links l 
            JOIN notes n1 ON l.from_note_id = n1.id 
            JOIN notes n2 ON l.to_note_id = n2.id 
            WHERE l.ai_suggested = 1 AND l.user_approved IS NULL
        """)
        links = [dict(row) for row in cursor.fetchall()]
        
        # Pending tags (AI suggested but not reviewed)
        cursor.execute("""
            SELECT t.*, n.title as note_title 
            FROM tags t 
            JOIN notes n ON t.note_id = n.id 
            WHERE t.ai_suggested = 1 AND t.user_approved IS NULL
        """)
        tags = [dict(row) for row in cursor.fetchall()]
        
        return {"links": links, "tags": tags}


# Initialize database on module import
init_database()
