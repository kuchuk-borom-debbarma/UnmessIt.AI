from src.infra import retrieval_cache


def setup_function():
    retrieval_cache.get_memory_json_cache.cache_clear()


def teardown_function():
    retrieval_cache.get_memory_json_cache.cache_clear()


async def test_retrieval_cache_reads_redis_once_then_memory(monkeypatch):
    calls = []

    async def fake_get_json(key):
        calls.append(key)
        return {"sub_queries": ["cached"]}

    monkeypatch.setattr(retrieval_cache.redis, "get_json", fake_get_json)

    assert await retrieval_cache.get_json("key-1") == {"sub_queries": ["cached"]}
    assert await retrieval_cache.get_json("key-1") == {"sub_queries": ["cached"]}
    assert calls == ["key-1"]


async def test_retrieval_cache_writes_memory_and_redis(monkeypatch):
    calls = []

    async def fake_set_json(key, value, ttl_seconds):
        calls.append((key, value, ttl_seconds))

    monkeypatch.setattr(retrieval_cache.redis, "set_json", fake_set_json)

    await retrieval_cache.set_json("key-1", {"sub_queries": ["cached"]})

    assert retrieval_cache.get_memory_json_cache().get("key-1") == {"sub_queries": ["cached"]}
    assert calls == [("key-1", {"sub_queries": ["cached"]}, retrieval_cache.TTL_SECONDS)]


def test_semantic_cache_respects_similarity_threshold(monkeypatch):
    class FakeCollection:
        def __init__(self, distance):
            self.distance = distance

        def query(self, **kwargs):
            return {"distances": [[self.distance]], "metadatas": [[{"payload": '{"subjects":["cached"]}'}]]}

    monkeypatch.setattr(retrieval_cache.chroma, "semantic_cache_collection", lambda user_id, namespace: FakeCollection(0.03))
    assert retrieval_cache.get_semantic_json("user-1", "ns", "query") == {"subjects": ["cached"]}

    monkeypatch.setattr(retrieval_cache.chroma, "semantic_cache_collection", lambda user_id, namespace: FakeCollection(0.05))
    assert retrieval_cache.get_semantic_json("user-1", "ns", "query") is None


def test_semantic_cache_writes_payload(monkeypatch):
    calls = []

    class FakeCollection:
        def upsert(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(retrieval_cache.chroma, "semantic_cache_collection", lambda user_id, namespace: FakeCollection())

    retrieval_cache.set_semantic_json("user-1", "ns", "query", {"subjects": ["cached"]})

    assert calls[0]["documents"] == ["query"]
    assert '"subjects": ["cached"]' in calls[0]["metadatas"][0]["payload"]
