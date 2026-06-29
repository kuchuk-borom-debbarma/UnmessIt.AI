from typing import Any, AsyncGenerator, Protocol
from pydantic import BaseModel


class ServerSentEvent(BaseModel):
    """Payload for Server-Sent Events."""
    event: str
    data: dict[str, Any]


class SseService(Protocol):
    """Protocol for SSE infrastructure to support multiple implementations (Memory, Redis, etc)."""

    async def publish(self, topic: str, event: str, data: dict[str, Any]) -> None:
        """Publish an event payload to a topic."""
        ...

    async def subscribe(self, topic: str) -> AsyncGenerator[ServerSentEvent, None]:
        """Subscribe to a topic and yield events as they arrive."""
        ...
