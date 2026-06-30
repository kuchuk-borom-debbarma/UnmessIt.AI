from __future__ import annotations

import json
import logging
from typing import Any

from src.services.rag.models import ProgressReporter

from ._graph import build_retrieval_graph
from ._search import finalize_chunks

logger = logging.getLogger(__name__)


class QueryEvidenceChain:
    """Find source chunks using an async LangGraph retrieval graph.

    Graph: breakdown (sub-query decomposition) → search (concurrent evidence per sub-query).
    After the graph runs, chunks are deduped, re-ranked, and context-packed.
    """

    def __init__(self, json_client) -> None:
        """Compile the retrieval graph once at construction."""
        self.json_client = json_client
        self._graph = build_retrieval_graph(json_client)

    async def run(self, query: str, user_id: str, reporter: ProgressReporter | None = None, within_directories: list[str] | None = None, excluding_directories: list[str] | None = None, within_tags: list[str] | None = None, excluding_tags: list[str] | None = None, within_tags_condition: str = "any") -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Return context-packed source chunks plus a trace of how they were found."""
        result = await self._graph.ainvoke({
            "query": query,
            "sub_queries": [],
            "extracted_subjects": [],
            "user_id": user_id,
            "reporter": reporter,
            "within_directories": within_directories or [],
            "excluding_directories": excluding_directories or [],
            "within_tags": within_tags or [],
            "excluding_tags": excluding_tags or [],
            "within_tags_condition": within_tags_condition,
            "chunks": [],
            "trace_parts": [],
        })

        sub_queries: list[str] = result["sub_queries"]
        extracted_subjects: list[str] = result.get("extracted_subjects") or []
        raw_chunks: list[dict[str, Any]] = result["chunks"]
        trace_parts: list[dict[str, Any]] = result["trace_parts"]
        if reporter:
            await reporter.report("Deduplicating, re-ranking, and context-packing evidence...")
        chunks, finalize_trace = finalize_chunks(raw_chunks, query)
        
        # Calculate true baseline chars (unique across all subqueries before budget dropping)
        global_unique_chunks = {}
        for t in trace_parts:
            global_unique_chunks.update(t.get("baseline_lengths", {}))
            
        true_before_chars = sum(global_unique_chunks.values())
        if true_before_chars > 0:
            finalize_trace["context_chars_before_packing"] = true_before_chars
            finalize_trace["context_chars_saved"] = max(true_before_chars - finalize_trace.get("context_chars_after_packing", 0), 0)

        trace = {
            "mode": "source_chunks_with_recall_expansion",
            "query": query,
            "sub_queries": sub_queries,
            "sub_query_count": len(sub_queries),
            "extracted_subjects": extracted_subjects,
            "sub_query_traces": trace_parts,
            "ranked_source_chunk_ids": [chunk["id"] for chunk in chunks],
            "source_chunk_count": len(chunks),
            **finalize_trace,
        }
        return chunks, trace


class QueryAnswerChain:
    """Generate an answer from already-selected source chunks."""

    def __init__(self, json_client) -> None:
        self.json_client = json_client

    async def run(self, query: str, chunks: list[dict[str, Any]], user_id: str) -> dict[str, Any]:
        """Return an answer and source chunk ids used as citations."""
        if not chunks:
            return {"answer": "I could not find relevant source chunks for that query.", "citation_ids": []}

        try:
            data = await self.json_client.async_invoke_json(
                system=(
                    "Answer the user query using only SOURCE_CHUNKS. "
                    "Return only valid JSON. No markdown. "
                    "SOURCE_CHUNKS are the only evidence; recall metadata is not evidence. "
                    "Each source chunk contains a summary and focused snippets from saved text. "
                    "If the evidence is incomplete, say what is missing. "
                    "For broad or timeline questions, combine relevant chunks in source/time order. "
                    "Citations must be source_chunk ids from SOURCE_CHUNKS."
                ),
                human=(
                    f"QUERY:\n{query}\n\n"
                    f"SOURCE_CHUNKS:\n{json.dumps(_chunk_payload(chunks), ensure_ascii=False)}\n\n"
                    'Return JSON with keys: {"answer":"string","citation_ids":["source_chunk_id"]}'
                ),
                user_id=user_id,
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
    citation_ids = answer.get("citation_ids") or answer.get("citations") or [chunk["id"] for chunk in chunks[:3]]
    cited_chunks = [chunk for chunk in chunks if chunk["id"] in set(citation_ids)]
    return {
        "answer": answer["answer"],
        "citations": [_citation(chunk, index + 1) for index, chunk in enumerate(cited_chunks)],
        "source_chunks": [_public_chunk(chunk) for chunk in chunks],
        "directories": answer.get("directories", []),
        "notes": answer.get("notes", []),
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
    return {
        "id": chunk["id"],
        "raw_input_id": chunk["raw_input_id"],
        "note_id": chunk.get("note_id") or chunk.get("raw_input_id"),
        "summary": chunk.get("summary", ""),
        "text": chunk.get("text", ""),
        "spans": chunk.get("spans", []),
        "source_time": chunk.get("source_time"),
    }
