from __future__ import annotations

import logging
import hashlib
import json
from functools import lru_cache
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from src.infra.embedding_cache import CachedEmbeddingFunction, embedding_cache_namespace
from src.infra.rate_limit import RateLimitedEmbeddingFunction, get_limiter
from src.infra.settings import (
    get_user_embedding_setting_candidates as get_user_setting_candidates,
    get_user_embedding_settings as get_user_settings,
)
from src.infra.progress import report_progress_sync, set_last_embedding_rotation_snapshot, get_last_embedding_rotation_snapshot
from src.infra.sqlite import DATA_DIR

logger = logging.getLogger(__name__)

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma_db"))
    return _client


@lru_cache(maxsize=100)
def _collection(user_id: str, processing_hash: str, stage: str):
    """Create or reuse the persistent Chroma collection for a specific user."""
    embedding_function = RotatingEmbeddingFunction(user_id, stage)
    client = _get_client()
    collection_name = f"statements_{_name_part(user_id)}_{processing_hash[:8]}"
    try:
        return client.get_or_create_collection(collection_name, embedding_function=embedding_function)
    except ValueError as exc:
        if "embedding function" not in str(exc).lower():
            raise
        # ponytail: provider changes invalidate stored vectors; reset instead of migration machinery.
        client.delete_collection(collection_name)
        return client.create_collection(collection_name, embedding_function=embedding_function)


def upsert(ids: list[str], texts: list[str], metadatas: list[dict[str, Any]], user_id: str, stage: str = "ingest.source_chunk_vectors") -> None:
    """Insert or replace vector documents."""
    if not ids:
        return
    collection = _collection_for(user_id, stage)
    set_last_embedding_rotation_snapshot(None)
    collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
    snapshot = get_last_embedding_rotation_snapshot()
    if snapshot:
        collection.update(
            ids=ids,
            metadatas=[{**metadata, "embedding_rotation_preset": json.dumps(snapshot, ensure_ascii=False)} for metadata in metadatas],
        )


def collection(user_id: str, stage: str = "retrieval.vector_search"):
    """Return the configured Chroma collection for repository-level maintenance."""
    return _collection_for(user_id, stage)


def existing_ids(ids: list[str], user_id: str, stage: str = "ingest.source_chunk_vectors") -> set[str]:
    """Return vector IDs already present in the collection."""
    if not ids:
        return set()
    result = _collection_for(user_id, stage).get(ids=ids)
    return set(result.get("ids") or [])


def delete(ids: list[str], user_id: str, stage: str = "ingest.source_chunk_vectors") -> None:
    """Delete vector documents by ID."""
    if not ids:
        return
    _collection_for(user_id, stage).delete(ids=ids)


def search(query: str, user_id: str, top_k: int = 8, where: dict[str, Any] | None = None, stage: str = "retrieval.vector_search") -> list[dict[str, Any]]:
    """Return normalized search hits from Chroma's nested result shape."""
    kwargs = {"query_texts": [query], "n_results": top_k}
    if where:
        kwargs["where"] = where
    results = _collection_for(user_id, stage).query(**kwargs)
    if not results["ids"] or not results["ids"][0]:
        return []

    hits = []
    for index, vector_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][index] if results["metadatas"] else {}
        object_id = metadata.get("object_id") or vector_id
        hits.append({
            "vector_id": vector_id,
            "object_id": object_id,
            "object_type": metadata.get("object_type", "unknown"),
            "text": results["documents"][0][index],
            "metadata": metadata,
            "distance": results["distances"][0][index] if results["distances"] else 0.0,
        })
    return hits


def reset(user_id: str) -> None:
    """Drop the vector collection and clear the cached handle for a user."""
    client = _get_client()
    prefix = f"statements_{_name_part(user_id)}_"
    for item in client.list_collections():
        name = getattr(item, "name", str(item))
        if name.startswith(prefix):
            try:
                client.delete_collection(name)
            except Exception:
                pass
    _collection.cache_clear()
    _user_collection(user_id, "retrieval.vector_search")


def _user_collection(user_id: str, stage: str):
    settings = get_user_settings(user_id, stage)
    digest = hashlib.sha256(settings.processing_signature().encode("utf-8")).hexdigest()
    return _collection(user_id, digest, stage)


def _collection_for(user_id: str, stage: str):
    try:
        return _user_collection(user_id, stage)
    except TypeError:
        # Compatibility for tests that monkeypatch _user_collection(user_id).
        return _user_collection(user_id)


@lru_cache(maxsize=100)
def semantic_cache_collection(user_id: str, namespace: str):
    """Return a disposable Chroma collection for retrieval semantic caches."""
    name_hash = hashlib.sha256(f"{user_id}:{namespace}".encode("utf-8")).hexdigest()[:24]
    return _get_client().get_or_create_collection(
        f"retrieval_cache_{name_hash}",
        embedding_function=RotatingEmbeddingFunction(user_id, "retrieval.semantic_cache"),
        metadata={"hnsw:space": "cosine"},
    )


class RotatingEmbeddingFunction(chromadb.EmbeddingFunction):
    """Chroma embedding callback that tries rotation lanes in order."""

    @staticmethod
    def name() -> str:
        return "RotatingEmbeddingFunction"

    def __init__(self, user_id: str, stage: str = "retrieval.vector_search") -> None:
        self.user_id = user_id
        self.stage = stage

    def get_config(self) -> dict:
        return {"user_id": self.user_id}

    def __call__(self, input):
        candidates = get_user_setting_candidates(self.user_id, self.stage)
        errors = []
        for index, settings in enumerate(candidates, start=1):
            report_progress_sync(
                f"Embedding config {index}/{len(candidates)} selected: {settings.preset_name}",
                {"preset_id": settings.preset_id, "preset_name": settings.preset_name, "attempt": index, "total": len(candidates)},
            )
            try:
                # httpx (via openai) will mistakenly try to grab the asyncio event loop 
                # inside worker threads if sniffio inherits the main thread's ContextVar.
                try:
                    import sniffio
                    sniffio.current_async_library_cvar.set(None)
                except Exception:
                    pass
                
                result = _embedding_function_for_key(settings.embedding_cache_key())(input)
                set_last_embedding_rotation_snapshot(settings.rotation_snapshot())
                report_progress_sync(
                    f"Embedding config succeeded: {settings.preset_name}",
                    {"preset_id": settings.preset_id, "preset_name": settings.preset_name},
                )
                return result
            except Exception as exc:
                errors.append(f"{settings.preset_name}: {exc}")
                report_progress_sync(
                    f"Embedding config failed: {settings.preset_name}",
                    {"preset_id": settings.preset_id, "preset_name": settings.preset_name, "error": str(exc)[:500]},
                )
        report_progress_sync("All embedding configs failed.", {"errors": errors})
        raise RuntimeError("All embedding configs failed: " + "; ".join(errors))


@lru_cache(maxsize=100)
def _embedding_function_for_key(cache_key: tuple):
    (
        _preset_id,
        provider,
        model,
        base_url,
        api_key,
        rate_limit,
    ) = cache_key
    if provider == "openai":
        fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key or "dummy-key",
            api_base=base_url or "https://api.openai.com/v1",
            model_name=model,
        )
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")

    if rate_limit > 0:
        fn = RateLimitedEmbeddingFunction(fn, get_limiter(rate_limit))
    return CachedEmbeddingFunction(fn, embedding_cache_namespace(provider, model, base_url))


def _name_part(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value)[:40] or "default"
