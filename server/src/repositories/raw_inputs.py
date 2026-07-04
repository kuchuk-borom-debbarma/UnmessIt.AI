from __future__ import annotations

from uuid import uuid4

from src.infra.sqlite import get_connection
from src.repositories import retrieval_index


def save(job_id: str, content: str, user_id: str, content_hash: str | None = None) -> str:
    """Persist the exact user input before any LLM-derived work starts."""
    raw_input_id = str(uuid4())
    conn = get_connection()
    _ensure_content_hash_column(conn)
    conn.execute(
        "INSERT INTO raw_inputs (id, job_id, content_hash, content, user_id) VALUES (?, ?, ?, ?, ?)",
        (raw_input_id, job_id, content_hash, content, user_id),
    )
    conn.commit()
    return raw_input_id


def save_or_reuse(job_id: str, content: str, user_id: str, content_hash: str) -> str:
    """Return the existing exact raw input or save it once.

    Content hash reuse is safe because it is computed after preprocessing, so
    the same user text resumes the same durable source record.
    """
    existing = find_by_hash_and_user(content_hash, user_id, content)
    if existing:
        return existing["id"]
    return save(job_id, content, user_id, content_hash)


def find_by_hash_and_user(content_hash: str, user_id: str, content: str | None = None) -> dict | None:
    """Find a raw input by content hash and user_id, with lazy backfill for old rows."""
    conn = get_connection()
    _ensure_content_hash_column(conn)
    row = conn.execute(
        "SELECT id, job_id, content_hash, content, user_id, created_at FROM raw_inputs WHERE content_hash = ? AND user_id = ? ORDER BY created_at ASC LIMIT 1",
        (content_hash, user_id),
    ).fetchone()
    if row:
        return dict(row)
    if content is None:
        return None
    old_row = conn.execute(
        "SELECT id, job_id, content_hash, content, user_id, created_at FROM raw_inputs WHERE content = ? AND user_id = ? ORDER BY created_at ASC LIMIT 1",
        (content, user_id),
    ).fetchone()
    if not old_row:
        return None
    conn.execute("UPDATE raw_inputs SET content_hash = ? WHERE id = ?", (content_hash, old_row["id"]))
    conn.commit()
    return {**dict(old_row), "content_hash": content_hash}


def get(input_id: str) -> dict | None:
    """Return one raw input for dev inspection."""
    conn = get_connection()
    _ensure_content_hash_column(conn)
    row = conn.execute("SELECT id, job_id, content_hash, content, user_id, created_at, deleted_at FROM raw_inputs WHERE id = ?", (input_id,)).fetchone()
    return dict(row) if row else None


def list_by_job(job_id: str, user_id: str) -> list[dict]:
    """Return raw inputs created by one user-owned ingest job."""
    rows = get_connection().execute(
        "SELECT id, job_id, content_hash, content, user_id, created_at, deleted_at FROM raw_inputs WHERE job_id = ? AND user_id = ?",
        (job_id, user_id),
    ).fetchall()
    return [dict(row) for row in rows]


def list_active() -> list[dict]:
    """Return all active raw inputs."""
    conn = get_connection()
    rows = conn.execute("SELECT id, job_id, content_hash, content, user_id, created_at FROM raw_inputs WHERE deleted_at IS NULL ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def list_user_ids() -> list[str]:
    """Return users that currently have raw inputs."""
    rows = get_connection().execute("SELECT DISTINCT user_id FROM raw_inputs WHERE user_id IS NOT NULL").fetchall()
    return [row["user_id"] for row in rows]


def list_trash() -> list[dict]:
    """Return all soft-deleted raw inputs."""
    conn = get_connection()
    rows = conn.execute("SELECT id, job_id, content_hash, content, user_id, created_at, deleted_at FROM raw_inputs WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC").fetchall()
    return [dict(r) for r in rows]


def soft_delete(input_id: str) -> None:
    """Move a raw input to the trash."""
    conn = get_connection()
    row = conn.execute("SELECT user_id FROM raw_inputs WHERE id = ?", (input_id,)).fetchone()
    cursor = conn.execute("UPDATE raw_inputs SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?", (input_id,))
    if cursor.rowcount > 0:
        retrieval_index.bump(row["user_id"] if row else None, conn)
    conn.commit()


def restore(input_id: str) -> None:
    """Restore a raw input from the trash."""
    conn = get_connection()
    row = conn.execute("SELECT user_id FROM raw_inputs WHERE id = ?", (input_id,)).fetchone()
    cursor = conn.execute("UPDATE raw_inputs SET deleted_at = NULL WHERE id = ?", (input_id,))
    if cursor.rowcount > 0:
        retrieval_index.bump(row["user_id"] if row else None, conn)
    conn.commit()


def hard_delete(input_id: str) -> None:
    """Permanently delete a raw input and cascade to chunks/links."""
    conn = get_connection()
    row = conn.execute("SELECT user_id FROM raw_inputs WHERE id = ?", (input_id,)).fetchone()
    cursor = conn.execute("DELETE FROM raw_inputs WHERE id = ?", (input_id,))
    if cursor.rowcount > 0:
        retrieval_index.bump(row["user_id"] if row else None, conn)
    conn.commit()


def _ensure_content_hash_column(conn) -> None:
    """Allow tests/scripts that touch repositories before app startup migration."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(raw_inputs)")}
    if "content_hash" not in columns:
        conn.execute("ALTER TABLE raw_inputs ADD COLUMN content_hash TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_inputs_content_hash ON raw_inputs(content_hash)")
        conn.commit()
