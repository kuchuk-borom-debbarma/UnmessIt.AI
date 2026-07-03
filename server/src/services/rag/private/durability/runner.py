from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from src.infra.progress import get_last_llm_rotation_snapshot, reset_progress_reporters, set_progress_reporters
from src.infra.settings import NoActivePresetError, get_user_settings
from src.repositories import recall, recall_key_vectors, source_chunk_vectors, source_chunks
from src.services.rag.models import SourceChunk, SourceChunkDraft, SourceWindow
from . import repository
from .models import (
    STAGE_RECALL,
    STAGE_RECALL_VECTORS,
    STAGE_RAW_INPUT,
    STAGE_SOURCE_CHUNKS,
    STAGE_SOURCE_VECTORS,
    STATUS_PAUSED,
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
        if not job or job["status"] == STATUS_PAUSED:
            return
        try:
            await self.graph.ainvoke({"job_id": job_id})
        except repository.IngestPaused:
            return

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
        await asyncio.to_thread(repository.update_metadata, job_id, {
            "raw_input_id": job["raw_input_id"],
            "input_chars": len(raw_text),
            "directory_path": directory_path or "",
        })
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
        await asyncio.to_thread(repository.update_metadata, state["job_id"], {"recall_vector_count": len(recall_keys)})
        return {**state, "recall_keys": recall_keys}

    async def _source_vector_node(self, state: IngestGraphState) -> IngestGraphState:
        """Index saved source chunks after recall-key vectors."""
        await self._source_vectors(state["job_id"], state["chunks"])
        await asyncio.to_thread(repository.update_metadata, state["job_id"], {"source_vector_count": len(state["chunks"])})
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
            "progress_message": _progress("Complete", 0, "complete"),
        })
        logger.info("ingest_job_complete job_id=%s source_chunks=%s recall_keys=%s", job_id, len(chunks), len(recall_keys))
        return state

    async def _source_chunks(self, job_id: str, raw_input_id: str, raw_text: str, user_id: str, directory_path: str | None) -> list[SourceChunk]:
        """Create chunks for only unfinished text pieces."""
        await asyncio.to_thread(repository.start_stage, job_id, STAGE_SOURCE_CHUNKS)
        await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress("Building source chunks", 0, STAGE_SOURCE_CHUNKS)})
        windows = list(self.source_windows.run(raw_text, user_id))
        await asyncio.to_thread(repository.update_metadata, job_id, {"source_window_count": len(windows)})
        existing = await asyncio.to_thread(source_chunks.get_by_raw_input_id, raw_input_id)
        has_checkpoints = await asyncio.to_thread(repository.has_stage_checkpoints, job_id, STAGE_SOURCE_CHUNKS)
        if existing and not has_checkpoints:
            await asyncio.to_thread(repository.update_metadata, job_id, {
                "source_chunk_count": len(existing),
                "source_chunks_reused": len(existing),
            })
            await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress(f"Reused {len(existing)} source chunk(s)", 1, f"{STAGE_SOURCE_CHUNKS}:reuse", STAGE_SOURCE_CHUNKS)})
            logger.info("ingest_stage_reuse job_id=%s stage=%s count=%s", job_id, STAGE_SOURCE_CHUNKS, len(existing))
            return existing

        for index, text_piece in enumerate(windows):
            unit_key = _source_piece_key(raw_input_id, text_piece)
            is_done = await asyncio.to_thread(repository.checkpoint_complete, job_id, STAGE_SOURCE_CHUNKS, unit_key)
            if is_done:
                logger.info("ingest_unit_reuse job_id=%s stage=%s unit=%s", job_id, STAGE_SOURCE_CHUNKS, unit_key)
                continue
            await self._run_unit(job_id, STAGE_SOURCE_CHUNKS, unit_key, lambda tp=text_piece, idx=index, tot=len(windows): self._build_source_piece(job_id, idx, tot, raw_input_id, raw_text, user_id, tp, unit_key, directory_path), user_id)
            current_chunks = await asyncio.to_thread(source_chunks.get_by_raw_input_id, raw_input_id)
            await asyncio.to_thread(repository.update_metadata, job_id, {"source_chunk_count": len(current_chunks)})
        chunks = await asyncio.to_thread(source_chunks.get_by_raw_input_id, raw_input_id)
        await asyncio.to_thread(repository.update_metadata, job_id, {"source_chunk_count": len(chunks)})
        return chunks

    async def _build_source_piece(self, job_id: str, index: int, total: int, raw_input_id: str, raw_text: str, user_id: str, text_piece: SourceWindow, unit_key: str, directory_path: str | None) -> tuple[str, dict[str, Any]]:
        """Summarize one text piece, then save the full piece as evidence."""
        snippet = (text_piece["text"][:25].replace('\n', ' ') + "...") if len(text_piece["text"]) > 25 else text_piece["text"].replace('\n', ' ')
        parent_ref = f"{STAGE_SOURCE_CHUNKS}:{unit_key}"
        await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress(f"Chunk {index + 1}/{total}: \"{snippet}\"", 2, parent_ref, STAGE_SOURCE_CHUNKS)})
        await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress("Drafting summary", 3, f"{parent_ref}:draft", parent_ref)})

        async def on_draft_progress(msg: str) -> None:
            await asyncio.to_thread(
                repository.update_metadata,
                job_id,
                {"progress_message": _progress(msg, 3, f"{parent_ref}:draft:cache", f"{parent_ref}:draft")},
            )

        drafts: list[SourceChunkDraft] = await self.source_chunk_drafts.run(text_piece, user_id, on_draft_progress)

        await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress("Assembling source chunk", 3, f"{parent_ref}:assemble", parent_ref)})
        chunks = await self.source_chunk_assembler.run(raw_input_id, raw_text, user_id, drafts, directory_path)

        await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress("Saving source chunk", 3, f"{parent_ref}:save", parent_ref)})
        processing_snapshot = _processing_snapshot(user_id)
        rotation_snapshot = get_last_llm_rotation_snapshot()
        for c_idx, chunk in enumerate(chunks):
            chunk["id"] = _stable_id("source_chunk", unit_key, str(c_idx), chunk["text"])
            chunk["metadata"] = {
                **(chunk.get("metadata") or {}),
                "processing_settings": processing_snapshot,
                "llm_rotation_preset": rotation_snapshot,
            }
        await asyncio.to_thread(source_chunks.save_many, chunks)
        chunk_ids = [chunk["id"] for chunk in chunks]
        return ",".join(chunk_ids), {"source_chunk_ids": chunk_ids, "processing_settings": processing_snapshot, "llm_rotation_preset": rotation_snapshot}

    async def _recall(self, job_id: str, raw_text: str, user_id: str, chunks: list[SourceChunk]) -> None:
        """Create recall links only for chunks without completed recall work."""
        await asyncio.to_thread(repository.start_stage, job_id, STAGE_RECALL)
        await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress("Building recall links", 0, STAGE_RECALL)})
        await asyncio.to_thread(repository.update_metadata, job_id, {"recall_chunk_count": len(chunks)})
        linked_chunk_ids = await asyncio.to_thread(recall.source_chunks_with_links, [chunk["id"] for chunk in chunks], user_id)
        for index, chunk in enumerate(chunks):
            unit_key = f"recall_chunk:{chunk['id']}"
            is_done = await asyncio.to_thread(repository.checkpoint_complete, job_id, STAGE_RECALL, unit_key)
            if is_done or chunk["id"] in linked_chunk_ids:
                await asyncio.to_thread(repository.complete_checkpoint, job_id, STAGE_RECALL, unit_key, chunk["id"], {"reused": True})
                await self._update_recall_counts(job_id, chunks, user_id)
                logger.info("ingest_unit_reuse job_id=%s stage=%s unit=%s", job_id, STAGE_RECALL, unit_key)
                continue
            await self._run_unit(job_id, STAGE_RECALL, unit_key, lambda c=chunk, idx=index, tot=len(chunks): self._build_recall(job_id, idx, tot, raw_text, user_id, c), user_id)
            await self._update_recall_counts(job_id, chunks, user_id)

    async def _update_recall_counts(self, job_id: str, chunks: list[SourceChunk], user_id: str) -> None:
        """Refresh job-level recall counters from saved evidence."""
        chunk_ids = [chunk["id"] for chunk in chunks]
        recall_keys = await asyncio.to_thread(recall.keys_for_source_chunks, chunk_ids, user_id)
        recall_link_count = await asyncio.to_thread(recall.count_links_for_source_chunks, chunk_ids, user_id)
        await asyncio.to_thread(repository.update_metadata, job_id, {
            "recall_key_count": len(recall_keys),
            "recall_link_count": recall_link_count,
        })

    async def _build_recall(self, job_id: str, index: int, total: int, raw_text: str, user_id: str, chunk: SourceChunk) -> tuple[str, dict[str, Any]]:
        """Run recall indexing for one source chunk."""
        snippet = (chunk["text"][:25].replace('\n', ' ') + "...") if len(chunk["text"]) > 25 else chunk["text"].replace('\n', ' ')
        
        async def on_progress(msg: str):
            await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress(msg, 3, f"{STAGE_RECALL}:recall_chunk:{chunk['id']}:{_ref_part(msg)}", f"{STAGE_RECALL}:recall_chunk:{chunk['id']}")})
            
        await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress(f"Recall chunk {index + 1}/{total}: \"{snippet}\"", 2, f"{STAGE_RECALL}:recall_chunk:{chunk['id']}", STAGE_RECALL)})
        index_result = await self.recall_index.run(raw_text, user_id, [chunk], on_progress)
        logger.info(
            "ingest_recall_index_result chunk_id=%s keys=%s links=%s analysis=%s",
            chunk["id"],
            len(index_result["recall_keys"]),
            len(index_result["recall_links"]),
            index_result.get("analysis", {}),
        )
        if not index_result["recall_links"]:
            raise ValueError("recall produced no links")
        processing_snapshot = _processing_snapshot(user_id)
        rotation_snapshot = get_last_llm_rotation_snapshot()
        for key in index_result["recall_keys"]:
            key["metadata"] = {
                **(key.get("metadata") or {}),
                "processing_settings": processing_snapshot,
                "llm_rotation_preset": rotation_snapshot,
            }
        for link in index_result["recall_links"]:
            link["metadata"] = {
                **(link.get("metadata") or {}),
                "processing_settings": processing_snapshot,
                "llm_rotation_preset": rotation_snapshot,
            }
        
        await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress("Saving recall links", 3, f"{STAGE_RECALL}:recall_chunk:{chunk['id']}:save", f"{STAGE_RECALL}:recall_chunk:{chunk['id']}")})
        saved_links = await asyncio.to_thread(recall.save_index, index_result, user_id)
        logger.info("ingest_recall_saved chunk_id=%s saved_links=%s", chunk["id"], saved_links)
        return chunk["id"], {"saved_links": saved_links, "recall_keys": [key["id"] for key in index_result["recall_keys"]], "llm_rotation_preset": rotation_snapshot}

    async def _recall_vectors(self, job_id: str, keys: list[dict[str, Any]]) -> None:
        """Index only missing recall-key vectors."""
        await asyncio.to_thread(repository.start_stage, job_id, STAGE_RECALL_VECTORS)
        await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress("Embedding recall keys", 0, STAGE_RECALL_VECTORS)})
        missing = []
        for key in keys:
            unit_key = f"recall_key_vector:{key['id']}"
            is_done = await asyncio.to_thread(repository.checkpoint_complete, job_id, STAGE_RECALL_VECTORS, unit_key)
            exists = await asyncio.to_thread(recall_key_vectors.exists, key["id"], key["user_id"])
            if is_done or exists:
                await asyncio.to_thread(repository.complete_checkpoint, job_id, STAGE_RECALL_VECTORS, unit_key, key["id"], {"reused": True})
                continue
            missing.append((unit_key, key))
        if missing:
            batch_size = get_user_settings(missing[0][1]["user_id"]).embedding_batch_size
            for i in range(0, len(missing), batch_size):
                batch = missing[i:i + batch_size]
                batch_str = f"{i + 1}-{i + len(batch)}" if len(batch) > 1 else str(i + 1)
                batch_ref = f"{STAGE_RECALL_VECTORS}:batch:{i}-{i + len(batch)}"
                await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress(f"Batch {batch_str}/{len(missing)}", 2, batch_ref, STAGE_RECALL_VECTORS)})
                await self._run_batch_units(
                    job_id,
                    STAGE_RECALL_VECTORS,
                    [(unit_key, key["id"], {}) for unit_key, key in batch],
                    lambda b=batch: asyncio.to_thread(recall_key_vectors.index, [k for _, k in b]),
                    batch[0][1]["user_id"],
                )

    async def _source_vectors(self, job_id: str, chunks: list[SourceChunk]) -> None:
        """Index only missing source chunk vectors."""
        await asyncio.to_thread(repository.start_stage, job_id, STAGE_SOURCE_VECTORS)
        await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress("Embedding source chunks", 0, STAGE_SOURCE_VECTORS)})
        missing = []
        for chunk in chunks:
            unit_key = f"source_vector:{chunk['id']}"
            is_done = await asyncio.to_thread(repository.checkpoint_complete, job_id, STAGE_SOURCE_VECTORS, unit_key)
            exists = await asyncio.to_thread(source_chunk_vectors.exists, chunk["id"], chunk["user_id"])
            if is_done or exists:
                await asyncio.to_thread(repository.complete_checkpoint, job_id, STAGE_SOURCE_VECTORS, unit_key, chunk["id"], {"reused": True})
                continue
            missing.append((unit_key, chunk))
        if missing:
            batch_size = get_user_settings(missing[0][1]["user_id"]).embedding_batch_size
            for i in range(0, len(missing), batch_size):
                batch = missing[i:i + batch_size]
                batch_str = f"{i + 1}-{i + len(batch)}" if len(batch) > 1 else str(i + 1)
                batch_ref = f"{STAGE_SOURCE_VECTORS}:batch:{i}-{i + len(batch)}"
                await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress(f"Batch {batch_str}/{len(missing)}", 2, batch_ref, STAGE_SOURCE_VECTORS)})
                await self._run_batch_units(
                    job_id,
                    STAGE_SOURCE_VECTORS,
                    [(unit_key, chunk["id"], {}) for unit_key, chunk in batch],
                    lambda b=batch: asyncio.to_thread(source_chunk_vectors.index, [c for _, c in b]),
                    batch[0][1]["user_id"],
                )

    async def _run_unit(self, job_id: str, stage: str, unit_key: str, work, user_id: str | None = None) -> None:
        """Run one unit and convert failures into durable retry state."""
        await asyncio.to_thread(repository.start_checkpoint, job_id, stage, unit_key)
        logger.info("ingest_unit_start job_id=%s stage=%s unit=%s", job_id, stage, unit_key)
        async def async_report(message: str, details: dict[str, Any] | None = None) -> None:
            await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress(_progress_message(message, details), 4, f"{stage}:{unit_key}:provider:{_ref_part(message)}", f"{stage}:{unit_key}")})

        def sync_report(message: str, details: dict[str, Any] | None = None) -> None:
            repository.update_metadata(job_id, {"progress_message": _progress(_progress_message(message, details), 4, f"{stage}:{unit_key}:provider:{_ref_part(message)}", f"{stage}:{unit_key}")})

        tokens = set_progress_reporters(async_report, sync_report)
        try:
            output_ref, metadata = await work()
            await asyncio.to_thread(repository.complete_checkpoint, job_id, stage, unit_key, output_ref, metadata)
            await asyncio.to_thread(repository.reset_attempts, job_id)
            logger.info("ingest_unit_complete job_id=%s stage=%s unit=%s", job_id, stage, unit_key)
        except Exception as exc:
            await asyncio.to_thread(repository.fail_checkpoint, job_id, stage, unit_key, str(exc))
            job = await asyncio.to_thread(repository.schedule_retry, job_id, stage, unit_key, str(exc), _retry_backoff(user_id))
            logger.info(
                "ingest_unit_retry job_id=%s stage=%s unit=%s status=%s attempt=%s error=%s",
                job_id, stage, unit_key, job["status"], job["attempt_count"], str(exc),
            )
            raise
        finally:
            reset_progress_reporters(tokens)

    async def _run_batch_units(self, job_id: str, stage: str, units: list[tuple[str, str, dict[str, Any]]], work, user_id: str | None = None) -> None:
        """Run one batch while preserving per-unit checkpoints."""
        for unit_key, _, _ in units:
            await asyncio.to_thread(repository.start_checkpoint, job_id, stage, unit_key)
        logger.info("ingest_batch_start job_id=%s stage=%s units=%s", job_id, stage, len(units))
        batch_ref = f"{stage}:batch:{_ref_part('|'.join(unit for unit, _, _ in units))}"
        async def async_report(message: str, details: dict[str, Any] | None = None) -> None:
            await asyncio.to_thread(repository.update_metadata, job_id, {"progress_message": _progress(_progress_message(message, details), 3, f"{batch_ref}:provider:{_ref_part(message)}", batch_ref)})

        def sync_report(message: str, details: dict[str, Any] | None = None) -> None:
            repository.update_metadata(job_id, {"progress_message": _progress(_progress_message(message, details), 3, f"{batch_ref}:provider:{_ref_part(message)}", batch_ref)})

        tokens = set_progress_reporters(async_report, sync_report)
        try:
            await work()
            for unit_key, output_ref, metadata in units:
                await asyncio.to_thread(repository.complete_checkpoint, job_id, stage, unit_key, output_ref, metadata)
            await asyncio.to_thread(repository.reset_attempts, job_id)
            logger.info("ingest_batch_complete job_id=%s stage=%s units=%s", job_id, stage, len(units))
        except Exception as exc:
            for unit_key, _, _ in units:
                await asyncio.to_thread(repository.fail_checkpoint, job_id, stage, unit_key, str(exc))
            retry_unit = units[0][0]
            job = await asyncio.to_thread(repository.schedule_retry, job_id, stage, retry_unit, str(exc), _retry_backoff(user_id))
            logger.info(
                "ingest_batch_retry job_id=%s stage=%s units=%s status=%s attempt=%s error=%s",
                job_id, stage, len(units), job["status"], job["attempt_count"], str(exc),
            )
            raise
        finally:
            reset_progress_reporters(tokens)


def _raw_input(raw_input_id: str) -> dict[str, Any] | None:
    from src.repositories import raw_inputs
    return raw_inputs.get(raw_input_id)


def _retry_backoff(user_id: str | None) -> list[int] | None:
    if not user_id:
        return None
    try:
        return getattr(get_user_settings(user_id), "ingest_retry_backoff_seconds", None)
    except NoActivePresetError:
        return None


def _source_piece_key(raw_input_id: str, text_piece: SourceWindow) -> str:
    """Content-bound unit key lets resume skip exactly completed text pieces."""
    digest = hashlib.sha256(text_piece["text"].encode("utf-8")).hexdigest()
    return f"source_piece:{raw_input_id}:{text_piece['start']}:{text_piece['end']}:{digest}"


def _stable_id(*parts: str) -> str:
    """Stable IDs make save-after-crash idempotent even before checkpoint completion."""
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest


def _progress_message(message: str, details: dict[str, Any] | None = None) -> str:
    preset = (details or {}).get("preset_name")
    return f"{message} [{preset}]" if preset else message


def _progress(message: str, depth: int, ref: str, parent_ref: str | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {"message": message, "depth": depth, "ref": ref}
    if parent_ref:
        data["parent_ref"] = parent_ref
    return data


def _ref_part(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def _processing_snapshot(user_id: str) -> dict[str, Any]:
    settings = get_user_settings(user_id)
    if hasattr(settings, "processing_snapshot"):
        return settings.processing_snapshot()
    return {}

def _directory_path(job_id: str) -> str | None:
    from src.infra.sqlite import get_connection
    row = get_connection().execute(
        "SELECT d.path FROM notes n JOIN directories d ON d.id = n.directory_id WHERE n.id = ?",
        (job_id,)
    ).fetchone()
    return row["path"] if row else None
