from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from src.infra.sqlite import get_connection

STATUS_PENDING = "pending"
STATUS_PUBLISHED = "published"
STATUS_FAILED = "failed"
HANDLER_RUNNING = "running"
HANDLER_COMPLETE = "complete"


def enqueue(
    topic: str,
    event_type: str,
    payload: dict[str, Any],
    idempotency_key: str | None = None,
    conn=None,
) -> str:
    event_id = str(uuid4())
    db = conn or get_connection()
    row = None
    if idempotency_key:
        row = db.execute("SELECT id FROM event_outbox WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
    if row:
        return row["id"]
    db.execute(
        """
        INSERT INTO event_outbox (id, topic, event_type, payload, idempotency_key)
        VALUES (?, ?, ?, ?, ?)
        """,
        (event_id, topic, event_type, json.dumps(payload, ensure_ascii=False), idempotency_key),
    )
    if conn is None:
        db.commit()
    return event_id


def pending(limit: int = 100) -> list[dict[str, Any]]:
    rows = get_connection().execute(
        """
        SELECT * FROM event_outbox
        WHERE status IN (?, ?)
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (STATUS_PENDING, STATUS_FAILED, limit),
    ).fetchall()
    return [_event(row) for row in rows]


def mark_published(event_id: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE event_outbox
        SET status = ?, attempts = attempts + 1, published_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (STATUS_PUBLISHED, event_id),
    )
    conn.commit()


def mark_failed(event_id: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE event_outbox
        SET status = ?, attempts = attempts + 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (STATUS_FAILED, event_id),
    )
    conn.commit()


def begin_handler(event_id: str, handler_name: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT status FROM event_handler_runs WHERE event_id = ? AND handler_name = ?",
        (event_id, handler_name),
    ).fetchone()
    if row and row["status"] == HANDLER_COMPLETE:
        return False
    conn.execute(
        """
        INSERT INTO event_handler_runs (event_id, handler_name, status, attempts)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(event_id, handler_name) DO UPDATE SET
            status = excluded.status,
            attempts = event_handler_runs.attempts + 1,
            error = NULL,
            updated_at = CURRENT_TIMESTAMP
        """,
        (event_id, handler_name, HANDLER_RUNNING),
    )
    conn.commit()
    return True


def complete_handler(event_id: str, handler_name: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE event_handler_runs
        SET status = ?, error = NULL, updated_at = CURRENT_TIMESTAMP
        WHERE event_id = ? AND handler_name = ?
        """,
        (HANDLER_COMPLETE, event_id, handler_name),
    )
    conn.commit()


def fail_handler(event_id: str, handler_name: str, error: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        UPDATE event_handler_runs
        SET status = ?, error = ?, updated_at = CURRENT_TIMESTAMP
        WHERE event_id = ? AND handler_name = ?
        """,
        (STATUS_FAILED, error[:500], event_id, handler_name),
    )
    conn.commit()


def _event(row) -> dict[str, Any]:
    data = dict(row)
    try:
        data["payload"] = json.loads(data.get("payload") or "{}")
    except (TypeError, json.JSONDecodeError):
        data["payload"] = {}
    return data
