from __future__ import annotations

import json
import hashlib
from typing import Any

from src.infra import chroma
from src.infra.settings import get_user_embedding_settings
from src.services.rag.models import SourceChunk


def index(chunks: list[SourceChunk]) -> None:
    """Index source chunks in Chroma.

    SQLite stores the durable chunk rows; vectors can be wiped and rebuilt.
    """
    from src.repositories import tags, raw_inputs
    
    ids, texts, metadatas = [], [], []
    settings = get_user_embedding_settings(chunks[0]["user_id"], "ingest.source_chunk_vectors") if chunks else None
    processing_snapshot = settings.processing_snapshot() if settings else {}
    rotation_snapshot = settings.rotation_snapshot() if settings else {}
    for chunk in chunks:
        # Get tags for this chunk's note
        raw_input = raw_inputs.get(chunk["raw_input_id"])
        note_id = raw_input["job_id"] if raw_input else None
        
        dir_path = chunk.get("directory_path") or ""
        
        meta = {
            "object_type": "source_chunk",
            "object_id": chunk["id"],
            "source_chunk_id": chunk["id"],
            "raw_input_id": chunk["raw_input_id"],
            "user_id": chunk["user_id"],
            "spans": json.dumps(chunk["spans"], ensure_ascii=False),
            "directory_path": dir_path,
            "processing_settings": json.dumps(processing_snapshot, ensure_ascii=False),
            "embedding_rotation_preset": json.dumps(rotation_snapshot or {}, ensure_ascii=False),
        }
        
        if dir_path:
            dir_ids = [d for d in dir_path.split("/") if d]
            for d in dir_ids:
                meta[f"dir_{d}"] = True
            for path in _directory_prefixes(dir_path):
                meta[_dir_path_key(path)] = True
        
        if note_id:
            note_tags = tags.get_for_note(note_id)
            for t in note_tags:
                meta[f"tag_{t['id']}"] = True
                
        ids.append(f"{chunk['id']}:source_chunk")
        texts.append(f"{chunk['summary']}\n{chunk['text']}")
        metadatas.append(meta)
        
    if chunks:
        user_id = chunks[0]["user_id"]
        chroma.upsert(ids, texts, metadatas, user_id, stage="ingest.source_chunk_vectors")


def delete(chunk_ids: list[str], user_id: str) -> None:
    """Delete source chunk vectors from Chroma."""
    ids = [vector_id(cid) for cid in chunk_ids if cid]
    chroma.delete(ids, user_id, stage="ingest.source_chunk_vectors")


def vector_id(chunk_id: str) -> str:
    """Return the deterministic Chroma ID for a source chunk."""
    return f"{chunk_id}:source_chunk"


def exists(chunk_id: str, user_id: str) -> bool:
    """Check if a source chunk vector already exists."""
    return vector_id(chunk_id) in chroma.existing_ids([vector_id(chunk_id)], user_id, stage="ingest.source_chunk_vectors")


def update_metadata(chunk_ids: list[str], metadata_updates: dict[str, Any], user_id: str) -> None:
    """Update metadata for existing source chunk vectors (merges with existing)."""
    if not chunk_ids:
        return
    vector_ids = [vector_id(cid) for cid in chunk_ids]
    collection = chroma.collection(user_id, stage="ingest.source_chunk_vectors")
    results = collection.get(ids=vector_ids, include=["metadatas"])
    existing_metadatas = results.get("metadatas") or []
    existing_ids = results.get("ids") or []
    
    if not existing_ids:
        return
        
    merged_metadatas = []
    for m in existing_metadatas:
        new_meta = dict(m) if m else {}
        if "directory_path" in metadata_updates:
            for key in list(new_meta):
                if key.startswith("dir_") or key.startswith("dirpath_"):
                    del new_meta[key]
            for directory_id in str(metadata_updates["directory_path"] or "").split("/"):
                if directory_id:
                    new_meta[f"dir_{directory_id}"] = True
            for path in _directory_prefixes(str(metadata_updates["directory_path"] or "")):
                new_meta[_dir_path_key(path)] = True
        new_meta.update(metadata_updates)
        merged_metadatas.append(new_meta)
        
    collection.update(ids=existing_ids, metadatas=merged_metadatas)


def search(
    query: str,
    user_id: str,
    top_k: int = 8,
    within_directories: list[str] | None = None,
    excluding_directories: list[str] | None = None,
    within_tags: list[str] | None = None,
    excluding_tags: list[str] | None = None,
    within_tags_condition: str = "any"
) -> list[dict[str, Any]]:
    """Search the rebuildable Chroma source chunk index."""
    where_conditions: list[dict[str, Any]] = [{"object_type": "source_chunk"}, {"user_id": user_id}]
    
    if within_directories:
        include_options = []
        for path in within_directories:
            include_options.extend(_directory_filters(path))
        where_conditions.append(include_options[0] if len(include_options) == 1 else {"$or": include_options})
            
    if excluding_directories:
        for path in excluding_directories:
            where_conditions.append({_dir_path_key(path): {"$ne": True}})
            
    if within_tags:
        if within_tags_condition == "all":
            for t in within_tags:
                where_conditions.append({f"tag_{t}": True})
        else: # any
            if len(within_tags) == 1:
                where_conditions.append({f"tag_{within_tags[0]}": True})
            else:
                or_conditions = [{f"tag_{t}": True} for t in within_tags]
                where_conditions.append({"$or": or_conditions})
                
    if excluding_tags:
        for t in excluding_tags:
            where_conditions.append({f"tag_{t}": {"$ne": True}})
            
    # Chroma only allows a single top-level $and or $or. 
    # If we have multiple where_conditions, we must wrap them in $and.
    if len(where_conditions) == 1:
        where = where_conditions[0]
    else:
        where = {"$and": where_conditions}
        
    return chroma.search(query, user_id, top_k=top_k, where=where, stage="retrieval.vector_search")


def reset(user_id: str) -> None:
    """Clear vectors during dev wipe for a specific user."""
    chroma.reset(user_id)


def _directory_prefixes(path: str) -> list[str]:
    parts = [part for part in path.split("/") if part]
    return ["/" + "/".join(parts[:index]) + "/" for index in range(1, len(parts) + 1)]


def _dir_path_key(path: str) -> str:
    normalized = path if path.endswith("/") else f"{path}/"
    return "dirpath_" + hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def _directory_filters(path: str) -> list[dict[str, Any]]:
    normalized = path if path.endswith("/") else f"{path}/"
    legacy_parts = [part for part in normalized.split("/") if part]
    filters = [{_dir_path_key(normalized): True}]
    if len(legacy_parts) == 1:
        filters.append({f"dir_{legacy_parts[0]}": True})
    return filters
