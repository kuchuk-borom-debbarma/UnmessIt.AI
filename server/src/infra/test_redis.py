import pytest

from src.infra import redis as redis_infra


def setup_function():
    redis_infra.get_redis.cache_clear()


def teardown_function():
    redis_infra.get_redis.cache_clear()


def test_redis_disabled_without_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert redis_infra.redis_url() == ""
    assert redis_infra.redis_enabled() is False
    assert redis_infra.get_redis() is None


def test_redis_disabled_without_package(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    monkeypatch.setattr(redis_infra, "Redis", None)
    assert redis_infra.redis_enabled() is False
    assert redis_infra.get_redis() is None


def test_get_redis_builds_decode_responses_client(monkeypatch):
    calls = []

    class FakeRedis:
        @staticmethod
        def from_url(url, decode_responses):
            calls.append((url, decode_responses))
            return "client"

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setattr(redis_infra, "Redis", FakeRedis)
    assert redis_infra.get_redis() == "client"
    assert calls == [("redis://localhost:6379/0", True)]


@pytest.mark.asyncio
async def test_json_helpers_handle_missing_client(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    await redis_infra.set_json("k", {"v": 1}, 5)
    assert await redis_infra.get_json("k") is None


@pytest.mark.asyncio
async def test_json_helpers_round_trip_and_ignore_bad_json(monkeypatch):
    store = {}

    class FakeRedis:
        @staticmethod
        def from_url(_url, decode_responses):
            return FakeRedis()

        async def set(self, key, value, ex):
            store[key] = (value, ex)

        async def get(self, key):
            return store.get(key, (None, None))[0]

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setattr(redis_infra, "Redis", FakeRedis)
    await redis_infra.set_json("k", {"v": 1}, 9)
    assert store["k"][1] == 9
    assert await redis_infra.get_json("k") == {"v": 1}
    assert await redis_infra.get_json("missing") is None
    store["bad"] = ("{", 9)
    assert await redis_infra.get_json("bad") is None
