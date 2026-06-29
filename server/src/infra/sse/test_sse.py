import asyncio
import pytest

from src.infra.sse import get_sse_service
from src.infra.sse.memory import MemorySseService
from src.infra.sse.mock import MockSseService


@pytest.mark.asyncio
async def test_memory_sse_pubsub():
    """Verify MemorySseService can route events to multiple subscribers and clean up."""
    service = MemorySseService()

    # Create two consumers for the same topic
    sub1 = service.subscribe("test_topic")
    sub2 = service.subscribe("test_topic")

    # Start iteration to register the queues inside the service
    # We use anext() to wait for the first item, but we'll run them as tasks
    # so they block until an event is published
    t1 = asyncio.create_task(anext(sub1))
    t2 = asyncio.create_task(anext(sub2))

    # Yield control to the event loop so the subscribers hit q.get() and register their queues
    await asyncio.sleep(0.01)

    assert "test_topic" in service._topics
    assert len(service._topics["test_topic"]) == 2

    # Publish an event
    await service.publish("test_topic", "message", {"hello": "world"})

    # Both subscribers should receive it
    event1 = await t1
    event2 = await t2

    assert event1.event == "message"
    assert event1.data == {"hello": "world"}
    assert event2.event == "message"
    assert event2.data == {"hello": "world"}

    # Simulate sub1 disconnecting (generator cleanup)
    await sub1.aclose()
    
    # Need to manually yield to let the finally block run
    await asyncio.sleep(0.01)
    
    # Topic should have 1 subscriber left
    assert len(service._topics["test_topic"]) == 1

    # Simulate sub2 disconnecting
    await sub2.aclose()
    await asyncio.sleep(0.01)

    # Topic should be deleted when empty
    assert "test_topic" not in service._topics


@pytest.mark.asyncio
async def test_mock_sse_service():
    """Verify MockSseService records published events."""
    service = MockSseService()
    
    await service.publish("some_topic", "test_event", {"status": "ok"})
    
    assert len(service.published_events) == 1
    topic, sse = service.published_events[0]
    assert topic == "some_topic"
    assert sse.event == "test_event"
    assert sse.data == {"status": "ok"}
