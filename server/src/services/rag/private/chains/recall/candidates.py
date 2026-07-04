from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Callable, Awaitable

from src.infra import retrieval_cache
from src.infra.settings import get_user_embedding_settings
from src.repositories import recall, recall_key_vectors, retrieval_index
from src.services.rag.models import SourceChunk

logger = logging.getLogger(__name__)


class RecallCandidateChain:
    """Find already-known names/topics that the new chunks may mention."""

    async def run(self, raw_text: str, user_id: str, source_chunks: list[SourceChunk], on_progress: Callable[[str], Awaitable[None]] | None = None) -> list[dict[str, Any]]:
        """Return top possible matches so the LLM can reuse them instead of inventing duplicates."""
        cache_key = _candidate_cache_key(raw_text, user_id, source_chunks)
        if cache_key:
            if on_progress: await on_progress("checking cached recall candidates")
            cached = _cached_candidates(await retrieval_cache.get_json(cache_key))
            if cached is not None:
                logger.info("recall_candidates_cache_hit chunks=%s candidates=%s", len(source_chunks), len(cached))
                if on_progress: await on_progress(f"reusing {len(cached)} cached recall candidate(s)")
                return cached
            if on_progress: await on_progress("no cached recall candidates")

        if on_progress: await on_progress("extracting terms from chunk entities")
        terms = _important_terms(raw_text, source_chunks)
        if on_progress: await on_progress("building semantic search string")
        text = _search_text(raw_text, source_chunks)

        if on_progress: await on_progress(f"searching sqlite for {len(terms)} term(s)")
        candidates = await asyncio.to_thread(recall.find_candidate_keys, terms, user_id, limit=20)
        
        if on_progress: await on_progress(f"searching vectors for semantic matches")
        vector_candidates = await _vector_candidates(text, user_id, limit=20)
        
        if on_progress: await on_progress("merging exact, keyword, and vector results")
        merged = _merge_candidates([*candidates, *vector_candidates], limit=20)
        logger.info(
            "recall_candidates chunks=%s terms=%s sqlite=%s vector=%s merged=%s sources=%s",
            len(source_chunks),
            len(terms),
            len(candidates),
            len(vector_candidates),
            len(merged),
            _source_counts(merged),
        )
        if cache_key:
            await retrieval_cache.set_json(cache_key, {"candidates": _json_safe_candidates(merged)})
            logger.info("recall_candidates_cache_set chunks=%s candidates=%s", len(source_chunks), len(merged))
            if on_progress: await on_progress(f"cached {len(merged)} recall candidate(s)")
        return merged


def _important_terms(raw_text: str, source_chunks: list[SourceChunk]) -> list[str]:
    """Pull search words from the cleanly extracted LLM entities."""
    result = []
    seen = set()
    for chunk in source_chunks:
        entities = chunk.get("metadata", {}).get("salient_entities", [])
        for entity in entities:
            clean = str(entity).strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                result.append(clean)
    return result[:20]


def _search_text(raw_text: str, source_chunks: list[SourceChunk]) -> str:
    """Build one compact semantic search string for recall-key vectors."""
    values = [raw_text[:1000], *[chunk["summary"] for chunk in source_chunks], *[chunk["text"][:400] for chunk in source_chunks]]
    return "\n".join(str(value) for value in values if str(value).strip())


async def _vector_candidates(text: str, user_id: str, limit: int) -> list[dict[str, Any]]:
    """Load recall keys found by semantic vector search."""
    hits = await asyncio.to_thread(recall_key_vectors.search, text, user_id, limit) if text.strip() else []
    ids = [hit["object_id"] for hit in hits if hit.get("object_type") == "recall_key"]
    keys = await asyncio.to_thread(recall.find_keys_by_ids, ids, user_id)
    distance_by_id = {hit["object_id"]: hit.get("distance") for hit in hits}
    for key in keys:
        key["match_source"] = "vector"
        key["match_notes"] = [f"semantic vector match, distance={distance_by_id.get(key['id'], 0.0)}"]
    return keys


def _merge_candidates(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Merge exact, keyword, and vector results into a small LLM candidate set."""
    score = {"exact": 0, "keyword": 1, "vector": 2}
    merged: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        existing = merged.get(candidate["id"])
        if not existing:
            merged[candidate["id"]] = candidate
            continue
        existing["match_notes"] = [*existing.get("match_notes", []), *candidate.get("match_notes", [])]
        if score.get(candidate.get("match_source"), 9) < score.get(existing.get("match_source"), 9):
            existing["match_source"] = candidate.get("match_source")
    return sorted(merged.values(), key=lambda item: score.get(item.get("match_source"), 9))[:limit]


def _source_counts(candidates: list[dict[str, Any]]) -> dict[str, int]:
    """Compact log summary of why recall-key candidates were selected."""
    counts: dict[str, int] = {}
    for candidate in candidates:
        source = str(candidate.get("match_source") or "unknown")
        counts[source] = counts.get(source, 0) + 1
    return counts


def _candidate_cache_key(raw_text: str, user_id: str, source_chunks: list[SourceChunk]) -> str:
    return retrieval_cache.cache_key(
        "recall_candidates:v1",
        user_id,
        retrieval_index.get_version(user_id),
        _embedding_settings_signature(user_id),
        raw_text[:1000],
        _chunk_payload(source_chunks),
    )


def _chunk_payload(source_chunks: list[SourceChunk]) -> list[dict[str, Any]]:
    return [
        {
            "id": chunk["id"],
            "summary": chunk.get("summary") or "",
            "text_preview": str(chunk.get("text") or "")[:400],
            "salient_entities": (chunk.get("metadata") or {}).get("salient_entities", []),
        }
        for chunk in source_chunks[:30]
    ]


def _embedding_settings_signature(user_id: str) -> str:
    try:
        settings = get_user_embedding_settings(user_id, "ingest.recall_key_vectors")
    except Exception:
        return "embedding-settings:none"
    return "|".join([
        settings.embedding_provider,
        settings.embedding_model,
        settings.embedding_base_url or "",
        str(settings.embedding_batch_size),
    ])


def _cached_candidates(value: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    if not isinstance(value, dict):
        return None
    candidates = value.get("candidates")
    if not isinstance(candidates, list):
        return None
    if any(not isinstance(candidate, dict) or not candidate.get("id") for candidate in candidates):
        return None
    return candidates


def _json_safe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return json.loads(json.dumps(candidates, ensure_ascii=False, default=str))
