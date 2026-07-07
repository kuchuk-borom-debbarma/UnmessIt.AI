from __future__ import annotations

import asyncio
import json
import socket
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from uuid import uuid4

from src.infra.redis import get_redis, set_json

from .memory import MemorySseService
from .models import ServerSentEvent, SseService

PRESENCE_TTL_SECONDS = 30
CHANNEL_PREFIX = "unmessit:sse:"


class RedisSseService(SseService):
    """Redis Pub/Sub fanout with process-local SSE sockets."""

    def __init__(self) -> None:
        self._local = MemorySseService()
        self._instance_id = f"{socket.gethostname()}:{uuid4()}"
        self._topics: set[str] = set()
        self._topic_counts: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._listener_task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        if self._listener_task:
            return
        self._listener_task = asyncio.create_task(self._listen(), name="redis-sse-listener")

    async def stop(self) -> None:
        self._stopped.set()
        if self._listener_task:
            self._listener_task.cancel()
            await asyncio.gather(self._listener_task, return_exceptions=True)
            self._listener_task = None

    async def publish(self, topic: str, event: str, data: dict[str, Any]) -> None:
        client = get_redis()
        if client is None:
            await self._local.publish(topic, event, data)
            return
            
        now_ts = int(datetime.now(timezone.utc).timestamp())
        min_score = now_ts - PRESENCE_TTL_SECONDS
        
        topic_key = f"{CHANNEL_PREFIX}topics:{topic}"
        await client.zremrangebyscore(topic_key, "-inf", min_score)
        active_instances = await client.zrangebyscore(topic_key, min_score, "+inf")
        
        payload = json.dumps({"topic": topic, "event": event, "data": data}, ensure_ascii=False)
        for instance in active_instances:
            await client.publish(f"{CHANNEL_PREFIX}instance:{instance}", payload)

    async def subscribe(self, topic: str) -> AsyncGenerator[ServerSentEvent, None]:
        connection_id = str(uuid4())
        await self._add_topic(topic)
        refresh = asyncio.create_task(self._refresh_presence(connection_id, topic))
        try:
            async for event in self._local.subscribe(topic):
                yield event
        finally:
            await self._remove_topic(topic)
            refresh.cancel()
            await asyncio.gather(refresh, return_exceptions=True)
            client = get_redis()
            if client is not None:
                await client.delete(_presence_key(connection_id))

    async def _add_topic(self, topic: str) -> None:
        async with self._lock:
            self._topic_counts[topic] = self._topic_counts.get(topic, 0) + 1
            self._topics.add(topic)

    async def _remove_topic(self, topic: str) -> None:
        async with self._lock:
            count = max(0, self._topic_counts.get(topic, 0) - 1)
            if count:
                self._topic_counts[topic] = count
                return
            self._topic_counts.pop(topic, None)
            self._topics.discard(topic)

    async def _listen(self) -> None:
        while not self._stopped.is_set():
            client = get_redis()
            if client is None:
                await asyncio.sleep(1)
                continue
            pubsub = client.pubsub()
            try:
                await pubsub.subscribe(f"{CHANNEL_PREFIX}instance:{self._instance_id}")
                async for message in pubsub.listen():
                    if self._stopped.is_set():
                        break
                    if message.get("type") != "message":
                        continue
                    await self._deliver(message.get("data"))
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(1)
            finally:
                close = getattr(pubsub, "aclose", pubsub.close)
                await close()

    async def _deliver(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return
        topic = str(payload.get("topic") or "")
        async with self._lock:
            if topic not in self._topics:
                return
        await self._local.publish(topic, str(payload.get("event") or "message"), payload.get("data") or {})

    async def _refresh_presence(self, connection_id: str, topic: str) -> None:
        while True:
            now = datetime.now(timezone.utc)
            await set_json(
                _presence_key(connection_id),
                {"instance_id": self._instance_id, "connection_id": connection_id, "topic": topic, "last_seen_at": now.isoformat()},
                PRESENCE_TTL_SECONDS,
            )
            client = get_redis()
            if client is not None:
                await client.zadd(f"{CHANNEL_PREFIX}topics:{topic}", {self._instance_id: int(now.timestamp())})
            await asyncio.sleep(PRESENCE_TTL_SECONDS / 3)


def _channel(topic: str) -> str:
    return f"{CHANNEL_PREFIX}{topic}"


def _presence_key(connection_id: str) -> str:
    return f"unmessit:sse:connections:{connection_id}"
