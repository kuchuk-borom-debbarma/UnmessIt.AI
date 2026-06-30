from __future__ import annotations

import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.routes.auth_utils import get_current_user_id

from src.infra.sse import get_sse_service
from src.services.rag.rag_service import get_rag_service
from src.services.rag.models import ProgressReporter

router = APIRouter(prefix="/api/retrieval", tags=["Retrieval"])


class QueryRequest(BaseModel):
    """Request body for the query endpoint."""

    query: str
    client_id: str | None = None
    within_directories: list[str] | None = None
    excluding_directories: list[str] | None = None


class SseProgressReporter(ProgressReporter):
    """Bridges RAG logic to SSE infrastructure without leaking dependencies."""
    
    def __init__(self, sse_service, topic: str):
        self.sse = sse_service
        self.topic = topic

    async def report(self, message: str, details: dict | None = None) -> None:
        await self.sse.publish(self.topic, "progress", {
            "message": message,
            "details": details or {}
        })


@router.get("/events/{client_id}")
async def sse_events(client_id: str, request: Request) -> StreamingResponse:
    """Stream retrieval progress events to the frontend."""
    sse_service = get_sse_service()
    
    async def event_generator():
        try:
            async for event in sse_service.subscribe(f"retrieval:{client_id}"):
                if await request.is_disconnected():
                    break
                yield f"event: {event.event}\ndata: {json.dumps(event.data)}\n\n"
        except Exception:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/query")
async def query_endpoint(
    request: QueryRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Return the current query response."""
    reporter = None
    if request.client_id:
        reporter = SseProgressReporter(get_sse_service(), f"retrieval:{request.client_id}")
    return await get_rag_service().query(
        request.query, 
        user_id, 
        reporter, 
        request.within_directories, 
        request.excluding_directories
    )
