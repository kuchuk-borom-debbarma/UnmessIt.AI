from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.infra.sqlite import get_connection


def create(name: str, user_id: str, parent_id: str | None = None) -> str:
    """Create a new directory using materialized path pattern."""
    dir_id = str(uuid4())
    conn = get_connection()
    
    path = f"/{dir_id}/"
    if parent_id:
        parent = get(parent_id, user_id)
        if not parent:
            raise ValueError(f"Parent directory {parent_id} not found")
        path = f"{parent['path']}{dir_id}/"
        
    conn.execute(
        """
        INSERT INTO directories (id, name, parent_id, path, user_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (dir_id, name, parent_id, path, user_id)
    )
    conn.commit()
    return dir_id


def get(dir_id: str, user_id: str) -> dict[str, Any] | None:
    row = get_connection().execute(
        "SELECT id, name, parent_id, path, user_id, created_at, updated_at FROM directories WHERE id = ? AND user_id = ?",
        (dir_id, user_id)
    ).fetchone()
    return dict(row) if row else None


def update(dir_id: str, name: str, user_id: str) -> bool:
    """Update directory name. (Moving requires updating all subtree paths, keeping it simple for now)."""
    conn = get_connection()
    cursor = conn.execute(
        """
        UPDATE directories 
        SET name = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        """,
        (name, dir_id, user_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def delete(dir_id: str, user_id: str) -> bool:
    """Delete a directory. SQLite CASCADE handles child dirs and nullifies note references."""
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM directories WHERE id = ? AND user_id = ?",
        (dir_id, user_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def list_children(user_id: str, parent_id: str | None = None) -> list[dict[str, Any]]:
    """List direct children of a directory."""
    query = "SELECT id, name, parent_id, path, user_id, created_at, updated_at FROM directories WHERE user_id = ?"
    params = [user_id]
    
    if parent_id:
        query += " AND parent_id = ?"
        params.append(parent_id)
    else:
        query += " AND parent_id IS NULL"
        
    query += " ORDER BY name ASC"
    
    rows = get_connection().execute(query, params).fetchall()
    return [dict(row) for row in rows]


def list_subtree(dir_id: str, user_id: str) -> list[dict[str, Any]]:
    """List all directories under a specific directory using materialized path."""
    parent = get(dir_id, user_id)
    if not parent:
        return []
        
    # Example: if parent path is "/1/4/", match "/1/4/%" but exclude "/1/4/" itself
    like_path = f"{parent['path']}%"
    rows = get_connection().execute(
        """
        SELECT id, name, parent_id, path, user_id, created_at, updated_at 
        FROM directories 
        WHERE user_id = ? AND path LIKE ? AND id != ?
        ORDER BY path ASC
        """,
        (user_id, like_path, dir_id)
    ).fetchall()
    return [dict(row) for row in rows]
