from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.services.rag.rag_service import get_rag_service
from src.routes.auth_utils import get_current_user_id

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    """Request body for raw text ingestion."""

    text: str = Field(..., min_length=1, description="The raw, messy conversational text to process.")


@router.post("/")
async def process_text(
    request: IngestRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Create or reuse a durable job and return immediately."""
    result = await get_rag_service().ingest(request.text, user_id, str(uuid4()))
    return {"status": "processing", "job_id": result["job_id"]}
