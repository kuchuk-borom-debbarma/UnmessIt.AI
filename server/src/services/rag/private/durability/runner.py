from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from src.repositories import recall, recall_key_vectors, source_chunk_vectors, source_chunks
from src.services.rag.models import SourceChunk, SourceChunkDraft, SourceWindow
from . import repository
from .models import (
    STAGE_RECALL,
    STAGE_RECALL_VECTORS,
    STAGE_RAW_INPUT,
    STAGE_SOURCE_CHUNKS,
    STAGE_SOURCE_VECTORS,
)

logger = logging.getLogger(__name__)


class IngestGraphState(TypedDict, total=False):
    """State passed between LangGraph ingest stage nodes."""

    job_id: str
    raw_input_id: str
    raw_text: str
    user_id: str
    chunks: list[SourceChunk]
    recall_keys: list[dict[str, Any]]
    corrupt: bool
    abort_reason: str
    directory_path: str | None


class DurableIngestRunner:
    """Run one durable ingest job through the async LangGraph stage workflow."""

    def __init__(self, source_windows, source_chunk_drafts, source_chunk_assembler, recall_index) -> None:
        """Receive existing chains; durability only coordinates checkpoints."""
        self.source_windows = source_windows
        self.source_chunk_drafts = source_chunk_drafts
        self.source_chunk_assembler = source_chunk_assembler
        self.recall_index = recall_index
        self.graph = self._build_graph()

    async def run_once(self, job_id: str) -> None:
        """Run until complete or until one graph node schedules retry."""
        job = await asyncio.to_thread(repository.get, job_id)
        if not job:
            return
        await self.graph.ainvoke({"job_id": job_id})

    def _build_graph(self):
        """Build the fixed durable ingest workflow once per runner."""
        graph = StateGraph(IngestGraphState)
        graph.add_node("load_raw_input", self._load_raw_input)
        graph.add_node("source_chunks", self._source_chunk_node)
        graph.add_node("recall", self._recall_node)
        graph.add_node("recall_vectors", self._recall_vector_node)
        graph.add_node("source_vectors", self._source_vector_node)
        graph.add_node("complete", self._complete_node)
        graph.add_node("abort", self._abort_node)
        graph.add_edge(START, "load_raw_input")
        graph.add_conditional_edges("load_raw_input", self._after_load_raw_input, {"abort": "abort", "continue": "source_chunks"})
        graph.add_edge("source_chunks", "recall")
        graph.add_edge("recall", "recall_vectors")
        graph.add_edge("recall_vectors", "source_vectors")
        graph.add_edge("source_vectors", "complete")
        graph.add_edge("complete", END)
        graph.add_edge("abort", END)
        return graph.compile()

    async def _load_raw_input(self, state: IngestGraphState) -> IngestGraphState:
        """Load source truth before any derived work runs."""
        job_id = state["job_id"]
        job = await asyncio.to_thread(repository.get, job_id)
        if not job or not job["raw_input_id"]:
            return {**state, "corrupt": True, "abort_reason": "raw input missing from ingest job"}

        raw_input = await asyncio.to_thread(_raw_input, job["raw_input_id"])
        if not raw_input:
            return {**state, "raw_input_id": job["raw_input_id"], "corrupt": True, "abort_reason": "raw input row missing"}

        raw_text = raw_input["content"]
        directory_path = await asyncio.to_thread(_directory_path, job_id)
        await asyncio.to_thread(repository.start_stage, job_id, STAGE_RAW_INPUT)
        await asyncio.to_thread(repository.complete_checkpoint, job_id, STAGE_RAW_INPUT, f"raw_input:{job['raw_input_id']}", job["raw_input_id"])
        return {**state, "raw_input_id": job["raw_input_id"], "raw_text": raw_text, "user_id": raw_input["user_id"], "directory_path": directory_path}

    def _after_load_raw_input(self, state: IngestGraphState) -> Literal["abort", "continue"]:
        """Branch corrupt jobs away from retryable ingest work."""
        return "abort" if state.get("corrupt") else "continue"

    async def _abort_node(self, state: IngestGraphState) -> IngestGraphState:
        """Abort corrupt jobs because missing source truth cannot be retried."""
        raw_input_id = state.get("raw_input_id")
        if raw_input_id:
            await asyncio.to_thread(source_chunks.delete_by_raw_input_id, raw_input_id)
        await asyncio.to_thread(repository.abort, state["job_id"], state.get("abort_reason", "ingest job is corrupt"), {"raw_input_id": raw_input_id})
        logger.info("ingest_job_aborted job_id=%s reason=%s", state["job_id"], state.get("abort_reason"))
        return state

    async def _source_chunk_node(self, state: IngestGraphState) -> IngestGraphState:
        """Build or reuse source chunks before recall work."""
        chunks = await self._source_chunks(state["job_id"], state["raw_input_id"], state["raw_text"], state["user_id"], state.get("directory_path"))
        return {**state, "chunks": chunks}

    async def _recall_node(self, state: IngestGraphState) -> IngestGraphState:
        """Build recall links from saved source chunks."""
        await self._recall(state["job_id"], state["raw_text"], state["user_id"], state["chunks"])
        return state

    async def _recall_vector_node(self, state: IngestGraphState) -> IngestGraphState:
        """Index recall keys connected to this job's source chunks."""
        recall_keys = await asyncio.to_thread(recall.keys_for_source_chunks, [chunk["id"] for chunk in state["chunks"]], state["user_id"])
        await self._recall_vectors(state["job_id"], recall_keys)
        return {**state, "recall_keys": recall_keys}

    async def _source_vector_node(self, state: IngestGraphState) -> IngestGraphState:
        """Index saved source chunks after recall-key vectors."""
        await self._source_vectors(state["job_id"], state["chunks"])
        return state

    async def _complete_node(self, state: IngestGraphState) -> IngestGraphState:
        """Persist final counts after every graph stage succeeds."""
        job_id = state["job_id"]
        chunks = state.get("chunks", [])
        recall_keys = state.get("recall_keys", [])
        await asyncio.to_thread(repository.complete, job_id, {
            "raw_input_id": state.get("raw_input_id"),
            "source_chunks": len(chunks),
            "recall_keys": len(recall_keys),
        })
        logger.info("ingest_job_complete job_id=%s source_chunks=%s recall_keys=%s", job_id, len(chunks), len(recall_keys))
        return state

    async def _source_chunks(self, job_id: str, raw_input_id: str, raw_text: str, user_id: str, directory_path: str | None) -> list[SourceChunk]:
        """Create chunks for only unfinished text pieces."""
        await asyncio.to_thread(repository.start_stage, job_id, STAGE_SOURCE_CHUNKS)
        existing = await asyncio.to_thread(source_chunks.get_by_raw_input_id, raw_input_id)
        has_checkpoints = await asyncio.to_thread(repository.has_stage_checkpoints, job_id, STAGE_SOURCE_CHUNKS)
        if existing and not has_checkpoints:
            logger.info("ingest_stage_reuse job_id=%s stage=%s count=%s", job_id, STAGE_SOURCE_CHUNKS, len(existing))
            return existing

        for text_piece in self.source_windows.run(raw_text, user_id):
            unit_key = _source_piece_key(raw_input_id, text_piece)
            is_done = await asyncio.to_thread(repository.checkpoint_complete, job_id, STAGE_SOURCE_CHUNKS, unit_key)
            if is_done:
                logger.info("ingest_unit_reuse job_id=%s stage=%s unit=%s", job_id, STAGE_SOURCE_CHUNKS, unit_key)
                continue
            await self._run_unit(job_id, STAGE_SOURCE_CHUNKS, unit_key, lambda tp=text_piece: self._build_source_piece(raw_input_id, raw_text, user_id, tp, unit_key, directory_path))
        return await asyncio.to_thread(source_chunks.get_by_raw_input_id, raw_input_id)

    async def _build_source_piece(self, raw_input_id: str, raw_text: str, user_id: str, text_piece: SourceWindow, unit_key: str, directory_path: str | None) -> tuple[str, dict[str, Any]]:
        """Summarize one text piece, then save the full piece as evidence."""
        drafts: list[SourceChunkDraft] = await self.source_chunk_drafts.run(text_piece, user_id)
        chunks = await self.source_chunk_assembler.run(raw_input_id, raw_text, user_id, drafts, directory_path)
        for index, chunk in enumerate(chunks):
            chunk["id"] = _stable_id("source_chunk", unit_key, str(index), chunk["text"])
        await asyncio.to_thread(source_chunks.save_many, chunks)
        chunk_ids = [chunk["id"] for chunk in chunks]
        return ",".join(chunk_ids), {"source_chunk_ids": chunk_ids}

    async def _recall(self, job_id: str, raw_text: str, user_id: str, chunks: list[SourceChunk]) -> None:
        """Create recall links only for chunks without completed recall work."""
        await asyncio.to_thread(repository.start_stage, job_id, STAGE_RECALL)
        linked_chunk_ids = await asyncio.to_thread(recall.source_chunks_with_links, [chunk["id"] for chunk in chunks], user_id)
        for chunk in chunks:
            unit_key = f"recall_chunk:{chunk['id']}"
            is_done = await asyncio.to_thread(repository.checkpoint_complete, job_id, STAGE_RECALL, unit_key)
            if is_done or chunk["id"] in linked_chunk_ids:
                await asyncio.to_thread(repository.complete_checkpoint, job_id, STAGE_RECALL, unit_key, chunk["id"], {"reused": True})
                logger.info("ingest_unit_reuse job_id=%s stage=%s unit=%s", job_id, STAGE_RECALL, unit_key)
                continue
            await self._run_unit(job_id, STAGE_RECALL, unit_key, lambda c=chunk: self._build_recall(raw_text, user_id, c))

    async def _build_recall(self, raw_text: str, user_id: str, chunk: SourceChunk) -> tuple[str, dict[str, Any]]:
        """Run recall indexing for one source chunk."""
        index = await self.recall_index.run(raw_text, user_id, [chunk])
        logger.info(
            "ingest_recall_index_result chunk_id=%s keys=%s links=%s analysis=%s",
            chunk["id"],
            len(index["recall_keys"]),
            len(index["recall_links"]),
            index.get("analysis", {}),
        )
        if not index["recall_links"]:
            raise ValueError("recall produced no links")
        saved_links = await asyncio.to_thread(recall.save_index, index, user_id)
        logger.info("ingest_recall_saved chunk_id=%s saved_links=%s", chunk["id"], saved_links)
        return chunk["id"], {"saved_links": saved_links, "recall_keys": [key["id"] for key in index["recall_keys"]]}

    async def _recall_vectors(self, job_id: str, keys: list[dict[str, Any]]) -> None:
        """Index only missing recall-key vectors."""
        await asyncio.to_thread(repository.start_stage, job_id, STAGE_RECALL_VECTORS)
        for key in keys:
            unit_key = f"recall_key_vector:{key['id']}"
            is_done = await asyncio.to_thread(repository.checkpoint_complete, job_id, STAGE_RECALL_VECTORS, unit_key)
            exists = await asyncio.to_thread(recall_key_vectors.exists, key["id"], key["user_id"])
            if is_done or exists:
                await asyncio.to_thread(repository.complete_checkpoint, job_id, STAGE_RECALL_VECTORS, unit_key, key["id"], {"reused": True})
                continue
            await self._run_unit(job_id, STAGE_RECALL_VECTORS, unit_key, lambda k=key: _index_recall_key(k))

    async def _source_vectors(self, job_id: str, chunks: list[SourceChunk]) -> None:
        """Index only missing source chunk vectors."""
        await asyncio.to_thread(repository.start_stage, job_id, STAGE_SOURCE_VECTORS)
        for chunk in chunks:
            unit_key = f"source_vector:{chunk['id']}"
            is_done = await asyncio.to_thread(repository.checkpoint_complete, job_id, STAGE_SOURCE_VECTORS, unit_key)
            exists = await asyncio.to_thread(source_chunk_vectors.exists, chunk["id"], chunk["user_id"])
            if is_done or exists:
                await asyncio.to_thread(repository.complete_checkpoint, job_id, STAGE_SOURCE_VECTORS, unit_key, chunk["id"], {"reused": True})
                continue
            await self._run_unit(job_id, STAGE_SOURCE_VECTORS, unit_key, lambda c=chunk: _index_source_chunk(c))

    async def _run_unit(self, job_id: str, stage: str, unit_key: str, work) -> None:
        """Run one unit and convert failures into durable retry state."""
        await asyncio.to_thread(repository.start_checkpoint, job_id, stage, unit_key)
        logger.info("ingest_unit_start job_id=%s stage=%s unit=%s", job_id, stage, unit_key)
        try:
            output_ref, metadata = await work()
            await asyncio.to_thread(repository.complete_checkpoint, job_id, stage, unit_key, output_ref, metadata)
            await asyncio.to_thread(repository.reset_attempts, job_id)
            logger.info("ingest_unit_complete job_id=%s stage=%s unit=%s", job_id, stage, unit_key)
        except Exception as exc:
            await asyncio.to_thread(repository.fail_checkpoint, job_id, stage, unit_key, str(exc))
            job = await asyncio.to_thread(repository.schedule_retry, job_id, stage, unit_key, str(exc))
            logger.info(
                "ingest_unit_retry job_id=%s stage=%s unit=%s status=%s attempt=%s error=%s",
                job_id, stage, unit_key, job["status"], job["attempt_count"], str(exc),
            )
            raise


async def _index_recall_key(key: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    await asyncio.to_thread(recall_key_vectors.index, [key])
    return key["id"], {}


async def _index_source_chunk(chunk: SourceChunk) -> tuple[str, dict[str, Any]]:
    await asyncio.to_thread(source_chunk_vectors.index, [chunk])
    return chunk["id"], {}


def _raw_input(raw_input_id: str) -> dict[str, Any] | None:
    from src.repositories import raw_inputs
    return raw_inputs.get(raw_input_id)


def _source_piece_key(raw_input_id: str, text_piece: SourceWindow) -> str:
    """Content-bound unit key lets resume skip exactly completed text pieces."""
    digest = hashlib.sha256(text_piece["text"].encode("utf-8")).hexdigest()
    return f"source_piece:{raw_input_id}:{text_piece['start']}:{text_piece['end']}:{digest}"


def _stable_id(*parts: str) -> str:
    """Stable IDs make save-after-crash idempotent even before checkpoint completion."""
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest

def _directory_path(job_id: str) -> str | None:
    from src.infra.sqlite import get_connection
    row = get_connection().execute(
        "SELECT d.path FROM notes n JOIN directories d ON d.id = n.directory_id WHERE n.id = ?",
        (job_id,)
    ).fetchone()
    return row["path"] if row else None
