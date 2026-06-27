import pytest
import asyncio
from src.infra.event_bus.adapters.in_memory_event_bus import InMemoryEventBus

@pytest.mark.anyio
async def test_in_memory_event_bus_pubsub():
    bus = InMemoryEventBus()
    
    # We will track messages received by a subscriber
    received_messages = []
    
    # Subscriber task
    async def subscriber_task():
        async for msg in bus.subscribe("pipeline_events"):
            received_messages.append(msg)
            if len(received_messages) == 2:
                break
                
    # Start the subscriber in the background
    sub_task = asyncio.create_task(subscriber_task())
    
    # Give the subscriber a tiny moment to hook onto the topic
    await asyncio.sleep(0.1)
    
    # Publish two events
    await bus.publish("pipeline_events", {"stage": "segmenter", "status": "processing"})
    await bus.publish("pipeline_events", {"stage": "llm_extract", "status": "processing"})
    
    # Wait for subscriber to finish
    await asyncio.wait_for(sub_task, timeout=1.0)
    
    # Verify the messages hit the subscriber through the queue
    assert len(received_messages) == 2
    assert received_messages[0]["stage"] == "segmenter"
    assert received_messages[1]["stage"] == "llm_extract"
