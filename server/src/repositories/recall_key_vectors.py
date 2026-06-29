from __future__ import annotations

import json
from typing import Any

from src.infra import chroma


def index(keys: list[dict[str, Any]]) -> None:
    """Index recall keys in Chroma for semantic candidate lookup.

    SQLite remains the source of truth. These vectors only help find likely
    existing keys when wording differs from a saved name or alias.
    """
    ids, texts, metadatas = [], [], []
    for key in keys:
        ids.append(f"{key['id']}:recall_key")
        texts.append(_text(key))
        metadatas.append({
            "object_type": "recall_key",
            "object_id": key["id"],
            "recall_key_id": key["id"],
            "name": key["name"],
            "user_id": key["user_id"],
        })
    chroma.upsert(ids, texts, metadatas)


def vector_id(recall_key_id: str) -> str:
    """Return the deterministic Chroma ID for a recall key."""
    return f"{recall_key_id}:recall_key"


def exists(recall_key_id: str) -> bool:
    """Check if a recall key vector already exists."""
    return vector_id(recall_key_id) in chroma.existing_ids([vector_id(recall_key_id)])


def search(query: str, user_id: str, top_k: int = 20) -> list[dict[str, Any]]:
    """Search only recall-key vectors, not source-chunk vectors."""
    return chroma.search(query, top_k=top_k, where={"$and": [{"object_type": "recall_key"}, {"user_id": user_id}]})


def _text(key: dict[str, Any]) -> str:
    """Build the recall-key text used for embeddings."""
    aliases = key.get("aliases", [])
    alias_text = ", ".join(str(alias) for alias in aliases) if isinstance(aliases, list) else str(aliases or "")
    metadata = key.get("metadata") if isinstance(key.get("metadata"), dict) else {}
    return "\n".join([
        str(key.get("name") or ""),
        alias_text,
        str(key.get("kind_label") or ""),
        str(key.get("summary") or ""),
        json.dumps(metadata, ensure_ascii=False),
    ]).strip()
