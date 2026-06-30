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
        if path.count('/') > 101:
            raise ValueError("Max directory depth of 100 exceeded")
        
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


def list_children(user_id: str, parent_id: str | None = None, page: int = 1, limit: int = 50) -> dict[str, Any]:
    """List direct children of a directory, paginated."""
    query = "FROM directories WHERE user_id = ?"
    params = [user_id]
    
    if parent_id:
        query += " AND parent_id = ?"
        params.append(parent_id)
    else:
        query += " AND parent_id IS NULL"
        
    conn = get_connection()
    offset = max(0, (page - 1) * limit)
    
    count_row = conn.execute(f"SELECT COUNT(*) as c {query}", params).fetchone()
    total = count_row["c"] if count_row else 0
    
    query += " ORDER BY name ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    rows = conn.execute(f"SELECT id, name, parent_id, path, user_id, created_at, updated_at {query}", params).fetchall()
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [dict(row) for row in rows]
    }


def list_subtree(dir_id: str, user_id: str, page: int = 1, limit: int = 50) -> dict[str, Any]:
    """List all directories under a specific directory using materialized path, paginated."""
    parent = get(dir_id, user_id)
    if not parent:
        return {"total": 0, "page": page, "limit": limit, "data": []}
        
    like_path = f"{parent['path']}%"
    conn = get_connection()
    offset = max(0, (page - 1) * limit)
    
    count_row = conn.execute(
        "SELECT COUNT(*) as c FROM directories WHERE user_id = ? AND path LIKE ? AND id != ?",
        (user_id, like_path, dir_id)
    ).fetchone()
    total = count_row["c"] if count_row else 0
    
    rows = conn.execute(
        """
        SELECT id, name, parent_id, path, user_id, created_at, updated_at 
        FROM directories 
        WHERE user_id = ? AND path LIKE ? AND id != ?
        ORDER BY path ASC LIMIT ? OFFSET ?
        """,
        (user_id, like_path, dir_id, limit, offset)
    ).fetchall()
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [dict(row) for row in rows]
    }


def list_all(user_id: str, page: int = 1, limit: int = 50) -> dict[str, Any]:
    """List all directories for a user, paginated."""
    conn = get_connection()
    offset = max(0, (page - 1) * limit)
    
    count_row = conn.execute("SELECT COUNT(*) as c FROM directories WHERE user_id = ?", (user_id,)).fetchone()
    total = count_row["c"] if count_row else 0
    
    rows = conn.execute(
        "SELECT id, name, parent_id, path, user_id, created_at, updated_at FROM directories WHERE user_id = ? ORDER BY path ASC LIMIT ? OFFSET ?",
        (user_id, limit, offset)
    ).fetchall()
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [dict(row) for row in rows]
    }

def search_by_name(query: str, user_id: str, limit: int = 10, cursor: int = 0) -> list[dict[str, Any]]:
    """Search directories by name using LIKE match."""
    conn = get_connection()
    # Simple prefix or contained match. User asked for LIKE match.
    like_query = f"%{query}%"
    rows = conn.execute(
        """
        SELECT id, name, parent_id, path, user_id, created_at, updated_at 
        FROM directories 
        WHERE user_id = ? AND name LIKE ? 
        ORDER BY name ASC 
        LIMIT ? OFFSET ?
        """,
        (user_id, like_query, limit, cursor)
    ).fetchall()
    return [dict(row) for row in rows]

def get_notes_in_subtree(dir_id: str, user_id: str) -> list[dict[str, Any]]:
    """Return all notes (id only) in this directory and any subdirectories."""
    parent = get(dir_id, user_id)
    if not parent:
        return []
        
    like_path = f"{parent['path']}%"
    rows = get_connection().execute(
        """
        SELECT n.id 
        FROM notes n
        JOIN directories d ON d.id = n.directory_id
        WHERE n.user_id = ? AND d.path LIKE ?
        """,
        (user_id, like_path)
    ).fetchall()
    return [dict(row) for row in rows]
