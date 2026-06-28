from __future__ import annotations

from uuid import uuid4

from src.infra.sqlite import get_connection


def save(job_id: str, content: str, content_hash: str | None = None) -> str:
    """Persist the exact user input before any LLM-derived work starts."""
    raw_input_id = str(uuid4())
    conn = get_connection()
    _ensure_content_hash_column(conn)
    conn.execute(
        "INSERT INTO raw_inputs (id, job_id, content_hash, content) VALUES (?, ?, ?, ?)",
        (raw_input_id, job_id, content_hash, content),
    )
    conn.commit()
    return raw_input_id


def save_or_reuse(job_id: str, content: str, content_hash: str) -> str:
    """Return the existing exact raw input or save it once.

    Content hash reuse is safe because it is computed after preprocessing, so
    the same user text resumes the same durable source record.
    """
    existing = find_by_hash(content_hash, content)
    if existing:
        return existing["id"]
    return save(job_id, content, content_hash)


def find_by_hash(content_hash: str, content: str | None = None) -> dict | None:
    """Find a raw input by content hash, with lazy backfill for old rows."""
    conn = get_connection()
    _ensure_content_hash_column(conn)
    row = conn.execute(
        "SELECT id, job_id, content_hash, content, created_at FROM raw_inputs WHERE content_hash = ? ORDER BY created_at ASC LIMIT 1",
        (content_hash,),
    ).fetchone()
    if row:
        return dict(row)
    if content is None:
        return None
    old_row = conn.execute(
        "SELECT id, job_id, content_hash, content, created_at FROM raw_inputs WHERE content = ? ORDER BY created_at ASC LIMIT 1",
        (content,),
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
    row = conn.execute("SELECT id, job_id, content_hash, content, created_at FROM raw_inputs WHERE id = ?", (input_id,)).fetchone()
    return dict(row) if row else None


def _ensure_content_hash_column(conn) -> None:
    """Allow tests/scripts that touch repositories before app startup migration."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(raw_inputs)")}
    if "content_hash" not in columns:
        conn.execute("ALTER TABLE raw_inputs ADD COLUMN content_hash TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_inputs_content_hash ON raw_inputs(content_hash)")
        conn.commit()
