from __future__ import annotations

import asyncio
import json
import logging
import socket
from typing import Any, Callable

try:
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import ResponseError, TimeoutError
except ModuleNotFoundError:  # pragma: no cover - import guard before uv sync
    class ResponseError(Exception):
        pass
    class RedisConnectionError(Exception):
        pass
    class TimeoutError(Exception):
        pass

from src.infra.redis import get_redis
from src.repositories import event_outbox

from .models import EventBus

logger = logging.getLogger(__name__)

STREAM = "unmessit:events"
GROUP = "unmessit:server"
DISPATCH_BATCH = 100
CONSUME_BATCH = 50
BLOCK_MS = 5000
STALE_MS = 60000


class RedisStreamEventBus(EventBus):
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
        self._consumer = f"{socket.gethostname()}:{id(self)}"
        self._tasks: list[asyncio.Task] = []
        self._stopped = asyncio.Event()

    def subscribe(self, topic: str, handler: Callable[[dict[str, Any]], None]) -> None:
        handlers = self._subscribers.setdefault(topic, [])
        if handler not in handlers:
            handlers.append(handler)

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        event_outbox.enqueue(topic, topic, payload, _idempotency_key(topic, payload))

    async def start(self) -> None:
        if self._tasks:
            return
        client = get_redis()
        if client is None:
            return
        try:
            await _ensure_group(client)
        except (RedisConnectionError, TimeoutError, OSError):
            logger.debug("redis_stream_start_waiting_for_redis")
        self._tasks = [
            asyncio.create_task(self._dispatch_loop(), name="redis-outbox-dispatcher"),
            asyncio.create_task(self._consume_loop(), name="redis-stream-consumer"),
        ]

    async def stop(self) -> None:
        self._stopped.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

    async def _dispatch_loop(self) -> None:
        while not self._stopped.is_set():
            client = get_redis()
            if client is None:
                await asyncio.sleep(1)
                continue
            for event in await asyncio.to_thread(event_outbox.pending, DISPATCH_BATCH):
                try:
                    await client.xadd(
                        STREAM,
                        {
                            "event_id": event["id"],
                            "topic": event["topic"],
                            "event_type": event["event_type"],
                            "payload": json.dumps(event["payload"], ensure_ascii=False),
                        },
                    )
                    await asyncio.to_thread(event_outbox.mark_published, event["id"])
                except Exception as exc:
                    if _is_redis_connection_error(exc):
                        logger.debug("event_outbox_publish_waiting_for_redis error=%s", exc)
                        await asyncio.sleep(5)
                        break
                    await asyncio.to_thread(event_outbox.mark_failed, event["id"])
                    logger.warning("event_outbox_publish_failed event_id=%s error=%s", event["id"], exc)
                    break
            await asyncio.sleep(0.5)

    async def _consume_loop(self) -> None:
        while not self._stopped.is_set():
            client = get_redis()
            if client is None:
                await asyncio.sleep(1)
                continue
            try:
                await self._consume_messages(client)
                await self._claim_stale(client)
            except asyncio.CancelledError:
                raise
            except ResponseError as exc:
                if _is_nogroup(exc):
                    await _ensure_group(client)
                    continue
                logger.warning("redis_stream_consume_failed error=%s", exc)
                await asyncio.sleep(1)
            except (RedisConnectionError, TimeoutError, OSError) as exc:
                logger.debug("redis_stream_waiting_for_redis error=%s", exc)
                await asyncio.sleep(5)
            except Exception as exc:
                logger.warning("redis_stream_consume_failed error=%s", exc)
                await asyncio.sleep(1)

    async def _consume_messages(self, client) -> None:
        messages = await client.xreadgroup(
            GROUP,
            self._consumer,
            {STREAM: ">"},
            count=CONSUME_BATCH,
            block=BLOCK_MS,
        )
        for _, entries in messages or []:
            for redis_id, fields in entries:
                if await self._handle(fields):
                    await client.xack(STREAM, GROUP, redis_id)

    async def _claim_stale(self, client) -> None:
        try:
            result = await client.xautoclaim(STREAM, GROUP, self._consumer, STALE_MS, "0-0", count=CONSUME_BATCH)
        except ResponseError:
            return
        for redis_id, fields in result[1]:
            if await self._handle(fields):
                await client.xack(STREAM, GROUP, redis_id)

    async def _handle(self, fields: dict[str, str]) -> bool:
        topic = fields.get("topic", "")
        event_id = fields.get("event_id", "")
        if not topic or not event_id:
            return True
        try:
            payload = json.loads(fields.get("payload") or "{}")
        except json.JSONDecodeError:
            payload = {}
        for handler in self._subscribers.get(topic, []):
            name = _handler_name(handler)
            if not await asyncio.to_thread(event_outbox.begin_handler, event_id, name):
                continue
            try:
                handler(payload)
            except Exception as exc:
                await asyncio.to_thread(event_outbox.fail_handler, event_id, name, str(exc))
                logger.warning("event_handler_failed event_id=%s handler=%s error=%s", event_id, name, exc)
                return False
            await asyncio.to_thread(event_outbox.complete_handler, event_id, name)
        return True


async def _ensure_group(client) -> None:
    try:
        await client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def _handler_name(handler: Callable[[dict[str, Any]], None]) -> str:
    return f"{handler.__module__}.{getattr(handler, '__qualname__', handler.__name__)}"


def _is_nogroup(exc: ResponseError) -> bool:
    return "NOGROUP" in str(exc)


def _is_redis_connection_error(exc: Exception) -> bool:
    return isinstance(exc, (RedisConnectionError, TimeoutError, OSError)) or "Connection refused" in str(exc)


def _idempotency_key(topic: str, payload: dict[str, Any]) -> str | None:
    explicit = payload.get("event_id") or payload.get("idempotency_key")
    if explicit:
        return f"{topic}:{explicit}"
    return None
