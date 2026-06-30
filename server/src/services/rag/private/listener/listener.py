from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.infra.events import get_event_bus
from src.services.rag.private.pipeline.ingest import submit_ingest_job

logger = logging.getLogger(__name__)


async def _handle_note_created(payload: dict[str, Any]) -> None:
    note_id = payload["note_id"]
    text = payload["text"]
    user_id = payload["user_id"]
    
    try:
        await submit_ingest_job(text, user_id, note_id)
        logger.info(f"Triggered RAG ingest for new note {note_id}")
    except Exception as e:
        logger.error(f"Failed to trigger RAG ingest for new note {note_id}: {e}")


async def _handle_note_updated(payload: dict[str, Any]) -> None:
    note_id = payload["note_id"]
    text = payload["text"]
    user_id = payload["user_id"]
    
    try:
        # Since ingest uses job_id = note_id, it will reuse or restart the job for this note
        await submit_ingest_job(text, user_id, note_id)
        logger.info(f"Triggered RAG ingest for updated note {note_id}")
    except Exception as e:
        logger.error(f"Failed to trigger RAG ingest for updated note {note_id}: {e}")


def _on_note_created(payload: dict[str, Any]) -> None:
    asyncio.create_task(_handle_note_created(payload))


def _on_note_updated(payload: dict[str, Any]) -> None:
    # Right now, simple approach: just re-submit the ingest job
    # Over time, we can make this more granular (e.g. diffing chunks)
    # The pipeline is idempotent if content hash matches.
    asyncio.create_task(submit_ingest_job(
        content=payload["text"],
        user_id=payload["user_id"],
        job_id=payload["note_id"]
    ))


async def _handle_note_moved(payload: dict[str, Any]) -> None:
    note_id = payload["note_id"]
    new_directory_id = payload["new_directory_id"]
    user_id = payload["user_id"]
    
    try:
        from src.repositories import directories, raw_inputs, source_chunks, source_chunk_vectors
        
        # 1. Resolve new materialized path
        new_path = None
        if new_directory_id:
            directory = await asyncio.to_thread(directories.get, new_directory_id, user_id)
            if directory:
                new_path = directory["path"]
                
        # 2. Get raw_input_id for the note
        inputs = await asyncio.to_thread(raw_inputs.list_by_job, note_id, user_id)
        for row in inputs:
            raw_input_id = row["id"]
            
            # 3. Update SQLite directory_path
            await asyncio.to_thread(source_chunks.update_directory_path, raw_input_id, new_path)
            
            # 4. Get chunks and update Chroma
            chunks = await asyncio.to_thread(source_chunks.get_by_raw_input_id, raw_input_id)
            if chunks:
                chunk_ids = [chunk["id"] for chunk in chunks]
                await asyncio.to_thread(source_chunk_vectors.update_metadata, chunk_ids, {"directory_path": new_path or ""}, user_id)
                
        logger.info(f"Updated directory path for moved note {note_id}")
    except Exception as e:
        logger.error(f"Failed to update directory path for moved note {note_id}: {e}")

def _on_note_moved(payload: dict[str, Any]) -> None:
    asyncio.create_task(_handle_note_moved(payload))


def _on_note_hard_deleted(payload: dict[str, Any]) -> None:
    note_id = payload["note_id"]
    user_id = payload["user_id"]
    
    def _cleanup():
        from src.repositories import raw_inputs, source_chunks, source_chunk_vectors
        inputs = raw_inputs.list_by_job(note_id, user_id)
        for row in inputs:
            input_id = row["id"]
            chunks = source_chunks.get_by_raw_input_id(input_id)
            if chunks:
                source_chunk_vectors.delete([chunk["id"] for chunk in chunks], user_id)
            raw_inputs.hard_delete(input_id)
            
    asyncio.create_task(asyncio.to_thread(_cleanup))


def register_rag_listeners() -> None:
    bus = get_event_bus()
    bus.subscribe("note.created", _on_note_created)
    bus.subscribe("note.updated", _on_note_updated)
    bus.subscribe("note.moved", _on_note_moved)
    bus.subscribe("note.hard_deleted", _on_note_hard_deleted)
