from __future__ import annotations

import asyncio
import os

import pytest

from src.infra import redis as redis_infra
from src.infra.events.redis_stream import RedisStreamEventBus
from src.infra.sse.redis_sse import RedisSseService
from src.infra.sqlite import get_connection
from src.repositories import event_outbox


pytestmark = pytest.mark.skipif(
    not os.getenv("LIVE_REDIS_URL"),
    reason="set LIVE_REDIS_URL to run live Redis integration tests",
)


@pytest.fixture(autouse=True)
async def live_redis(monkeypatch):
    monkeypatch.setenv("REDIS_URL", os.environ["LIVE_REDIS_URL"])
    redis_infra.get_redis.cache_clear()
    client = redis_infra.get_redis()
    assert client is not None
    await client.flushdb()
    conn = get_connection()
    conn.execute("DELETE FROM event_handler_runs")
    conn.execute("DELETE FROM event_outbox")
    conn.commit()
    yield client
    await client.flushdb()
    await client.aclose()
    redis_infra.get_redis.cache_clear()


@pytest.mark.asyncio
async def test_live_redis_stream_dispatch_consume_and_duplicate_skip(live_redis):
    calls = []
    bus = RedisStreamEventBus()
    bus.subscribe("live.topic", lambda payload: calls.append(payload))
    await bus.start()
    event_id = event_outbox.enqueue("live.topic", "live.topic", {"value": 1}, "live-topic-1")

    await _wait_for(lambda: calls == [{"value": 1}])
    row = get_connection().execute(
        "SELECT status FROM event_outbox WHERE id = ?",
        (event_id,),
    ).fetchone()
    assert row["status"] == event_outbox.STATUS_PUBLISHED

    await live_redis.xadd(
        "unmessit:events",
        {"event_id": event_id, "topic": "live.topic", "event_type": "live.topic", "payload": '{"value": 1}'},
    )
    await asyncio.sleep(0.25)
    assert calls == [{"value": 1}]
    await bus.stop()


@pytest.mark.asyncio
async def test_live_redis_sse_cross_instance_fanout_and_presence(live_redis):
    publisher = RedisSseService()
    subscriber = RedisSseService()
    await publisher.start()
    await subscriber.start()
    stream = subscriber.subscribe("live.sse")
    task = asyncio.create_task(anext(stream))
    await asyncio.sleep(0.05)

    keys = await live_redis.keys("unmessit:sse:connections:*")
    assert len(keys) == 1

    await publisher.publish("live.sse", "message", {"ok": True})
    event = await asyncio.wait_for(task, timeout=2)
    assert event.event == "message"
    assert event.data == {"ok": True}

    await stream.aclose()
    await asyncio.sleep(0.05)
    assert await live_redis.keys("unmessit:sse:connections:*") == []
    await publisher.stop()
    await subscriber.stop()


async def _wait_for(predicate, timeout: float = 3) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition was not met before timeout")
