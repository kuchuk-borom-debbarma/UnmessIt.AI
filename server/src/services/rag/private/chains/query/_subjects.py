from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from src.infra import retrieval_cache
from src.infra.settings import get_user_embedding_settings

from ._breakdown import _llm_settings_signature
from ._state import QueryState

logger = logging.getLogger(__name__)

_MAX_SUBJECTS = 8
_PROMPT_VERSION = "query_subjects:v1"


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
            await reporter.report("Looking up specific named topics...", {"depth": 1, "ref": "retrieval:subjects"})
            
        subjects = await _identify_subjects(json_client, query, sub_queries, user_id)
        logger.info("query_subjects query_len=%s extracted=%s", len(query), len(subjects))
        
        if reporter:
            await reporter.report(
                f"Found specific named topics: {', '.join(subjects)}" if subjects else "No specific named topics found.",
                {"depth": 1, "ref": "retrieval:subjects:done", "subjects": subjects},
            )
            
        return {"extracted_subjects": subjects}

    return _node


async def _identify_subjects(json_client, query: str, sub_queries: list[str], user_id: str | None) -> list[str]:
    """Ask the LLM for subjects the query refers to by description; fall back to [].

    CRITICAL INSIGHT:
    For multi-hop relational queries that describe a subject indirectly, generic
    lexical extraction only yields broad nouns. FTS search can then miss the
    actual recall key name.
    
    The only way to bridge this gap in a single-pass graph is to explicitly ask the LLM
    to use its general knowledge to resolve descriptions into specific proper names.
    If the LLM knows the subject, it returns the exact name, allowing the downstream
    FTS to perfectly hit the recall keys for those entities.
    """
    system = _subjects_system_prompt()
    human = _subjects_human_prompt(query, sub_queries)
    exact_key = _subjects_exact_cache_key(query, sub_queries, user_id, system, human)
    if exact_key:
        cached = _cached_subjects(await retrieval_cache.get_json(exact_key))
        if cached is not None:
            return cached

    semantic_key = _subjects_semantic_cache_key(query, sub_queries, user_id, system)
    if semantic_key:
        namespace, text = semantic_key
        cached = _cached_subjects(await asyncio.to_thread(retrieval_cache.get_semantic_json, user_id or "", namespace, text))
        if cached is not None:
            return cached

    try:
        data = await json_client.async_invoke_json(system, human, user_id=user_id)
        subjects = data.get("subjects") if isinstance(data, dict) else None
        if not isinstance(subjects, list):
            return []
        cleaned = [str(s).strip() for s in subjects if str(s).strip()]
        result = cleaned[:_MAX_SUBJECTS]
        payload = {"subjects": result}
        if exact_key:
            await retrieval_cache.set_json(exact_key, payload)
        if semantic_key:
            namespace, text = semantic_key
            await asyncio.to_thread(
                retrieval_cache.set_semantic_json,
                user_id or "",
                namespace,
                text,
                {
                    **payload,
                    "query": query,
                    "sub_queries": sub_queries,
                    "normalized_query": text,
                    "prompt_version": _PROMPT_VERSION,
                },
            )
        return result
    except Exception as exc:
        logger.warning("query_subjects_failed error=%s", exc)
        return []


def _subjects_system_prompt() -> str:
    return (
        "Identify specific named subjects that the query refers to by description rather than by explicit name. "
        "Use your general knowledge to resolve the descriptions into specific proper names whenever possible. "
        "Subjects can be entities, documents, works, events, concepts, systems, objects, places, organizations, or people. "
        "If the query describes a subject indirectly, return the most likely exact name. "
        "Return only valid JSON. No markdown. "
        f"Return at most {_MAX_SUBJECTS} subjects. "
        "If every subject is already stated by explicit proper name in the query, return []."
    )


def _subjects_human_prompt(query: str, sub_queries: list[str]) -> str:
    return (
        f"QUERY:\n{query}\n\n"
        + (f"SUB_QUERIES:\n{sub_queries}\n\n" if sub_queries else "")
        + 'Return JSON: {"subjects": ["subject name 1", "subject name 2"]}'
    )


def _subjects_exact_cache_key(query: str, sub_queries: list[str], user_id: str | None, system: str, human: str) -> str | None:
    signature = _llm_settings_signature(user_id)
    if not signature:
        return None
    return retrieval_cache.cache_key(_PROMPT_VERSION, user_id or "", signature, system, human, query, sub_queries)


def _subjects_semantic_cache_key(query: str, sub_queries: list[str], user_id: str | None, system: str) -> tuple[str, str] | None:
    llm_signature = _llm_settings_signature(user_id)
    embedding_signature = _embedding_settings_signature(user_id)
    if not llm_signature or not embedding_signature:
        return None
    namespace = retrieval_cache.semantic_namespace(_PROMPT_VERSION, user_id or "", llm_signature, embedding_signature, system)
    text = retrieval_cache.normalize_semantic_text(query, sub_queries)
    return (namespace, text) if text else None


def _embedding_settings_signature(user_id: str | None) -> str | None:
    try:
        settings = get_user_embedding_settings(user_id or "")
    except Exception:
        return None
    safe = {
        "provider": settings.embedding_provider,
        "model": settings.embedding_model,
        "base_url": settings.embedding_base_url,
    }
    return json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _cached_subjects(value: dict[str, Any] | None) -> list[str] | None:
    if not isinstance(value, dict):
        return None
    subjects = value.get("subjects")
    if not isinstance(subjects, list):
        return None
    return [str(item).strip() for item in subjects if str(item).strip()][:_MAX_SUBJECTS]
