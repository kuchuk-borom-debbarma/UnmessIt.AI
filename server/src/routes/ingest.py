from fastapi import APIRouter
from kink import di
from pydantic import BaseModel, Field
import uuid

from src.ports.event_bus import EventBus

router = APIRouter(prefix="/ingest", tags=["ingest"])

class IngestRequest(BaseModel):
    text: str = Field(..., min_length=1, description="The raw, messy conversational text to process.")

@router.post("/")
async def process_text(request: IngestRequest):
    """
    Publish the raw text to the event bus and return instantly.
    The background listener will pick it up and run the heavy ML pipeline.
    """
    job_id = str(uuid.uuid4())

    await di[EventBus].publish("ingest_requests", {"job_id": job_id, "text": request.text})
    
    return {
        "status": "processing",
        "job_id": job_id
    }
