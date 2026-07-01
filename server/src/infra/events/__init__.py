from src.infra.redis import redis_enabled

from .memory import MemoryEventBus
from .models import EventBus
from .redis_stream import RedisStreamEventBus

_bus: EventBus = RedisStreamEventBus() if redis_enabled() else MemoryEventBus()

def get_event_bus() -> EventBus:
    """Return the singleton event bus."""
    return _bus


async def start_event_bus() -> None:
    start = getattr(_bus, "start", None)
    if start:
        await start()


async def stop_event_bus() -> None:
    stop = getattr(_bus, "stop", None)
    if stop:
        await stop()
