import logging
from .models import NotificationService

logger = logging.getLogger(__name__)

class ConsoleNotificationService(NotificationService):
    async def send(self, recipient: str, subject: str, message: str) -> None:
        """A simple console notification implementation."""
        logger.info("\n========== NOTIFICATION ==========\nTo: %s\nSubject: %s\nMessage:\n%s\n==================================", recipient, subject, message)
