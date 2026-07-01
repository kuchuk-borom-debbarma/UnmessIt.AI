from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from functools import lru_cache
from uuid import uuid4

from src.infra.langchain_json import get_json_client
from src.services.rag.models import IngestResult
from src.services.rag.private.chains.preprocess import NoopPreprocessChain
from src.services.rag.private.chains.recall.index import RecallIndexChain
from src.services.rag.private.chains.source_chunk_assembler import SourceChunkAssemblerChain
from src.services.rag.private.chains.source_chunk_drafts import SourceChunkDraftChain
from src.services.rag.private.chains.source_windows import SourceWindowChain
from src.services.rag.private.durability import DurableIngest

logger = logging.getLogger(__name__)

_submit_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


@lru_cache(maxsize=1)
def get_durable_ingest() -> DurableIngest:
    """Build and cache the durable ingestion dependencies."""
    json_client = get_json_client()
    return DurableIngest(
        NoopPreprocessChain(),
        SourceWindowChain(),
        SourceChunkDraftChain(json_client),
        SourceChunkAssemblerChain(),
        RecallIndexChain(json_client),
    )


async def submit_ingest_job(data: str, user_id: str, job_id: str | None = None) -> IngestResult:
    """Submit durable ingestion and return the durable job result."""
    job_id = job_id or str(uuid4())
    lock = _submit_locks[job_id]
    
    async with lock:
        durability = get_durable_ingest()
        job = await durability.submit(data, user_id, job_id)
    return {
        "job_id": job["id"],
        "status": job["status"],
        "raw_input_id": job["raw_input_id"] or "",
        "source_chunks": [],
        "analysis": {
            "stage": job["stage"],
            "attempt_count": job["attempt_count"],
            "metadata": job["metadata"],
        },
    }
