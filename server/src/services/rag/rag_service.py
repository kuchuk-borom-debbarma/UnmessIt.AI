from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from src.infra.langchain_json import get_json_client
from src.services.rag.models import IngestResult, QueryResult
from src.services.rag.private.rag_service_impl import RagServiceImpl


class RagService(Protocol):
    """Methods exposed to HTTP routes."""

    async def ingest(self, data: str, job_id: str | None = None) -> IngestResult:
        ...

    async def query(self, data: str) -> QueryResult:
        ...

    async def resume_pending_jobs(self) -> None:
        ...

    async def resume_ingest_job(self, job_id: str) -> dict | None:
        ...

    def list_ingest_jobs(self) -> list[dict]:
        ...

    def delete_ingest_job(self, job_id: str) -> bool:
        ...


@lru_cache(maxsize=1)
def get_rag_service() -> RagService:
    """Build and cache the RAG service with its chain dependencies."""
    json_client = get_json_client()
    return RagServiceImpl(json_client)
