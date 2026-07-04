from __future__ import annotations

import json
import logging
from typing import Any

from src.services.rag.models import ProgressReporter

logger = logging.getLogger(__name__)


class SemanticCacheVerifierChain:
    """Judge whether a semantically similar cached query result fully answers a new query."""

    def __init__(self, json_client) -> None:
        self.json_client = json_client

    async def run(
        self,
        new_query: str,
        cached_query: str,
        cached_answer: str,
        user_id: str,
        reporter: ProgressReporter | None = None,
    ) -> bool:
        """Return True if the cached answer is safe to reuse for the new query."""
        if reporter:
            await reporter.report(
                "Verifying if past answer perfectly matches new question...",
                {"depth": 1, "ref": "retrieval:cache_lookup:verify"},
            )

        system = (
            "You are a strict safety verifier for a semantic cache. "
            "Your job is to determine if a cached answer (generated for an older query) "
            "completely and accurately answers a new user query.\n"
            "Return JSON with keys: {'is_safe': boolean, 'reason': string}\n"
            "Rules:\n"
            "1. If the new query introduces ANY new constraints (e.g. time, negative constraints, antonyms, different scope), return false.\n"
            "2. If the new query asks for differences, but the old query asked for similarities, return false.\n"
            "3. If the cached answer lacks specific details requested by the new query, return false.\n"
            "4. If the new query is just a rephrasing of the old query with the exact same intent and constraints, return true."
        )

        human = (
            f"OLD QUERY:\n{cached_query}\n\n"
            f"CACHED ANSWER:\n{cached_answer}\n\n"
            f"NEW QUERY:\n{new_query}\n\n"
            "Does the cached answer completely and accurately answer the new query without missing any constraints?"
        )

        try:
            data = await self.json_client.async_invoke_json(
                system=system,
                human=human,
                user_id=user_id,
                stage="retrieval.semantic_cache_verifier",
            )
        except Exception as exc:
            logger.warning("semantic_cache_verifier_failed error=%s", exc)
            if reporter:
                await reporter.report(
                    "Verification failed; falling back to full search.",
                    {"depth": 1, "ref": "retrieval:cache_lookup:verify:error", "error": str(exc)[:500]},
                )
            return False

        if not isinstance(data, dict):
            return False

        is_safe = bool(data.get("is_safe", False))
        reason = str(data.get("reason", ""))
        
        logger.info(
            "semantic_cache_verifier_result is_safe=%s reason=%s new_query=%s old_query=%s",
            is_safe,
            reason,
            new_query,
            cached_query,
        )
        
        if reporter:
            if is_safe:
                await reporter.report(
                    "Past answer verified! Reusing it to save time.",
                    {"depth": 1, "ref": "retrieval:cache_lookup:verify:safe", "reason": reason},
                )
            else:
                await reporter.report(
                    "Question has new constraints; starting fresh search.",
                    {"depth": 1, "ref": "retrieval:cache_lookup:verify:unsafe", "reason": reason},
                )

        return is_safe
