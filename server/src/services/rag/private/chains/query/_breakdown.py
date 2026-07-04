from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.infra import retrieval_cache

from ._state import QueryState

logger = logging.getLogger(__name__)

_MAX_SUB_QUERIES = 6

_ATTRIBUTE_TERMS = {
    "appearance", "appearances", "attribute", "attributes", "body", "build",
    "characteristic", "characteristics", "count", "counts", "description",
    "described", "detail", "details", "face", "feature", "features", "look",
    "looks", "mark", "marks", "mole", "moles", "number", "numbers",
    "physical", "property", "properties", "quality", "qualities", "spec",
    "specs", "trait", "traits",
}
_COMPARISON_TERMS = {
    "compare", "comparison", "contrast", "contrasts", "different",
    "difference", "differences", "dissimilar", "dissimilarities", "parallel",
    "parallels", "same", "similar", "similarities", "similarity", "versus",
    "vs",
}
_REASONING_TERMS = {
    "cause", "causes", "changed", "changes", "developed", "development",
    "effect", "effects", "evolved", "evolution", "impact", "impacts",
    "reason", "reasons", "timeline", "why",
}
_QUESTION_STOPWORDS = {
    "about", "and", "are", "compare", "different", "does", "for", "how", "is",
    "me", "similar", "tell", "the", "to", "versus", "vs", "what", "who", "why",
}


def breakdown_node(json_client) -> callable:
    """Return a LangGraph node function that decomposes the query into sub-queries.

    Always keeps the original query as the first sub-query so simple queries
    pass through with a single search pass and no extra LLM latency cost.

    On any LLM failure, falls back to [query] so retrieval still runs.
    """

    async def _node(state: QueryState) -> dict[str, Any]:
        query = state["query"]
        reporter = state.get("reporter")
        user_id = state.get("user_id")
        
        if reporter:
            await reporter.report("Planning specific searches...", {"depth": 1, "ref": "retrieval:plan", "query_chars": len(query)})
        cache_events: list[dict[str, Any]] = []
        sub_queries = await _decompose(json_client, query, user_id, cache_events)
        logger.info("query_breakdown query_len=%s sub_queries=%s", len(query), len(sub_queries))
        
        if reporter:
            await reporter.report(
                f"Planned {len(sub_queries)} specific search(es).",
                {"depth": 1, "ref": "retrieval:plan:subqueries", "sub_queries": sub_queries},
            )
            
        return {"sub_queries": sub_queries, "cache_events": cache_events}

    return _node


async def _decompose(json_client, query: str, user_id: str, cache_events: list[dict[str, Any]] | None = None) -> list[str]:
    """Ask the LLM to break the query into focused sub-queries; fall back on failure."""
    system = _breakdown_system_prompt()
    human = _breakdown_human_prompt(query)
    cache_key = _breakdown_cache_key(query, user_id, system, human)
    if cache_key:
        cached = await retrieval_cache.get_json(cache_key)
        sub_queries = _cached_sub_queries(cached)
        if sub_queries:
            if cache_events is not None:
                cache_events.append({"stage": "breakdown", "status": "hit"})
            return sub_queries
        if cache_events is not None:
            cache_events.append({"stage": "breakdown", "status": "miss"})

    try:
        data = await json_client.async_invoke_json(
            system,
            human,
            user_id=user_id,
            stage="retrieval.query_breakdown",
        )
        sub_queries = data.get("sub_queries") if isinstance(data, dict) else None
        if not isinstance(sub_queries, list) or not sub_queries:
            return [query]
        cleaned = [str(q).strip() for q in sub_queries if str(q).strip()]
        deterministic = _deterministic_expansions(query)
        seen: set[str] = set()
        result = []
        for q in [query, *deterministic, *cleaned]:
            if q not in seen:
                seen.add(q)
                result.append(q)
        result = result[:_MAX_SUB_QUERIES]
        if cache_key:
            await retrieval_cache.set_json(cache_key, {"sub_queries": result})
            if cache_events is not None:
                cache_events.append({"stage": "breakdown", "status": "set"})
        return result
    except Exception as exc:
        logger.warning("query_breakdown_failed error=%s", exc)
        return [query]


def _breakdown_system_prompt() -> str:
    return (
        "Decompose the user query into focused sub-queries for evidence retrieval. "
        "Return only valid JSON. No markdown. "
        "Each sub-query must be self-contained and searchable on its own. "
        "Write sub-queries as deterministic embedding-friendly search phrases, not conversational questions. "
        "Normalize output: Use consistent phrasing (e.g. 'statements on X', 'details of Y'). "
        "Remove all filler words (e.g. 'tell me about', 'find', 'search for'). "
        "Lowercase all output except for proper nouns. "
        "Use stable nouns and qualifiers from the query; avoid pronouns, punctuation-only differences, and wording variation that does not change meaning. "
        "Include the original query as the first item. "
        f"Return at most {_MAX_SUB_QUERIES} sub-queries. "
        "For multi-part questions, include focused searches for each requested subject, scope, and comparison or reasoning dimension. "
        "For attribute questions, include specific detail searches for the requested subject and attribute family. "
        "Preserve query qualifiers such as source, time, place, folder, product, work, or domain so same-word matches from another context do not dominate. "
        "If the query is already simple and focused, return only the original query."
    )


def _breakdown_human_prompt(query: str) -> str:
    return (
        f"QUERY:\n{query}\n\n"
        f'Return JSON: {{"sub_queries":["original query","sub-query 1","sub-query 2"]}}'
    )


def _breakdown_cache_key(query: str, user_id: str | None, system: str, human: str) -> str | None:
    signature = retrieval_cache.llm_settings_signature(user_id, "retrieval.query_breakdown")
    if not signature:
        return None
    return retrieval_cache.cache_key("query_breakdown:v1", signature, system, human, query)





def _cached_sub_queries(value: dict[str, Any] | None) -> list[str] | None:
    if not isinstance(value, dict):
        return None
    items = value.get("sub_queries")
    if not isinstance(items, list) or not items:
        return None
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return cleaned[:_MAX_SUB_QUERIES] or None


def _deterministic_expansions(query: str) -> list[str]:
    """Add cheap intent-aware searches when the LLM under-plans broad questions."""
    terms = {term.lower() for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]*", query)}
    subjects = _named_subjects(query)
    expansions: list[str] = []

    expansions.extend(_multipart_expansions(query))

    if terms & _ATTRIBUTE_TERMS:
        if subjects:
            for subject in subjects[:3]:
                expansions.append(
                    f"{subject} appearance physical details visible features marks counts measurements"
                )
        else:
            expansions.append("appearance physical details visible features marks counts measurements")

    if terms & _COMPARISON_TERMS:
        for subject in subjects[:3]:
            expansions.append(
                f"{subject} attributes context behavior goals constraints changes outcomes relationships"
            )
        if len(subjects) >= 2:
            expansions.append(
                f"{subjects[0]} {subjects[1]} similarities differences parallels contrast attributes context changes goals outcomes"
            )
        else:
            expansions.append("similarities differences parallels contrast attributes context changes goals outcomes")

    if terms & _REASONING_TERMS:
        if subjects:
            for subject in subjects[:3]:
                expansions.append(
                    f"{subject} evidence context causes effects changes outcomes sequence"
                )
        else:
            expansions.append("evidence context causes effects changes outcomes sequence")

    return _dedupe(expansions)[: _MAX_SUB_QUERIES - 1]


def _multipart_expansions(query: str) -> list[str]:
    """Split broad enumerations into direct searches without knowing the domain."""
    if len(query) < 80:
        return []
    normalized = " ".join(query.split())
    pieces = [
        piece.strip(" .?!")
        for piece in re.split(r"\s*(?:,|;|\band\b|\bor\b)\s*", normalized, flags=re.IGNORECASE)
    ]
    pieces = [piece for piece in pieces if 12 <= len(piece) <= 160 and len(piece.split()) >= 2]
    if len(pieces) < 3:
        return []
    return [f"{piece} evidence context" for piece in pieces[: _MAX_SUB_QUERIES - 1]]


def _named_subjects(query: str) -> list[str]:
    """Pull obvious named subjects from the query without an LLM round trip."""
    subjects: list[str] = []
    for match in re.finditer(r"\b[A-Z][A-Za-z0-9'_-]*(?:\s+[A-Z][A-Za-z0-9'_-]*)*\b", query):
        subject = _clean_subject(match.group(0))
        if subject and subject.lower() not in _QUESTION_STOPWORDS:
            subjects.append(subject)
    return _dedupe(subjects)[:4]


def _clean_subject(subject: str) -> str:
    words = subject.strip().split()
    while words and words[0].lower().removesuffix("'s") in _QUESTION_STOPWORDS:
        words.pop(0)
    while words and words[-1].lower().removesuffix("'s") in _QUESTION_STOPWORDS:
        words.pop()
    cleaned = " ".join(words).strip().removesuffix("'s").removesuffix("'")
    return cleaned if len(cleaned) >= 3 else ""


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result
