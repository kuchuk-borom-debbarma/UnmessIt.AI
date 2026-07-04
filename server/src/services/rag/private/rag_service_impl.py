from __future__ import annotations

import asyncio
from uuid import uuid4

from src.infra.progress import reset_progress_reporters, set_progress_reporters, set_active_parent_ref
from src.services.rag.models import IngestResult, QueryResult, ProgressReporter, NullProgressReporter
from src.services.rag.private.chains.query import QueryAnswerChain, QueryEvidenceChain, QueryVerifierChain, SemanticCacheVerifierChain, build_query_result
from src.services.rag.private.chains.query._search import finalize_chunks
from src.services.rag.private.pipeline.ingest import get_durable_ingest
from src.infra import retrieval_cache


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

    async def query(self, data: str, user_id: str, reporter: ProgressReporter | None = None, within_directories: list[str] | None = None, excluding_directories: list[str] | None = None, within_tags: list[str] | None = None, excluding_tags: list[str] | None = None, within_tags_condition: str = "any") -> QueryResult:
        """Search source chunks, expand through recall links, then answer."""
        reporter = reporter or NullProgressReporter()
        query = " ".join(data.split())
        
        if not query:
            trace = {"mode": "empty_query", "query": query, "source_chunk_count": 0}
            answer = {"answer": "Ask a question to search your source chunks.", "citations": [], "directories": [], "notes": []}
            return build_query_result(query, [], answer, trace)

        loop = asyncio.get_running_loop()

        llm_saved_metrics = {"llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        async def async_report(message: str, details: dict | None = None) -> None:
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
            
            cached_match = await retrieval_cache.get_semantic_query_result(user_id, query, threshold=0.95, emit_progress=False)
            if cached_match:
                cached_payload, cached_query, distance = cached_match
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
            result = build_query_result(query, chunks, answer, trace)
            
            # Save the full result to the semantic cache
            await retrieval_cache.set_semantic_query_result(user_id, query, result)
            
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
