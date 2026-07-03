from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from functools import lru_cache
from typing import Any

from src.infra import chroma
from src.infra import redis


TTL_SECONDS = 60 * 60 * 24
MEMORY_MAX_ITEMS = 1000
SEMANTIC_THRESHOLD = 0.96


class MemoryJsonCache:
    def __init__(self, max_items: int = MEMORY_MAX_ITEMS) -> None:
        self.max_items = max_items
        self._values: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def get(self, key: str) -> dict[str, Any] | None:
        value = self._values.get(key)
        if value is None:
            return None
        self._values.move_to_end(key)
        return value

    def set(self, key: str, value: dict[str, Any]) -> None:
        self._values[key] = value
        self._values.move_to_end(key)
        while len(self._values) > self.max_items:
            self._values.popitem(last=False)


@lru_cache(maxsize=1)
def get_memory_json_cache() -> MemoryJsonCache:
    return MemoryJsonCache()


async def get_json(key: str) -> dict[str, Any] | None:
    memory = get_memory_json_cache()
    value = memory.get(key)
    if value is not None:
        return value
    try:
        value = await redis.get_json(key)
    except Exception:
        return None
    if value is not None:
        memory.set(key, value)
    return value


async def set_json(key: str, value: dict[str, Any]) -> None:
    get_memory_json_cache().set(key, value)
    try:
        await redis.set_json(key, value, TTL_SECONDS)
    except Exception:
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


def get_semantic_json(user_id: str, namespace: str, text: str, threshold: float = SEMANTIC_THRESHOLD) -> dict[str, Any] | None:
    if not user_id or not namespace or not text:
        return None
    try:
        results = chroma.semantic_cache_collection(user_id, namespace).query(
            query_texts=[text],
            n_results=1,
            include=["metadatas", "distances"],
        )
    except Exception:
        return None
    distances = (results.get("distances") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    if not distances or not metadatas:
        return None
    if 1 - float(distances[0]) < threshold:
        return None
    try:
        value = json.loads(metadatas[0].get("payload") or "{}")
    except (AttributeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def set_semantic_json(user_id: str, namespace: str, text: str, value: dict[str, Any]) -> None:
    if not user_id or not namespace or not text:
        return
    item_id = hashlib.sha256(f"{namespace}:{text}".encode("utf-8")).hexdigest()
    try:
        chroma.semantic_cache_collection(user_id, namespace).upsert(
            ids=[item_id],
            documents=[text],
            metadatas=[{"payload": json.dumps(value, ensure_ascii=False)}],
        )
    except Exception:
        return


def _text_part(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value or "")
