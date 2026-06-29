from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.repositories import dev
from src.services.rag.rag_service import get_rag_service

router = APIRouter(prefix="/dev", tags=["dev"])
logger = logging.getLogger(__name__)


@router.get("/facts")
def get_facts() -> dict:
    """Compatibility alias for the active source chunk dev view."""
    return {"status": "success", **dev.memory_view()}


@router.get("/seai")
def get_seai() -> dict:
    """Return raw inputs with nested source chunks."""
    return {"status": "success", **dev.memory_view()}


@router.get("/raw_inputs/{input_id}")
def get_raw_input(input_id: str) -> dict:
    """Return one saved raw input, or 404 for unknown IDs."""
    raw_input = dev.raw_input(input_id)
    if not raw_input:
        raise HTTPException(status_code=404, detail="Raw input not found")
    return {"status": "success", "data": raw_input}


@router.get("/recall")
def get_recall() -> dict:
    """Return recall keys with their evidence links."""
    return {"status": "success", **dev.recall_view()}


@router.get("/ingest_jobs")
def get_ingest_jobs() -> dict:
    """Return durable ingestion jobs for dev inspection."""
    jobs = get_rag_service().list_ingest_jobs()
    return {"status": "success", "total_jobs": len(jobs), "data": jobs}


@router.post("/ingest_jobs/{job_id}/resume")
async def resume_ingest_job(job_id: str) -> dict:
    """Manually resume one waiting or failed durable ingestion job."""
    job = await get_rag_service().resume_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    return {"status": "success", "data": job}


@router.delete("/ingest_jobs/{job_id}")
def delete_ingest_job(job_id: str) -> dict:
    """Delete a specific durable ingestion job."""
    deleted = get_rag_service().delete_ingest_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    return {"status": "success"}


@router.delete("/facts")
def delete_all_facts() -> dict:
    """Clear local memory and its vector index for dev reset."""
    dev.wipe_all()
    return {"status": "success", "message": "All active ingestion data cleared successfully"}
