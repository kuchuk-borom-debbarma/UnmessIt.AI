from .models import EventBus
from .memory import MemoryEventBus

_bus = MemoryEventBus()

def get_event_bus() -> EventBus:
    """Return the singleton in-memory event bus."""
    return _bus
