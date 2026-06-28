from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from . import repository
from .models import STATUS_ABORTED, STATUS_COMPLETE, STATUS_FAILED, STATUS_WAITING_RETRY

logger = logging.getLogger(__name__)


class DurableScheduler:
    """Run durable jobs as asyncio tasks without duplicate in-process runs.

    asyncio.create_task() replaces threading.Thread. All I/O in the task loop
    uses await so the event loop stays free between SQLite/LLM calls.
    """

    def __init__(self, runner) -> None:
        self.runner = runner
        self._running: set[str] = set()

    async def schedule(self, job_id: str) -> None:
        """Start or keep one background task for the job."""
        if job_id in self._running:
            return
        self._running.add(job_id)
        asyncio.create_task(self._run_loop(job_id), name=f"ingest-{job_id[:8]}")

    async def resume_pending(self) -> None:
        """Resume queued/running/due retry jobs after server startup."""
        jobs = await asyncio.to_thread(repository.list_resumable_jobs)
        for job in jobs:
            logger.info("ingest_job_startup_resume job_id=%s status=%s stage=%s", job["id"], job["status"], job["stage"])
            await self.schedule(job["id"])

    async def resume_job(self, job_id: str) -> dict | None:
        """Manually resume a waiting or failed job."""
        job = await asyncio.to_thread(repository.get, job_id)
        if not job:
            return None
        if job["status"] == STATUS_ABORTED:
            return job
        await asyncio.to_thread(repository.resume, job_id)
        logger.info("ingest_job_manual_resume job_id=%s", job_id)
        await self.schedule(job_id)
        return await asyncio.to_thread(repository.get, job_id)

    async def _run_loop(self, job_id: str) -> None:
        try:
            while True:
                job = await asyncio.to_thread(repository.get, job_id)
                if not job or job["status"] in {STATUS_COMPLETE, STATUS_FAILED, STATUS_ABORTED}:
                    return
                if job["status"] == STATUS_WAITING_RETRY:
                    delay = _delay_seconds(job["next_run_at"])
                    if delay > 0:
                        await asyncio.sleep(delay)
                try:
                    await self.runner.run_once(job_id)
                except Exception:
                    job = await asyncio.to_thread(repository.get, job_id)
                    if not job or job["status"] == STATUS_FAILED:
                        return
                    continue
        finally:
            self._running.discard(job_id)


def _delay_seconds(next_run_at: str | None) -> float:
    if not next_run_at:
        return 0
    try:
        target = datetime.fromisoformat(next_run_at)
    except ValueError:
        return 0
    return max(0.0, (target - datetime.now(timezone.utc)).total_seconds())
