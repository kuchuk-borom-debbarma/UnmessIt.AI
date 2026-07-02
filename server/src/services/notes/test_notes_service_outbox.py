import pytest

from src.infra.sqlite import get_connection
from src.services.notes import notes_service
from src.services.notes.notes_service import NotesService


class RecordingBus:
    def __init__(self):
        self.events = []

    def publish(self, topic, payload):
        self.events.append((topic, payload))


@pytest.fixture(autouse=True)
def setup_db():
    conn = get_connection()
    conn.execute("DELETE FROM event_outbox")
    conn.execute("DELETE FROM note_tags")
    conn.execute("DELETE FROM tags")
    conn.execute("DELETE FROM notes")
    conn.execute("DELETE FROM directories")
    conn.execute("DELETE FROM users")
    conn.execute("INSERT INTO users (id, identifier, password_hash) VALUES ('user-1', 'user', 'hash')")
    conn.commit()
    yield
    conn.execute("DELETE FROM event_outbox")
    conn.execute("DELETE FROM note_tags")
    conn.execute("DELETE FROM tags")
    conn.execute("DELETE FROM notes")
    conn.execute("DELETE FROM directories")
    conn.execute("DELETE FROM users")
    conn.commit()


@pytest.mark.asyncio
async def test_create_note_writes_outbox_in_redis_mode(monkeypatch):
    monkeypatch.setattr(notes_service, "redis_enabled", lambda: True)

    note_id = await NotesService().create_note("hello", "user-1")

    conn = get_connection()
    note = conn.execute("SELECT id, text FROM notes WHERE id = ?", (note_id,)).fetchone()
    event = conn.execute("SELECT topic, payload FROM event_outbox").fetchone()

    assert dict(note) == {"id": note_id, "text": "hello"}
    assert event["topic"] == "note.created"
    assert note_id in event["payload"]


@pytest.mark.asyncio
async def test_create_note_rolls_back_when_outbox_enqueue_fails(monkeypatch):
    monkeypatch.setattr(notes_service, "redis_enabled", lambda: True)

    def fail_enqueue(*args, **kwargs):
        raise RuntimeError("outbox down")

    monkeypatch.setattr(notes_service.event_outbox, "enqueue", fail_enqueue)

    with pytest.raises(RuntimeError):
        await NotesService().create_note("hello", "user-1")

    row = get_connection().execute("SELECT id FROM notes WHERE text = 'hello'").fetchone()
    assert row is None


@pytest.mark.asyncio
async def test_create_note_with_tags_writes_single_created_event(monkeypatch):
    monkeypatch.setattr(notes_service, "redis_enabled", lambda: True)

    note_id = await NotesService().create_note("hello", "user-1", tag_names=["a", "b"])

    conn = get_connection()
    tags = conn.execute(
        """
        SELECT t.name
        FROM tags t
        JOIN note_tags nt ON nt.tag_id = t.id
        WHERE nt.note_id = ?
        ORDER BY t.name
        """,
        (note_id,),
    ).fetchall()
    events = conn.execute("SELECT topic FROM event_outbox").fetchall()
    assert [row["name"] for row in tags] == ["a", "b"]
    assert [row["topic"] for row in events] == ["note.created"]


@pytest.mark.asyncio
async def test_update_note_text_and_move_write_transactional_events(monkeypatch):
    monkeypatch.setattr(notes_service, "redis_enabled", lambda: True)
    conn = get_connection()
    conn.execute("INSERT INTO directories (id, name, path, user_id) VALUES ('dir-1', 'Dir', '/dir-1/', 'user-1')")
    conn.commit()
    service = NotesService()
    note_id = await service.create_note("old", "user-1")
    conn.execute("DELETE FROM event_outbox")
    conn.commit()

    assert await service.update_note(note_id, "new", "user-1", directory_id="dir-1") is True

    note = conn.execute("SELECT text, directory_id FROM notes WHERE id = ?", (note_id,)).fetchone()
    topics = [row["topic"] for row in conn.execute("SELECT topic FROM event_outbox ORDER BY created_at").fetchall()]
    assert dict(note) == {"text": "new", "directory_id": "dir-1"}
    assert topics == ["note.updated", "note.moved"]


@pytest.mark.asyncio
async def test_update_note_tags_only_writes_tags_changed(monkeypatch):
    monkeypatch.setattr(notes_service, "redis_enabled", lambda: True)
    service = NotesService()
    note_id = await service.create_note("same", "user-1", tag_names=["old"])
    conn = get_connection()
    conn.execute("DELETE FROM event_outbox")
    conn.commit()

    assert await service.update_note(note_id, "same", "user-1", tag_names=["new"]) is True

    topics = [row["topic"] for row in conn.execute("SELECT topic FROM event_outbox").fetchall()]
    assert topics == ["note.tags_changed"]


@pytest.mark.asyncio
async def test_note_lifecycle_events_and_missing_update(monkeypatch):
    monkeypatch.setattr(notes_service, "redis_enabled", lambda: True)
    service = NotesService()
    assert await service.update_note("missing", "x", "user-1") is False
    note_id = await service.create_note("delete me", "user-1")
    conn = get_connection()
    conn.execute("DELETE FROM event_outbox")
    conn.commit()

    assert await service.soft_delete_note(note_id, "user-1") is True
    assert await service.restore_note(note_id, "user-1") is True
    assert await service.hard_delete_note(note_id, "user-1") is True

    topics = [row["topic"] for row in conn.execute("SELECT topic FROM event_outbox").fetchall()]
    assert topics == ["note.soft_deleted", "note.restored", "note.hard_deleted"]


@pytest.mark.asyncio
async def test_delete_directory_hard_deletes_notes_and_directory(monkeypatch):
    monkeypatch.setattr(notes_service, "redis_enabled", lambda: True)
    conn = get_connection()
    conn.execute("INSERT INTO directories (id, name, path, user_id) VALUES ('dir-1', 'Dir', '/dir-1/', 'user-1')")
    conn.commit()
    service = NotesService()
    await service.create_note("inside", "user-1", directory_id="dir-1")
    conn.execute("DELETE FROM event_outbox")
    conn.commit()

    assert await service.delete_directory("dir-1", "user-1") is True

    assert conn.execute("SELECT id FROM notes").fetchone() is None
    assert conn.execute("SELECT id FROM directories").fetchone() is None
    assert [row["topic"] for row in conn.execute("SELECT topic FROM event_outbox").fetchall()] == ["note.hard_deleted"]


@pytest.mark.asyncio
async def test_memory_mode_publishes_note_lifecycle_events_without_outbox(monkeypatch):
    monkeypatch.setattr(notes_service, "redis_enabled", lambda: False)
    service = NotesService()
    bus = RecordingBus()
    service.event_bus = bus

    note_id = await service.create_note("old", "user-1", tag_names=["old"])
    assert await service.update_note(note_id, "new", "user-1", tag_names=["old"]) is True
    assert await service.update_note(note_id, "new", "user-1", tag_names=["new"]) is True
    assert await service.soft_delete_note(note_id, "user-1") is True

    topics = [topic for topic, _payload in bus.events]
    assert topics == ["note.created", "note.updated", "note.tags_changed", "note.soft_deleted"]
    assert get_connection().execute("SELECT id FROM event_outbox").fetchone() is None


@pytest.mark.asyncio
async def test_memory_mode_publishes_move_event(monkeypatch):
    monkeypatch.setattr(notes_service, "redis_enabled", lambda: False)
    conn = get_connection()
    conn.execute("INSERT INTO directories (id, name, path, user_id) VALUES ('dir-1', 'Dir', '/dir-1/', 'user-1')")
    conn.commit()
    service = NotesService()
    bus = RecordingBus()
    service.event_bus = bus
    note_id = await service.create_note("same", "user-1")
    bus.events.clear()

    assert await service.update_note(note_id, "same", "user-1", directory_id="dir-1") is True

    assert bus.events == [
        (
            "note.moved",
            {"note_id": note_id, "old_directory_id": None, "new_directory_id": "dir-1", "user_id": "user-1"},
        )
    ]


@pytest.mark.asyncio
async def test_update_note_rolls_back_when_writer_fails(monkeypatch):
    monkeypatch.setattr(notes_service, "redis_enabled", lambda: True)
    service = NotesService()
    note_id = await service.create_note("original", "user-1")

    def fail_update(*args, **kwargs):
        raise RuntimeError("write failed")

    monkeypatch.setattr(notes_service.notes, "update", fail_update)

    with pytest.raises(RuntimeError):
        await service.update_note(note_id, "changed", "user-1")

    note = get_connection().execute("SELECT text FROM notes WHERE id = ?", (note_id,)).fetchone()
    assert note["text"] == "original"


def test_lifecycle_write_rolls_back_when_writer_fails(monkeypatch):
    monkeypatch.setattr(notes_service, "redis_enabled", lambda: True)
    service = NotesService()

    def fail_writer(note_id, user_id, conn):
        conn.execute("INSERT INTO notes (id, text, user_id) VALUES ('partial', 'bad', 'user-1')")
        raise RuntimeError("write failed")

    with pytest.raises(RuntimeError):
        service._write_note_lifecycle_event("note.soft_deleted", "note-1", "user-1", fail_writer)

    assert get_connection().execute("SELECT id FROM notes WHERE id = 'partial'").fetchone() is None


def test_get_notes_service_creates_singleton(monkeypatch):
    monkeypatch.setattr(notes_service, "_instance", None)

    first = notes_service.get_notes_service()
    second = notes_service.get_notes_service()

    assert first is second
