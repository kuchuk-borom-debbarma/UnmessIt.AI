from __future__ import annotations

import logging
import re
from typing import Any

from src.repositories import recall, recall_key_vectors
from src.services.rag.models import SourceChunk

logger = logging.getLogger(__name__)


class RecallCandidateChain:
    """Find already-known names/topics that the new chunks may mention."""

    def run(self, raw_text: str, source_chunks: list[SourceChunk]) -> list[dict[str, Any]]:
        """Return top possible matches so the LLM can reuse them instead of inventing duplicates."""
        terms = _important_terms(raw_text, source_chunks)
        text = _search_text(raw_text, source_chunks)

        # Exact and keyword matches run before the LLM so obvious reuse is cheap and bounded.
        candidates = recall.find_candidate_keys(terms, limit=20)
        # Semantic recall-key search only helps after at least one recall key exists.
        vector_candidates = _vector_candidates(text, limit=20) if recall.has_keys() else []
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
        return merged


def _important_terms(raw_text: str, source_chunks: list[SourceChunk]) -> list[str]:
    """Pull simple search words from the new text and chunk summaries."""
    values = [
        raw_text[:1000],
        *[chunk["summary"] for chunk in source_chunks],
        *[chunk["text"][:400] for chunk in source_chunks],
    ]
    stop = {"what", "with", "from", "that", "this", "they", "them", "were", "have", "about", "source", "chunk"}
    result = []
    seen = set()
    for value in values:
        for term in re.findall(r"[A-Za-z][A-Za-z']+", str(value)):
            lowered = term.lower().strip("'")
            if len(lowered) >= 4 and lowered not in stop and lowered not in seen:
                # These words are only lookup hints; the LLM still decides whether a candidate is the same thing.
                seen.add(lowered)
                result.append(term.strip("'"))
    return result[:12]


def _search_text(raw_text: str, source_chunks: list[SourceChunk]) -> str:
    """Build one compact semantic search string for recall-key vectors."""
    values = [raw_text[:1000], *[chunk["summary"] for chunk in source_chunks], *[chunk["text"][:400] for chunk in source_chunks]]
    return "\n".join(str(value) for value in values if str(value).strip())


def _vector_candidates(text: str, limit: int) -> list[dict[str, Any]]:
    """Load recall keys found by semantic vector search."""
    hits = recall_key_vectors.search(text, top_k=limit) if text.strip() else []
    ids = [hit["object_id"] for hit in hits if hit.get("object_type") == "recall_key"]
    keys = recall.find_keys_by_ids(ids)
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
