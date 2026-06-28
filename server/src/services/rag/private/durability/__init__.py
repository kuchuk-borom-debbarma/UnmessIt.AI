from __future__ import annotations

import hashlib
import logging

from src.repositories import raw_inputs
from . import repository
from .runner import DurableIngestRunner
from .scheduler import DurableScheduler

logger = logging.getLogger(__name__)


class DurableIngest:
    """Private durability layer used by the RAG service.

    RAG owns the product flow and chains. This layer owns durable submission,
    idempotency, checkpoints, retries, and resume.
    """

    def __init__(self, preprocessor, source_windows, source_chunk_drafts, source_chunk_assembler, recall_index) -> None:
        self.preprocessor = preprocessor
        self.runner = DurableIngestRunner(source_windows, source_chunk_drafts, source_chunk_assembler, recall_index)
        self.scheduler = DurableScheduler(self.runner)

    def submit(self, text: str, requested_job_id: str) -> dict:
        """Create/reuse a durable job and schedule it in the background."""
        raw_text = self.preprocessor.run(text)
        content_hash = _hash(raw_text)
        raw_input_id = raw_inputs.save_or_reuse(requested_job_id, raw_text, content_hash)
        job = repository.create_or_reuse_job(requested_job_id, content_hash, raw_input_id)
        repository.set_raw_input(job["id"], raw_input_id)
        response_job = repository.get(job["id"]) or {**job, "raw_input_id": raw_input_id}
        logger.info(
            "ingest_job_submitted job_id=%s raw_input_id=%s status=%s stage=%s",
            job["id"],
            raw_input_id,
            job["status"],
            job["stage"],
        )
        # Start background work after preparing the HTTP response data.
        self.scheduler.schedule(job["id"])
        return response_job

    def resume_pending(self) -> None:
        """Resume queued/running/due retry jobs on server startup."""
        self.scheduler.resume_pending()

    def resume_job(self, job_id: str) -> dict | None:
        """Manually resume a job from the dev route."""
        return self.scheduler.resume_job(job_id)

    def list_jobs(self) -> list[dict]:
        """Return durable jobs for dev inspection."""
        return repository.list_jobs()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
