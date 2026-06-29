from typing import Any, Callable, Protocol

class EventBus(Protocol):
    def subscribe(self, topic: str, handler: Callable[[dict[str, Any]], None]) -> None:
        """Subscribe a synchronous handler to a topic."""
        ...
        
    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish an event to all subscribers synchronously."""
        ...
