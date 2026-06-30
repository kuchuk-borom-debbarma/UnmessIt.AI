from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from src.infra.sqlite import get_connection
from .models import (
    BACKOFF_SECONDS,
    CHECKPOINT_COMPLETE,
    CHECKPOINT_FAILED,
    CHECKPOINT_RUNNING,
    RETRY_LIMIT,
    STATUS_ABORTED,
    STATUS_COMPLETE,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_WAITING_RETRY,
    STATUS_PAUSED,
    STAGE_ABORTED,
    STAGE_RAW_INPUT,
    IngestJob,
)


class IngestPaused(RuntimeError):
    """Raised inside a running worker when the user pauses the job."""


def create_or_reuse_job(job_id: str, content_hash: str, raw_input_id: str) -> IngestJob:
    """Create one durable job per exact input hash."""
    existing = get_by_hash(content_hash)
    if existing:
        if existing["status"] == STATUS_ABORTED:
            _requeue_aborted(existing["id"], raw_input_id)
            return get(existing["id"]) or existing
        if existing["status"] == STATUS_WAITING_RETRY:
            resume(existing["id"])
        return get(existing["id"]) or existing

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO ingest_jobs (id, content_hash, raw_input_id, status, stage, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (job_id, content_hash, raw_input_id, STATUS_QUEUED, STAGE_RAW_INPUT, "{}"),
    )
    conn.commit()
    return get(job_id)


def _requeue_aborted(job_id: str, raw_input_id: str) -> None:
    """Allow a fresh user submit to rerun an exact input that was aborted."""
    get_connection().execute(
        """
        UPDATE ingest_jobs
        SET raw_input_id = ?, status = ?, stage = ?, attempt_count = 0,
            next_run_at = NULL, error = NULL, metadata = '{}', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (raw_input_id, STATUS_QUEUED, STAGE_RAW_INPUT, job_id),
    )
    get_connection().commit()


def get(job_id: str) -> IngestJob | None:
    """Load one ingest job."""
    row = get_connection().execute("SELECT * FROM ingest_jobs WHERE id = ?", (job_id,)).fetchone()
    return _job(row) if row else None


def get_by_hash(content_hash: str) -> IngestJob | None:
    """Load the existing idempotency job for the input hash."""
    row = get_connection().execute("SELECT * FROM ingest_jobs WHERE content_hash = ?", (content_hash,)).fetchone()
    return _job(row) if row else None


def list_jobs(user_id: str | None = None, page: int = 1, limit: int = 20) -> dict[str, Any]:
    """Return paginated jobs newest first for dev inspection."""
    conn = get_connection()
    offset = max(0, (page - 1) * limit)
    
    if user_id:
        count_row = conn.execute(
            """
            SELECT COUNT(j.id) as c
            FROM ingest_jobs j
            JOIN raw_inputs r ON r.id = j.raw_input_id
            WHERE r.user_id = ?
            """,
            (user_id,),
        ).fetchone()
        
        rows = conn.execute(
            """
            SELECT j.*, n.text as note_text
            FROM ingest_jobs j
            JOIN raw_inputs r ON r.id = j.raw_input_id
            LEFT JOIN notes n ON n.id = j.id
            WHERE r.user_id = ?
            ORDER BY j.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        ).fetchall()
    else:
        count_row = conn.execute("SELECT COUNT(*) as c FROM ingest_jobs").fetchone()
        
        rows = conn.execute(
            """
            SELECT j.*, n.text as note_text 
            FROM ingest_jobs j
            LEFT JOIN notes n ON n.id = j.id
            ORDER BY j.created_at DESC 
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        ).fetchall()
        
    return {
        "total": count_row["c"] if count_row else 0,
        "page": page,
        "limit": limit,
        "data": [_job(row) for row in rows]
    }


def list_resumable_jobs() -> list[IngestJob]:
    """Return jobs that should resume automatically on startup."""
    now = _now()
    rows = get_connection().execute(
        """
        SELECT * FROM ingest_jobs
        WHERE status IN (?, ?)
           OR (status = ? AND (next_run_at IS NULL OR next_run_at <= ?))
        ORDER BY created_at ASC
        """,
        (STATUS_QUEUED, STATUS_RUNNING, STATUS_WAITING_RETRY, now),
    ).fetchall()
    return [_job(row) for row in rows]


def start_stage(job_id: str, stage: str) -> None:
    """Mark a job stage as running."""
    job = get(job_id)
    if not job or job["status"] == STATUS_PAUSED:
        raise IngestPaused(job_id)
    get_connection().execute(
        """
        UPDATE ingest_jobs
        SET status = ?, stage = ?, error = NULL, next_run_at = NULL, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (STATUS_RUNNING, stage, job_id),
    )
    get_connection().commit()


def set_raw_input(job_id: str, raw_input_id: str) -> None:
    """Attach the durable raw input row to the job."""
    get_connection().execute(
        "UPDATE ingest_jobs SET raw_input_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (raw_input_id, job_id),
    )
    get_connection().commit()


def reset_attempts(job_id: str) -> None:
    """A successful unit resets retries for the next failing unit."""
    job = get(job_id)
    metadata = {**((job or {}).get("metadata") or {})}
    metadata.pop("failed_unit_key", None)
    get_connection().execute(
        """
        UPDATE ingest_jobs
        SET attempt_count = 0, error = NULL, next_run_at = NULL,
            metadata = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (json.dumps(metadata, ensure_ascii=False), job_id),
    )
    get_connection().commit()


def update_metadata(job_id: str, updates: dict[str, Any]) -> None:
    """Merge inspectable progress metadata into a job row."""
    if not updates:
        return
    job = get(job_id)
    if not job:
        return
    metadata = {**(job.get("metadata") or {}), **updates}
    get_connection().execute(
        "UPDATE ingest_jobs SET metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (json.dumps(metadata, ensure_ascii=False), job_id),
    )
    get_connection().commit()


def complete(job_id: str, metadata: dict[str, Any]) -> None:
    """Mark a job complete with final counts."""
    job = get(job_id)
    merged_metadata = {**((job or {}).get("metadata") or {}), **metadata}
    merged_metadata.pop("failed_unit_key", None)
    get_connection().execute(
        """
        UPDATE ingest_jobs
        SET status = ?, stage = ?, attempt_count = 0, error = NULL, next_run_at = NULL,
            metadata = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (STATUS_COMPLETE, STATUS_COMPLETE, json.dumps(merged_metadata, ensure_ascii=False), job_id),
    )
    get_connection().commit()


def abort(job_id: str, error: str, metadata: dict[str, Any] | None = None) -> None:
    """Mark corrupt jobs terminal and remove their resumable checkpoints."""
    conn = get_connection()
    job = get(job_id)
    merged_metadata = {**((job or {}).get("metadata") or {}), **(metadata or {})}
    conn.execute("DELETE FROM ingest_checkpoints WHERE job_id = ?", (job_id,))
    conn.execute(
        """
        UPDATE ingest_jobs
        SET status = ?, stage = ?, attempt_count = 0, next_run_at = NULL,
            error = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (STATUS_ABORTED, STAGE_ABORTED, error[:500], json.dumps(merged_metadata, ensure_ascii=False), job_id),
    )
    conn.commit()


def schedule_retry(job_id: str, stage: str, unit_key: str, error: str) -> IngestJob:
    """Schedule a bounded retry for the failed unit.

    The delay prevents tight loops around a down model/API while preserving the
    exact unit that needs to resume next.
    """
    job = get(job_id)
    if job and job["status"] == STATUS_PAUSED:
        return job
    attempt = (job["attempt_count"] if job else 0) + 1
    status = STATUS_FAILED if attempt >= RETRY_LIMIT else STATUS_WAITING_RETRY
    delay = BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)]
    next_run_at = None if status == STATUS_FAILED else _after(delay)
    metadata = {**((job or {}).get("metadata") or {}), "failed_unit_key": unit_key}
    get_connection().execute(
        """
        UPDATE ingest_jobs
        SET status = ?, stage = ?, attempt_count = ?, next_run_at = ?, error = ?,
            metadata = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, stage, attempt, next_run_at, error[:500], json.dumps(metadata, ensure_ascii=False), job_id),
    )
    get_connection().commit()
    return get(job_id)


def resume(job_id: str) -> None:
    """Reset a waiting/failed/paused job without deleting completed checkpoints."""
    get_connection().execute(
        """
        UPDATE ingest_jobs
        SET status = ?, attempt_count = 0, next_run_at = NULL, error = NULL, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (STATUS_QUEUED, job_id),
    )
    get_connection().commit()


def pause(job_id: str) -> None:
    """Manually pause an active job. It will remain paused until resumed."""
    get_connection().execute(
        """
        UPDATE ingest_jobs
        SET status = ?, next_run_at = NULL, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status IN (?, ?, ?)
        """,
        (STATUS_PAUSED, job_id, STATUS_QUEUED, STATUS_RUNNING, STATUS_WAITING_RETRY),
    )
    get_connection().commit()


def start_checkpoint(job_id: str, stage: str, unit_key: str) -> None:
    """Mark one deterministic work unit as running."""
    job = get(job_id)
    if not job or job["status"] == STATUS_PAUSED:
        raise IngestPaused(job_id)
    get_connection().execute(
        """
        INSERT INTO ingest_checkpoints (job_id, stage, unit_key, status, metadata)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(job_id, stage, unit_key) DO UPDATE SET
            status = excluded.status,
            error = NULL,
            updated_at = CURRENT_TIMESTAMP
        """,
        (job_id, stage, unit_key, CHECKPOINT_RUNNING, "{}"),
    )
    get_connection().commit()


def complete_checkpoint(job_id: str, stage: str, unit_key: str, output_ref: str = "", metadata: dict[str, Any] | None = None) -> None:
    """Persist the completed unit and enough metadata to skip it later."""
    get_connection().execute(
        """
        INSERT INTO ingest_checkpoints (job_id, stage, unit_key, status, output_ref, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id, stage, unit_key) DO UPDATE SET
            status = excluded.status,
            output_ref = excluded.output_ref,
            error = NULL,
            metadata = excluded.metadata,
            updated_at = CURRENT_TIMESTAMP
        """,
        (job_id, stage, unit_key, CHECKPOINT_COMPLETE, output_ref, json.dumps(metadata or {}, ensure_ascii=False)),
    )
    get_connection().commit()


def fail_checkpoint(job_id: str, stage: str, unit_key: str, error: str) -> None:
    """Record the failed unit for dev inspection."""
    get_connection().execute(
        """
        INSERT INTO ingest_checkpoints (job_id, stage, unit_key, status, error, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id, stage, unit_key) DO UPDATE SET
            status = excluded.status,
            error = excluded.error,
            updated_at = CURRENT_TIMESTAMP
        """,
        (job_id, stage, unit_key, CHECKPOINT_FAILED, error[:500], "{}"),
    )
    get_connection().commit()


def checkpoint(job_id: str, stage: str, unit_key: str) -> dict[str, Any] | None:
    """Load one checkpoint."""
    row = get_connection().execute(
        "SELECT * FROM ingest_checkpoints WHERE job_id = ? AND stage = ? AND unit_key = ?",
        (job_id, stage, unit_key),
    ).fetchone()
    return _checkpoint(row) if row else None


def checkpoint_complete(job_id: str, stage: str, unit_key: str) -> bool:
    """Return whether the deterministic unit is already done."""
    item = checkpoint(job_id, stage, unit_key)
    return bool(item and item["status"] == CHECKPOINT_COMPLETE)


def has_stage_checkpoints(job_id: str, stage: str) -> bool:
    """Tell old saved data from an interrupted checkpointed job."""
    row = get_connection().execute(
        "SELECT 1 FROM ingest_checkpoints WHERE job_id = ? AND stage = ? LIMIT 1",
        (job_id, stage),
    ).fetchone()
    return row is not None


def clear_all() -> None:
    """Clear durability tables during dev wipe."""
    conn = get_connection()
    conn.execute("DELETE FROM ingest_checkpoints")
    conn.execute("DELETE FROM ingest_jobs")
    conn.commit()


def delete_job(job_id: str) -> bool:
    """Delete a durable job and its checkpoints."""
    conn = get_connection()
    conn.execute("DELETE FROM ingest_checkpoints WHERE job_id = ?", (job_id,))
    cursor = conn.execute("DELETE FROM ingest_jobs WHERE id = ?", (job_id,))
    conn.commit()
    return cursor.rowcount > 0


def _job(row) -> IngestJob:
    data = dict(row)
    data["metadata"] = _json(data.get("metadata"), {})
    return data


def _checkpoint(row) -> dict[str, Any]:
    data = dict(row)
    data["metadata"] = _json(data.get("metadata"), {})
    return data


def _json(value: Any, fallback: Any) -> Any:
    try:
        return json.loads(value) if value else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _after(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()
