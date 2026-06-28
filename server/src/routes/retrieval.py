from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from src.services.rag.rag_service import get_rag_service

router = APIRouter(prefix="/api/retrieval", tags=["Retrieval"])


class QueryRequest(BaseModel):
    """Request body for the query endpoint."""

    query: str


@router.post("/query")
async def query_endpoint(request: QueryRequest) -> dict:
    """Return the current query response."""
    return get_rag_service().query(request.query)
