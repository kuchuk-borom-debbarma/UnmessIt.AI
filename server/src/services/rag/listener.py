from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.infra.events import get_event_bus
from src.services.rag.rag_service import get_rag_service

logger = logging.getLogger(__name__)


async def _handle_note_created(payload: dict[str, Any]) -> None:
    note_id = payload["note_id"]
    text = payload["text"]
    user_id = payload["user_id"]
    
    try:
        await get_rag_service().ingest(text, user_id, note_id)
        logger.info(f"Triggered RAG ingest for new note {note_id}")
    except Exception as e:
        logger.error(f"Failed to trigger RAG ingest for new note {note_id}: {e}")


async def _handle_note_updated(payload: dict[str, Any]) -> None:
    note_id = payload["note_id"]
    text = payload["text"]
    user_id = payload["user_id"]
    
    try:
        # Since ingest uses job_id = note_id, it will reuse or restart the job for this note
        await get_rag_service().ingest(text, user_id, note_id)
        logger.info(f"Triggered RAG ingest for updated note {note_id}")
    except Exception as e:
        logger.error(f"Failed to trigger RAG ingest for updated note {note_id}: {e}")


def _on_note_created(payload: dict[str, Any]) -> None:
    asyncio.create_task(_handle_note_created(payload))


def _on_note_updated(payload: dict[str, Any]) -> None:
    asyncio.create_task(_handle_note_updated(payload))


def register_rag_listeners() -> None:
    bus = get_event_bus()
    bus.subscribe("note.created", _on_note_created)
    bus.subscribe("note.updated", _on_note_updated)
