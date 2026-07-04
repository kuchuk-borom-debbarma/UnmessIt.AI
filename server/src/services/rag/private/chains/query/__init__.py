from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.infra import retrieval_cache
from src.services.rag.models import ProgressReporter

from ._graph import build_retrieval_graph
from ._search import finalize_chunks

logger = logging.getLogger(__name__)
_CITE_MARKER_RE = re.compile(r"\[\[cite:([^\]\s]+)\]\]?")
_VERIFIER_CACHE_VERSION = "query_verifier:v1"
_ANSWER_CACHE_VERSION = "query_answer:v1"


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
            "cache_events": [],
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
        cache_events: list[dict[str, Any]] = result.get("cache_events") or []
        if reporter:
            await reporter.report(
                "Combining and selecting the best notes...",
                {"depth": 1, "ref": "retrieval:evidence:merge", "raw_chunk_count": len(raw_chunks), "sub_query_count": len(trace_parts)},
            )
        chunks, finalize_trace = finalize_chunks(raw_chunks, query)
        for key in (
            "context_engineering",
            "context_chars_before_packing",
            "context_chars_after_packing",
            "context_chars_saved",
            "selected_snippet_counts",
        ):
            if key in result:
                finalize_trace[key] = result[key]
        if reporter:
            await reporter.report(
                f"Selected {len(chunks)} best notes for reading.",
                {"depth": 1, "ref": "retrieval:evidence:final", "source_chunk_ids": [chunk["id"] for chunk in chunks], **finalize_trace},
            )

        trace = {
            "mode": "source_chunks_with_recall_expansion",
            "query": query,
            "sub_queries": sub_queries,
            "sub_query_count": len(sub_queries),
            "extracted_subjects": extracted_subjects,
            "sub_query_traces": trace_parts,
            "ranked_source_chunk_ids": [chunk["id"] for chunk in chunks],
            "source_chunk_count": len(chunks),
            "cache_events": cache_events,
            **finalize_trace,
        }
        return chunks, trace


class QueryVerifierChain:
    """Judge whether packed evidence matches the query scope before answering."""

    def __init__(self, json_client) -> None:
        self.json_client = json_client

    async def run(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        user_id: str,
        reporter: ProgressReporter | None = None,
        attempt: int = 1,
    ) -> dict[str, Any]:
        """Return relevance decisions and an optional focused retry query."""
        if not chunks:
            return {
                "status": "insufficient",
                "reason": "No evidence chunks were selected.",
                "on_topic_ids": [],
                "off_topic_ids": [],
                "retry_query": query,
            }

        if reporter:
            await reporter.report(
                "Checking if notes answer the question...",
                {"depth": 1, "ref": f"retrieval:verify:{attempt}", "source_chunk_count": len(chunks)},
            )

        valid_ids = {chunk["id"] for chunk in chunks}
        system = _verifier_system_prompt()
        human = _verifier_human_prompt(query, chunks)
        cache_key = _verifier_cache_key(query, user_id, attempt, system, human)
        if cache_key:
            cached = _cached_verifier_result(await retrieval_cache.get_json(cache_key), valid_ids)
            if cached is not None:
                logger.info(
                    "query_verifier_cache_hit attempt=%s status=%s on_topic=%s off_topic=%s",
                    attempt,
                    cached["status"],
                    len(cached["on_topic_ids"]),
                    len(cached["off_topic_ids"]),
                )
                if reporter:
                    await reporter.report(
                        "Reusing previous note review.",
                        {
                            "depth": 1,
                            "ref": f"retrieval:verify:{attempt}:cache_hit",
                            "status": cached["status"],
                            "on_topic_count": len(cached["on_topic_ids"]),
                            "off_topic_count": len(cached["off_topic_ids"]),
                            "retry_query": cached["retry_query"],
                        },
                    )
                return {**cached, "_cache_events": [{"stage": "verifier", "status": "hit"}]}

        try:
            data = await self.json_client.async_invoke_json(
                system=system,
                human=human,
                user_id=user_id,
                stage="retrieval.verifier",
            )
        except Exception as exc:
            logger.warning("query_verifier_failed error=%s", exc)
            if reporter:
                await reporter.report(
                    "Verification skipped; continuing with selected notes.",
                    {"depth": 1, "ref": f"retrieval:verify:{attempt}:fallback", "error": str(exc)[:500]},
                )
            return {
                "status": "sufficient",
                "reason": "Verifier unavailable; using ranked retrieval output.",
                "on_topic_ids": [chunk["id"] for chunk in chunks],
                "off_topic_ids": [],
                "retry_query": "",
            }

        result = _normalize_verifier_result(data if isinstance(data, dict) else {}, chunks)
        if cache_key and isinstance(data, dict):
            await retrieval_cache.set_json(cache_key, result)
            logger.info(
                "query_verifier_cache_set attempt=%s status=%s on_topic=%s off_topic=%s",
                attempt,
                result["status"],
                len(result["on_topic_ids"]),
                len(result["off_topic_ids"]),
            )
            if reporter:
                await reporter.report(
                    "Saved note review for exact repeat questions.",
                    {
                        "depth": 1,
                        "ref": f"retrieval:verify:{attempt}:cache_set",
                        "status": result["status"],
                        "on_topic_count": len(result["on_topic_ids"]),
                        "off_topic_count": len(result["off_topic_ids"]),
                    },
                )
            result["_cache_events"] = [{"stage": "verifier", "status": "miss"}, {"stage": "verifier", "status": "set"}]
        if reporter:
            await reporter.report(
                f"Approved {len(result['on_topic_ids'])} notes as highly relevant, rejected {len(result['off_topic_ids'])}.",
                {
                    "depth": 1,
                    "ref": f"retrieval:verify:{attempt}:result",
                    "status": result["status"],
                    "on_topic_count": len(result["on_topic_ids"]),
                    "off_topic_count": len(result["off_topic_ids"]),
                    "retry_query": result["retry_query"],
                },
            )
        return result


def _verifier_system_prompt() -> str:
    return (
        "Judge whether retrieved evidence can answer the user's query without mixing unrelated contexts. "
        "Return only valid JSON. No markdown. "
        "Use only the provided compact chunk payloads. "
        "Classify chunks as on-topic when they match the user's requested subject, scope, qualifiers, and sense of ambiguous terms. "
        "Classify chunks as off-topic when they use a different sense, domain, event, entity, time, or scope than the query asks for. "
        "When the query explicitly asks to compare, connect, or contrast multiple subjects, chunks for each requested subject may be on-topic even if they come from different contexts. "
        "When the query asks for an opinion, take, impression, or what to think about a subject, treat it as a request for a source-grounded assessment; chunks about that subject can be on-topic even if they do not contain someone else's opinion. "
        "When the query is scoped to one context, do not keep chunks from another context just because words overlap. "
        "If some chunks support only part of a multi-part query, keep those chunks on-topic and mark missing parts in reason. "
        "Do not set status to insufficient when on-topic chunks can support a partial answer. "
        "If enough on-topic evidence exists, status is sufficient. "
        "If on-topic evidence is partial and a focused retry may find missing parts, status is needs_retry and retry_query must be focused. "
        "If no selected chunk can answer any part of the query and a retry is unlikely to help, status is insufficient. "
        "Do not reveal hidden reasoning; put a concise user-safe reason in reason."
    )


def _verifier_human_prompt(query: str, chunks: list[dict[str, Any]]) -> str:
    return (
        f"QUERY:\n{query}\n\n"
        f"CHUNKS:\n{json.dumps(_chunk_payload(chunks), ensure_ascii=False)}\n\n"
        'Return JSON: {"status":"sufficient|needs_retry|insufficient","reason":"short reason","on_topic_ids":["source_chunk_id"],"off_topic_ids":["source_chunk_id"],"retry_query":"focused query or empty string"}'
    )


def _verifier_cache_key(query: str, user_id: str | None, attempt: int, system: str, human: str) -> str | None:
    signature = retrieval_cache.llm_settings_signature(user_id, "retrieval.verifier")
    if not signature:
        return None
    return retrieval_cache.cache_key(_VERIFIER_CACHE_VERSION, user_id or "", attempt, signature, system, human, query)


def _normalize_verifier_result(data: dict[str, Any], chunks: list[dict[str, Any]]) -> dict[str, Any]:
    valid_ids = {chunk["id"] for chunk in chunks}
    status = str(data.get("status") or "sufficient").strip().lower()
    if status not in {"sufficient", "needs_retry", "insufficient"}:
        status = "sufficient"
    on_topic_ids = _valid_ids(data.get("on_topic_ids"), valid_ids)
    off_topic_ids = _valid_ids(data.get("off_topic_ids"), valid_ids)
    if on_topic_ids:
        off_topic_ids = [chunk_id for chunk_id in off_topic_ids if chunk_id not in set(on_topic_ids)]
    elif off_topic_ids:
        off_topic = set(off_topic_ids)
        on_topic_ids = [chunk["id"] for chunk in chunks if chunk["id"] not in off_topic]
    elif status == "sufficient":
        on_topic_ids = [chunk["id"] for chunk in chunks]

    retry_query = str(data.get("retry_query") or "").strip()
    if on_topic_ids and status == "insufficient":
        status = "needs_retry" if retry_query else "sufficient"
    reason = str(data.get("reason") or "").strip()[:500]
    return {
        "status": status,
        "reason": reason or "Evidence checked against the query scope.",
        "on_topic_ids": on_topic_ids,
        "off_topic_ids": off_topic_ids,
        "retry_query": retry_query,
    }


def _cached_verifier_result(value: dict[str, Any] | None, valid_ids: set[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if value.get("status") not in {"sufficient", "needs_retry", "insufficient"}:
        return None
    if not isinstance(value.get("reason"), str) or not isinstance(value.get("retry_query"), str):
        return None
    on_topic_ids = _cached_ids(value.get("on_topic_ids"), valid_ids)
    off_topic_ids = _cached_ids(value.get("off_topic_ids"), valid_ids)
    if on_topic_ids is None or off_topic_ids is None:
        return None
    if set(on_topic_ids) & set(off_topic_ids):
        return None
    return {
        "status": value["status"],
        "reason": value["reason"][:500] or "Evidence checked against the query scope.",
        "on_topic_ids": on_topic_ids,
        "off_topic_ids": off_topic_ids,
        "retry_query": value["retry_query"].strip(),
    }


def _cached_ids(value: Any, valid_ids: set[str]) -> list[str] | None:
    if not isinstance(value, list):
        return None
    result = []
    for item in value:
        if not isinstance(item, str) or item not in valid_ids or item in result:
            return None
        result.append(item)
    return result


class QueryAnswerChain:
    """Generate an answer from already-selected source chunks."""

    def __init__(self, json_client) -> None:
        self.json_client = json_client

    async def run(self, query: str, chunks: list[dict[str, Any]], user_id: str, reporter: ProgressReporter | None = None) -> dict[str, Any]:
        """Return an answer and source chunk ids used as citations."""
        if not chunks:
            if reporter:
                await reporter.report("No notes found; skipping answer generation.", {"depth": 1, "ref": "retrieval:answer:empty"})
            return {"answer": "I could not find relevant source chunks for that query.", "citation_ids": []}

        system = _answer_system_prompt()
        human = _answer_human_prompt(query, chunks)
        cache_key = _answer_cache_key(query, user_id, system, human)
        if cache_key:
            cached = _cached_answer_result(await retrieval_cache.get_json(cache_key), {chunk["id"] for chunk in chunks})
            if cached is not None:
                logger.info("query_answer_cache_hit citations=%s", len(cached["citation_ids"]))
                if reporter:
                    await reporter.report(
                        "Reusing previous final answer.",
                        {"depth": 1, "ref": "retrieval:answer:cache_hit", "citation_count": len(cached["citation_ids"])},
                    )
                return {**cached, "_cache_events": [{"stage": "answer", "status": "hit"}]}

        try:
            if reporter:
                await reporter.report(
                    "Synthesizing answer from verified notes...",
                    {"depth": 1, "ref": "retrieval:answer:prompt", "source_chunk_count": len(chunks)},
                )
            data = await self.json_client.async_invoke_json(
                system=system,
                human=human,
                user_id=user_id,
                stage="retrieval.answer",
            )
            if reporter:
                await reporter.report("Validating citations...", {"depth": 1, "ref": "retrieval:answer:validate"})
        except Exception as exc:
            logger.warning("query_answer_failed error=%s", exc)
            if reporter:
                await reporter.report(f"Answer generation failed: {exc}", {"depth": 1, "ref": "retrieval:answer:error"})
            return {"answer": "I found relevant source chunks, but answer generation failed.", "citation_ids": []}

        result = _normalize_answer_result(data if isinstance(data, dict) else {}, chunks)
        if cache_key and isinstance(data, dict) and str(data.get("answer") or "").strip():
            await retrieval_cache.set_json(cache_key, result)
            logger.info("query_answer_cache_set citations=%s", len(result["citation_ids"]))
            if reporter:
                await reporter.report(
                    "Saved final answer for exact repeat questions.",
                    {"depth": 1, "ref": "retrieval:answer:cache_set", "citation_count": len(result["citation_ids"])},
                )
            result["_cache_events"] = [{"stage": "answer", "status": "miss"}, {"stage": "answer", "status": "set"}]
        if reporter:
            await reporter.report(
                f"Selected {len(result['citation_ids'])} citation(s) to back the answer",
                {"depth": 1, "ref": "retrieval:answer:citations", "citation_ids": result["citation_ids"]},
            )
        return result


def _answer_system_prompt() -> str:
    return (
        "Answer the user query using only SOURCE_CHUNKS. "
        "Return only valid JSON. No markdown. "
        "SOURCE_CHUNKS are the only evidence; recall metadata is not evidence. "
        "Each source chunk contains a summary and focused snippets from saved text. "
        "If evidence supports only part of the query, answer the supported part first and briefly name what is missing. "
        "Do not refuse the whole query only because another requested part is missing. "
        "Do not mention SOURCE_CHUNKS, chunks, retrieval internals, or source ids in prose. "
        "For broad, timeline, comparison, similarity, or reasoning questions, synthesize across chunks when the facts for each side are present. "
        "Do not require a source to explicitly perform the comparison; compare the sourced facts yourself. "
        "When the user explicitly asks to compare or relate subjects, do not reject the comparison only because the subjects come from different contexts or sources. "
        "If chunks describe subject A and separate chunks describe subject B, infer similarities and differences from those facts instead of saying direct comparative analysis is unavailable. "
        "For attribute questions, collect small details from all relevant snippets before deciding the answer is missing. "
        "For attribute answers, preserve exact counts, labels, descriptors, and qualifiers when the snippets contain them. "
        "Use cautious wording for inference, but provide the inference when the evidence supports it. "
        "Embed source markers directly in the answer where they help verification, using [[cite:SOURCE_CHUNK_ID]] immediately after the supported claim. "
        "Do not show raw ids except inside [[cite:...]] markers. "
        "Citations must be source_chunk ids from SOURCE_CHUNKS."
    )


def _answer_human_prompt(query: str, chunks: list[dict[str, Any]]) -> str:
    return (
        f"QUERY:\n{query}\n\n"
        f"SOURCE_CHUNKS:\n{json.dumps(_chunk_payload(chunks), ensure_ascii=False)}\n\n"
        'Return JSON with keys: {"answer":"string with optional [[cite:source_chunk_id]] markers","citation_ids":["source_chunk_id"]}'
    )


def _answer_cache_key(query: str, user_id: str | None, system: str, human: str) -> str | None:
    signature = retrieval_cache.llm_settings_signature(user_id, "retrieval.answer")
    if not signature:
        return None
    return retrieval_cache.cache_key(_ANSWER_CACHE_VERSION, user_id or "", signature, system, human, query)


def _normalize_answer_result(data: dict[str, Any], chunks: list[dict[str, Any]]) -> dict[str, Any]:
    answer = str(data.get("answer") or "").strip()
    valid_ids = {chunk["id"] for chunk in chunks}
    marker_ids = [match.group(1) for match in _CITE_MARKER_RE.finditer(answer) if match.group(1) in valid_ids]
    citation_ids = [str(item) for item in data.get("citation_ids", []) if str(item) in valid_ids]
    citation_ids = list(dict.fromkeys([*citation_ids, *marker_ids]))[:6]
    answer = _sanitize_answer_citations(answer, set(citation_ids))
    return {
        "answer": answer or "I found relevant source chunks, but no answer was generated.",
        "citation_ids": citation_ids,
    }


def _cached_answer_result(value: dict[str, Any] | None, valid_ids: set[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict) or not isinstance(value.get("answer"), str):
        return None
    citation_ids = _cached_ids(value.get("citation_ids"), valid_ids)
    if citation_ids is None:
        return None
    answer = _sanitize_answer_citations(value["answer"].strip(), set(citation_ids))
    if not answer:
        return None
    return {"answer": answer, "citation_ids": citation_ids}


def build_query_result(query: str, chunks: list[dict[str, Any]], answer: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    """Build the route response shape expected by the UI."""
    citation_ids = answer.get("citation_ids") or answer.get("citations") or [chunk["id"] for chunk in chunks[:3]]
    cited_chunks = [chunk for chunk in chunks if chunk["id"] in set(citation_ids)]
    cache_events = trace.get("cache_events") if isinstance(trace.get("cache_events"), list) else []
    cache_summary = _cache_summary(cache_events)
    context_trace = _context_engineering_for_result(chunks, trace, cache_summary)
    return {
        "answer": answer["answer"],
        "citations": [_citation(chunk, index + 1) for index, chunk in enumerate(cited_chunks)],
        "source_chunks": [_public_chunk(chunk) for chunk in chunks],
        "directories": answer.get("directories", []),
        "notes": answer.get("notes", []),
        "retrieval_trace": {
            **trace,
            **context_trace,
            "cache_summary": cache_summary,
            "citation_count": len(cited_chunks),
        },
    }


def _cache_summary(events: list[dict[str, Any]]) -> dict[str, str]:
    summary: dict[str, str] = {}
    for event in events:
        stage = event.get("stage")
        status = event.get("status")
        if not isinstance(stage, str) or not isinstance(status, str):
            continue
        cache = event.get("cache")
        summary[stage] = f"{cache}_{status}" if cache and cache != "exact" else status
    return summary


def _context_engineering_for_result(
    chunks: list[dict[str, Any]],
    trace: dict[str, Any],
    cache_summary: dict[str, str],
) -> dict[str, Any]:
    context = trace.get("context_engineering")
    if isinstance(context, dict) and (context.get("ran") or context.get("raw_chars")):
        return {
            "context_engineering": context,
            "context_chars_before_packing": context.get("raw_chars", 0),
            "context_chars_after_packing": context.get("packed_chars", 0),
            "context_chars_saved": context.get("saved_chars", 0),
        }
    if cache_summary.get("verifier") == "hit" and cache_summary.get("answer") == "hit":
        return _zero_context_engineering()
    raw_chars = sum(len(str(chunk.get("text", ""))) for chunk in chunks)
    packed_chars = sum(
        len(str(chunk.get("summary", ""))) + sum(len(str(snippet)) for snippet in (chunk.get("_snippets") or []))
        for chunk in chunks
    )
    if raw_chars <= 0 or packed_chars <= 0:
        return _zero_context_engineering()
    saved_chars = max(raw_chars - packed_chars, 0)
    context = {
        "ran": True,
        "source": "cache",
        "raw_chars": raw_chars,
        "packed_chars": packed_chars,
        "saved_chars": saved_chars,
        "shrink_percent": round(min(100, max(0, (saved_chars / raw_chars) * 100))),
        "chunk_count": len(chunks),
        "snippet_count": sum(len(chunk.get("_snippets") or []) for chunk in chunks),
    }
    return {
        "context_engineering": context,
        "context_chars_before_packing": raw_chars,
        "context_chars_after_packing": packed_chars,
        "context_chars_saved": saved_chars,
    }


def _zero_context_engineering() -> dict[str, Any]:
    context = {
        "ran": False,
        "source": "cache",
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


def _valid_ids(value: Any, valid_ids: set[str]) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        chunk_id = str(item)
        if chunk_id in valid_ids and chunk_id not in result:
            result.append(chunk_id)
    return result


def _sanitize_answer_citations(answer: str, citation_ids: set[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        chunk_id = match.group(1)
        return f"[[cite:{chunk_id}]]" if chunk_id in citation_ids else ""

    cleaned = _CITE_MARKER_RE.sub(replace, answer)
    cleaned = re.sub(r"[ \t]+([,.;:])", r"\1", cleaned)
    cleaned = re.sub(r"([,;:])(?:[ \t]*[,;:])+", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _citation(chunk: dict[str, Any], number: int) -> dict[str, Any]:
    span = (chunk.get("spans") or [{}])[0]
    text = str(chunk.get("text", ""))
    quote = str((chunk.get("_snippets") or [text])[0]).strip()
    start_char = span.get("start")
    end_char = span.get("end")
    if quote:
        needle = quote.removeprefix("...").removesuffix("...")
        offset = text.find(needle)
        if offset >= 0 and isinstance(start_char, int):
            start_char = start_char + offset
            end_char = start_char + len(needle)
    quote = " ".join(quote.split())[:420]
    return {
        "id": f"citation-{number}",
        "source_chunk_id": chunk["id"],
        "source_input_id": chunk.get("note_id") or chunk["raw_input_id"],
        "exact_quote": quote,
        "raw_text": quote,
        "cleaned_text": chunk.get("summary", ""),
        "start_char": start_char,
        "end_char": end_char,
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
