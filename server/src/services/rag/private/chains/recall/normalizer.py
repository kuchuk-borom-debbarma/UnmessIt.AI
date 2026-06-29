from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from src.repositories import recall
from src.services.rag.models import RecallIndex, SourceChunk

KINDS = {"entity", "topic", "event", "task", "question", "other"}
RELATIONS = {"mentions", "about", "updates", "contradicts", "supports", "other"}
logger = logging.getLogger(__name__)


class RecallNormalizerChain:
    """Turn LLM recall suggestions into safe records for storage.

    The LLM may suggest a new key or reuse an existing candidate. This chain
    accepts reuse only through candidate IDs we supplied, keeps aliases short,
    rejects links to unknown chunks, and drops duplicate links from this run.
    """

    async def run(
        self,
        data: dict[str, Any],
        source_chunks: list[SourceChunk],
        user_id: str,
        candidates: list[dict[str, Any]],
    ) -> tuple[RecallIndex, list[str]]:
        """Return normalized recall index data and validation errors."""
        valid_chunk_ids = {chunk["id"] for chunk in source_chunks}
        # Only candidates found by our lookup can be reused; arbitrary LLM IDs are ignored.
        candidates_by_id = {str(candidate["id"]): candidate for candidate in candidates}
        key_by_ref: dict[str, dict[str, Any]] = {}
        keys_by_norm_name: dict[str, dict[str, Any]] = {}
        keys = []
        links = []
        errors = []

        draft_keys = _as_list(data.get("recall_keys"))
        draft_links = _as_list(data.get("recall_links"))
        logger.info(
            "recall_normalizer_input chunks=%s candidates=%s draft_keys=%s draft_links=%s key_refs=%s link_refs=%s",
            len(source_chunks),
            len(candidates),
            len(draft_keys),
            len(draft_links),
            _key_refs(draft_keys),
            _link_refs(draft_links),
        )
        if not draft_keys:
            errors.append("missing recall_keys")
        if not draft_links:
            errors.append("missing recall_links")

        for draft in draft_keys[:8]:
            ref = str(draft.get("ref") or "").strip()
            existing = candidates_by_id.get(str(draft.get("existing_recall_key_id") or "").strip())
            name = str(draft.get("name") or (existing or {}).get("name") or "").strip()
            if not ref or not name:
                errors.append("recall key missing ref or name")
                continue

            norm_name = recall.normalize_term(name)
            if not existing and norm_name in keys_by_norm_name:
                key_by_ref[ref] = keys_by_norm_name[norm_name]
                continue

            if not existing:
                existing = _exact_existing_key(name, _as_strings(draft.get("aliases")), user_id, errors)
            kind, metadata = _allowed(draft.get("kind"), KINDS, draft.get("metadata"))
            if existing and existing.get("kind") != "other":
                # Existing coarse type wins unless it was unknown, so later text does not drift identity.
                kind = str(existing["kind"])
            key = {
                # Reused keys keep the same ID and name; new keys get a fresh ID.
                "id": existing["id"] if existing else str(uuid4()),
                "name": str((existing or {}).get("name") or name)[:160],
                "kind": kind,
                "kind_label": _optional_str(draft.get("kind_label")) or (existing or {}).get("kind_label"),
                # Aliases let future ingests find this same key without renaming it.
                "aliases": _aliases([*((existing or {}).get("aliases") or []), *(_as_strings(draft.get("aliases")))]),
                "summary": str(draft.get("summary") or (existing or {}).get("summary") or "").strip()[:240],
                "metadata": {**((existing or {}).get("metadata") or {}), **metadata},
            }
            # Links point to this short ref inside the same LLM response.
            key_by_ref[ref] = key
            keys_by_norm_name[norm_name] = key
            keys.append(key)

        seen_links = set()
        for draft in draft_links[:24]:
            key = key_by_ref.get(str(draft.get("recall_key_ref") or "").strip())
            chunk_id = str(draft.get("source_chunk_id") or "").strip()
            if not key or chunk_id not in valid_chunk_ids:
                # A link is only useful if it connects one accepted key to one chunk we just saved.
                errors.append("recall link references unknown source_chunk_id or recall_key_ref")
                continue
            relation, metadata = _allowed(draft.get("relation"), RELATIONS, draft.get("metadata"))
            relation_label = _optional_str(draft.get("relation_label")) or ""
            dedupe_key = (key["id"], chunk_id, relation, relation_label)
            if dedupe_key in seen_links:
                # Skip the same key->chunk relation repeated by the LLM in this response.
                continue
            seen_links.add(dedupe_key)
            links.append({
                "id": str(uuid4()),
                "recall_key_id": key["id"],
                "source_chunk_id": chunk_id,
                "relation": relation,
                "relation_label": relation_label,
                "confidence": _confidence(draft.get("confidence")),
                "reason": str(draft.get("reason") or "").strip()[:240],
                "event_time": _optional_str(draft.get("event_time")),
                "time_label": _optional_str(draft.get("time_label")),
                "metadata": metadata,
            })

        linked_key_ids = {link["recall_key_id"] for link in links}
        # Store only keys that have evidence links; loose names without a chunk are not useful yet.
        keys = [key for key in keys if key["id"] in linked_key_ids]
        if not links:
            errors.append("no recall links for available source chunks")
        logger.info(
            "recall_normalizer_result keys=%s links=%s errors=%s",
            len(keys),
            len(links),
            list(dict.fromkeys(errors)),
        )
        return {"recall_keys": keys, "recall_links": links, "analysis": {"recall_keys": len(keys), "recall_links": len(links)}}, list(dict.fromkeys(errors))


def _as_list(value: Any) -> list[dict[str, Any]]:
    """Keep dict items from an LLM list field."""
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _exact_existing_key(name: str, aliases: list[str], user_id: str, errors: list[str]) -> dict[str, Any] | None:
    """Reuse only one unambiguous exact name/alias match from the whole key store."""
    matches = recall.find_exact_term_matches([name, *aliases], user_id, limit=5)
    unique = {match["id"]: match for match in matches}
    if len(unique) == 1:
        # Exact normalized text is safe to auto-reuse; semantic matches are not.
        return next(iter(unique.values()))
    if len(unique) > 1:
        # If ambiguous, check if any exactly match the primary name to prevent runaway duplication.
        norm_name = recall.normalize_term(name)
        name_matches = [m for m in unique.values() if recall.normalize_term(m.get("name", "")) == norm_name]
        if name_matches:
            return name_matches[0]
        errors.append("new recall key exact match is ambiguous")
    return None


def _as_strings(value: Any) -> list[str]:
    """Accept one string or a list of strings from LLM output."""
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value] if isinstance(value, list) else []


def _allowed(value: Any, allowed: set[str], metadata: Any) -> tuple[str, dict[str, Any]]:
    """Normalize coarse buckets while preserving unknown labels."""
    clean = str(value or "").lower().strip()
    result = clean if clean in allowed else "other"
    data = metadata if isinstance(metadata, dict) else {}
    if clean and clean not in allowed:
        data = {**data, "original_kind_or_relation": clean}
    return result, data


def _aliases(values: list[str]) -> list[str]:
    """Keep short alias-like values without duplicates."""
    result = []
    seen = set()
    for value in values:
        clean = value.strip()
        lowered = clean.lower()
        if clean and lowered not in seen and len(clean.split()) <= 6:
            seen.add(lowered)
            result.append(clean[:120])
    return result[:10]


def _confidence(value: Any) -> float:
    """Clamp link confidence into a predictable 0..1 range."""
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return 0.5


def _optional_str(value: Any) -> str | None:
    """Return short optional strings for stored recall fields."""
    clean = str(value or "").strip()
    return clean[:160] if clean else None


def _key_refs(keys: list[dict[str, Any]]) -> list[str]:
    """Log only compact LLM key refs/names."""
    return [f"{str(key.get('ref') or '')}:{str(key.get('name') or '')[:40]}" for key in keys[:8]]


def _link_refs(links: list[dict[str, Any]]) -> list[str]:
    """Log only compact LLM link refs and chunk ids."""
    result = []
    for link in links[:12]:
        chunk_id = str(link.get("source_chunk_id") or "")
        result.append(f"{str(link.get('recall_key_ref') or '')}->{chunk_id[:12]}:{str(link.get('relation') or '')[:20]}")
    return result
