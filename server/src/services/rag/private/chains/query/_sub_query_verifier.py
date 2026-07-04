from __future__ import annotations

import logging
from typing import Any

from src.services.rag.models import ProgressReporter

logger = logging.getLogger(__name__)


class SemanticSubQueryVerifierChain:
    """Fast judge to determine if a past sub-query is a safe semantic match for a new sub-query.
    
    Since sub-queries only retrieve chunks and do not have text answers, we only need to compare
    the new sub-query with the old sub-query to ensure constraints haven't fundamentally changed.
    """

    def __init__(self, json_client) -> None:
        self.json_client = json_client

    async def run(
        self,
        new_sub_query: str,
        cached_sub_query: str,
        user_id: str,
        reporter: ProgressReporter | None = None,
    ) -> bool:
        """Return True if the cached sub-query is safe to reuse for the new sub-query."""
        if reporter:
            await reporter.report(
                "Verifying sub-query semantic match...",
                {"depth": 3, "ref": "retrieval:search:semantic:verify"},
            )

        system = (
            "You are a strict safety verifier for a sub-query semantic cache. "
            "Your job is to determine if a cached sub-query (used previously to retrieve evidence) "
            "is perfectly safe to reuse for a NEW sub-query.\n"
            "Return JSON with keys: {'is_safe': boolean, 'reason': string}\n"
            "Rules:\n"
            "1. If the new sub-query introduces ANY new constraints (e.g. time, negative constraints, antonyms, different scope), return false.\n"
            "2. If the new sub-query asks for differences, but the old sub-query asked for similarities, return false.\n"
            "3. If the new sub-query is just a rephrasing of the old sub-query with the exact same intent and constraints, return true.\n"
            "4. If the old sub-query is BROADER than the new sub-query, return false (we might retrieve too much irrelevant evidence)."
        )

        human = (
            f"OLD SUB-QUERY:\n{cached_sub_query}\n\n"
            f"NEW SUB-QUERY:\n{new_sub_query}\n\n"
            "Are these two sub-queries semantically identical in intent and constraints?"
        )

        try:
            data = await self.json_client.async_invoke_json(
                system=system,
                human=human,
                user_id=user_id,
                stage="retrieval.sub_query_verifier",
            )
        except Exception as exc:
            logger.warning("sub_query_verifier_failed error=%s", exc)
            if reporter:
                await reporter.report(
                    "Sub-query verification failed; running full search.",
                    {"depth": 3, "ref": "retrieval:search:semantic:verify:error", "error": str(exc)[:500]},
                )
            return False

        if not isinstance(data, dict):
            return False

        is_safe = bool(data.get("is_safe", False))
        reason = str(data.get("reason", ""))
        
        logger.info(
            "sub_query_verifier_result is_safe=%s reason=%s new_sub_query=%s old_sub_query=%s",
            is_safe,
            reason,
            new_sub_query,
            cached_sub_query,
        )
        if reporter:
            await reporter.report(
                "Reusing past search results." if is_safe else "Sub-query constraints differ; running full search.",
                {
                    "depth": 3,
                    "ref": "retrieval:search:semantic:verify:done",
                    "is_safe": is_safe,
                    "reason": reason,
                },
            )

        return is_safe
