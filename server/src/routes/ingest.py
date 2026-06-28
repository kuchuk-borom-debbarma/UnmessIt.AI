from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.services.rag.rag_service import get_rag_service

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    """Request body for raw text ingestion."""

    text: str = Field(..., min_length=1, description="The raw, messy conversational text to process.")


@router.post("/")
async def process_text(request: IngestRequest) -> dict:
    """Create or reuse a durable job and return immediately."""
    result = await get_rag_service().ingest(request.text, str(uuid4()))
    return {"status": "processing", "job_id": result["job_id"]}
