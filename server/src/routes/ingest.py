from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.routes.auth_utils import get_current_user_id
from src.services.rag.private.pipeline.ingest import submit_ingest_job

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    text: str = Field(..., min_length=1)


@router.post("/")
async def ingest(request: IngestRequest, user_id: str = Depends(get_current_user_id)) -> dict:
    return await submit_ingest_job(request.text, user_id)
