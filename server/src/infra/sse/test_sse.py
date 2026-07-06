import asyncio
import pytest

from src.infra.sse import get_sse_service
from src.infra.sse.memory import MemorySseService
from src.infra.sse.mock import MockSseService
from src.infra.sse import redis_sse
from src.infra.sse.redis_sse import RedisSseService


@pytest.mark.asyncio
async def test_memory_sse_pubsub():
    """Verify MemorySseService can route events to multiple subscribers and clean up."""
    service = MemorySseService()

    # Create two consumers for the same topic
    sub1 = service.subscribe("test_topic")
    sub2 = service.subscribe("test_topic")

    # Start iteration to register the queues inside the service
    # We use anext() to wait for the first item, but we'll run them as tasks
    # so they block until an event is published
    t1 = asyncio.create_task(anext(sub1))
    t2 = asyncio.create_task(anext(sub2))

    # Yield control to the event loop so the subscribers hit q.get() and register their queues
    await asyncio.sleep(0.01)

    assert "test_topic" in service._topics
    assert len(service._topics["test_topic"]) == 2

    # Publish an event
    await service.publish("test_topic", "message", {"hello": "world"})

    # Both subscribers should receive it
    event1 = await t1
    event2 = await t2

    assert event1.event == "message"
    assert event1.data == {"hello": "world"}
    assert event2.event == "message"
    assert event2.data == {"hello": "world"}

    # Simulate sub1 disconnecting (generator cleanup)
    await sub1.aclose()
    
    # Need to manually yield to let the finally block run
    await asyncio.sleep(0.01)
    
    # Topic should have 1 subscriber left
    assert len(service._topics["test_topic"]) == 1

    # Simulate sub2 disconnecting
    await sub2.aclose()
    await asyncio.sleep(0.01)

    # Topic should be deleted when empty
    assert "test_topic" not in service._topics


@pytest.mark.asyncio
async def test_mock_sse_service():
    """Verify MockSseService records published events."""
    service = MockSseService()
    
    await service.publish("some_topic", "test_event", {"status": "ok"})
    
    assert len(service.published_events) == 1
    topic, sse = service.published_events[0]
    assert topic == "some_topic"
    assert sse.event == "test_event"
    assert sse.data == {"status": "ok"}


@pytest.mark.asyncio
async def test_redis_sse_pubsub_and_presence(monkeypatch):
    queue: asyncio.Queue = asyncio.Queue()
    deleted = []
    presence = []

    class FakePubSub:
        async def subscribe(self, _channel):
            return None

        async def listen(self):
            while True:
                yield await queue.get()

        async def close(self):
            return None

    class FakeRedis:
        def pubsub(self):
            return FakePubSub()

        async def publish(self, channel, data):
            await queue.put({"type": "message", "channel": channel, "data": data})

        async def delete(self, key):
            deleted.append(key)
            
        async def zadd(self, name, mapping):
            pass
            
        async def zremrangebyscore(self, name, min, max):
            pass
            
        async def zrangebyscore(self, name, min, max):
            # mock getting the instance_id
            return ["fake_instance_id"]

    async def fake_set_json(key, value, ttl_seconds):
        presence.append((key, value, ttl_seconds))

    fake = FakeRedis()
    monkeypatch.setattr(redis_sse, "get_redis", lambda: fake)
    monkeypatch.setattr(redis_sse, "set_json", fake_set_json)

    service = RedisSseService()
    service._instance_id = "fake_instance_id"
    await service.start()
    sub1 = service.subscribe("topic")
    sub2 = service.subscribe("topic")
    t1 = asyncio.create_task(anext(sub1))
    t2 = asyncio.create_task(anext(sub2))
    await asyncio.sleep(0.01)

    await service.publish("topic", "message", {"ok": True})

    event1 = await asyncio.wait_for(t1, timeout=1)
    event2 = await asyncio.wait_for(t2, timeout=1)
    assert event1.data == {"ok": True}
    assert event2.data == {"ok": True}
    assert presence

    await sub1.aclose()
    await sub2.aclose()
    await service.stop()
    assert len(deleted) == 2


@pytest.mark.asyncio
async def test_redis_sse_falls_back_to_local_publish(monkeypatch):
    monkeypatch.setattr(redis_sse, "get_redis", lambda: None)
    service = RedisSseService()
    sub = service.subscribe("topic")
    task = asyncio.create_task(anext(sub))
    await asyncio.sleep(0.01)

    await service.publish("topic", "message", {"local": True})

    assert (await task).data == {"local": True}
    await sub.aclose()


@pytest.mark.asyncio
async def test_redis_sse_start_is_idempotent(monkeypatch):
    service = RedisSseService()
    task = asyncio.create_task(asyncio.sleep(60))
    service._listener_task = task

    await service.start()

    assert service._listener_task is task
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_redis_sse_listener_waits_without_redis(monkeypatch):
    service = RedisSseService()
    monkeypatch.setattr(redis_sse, "get_redis", lambda: None)

    async def fake_sleep(_seconds):
        service._stopped.set()

    monkeypatch.setattr(redis_sse.asyncio, "sleep", fake_sleep)

    await service._listen()


@pytest.mark.asyncio
async def test_redis_sse_listener_ignores_non_messages_and_stops(monkeypatch):
    closed = []

    class FakePubSub:
        async def subscribe(self, _channel):
            return None

        async def listen(self):
            yield {"type": "subscribe", "data": "ok"}
            yield {"type": "message", "data": '{"topic":"topic","event":"message","data":{"ok":true}}'}

        async def close(self):
            closed.append(True)

    class FakeRedis:
        def pubsub(self):
            return FakePubSub()

    service = RedisSseService()
    service._topics.add("topic")
    delivered = []
    monkeypatch.setattr(redis_sse, "get_redis", lambda: FakeRedis())

    async def fake_publish(topic, event, data):
        delivered.append((topic, event, data))
        service._stopped.set()

    monkeypatch.setattr(service._local, "publish", fake_publish)

    async def fake_sleep(_seconds):
        service._stopped.set()

    monkeypatch.setattr(redis_sse.asyncio, "sleep", fake_sleep)

    await service._listen()

    assert delivered == [("topic", "message", {"ok": True})]
    assert closed == [True]


@pytest.mark.asyncio
async def test_redis_sse_listener_breaks_when_stopped(monkeypatch):
    closed = []

    class FakePubSub:
        async def subscribe(self, _channel):
            return None

        async def listen(self):
            service._stopped.set()
            yield {"type": "message", "data": '{"topic":"topic"}'}

        async def close(self):
            closed.append(True)

    class FakeRedis:
        def pubsub(self):
            return FakePubSub()

    service = RedisSseService()
    monkeypatch.setattr(redis_sse, "get_redis", lambda: FakeRedis())

    await service._listen()

    assert closed == [True]


@pytest.mark.asyncio
async def test_redis_sse_listener_recovers_after_pubsub_error(monkeypatch):
    closed = []

    class FakePubSub:
        async def subscribe(self, _channel):
            raise RuntimeError("pubsub down")

        async def close(self):
            closed.append(True)

    class FakeRedis:
        def pubsub(self):
            return FakePubSub()

    service = RedisSseService()
    monkeypatch.setattr(redis_sse, "get_redis", lambda: FakeRedis())

    async def fake_sleep(_seconds):
        service._stopped.set()

    monkeypatch.setattr(redis_sse.asyncio, "sleep", fake_sleep)

    await service._listen()

    assert closed == [True]


@pytest.mark.asyncio
async def test_redis_sse_ignores_bad_or_unsubscribed_messages(monkeypatch):
    service = RedisSseService()
    await service._deliver("{")
    await service._deliver('{"topic": "other", "event": "message", "data": {"x": 1}}')
    assert service._topics == set()
