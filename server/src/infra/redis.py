from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

try:
    from redis.asyncio import Redis
except ModuleNotFoundError:  # pragma: no cover - allows manual runs before uv sync
    Redis = None


def redis_url() -> str:
    return os.getenv("REDIS_URL", "").strip()


def redis_enabled() -> bool:
    return bool(redis_url() and Redis is not None)


@lru_cache(maxsize=1)
def get_redis() -> Redis | None:
    if not redis_enabled():
        return None
    return Redis.from_url(redis_url(), decode_responses=True, socket_timeout=15)


async def set_json(key: str, value: dict[str, Any], ttl_seconds: int) -> None:
    client = get_redis()
    if client is None:
        return
    await client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl_seconds)


async def get_json(key: str) -> dict[str, Any] | None:
    client = get_redis()
    if client is None:
        return None
    raw = await client.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
