from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal, TypedDict, Callable, Awaitable

from langgraph.graph import END, START, StateGraph

from src.repositories import recall
from src.services.rag.models import RecallIndex, SourceChunk
from src.services.rag.private.chains.recall.candidates import RecallCandidateChain
from src.services.rag.private.chains.recall.drafts import RecallDraftChain
from src.services.rag.private.chains.recall.normalizer import RecallNormalizerChain

logger = logging.getLogger(__name__)


class RecallGraphState(TypedDict, total=False):
    """State shared by the recall indexing subgraph."""

    raw_text: str
    user_id: str
    source_chunks: list[SourceChunk]
    candidates: list[dict[str, Any]]
    draft: dict[str, Any]
    recall_index: RecallIndex
    errors: list[str]
    retry_used: bool
    retry_ready: bool
    on_progress: Callable[[str], Awaitable[None]] | None


class RecallIndexChain:
    """Coordinate recall-key/link creation with a small LangGraph subgraph.

    The recall recipe is:
    find likely existing keys -> ask the LLM for keys/links -> normalize output
    -> retry once with validation errors when the first answer is not usable.

    This keeps ingestion readable while keeping the recall-specific branching
    near the recall chains that understand it.
    """

    def __init__(self, json_client) -> None:
        """Create the small recall subchains used by this coordinator."""
        self.candidates = RecallCandidateChain()
        self.drafts = RecallDraftChain(json_client)
        self.normalizer = RecallNormalizerChain()
        self.graph = self._build_graph()

    async def run(self, raw_text: str, user_id: str, source_chunks: list[SourceChunk], on_progress: Callable[[str], Awaitable[None]] | None = None) -> RecallIndex:
        """Return normalized recall keys and links for saved source chunks."""
        logger.info("recall_index_start chunks=%s chunk_ids=%s", len(source_chunks), [chunk["id"] for chunk in source_chunks])
        state = await self.graph.ainvoke({"raw_text": raw_text, "user_id": user_id, "source_chunks": source_chunks, "retry_used": False, "on_progress": on_progress})
        recall_index = state["recall_index"]
        errors = state.get("errors", [])
        logger.info(
            "recall_index_complete normalized_keys=%s normalized_links=%s validation_errors=%s errors=%s",
            len(recall_index["recall_keys"]),
            len(recall_index["recall_links"]),
            len(errors),
            errors,
        )
        recall_index["analysis"]["validation_errors"] = len(errors)
        recall_index["analysis"]["retry_used"] = bool(state.get("retry_used"))
        return recall_index

    def _build_graph(self):
        """Build the recall decision workflow once."""
        graph = StateGraph(RecallGraphState)
        graph.add_node("find_candidates", self._find_candidates)
        graph.add_node("draft", self._draft)
        graph.add_node("normalize", self._normalize)
        graph.add_edge(START, "find_candidates")
        graph.add_edge("find_candidates", "draft")
        graph.add_edge("draft", "normalize")
        graph.add_conditional_edges("normalize", self._after_normalize, {"retry": "draft", "done": END})
        return graph.compile()

    async def _find_candidates(self, state: RecallGraphState) -> RecallGraphState:
        """Find existing recall keys before asking the LLM to create new ones."""
        if state.get("on_progress"):
            await state["on_progress"]("finding existing candidates")
        candidates = await self.candidates.run(state["raw_text"], state["user_id"], state["source_chunks"], state.get("on_progress"))
        return {**state, "candidates": candidates}

    async def _draft(self, state: RecallGraphState) -> RecallGraphState:
        """Ask the LLM for recall keys/links, including retry errors when present."""
        if state.get("on_progress"):
            await state["on_progress"]("drafting links via LLM")
        draft = await self.drafts.run(state["source_chunks"], state.get("candidates", []), state["user_id"], state.get("errors") if state.get("retry_ready") else None, state.get("on_progress"))
        return {**state, "draft": draft, "retry_ready": False}

    async def _normalize(self, state: RecallGraphState) -> RecallGraphState:
        """Validate LLM output and prepare the graph branch decision."""
        if state.get("on_progress"):
            await state["on_progress"]("normalizing LLM output")
        recall_index, errors = await self.normalizer.run(state.get("draft", {}), state["source_chunks"], state["user_id"], state.get("candidates", []), state.get("on_progress"))
        if errors and not state.get("retry_used"):
            logger.info(
                "recall_index_retry validation_errors=%s normalized_keys=%s normalized_links=%s errors=%s",
                len(errors),
                len(recall_index["recall_keys"]),
                len(recall_index["recall_links"]),
                errors,
            )
            return {**state, "recall_index": recall_index, "errors": errors, "retry_used": True, "retry_ready": True}
        return {**state, "recall_index": recall_index, "errors": errors}

    def _after_normalize(self, state: RecallGraphState) -> Literal["retry", "done"]:
        """Retry once when validation failed; otherwise finish the subgraph."""
        if state.get("retry_ready"):
            return "retry"
        return "done"
