from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from src.repositories import dev, raw_inputs, source_chunk_vectors, source_chunks
from src.repositories import recall as recall_repo
from src.routes.auth_utils import get_current_user_id
from src.services.auth import get_auth_service
from src.infra.sse import get_sse_service
from src.services.rag.rag_service import get_rag_service

router = APIRouter(prefix="/api/advanced", tags=["advanced"])


@router.get("/memory")
async def memory(user_id: str = Depends(get_current_user_id)) -> dict:
    return {"status": "success", **dev.memory_view(user_id)}


@router.get("/recall")
async def recall(user_id: str = Depends(get_current_user_id)) -> dict:
    return {"status": "success", **dev.recall_view(user_id)}


@router.get("/notes/{note_id}/chunks")
async def get_note_chunks(
    note_id: str,
    page: int = 1,
    limit: int = 10,
    user_id: str = Depends(get_current_user_id)
) -> dict:
    page = max(1, page)
    limit = max(1, min(limit, 50))
    result = source_chunks.get_paginated_for_note(note_id, user_id, page, limit)
    return {"status": "success", **result}


@router.get("/notes/{note_id}/recall_keys")
async def get_note_recall_keys(
    note_id: str,
    page: int = 1,
    limit: int = 10,
    user_id: str = Depends(get_current_user_id)
) -> dict:
    page = max(1, page)
    limit = max(1, min(limit, 50))
    result = recall_repo.get_paginated_keys_for_note(note_id, user_id, page, limit)
    return {"status": "success", **result}


@router.get("/notes/{note_id}/recall_links")
async def get_note_recall_links(
    note_id: str,
    page: int = 1,
    limit: int = 10,
    user_id: str = Depends(get_current_user_id)
) -> dict:
    page = max(1, page)
    limit = max(1, min(limit, 50))
    result = recall_repo.get_paginated_links_for_note(note_id, user_id, page, limit)
    return {"status": "success", **result}


@router.get("/raw_inputs/{input_id}")
async def raw_input(input_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    row = raw_inputs.get(input_id)
    if not row or row.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Raw input not found")
    return {"status": "success", "data": row}


@router.delete("/raw_inputs/{input_id}/hard")
async def hard_delete_raw_input(input_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    row = raw_inputs.get(input_id)
    if not row or row.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Raw input not found")
    chunks = source_chunks.get_by_raw_input_id(input_id)
    if chunks:
        source_chunk_vectors.delete([chunk["id"] for chunk in chunks], user_id)
    raw_inputs.hard_delete(input_id)
    return {"status": "success"}


@router.get("/ingest_jobs")
async def ingest_jobs(
    page: int = 1,
    limit: int = 20,
    _user_id: str = Depends(get_current_user_id)
) -> dict:
    return {"status": "success", **get_rag_service().list_ingest_jobs(_user_id, page, limit)}


@router.get("/ingest_jobs/events")
async def ingest_job_events(request: Request, token: str | None = None) -> StreamingResponse:
    """Stream current-user ingest job changes."""
    bearer = request.headers.get("authorization", "")
    auth_token = token or (bearer[7:] if bearer.lower().startswith("bearer ") else "")
    user = get_auth_service().verify_token(auth_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    async def event_generator():
        try:
            async for event in get_sse_service().subscribe(f"ingest_jobs:{user['id']}"):
                if await request.is_disconnected():
                    break
                yield f"event: {event.event}\ndata: {json.dumps(event.data)}\n\n"
        except Exception:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/ingest_jobs/{job_id}/resume")
async def resume_ingest_job(job_id: str, _user_id: str = Depends(get_current_user_id)) -> dict:
    if job_id not in {job["id"] for job in get_rag_service().list_ingest_jobs(_user_id, limit=1000)["data"]}:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    job = await get_rag_service().resume_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    return {"status": "success", "data": job}


@router.post("/ingest_jobs/{job_id}/pause")
async def pause_ingest_job(job_id: str, _user_id: str = Depends(get_current_user_id)) -> dict:
    if job_id not in {job["id"] for job in get_rag_service().list_ingest_jobs(_user_id, limit=1000)["data"]}:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    job = get_rag_service().pause_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    return {"status": "success", "data": job}


@router.post("/ingest_jobs/{job_id}/stop")
async def stop_ingest_job(job_id: str, _user_id: str = Depends(get_current_user_id)) -> dict:
    if job_id not in {job["id"] for job in get_rag_service().list_ingest_jobs(_user_id, limit=1000)["data"]}:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    job = get_rag_service().stop_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    return {"status": "success", "data": job}


@router.delete("/ingest_jobs/{job_id}")
async def delete_ingest_job(job_id: str, _user_id: str = Depends(get_current_user_id)) -> dict:
    if job_id not in {job["id"] for job in get_rag_service().list_ingest_jobs(_user_id, limit=1000)["data"]}:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    if not get_rag_service().delete_ingest_job(job_id):
        raise HTTPException(status_code=404, detail="Ingest job not found")
    return {"status": "success"}
