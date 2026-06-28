from __future__ import annotations

import json
import logging
from typing import Any

from ._graph import build_retrieval_graph
from ._search import finalize_chunks

logger = logging.getLogger(__name__)


class QueryEvidenceChain:
    """Find source chunks using a LangGraph retrieval graph.

    Graph: breakdown (sub-query decomposition) → search (evidence per sub-query).
    After the graph runs, chunks are deduped, re-ranked, and context-packed
    before being returned.
    """

    def __init__(self, json_client) -> None:
        """Compile the retrieval graph once at construction."""
        self.json_client = json_client
        # Graph is compiled once; subsequent calls just invoke it.
        self._graph = build_retrieval_graph(json_client)

    def run(self, query: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Return context-packed source chunks plus a trace of how they were found."""
        result = self._graph.invoke({
            "query": query,
            "sub_queries": [],
            "chunks": [],
            "trace_parts": [],
        })

        sub_queries: list[str] = result["sub_queries"]
        raw_chunks: list[dict[str, Any]] = result["chunks"]
        trace_parts: list[dict[str, Any]] = result["trace_parts"]

        chunks, finalize_trace = finalize_chunks(raw_chunks, query)

        trace = {
            "mode": "source_chunks_with_recall_expansion",
            "query": query,
            "sub_queries": sub_queries,
            "sub_query_count": len(sub_queries),
            "sub_query_traces": trace_parts,
            "ranked_source_chunk_ids": [chunk["id"] for chunk in chunks],
            "source_chunk_count": len(chunks),
            **finalize_trace,
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
