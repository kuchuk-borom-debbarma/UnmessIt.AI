from __future__ import annotations

from uuid import uuid4

from src.services.rag.models import IngestResult, QueryResult, ProgressReporter, NullProgressReporter
from src.services.rag.private.chains.query import QueryAnswerChain, QueryEvidenceChain, build_query_result
from src.services.rag.private.pipeline.ingest import get_durable_ingest


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
        self.query_answer = QueryAnswerChain(json_client)

    async def resume_pending_jobs(self) -> None:
        """Resume durable jobs after app startup."""
        await get_durable_ingest().resume_pending()

    async def resume_ingest_job(self, job_id: str) -> dict | None:
        """Resume one durable job from the dev route."""
        return await get_durable_ingest().resume_job(job_id)

    def list_ingest_jobs(self, user_id: str | None = None) -> list[dict]:
        """List durable jobs for the dev route (sync: read-only, cheap)."""
        return get_durable_ingest().list_jobs(user_id)

    def delete_ingest_job(self, job_id: str) -> bool:
        """Delete one durable job."""
        return get_durable_ingest().delete_job(job_id)

    async def query(self, data: str, user_id: str, reporter: ProgressReporter | None = None) -> QueryResult:
        """Search source chunks, expand through recall links, then answer."""
        reporter = reporter or NullProgressReporter()
        query = " ".join(data.split())
        
        if not query:
            trace = {"mode": "empty_query", "query": query, "source_chunk_count": 0}
            answer = {"answer": "Ask a question to search your source chunks.", "citations": [], "directories": [], "notes": []}
            return build_query_result(query, [], answer, trace)
            
        await reporter.report("Searching source-backed evidence...")
        chunks, trace = await self.query_evidence.run(query, user_id, reporter)
        answer = await self.query_answer.run(query, chunks, user_id)
        
        return build_query_result(query, chunks, answer, trace)
