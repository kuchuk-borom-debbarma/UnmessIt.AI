from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.infra.events import get_event_bus
from src.infra.sse import get_sse_service
from src.repositories import raw_inputs

from . import repository

logger = logging.getLogger(__name__)

JOB_CHANGED_TOPIC = "ingest_job.changed"
JOB_PROGRESS_TOPIC = "ingest_job.progress"
_registered = False


def publish_job_changed(job_id: str) -> None:
    """Emit a durability domain event; delivery adapters subscribe elsewhere."""
    get_event_bus().publish(JOB_CHANGED_TOPIC, {"job_id": job_id})


def publish_job_progress(job_id: str, message: str) -> None:
    """Emit volatile job progress; not persisted."""
    get_event_bus().publish(JOB_PROGRESS_TOPIC, {"job_id": job_id, "message": message})


def register_ingest_job_sse_bridge() -> None:
    """Bridge ingest job changes to per-user SSE topics."""
    global _registered
    if _registered:
        return
    loop = asyncio.get_running_loop()

    def _handler(payload: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(_create_logged_task, _publish_job(payload), "ingest_job_changed")

    def _progress_handler(payload: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(_create_logged_task, _publish_progress(payload), "ingest_job_progress")

    get_event_bus().subscribe(JOB_CHANGED_TOPIC, _handler)
    get_event_bus().subscribe(JOB_PROGRESS_TOPIC, _progress_handler)
    _registered = True


async def _publish_job(payload: dict[str, Any]) -> None:
    job_id = str(payload.get("job_id") or "")
    if not job_id:
        return
    job = await asyncio.to_thread(repository.get, job_id)
    if not job or not job.get("raw_input_id"):
        return
    raw_input = await asyncio.to_thread(raw_inputs.get, job["raw_input_id"])
    user_id = (raw_input or {}).get("user_id")
    if not user_id:
        return
    await get_sse_service().publish(f"ingest_jobs:{user_id}", "job", {"job": job})
    logger.debug("ingest_job_sse job_id=%s user_id=%s status=%s", job_id, user_id, job["status"])


async def _publish_progress(payload: dict[str, Any]) -> None:
    job_id = str(payload.get("job_id") or "")
    message = str(payload.get("message") or "")
    if not job_id or not message:
        return
    job = await asyncio.to_thread(repository.get, job_id)
    if not job or not job.get("raw_input_id"):
        return
    raw_input = await asyncio.to_thread(raw_inputs.get, job["raw_input_id"])
    user_id = (raw_input or {}).get("user_id")
    if not user_id:
        return
    await get_sse_service().publish(
        f"ingest_jobs:{user_id}",
        "job_progress",
        {"job_id": job_id, "status": job["status"], "stage": job["stage"], "message": message},
    )


def _create_logged_task(coro, label: str) -> None:
    task = asyncio.create_task(coro)

    def _log_failure(done: asyncio.Task) -> None:
        try:
            done.result()
        except Exception as exc:
            logger.warning("ingest_sse_bridge_task_failed label=%s error=%s", label, exc)

    task.add_done_callback(_log_failure)
