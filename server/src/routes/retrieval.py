from __future__ import annotations

import json
import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.routes.auth_utils import get_current_user_id
from src.repositories import tags

from src.infra.sse import get_sse_service
from src.services.rag.rag_service import get_rag_service
from src.services.rag.models import ProgressReporter

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """Request body for the query endpoint."""

    query: str
    client_id: str | None = None
    within_directories: list[str] | None = None
    excluding_directories: list[str] | None = None
    within_tags: list[str] | None = None
    excluding_tags: list[str] | None = None
    within_tags_condition: str = "any"  # "any" or "all"


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
        except Exception as exc:
            logger.warning("retrieval_sse_stream_failed client_id=%s error=%s", client_id, exc)

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
        _paths(request.within_directories), 
        _paths(request.excluding_directories),
        _tag_ids(request.within_tags, user_id),
        _tag_ids(request.excluding_tags, user_id),
        request.within_tags_condition
    )


def _paths(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    paths = []
    for value in values:
        path = str(value).strip()
        if path and path not in paths:
            paths.append(path if path.endswith("/") else f"{path}/")
    return paths or None


def _tag_ids(values: list[str] | None, user_id: str) -> list[str] | None:
    if not values:
        return None
    result = []
    for value in values:
        item = str(value).split("|", 1)[0].strip()
        tag = tags.get_by_name(item, user_id)
        tag_id = tag["id"] if tag else item
        if tag_id and tag_id not in result:
            result.append(tag_id)
    return result or None
