import asyncio
import logging

from kink import di

from src.ports.event_bus import EventBus
from src.services.ingest_engine.ports.inbound.ingestor import Ingestor

logger = logging.getLogger(__name__)

async def start_ingest_listener():
    """
    Background worker that listens for ingest requests and safely pushes 
    the heavy ML processing into an OS thread.
    """
    ingest_service = di[Ingestor]
    event_bus = di[EventBus]
    
    logger.info("ingest_listener_started topic=ingest_requests")
    
    try:
        async for message in event_bus.subscribe("ingest_requests"):
            text = message.get("text")
            job_id = message.get("job_id")
            if text:
                logger.info("ingest_listener_job_received job_id=%s", job_id)
                # Run the heavy synchronous ML pipeline in a background thread 
                # so the async listener isn't blocked from receiving new requests
                try:
                    await asyncio.to_thread(ingest_service.ingest, text, job_id)
                    logger.info("ingest_listener_job_finished job_id=%s", job_id)
                except Exception as exc:
                    logger.exception("ingest_listener_job_failed job_id=%s error=%s", job_id, exc)
    except asyncio.CancelledError:
        logger.info("ingest_listener_shutdown")
