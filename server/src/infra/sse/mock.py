from typing import Any, AsyncGenerator
from .models import ServerSentEvent, SseService


class MockSseService(SseService):
    """Mock SSE service for testing without hanging on actual queues."""

    def __init__(self) -> None:
        self.published_events: list[tuple[str, ServerSentEvent]] = []

    async def publish(self, topic: str, event: str, data: dict[str, Any]) -> None:
        self.published_events.append((topic, ServerSentEvent(event=event, data=data)))

    async def subscribe(self, topic: str) -> AsyncGenerator[ServerSentEvent, None]:
        # Yield a mock event and exit, preventing infinite hanging in tests
        yield ServerSentEvent(event="mock_started", data={})
