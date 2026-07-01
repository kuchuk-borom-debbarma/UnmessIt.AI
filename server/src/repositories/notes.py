from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from src.repositories import directories
from src.infra.sqlite import get_connection


def create(text: str, user_id: str, directory_id: str | None = None, metadata: dict[str, Any] | None = None, conn=None) -> str:
    _check_directory(directory_id, user_id)
    note_id = str(uuid4())
    db = conn or get_connection()
    db.execute(
        """
        INSERT INTO notes (id, text, directory_id, user_id, metadata)
        VALUES (?, ?, ?, ?, ?)
        """,
        (note_id, text, directory_id, user_id, json.dumps(metadata or {}, ensure_ascii=False))
    )
    if conn is None:
        db.commit()
    return note_id


def get(note_id: str, user_id: str) -> dict[str, Any] | None:
    row = get_connection().execute(
        """
        SELECT n.id, n.text, n.directory_id, n.user_id, n.created_at, n.updated_at, n.deleted_at, n.metadata, j.status as job_status 
        FROM notes n
        LEFT JOIN ingest_jobs j ON j.id = n.id
        WHERE n.id = ? AND n.user_id = ? AND n.deleted_at IS NULL
        """,
        (note_id, user_id)
    ).fetchone()
    return _note(row) if row else None


def update(note_id: str, text: str, user_id: str, directory_id: str | None = None, metadata: dict[str, Any] | None = None, conn=None) -> bool:
    _check_directory(directory_id, user_id)
    db = conn or get_connection()
    if metadata is not None:
        cursor = db.execute(
            """
            UPDATE notes 
            SET text = ?, directory_id = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (text, directory_id, json.dumps(metadata, ensure_ascii=False), note_id, user_id)
        )
    else:
        cursor = db.execute(
            """
            UPDATE notes 
            SET text = ?, directory_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (text, directory_id, note_id, user_id)
        )
    if conn is None:
        db.commit()
    return cursor.rowcount > 0


def delete(note_id: str, user_id: str, conn=None) -> bool:
    """Soft delete a note."""
    db = conn or get_connection()
    cursor = db.execute(
        "UPDATE notes SET deleted_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
        (note_id, user_id)
    )
    if conn is None:
        db.commit()
    return cursor.rowcount > 0

def hard_delete(note_id: str, user_id: str, conn=None) -> bool:
    """Permanently delete a note."""
    db = conn or get_connection()
    cursor = db.execute(
        "DELETE FROM notes WHERE id = ? AND user_id = ?",
        (note_id, user_id)
    )
    if conn is None:
        db.commit()
    return cursor.rowcount > 0

def restore(note_id: str, user_id: str, conn=None) -> bool:
    """Restore a soft-deleted note."""
    db = conn or get_connection()
    cursor = db.execute(
        "UPDATE notes SET deleted_at = NULL WHERE id = ? AND user_id = ?",
        (note_id, user_id)
    )
    if conn is None:
        db.commit()
    return cursor.rowcount > 0

def list_notes(user_id: str, directory_id: str | None = None, tag_id: str | None = None, include_all: bool = False, page: int = 1, limit: int = 20) -> dict[str, Any]:
    conn = get_connection()
    offset = max(0, (page - 1) * limit)
    
    query = "FROM notes n LEFT JOIN ingest_jobs j ON j.id = n.id "
    if tag_id:
        query += "INNER JOIN note_tags nt ON nt.note_id = n.id "
    
    query += "WHERE n.user_id = ? AND n.deleted_at IS NULL"
    params = [user_id]
    
    if tag_id:
        query += " AND nt.tag_id = ?"
        params.append(tag_id)
    
    if not include_all:
        if directory_id:
            query += " AND n.directory_id = ?"
            params.append(directory_id)
        else:
            query += " AND n.directory_id IS NULL"
            
    count_row = conn.execute(f"SELECT COUNT(*) as c {query}", params).fetchone()
    total = count_row["c"] if count_row else 0
    
    query += " ORDER BY n.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = conn.execute(f"SELECT n.id, n.text, n.directory_id, n.user_id, n.created_at, n.updated_at, n.metadata, j.status as job_status {query}", params).fetchall()
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [_note(row) for row in rows]
    }

def list_trash(user_id: str, page: int = 1, limit: int = 20) -> dict[str, Any]:
    conn = get_connection()
    offset = max(0, (page - 1) * limit)
    
    query = "FROM notes WHERE user_id = ? AND deleted_at IS NOT NULL"
    params = [user_id]
    
    count_row = conn.execute(f"SELECT COUNT(*) as c {query}", params).fetchone()
    total = count_row["c"] if count_row else 0
    
    query += " ORDER BY deleted_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = conn.execute(f"SELECT id, text, directory_id, user_id, created_at, updated_at, deleted_at, metadata {query}", params).fetchall()
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [_note(row) for row in rows]
    }


def _check_directory(directory_id: str | None, user_id: str) -> None:
    if directory_id and not directories.get(directory_id, user_id):
        raise ValueError("Directory not found")

def _note(row) -> dict[str, Any]:
    data = dict(row)
    try:
        data["metadata"] = json.loads(data.get("metadata") or "{}")
    except (TypeError, json.JSONDecodeError):
        data["metadata"] = {}
    return data
