from __future__ import annotations

import json
from uuid import uuid4

from src.infra.sqlite import get_connection

def save(user_id: str, query_text: str, duration_ms: int, result_json: dict) -> str:
    """Persist a query and its full retrieval trace."""
    query_id = str(uuid4())
    conn = get_connection()
    _ensure_table(conn)
    conn.execute(
        "INSERT INTO queries (id, user_id, query_text, duration_ms, result_json) VALUES (?, ?, ?, ?, ?)",
        (query_id, user_id, query_text, duration_ms, json.dumps(result_json)),
    )
    conn.commit()
    return query_id

def list_queries(user_id: str, limit: int = 50) -> list[dict]:
    """Return the most recent queries for a user."""
    conn = get_connection()
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT id, user_id, query_text, duration_ms, result_json, created_at FROM queries WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    
    results = []
    for row in rows:
        d = dict(row)
        try:
            d["result_json"] = json.loads(d["result_json"])
        except Exception:
            pass
        results.append(d)
    return results

def cleanup_stale(days: int = 7) -> int:
    """Delete queries older than the specified number of days."""
    conn = get_connection()
    _ensure_table(conn)
    cursor = conn.execute(
        "DELETE FROM queries WHERE created_at < datetime('now', ?)",
        (f"-{days} days",)
    )
    conn.commit()
    return cursor.rowcount

def _ensure_table(conn) -> None:
    """Allow tests/scripts that touch repositories before app startup migration."""
    # We rely on init_db() in sqlite.py for main table creation, 
    # but this handles tests that might not run it.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS queries (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            query_text TEXT NOT NULL,
            duration_ms INTEGER NOT NULL,
            result_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_queries_user_id ON queries(user_id)")
    conn.commit()
