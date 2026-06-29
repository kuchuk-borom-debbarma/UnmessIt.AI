from typing import Any, Callable
from .models import EventBus

class MemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
        
    def subscribe(self, topic: str, handler: Callable[[dict[str, Any]], None]) -> None:
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        if handler in self._subscribers[topic]:
            return
        self._subscribers[topic].append(handler)
        
    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        if topic in self._subscribers:
            for handler in self._subscribers[topic]:
                handler(payload)
