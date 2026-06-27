from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any


class EventBus(ABC):
    @abstractmethod
    async def publish(self, topic: str, message: Any) -> None:
        ...

    @abstractmethod
    async def subscribe(self, topic: str) -> AsyncGenerator[Any, None]:
        ...

