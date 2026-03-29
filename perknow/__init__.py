"""
Perknow - Personal Knowledge Management System
AI-assisted organization for your ideas
"""

__version__ = "0.1.0"
__author__ = "Perknow Team"

from perknow.config import settings
from perknow.database import (
    init_database,
    create_note,
    get_note,
    update_note,
    list_notes,
    queue_operation,
    create_link,
    create_tag,
    get_pending_suggestions,
)

__all__ = [
    "settings",
    "init_database",
    "create_note",
    "get_note",
    "update_note",
    "list_notes",
    "queue_operation",
    "create_link",
    "create_tag",
    "get_pending_suggestions",
]
