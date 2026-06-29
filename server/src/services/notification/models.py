from typing import Protocol

class NotificationService(Protocol):
    async def send(self, recipient: str, subject: str, message: str) -> None:
        """Send a notification."""
        ...
