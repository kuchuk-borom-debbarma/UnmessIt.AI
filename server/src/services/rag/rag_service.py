from __future__ import annotations

from functools import lru_cache
from typing import Protocol, Any

from src.infra.langchain_json import get_json_client
from src.services.rag.models import IngestResult, QueryResult, ProgressReporter
from src.services.rag.private.rag_service_impl import RagServiceImpl


class RagService(Protocol):
    """Methods exposed to HTTP routes."""

    async def query(self, data: str, user_id: str, reporter: ProgressReporter | None = None, within_directories: list[str] | None = None, excluding_directories: list[str] | None = None, within_tags: list[str] | None = None, excluding_tags: list[str] | None = None, within_tags_condition: str = "any") -> QueryResult:
        ...

    async def resume_pending_jobs(self) -> None:
        ...

    async def resume_ingest_job(self, job_id: str) -> dict | None:
        ...

    def list_ingest_jobs(self, user_id: str | None = None, page: int = 1, limit: int = 20) -> dict[str, Any]:
        ...

    def pause_ingest_job(self, job_id: str) -> dict | None:
        ...

    def stop_ingest_job(self, job_id: str) -> dict | None:
        ...

    def delete_ingest_job(self, job_id: str) -> bool:
        ...

    def reindex_all(self, user_id: str) -> None:
        ...

    def reindex_note(self, user_id: str, note_id: str) -> None:
        ...


@lru_cache(maxsize=1)
def get_rag_service_impl() -> RagServiceImpl:
    """Build and cache the internal RAG service implementation."""
    json_client = get_json_client()
    return RagServiceImpl(json_client)


def get_rag_service() -> RagService:
    """Return the public protocol for HTTP routes."""
    return get_rag_service_impl()
