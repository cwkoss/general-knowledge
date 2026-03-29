"""
Exporter - Markdown export to git-tracked files
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from perknow.config import settings
from perknow import database as db


def sanitize_filename(title: str) -> str:
    """
    Convert a title to a safe filename.
    Removes/replaces special characters and limits length.
    """
    # Remove or replace unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = safe.replace(' ', '_')
    safe = re.sub(r'_+', '_', safe)  # Collapse multiple underscores
    safe = safe.strip('._')
    
    # Limit length
    if len(safe) > 50:
        safe = safe[:50]
    
    return safe or "untitled"


def escape_yaml_string(s: str) -> str:
    """Escape a string for YAML frontmatter"""
    if not s:
        return '""'
    
    # Check if we need quotes
    if any(c in s for c in [':', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`', '"', "'"]):
        # Escape quotes
        escaped = s.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    
    return s


def export_note_to_markdown(
    note_id: int,
    subdir: Optional[str] = None
) -> Path:
    """
    Export a note to markdown format with YAML frontmatter.
    
    Args:
        note_id: The note ID to export
        subdir: Optional subdirectory within export path (e.g., "inbox")
    
    Returns:
        Path to the exported file
    """
    # Get note from database
    note = db.get_note(note_id)
    if not note:
        raise ValueError(f"Note {note_id} not found")
    
    # Get approved tags
    tags = db.get_note_tags(note_id, include_unapproved=False)
    tag_list = [t["tag"] for t in tags]
    
    # Get approved links for wiki-link conversion
    links = db.get_note_links(note_id)
    approved_outgoing = [
        l for l in links["outgoing"] 
        if not l["ai_suggested"] or l.get("user_approved") == 1
    ]
    
    # Build YAML frontmatter
    title = note.get("title") or "Untitled Note"
    created = note["created_at"]
    updated = note["updated_at"]
    
    frontmatter_lines = [
        "---",
        f"id: {note_id}",
        f"title: {escape_yaml_string(title)}",
        f"created: {created}",
        f"updated: {updated}",
    ]
    
    if tag_list:
        frontmatter_lines.append(f"tags: [{', '.join(escape_yaml_string(t) for t in tag_list)}]")
    
    frontmatter_lines.append("---")
    frontmatter = "\n".join(frontmatter_lines)
    
    # Process content
    content = note["content"]
    
    # Add outgoing links section if there are approved links
    links_section = ""
    if approved_outgoing:
        links_section = "\n\n## Related Notes\n\n"
        for link in approved_outgoing:
            link_title = link.get("to_title") or f"Note {link['to_note_id']}"
            safe_title = link_title.replace("[", "").replace("]", "")
            links_section += f"- [[{safe_title}]]\n"
    
    # Build full markdown
    markdown = f"{frontmatter}\n\n# {title}\n\n{content}{links_section}"
    
    # Determine output path
    export_dir = settings.EXPORT_PATH
    if subdir:
        export_dir = export_dir / subdir
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename
    safe_title = sanitize_filename(title)
    filename = f"{note_id:04d}_{safe_title}.md"
    filepath = export_dir / filename
    
    # Write file
    filepath.write_text(markdown, encoding="utf-8")
    
    return filepath


def export_all_notes(
    subdir: Optional[str] = None,
    status_filter: Optional[str] = None
) -> dict:
    """
    Export all notes to markdown.
    
    Args:
        subdir: Optional subdirectory for output
        status_filter: Optional status to filter by
    
    Returns:
        Dict with export statistics
    """
    notes = db.list_notes(limit=10000, status=status_filter)
    
    exported = 0
    errors = []
    
    for note in notes:
        try:
            export_note_to_markdown(note["id"], subdir)
            exported += 1
        except Exception as e:
            errors.append({"note_id": note["id"], "error": str(e)})
    
    return {
        "total": len(notes),
        "exported": exported,
        "errors": errors
    }


def get_export_path(note_id: int, subdir: Optional[str] = None) -> Optional[Path]:
    """
    Get the expected export path for a note (without actually exporting).
    Useful for displaying paths in the UI.
    """
    note = db.get_note(note_id)
    if not note:
        return None
    
    title = note.get("title") or "Untitled Note"
    safe_title = sanitize_filename(title)
    filename = f"{note_id:04d}_{safe_title}.md"
    
    export_dir = settings.EXPORT_PATH
    if subdir:
        export_dir = export_dir / subdir
    
    return export_dir / filename


def rewrite_links_to_wikilinks(content: str, note_id_map: dict) -> str:
    """
    Rewrite note references in content to [[WikiLinks]] format.
    
    Args:
        content: The note content
        note_id_map: Dict mapping note IDs to titles
    
    Returns:
        Content with wiki-links
    """
    # Pattern to match note references like #123 or note://123
    pattern = r'(?:#|note://)(\d+)'
    
    def replace_match(match):
        note_id = int(match.group(1))
        title = note_id_map.get(note_id, f"Note {note_id}")
        return f"[[{title}]]"
    
    return re.sub(pattern, replace_match, content)
