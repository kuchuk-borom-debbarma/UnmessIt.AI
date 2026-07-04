from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from collections import OrderedDict
from functools import lru_cache
from typing import Any

from src.infra import chroma
from src.infra import redis
from src.infra.progress import report_progress, report_progress_sync
from src.infra.settings import get_user_llm_setting_candidates

logger = logging.getLogger(__name__)


TTL_SECONDS = 60 * 60 * 24
MEMORY_MAX_ITEMS = 1000
SEMANTIC_THRESHOLD = 0.96


class MemoryJsonCache:
    def __init__(self, max_items: int = MEMORY_MAX_ITEMS) -> None:
        self.max_items = max_items
        self._values: OrderedDict[str, tuple[dict[str, Any], float]] = OrderedDict()

    def get(self, key: str) -> dict[str, Any] | None:
        item = self._values.get(key)
        if item is None:
            return None
        self._values.move_to_end(key)
        return item[0]

    def set(self, key: str, value: dict[str, Any]) -> None:
        self._values[key] = (value, time.time())
        self._values.move_to_end(key)
        while len(self._values) > self.max_items:
            self._values.popitem(last=False)

    def cleanup_stale(self, ttl_seconds: int) -> int:
        now = time.time()
        stale_keys = [k for k, v in self._values.items() if now - v[1] > ttl_seconds]
        for k in stale_keys:
            self._values.pop(k, None)
        return len(stale_keys)


@lru_cache(maxsize=1)
def get_memory_json_cache() -> MemoryJsonCache:
    return MemoryJsonCache()


async def get_json(key: str) -> dict[str, Any] | None:
    memory = get_memory_json_cache()
    value = memory.get(key)
    if value is not None:
        logger.info("retrieval_cache_hit source=memory key=%s", key)
        await report_progress("Using previously cached results to save time.", {"depth": 2, "ref": "cache:retrieval:hit:memory", "key": key})
        return value
    try:
        value = await redis.get_json(key)
    except Exception as exc:
        logger.warning("retrieval_cache_redis_error error=%s", exc)
        return None
    if value is not None:
        logger.info("retrieval_cache_hit source=redis key=%s", key)
        await report_progress("Using previously cached results to save time.", {"depth": 2, "ref": "cache:retrieval:hit:redis", "key": key})
        memory.set(key, value)
    else:
        logger.info("retrieval_cache_miss key=%s", key)
        await report_progress("No exact match found; starting full search.", {"depth": 2, "ref": "cache:retrieval:miss", "key": key})
    return value


async def set_json(key: str, value: dict[str, Any]) -> None:
    logger.info("retrieval_cache_set key=%s", key)
    await report_progress("Cached retrieval JSON.", {"depth": 2, "ref": "cache:retrieval:set", "key": key})
    get_memory_json_cache().set(key, value)
    try:
        await redis.set_json(key, value, TTL_SECONDS)
    except Exception as exc:
        logger.warning("retrieval_cache_redis_set_error error=%s", exc)
        return


def cache_key(namespace: str, *parts: object) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"unmessit:retrieval:{namespace}:{digest}"


def semantic_namespace(namespace: str, *parts: object) -> str:
    payload = json.dumps([namespace, *parts], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def normalize_semantic_text(*parts: object) -> str:
    text = " ".join(_text_part(part) for part in parts)
    text = re.sub(r"[^\w\s'-]+", " ", text.lower(), flags=re.UNICODE)
    return " ".join(text.split())


def get_semantic_json_match(
    user_id: str,
    namespace: str,
    text: str,
    threshold: float = SEMANTIC_THRESHOLD,
    emit_progress: bool = True,
) -> tuple[dict[str, Any], float] | None:
    if not user_id or not namespace or not text:
        return None
    try:
        results = chroma.semantic_cache_collection(user_id, namespace).query(
            query_texts=[text],
            n_results=1,
            include=["metadatas", "distances"],
        )
    except Exception as exc:
        logger.warning("semantic_cache_query_error error=%s", exc)
        return None
    distances = (results.get("distances") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    if not distances or not metadatas:
        logger.info("semantic_cache_miss namespace=%s reason=no_results text_len=%d", namespace, len(text))
        if emit_progress:
            report_progress_sync("New topic detected; starting full search.", {"depth": 2, "ref": "cache:semantic:miss:no_results", "namespace": namespace})
        return None
    distance = float(distances[0])
    if 1 - distance < threshold:
        logger.info("semantic_cache_miss namespace=%s reason=below_threshold distance=%s threshold=%s", namespace, distance, threshold)
        if emit_progress:
            report_progress_sync("New topic detected; starting full search.", {"depth": 2, "ref": "cache:semantic:miss:below_threshold", "namespace": namespace, "distance": distance})
        return None
    try:
        value = json.loads(metadatas[0].get("payload") or "{}")
    except (AttributeError, json.JSONDecodeError):
        return None
    logger.info("semantic_cache_hit namespace=%s distance=%s", namespace, distance)
    if emit_progress:
        report_progress_sync("Found a highly similar previous question; reusing its answer!", {"depth": 2, "ref": "cache:semantic:hit", "namespace": namespace, "distance": distance})
    return (value, distance) if isinstance(value, dict) else None


def get_semantic_json(user_id: str, namespace: str, text: str, threshold: float = SEMANTIC_THRESHOLD) -> dict[str, Any] | None:
    match = get_semantic_json_match(user_id, namespace, text, threshold)
    return match[0] if match else None


def set_semantic_json(user_id: str, namespace: str, text: str, value: dict[str, Any]) -> None:
    if not user_id or not namespace or not text:
        return
    item_id = hashlib.sha256(f"{namespace}:{text}".encode("utf-8")).hexdigest()
    logger.info("semantic_cache_set namespace=%s text_len=%d", namespace, len(text))
    report_progress_sync("Cached semantic JSON.", {"depth": 2, "ref": "cache:semantic:set", "namespace": namespace})
    try:
        chroma.semantic_cache_collection(user_id, namespace).upsert(
            ids=[item_id],
            documents=[text],
            metadatas=[{"payload": json.dumps(value, ensure_ascii=False)}],
        )
    except Exception as exc:
        logger.warning("semantic_cache_set_error error=%s", exc)
        return


async def get_semantic_query_result(user_id: str, text: str, threshold: float = SEMANTIC_THRESHOLD, emit_progress: bool = True) -> tuple[dict[str, Any], str, float] | None:
    """Return (payload, original_text, distance) if a semantically similar query result exists."""
    if not user_id or not text:
        return None
        
    namespace = "query_result"
    try:
        results = await asyncio.to_thread(
            chroma.semantic_cache_collection(user_id, namespace).query,
            query_texts=[text],
            n_results=1,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.warning("semantic_cache_query_error error=%s", exc)
        return None
        
    distances = (results.get("distances") or [[]])[0]
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    
    if not distances or not metadatas or not documents:
        return None
        
    distance = float(distances[0])
    if 1 - distance < threshold:
        return None
        
    redis_key = metadatas[0].get("redis_key")
    if not redis_key:
        return None
        
    value = await redis.get_json(redis_key)
    if not isinstance(value, dict):
        return None
        
    return value, documents[0], distance


async def set_semantic_query_result(user_id: str, text: str, value: dict[str, Any]) -> None:
    """Store the query result payload in Redis and index its text in ChromaDB."""
    if not user_id or not text:
        return
        
    namespace = "query_result"
    item_id = hashlib.sha256(f"{namespace}:{text}".encode("utf-8")).hexdigest()
    redis_key = f"unmessit:semantic_cache:{user_id}:{item_id}"
    
    # Store large payload in redis for 7 days
    try:
        await redis.set_json(redis_key, value, 60 * 60 * 24 * 7)
    except Exception as exc:
        logger.warning("semantic_cache_redis_set_error error=%s", exc)
        return
        
    # Store embedding in chroma
    try:
        await asyncio.to_thread(
            chroma.semantic_cache_collection(user_id, namespace).upsert,
            ids=[item_id],
            documents=[text],
            metadatas=[{"redis_key": redis_key}],
        )
    except Exception as exc:
        logger.warning("semantic_cache_chroma_set_error error=%s", exc)
        return


def _text_part(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value or "")


def llm_settings_signature(user_id: str | None, stage: str | None = None) -> str | None:
    try:
        candidates = get_user_llm_setting_candidates(user_id or "", stage)
    except Exception:
        return None
    safe = [
        {
            "provider": item.llm_provider,
            "model": item.llm_model,
            "base_url": item.llm_base_url,
            "temperature": item.llm_temperature,
            "max_tokens": item.llm_max_tokens,
        }
        for item in candidates
    ]
    return json.dumps(safe, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
