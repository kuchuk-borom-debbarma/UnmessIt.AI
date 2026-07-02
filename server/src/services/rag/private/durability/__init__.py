from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

from src.repositories import raw_inputs
from . import repository

logger = logging.getLogger(__name__)


class DurableIngest:
    """Private durability layer used by the RAG service.

    RAG owns the product flow and chains. This layer owns durable submission,
    idempotency, checkpoints, retries, and resume.
    """

    def __init__(self, preprocessor, source_windows, source_chunk_drafts, source_chunk_assembler, recall_index) -> None:
        from .runner import DurableIngestRunner
        from .scheduler import DurableScheduler

        self.preprocessor = preprocessor
        self.runner = DurableIngestRunner(source_windows, source_chunk_drafts, source_chunk_assembler, recall_index)
        self.scheduler = DurableScheduler(self.runner)

    async def submit(self, text: str, user_id: str, requested_job_id: str) -> dict:
        """Create/reuse a durable job and schedule it in the background."""
        raw_text = self.preprocessor.run(text)
        content_hash = _hash(user_id, raw_text)
        await asyncio.to_thread(_delete_changed_job, requested_job_id, user_id, content_hash)
        raw_input_id = await asyncio.to_thread(raw_inputs.save_or_reuse, requested_job_id, raw_text, user_id, content_hash)
        job = await asyncio.to_thread(repository.create_or_reuse_job, requested_job_id, content_hash, raw_input_id)
        await asyncio.to_thread(repository.set_raw_input, job["id"], raw_input_id)
        response_job = await asyncio.to_thread(repository.get, job["id"]) or {**job, "raw_input_id": raw_input_id}
        logger.info(
            "ingest_job_submitted job_id=%s raw_input_id=%s status=%s stage=%s",
            job["id"],
            raw_input_id,
            job["status"],
            job["stage"],
        )
        await self.scheduler.schedule(job["id"])
        return response_job

    async def resume_pending(self) -> None:
        """Resume queued/running/due retry jobs on server startup."""
        await self.scheduler.resume_pending()

    async def resume_job(self, job_id: str) -> dict | None:
        """Manually resume a job from the dev route."""
        return await self.scheduler.resume_job(job_id)

    def list_jobs(self, user_id: str | None = None, page: int = 1, limit: int = 20) -> dict[str, Any]:
        """Return durable jobs for dev inspection (sync: read-only, cheap)."""
        return repository.list_jobs(user_id, page, limit)

    def delete_job(self, job_id: str) -> bool:
        """Delete one durable job."""
        return repository.delete_job(job_id)


def _delete_changed_job(job_id: str, user_id: str, content_hash: str) -> None:
    """Replace stale derived data when a note is edited with new text."""
    from src.repositories import source_chunk_vectors, source_chunks

    job = repository.get(job_id)
    if not job or job["content_hash"] == content_hash:
        return
    for raw_input in raw_inputs.list_by_job(job_id, user_id):
        chunks = source_chunks.get_by_raw_input_id(raw_input["id"])
        if chunks:
            source_chunk_vectors.delete([chunk["id"] for chunk in chunks], user_id)
        raw_inputs.hard_delete(raw_input["id"])
    repository.delete_job(job_id)


def _hash(user_id: str, text: str) -> str:
    return hashlib.sha256(f"{user_id}\0{text}".encode("utf-8")).hexdigest()
