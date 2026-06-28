from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone

from . import repository
from .models import STATUS_ABORTED, STATUS_COMPLETE, STATUS_FAILED, STATUS_WAITING_RETRY

logger = logging.getLogger(__name__)


class DurableScheduler:
    """Run durable jobs in background threads without duplicate in-process runs."""

    def __init__(self, runner) -> None:
        self.runner = runner
        self._running: set[str] = set()
        self._lock = threading.Lock()

    def schedule(self, job_id: str) -> None:
        """Start or keep one background worker for the job."""
        with self._lock:
            if job_id in self._running:
                return
            self._running.add(job_id)
        thread = threading.Thread(target=self._run_loop, args=(job_id,), daemon=True)
        thread.start()

    def resume_pending(self) -> None:
        """Resume queued/running/due retry jobs after server startup."""
        jobs = repository.list_resumable_jobs()
        for job in jobs:
            logger.info("ingest_job_startup_resume job_id=%s status=%s stage=%s", job["id"], job["status"], job["stage"])
            self.schedule(job["id"])

    def resume_job(self, job_id: str) -> dict | None:
        """Manually resume a waiting or failed job."""
        job = repository.get(job_id)
        if not job:
            return None
        if job["status"] == STATUS_ABORTED:
            return job
        repository.resume(job_id)
        logger.info("ingest_job_manual_resume job_id=%s", job_id)
        self.schedule(job_id)
        return repository.get(job_id)

    def _run_loop(self, job_id: str) -> None:
        try:
            while True:
                job = repository.get(job_id)
                if not job or job["status"] in {STATUS_COMPLETE, STATUS_FAILED, STATUS_ABORTED}:
                    return
                if job["status"] == STATUS_WAITING_RETRY:
                    delay = _delay_seconds(job["next_run_at"])
                    if delay > 0:
                        time.sleep(delay)
                try:
                    self.runner.run_once(job_id)
                except Exception:
                    job = repository.get(job_id)
                    if not job or job["status"] == STATUS_FAILED:
                        return
                    continue
        finally:
            with self._lock:
                self._running.discard(job_id)


def _delay_seconds(next_run_at: str | None) -> float:
    if not next_run_at:
        return 0
    try:
        target = datetime.fromisoformat(next_run_at)
    except ValueError:
        return 0
    return max(0.0, (target - datetime.now(timezone.utc)).total_seconds())
