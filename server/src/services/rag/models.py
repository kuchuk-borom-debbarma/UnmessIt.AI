from __future__ import annotations

from typing import Any, Protocol, TypedDict


class ProgressReporter(Protocol):
    """Stateless reporter for streaming progress events."""
    
    async def report(self, message: str, details: dict[str, Any] | None = None) -> None:
        ...


class NullProgressReporter(ProgressReporter):
    """No-op reporter when no client is listening."""
    
    async def report(self, message: str, details: dict[str, Any] | None = None) -> None:
        pass


class Span(TypedDict):
    """Character offsets into the original raw input."""

    start: int
    end: int


class SourceChunk(TypedDict):
    """One citable evidence unit derived from raw input."""

    id: str
    raw_input_id: str
    text: str
    summary: str
    spans: list[Span]
    source_time: str | None
    user_id: str
    metadata: dict[str, object]


class SourceWindow(TypedDict):
    """A smaller piece of the input text with its original character positions."""

    text: str
    start: int
    end: int


class SourceChunkDraft(TypedDict):
    """LLM summary for one deterministic source window."""

    window: SourceWindow
    summary: str
    source_time: str | None
    metadata: dict[str, object]


class RecallIndex(TypedDict):
    """LLM-produced recall keys/links plus chain diagnostics."""

    recall_keys: list[dict[str, Any]]
    recall_links: list[dict[str, Any]]
    analysis: dict[str, Any]


class IngestResult(TypedDict):
    """Public result returned by `RagService.ingest()`."""

    job_id: str
    status: str
    raw_input_id: str
    source_chunks: list[SourceChunk]
    analysis: dict[str, Any]


class QueryResult(TypedDict):
    """Response returned by the query endpoint."""

    answer: str
    citations: list[dict[str, Any]]
    source_chunks: list[dict[str, Any]]
    retrieval_trace: dict[str, Any]
