from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from typing import Any

from src.infra import retrieval_cache
from src.infra.settings import get_user_embedding_settings
from src.repositories import recall, recall_key_vectors, retrieval_index, source_chunk_vectors, source_chunks

from ._state import QueryState
from ._sub_query_verifier import SemanticSubQueryVerifierChain

logger = logging.getLogger(__name__)

MAX_EVIDENCE_CHUNKS = 12
MAX_SNIPPETS_PER_CHUNK = 3
MAX_SNIPPET_CHARS = 420
_CONTEXT_CHARS_PER_PASS = 6000
_EVIDENCE_CACHE_VERSION = "evidence-search-v1"
_SEMANTIC_EVIDENCE_CACHE_VERSION = "evidence-semantic-candidates-v2"
_SEMANTIC_EVIDENCE_THRESHOLD = 0.85
_CONTEXT_COMPACTOR_CACHE_VERSION = "context-engineering-llm:v1"
_LLM_CONTEXT_MIN_RAW_CHARS = 9000
_LLM_CONTEXT_MAX_PACKED_CHARS = 4500

_ATTRIBUTE_TRIGGERS = {
    "appearance", "appearances", "attribute", "attributes", "body", "build",
    "characteristic", "characteristics", "count", "counts", "description",
    "described", "detail", "details", "face", "feature", "features", "look",
    "looks", "mark", "marks", "mole", "moles", "number", "numbers",
    "physical", "property", "properties", "quality", "qualities", "spec",
    "specs", "trait", "traits",
}
_ATTRIBUTE_EXPANSIONS = [
    "attribute", "attributes", "detail", "details", "descriptor",
    "descriptors", "label", "labels", "count", "counts", "number", "numbers",
    "feature", "features", "property", "properties", "measurement",
    "measurements", "appearance", "physical", "body", "face", "hair", "eyes",
    "eye", "skin", "height", "build", "scar", "scars", "mole", "moles",
    "mark", "marks", "birthmark", "birthmarks", "freckle", "freckles",
    "complexion", "tattoo", "tattoos", "piercing", "piercings",
]
_COMPARISON_TRIGGERS = {
    "compare", "comparison", "contrast", "contrasts", "different",
    "difference", "differences", "dissimilar", "dissimilarities", "parallel",
    "parallels", "same", "similar", "similarities", "similarity", "versus",
    "vs",
}
_COMPARISON_EXPANSIONS = [
    "attribute", "attributes", "context", "background", "behavior", "change",
    "changes", "goal", "goals", "constraint", "constraints", "relationship",
    "relationships", "decision", "decisions", "outcome", "outcomes",
    "parallels", "contrast",
]
_REASONING_TRIGGERS = {
    "cause", "causes", "changed", "changes", "developed", "development",
    "effect", "effects", "evolved", "evolution", "impact", "impacts",
    "reason", "reasons", "timeline", "why",
}
_REASONING_EXPANSIONS = [
    "evidence", "context", "background", "cause", "causes", "effect",
    "effects", "change", "changes", "outcome", "outcomes", "sequence",
    "before", "after", "because",
]


async def search_node(state: QueryState) -> dict[str, Any]:
    """LangGraph node: run evidence search for all sub-queries concurrently.

    asyncio.gather() fires each sub-query's vector+lexical+recall searches in
    parallel. For N sub-queries the wall-clock time is roughly one search pass
    instead of N sequential passes.
    """
    extracted_subjects = state.get("extracted_subjects") or []
    reporter = state.get("reporter")
    user_id = state.get("user_id")
    
    if not user_id:
        raise ValueError("user_id is required in QueryState for multi-tenant search")
    
    if reporter:
        await reporter.report(
            f"Starting concurrent search across {len(state['sub_queries'])} sub-query pass(es)...",
            {"depth": 1, "ref": "retrieval:search", "sub_query_count": len(state["sub_queries"])},
        )
        
    within_directories = state.get("within_directories") or []
    excluding_directories = state.get("excluding_directories") or []
    within_tags = state.get("within_tags") or []
    excluding_tags = state.get("excluding_tags") or []
    within_tags_condition = state.get("within_tags_condition", "any")
    index_version = await asyncio.to_thread(retrieval_index.get_version, user_id)
    embedding_signature = await asyncio.to_thread(_embedding_settings_signature, user_id)
    filters_signature = _filter_signature(
        within_directories,
        excluding_directories,
        within_tags,
        excluding_tags,
        within_tags_condition,
    )
    cache_key = _evidence_cache_key(
        state.get("query", ""),
        state["sub_queries"],
        extracted_subjects,
        user_id,
        index_version,
        embedding_signature,
        filters_signature,
    )
    cached = _valid_evidence_cache(await retrieval_cache.get_json(cache_key), index_version)
    if cached is not None:
        context_trace = _empty_context_engineering("cache")
        if reporter:
            await reporter.report(
                "Using cached evidence search results.",
                {
                    "depth": 1,
                    "ref": "retrieval:search:cache_hit",
                    "parent_ref": "retrieval:search",
                    "retrieval_index_version": index_version,
                    **context_trace,
                },
            )
        return {**cached, **context_trace, "cache_events": [{"stage": "evidence", "status": "hit"}]}
    cache_events = [{"stage": "evidence", "status": "miss"}]

    async def _search_and_report(index: int, sq: str):
        search_ref = f"retrieval:search:{index}"
        if reporter:
            await reporter.report(
                f"Sub-query {index}/{len(state['sub_queries'])}: searching focused evidence.",
                {"depth": 2, "ref": search_ref, "parent_ref": "retrieval:search", "sub_query": sq},
            )
        res = await _evidence_for(
            sq,
            state.get("query", ""),
            user_id,
            extracted_subjects,
            within_directories,
            excluding_directories,
            within_tags,
            excluding_tags,
            within_tags_condition,
            index_version,
            embedding_signature,
            filters_signature,
            state.get("json_client"),
            reporter,
            search_ref,
        )
        if reporter:
            chunks, trace = res
            await reporter.report(
                f"Sub-query {index}/{len(state['sub_queries'])}: engineered {len(chunks)} evidence chunk(s)",
                {"depth": 2, "ref": f"{search_ref}:done", "parent_ref": search_ref, **{k: v for k, v in trace.items() if k != "baseline_lengths"}},
            )
        return res
        
    results = await asyncio.gather(*[_search_and_report(index + 1, sq) for index, sq in enumerate(state["sub_queries"])])
    
    all_chunks: list[dict[str, Any]] = []
    trace_parts: list[dict[str, Any]] = []
    for chunks, trace_part in results:
        all_chunks.extend(chunks)
        cache_events.extend(trace_part.pop("cache_events", []))
        trace_parts.append(trace_part)
    context_trace = _aggregate_context_engineering(trace_parts)
        
    await retrieval_cache.set_json(cache_key, {
        "cache_version": _EVIDENCE_CACHE_VERSION,
        "retrieval_index_version": index_version,
        "chunks": all_chunks,
        "trace_parts": trace_parts,
    })
    cache_events.append({"stage": "evidence", "status": "set"})
    return {"chunks": all_chunks, "trace_parts": trace_parts, "cache_events": cache_events, **context_trace}


def finalize_chunks(raw_chunks: list[dict[str, Any]], query: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Dedup and re-rank accumulated chunks from all sub-query passes.

    Called by QueryEvidenceChain after the graph completes; not a graph node itself
    because it needs the full merged set before trimming to MAX_EVIDENCE_CHUNKS.
    This is pure CPU — no I/O — so it does not need to be async.
    """
    seen: dict[str, dict[str, Any]] = {}
    for chunk in raw_chunks:
        seen.setdefault(chunk["id"], chunk)
    deduped = list(seen.values())

    ranked, score_trace = _rank_chunks(query, deduped)
    ranked = ranked[:MAX_EVIDENCE_CHUNKS]
    selected_score_trace = {chunk["id"]: score_trace.get(chunk["id"], []) for chunk in ranked}
    selected_snippet_counts = {chunk["id"]: len(chunk.get("_snippets") or []) for chunk in ranked}
    return ranked, {"selected_snippet_counts": selected_snippet_counts, "chunk_score_reasons": selected_score_trace}


# ── internal helpers ─────────────────────────────────────────────────────────


def _evidence_cache_key(
    query: str,
    sub_queries: list[str],
    subjects: list[str],
    user_id: str,
    index_version: int,
    embedding_signature: str,
    filters_signature: dict[str, Any],
) -> str:
    return retrieval_cache.cache_key(
        "evidence_search",
        _EVIDENCE_CACHE_VERSION,
        user_id,
        query,
        sub_queries,
        subjects,
        index_version,
        embedding_signature,
        filters_signature,
    )


def _valid_evidence_cache(value: dict[str, Any] | None, index_version: int) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if value.get("cache_version") != _EVIDENCE_CACHE_VERSION:
        return None
    if value.get("retrieval_index_version") != index_version:
        return None
    chunks = value.get("chunks")
    trace_parts = value.get("trace_parts")
    if not isinstance(chunks, list) or not isinstance(trace_parts, list):
        return None
    if any(not isinstance(chunk, dict) or not chunk.get("id") for chunk in chunks):
        return None
    if any(not isinstance(trace, dict) for trace in trace_parts):
        return None
    return {"chunks": chunks, "trace_parts": trace_parts}


def _embedding_settings_signature(user_id: str) -> str:
    try:
        settings = get_user_embedding_settings(user_id, "retrieval.vector_search")
    except Exception:
        return "embedding-settings:none"
    return "|".join([
        settings.embedding_provider,
        settings.embedding_model,
        settings.embedding_base_url or "",
        str(settings.chunk_size),
        str(settings.chunk_overlap),
        str(settings.embedding_batch_size),
    ])


def _stable_list(values: list[str]) -> list[str]:
    return sorted({str(value) for value in values if str(value)})


def _filter_signature(
    within_directories: list[str],
    excluding_directories: list[str],
    within_tags: list[str],
    excluding_tags: list[str],
    within_tags_condition: str,
) -> dict[str, Any]:
    return {
        "within_directories": _stable_list(within_directories),
        "excluding_directories": _stable_list(excluding_directories),
        "within_tags": _stable_list(within_tags),
        "excluding_tags": _stable_list(excluding_tags),
        "within_tags_condition": within_tags_condition,
    }


async def _evidence_for(
    sub_query: str,
    global_query: str,
    user_id: str,
    extracted_subjects: list[str],
    within_directories: list[str],
    excluding_directories: list[str],
    within_tags: list[str],
    excluding_tags: list[str],
    within_tags_condition: str,
    index_version: int,
    embedding_signature: str,
    filters_signature: dict[str, Any],
    json_client=None,
    reporter=None,
    parent_ref: str = "retrieval:search",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run all three search paths for one sub-query concurrently where possible."""
    # 1. Check Sub-Query Semantic Cache First!
    semantic_chunks, semantic_trace, semantic_events = await _semantic_evidence_candidates(
        sub_query,
        extracted_subjects,
        user_id,
        index_version,
        embedding_signature,
        filters_signature,
        json_client,
        reporter,
        parent_ref,
    )
    if semantic_events and semantic_events[0]["status"] == "hit":
        trace_part = {
            "sub_query": sub_query,
            "extracted_subjects": extracted_subjects,
            **semantic_trace,
            "vector_source_chunk_ids": [],
            "lexical_source_chunk_count": 0,
            "recall_key_count": 0,
            "recall_keys": [],
            "linked_source_chunk_count": 0,
            "source_chunk_count": len(semantic_chunks),
            "baseline_lengths": {},
            "context_engineering": {
                "ran": False,
                "source": "semantic_cache",
                "raw_chars": 0,
                "packed_chars": sum(len(str(c.get("summary", ""))) + sum(len(s) for s in c.get("_snippets", [])) for c in semantic_chunks),
                "saved_chars": 0,
                "shrink_percent": 0.0,
                "chunk_count": len(semantic_chunks),
                "snippet_count": sum(len(c.get("_snippets", [])) for c in semantic_chunks),
            },
            "cache_events": semantic_events,
        }
        return semantic_chunks, trace_part

    # Vector search and lexical search can run in parallel; recall key lookup is cheap.
    async def _vector_path():
        if reporter:
            await reporter.report("Searching by topic meaning...", {"depth": 3, "ref": f"{parent_ref}:vector", "parent_ref": parent_ref, "sub_query": sub_query})
        chunks, ids = await _vector_source_chunks(sub_query, user_id, within_directories, excluding_directories, within_tags, excluding_tags, within_tags_condition, reporter, parent_ref)
        if reporter:
            await reporter.report(
                f"Topic meaning search returned {len(ids)} hit(s)",
                {"depth": 3, "ref": f"{parent_ref}:vector:done", "parent_ref": f"{parent_ref}:vector", "sub_query": sub_query, "source_chunk_ids": ids},
            )
        return chunks, ids

    async def _lexical_path():
        if reporter:
            await reporter.report("Searching by exact keywords...", {"depth": 3, "ref": f"{parent_ref}:lexical", "parent_ref": parent_ref, "sub_query": sub_query})
        chunks = await asyncio.to_thread(source_chunks.search, sub_query, user_id, 8, within_directories, excluding_directories, within_tags, excluding_tags, within_tags_condition)
        if reporter:
            await reporter.report(
                f"Exact keyword search returned {len(chunks)} hit(s)",
                {"depth": 3, "ref": f"{parent_ref}:lexical:done", "parent_ref": f"{parent_ref}:lexical", "sub_query": sub_query, "source_chunk_ids": [chunk["id"] for chunk in chunks]},
            )
        return chunks

    async def _recall_path():
        if reporter:
            await reporter.report("Following connected ideas...", {"depth": 3, "ref": f"{parent_ref}:recall", "parent_ref": parent_ref, "sub_query": sub_query})
        keys = await _recall_keys(sub_query, user_id, extracted_subjects)
        if reporter:
            await reporter.report(
                f"Connected ideas search returned {len(keys)} hit(s)",
                {"depth": 3, "ref": f"{parent_ref}:recall:done", "parent_ref": f"{parent_ref}:recall", "sub_query": sub_query, "recall_keys": [{"id": key["id"], "name": key["name"]} for key in keys]},
            )
        return keys

    (vector_chunks, vector_ids), lexical_chunks, recall_keys = await asyncio.gather(
        _vector_path(),
        _lexical_path(),
        _recall_path(),
    )
    if reporter:
        await reporter.report(
            f"Expanding {len(recall_keys)} recall key(s) into linked chunks",
            {"depth": 3, "ref": f"{parent_ref}:recall:expand", "parent_ref": f"{parent_ref}:recall", "sub_query": sub_query},
        )
    linked_ids = await asyncio.to_thread(recall.linked_source_chunk_ids, [key["id"] for key in recall_keys], user_id, 12, within_directories, excluding_directories, within_tags, excluding_tags, within_tags_condition)
    linked_chunks = await asyncio.to_thread(source_chunks.get_by_ids, linked_ids, user_id)
    if reporter:
        await reporter.report(
            f"Recall expansion returned {len(linked_chunks)} linked chunk(s)",
            {"depth": 3, "ref": f"{parent_ref}:recall:expand:done", "parent_ref": f"{parent_ref}:recall:expand", "sub_query": sub_query, "source_chunk_ids": linked_ids},
        )
        
    chunks, _ = _rank_chunks(sub_query, [*vector_chunks, *lexical_chunks, *linked_chunks])
    if reporter:
        await reporter.report(
            f"Ranked {len(chunks)} unique chunk(s) for sub-query",
            {"depth": 3, "ref": f"{parent_ref}:rank", "parent_ref": parent_ref, "sub_query": sub_query, "source_chunk_ids": [chunk["id"] for chunk in chunks[:MAX_EVIDENCE_CHUNKS]]},
        )
    
    top_chunks = chunks[:MAX_EVIDENCE_CHUNKS]
    baseline_lengths = {chunk["id"]: len(str(chunk.get("text", ""))) for chunk in top_chunks}
    
    chunks, pack_trace = await _pack_context(
        sub_query,
        top_chunks,
        user_id=user_id,
        json_client=json_client,
        reporter=reporter,
        parent_ref=parent_ref,
        budget=_CONTEXT_CHARS_PER_PASS,
    )
    context = pack_trace["context_engineering"]
    logger.info(
        "context_engineering source=%s raw_chars=%s packed_chars=%s saved_chars=%s chunks=%s",
        context["source"],
        context["raw_chars"],
        context["packed_chars"],
        context["saved_chars"],
        context["chunk_count"],
    )
    if reporter:
        await reporter.report(
            f"Engineered context: {context['raw_chars']} -> {context['packed_chars']} chars",
            {"depth": 3, "ref": f"{parent_ref}:context", "parent_ref": parent_ref, "sub_query": sub_query, **pack_trace},
        )

    context_cache_events = pack_trace.pop("cache_events", [])
    trace_part = {
        "sub_query": sub_query,
        "extracted_subjects": extracted_subjects,
        **semantic_trace,
        "vector_source_chunk_ids": vector_ids,
        "lexical_source_chunk_count": len(lexical_chunks),
        "recall_key_count": len(recall_keys),
        "recall_keys": [{"id": key["id"], "name": key["name"]} for key in recall_keys],
        "linked_source_chunk_count": len(linked_chunks),
        "source_chunk_count": len(chunks),
        "baseline_lengths": baseline_lengths,
        **pack_trace,
        "cache_events": [*semantic_events, *context_cache_events],
    }
    
    semantic_events.extend(await _set_semantic_evidence_candidates(
        sub_query,
        extracted_subjects,
        user_id,
        index_version,
        embedding_signature,
        filters_signature,
        chunks,
        bool(semantic_chunks),
        reporter,
        parent_ref,
    ))
    return chunks, trace_part


async def _semantic_evidence_candidates(
    sub_query: str,
    extracted_subjects: list[str],
    user_id: str,
    index_version: int,
    embedding_signature: str,
    filters_signature: dict[str, Any],
    json_client=None,
    reporter=None,
    parent_ref: str = "retrieval:search",
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    namespace = _semantic_evidence_namespace(user_id, index_version, embedding_signature, filters_signature)
    text = retrieval_cache.normalize_semantic_text(sub_query)
    if reporter:
        await reporter.report(
            "Checking similar previous evidence...",
            {"depth": 3, "ref": f"{parent_ref}:semantic", "parent_ref": parent_ref, "namespace": namespace},
        )
    match = await asyncio.to_thread(
        retrieval_cache.get_semantic_json_match,
        user_id,
        namespace,
        text,
        _SEMANTIC_EVIDENCE_THRESHOLD,
        False,
    )
    payload, distance = match if match else (None, None)
    packed_chunks, old_sub_query = _valid_semantic_evidence_payload(payload, index_version, embedding_signature, filters_signature)
    
    if packed_chunks and old_sub_query and json_client:
        # Skip LLM verifier for near-exact matches (same sub-query text reused).
        _EXACT_MATCH_EPSILON = 0.02
        if distance is not None and abs(distance) < _EXACT_MATCH_EPSILON:
            is_safe = True
        else:
            verifier = SemanticSubQueryVerifierChain(json_client)
            is_safe = await verifier.run(sub_query, old_sub_query, user_id, reporter)
        if is_safe:
            logger.info(
                "semantic_evidence_cache_hit namespace=%s distance=%s candidates=%s index_version=%s",
                namespace,
                distance,
                len(packed_chunks),
                index_version,
            )
            if reporter:
                await reporter.report(
                    f"Sub-query semantic cache hit! Reused {len(packed_chunks)} packed chunk(s).",
                    {
                        "depth": 3,
                        "ref": f"{parent_ref}:semantic:hit",
                        "parent_ref": f"{parent_ref}:semantic",
                        "namespace": namespace,
                        "distance": distance,
                        "source_chunk_ids": [chunk["id"] for chunk in packed_chunks],
                    },
                )
            return packed_chunks, {
                "semantic_cached_source_chunk_ids": [chunk["id"] for chunk in packed_chunks],
                "semantic_candidate_count": len(packed_chunks),
                "semantic_distance": distance,
            }, [{"stage": "evidence_semantic", "status": "hit"}]
            
    logger.info("semantic_evidence_cache_miss namespace=%s index_version=%s", namespace, index_version)
    if reporter:
        await reporter.report(
            "No safe similar evidence match.",
            {"depth": 3, "ref": f"{parent_ref}:semantic:miss", "parent_ref": f"{parent_ref}:semantic", "namespace": namespace},
        )
    return [], {"semantic_candidate_count": 0}, [{"stage": "evidence_semantic", "status": "miss"}]


async def _set_semantic_evidence_candidates(
    sub_query: str,
    extracted_subjects: list[str],
    user_id: str,
    index_version: int,
    embedding_signature: str,
    filters_signature: dict[str, Any],
    packed_chunks: list[dict[str, Any]],
    had_hit: bool,
    reporter=None,
    parent_ref: str = "retrieval:search",
) -> list[dict[str, Any]]:
    if had_hit or not packed_chunks:
        return []
    namespace = _semantic_evidence_namespace(user_id, index_version, embedding_signature, filters_signature)
    text = retrieval_cache.normalize_semantic_text(sub_query)
    payload = {
        "cache_version": _SEMANTIC_EVIDENCE_CACHE_VERSION,
        "retrieval_index_version": index_version,
        "embedding_signature": embedding_signature,
        "filters": filters_signature,
        "normalized_query": text,
        "sub_query": sub_query,
        "packed_chunks": packed_chunks,
    }
    await asyncio.to_thread(retrieval_cache.set_semantic_json, user_id, namespace, text, payload)
    logger.info(
        "semantic_evidence_cache_set namespace=%s candidates=%s index_version=%s",
        namespace,
        len(packed_chunks),
        index_version,
    )
    if reporter:
        await reporter.report(
            f"Saved {len(packed_chunks)} evidence candidate(s) for similar searches.",
            {
                "depth": 3,
                "ref": f"{parent_ref}:semantic:set",
                "parent_ref": f"{parent_ref}:semantic",
                "namespace": namespace,
                "source_chunk_ids": [chunk["id"] for chunk in packed_chunks],
            },
        )
    return [{"stage": "evidence_semantic", "status": "set"}]


def _semantic_evidence_namespace(
    user_id: str,
    index_version: int,
    embedding_signature: str,
    filters_signature: dict[str, Any],
) -> str:
    return retrieval_cache.semantic_namespace(
        _SEMANTIC_EVIDENCE_CACHE_VERSION,
        user_id,
        index_version,
        embedding_signature,
        filters_signature,
    )


def _valid_semantic_evidence_payload(
    value: dict[str, Any] | None,
    index_version: int,
    embedding_signature: str,
    filters_signature: dict[str, Any],
) -> tuple[list[dict[str, Any]], str | None]:
    if not isinstance(value, dict):
        return [], None
    if value.get("cache_version") != _SEMANTIC_EVIDENCE_CACHE_VERSION:
        return [], None
    if value.get("retrieval_index_version") != index_version:
        return [], None
    if value.get("embedding_signature") != embedding_signature:
        return [], None
    if value.get("filters") != filters_signature:
        return [], None
    packed_chunks = value.get("packed_chunks")
    old_sub_query = value.get("sub_query")
    if not isinstance(packed_chunks, list) or not isinstance(old_sub_query, str):
        return [], None
    return packed_chunks, old_sub_query

async def _vector_source_chunks(query: str, user_id: str, within_directories: list[str], excluding_directories: list[str], within_tags: list[str], excluding_tags: list[str], within_tags_condition: str, reporter=None, parent_ref: str = "retrieval:search") -> tuple[list[dict[str, Any]], list[str]]:
    """Use Chroma when available; lexical search still works if embeddings are down."""
    try:
        hits = await asyncio.to_thread(source_chunk_vectors.search, query, user_id, 8, within_directories, excluding_directories, within_tags, excluding_tags, within_tags_condition)
    except Exception as exc:
        logger.warning("query_source_vector_search_failed error=%s", exc)
        if reporter:
            await reporter.report(
                "Searching by topic meaning failed; continuing with exact keywords and connected ideas.",
                {"depth": 3, "ref": f"{parent_ref}:vector:error", "parent_ref": f"{parent_ref}:vector", "error": str(exc)[:500]},
            )
        return [], []
    ids = [hit["object_id"] for hit in hits if hit.get("object_type") == "source_chunk"]
    chunks = await asyncio.to_thread(source_chunks.get_by_ids, ids, user_id)
    return chunks, ids


async def _recall_keys(query: str, user_id: str, extracted_subjects: list[str]) -> list[dict[str, Any]]:
    """Find recall keys via three concurrent paths:

    1. FTS term search on the sub-query words.
    2. FTS name search on extracted subject names (handles diacritics via FTS5).
    3. Vector search — two concurrent queries:
       a. Full sub-query text (semantic context).
       b. Subject names joined as a compact string (direct entity embedding).
       Both run concurrently; results are merged.

    Path 2+3b handle queries that describe subjects by relationship rather than
    by explicit name — the subjects node extracts those names before search runs.
    """
    term_keys = await asyncio.to_thread(recall.find_candidate_keys, _expanded_terms(query), user_id, 8)
    all_keys = []
    
    # Direct FTS name lookup for implied subjects (Highest priority)
    # CRITICAL INSIGHT: If the LLM successfully resolved a description
    # into a specific entity name, we MUST put these keys at the
    # front of the list. Otherwise, they get pushed behind generic term matches like 
    # "Officer" or "Guards" and truncated by the [:8] cap at the end.
    if extracted_subjects:
        subject_keys = await asyncio.to_thread(recall.find_keys_by_names, extracted_subjects, user_id)
        all_keys.extend(subject_keys)
        
    try:
        # Run sub-query vector search and subject-name vector search concurrently.
        searches = [asyncio.to_thread(recall_key_vectors.search, query, user_id, 8)]
        if extracted_subjects:
            subject_query = " ".join(extracted_subjects)
            searches.append(asyncio.to_thread(recall_key_vectors.search, subject_query, user_id, 8))
        results = await asyncio.gather(*searches, return_exceptions=True)
        vector_ids: list[str] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("query_recall_vector_search_failed error=%s", result)
                continue
            vector_ids.extend(
                hit["object_id"] for hit in result if hit.get("object_type") == "recall_key"
            )
        if vector_ids:
            vector_keys = await asyncio.to_thread(recall.find_keys_by_ids, list(dict.fromkeys(vector_ids)), user_id)
            all_keys.extend(vector_keys)
    except Exception as exc:
        logger.warning("query_recall_vector_search_failed error=%s", exc)
            
    # Add generic term matches last (Lowest priority)
    all_keys.extend(term_keys)
    
    return _merge_keys(all_keys)[:8]



def _rank_chunks(
    query: str,
    chunks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Merge search paths and keep why each chunk was selected."""
    merged: dict[str, dict[str, Any]] = {}
    scores: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}
    
    # We must explicitly track how many times a chunk appears across the different search paths 
    # (vector, lexical, recall) to properly reward multiple-path discovery.
    # We cannot simply append to a reasons list inside the loop because the raw chunks list 
    # contains duplicates. If we processed duplicates sequentially, we would incorrectly 
    # multiply the exact-match lexical overlap score over and over again.
    appearances: dict[str, int] = {}

    terms = set(_expanded_terms(query))
    for chunk in chunks:
        chunk_id = chunk["id"]
        merged.setdefault(chunk_id, chunk)
        scores.setdefault(chunk_id, 0)
        reasons.setdefault(chunk_id, [])
        appearances.setdefault(chunk_id, 0)
        appearances[chunk_id] += 1

    for chunk_id, chunk in merged.items():
        text = f"{chunk.get('summary', '')} {chunk.get('text', '')}".lower()
        overlap = sum(1 for term in terms if term.lower() in text)
        if overlap:
            scores[chunk_id] += overlap
            reasons[chunk_id].append(f"query_terms:{overlap}")
            
        # Reward chunks that were discovered via multiple independent search strategies.
        # This gives a boost to chunks found by both vector + recall even if they have 0 exact lexical overlap.
        apps = appearances[chunk_id]
        if apps > 1:
            scores[chunk_id] += (apps - 1) * 5
            reasons[chunk_id].append(f"multiple_paths:{apps}")

    ranked_ids = sorted(merged, key=lambda cid: scores[cid], reverse=True)
    ranked = []
    for chunk_id in ranked_ids:
        chunk = dict(merged[chunk_id])
        chunk["_retrieval_score"] = scores[chunk_id]
        chunk["_retrieval_reasons"] = reasons[chunk_id]
        ranked.append(chunk)
    return ranked, reasons


async def _pack_context(
    query: str,
    chunks: list[dict[str, Any]],
    user_id: str | None = None,
    json_client=None,
    reporter=None,
    parent_ref: str = "retrieval:search",
    budget: int = _CONTEXT_CHARS_PER_PASS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Attach focused snippets so the answer prompt skips unrelated text."""
    before_chars = sum(len(str(chunk.get("text", ""))) for chunk in chunks)
    after_chars = 0
    snippet_counts: dict[str, int] = {}
    packed = []
    for chunk in chunks:
        next_chunk = dict(chunk)
        snippets = _snippets(query, str(chunk.get("text", "")), str(chunk.get("summary", "")))
        next_chunk["_snippets"] = snippets
        snippet_counts[chunk["id"]] = len(snippets)
        after_chars += len(str(chunk.get("summary", ""))) + sum(len(s) for s in snippets)
        packed.append(next_chunk)
        if after_chars >= budget:
            break

    source = "deterministic"
    cache_events: list[dict[str, str]] = []
    if _should_llm_compact(before_chars, after_chars, packed, json_client):
        cache_key = _context_compactor_cache_key(query, user_id, packed)
        cached = _valid_context_compactor_cache(await retrieval_cache.get_json(cache_key), packed) if cache_key else None
        if cached is not None:
            packed, after_chars, snippet_counts = _apply_compacted_snippets(packed, cached)
            source = "llm_cache"
            cache_events.append({"stage": "context_engineering", "status": "hit"})
            logger.info("context_engineering_cache_hit chunks=%s packed_chars=%s", len(packed), after_chars)
            if reporter:
                await reporter.report(
                    "Reusing previous context compression.",
                    {"depth": 3, "ref": f"{parent_ref}:context:cache_hit", "parent_ref": f"{parent_ref}:context", "chunk_count": len(packed), "packed_chars": after_chars},
                )
        else:
            if cache_key:
                cache_events.append({"stage": "context_engineering", "status": "miss"})
            compacted = await _llm_compact_context(query, packed, user_id or "", json_client, reporter, parent_ref)
            if compacted:
                packed, after_chars, snippet_counts = _apply_compacted_snippets(packed, compacted)
                source = "llm"
                if cache_key:
                    await retrieval_cache.set_json(cache_key, _context_compactor_payload(compacted))
                    cache_events.append({"stage": "context_engineering", "status": "set"})
                    logger.info("context_engineering_cache_set chunks=%s packed_chars=%s", len(packed), after_chars)
            elif cache_key:
                cache_events.append({"stage": "context_engineering", "status": "fallback"})
    elif reporter:
        await reporter.report(
            "Selected compact snippets without LLM compression.",
            {"depth": 3, "ref": f"{parent_ref}:context:deterministic", "parent_ref": f"{parent_ref}:context", "chunk_count": len(packed)},
        )

    saved_chars = max(before_chars - after_chars, 0)
    context = {
        "ran": True,
        "source": source,
        "raw_chars": before_chars,
        "packed_chars": after_chars,
        "saved_chars": saved_chars,
        "shrink_percent": _shrink_percent(before_chars, after_chars),
        "chunk_count": len(packed),
        "snippet_count": sum(snippet_counts.values()),
    }
    return packed, {
        "context_chars_before_packing": before_chars,
        "context_chars_after_packing": after_chars,
        "context_chars_saved": saved_chars,
        "context_engineering": context,
        "selected_snippet_counts": snippet_counts,
        "cache_events": cache_events,
    }


def _should_llm_compact(before_chars: int, after_chars: int, packed: list[dict[str, Any]], json_client) -> bool:
    if not json_client or not packed:
        return False
    if before_chars >= _LLM_CONTEXT_MIN_RAW_CHARS:
        return True
    return after_chars >= _LLM_CONTEXT_MAX_PACKED_CHARS


def _context_compactor_cache_key(query: str, user_id: str | None, chunks: list[dict[str, Any]]) -> str | None:
    signature = retrieval_cache.llm_settings_signature(user_id, "retrieval.context_engineering")
    if not signature:
        return None
    chunk_signature = [
        {
            "id": chunk.get("id"),
            "text_hash": hashlib.sha256(str(chunk.get("text", "")).encode("utf-8")).hexdigest(),
            "summary_hash": hashlib.sha256(str(chunk.get("summary", "")).encode("utf-8")).hexdigest(),
        }
        for chunk in chunks
    ]
    return retrieval_cache.cache_key(_CONTEXT_COMPACTOR_CACHE_VERSION, user_id or "", signature, query, chunk_signature)


async def _llm_compact_context(
    query: str,
    chunks: list[dict[str, Any]],
    user_id: str,
    json_client,
    reporter,
    parent_ref: str,
) -> dict[str, list[str]] | None:
    if reporter:
        await reporter.report(
            "Compressing large context with LLM.",
            {"depth": 3, "ref": f"{parent_ref}:context:llm", "parent_ref": f"{parent_ref}:context", "chunk_count": len(chunks)},
        )
    try:
        data = await json_client.async_invoke_json(
            system=_context_compactor_system_prompt(),
            human=_context_compactor_human_prompt(query, chunks),
            user_id=user_id,
            stage="retrieval.context_engineering",
        )
    except Exception as exc:
        logger.info("context_engineering_llm_fallback error=%s", str(exc)[:200])
        if reporter:
            await reporter.report(
                "Context compression unavailable; using deterministic snippets.",
                {"depth": 3, "ref": f"{parent_ref}:context:llm:fallback", "parent_ref": f"{parent_ref}:context:llm"},
            )
        return None
    compacted = _valid_context_compactor_cache(data, chunks)
    if not compacted:
        logger.info("context_engineering_llm_invalid chunks=%s", len(chunks))
        return None
    if reporter:
        await reporter.report(
            "Compressed context for verifier and answer.",
            {
                "depth": 3,
                "ref": f"{parent_ref}:context:llm:done",
                "parent_ref": f"{parent_ref}:context:llm",
                "chunk_count": len(compacted),
                "snippet_count": sum(len(snippets) for snippets in compacted.values()),
            },
        )
    return compacted


def _context_compactor_system_prompt() -> str:
    return (
        "Compress retrieved source chunks for verifier and answer prompts. "
        "Return only valid JSON. No markdown. "
        "Use only exact text copied from each SOURCE_CHUNK text or summary. "
        "Keep passages that directly help answer the query, including qualifiers, counts, dates, and contrasting details. "
        "Do not paraphrase, infer, add facts, or combine chunks. "
        "If a chunk has no useful passage, return an empty snippets list for that chunk."
    )


def _context_compactor_human_prompt(query: str, chunks: list[dict[str, Any]]) -> str:
    payload = [
        {
            "id": chunk["id"],
            "summary": str(chunk.get("summary", ""))[:1200],
            "text": str(chunk.get("text", ""))[:3500],
        }
        for chunk in chunks
    ]
    return (
        f"QUERY:\n{query}\n\n"
        f"SOURCE_CHUNKS:\n{json.dumps(payload, ensure_ascii=False)}\n\n"
        f"Return JSON: {{\"chunks\":[{{\"id\":\"source_chunk_id\",\"snippets\":[\"exact copied passage up to {MAX_SNIPPET_CHARS} chars\"]}}]}}"
    )


def _valid_context_compactor_cache(value: Any, chunks: list[dict[str, Any]]) -> dict[str, list[str]] | None:
    if not isinstance(value, dict) or not isinstance(value.get("chunks"), list):
        return None
    by_id = {str(chunk.get("id")): chunk for chunk in chunks}
    compacted: dict[str, list[str]] = {}
    for item in value["chunks"]:
        if not isinstance(item, dict):
            return None
        chunk_id = str(item.get("id") or "")
        if chunk_id not in by_id or not isinstance(item.get("snippets"), list):
            return None
        text = str(by_id[chunk_id].get("text", ""))
        summary = str(by_id[chunk_id].get("summary", ""))
        snippets = []
        for snippet in item["snippets"][:MAX_SNIPPETS_PER_CHUNK]:
            if not isinstance(snippet, str):
                return None
            clean = " ".join(snippet.strip().split())
            if not clean:
                continue
            if clean not in text and clean not in summary:
                continue
            snippets.append(clean[:MAX_SNIPPET_CHARS])
        compacted[chunk_id] = list(dict.fromkeys(snippets))
    return compacted if compacted else None


def _context_compactor_payload(compacted: dict[str, list[str]]) -> dict[str, Any]:
    return {"chunks": [{"id": chunk_id, "snippets": snippets} for chunk_id, snippets in compacted.items()]}


def _apply_compacted_snippets(
    packed: list[dict[str, Any]],
    compacted: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
    after_chars = 0
    snippet_counts: dict[str, int] = {}
    next_packed = []
    for chunk in packed:
        next_chunk = dict(chunk)
        snippets = compacted.get(str(chunk.get("id"))) or next_chunk.get("_snippets") or []
        next_chunk["_snippets"] = snippets
        snippet_counts[str(chunk["id"])] = len(snippets)
        after_chars += len(str(chunk.get("summary", ""))) + sum(len(str(snippet)) for snippet in snippets)
        next_packed.append(next_chunk)
    return next_packed, after_chars, snippet_counts


def _empty_context_engineering(source: str) -> dict[str, Any]:
    context = {
        "ran": False,
        "source": source,
        "raw_chars": 0,
        "packed_chars": 0,
        "saved_chars": 0,
        "shrink_percent": 0,
        "chunk_count": 0,
        "snippet_count": 0,
    }
    return {
        "context_engineering": context,
        "context_chars_before_packing": 0,
        "context_chars_after_packing": 0,
        "context_chars_saved": 0,
        "selected_snippet_counts": {},
    }


def _aggregate_context_engineering(trace_parts: list[dict[str, Any]]) -> dict[str, Any]:
    selected_snippet_counts: dict[str, int] = {}
    raw_chars = 0
    packed_chars = 0
    chunk_count = 0
    snippet_count = 0
    ran = False
    sources: set[str] = set()
    for trace in trace_parts:
        selected_snippet_counts.update(trace.get("selected_snippet_counts") or {})
        context = trace.get("context_engineering") or {}
        if not context.get("ran"):
            continue
        ran = True
        sources.add(str(context.get("source") or "deterministic"))
        raw_chars += int(context.get("raw_chars") or 0)
        packed_chars += int(context.get("packed_chars") or 0)
        chunk_count += int(context.get("chunk_count") or 0)
        snippet_count += int(context.get("snippet_count") or 0)
    if not ran:
        return _empty_context_engineering("cache")
    saved_chars = max(raw_chars - packed_chars, 0)
    context = {
        "ran": True,
        "source": sources.pop() if len(sources) == 1 else "mixed",
        "raw_chars": raw_chars,
        "packed_chars": packed_chars,
        "saved_chars": saved_chars,
        "shrink_percent": _shrink_percent(raw_chars, packed_chars),
        "chunk_count": chunk_count,
        "snippet_count": snippet_count,
    }
    return {
        "context_engineering": context,
        "context_chars_before_packing": raw_chars,
        "context_chars_after_packing": packed_chars,
        "context_chars_saved": saved_chars,
        "selected_snippet_counts": selected_snippet_counts,
    }


def _shrink_percent(before: int, after: int) -> int:
    if before <= 0:
        return 0
    return round(min(100, max(0, ((before - after) / before) * 100)))


def _snippets(query: str, text: str, summary: str) -> list[str]:
    """Pick small passages with query-term overlap; fall back to the start."""
    terms = {term.lower() for term in _expanded_terms(query)}
    passages = _passages(text)
    scored = []
    for index, passage in enumerate(passages):
        lowered = passage.lower()
        score = sum(1 for term in terms if term in lowered)
        if score:
            scored.append((score, index, passage))
    if not scored:
        fallback_passages = []
        if summary:
            fallback_passages.append(summary[:MAX_SNIPPET_CHARS])
        fallback_passages.extend(p[:MAX_SNIPPET_CHARS] for p in passages[:MAX_SNIPPETS_PER_CHUNK])
        return list(dict.fromkeys(item for item in fallback_passages if item))[:MAX_SNIPPETS_PER_CHUNK]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [_focused_snippet(passage, terms) for _, _, passage in scored[:MAX_SNIPPETS_PER_CHUNK]]


def _focused_snippet(passage: str, terms: set[str]) -> str:
    if len(passage) <= MAX_SNIPPET_CHARS:
        return passage
    lowered = passage.lower()
    indexes = [lowered.find(term) for term in terms if term and lowered.find(term) >= 0]
    if not indexes:
        return passage[:MAX_SNIPPET_CHARS]
    center = min(indexes)
    start = max(0, center - MAX_SNIPPET_CHARS // 3)
    end = start + MAX_SNIPPET_CHARS
    if end > len(passage):
        end = len(passage)
        start = max(0, end - MAX_SNIPPET_CHARS)
    prefix = "..." if start else ""
    suffix = "..." if end < len(passage) else ""
    return f"{prefix}{passage[start:end]}{suffix}"


def _passages(text: str) -> list[str]:
    """Split text into readable passages without pulling in another parser."""
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    if len(paragraphs) > 1:
        return paragraphs
    marker = "__LIST_DOT__"
    protected = re.sub(r"(?m)^(\s*\d+)\.\s+", rf"\1{marker} ", text)
    sentences = [item.replace(marker, ".").strip() for item in re.split(r"(?<=[.!?])\s+", protected) if item.strip()]
    return sentences or ([text.strip()] if text.strip() else [])


def _merge_keys(keys: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedupe recall keys before expanding to linked chunks."""
    merged: dict[str, dict[str, Any]] = {}
    for key in keys:
        merged.setdefault(key["id"], key)
    return list(merged.values())


def _terms(query: str) -> list[str]:
    """Extract simple lookup terms for exact and FTS recall-key search."""
    seen: set[str] = set()
    terms = []
    for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]*", query):
        lowered = word.lower()
        if len(word) >= 3 and lowered not in seen:
            seen.add(lowered)
            terms.append(word)
    return terms[:10]


def _expanded_terms(query: str) -> list[str]:
    """Add small, deterministic synonym sets for common underspecified asks."""
    terms = _terms(query)
    lowered = {term.lower() for term in terms}
    expansions: list[str] = []

    if lowered & _ATTRIBUTE_TRIGGERS:
        expansions.extend(_ATTRIBUTE_EXPANSIONS)

    if lowered & _COMPARISON_TRIGGERS:
        expansions.extend(_COMPARISON_EXPANSIONS)

    if lowered & _REASONING_TRIGGERS:
        expansions.extend(_REASONING_EXPANSIONS)

    seen = {term.lower() for term in terms}
    for term in expansions:
        if term.lower() not in seen:
            seen.add(term.lower())
            terms.append(term)
    return terms[:36]
