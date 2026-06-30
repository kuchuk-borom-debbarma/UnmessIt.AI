from __future__ import annotations

from uuid import uuid4

from src.services.rag.models import SourceChunk, SourceChunkDraft, Span


class SourceChunkAssemblerChain:
    """Turn deterministic text windows into saved source chunk records."""

    async def run(self, raw_input_id: str, raw_text: str, user_id: str, drafts: list[SourceChunkDraft], directory_path: str | None = None) -> list[SourceChunk]:
        """Attach exact source positions and build final chunk dictionaries."""
        chunks = [_chunk_from_draft(raw_input_id, raw_text, user_id, draft, directory_path) for draft in drafts]
        return chunks or [_fallback_chunk(raw_input_id, raw_text, user_id, {"start": 0, "end": len(raw_text)}, directory_path)]


def _chunk_from_draft(raw_input_id: str, raw_text: str, user_id: str, draft: SourceChunkDraft, directory_path: str | None) -> SourceChunk:
    """Save the whole window so source chunks never lose raw input text."""
    window = draft["window"]
    span = {"start": window["start"], "end": window["end"]}
    text = raw_text[span["start"]:span["end"]]
    return {
        "id": str(uuid4()),
        "raw_input_id": raw_input_id,
        "text": text,
        "user_id": user_id,
        "summary": (draft["summary"] or _summary(text))[:240],
        "spans": [span],
        "source_time": draft["source_time"],
        "metadata": draft["metadata"],
        "directory_path": directory_path,
    }


def _fallback_chunk(raw_input_id: str, raw_text: str, user_id: str, span: Span, directory_path: str | None) -> SourceChunk:
    """Build one chunk directly from the full input text."""
    return {
        "id": str(uuid4()),
        "raw_input_id": raw_input_id,
        "text": raw_text,
        "user_id": user_id,
        "summary": _summary(raw_text),
        "spans": [span],
        "source_time": None,
        "metadata": {},
        "directory_path": directory_path,
    }


def _summary(text: str) -> str:
    """Build a short summary directly from source text."""
    return " ".join(text.split())[:240]
