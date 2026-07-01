import asyncio
import logging
from typing import Any
from src.infra.events import get_event_bus
from .models import NotificationService
from .console_impl import ConsoleNotificationService

logger = logging.getLogger(__name__)

_service = ConsoleNotificationService()

def get_notification_service() -> NotificationService:
    return _service

def _handle_notification_event(payload: dict[str, Any]) -> None:
    recipient = payload.get("recipient")
    subject = payload.get("subject")
    message = payload.get("message")
    if recipient and subject and message:
        # We fire the async send in the background since the event bus is synchronous.
        task = asyncio.create_task(_service.send(recipient, subject, message))
        task.add_done_callback(_log_send_failure)


def _log_send_failure(done: asyncio.Task) -> None:
    try:
        done.result()
    except Exception as exc:
        logger.warning("notification_send_failed error=%s", exc)

# Register the listener
get_event_bus().subscribe("notification.send", _handle_notification_event)
