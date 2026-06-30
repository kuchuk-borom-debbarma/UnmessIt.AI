from __future__ import annotations

import logging
from typing import Any

from ._state import QueryState

logger = logging.getLogger(__name__)

_MAX_SUBJECTS = 8


def subjects_node(json_client) -> callable:
    """Return a LangGraph node that extracts subjects the query refers to by description.

    The recall key term search only works when the query contains explicit names.
    This node asks the LLM to surface any subjects implied by description so the
    search node can look them up directly in the recall key index.

    Falls back to empty list on any failure so retrieval always continues.
    Domain-neutral: the prompt uses general words (subject, concept, topic) and
    does not assume any schema, genre, or domain.
    """

    async def _node(state: QueryState) -> dict[str, Any]:
        query = state["query"]
        sub_queries = state.get("sub_queries", [])
        user_id = state.get("user_id")
        reporter = state.get("reporter")
        
        if reporter:
            await reporter.report("Extracting implicit subjects from query...")
            
        subjects = await _identify_subjects(json_client, query, sub_queries, user_id)
        logger.info("query_subjects query_len=%s extracted=%s", len(query), len(subjects))
        
        if reporter and subjects:
            await reporter.report(f"Found implicit subjects: {', '.join(subjects)}")
            
        return {"extracted_subjects": subjects}

    return _node


async def _identify_subjects(json_client, query: str, sub_queries: list[str], user_id: str | None) -> list[str]:
    """Ask the LLM for subjects the query refers to by description; fall back to [].

    CRITICAL INSIGHT:
    For multi-hop relational queries (e.g., "the man who helped the young officer"),
    generic lexical extraction only yields nouns ("man", "officer"). FTS search will 
    fail to match these to the actual entity keys ("Prince Vasili", "Boris").
    
    The only way to bridge this gap in a single-pass graph is to explicitly ask the LLM
    to use its general knowledge to resolve descriptions into specific proper names.
    If the LLM knows the subject, it returns the exact name, allowing the downstream
    FTS to perfectly hit the recall keys for those entities.
    """
    try:
        data = await json_client.async_invoke_json(
            (
                "Identify the specific named entities (people, characters, places, items, concepts) that the query refers to by description rather than by explicit name. "
                "Use your general knowledge to resolve the descriptions into specific proper names whenever possible. "
                "If the query describes a subject (e.g., 'the man who...', 'the young officer', 'the company'), figure out who or what it is and return their exact name. "
                "Return only valid JSON. No markdown. "
                f"Return at most {_MAX_SUBJECTS} subjects. "
                "If every subject is already stated by explicit proper name in the query, return []."
            ),
            (
                f"QUERY:\n{query}\n\n"
                + (f"SUB_QUERIES:\n{sub_queries}\n\n" if sub_queries else "")
                + 'Return JSON: {"subjects": ["subject name 1", "subject name 2"]}'
            ),
            user_id=user_id,
        )
        subjects = data.get("subjects") if isinstance(data, dict) else None
        if not isinstance(subjects, list):
            return []
        cleaned = [str(s).strip() for s in subjects if str(s).strip()]
        return cleaned[:_MAX_SUBJECTS]
    except Exception as exc:
        # ponytail: silent fallback — retrieval always runs even if extraction fails.
        logger.warning("query_subjects_failed error=%s", exc)
        return []
