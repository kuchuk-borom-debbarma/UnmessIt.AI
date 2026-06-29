from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.repositories import directories
from src.infra.sqlite import get_connection


def create(text: str, user_id: str, directory_id: str | None = None) -> str:
    _check_directory(directory_id, user_id)
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
    _check_directory(directory_id, user_id)
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


def list_notes(user_id: str, directory_id: str | None = None, include_all: bool = False) -> list[dict[str, Any]]:
    query = "SELECT id, text, directory_id, user_id, created_at, updated_at FROM notes WHERE user_id = ?"
    params = [user_id]
    
    if not include_all:
        if directory_id:
            query += " AND directory_id = ?"
            params.append(directory_id)
        else:
            query += " AND directory_id IS NULL"
        
    query += " ORDER BY created_at DESC"
    
    rows = get_connection().execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _check_directory(directory_id: str | None, user_id: str) -> None:
    if directory_id and not directories.get(directory_id, user_id):
        raise ValueError("Directory not found")
