from src.infra.events.memory import MemoryEventBus


def test_memory_event_bus_dedupes_handlers():
    bus = MemoryEventBus()
    calls = []

    def handler(payload):
        calls.append(payload)

    bus.subscribe("note.created", handler)
    bus.subscribe("note.created", handler)
    bus.publish("note.created", {"id": "note-1"})

    assert calls == [{"id": "note-1"}]
