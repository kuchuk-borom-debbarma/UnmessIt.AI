from __future__ import annotations

import json
import logging
from typing import Any

from src.services.rag.models import SourceChunk

logger = logging.getLogger(__name__)


class RecallDraftChain:
    """Ask the LLM which names/topics matter and which chunks mention them."""

    def __init__(self, json_client) -> None:
        """Keep the JSON client at the chain boundary."""
        self.json_client = json_client

    async def run(
        self,
        source_chunks: list[SourceChunk],
        candidates: list[dict[str, Any]],
        user_id: str,
        errors: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return raw LLM output before code validates IDs and duplicate links."""
        repair = ""
        if errors:
            repair = "The previous response failed validation. Fix these errors:\n" + "\n".join(f"- {error}" for error in errors[:8]) + "\n\n"
        logger.info(
            "recall_draft_request chunks=%s candidates=%s retry=%s",
            len(source_chunks),
            len(candidates),
            bool(errors),
        )
        data = await self.json_client.async_invoke_json(
            (
                "Create recall keys and recall links for source chunks. Return only valid JSON. No markdown.\n"
                "Use SOURCE_CHUNKS as source evidence. EXISTING_CANDIDATES are reuse hints, not source evidence.\n"
                "Reuse existing_recall_key_id only when the candidate clearly matches. Create a new key only when no candidate clearly matches.\n"
                "For reused keys, keep the candidate's identity broad: write summary as a stable merged orientation using the old candidate summary plus this new source evidence.\n"
                "If the old summary is already good, repeat it instead of narrowing it to the latest chunk.\n"
                "Canonical names must be clean, human-readable, and language-consistent; avoid mixed-script names unless the source itself uses them.\n"
                "Prefer reusable keys a user may ask about later. Avoid tiny phrase-specific topic keys when a broader candidate fits.\n"
                "Aim for 1-5 important recall keys per source chunk."
            ),
            (
                f"{repair}"
                "Return exactly this JSON shape, with no markdown:\n"
                "{\n"
                "  \"recall_keys\": [\n"
                "    {\"ref\":\"k1\",\"name\":\"canonical name\",\"kind\":\"entity|topic|event|task|question|other\","
                "\"kind_label\":\"optional specific label\",\"aliases\":[\"alternate name\"],\"summary\":\"short hint\"}\n"
                "  ],\n"
                "  \"recall_links\": [\n"
                "    {\"recall_key_ref\":\"k1\",\"source_chunk_id\":\"exact id from SOURCE_CHUNKS\","
                "\"relation\":\"mentions|about|updates|contradicts|supports|other\","
                "\"relation_label\":\"optional specific relation\",\"confidence\":0.8,\"reason\":\"short source-grounded reason\"}\n"
                "  ]\n"
                "}\n"
                "Every recall key must have a non-empty ref like k1, k2, k3.\n"
                "Every recall link must use recall_key_ref that matches one recall key ref.\n"
                "Every source_chunk_id must be copied exactly from SOURCE_CHUNKS.\n"
                "Allowed kind: entity, topic, event, task, question, other.\n"
                "Allowed relation: mentions, about, updates, contradicts, supports, other.\n"
                "\n"
                f"EXISTING_CANDIDATES:\n{json.dumps(candidates[:12], ensure_ascii=False)}\n\n"
                f"SOURCE_CHUNKS:\n{json.dumps(_chunk_payload(source_chunks), ensure_ascii=False)}"
            ),
            user_id=user_id,
        )
        if not isinstance(data, dict):
            logger.info("recall_draft_response invalid_type=%s", type(data).__name__)
            return {}
        logger.info(
            "recall_draft_response keys=%s draft_keys=%s draft_links=%s",
            sorted(data.keys()),
            _list_count(data.get("recall_keys")),
            _list_count(data.get("recall_links")),
        )
        return data



def _chunk_payload(source_chunks: list[SourceChunk]) -> list[dict[str, Any]]:
    """Send only the fields needed to choose recall keys and links."""
    return [{"id": chunk["id"], "summary": chunk["summary"], "text_preview": chunk["text"][:500]} for chunk in source_chunks[:30]]


def _list_count(value: Any) -> int:
    """Count LLM list fields for logs without printing full model output."""
    return len(value) if isinstance(value, list) else 0
