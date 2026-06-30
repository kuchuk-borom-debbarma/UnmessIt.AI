from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.repositories import dev, raw_inputs as raw_inputs_repo, source_chunks, source_chunk_vectors
from src.services.rag.rag_service import get_rag_service

router = APIRouter(prefix="/dev", tags=["dev"])
logger = logging.getLogger(__name__)


@router.get("/facts")
def get_facts() -> dict:
    """Compatibility alias for the active source chunk dev view."""
    return {"status": "success", **dev.memory_view()}


@router.get("/seai")
def get_seai() -> dict:
    """Return active raw inputs with nested source chunks."""
    # The list_with_raw_inputs repo method already filters deleted_at IS NULL
    return {"status": "success", **dev.memory_view()}


@router.get("/trash")
def get_trash() -> dict:
    """Return all soft-deleted raw inputs."""
    trashed = raw_inputs_repo.list_trash()
    return {"status": "success", "total_trash": len(trashed), "data": trashed}


@router.get("/raw_inputs/{input_id}")
def get_raw_input(input_id: str) -> dict:
    """Return one saved raw input, or 404 for unknown IDs."""
    raw_input = dev.raw_input(input_id)
    if not raw_input:
        raise HTTPException(status_code=404, detail="Raw input not found")
    return {"status": "success", "data": raw_input}


@router.delete("/raw_inputs/{input_id}")
def soft_delete_raw_input(input_id: str) -> dict:
    """Soft delete a raw input and remove its chunks from ChromaDB."""
    raw_input = raw_inputs_repo.get(input_id)
    if not raw_input:
        raise HTTPException(status_code=404, detail="Raw input not found")
    raw_inputs_repo.soft_delete(input_id)
    chunks = source_chunks.get_by_raw_input_id(input_id)
    if chunks:
        source_chunk_vectors.delete([c["id"] for c in chunks], raw_input["user_id"])
    return {"status": "success"}


@router.post("/raw_inputs/{input_id}/restore")
def restore_raw_input(input_id: str) -> dict:
    """Restore a soft-deleted raw input and re-index its chunks to ChromaDB."""
    raw_input = raw_inputs_repo.get(input_id)
    if not raw_input:
        raise HTTPException(status_code=404, detail="Raw input not found")
    raw_inputs_repo.restore(input_id)
    chunks = source_chunks.get_by_raw_input_id(input_id)
    if chunks:
        source_chunk_vectors.index(chunks)
    return {"status": "success"}


@router.delete("/raw_inputs/{input_id}/hard")
def hard_delete_raw_input(input_id: str) -> dict:
    """Permanently delete a raw input."""
    raw_input = raw_inputs_repo.get(input_id)
    if not raw_input:
        raise HTTPException(status_code=404, detail="Raw input not found")
    chunks = source_chunks.get_by_raw_input_id(input_id)
    if chunks:
        source_chunk_vectors.delete([c["id"] for c in chunks], raw_input["user_id"])
    raw_inputs_repo.hard_delete(input_id)
    return {"status": "success"}


@router.get("/recall")
def get_recall() -> dict:
    """Return recall keys with their evidence links."""
    return {"status": "success", **dev.recall_view()}


@router.get("/ingest_jobs")
def get_ingest_jobs(page: int = 1, limit: int = 20) -> dict:
    """Return paginated jobs across all users."""
    return {"status": "success", **get_rag_service().list_ingest_jobs(None, page, limit)}


@router.post("/ingest_jobs/{job_id}/resume")
async def resume_ingest_job(job_id: str) -> dict:
    """Manually resume one waiting, failed or paused durable ingestion job."""
    job = await get_rag_service().resume_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    return {"status": "success", "data": job}


@router.post("/ingest_jobs/{job_id}/pause")
def pause_ingest_job(job_id: str) -> dict:
    """Pause one durable ingestion job."""
    job = get_rag_service().pause_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    return {"status": "success", "data": job}


@router.post("/ingest_jobs/{job_id}/stop")
def stop_ingest_job(job_id: str) -> dict:
    """Stop one durable ingestion job."""
    job = get_rag_service().stop_ingest_job(job_id)
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
