import asyncio
from typing import Any, AsyncGenerator
from .models import ServerSentEvent, SseService


class MemorySseService(SseService):
    """In-memory SSE pub/sub implementation for single-instance scaling.
    
    Uses asyncio.Queue to route events to subscribed clients safely.
    """

    def __init__(self) -> None:
        # topic -> set of client queues
        self._topics: dict[str, set[asyncio.Queue[ServerSentEvent]]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, event: str, data: dict[str, Any]) -> None:
        """Publish an event to all connected queues on a topic."""
        sse = ServerSentEvent(event=event, data=data)
        async with self._lock:
            queues = self._topics.get(topic, set())
            for q in queues:
                await q.put(sse)

    async def subscribe(self, topic: str) -> AsyncGenerator[ServerSentEvent, None]:
        """Subscribe to a topic and yield events until the connection closes."""
        q: asyncio.Queue[ServerSentEvent] = asyncio.Queue()
        async with self._lock:
            if topic not in self._topics:
                self._topics[topic] = set()
            self._topics[topic].add(q)

        try:
            while True:
                sse = await q.get()
                yield sse
        finally:
            # Client disconnected, clean up queue
            async with self._lock:
                if topic in self._topics:
                    self._topics[topic].discard(q)
                    if not self._topics[topic]:
                        del self._topics[topic]
