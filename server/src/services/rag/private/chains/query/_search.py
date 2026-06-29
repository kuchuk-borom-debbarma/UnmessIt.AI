from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from src.repositories import recall, recall_key_vectors, source_chunk_vectors, source_chunks

from ._state import QueryState

logger = logging.getLogger(__name__)

MAX_EVIDENCE_CHUNKS = 12
MAX_SNIPPETS_PER_CHUNK = 3
MAX_SNIPPET_CHARS = 420
_CONTEXT_CHARS_PER_PASS = 6000


async def search_node(state: QueryState) -> dict[str, Any]:
    """LangGraph node: run evidence search for all sub-queries concurrently.

    asyncio.gather() fires each sub-query's vector+lexical+recall searches in
    parallel. For N sub-queries the wall-clock time is roughly one search pass
    instead of N sequential passes.
    """
    extracted_subjects = state.get("extracted_subjects") or []
    results = await asyncio.gather(*[_evidence_for(sq, extracted_subjects) for sq in state["sub_queries"]])
    all_chunks: list[dict[str, Any]] = []
    trace_parts: list[dict[str, Any]] = []
    for chunks, trace_part in results:
        all_chunks.extend(chunks)
        trace_parts.append(trace_part)
    return {"chunks": all_chunks, "trace_parts": trace_parts}


def finalize_chunks(raw_chunks: list[dict[str, Any]], query: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Dedup, re-rank, and context-pack the accumulated chunks from all sub-query passes.

    Called by QueryEvidenceChain after the graph completes; not a graph node itself
    because it needs the full merged set before trimming to MAX_EVIDENCE_CHUNKS.
    This is pure CPU — no I/O — so it does not need to be async.
    """
    seen: dict[str, dict[str, Any]] = {}
    for chunk in raw_chunks:
        seen.setdefault(chunk["id"], chunk)
    deduped = list(seen.values())

    ranked, score_trace = _rank_chunks(query, deduped)
    ranked, context_trace = _pack_context(query, ranked[:MAX_EVIDENCE_CHUNKS])
    selected_score_trace = {chunk["id"]: score_trace.get(chunk["id"], []) for chunk in ranked}
    return ranked, {**context_trace, "chunk_score_reasons": selected_score_trace}


# ── internal helpers ─────────────────────────────────────────────────────────


async def _evidence_for(sub_query: str, extracted_subjects: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run all three search paths for one sub-query concurrently where possible."""
    # Vector search and lexical search can run in parallel; recall key lookup is cheap.
    (vector_chunks, vector_ids), lexical_chunks, recall_keys = await asyncio.gather(
        _vector_source_chunks(sub_query),
        asyncio.to_thread(source_chunks.search, sub_query, 8),
        _recall_keys(sub_query, extracted_subjects),
    )
    linked_ids = await asyncio.to_thread(recall.linked_source_chunk_ids, [key["id"] for key in recall_keys], 12)
    linked_chunks = await asyncio.to_thread(source_chunks.get_by_ids, linked_ids)

    chunks, _ = _rank_chunks(sub_query, [*vector_chunks, *lexical_chunks, *linked_chunks])
    chunks, _ = _pack_context(sub_query, chunks[:MAX_EVIDENCE_CHUNKS], budget=_CONTEXT_CHARS_PER_PASS)

    trace_part = {
        "sub_query": sub_query,
        "extracted_subjects": extracted_subjects,
        "vector_source_chunk_ids": vector_ids,
        "lexical_source_chunk_count": len(lexical_chunks),
        "recall_key_count": len(recall_keys),
        "recall_keys": [{"id": key["id"], "name": key["name"]} for key in recall_keys],
        "linked_source_chunk_count": len(linked_chunks),
        "source_chunk_count": len(chunks),
    }
    return chunks, trace_part


async def _vector_source_chunks(query: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Use Chroma when available; lexical search still works if embeddings are down."""
    try:
        hits = await asyncio.to_thread(source_chunk_vectors.search, query, 8)
    except Exception as exc:
        logger.warning("query_source_vector_search_failed error=%s", exc)
        return [], []
    ids = [hit["object_id"] for hit in hits if hit.get("object_type") == "source_chunk"]
    chunks = await asyncio.to_thread(source_chunks.get_by_ids, ids)
    return chunks, ids


async def _recall_keys(query: str, extracted_subjects: list[str]) -> list[dict[str, Any]]:
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
    term_keys = await asyncio.to_thread(recall.find_candidate_keys, _terms(query), 8)
    has_keys = await asyncio.to_thread(recall.has_keys)
    
    all_keys = []
    
    if has_keys:
        # Direct FTS name lookup for implied subjects (Highest priority)
        # CRITICAL INSIGHT: If the LLM successfully resolved a description (e.g. "the man") 
        # into a specific entity name ("Prince Vasili"), we MUST put these keys at the 
        # front of the list. Otherwise, they get pushed behind generic term matches like 
        # "Officer" or "Guards" and truncated by the [:8] cap at the end.
        if extracted_subjects:
            subject_keys = await asyncio.to_thread(recall.find_keys_by_names, extracted_subjects)
            all_keys.extend(subject_keys)
            
        try:
            # Run sub-query vector search and subject-name vector search concurrently.
            searches = [asyncio.to_thread(recall_key_vectors.search, query, 8)]
            if extracted_subjects:
                subject_query = " ".join(extracted_subjects)
                searches.append(asyncio.to_thread(recall_key_vectors.search, subject_query, 8))
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
                vector_keys = await asyncio.to_thread(recall.find_keys_by_ids, list(dict.fromkeys(vector_ids)))
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

    terms = set(_terms(query))
    for chunk in chunks:
        chunk_id = chunk["id"]
        merged.setdefault(chunk_id, chunk)
        scores.setdefault(chunk_id, 0)
        reasons.setdefault(chunk_id, [])

        text = f"{chunk.get('summary', '')} {chunk.get('text', '')}".lower()
        overlap = sum(1 for term in terms if term.lower() in text)
        if overlap:
            scores[chunk_id] += overlap
            reasons[chunk_id].append(f"query_terms:{overlap}")
        if len(reasons[chunk_id]) > 1:
            scores[chunk_id] += 5
            reasons[chunk_id].append("multiple_paths")

    ranked_ids = sorted(merged, key=lambda cid: scores[cid], reverse=True)
    ranked = []
    for chunk_id in ranked_ids:
        chunk = dict(merged[chunk_id])
        chunk["_retrieval_score"] = scores[chunk_id]
        chunk["_retrieval_reasons"] = reasons[chunk_id]
        ranked.append(chunk)
    return ranked, reasons


def _pack_context(
    query: str,
    chunks: list[dict[str, Any]],
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
    return packed, {
        "context_chars_before_packing": before_chars,
        "context_chars_after_packing": after_chars,
        "context_chars_saved": max(before_chars - after_chars, 0),
        "selected_snippet_counts": snippet_counts,
    }


def _snippets(query: str, text: str, summary: str) -> list[str]:
    """Pick small passages with query-term overlap; fall back to the start."""
    terms = {term.lower() for term in _terms(query)}
    passages = _passages(text)
    scored = []
    for index, passage in enumerate(passages):
        lowered = passage.lower()
        score = sum(1 for term in terms if term in lowered)
        if score:
            scored.append((score, index, passage))
    if not scored:
        fallback = summary or text
        return [fallback[:MAX_SNIPPET_CHARS]] if fallback else []
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [passage[:MAX_SNIPPET_CHARS] for _, _, passage in scored[:MAX_SNIPPETS_PER_CHUNK]]


def _passages(text: str) -> list[str]:
    """Split text into readable passages without pulling in another parser."""
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    if len(paragraphs) > 1:
        return paragraphs
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()]
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
