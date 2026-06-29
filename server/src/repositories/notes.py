from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.infra.sqlite import get_connection


def create(text: str, user_id: str, directory_id: str | None = None) -> str:
    note_id = str(uuid4())
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO notes (id, text, directory_id, user_id)
        VALUES (?, ?, ?, ?)
        """,
        (note_id, text, directory_id, user_id)
    )
    conn.commit()
    return note_id


def get(note_id: str, user_id: str) -> dict[str, Any] | None:
    row = get_connection().execute(
        "SELECT id, text, directory_id, user_id, created_at, updated_at FROM notes WHERE id = ? AND user_id = ?",
        (note_id, user_id)
    ).fetchone()
    return dict(row) if row else None


def update(note_id: str, text: str, user_id: str, directory_id: str | None = None) -> bool:
    conn = get_connection()
    cursor = conn.execute(
        """
        UPDATE notes 
        SET text = ?, directory_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        """,
        (text, directory_id, note_id, user_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def delete(note_id: str, user_id: str) -> bool:
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM notes WHERE id = ? AND user_id = ?",
        (note_id, user_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def list_notes(user_id: str, directory_id: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT id, text, directory_id, user_id, created_at, updated_at FROM notes WHERE user_id = ?"
    params = [user_id]
    
    if directory_id:
        query += " AND directory_id = ?"
        params.append(directory_id)
    else:
        query += " AND directory_id IS NULL"
        
    query += " ORDER BY created_at DESC"
    
    rows = get_connection().execute(query, params).fetchall()
    return [dict(row) for row in rows]
