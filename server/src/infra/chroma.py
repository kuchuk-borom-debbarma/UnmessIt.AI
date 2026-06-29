from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from src.infra.rate_limit import RateLimitedEmbeddingFunction, get_limiter
from src.infra.settings import get_user_settings
from src.infra.sqlite import DATA_DIR

logger = logging.getLogger(__name__)


@lru_cache(maxsize=100)
def _collection(user_id: str):
    """Create or reuse the persistent Chroma collection for a specific user."""
    settings = get_user_settings(user_id)
    embedding_function = _embedding_function(user_id)
    client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma_db"))
    collection_name = f"statements_{user_id}"
    try:
        return client.get_or_create_collection(collection_name, embedding_function=embedding_function)
    except ValueError as exc:
        if "embedding function" not in str(exc).lower():
            raise
        # ponytail: provider changes invalidate stored vectors; reset instead of migration machinery.
        client.delete_collection(collection_name)
        return client.create_collection(collection_name, embedding_function=embedding_function)


def upsert(ids: list[str], texts: list[str], metadatas: list[dict[str, Any]], user_id: str) -> None:
    """Insert or replace vector documents."""
    if not ids:
        return
    _collection(user_id).upsert(ids=ids, documents=texts, metadatas=metadatas)


def existing_ids(ids: list[str], user_id: str) -> set[str]:
    """Return vector IDs already present in the collection."""
    if not ids:
        return set()
    result = _collection(user_id).get(ids=ids)
    return set(result.get("ids") or [])


def delete(ids: list[str], user_id: str) -> None:
    """Delete vector documents by ID."""
    if not ids:
        return
    _collection(user_id).delete(ids=ids)


def search(query: str, user_id: str, top_k: int = 8, where: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return normalized search hits from Chroma's nested result shape."""
    kwargs = {"query_texts": [query], "n_results": top_k}
    if where:
        kwargs["where"] = where
    results = _collection(user_id).query(**kwargs)
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
    client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma_db"))
    collection_name = f"statements_{user_id}"
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    _collection.cache_clear()
    client.get_or_create_collection(collection_name, embedding_function=_embedding_function(user_id))


def _embedding_function(user_id: str):
    """Build the configured embedding function for Chroma."""
    settings = get_user_settings(user_id)
    if settings.embedding_provider == "ollama":
        fn = embedding_functions.OllamaEmbeddingFunction(
            url=settings.embedding_base_url or "http://localhost:11434/api/embeddings",
            model_name=settings.embedding_model,
        )
    elif settings.embedding_provider == "openai":
        fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.embedding_api_key,
            api_base=settings.embedding_base_url or "https://api.openai.com/v1",
            model_name=settings.embedding_model,
        )
    else:
        raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")

    if settings.embedding_rate_limit_per_minute > 0:
        return RateLimitedEmbeddingFunction(fn, get_limiter(settings.embedding_rate_limit_per_minute))
    return fn
