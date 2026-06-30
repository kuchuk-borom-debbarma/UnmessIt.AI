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
            "user_id": chunk["user_id"],
            "spans": json.dumps(chunk["spans"], ensure_ascii=False),
            "directory_path": chunk.get("directory_path") or "",
        })
    if chunks:
        user_id = chunks[0]["user_id"]
        chroma.upsert(ids, texts, metadatas, user_id)


def delete(chunk_ids: list[str], user_id: str) -> None:
    """Delete source chunk vectors from Chroma."""
    ids = [vector_id(cid) for cid in chunk_ids if cid]
    chroma.delete(ids, user_id)


def vector_id(chunk_id: str) -> str:
    """Return the deterministic Chroma ID for a source chunk."""
    return f"{chunk_id}:source_chunk"


def exists(chunk_id: str, user_id: str) -> bool:
    """Check if a source chunk vector already exists."""
    return vector_id(chunk_id) in chroma.existing_ids([vector_id(chunk_id)], user_id)


def update_metadata(chunk_ids: list[str], metadata_updates: dict[str, Any], user_id: str) -> None:
    """Update metadata for existing source chunk vectors (merges with existing)."""
    if not chunk_ids:
        return
    vector_ids = [vector_id(cid) for cid in chunk_ids]
    collection = chroma._collection(user_id)
    results = collection.get(ids=vector_ids, include=["metadatas"])
    existing_metadatas = results.get("metadatas") or []
    existing_ids = results.get("ids") or []
    
    if not existing_ids:
        return
        
    merged_metadatas = []
    for m in existing_metadatas:
        new_meta = dict(m) if m else {}
        new_meta.update(metadata_updates)
        merged_metadatas.append(new_meta)
        
    collection.update(ids=existing_ids, metadatas=merged_metadatas)


def search(query: str, user_id: str, top_k: int = 8, within_directories: list[str] | None = None, excluding_directories: list[str] | None = None) -> list[dict[str, Any]]:
    """Search the rebuildable Chroma source chunk index."""
    from src.repositories import directories
    
    where_conditions: list[dict[str, Any]] = [{"object_type": "source_chunk"}, {"user_id": user_id}]
    
    if within_directories:
        resolved_paths = set()
        for dir_id in within_directories:
            d = directories.get(dir_id, user_id)
            if d:
                resolved_paths.add(d["path"])
            subs = directories.list_subtree(dir_id, user_id, limit=1000).get("data", [])
            resolved_paths.update([sub["path"] for sub in subs])
            
        if not resolved_paths:
            where_conditions.append({"directory_path": "__NO_MATCH__"})
        else:
            where_conditions.append({"directory_path": {"$in": list(resolved_paths)}})
            
    if excluding_directories:
        resolved_paths = set()
        for dir_id in excluding_directories:
            d = directories.get(dir_id, user_id)
            if d:
                resolved_paths.add(d["path"])
            subs = directories.list_subtree(dir_id, user_id, limit=1000).get("data", [])
            resolved_paths.update([sub["path"] for sub in subs])
            
        if len(resolved_paths) == 1:
            where_conditions.append({"directory_path": {"$ne": list(resolved_paths)[0]}})
        elif len(resolved_paths) > 1:
            where_conditions.append({"directory_path": {"$nin": list(resolved_paths)}})
            
    return chroma.search(query, user_id, top_k=top_k, where={"$and": where_conditions})


def reset(user_id: str) -> None:
    """Clear vectors during dev wipe for a specific user."""
    chroma.reset(user_id)
