from __future__ import annotations

from typing import Any, TypedDict

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_WAITING_RETRY = "waiting_retry"
STATUS_COMPLETE = "complete"
STATUS_FAILED = "failed"
STATUS_ABORTED = "aborted"
STATUS_PAUSED = "paused"

CHECKPOINT_RUNNING = "running"
CHECKPOINT_COMPLETE = "complete"
CHECKPOINT_FAILED = "failed"

STAGE_RAW_INPUT = "raw_input"
STAGE_SOURCE_CHUNKS = "source_chunks"
STAGE_RECALL = "recall"
STAGE_RECALL_VECTORS = "recall_vectors"
STAGE_SOURCE_VECTORS = "source_vectors"
STAGE_COMPLETE = "complete"
STAGE_ABORTED = "aborted"

STAGES = [
    STAGE_RAW_INPUT,
    STAGE_SOURCE_CHUNKS,
    STAGE_RECALL,
    STAGE_RECALL_VECTORS,
    STAGE_SOURCE_VECTORS,
    STAGE_COMPLETE,
    STAGE_ABORTED,
]

RETRY_LIMIT = 5
BACKOFF_SECONDS = [5, 15, 30, 60, 120]


class IngestJob(TypedDict):
    """Durable job row used by the private ingestion worker."""

    id: str
    content_hash: str
    raw_input_id: str | None
    status: str
    stage: str
    attempt_count: int
    next_run_at: str | None
    error: str | None
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


class Checkpoint(TypedDict):
    """Unit-level checkpoint row for resumable work."""

    job_id: str
    stage: str
    unit_key: str
    status: str
    output_ref: str | None
    error: str | None
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
