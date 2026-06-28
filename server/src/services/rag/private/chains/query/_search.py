from __future__ import annotations

import logging
import re
from typing import Any

from src.repositories import recall, recall_key_vectors, source_chunk_vectors, source_chunks

from ._state import QueryState

logger = logging.getLogger(__name__)

MAX_EVIDENCE_CHUNKS = 12
MAX_SNIPPETS_PER_CHUNK = 3
MAX_SNIPPET_CHARS = 420
# Context budget per sub-query pass; total is capped again after merge.
_CONTEXT_CHARS_PER_PASS = 6000


def search_node(state: QueryState) -> dict[str, Any]:
    """LangGraph node: run evidence search for every sub-query and accumulate chunks.

    Each sub-query contributes independently ranked chunks. The caller (graph)
    merges all returned chunk lists via the operator.add reducer on QueryState.chunks.
    We return one trace_part per sub-query so the final trace can show per-sub-query
    diagnostics.
    """
    all_chunks: list[dict[str, Any]] = []
    trace_parts: list[dict[str, Any]] = []

    for sub_query in state["sub_queries"]:
        chunks, trace_part = _evidence_for(sub_query)
        all_chunks.extend(chunks)
        trace_parts.append(trace_part)

    return {"chunks": all_chunks, "trace_parts": trace_parts}


def finalize_chunks(raw_chunks: list[dict[str, Any]], query: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Dedup, re-rank, and context-pack the accumulated chunks from all sub-query passes.

    Called by QueryEvidenceChain after the graph completes; not a graph node itself
    because it needs the full merged set before trimming to MAX_EVIDENCE_CHUNKS.
    """
    # Dedup: operator.add may produce duplicates across sub-query passes.
    seen: dict[str, dict[str, Any]] = {}
    for chunk in raw_chunks:
        seen.setdefault(chunk["id"], chunk)
    deduped = list(seen.values())

    # Re-rank across the full merged set using the original user query for term overlap.
    ranked, score_trace = _rank_chunks(query, deduped)
    ranked, context_trace = _pack_context(query, ranked[:MAX_EVIDENCE_CHUNKS])
    selected_score_trace = {chunk["id"]: score_trace.get(chunk["id"], []) for chunk in ranked}
    return ranked, {**context_trace, "chunk_score_reasons": selected_score_trace}


# ── internal helpers ─────────────────────────────────────────────────────────


def _evidence_for(sub_query: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run all three search paths for one sub-query."""
    vector_chunks, vector_ids = _vector_source_chunks(sub_query)
    lexical_chunks = source_chunks.search(sub_query, limit=8)
    recall_keys = _recall_keys(sub_query)
    linked_ids = recall.linked_source_chunk_ids([key["id"] for key in recall_keys], limit=12)
    linked_chunks = source_chunks.get_by_ids(linked_ids)

    # Source chunks are evidence; recall only expands the search area.
    chunks, _ = _rank_chunks(sub_query, [*vector_chunks, *lexical_chunks, *linked_chunks])
    chunks, _ = _pack_context(sub_query, chunks[:MAX_EVIDENCE_CHUNKS], budget=_CONTEXT_CHARS_PER_PASS)

    trace_part = {
        "sub_query": sub_query,
        "vector_source_chunk_ids": vector_ids,
        "lexical_source_chunk_count": len(lexical_chunks),
        "recall_key_count": len(recall_keys),
        "recall_keys": [{"id": key["id"], "name": key["name"]} for key in recall_keys],
        "linked_source_chunk_count": len(linked_chunks),
        "source_chunk_count": len(chunks),
    }
    return chunks, trace_part


def _vector_source_chunks(query: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Use Chroma when available; lexical search still works if embeddings are down."""
    try:
        hits = source_chunk_vectors.search(query, top_k=8)
    except Exception as exc:
        logger.warning("query_source_vector_search_failed error=%s", exc)
        return [], []
    ids = [hit["object_id"] for hit in hits if hit.get("object_type") == "source_chunk"]
    return source_chunks.get_by_ids(ids), ids


def _recall_keys(query: str) -> list[dict[str, Any]]:
    """Find recall keys that may point to broader related evidence."""
    keys = recall.find_candidate_keys(_terms(query), limit=8)
    if recall.has_keys():
        try:
            vector_ids = [
                hit["object_id"]
                for hit in recall_key_vectors.search(query, top_k=8)
                if hit.get("object_type") == "recall_key"
            ]
            keys = [*keys, *recall.find_keys_by_ids(vector_ids)]
        except Exception as exc:
            logger.warning("query_recall_vector_search_failed error=%s", exc)
    return _merge_keys(keys)[:8]


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
    """Attach focused snippets so the answer prompt skips unrelated text.

    Context engineering: instead of sending full chunk text we select only
    the most query-relevant passages per chunk. This keeps each sub-query pass
    within `budget` chars and the merged final context within MAX_CONTEXT_CHARS.
    """
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
