from __future__ import annotations

import sqlite3
from typing import Any
from uuid import uuid4

from src.infra.sqlite import get_connection
from src.repositories import retrieval_index


def create(name: str, user_id: str, conn=None) -> str:
    """Create a new tag. Raises sqlite3.IntegrityError if name already exists for user."""
    tag_id = str(uuid4())
    db = conn or get_connection()
    db.execute(
        """
        INSERT INTO tags (id, name, user_id)
        VALUES (?, ?, ?)
        """,
        (tag_id, name, user_id)
    )
    if conn is None:
        db.commit()
    return tag_id


def list_tags(user_id: str) -> list[dict[str, Any]]:
    rows = get_connection().execute(
        "SELECT id, name, user_id, created_at FROM tags WHERE user_id = ? ORDER BY name ASC",
        (user_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def search_tags(user_id: str, query: str = "", limit: int = 20, cursor: int = 0) -> list[dict[str, Any]]:
    conn = get_connection()
    if query:
        rows = conn.execute(
            "SELECT id, name, user_id, created_at FROM tags WHERE user_id = ? AND name LIKE ? ORDER BY name ASC LIMIT ? OFFSET ?",
            (user_id, f"%{query}%", limit, cursor)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, user_id, created_at FROM tags WHERE user_id = ? ORDER BY name ASC LIMIT ? OFFSET ?",
            (user_id, limit, cursor)
        ).fetchall()
    return [dict(row) for row in rows]


def get_by_name(name: str, user_id: str) -> dict[str, Any] | None:
    row = get_connection().execute(
        "SELECT id, name, user_id, created_at FROM tags WHERE name = ? AND user_id = ?",
        (name, user_id)
    ).fetchone()
    return dict(row) if row else None


def add_to_note(note_id: str, tag_id: str, conn=None) -> None:
    """Associate a tag with a note."""
    db = conn or get_connection()
    try:
        cursor = db.execute(
            """
            INSERT INTO note_tags (note_id, tag_id)
            VALUES (?, ?)
            """,
            (note_id, tag_id)
        )
        if cursor.rowcount > 0:
            retrieval_index.bump(_note_user_id(db, note_id), db)
        if conn is None:
            db.commit()
    except sqlite3.IntegrityError:
        pass # Already tagged


def remove_from_note(note_id: str, tag_id: str, conn=None) -> None:
    db = conn or get_connection()
    cursor = db.execute(
        "DELETE FROM note_tags WHERE note_id = ? AND tag_id = ?",
        (note_id, tag_id)
    )
    if cursor.rowcount > 0:
        retrieval_index.bump(_note_user_id(db, note_id), db)
    if conn is None:
        db.commit()


def get_for_note(note_id: str) -> list[dict[str, Any]]:
    rows = get_connection().execute(
        """
        SELECT t.id, t.name, t.user_id, t.created_at
        FROM tags t
        JOIN note_tags nt ON nt.tag_id = t.id
        WHERE nt.note_id = ?
        ORDER BY t.name ASC
        """,
        (note_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def _note_user_id(conn, note_id: str) -> str | None:
    row = conn.execute("SELECT user_id FROM notes WHERE id = ?", (note_id,)).fetchone()
    return row["user_id"] if row else None
