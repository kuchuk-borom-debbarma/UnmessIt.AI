from __future__ import annotations

import logging
from typing import Any

from src.infra import retrieval_cache
from src.services.rag.models import SourceChunkDraft, SourceWindow

logger = logging.getLogger(__name__)


class SourceChunkDraftChain:
    """Ask the LLM to summarize one already-bounded text piece."""

    def __init__(self, json_client) -> None:
        """Keep the JSON client at the chain boundary."""
        self.json_client = json_client

    async def run(self, window: SourceWindow, user_id: str) -> list[SourceChunkDraft]:
        """Return summary metadata while keeping source text selection deterministic."""
        llm_signature = retrieval_cache.llm_settings_signature(user_id)
        cache_key = retrieval_cache.cache_key("ingest_chunk_draft:v1", llm_signature, window["text"]) if llm_signature else None
        
        if cache_key:
            cached = await retrieval_cache.get_json(cache_key)
            if cached is not None:
                return [_draft(window, cached)]
                
        try:
            data = await self.json_client.async_invoke_json(
                "Summarize one source chunk and extract its main subjects. Return only JSON.",
                (
                    "Return JSON: {\"summary\":\"short neutral summary\",\"source_time\":null,\"metadata\":{\"salient_entities\":[\"Subject 1\",\"Subject 2\"]}}\n"
                    "Do not omit details because the full SOURCE_TEXT is saved as the citable chunk.\n"
                    "Extract 2-8 of the most important people, places, topics, or events into salient_entities to aid later retrieval.\n\n"
                    f"SOURCE_TEXT:\n{window['text']}"
                ),
                user_id=user_id,
            )
            result = data if isinstance(data, dict) else {}
            if cache_key and isinstance(data, dict):
                await retrieval_cache.set_json(cache_key, result)
            return [_draft(window, result)]
        except Exception as exc:
            # Durable ingest should retry provider/auth outages instead of saving guessed chunks.
            logger.warning("source_chunk_draft_failed retryable=true error=%s", exc)
            raise



def _draft(window: SourceWindow, value: dict[str, Any]) -> SourceChunkDraft:
    """Normalize one LLM source chunk suggestion."""
    meta = value.get("metadata") if isinstance(value.get("metadata"), dict) else {}
    entities = meta.get("salient_entities") if isinstance(meta.get("salient_entities"), list) else []
    clean_entities = [str(e).strip() for e in entities if str(e).strip()]
    
    return {
        "window": window,
        "summary": str(value.get("summary") or "").strip(),
        "source_time": _optional_str(value.get("source_time")),
        "metadata": {**meta, "salient_entities": clean_entities[:20]},
    }


def _optional_str(value: Any) -> str | None:
    """Return short optional strings for stored metadata fields."""
    clean = str(value or "").strip()
    return clean[:160] if clean else None
