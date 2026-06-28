from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.repositories import recall, recall_key_vectors, source_chunk_vectors, source_chunks

logger = logging.getLogger(__name__)

MAX_EVIDENCE_CHUNKS = 12
MAX_SNIPPETS_PER_CHUNK = 3
MAX_SNIPPET_CHARS = 420
MAX_CONTEXT_CHARS = 6000


class QueryEvidenceChain:
    """Find source chunks by direct search and one-hop recall expansion."""

    def run(self, query: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Return capped source chunks plus a trace of how they were found."""
        vector_chunks, vector_ids = _vector_source_chunks(query)
        lexical_chunks = source_chunks.search(query, limit=8)
        recall_keys = _recall_keys(query)
        linked_ids = recall.linked_source_chunk_ids([key["id"] for key in recall_keys], limit=12)
        linked_chunks = source_chunks.get_by_ids(linked_ids)

        # Source chunks are evidence; recall only expands the search area.
        chunks, score_trace = _rank_chunks(query, vector_chunks, lexical_chunks, linked_chunks)
        chunks, context_trace = _pack_context(query, chunks[:MAX_EVIDENCE_CHUNKS])
        selected_score_trace = {chunk["id"]: score_trace.get(chunk["id"], []) for chunk in chunks}
        trace = {
            "mode": "source_chunks_with_recall_expansion",
            "query": query,
            "vector_source_chunk_ids": vector_ids,
            "lexical_source_chunk_ids": [chunk["id"] for chunk in lexical_chunks],
            "lexical_source_chunk_count": len(lexical_chunks),
            "recall_key_count": len(recall_keys),
            "recall_keys": [{"id": key["id"], "name": key["name"]} for key in recall_keys],
            "linked_source_chunk_ids": linked_ids,
            "linked_source_chunk_count": len(linked_chunks),
            "source_chunk_count": len(chunks),
            "ranked_source_chunk_ids": [chunk["id"] for chunk in chunks],
            "chunk_score_reasons": selected_score_trace,
            **context_trace,
        }
        return chunks, trace


class QueryAnswerChain:
    """Generate an answer from already-selected source chunks."""

    def __init__(self, json_client) -> None:
        """Use the same JSON client as ingestion chains."""
        self.json_client = json_client

    def run(self, query: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Return an answer and source chunk ids used as citations."""
        if not chunks:
            return {"answer": "I could not find relevant source chunks for that query.", "citation_ids": []}

        try:
            data = self.json_client.invoke_json(
                (
                    "Answer the user query using only SOURCE_CHUNKS. "
                    "Return only valid JSON. No markdown. "
            "SOURCE_CHUNKS are the only evidence; recall metadata is not evidence. "
            "Each source chunk contains a summary and focused snippets from saved text. "
                    "If the evidence is incomplete, say what is missing. "
                    "For broad or timeline questions, combine relevant chunks in source/time order. "
                    "Citations must be source_chunk ids from SOURCE_CHUNKS."
                ),
                (
                    f"QUERY:\n{query}\n\n"
                    f"SOURCE_CHUNKS:\n{json.dumps(_chunk_payload(chunks), ensure_ascii=False)}\n\n"
                    'Return JSON with keys: {"answer":"string","citation_ids":["source_chunk_id"]}'
                ),
            )
        except Exception as exc:
            logger.warning("query_answer_failed error=%s", exc)
            return {"answer": "I found relevant source chunks, but answer generation failed.", "citation_ids": []}

        answer = str(data.get("answer") or "").strip()
        valid_ids = {chunk["id"] for chunk in chunks}
        citation_ids = [str(item) for item in data.get("citation_ids", []) if str(item) in valid_ids]
        return {"answer": answer or "I found relevant source chunks, but no answer was generated.", "citation_ids": citation_ids[:6]}


def build_query_result(query: str, chunks: list[dict[str, Any]], answer: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    """Build the route response shape expected by the UI."""
    citation_ids = answer["citation_ids"] or [chunk["id"] for chunk in chunks[:3]]
    cited_chunks = [chunk for chunk in chunks if chunk["id"] in set(citation_ids)]
    return {
        "answer": answer["answer"],
        "citations": [_citation(chunk, index + 1) for index, chunk in enumerate(cited_chunks)],
        "source_chunks": [_public_chunk(chunk) for chunk in chunks],
        "retrieval_trace": {**trace, "citation_count": len(cited_chunks)},
    }


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
            vector_ids = [hit["object_id"] for hit in recall_key_vectors.search(query, top_k=8) if hit.get("object_type") == "recall_key"]
            keys = [*keys, *recall.find_keys_by_ids(vector_ids)]
        except Exception as exc:
            logger.warning("query_recall_vector_search_failed error=%s", exc)
    return _merge_keys(keys)[:8]


def _rank_chunks(
    query: str,
    vector_chunks: list[dict[str, Any]],
    lexical_chunks: list[dict[str, Any]],
    linked_chunks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Merge search paths and keep why each chunk was selected."""
    merged: dict[str, dict[str, Any]] = {}
    scores: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}

    _add_ranked(merged, scores, reasons, vector_chunks, "vector", 80)
    _add_ranked(merged, scores, reasons, lexical_chunks, "lexical", 50)
    _add_ranked(merged, scores, reasons, linked_chunks, "recall_link", 25)

    terms = set(_terms(query))
    for chunk_id, chunk in merged.items():
        text = f"{chunk.get('summary', '')} {chunk.get('text', '')}".lower()
        overlap = sum(1 for term in terms if term.lower() in text)
        if overlap:
            scores[chunk_id] += overlap
            reasons[chunk_id].append(f"query_terms:{overlap}")
        if len(reasons[chunk_id]) > 1:
            scores[chunk_id] += 5
            reasons[chunk_id].append("multiple_paths")

    ranked_ids = sorted(merged, key=lambda chunk_id: scores[chunk_id], reverse=True)
    ranked = []
    for chunk_id in ranked_ids:
        chunk = dict(merged[chunk_id])
        chunk["_retrieval_score"] = scores[chunk_id]
        chunk["_retrieval_reasons"] = reasons[chunk_id]
        ranked.append(chunk)
    return ranked, reasons


def _add_ranked(
    merged: dict[str, dict[str, Any]],
    scores: dict[str, float],
    reasons: dict[str, list[str]],
    chunks: list[dict[str, Any]],
    source: str,
    base_score: int,
) -> None:
    """Give earlier hits in each path a slightly higher score."""
    for index, chunk in enumerate(chunks):
        chunk_id = chunk["id"]
        merged.setdefault(chunk_id, chunk)
        scores[chunk_id] = scores.get(chunk_id, 0) + max(base_score - index, 1)
        reasons.setdefault(chunk_id, []).append(source)


def _pack_context(query: str, chunks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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
        after_chars += len(str(chunk.get("summary", ""))) + sum(len(snippet) for snippet in snippets)
        packed.append(next_chunk)
        if after_chars >= MAX_CONTEXT_CHARS:
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


def _chunk_payload(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Send focused snippets while keeping source chunk IDs citable."""
    return [
        {
            "id": chunk["id"],
            "summary": chunk.get("summary", ""),
            "source_time": chunk.get("source_time"),
            "spans": chunk.get("spans", []),
            "snippets": chunk.get("_snippets", []),
        }
        for chunk in chunks
    ]


def _citation(chunk: dict[str, Any], number: int) -> dict[str, Any]:
    """Map one source chunk into the citation fields used by the frontend."""
    span = (chunk.get("spans") or [{}])[0]
    text = str(chunk.get("text", ""))
    quote = " ".join(text.split())[:360]
    return {
        "id": f"citation-{number}",
        "source_chunk_id": chunk["id"],
        "source_input_id": chunk["raw_input_id"],
        "exact_quote": quote,
        "raw_text": text,
        "cleaned_text": chunk.get("summary", ""),
        "start_char": span.get("start"),
        "end_char": span.get("end"),
    }


def _public_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    """Return compact source chunk data for dev-friendly UI display."""
    return {
        "id": chunk["id"],
        "raw_input_id": chunk["raw_input_id"],
        "summary": chunk.get("summary", ""),
        "text": chunk.get("text", ""),
        "spans": chunk.get("spans", []),
        "source_time": chunk.get("source_time"),
    }


def _terms(query: str) -> list[str]:
    """Extract simple lookup terms for exact and FTS recall-key search."""
    seen = set()
    terms = []
    for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]*", query):
        lowered = word.lower()
        if len(word) >= 3 and lowered not in seen:
            seen.add(lowered)
            terms.append(word)
    return terms[:10]
