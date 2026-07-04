import json

from src.infra import embedding_cache
from src.infra.embedding_cache import CachedEmbeddingFunction, MemoryEmbeddingCache, RedisEmbeddingCache


class FakeEmbeddingFunction:
    def __init__(self) -> None:
        self.calls = []

    def __call__(self, texts):
        self.calls.append(list(texts))
        return [[float(len(text)), float(index)] for index, text in enumerate(texts)]


class FakeRedis:
    def __init__(self) -> None:
        self.values = {}
        self.ttls = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex):
        self.values[key] = value
        self.ttls[key] = ex


def test_memory_cache_hit_avoids_second_provider_call(monkeypatch):
    monkeypatch.setattr(embedding_cache, "get_redis_embedding_cache", lambda: None)
    provider = FakeEmbeddingFunction()
    cached = CachedEmbeddingFunction(provider, "ns", MemoryEmbeddingCache())

    assert cached(["same"]) == [[4.0, 0.0]]
    assert cached(["same"]) == [[4.0, 0.0]]

    assert provider.calls == [["same"]]


def test_redis_cache_hit_avoids_provider_call_with_empty_memory():
    redis = FakeRedis()
    provider = FakeEmbeddingFunction()
    first = CachedEmbeddingFunction(provider, "ns", MemoryEmbeddingCache(), RedisEmbeddingCache(redis))

    assert first(["persisted"]) == [[9.0, 0.0]]

    second_provider = FakeEmbeddingFunction()
    second = CachedEmbeddingFunction(second_provider, "ns", MemoryEmbeddingCache(), RedisEmbeddingCache(redis))

    assert second(["persisted"]) == [[9.0, 0.0]]
    assert second_provider.calls == []


def test_redis_disabled_falls_back_to_memory_only(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setattr(embedding_cache, "Redis", None)
    embedding_cache.get_redis_embedding_cache.cache_clear()
    provider = FakeEmbeddingFunction()
    cached = CachedEmbeddingFunction(provider, "ns", MemoryEmbeddingCache())

    assert cached(["one"]) == [[3.0, 0.0]]
    assert cached(["one"]) == [[3.0, 0.0]]

    assert provider.calls == [["one"]]


def test_mixed_hit_miss_batch_preserves_output_order(monkeypatch):
    monkeypatch.setattr(embedding_cache, "get_redis_embedding_cache", lambda: None)
    provider = FakeEmbeddingFunction()
    cached = CachedEmbeddingFunction(provider, "ns", MemoryEmbeddingCache())

    assert cached(["cached"]) == [[6.0, 0.0]]
    assert cached(["new-a", "cached", "new-b"]) == [[5.0, 0.0], [6.0, 0.0], [5.0, 1.0]]

    assert provider.calls == [["cached"], ["new-a", "new-b"]]


def test_corrupted_redis_json_is_ignored_and_recomputed():
    redis = FakeRedis()
    redis.values["unmessit:embedding:ns:bad"] = "{"

    class CorruptRedisCache(RedisEmbeddingCache):
        def get(self, key):
            return super().get("unmessit:embedding:ns:bad")

    provider = FakeEmbeddingFunction()
    cached = CachedEmbeddingFunction(provider, "ns", MemoryEmbeddingCache(), CorruptRedisCache(redis))

    assert cached(["bad"]) == [[3.0, 0.0]]
    assert provider.calls == [["bad"]]
    assert [3.0, 0.0] in [json.loads(value) for value in redis.values.values() if value != "{"]
