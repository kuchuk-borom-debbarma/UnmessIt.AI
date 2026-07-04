from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from functools import lru_cache
import logging
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

from src.infra.progress import report_progress_sync
from src.infra.redis import redis_url

logger = logging.getLogger(__name__)

try:
    from redis import Redis
except ModuleNotFoundError:  # pragma: no cover - allows manual runs before uv sync
    Redis = None


REDIS_TTL_SECONDS = 60 * 60 * 24 * 30
MEMORY_MAX_ITEMS = 10000


class EmbeddingCache(Protocol):
    def get(self, key: str) -> list[float] | None:
        ...

    def set(self, key: str, value: list[float]) -> None:
        ...


class MemoryEmbeddingCache:
    def __init__(self, max_items: int = MEMORY_MAX_ITEMS) -> None:
        self.max_items = max_items
        self._values: OrderedDict[str, tuple[list[float], float]] = OrderedDict()

    def get(self, key: str) -> list[float] | None:
        item = self._values.get(key)
        if item is None:
            return None
        self._values.move_to_end(key)
        return item[0]

    def set(self, key: str, value: list[float]) -> None:
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


class RedisEmbeddingCache:
    def __init__(self, client, ttl_seconds: int = REDIS_TTL_SECONDS) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> list[float] | None:
        raw = self.client.get(key)
        if not raw:
            return None
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(value, list) or not all(isinstance(item, int | float) for item in value):
            return None
        return [float(item) for item in value]

    def set(self, key: str, value: list[float]) -> None:
        self.client.set(key, json.dumps(value, ensure_ascii=False), ex=self.ttl_seconds)


class CachedEmbeddingFunction:
    def __init__(
        self,
        embedding_function,
        namespace: str,
        memory_cache: EmbeddingCache | None = None,
        redis_cache: EmbeddingCache | None = None,
    ) -> None:
        self.embedding_function = embedding_function
        self.namespace = namespace
        self.memory_cache = memory_cache or get_memory_embedding_cache()
        self.redis_cache = redis_cache if redis_cache is not None else get_redis_embedding_cache()

    def __call__(self, input):
        texts = [str(item) for item in input]
        keys = [_cache_key(self.namespace, text) for text in texts]
        results: list[list[float] | None] = [None] * len(texts)
        misses: OrderedDict[str, str] = OrderedDict()

        for index, (key, text) in enumerate(zip(keys, texts)):
            cached = self._get(key)
            if cached is None:
                misses.setdefault(key, text)
            else:
                results[index] = cached

        hits = len(texts) - len(misses)
        if hits > 0:
            logger.info("embedding_cache_hit count=%d", hits)
            report_progress_sync(
                f"Reused previously computed vectors for {hits} items.",
                {"depth": 2, "ref": "cache:embedding:hit", "hits": hits},
            )

        if misses:
            miss_keys = list(misses)
            logger.info("embedding_cache_miss count=%d", len(misses))
            report_progress_sync(
                f"Computing search vectors for {len(misses)} new items...",
                {"depth": 2, "ref": "cache:embedding:miss", "misses": len(misses)},
            )
            embeddings = self.embedding_function(list(misses.values()))
            for key, embedding in zip(miss_keys, embeddings):
                value = [float(item) for item in embedding]
                self._set(key, value)
                for index, candidate in enumerate(keys):
                    if candidate == key:
                        results[index] = value
            
            logger.info("embedding_cache_set count=%d", len(misses))
            report_progress_sync(
                f"Cached {len(misses)} new embeddings.",
                {"depth": 2, "ref": "cache:embedding:set", "count": len(misses)},
            )

        if any(result is None for result in results):
            raise RuntimeError("Embedding provider returned fewer vectors than requested.")
        return [result for result in results if result is not None]

    def __getattr__(self, name):
        return getattr(self.embedding_function, name)

    def _get(self, key: str) -> list[float] | None:
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        if self.redis_cache is None:
            return None
        try:
            value = self.redis_cache.get(key)
        except Exception:
            return None
        if value is not None:
            self.memory_cache.set(key, value)
        return value

    def _set(self, key: str, value: list[float]) -> None:
        self.memory_cache.set(key, value)
        if self.redis_cache is None:
            return
        try:
            self.redis_cache.set(key, value)
        except Exception:
            return


@lru_cache(maxsize=1)
def get_memory_embedding_cache() -> MemoryEmbeddingCache:
    return MemoryEmbeddingCache()


@lru_cache(maxsize=1)
def get_redis_embedding_cache() -> RedisEmbeddingCache | None:
    url = redis_url()
    if not url or Redis is None:
        return None
    return RedisEmbeddingCache(Redis.from_url(url, decode_responses=True, socket_timeout=15))


def embedding_cache_namespace(provider: str, model: str, base_url: str | None) -> str:
    text = "|".join([provider.lower(), model, _normalized_base_url(base_url)])
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def _cache_key(namespace: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"unmessit:embedding:{namespace}:{digest}"


def _normalized_base_url(base_url: str | None) -> str:
    raw = base_url or "https://api.openai.com/v1"
    parsed = urlsplit(raw)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))
