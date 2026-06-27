import asyncio
from typing import AsyncGenerator, Any
from src.ports.event_bus import EventBus

class InMemoryEventBus(EventBus):
    def __init__(self):
        # One queue per subscriber keeps publish fan-out simple for the monolith.
        self._topics: dict[str, set[asyncio.Queue]] = {}

    async def publish(self, topic: str, message: Any):
        if topic not in self._topics:
            return
            
        # Push the message to all queues currently listening to this topic
        for queue in self._topics[topic]:
            await queue.put(message)

    async def subscribe(self, topic: str) -> AsyncGenerator[Any, None]:
        queue = asyncio.Queue()
        
        if topic not in self._topics:
            self._topics[topic] = set()
            
        self._topics[topic].add(queue)
        
        try:
            while True:
                # Yield messages as they arrive in the queue
                message = await queue.get()
                yield message
        finally:
            # Cleanup when the consumer disconnects (e.g. SSE client drops)
            self._topics[topic].remove(queue)
            if not self._topics[topic]:
                del self._topics[topic]
