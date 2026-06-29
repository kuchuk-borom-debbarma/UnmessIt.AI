from __future__ import annotations

import json
from typing import Any

from src.infra import chroma
from src.services.rag.models import SourceChunk


def index(chunks: list[SourceChunk]) -> None:
    """Index source chunks in Chroma.

    SQLite stores the durable chunk rows; vectors can be wiped and rebuilt.
    """
    ids, texts, metadatas = [], [], []
    for chunk in chunks:
        ids.append(f"{chunk['id']}:source_chunk")
        texts.append(f"{chunk['summary']}\n{chunk['text']}")
        metadatas.append({
            "object_type": "source_chunk",
            "object_id": chunk["id"],
            "source_chunk_id": chunk["id"],
            "raw_input_id": chunk["raw_input_id"],
            "spans": json.dumps(chunk["spans"], ensure_ascii=False),
        })
    chroma.upsert(ids, texts, metadatas)


def delete(chunk_ids: list[str]) -> None:
    """Delete source chunk vectors from Chroma."""
    ids = [vector_id(cid) for cid in chunk_ids if cid]
    chroma.delete(ids)


def vector_id(chunk_id: str) -> str:
    """Return the deterministic Chroma ID for a source chunk."""
    return f"{chunk_id}:source_chunk"


def exists(chunk_id: str) -> bool:
    """Check if a source chunk vector already exists."""
    return vector_id(chunk_id) in chroma.existing_ids([vector_id(chunk_id)])


def search(query: str, top_k: int = 8) -> list[dict[str, Any]]:
    """Search the rebuildable Chroma source chunk index."""
    return chroma.search(query, top_k=top_k, where={"object_type": "source_chunk"})


def reset() -> None:
    """Clear vectors during dev wipe."""
    chroma.reset()
