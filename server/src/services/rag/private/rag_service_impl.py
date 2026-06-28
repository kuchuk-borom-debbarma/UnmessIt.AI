from __future__ import annotations

from uuid import uuid4

from src.services.rag.models import IngestResult, QueryResult
from src.services.rag.private.chains.preprocess import NoopPreprocessChain
from src.services.rag.private.chains.query import QueryAnswerChain, QueryEvidenceChain, build_query_result
from src.services.rag.private.chains.recall.index import RecallIndexChain
from src.services.rag.private.chains.source_chunk_assembler import SourceChunkAssemblerChain
from src.services.rag.private.chains.source_chunk_drafts import SourceChunkDraftChain
from src.services.rag.private.chains.source_windows import SourceWindowChain
from src.services.rag.private.durability import DurableIngest


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
        self.preprocess = NoopPreprocessChain()
        self.source_windows = SourceWindowChain()
        self.source_chunk_drafts = SourceChunkDraftChain(json_client)
        self.source_chunk_assembler = SourceChunkAssemblerChain()
        self.recall_index = RecallIndexChain(json_client)
        self.query_evidence = QueryEvidenceChain(json_client)
        self.query_answer = QueryAnswerChain(json_client)
        self.durability = DurableIngest(
            self.preprocess,
            self.source_windows,
            self.source_chunk_drafts,
            self.source_chunk_assembler,
            self.recall_index,
        )

    def ingest(self, data: str, job_id: str | None = None) -> IngestResult:
        """Submit durable ingestion and return the durable job id."""
        job_id = job_id or str(uuid4())
        job = self.durability.submit(data, job_id)
        return {
            "job_id": job["id"],
            "status": job["status"],
            "raw_input_id": job["raw_input_id"] or "",
            "source_chunks": [],
            "analysis": {
                "stage": job["stage"],
                "attempt_count": job["attempt_count"],
                "metadata": job["metadata"],
            },
        }

    def resume_pending_jobs(self) -> None:
        """Resume durable jobs after app startup."""
        self.durability.resume_pending()

    def resume_ingest_job(self, job_id: str) -> dict | None:
        """Resume one durable job from the dev route."""
        return self.durability.resume_job(job_id)

    def list_ingest_jobs(self) -> list[dict]:
        """List durable jobs for the dev route."""
        return self.durability.list_jobs()

    def query(self, data: str) -> QueryResult:
        """Search source chunks, expand through recall links, then answer."""
        query = " ".join(data.split())
        if not query:
            trace = {"mode": "empty_query", "query": query, "source_chunk_count": 0}
            answer = {"answer": "Ask a question to search your source chunks.", "citation_ids": []}
            return build_query_result(query, [], answer, trace)
        chunks, trace = self.query_evidence.run(query)
        answer = self.query_answer.run(query, chunks)
        return build_query_result(query, chunks, answer, trace)
