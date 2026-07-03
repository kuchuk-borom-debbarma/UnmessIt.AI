from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from functools import lru_cache
from typing import Any

from src.infra import redis


TTL_SECONDS = 60 * 60 * 24
MEMORY_MAX_ITEMS = 1000


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
