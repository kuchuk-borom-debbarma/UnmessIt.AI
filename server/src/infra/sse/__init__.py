from functools import lru_cache

from src.infra.redis import redis_enabled

from .models import ServerSentEvent, SseService
from .memory import MemorySseService
from .mock import MockSseService
from .redis_sse import RedisSseService

__all__ = ["SseService", "ServerSentEvent", "get_sse_service", "MockSseService"]


@lru_cache(maxsize=1)
def get_sse_service() -> SseService:
    """Build and cache the SSE service."""
    return RedisSseService() if redis_enabled() else MemorySseService()
