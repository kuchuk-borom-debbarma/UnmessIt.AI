import asyncio

import pytest

from src.infra.events import redis_stream
from src.infra.events.redis_stream import RedisStreamEventBus, ResponseError


@pytest.mark.asyncio
async def test_start_without_redis_does_nothing(monkeypatch):
    monkeypatch.setattr(redis_stream, "get_redis", lambda: None)
    bus = RedisStreamEventBus()
    await bus.start()
    assert bus._tasks == []


def test_publish_passes_explicit_idempotency_key(monkeypatch):
    calls = []
    bus = RedisStreamEventBus()
    monkeypatch.setattr(redis_stream.event_outbox, "enqueue", lambda *args: calls.append(args))

    bus.publish("topic", {"event_id": "event-1"})

    assert calls == [("topic", "topic", {"event_id": "event-1"}, "topic:event-1")]


def test_publish_without_explicit_key_allows_non_deduped_event(monkeypatch):
    calls = []
    bus = RedisStreamEventBus()
    monkeypatch.setattr(redis_stream.event_outbox, "enqueue", lambda *args: calls.append(args))

    bus.publish("topic", {"value": 1})

    assert calls == [("topic", "topic", {"value": 1}, None)]


@pytest.mark.asyncio
async def test_start_is_idempotent(monkeypatch):
    bus = RedisStreamEventBus()
    task = asyncio.create_task(asyncio.sleep(60))
    bus._tasks = [task]
    monkeypatch.setattr(redis_stream, "get_redis", lambda: pytest.fail("redis should not be read"))

    await bus.start()

    assert bus._tasks == [task]
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_dispatch_loop_waits_when_redis_is_unavailable(monkeypatch):
    bus = RedisStreamEventBus()
    monkeypatch.setattr(redis_stream, "get_redis", lambda: None)

    async def fake_sleep(_seconds):
        bus._stopped.set()

    monkeypatch.setattr(redis_stream.asyncio, "sleep", fake_sleep)

    await bus._dispatch_loop()


@pytest.mark.asyncio
async def test_dispatch_loop_marks_failed_when_xadd_fails(monkeypatch):
    bus = RedisStreamEventBus()
    failed = []

    class FakeClient:
        async def xadd(self, *args, **kwargs):
            raise RuntimeError("redis down")

    async def fake_sleep(_seconds):
        bus._stopped.set()

    monkeypatch.setattr(redis_stream, "get_redis", lambda: FakeClient())
    monkeypatch.setattr(redis_stream.event_outbox, "pending", lambda _limit: [{"id": "event-1", "topic": "topic", "event_type": "topic", "payload": {}}])
    monkeypatch.setattr(redis_stream.event_outbox, "mark_failed", lambda event_id: failed.append(event_id))
    monkeypatch.setattr(redis_stream.asyncio, "sleep", fake_sleep)

    await bus._dispatch_loop()

    assert failed == ["event-1"]


@pytest.mark.asyncio
async def test_consume_loop_waits_when_redis_is_unavailable(monkeypatch):
    bus = RedisStreamEventBus()
    monkeypatch.setattr(redis_stream, "get_redis", lambda: None)

    async def fake_sleep(_seconds):
        bus._stopped.set()

    monkeypatch.setattr(redis_stream.asyncio, "sleep", fake_sleep)

    await bus._consume_loop()


@pytest.mark.asyncio
async def test_consume_loop_recovers_after_consumer_error(monkeypatch):
    bus = RedisStreamEventBus()
    monkeypatch.setattr(redis_stream, "get_redis", lambda: object())
    monkeypatch.setattr(bus, "_consume_messages", lambda _client: asyncio.sleep(0, result=None / 0))

    async def fake_sleep(_seconds):
        bus._stopped.set()

    monkeypatch.setattr(redis_stream.asyncio, "sleep", fake_sleep)

    await bus._consume_loop()


@pytest.mark.asyncio
async def test_ensure_group_ignores_busygroup():
    class FakeClient:
        async def xgroup_create(self, *args, **kwargs):
            raise ResponseError("BUSYGROUP Consumer Group name already exists")

    await redis_stream._ensure_group(FakeClient())


@pytest.mark.asyncio
async def test_ensure_group_reraises_other_response_error():
    class FakeClient:
        async def xgroup_create(self, *args, **kwargs):
            raise ResponseError("nope")

    with pytest.raises(ResponseError):
        await redis_stream._ensure_group(FakeClient())


@pytest.mark.asyncio
async def test_handle_missing_fields_and_bad_json(monkeypatch):
    bus = RedisStreamEventBus()
    assert await bus._handle({}) is True
    assert await bus._handle({"topic": "missing-event"}) is True
    assert await bus._handle({"topic": "topic", "event_id": "e1", "payload": "{"}) is True


@pytest.mark.asyncio
async def test_handle_skips_completed_handler(monkeypatch):
    calls = []
    bus = RedisStreamEventBus()
    bus.subscribe("topic", lambda payload: calls.append(payload))
    monkeypatch.setattr(redis_stream.event_outbox, "begin_handler", lambda event_id, name: False)

    assert await bus._handle({"topic": "topic", "event_id": "e1", "payload": '{"ok": true}'}) is True
    assert calls == []


@pytest.mark.asyncio
async def test_handle_records_failure(monkeypatch):
    failures = []
    bus = RedisStreamEventBus()

    def bad_handler(_payload):
        raise RuntimeError("boom")

    bus.subscribe("topic", bad_handler)
    monkeypatch.setattr(redis_stream.event_outbox, "begin_handler", lambda event_id, name: True)
    monkeypatch.setattr(redis_stream.event_outbox, "fail_handler", lambda *args: failures.append(args))

    ok = await bus._handle({"topic": "topic", "event_id": "e1", "payload": '{"ok": true}'})

    assert ok is False
    assert failures and failures[0][0] == "e1"


@pytest.mark.asyncio
async def test_consume_messages_acks_only_handled(monkeypatch):
    handled = []
    acked = []
    bus = RedisStreamEventBus()

    class FakeClient:
        async def xreadgroup(self, *args, **kwargs):
            return [["stream", [("1-0", {"event_id": "e1"}), ("2-0", {"event_id": "e2"})]]]

        async def xack(self, stream, group, redis_id):
            acked.append((stream, group, redis_id))

    async def fake_handle(fields):
        handled.append(fields["event_id"])
        return fields["event_id"] == "e1"

    monkeypatch.setattr(bus, "_handle", fake_handle)
    await bus._consume_messages(FakeClient())

    assert handled == ["e1", "e2"]
    assert acked == [(redis_stream.STREAM, redis_stream.GROUP, "1-0")]


@pytest.mark.asyncio
async def test_claim_stale_handles_response_error_and_acks(monkeypatch):
    acked = []
    bus = RedisStreamEventBus()

    class ErrorClient:
        async def xautoclaim(self, *args, **kwargs):
            raise ResponseError("empty")

    await bus._claim_stale(ErrorClient())

    class GoodClient:
        async def xautoclaim(self, *args, **kwargs):
            return ["0-0", [("3-0", {"event_id": "e3"})]]

        async def xack(self, stream, group, redis_id):
            acked.append(redis_id)

    monkeypatch.setattr(bus, "_handle", lambda fields: asyncio.sleep(0, result=True))
    await bus._claim_stale(GoodClient())
    assert acked == ["3-0"]
