from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from src.infra.progress import reset_progress_reporters, set_progress_reporters, set_active_parent_ref
from src.services.rag.models import IngestResult, QueryResult, ProgressReporter, NullProgressReporter
from src.services.rag.private.chains.query import QueryAnswerChain, QueryEvidenceChain, QueryVerifierChain, SemanticCacheVerifierChain, build_query_result
from src.services.rag.private.chains.query._search import finalize_chunks
from src.services.rag.private.pipeline.ingest import get_durable_ingest
from src.infra import retrieval_cache
from src.repositories import queries

_QUERY_RESULT_SEMANTIC_THRESHOLD = 0.75


class RagServiceImpl:
    """Run the active source-chunk ingestion recipe.

    The recipe is:
    user text -> save the full text -> split long text into smaller pieces
    -> save each full piece as a source chunk with an LLM-written summary
    -> create recall keys/links -> index chunks for search.

    Source chunks are the durable evidence records. Recall keys/links help
    connect people, topics, and events back to those chunks. Search vectors
    help retrieval find chunks later. Both can be rebuilt from saved chunks.
    """

    def __init__(self, json_client) -> None:
        """Create the fixed chains used by every ingest call."""
        self.query_evidence = QueryEvidenceChain(json_client)
        self.query_verifier = QueryVerifierChain(json_client)
        self.query_answer = QueryAnswerChain(json_client)
        self.semantic_verifier = SemanticCacheVerifierChain(json_client)

    async def resume_pending_jobs(self) -> None:
        """Resume durable jobs after app startup."""
        await get_durable_ingest().resume_pending()

    async def resume_ingest_job(self, job_id: str) -> dict | None:
        """Resume one durable job from the dev route."""
        return await get_durable_ingest().resume_job(job_id)

    def list_ingest_jobs(self, user_id: str | None = None, page: int = 1, limit: int = 20) -> dict[str, Any]:
        """List durable jobs for the dev route (sync: read-only, cheap)."""
        return get_durable_ingest().list_jobs(user_id, page, limit)

    def pause_ingest_job(self, job_id: str) -> dict | None:
        """Pause one durable job."""
        from src.services.rag.private.durability.repository import pause, get
        pause(job_id)
        return get(job_id)

    def stop_ingest_job(self, job_id: str) -> dict | None:
        """Stop/Abort one durable job."""
        from src.services.rag.private.durability.repository import abort, get
        abort(job_id, error="Stopped by user")
        return get(job_id)

    def delete_ingest_job(self, job_id: str) -> bool:
        """Delete one durable job."""
        return get_durable_ingest().delete_job(job_id)

    def reindex_all(self, user_id: str) -> None:
        """Trigger a complete re-indexing for a user by wiping derived data and requeuing."""
        from src.repositories import source_chunks, source_chunk_vectors, recall
        from src.services.rag.private.durability.repository import requeue_all
        source_chunks.delete_all(user_id)
        source_chunk_vectors.reset(user_id)
        recall.delete_all(user_id)
        requeue_all(user_id)

    def reindex_note(self, user_id: str, note_id: str) -> None:
        """Trigger a complete re-indexing for a single note."""
        from src.repositories import source_chunks, source_chunk_vectors, recall
        from src.services.rag.private.durability.repository import requeue_note
        
        page = 1
        while True:
            res = source_chunks.get_paginated_for_note(note_id, user_id, page=page, limit=100)
            chunks = res.get("data", [])
            if not chunks:
                break
            source_chunk_vectors.delete([c["id"] for c in chunks], user_id)
            page += 1
            
        source_chunks.delete_for_note(note_id, user_id)
        recall.delete_for_note(note_id, user_id)
        requeue_note(user_id, note_id)

    async def query(self, data: str, user_id: str, reporter: ProgressReporter | None = None, within_directories: list[str] | None = None, excluding_directories: list[str] | None = None, within_tags: list[str] | None = None, excluding_tags: list[str] | None = None, within_tags_condition: str = "any") -> QueryResult:
        """Search source chunks, expand through recall links, then answer."""
        reporter = reporter or NullProgressReporter()
        query = " ".join(data.split())
        
        if not query:
            trace = {"mode": "empty_query", "query": query, "source_chunk_count": 0}
            answer = {"answer": "Ask a question to search your source chunks.", "citations": [], "directories": [], "notes": []}
            result = build_query_result(query, [], answer, trace)
            asyncio.create_task(asyncio.to_thread(queries.save, user_id, query, 0, result))
            return result

        loop = asyncio.get_running_loop()
        started_at = time.time()
        trace_events: list[dict] = []

        llm_saved_metrics = {"llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        async def async_report(message: str, details: dict | None = None) -> None:
            trace_events.append(_trace_event(message, details))
            if details and details.get("ref") == "llm:usage":
                metrics = details.get("metrics", {})
                llm_saved_metrics["llm_calls"] += 1
                llm_saved_metrics["prompt_tokens"] += metrics.get("prompt_tokens", 0)
                llm_saved_metrics["completion_tokens"] += metrics.get("completion_tokens", 0)
                llm_saved_metrics["total_tokens"] += metrics.get("total_tokens", 0)
            await reporter.report(message, details)

        def sync_report(message: str, details: dict | None = None) -> None:
            loop.call_soon_threadsafe(asyncio.create_task, reporter.report(message, details))

        tokens = set_progress_reporters(async_report, sync_report)
        
        try:
            set_active_parent_ref(None)
            await reporter.report("Checking for identical past questions...", {"depth": 0, "ref": "retrieval:cache_lookup"})

            # Build a stable filter signature once; baked into ALL cache keys so
            # filtered and unfiltered queries never share cache entries.
            filters_sig = _query_filters_signature(
                within_directories or [],
                excluding_directories or [],
                within_tags or [],
                excluding_tags or [],
                within_tags_condition,
            )

            # ── 1. Exact cache (hash lookup, ~1ms, no embedding) ──────────────
            exact_cache_key = _query_exact_cache_key(query, user_id, filters_sig)
            if exact_cache_key:
                exact_cached = await retrieval_cache.get_json(exact_cache_key)
                if isinstance(exact_cached, dict):
                    summary = exact_cached.setdefault("retrieval_trace", {}).setdefault("cache_summary", {})
                    for stage in summary:
                        summary[stage] = "skip"
                    summary["query"] = "exact_hit"
                    exact_cached["retrieval_trace"]["ui"] = _top_level_cache_ui("exact", None, int((time.time() - started_at) * 1000))
                    await reporter.report("Retrieval complete (Exact Cache Hit).", {"depth": 0, "ref": "retrieval:done"})
                    asyncio.create_task(asyncio.to_thread(queries.save, user_id, query, int((time.time() - started_at) * 1000), exact_cached))
                    return exact_cached

            # ── 2. Semantic cache (embedding + vector search) ─────────────────
            cached_match = await retrieval_cache.get_semantic_query_result(
                user_id,
                query,
                threshold=_QUERY_RESULT_SEMANTIC_THRESHOLD,
                emit_progress=False,
                filters_namespace=filters_sig,
            )
            if cached_match:
                cached_payload, cached_query, distance = cached_match
                # Skip the LLM verifier for near-exact matches (distance ≈ 0 means identical query).
                # Only run the verifier for genuinely similar-but-different queries.
                _EXACT_MATCH_EPSILON = 0.02
                if distance is not None and abs(distance) < _EXACT_MATCH_EPSILON:
                    is_safe = True
                else:
                    is_safe = await self.semantic_verifier.run(
                        new_query=query,
                        cached_query=cached_query,
                        cached_answer=cached_payload.get("answer", ""),
                        user_id=user_id,
                        reporter=reporter
                    )
                if is_safe:
                    await reporter.report("Retrieval complete (Cache Hit).", {"depth": 0, "ref": "retrieval:done"})

                    if "retrieval_trace" not in cached_payload:
                        cached_payload["retrieval_trace"] = {}
                    if "cache_summary" not in cached_payload["retrieval_trace"]:
                        cached_payload["retrieval_trace"]["cache_summary"] = {}

                    # Override existing stages to "skip"
                    summary = cached_payload["retrieval_trace"]["cache_summary"]
                    for stage in summary:
                        summary[stage] = "skip"
                    summary["semantic_query"] = "semantic_hit"
                    cached_payload["retrieval_trace"]["ui"] = _top_level_cache_ui("semantic", distance, int((time.time() - started_at) * 1000))

                    asyncio.create_task(asyncio.to_thread(queries.save, user_id, query, int((time.time() - started_at) * 1000), cached_payload))
                    return cached_payload

            await reporter.report("Preparing search...", {"depth": 0, "ref": "retrieval:normalize", "query_chars": len(query)})
            
            set_active_parent_ref("retrieval:evidence")
            await reporter.report("Gathering relevant notes and context...", {
                "depth": 0,
                "ref": "retrieval:evidence",
                "within_directories": within_directories or [],
                "excluding_directories": excluding_directories or [],
                "within_tags": within_tags or [],
                "excluding_tags": excluding_tags or [],
                "within_tags_condition": within_tags_condition,
            })
            chunks, trace = await self.query_evidence.run(query, user_id, reporter, within_directories, excluding_directories, within_tags, excluding_tags, within_tags_condition)
            # Evidence-search exact cache is inside QueryEvidenceChain, before verifier.
            
            set_active_parent_ref("retrieval:verify")
            await reporter.report("Reviewing gathered information...", {"depth": 0, "ref": "retrieval:verify"})
            verification = await self.query_verifier.run(query, chunks, user_id, reporter, attempt=1)
            trace.setdefault("cache_events", []).extend(verification.pop("_cache_events", []))
            chunks = _verified_chunks(chunks, verification)
            trace["verification_attempts"] = [verification]

            retry_query = verification.get("retry_query") or ""
            if verification.get("status") == "needs_retry" and retry_query and retry_query.lower() != query.lower():
                set_active_parent_ref("retrieval:retry")
                await reporter.report(
                    "Refining search to find better answers...",
                    {"depth": 0, "ref": "retrieval:retry", "retry_query": retry_query},
                )
                retry_chunks, retry_trace = await self.query_evidence.run(
                    retry_query,
                    user_id,
                    reporter,
                    within_directories,
                    excluding_directories,
                    within_tags,
                    excluding_tags,
                    within_tags_condition,
                )
                combined_chunks, combine_trace = finalize_chunks([*chunks, *retry_chunks], query)
                
                set_active_parent_ref("retrieval:verify:retry")
                await reporter.report("Reviewing refined information...", {"depth": 0, "ref": "retrieval:verify:retry"})
                retry_verification = await self.query_verifier.run(query, combined_chunks, user_id, reporter, attempt=2)
                trace.setdefault("cache_events", []).extend(retry_trace.get("cache_events") or [])
                trace.setdefault("cache_events", []).extend(retry_verification.pop("_cache_events", []))
                chunks = _verified_chunks(combined_chunks, retry_verification)
                trace["verification_attempts"].append(retry_verification)
                trace["retry_query"] = retry_query
                trace["retry_trace"] = retry_trace
                trace["retry_context_pack"] = combine_trace

            trace["verification"] = trace["verification_attempts"][-1]
            trace["verified_source_chunk_ids"] = [chunk["id"] for chunk in chunks]
            trace["verified_source_chunk_count"] = len(chunks)

            set_active_parent_ref("retrieval:answer")
            await reporter.report("Writing your final answer...", {"depth": 0, "ref": "retrieval:answer", "source_chunk_count": len(chunks)})
            answer = await self.query_answer.run(query, chunks, user_id, reporter)
            trace.setdefault("cache_events", []).extend(answer.pop("_cache_events", []))
            
            set_active_parent_ref(None)
            trace["llm_saved_metrics"] = llm_saved_metrics
            trace["trace_events"] = trace_events
            trace["duration_ms"] = int((time.time() - started_at) * 1000)
            result = build_query_result(query, chunks, answer, trace)
            
            # Save the full result to both exact cache (instant next hit) and semantic cache (fuzzy)
            if exact_cache_key:
                await retrieval_cache.set_json(exact_cache_key, result)
            await retrieval_cache.set_semantic_query_result(user_id, query, result, filters_namespace=filters_sig)
            
            await reporter.report(
                "Retrieval complete.",
                {
                    "depth": 0,
                    "ref": "retrieval:done",
                    "citation_count": len(answer.get("citation_ids", [])),
                    "cache_summary": result["retrieval_trace"].get("cache_summary", {}),
                    "context_engineering": result["retrieval_trace"].get("context_engineering", {}),
                },
            )
        finally:
            reset_progress_reporters(tokens)
            set_active_parent_ref(None)
        
        asyncio.create_task(asyncio.to_thread(queries.save, user_id, query, int((time.time() - started_at) * 1000), result))
        return result


def _verified_chunks(chunks: list[dict], verification: dict) -> list[dict]:
    on_topic_ids = verification.get("on_topic_ids") or []
    if on_topic_ids:
        allowed = set(on_topic_ids)
        return [chunk for chunk in chunks if chunk["id"] in allowed]
    off_topic_ids = set(verification.get("off_topic_ids") or [])
    if off_topic_ids:
        return [chunk for chunk in chunks if chunk["id"] not in off_topic_ids]
    return chunks


def _query_exact_cache_key(query: str, user_id: str | None, filters_sig: str = "") -> str | None:
    """Deterministic cache key for the top-level query result.

    Keyed on query text + LLM settings + active filters so that:
    - Changing model/temperature correctly invalidates the cached answer.
    - Changing directory/tag filters produces a different key (no cross-contamination).
    """
    signature = retrieval_cache.llm_settings_signature(user_id)
    if not signature:
        return None
    return retrieval_cache.cache_key("query_result:v1", user_id or "", signature, filters_sig, query)


def _query_filters_signature(
    within_directories: list[str],
    excluding_directories: list[str],
    within_tags: list[str],
    excluding_tags: list[str],
    within_tags_condition: str,
) -> str:
    """Stable short hash of all active query filters.

    Empty string when no filters are active (unfiltered queries use the default
    namespace so existing cached results stay valid without invalidation).
    """
    if not any([within_directories, excluding_directories, within_tags, excluding_tags]):
        return ""
    import json as _json
    payload = _json.dumps({
        "wd": sorted(within_directories),
        "ed": sorted(excluding_directories),
        "wt": sorted(within_tags),
        "et": sorted(excluding_tags),
        "wc": within_tags_condition,
    }, separators=(",", ":"))
    import hashlib as _hashlib
    return _hashlib.sha256(payload.encode()).hexdigest()[:16]


def _trace_event(message: str, details: dict | None) -> dict:
    details = details or {}
    return {
        "message": message,
        "ref": details.get("ref"),
        "parent_ref": details.get("parent_ref"),
        "depth": details.get("depth", 0),
        "details": details,
    }


def _top_level_cache_ui(mode: str, distance: float | None, duration_ms: int) -> dict:
    label = "Exact cache" if mode == "exact" else "Semantic cache"
    detail = "Same query reused." if mode == "exact" else f"Verifier approved similar answer; distance {distance:.3f}."
    return {
        "summary": [
            {"id": "duration", "label": "Time", "value": f"{duration_ms} ms", "detail": "Returned before retrieval", "tone": "success"},
            {"id": "cache", "label": "Cache", "value": "Hit", "detail": label, "tone": "success"},
            {"id": "skipped", "label": "Steps skipped", "value": "Retrieval + LLM", "detail": "Full answer reused", "tone": "warning"},
        ],
        "flow": [
            {
                "id": "query_cache",
                "title": label,
                "subtitle": detail,
                "type": "cache",
                "status": "hit",
                "metrics": {"duration_ms": duration_ms},
                "badges": ["hit", "skipped downstream"],
                "children": [],
            }
        ],
        "savings": {
            "cache_hits": 1,
            "cache_misses": 0,
            "cache_sets": 0,
            "steps_skipped": ["breakdown", "subjects", "evidence", "verifier", "answer"],
            "llm_calls_saved": 2,
        },
    }
