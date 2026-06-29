from functools import lru_cache

from .models import ServerSentEvent, SseService
from .memory import MemorySseService
from .mock import MockSseService

__all__ = ["SseService", "ServerSentEvent", "get_sse_service", "MockSseService"]


@lru_cache(maxsize=1)
def get_sse_service() -> SseService:
    """Build and cache the SSE service.
    
    Future: Read from settings to return RedisSseService if running in a distributed environment.
    """
    return MemorySseService()
