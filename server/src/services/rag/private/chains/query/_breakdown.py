from __future__ import annotations

import logging
from typing import Any

from ._state import QueryState

logger = logging.getLogger(__name__)

_MAX_SUB_QUERIES = 4


def breakdown_node(json_client) -> callable:
    """Return a LangGraph node function that decomposes the query into sub-queries.

    Always keeps the original query as the first sub-query so simple queries
    pass through with a single search pass and no extra LLM latency cost.

    On any LLM failure, falls back to [query] so retrieval still runs.
    """

    def _node(state: QueryState) -> dict[str, Any]:
        query = state["query"]
        sub_queries = _decompose(json_client, query)
        logger.info("query_breakdown query_len=%s sub_queries=%s", len(query), len(sub_queries))
        return {"sub_queries": sub_queries}

    return _node


def _decompose(json_client, query: str) -> list[str]:
    """Ask the LLM to break the query into focused sub-queries; fall back on failure."""
    try:
        data = json_client.invoke_json(
            (
                "Decompose the user query into focused sub-queries for evidence retrieval. "
                "Return only valid JSON. No markdown. "
                "Each sub-query must be self-contained and searchable on its own. "
                "Include the original query as the first item. "
                f"Return at most {_MAX_SUB_QUERIES} sub-queries. "
                "If the query is already simple and focused, return only the original query."
            ),
            (
                f"QUERY:\n{query}\n\n"
                f'Return JSON: {{"sub_queries":["original query","sub-query 1","sub-query 2"]}}'
            ),
        )
        sub_queries = data.get("sub_queries") if isinstance(data, dict) else None
        if not isinstance(sub_queries, list) or not sub_queries:
            return [query]
        # Always anchor to original; dedupe; cap.
        cleaned = [str(q).strip() for q in sub_queries if str(q).strip()]
        seen: set[str] = set()
        result = []
        for q in [query, *cleaned]:
            if q not in seen:
                seen.add(q)
                result.append(q)
        return result[:_MAX_SUB_QUERIES]
    except Exception as exc:
        # ponytail: silent fallback keeps retrieval alive when breakdown LLM fails.
        logger.warning("query_breakdown_failed error=%s", exc)
        return [query]
