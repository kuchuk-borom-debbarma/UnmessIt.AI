from __future__ import annotations

import json
from typing import Any

from src.infra.events import get_event_bus
from src.infra.redis import redis_enabled
from src.infra.sqlite import get_connection
from src.repositories import event_outbox
from src.repositories import notes, tags, directories


class NotesService:
    def __init__(self) -> None:
        self.event_bus = get_event_bus()
        
    async def create_note(self, text: str, user_id: str, directory_id: str | None = None, tag_names: list[str] | None = None, metadata: dict[str, Any] | None = None) -> str:
        """Create a note and publish event for ingestion."""
        payload = None
        conn = get_connection()
        try:
            note_id = notes.create(text, user_id, directory_id, metadata, conn)
            if tag_names:
                for name in tag_names:
                    tag = tags.get_by_name(name, user_id)
                    tag_id = tag["id"] if tag else tags.create(name, user_id, conn)
                    tags.add_to_note(note_id, tag_id, conn)
            payload = {"note_id": note_id, "text": text, "user_id": user_id}
            _enqueue_or_defer("note.created", payload, _event_key("note.created", payload), conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        if payload and not redis_enabled():
            self.event_bus.publish("note.created", payload)
        return note_id

    async def update_note(
        self,
        note_id: str,
        text: str,
        user_id: str,
        directory_id: str | None = None,
        tag_names: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update a note and publish event for ingestion."""
        old_note = notes.get(note_id, user_id)
        if not old_note:
            return False
            
        old_dir = old_note["directory_id"]
        
        old_tag_names = {t["name"] for t in tags.get_for_note(note_id)}
        new_tag_names = set(tag_names) if tag_names is not None else old_tag_names
        events: list[tuple[str, dict[str, Any]]] = []
        conn = get_connection()
        try:
            success = notes.update(note_id, text, user_id, directory_id, metadata, conn)
            if success:
                if tag_names is not None:
                    for tag in tags.get_for_note(note_id):
                        tags.remove_from_note(note_id, tag["id"], conn)
                    for name in tag_names:
                        tag = tags.get_by_name(name, user_id)
                        tag_id = tag["id"] if tag else tags.create(name, user_id, conn)
                        tags.add_to_note(note_id, tag_id, conn)
                if old_note["text"] != text:
                    events.append(("note.updated", {"note_id": note_id, "text": text, "user_id": user_id}))
                elif old_tag_names != new_tag_names:
                    events.append(("note.tags_changed", {"note_id": note_id, "user_id": user_id}))
                if old_dir != directory_id:
                    events.append(("note.moved", {
                        "note_id": note_id,
                        "old_directory_id": old_dir,
                        "new_directory_id": directory_id,
                        "user_id": user_id,
                    }))
                for topic, payload in events:
                    _enqueue_or_defer(topic, payload, _event_key(topic, payload), conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        if not redis_enabled():
            for topic, payload in events:
                self.event_bus.publish(topic, payload)
        return success

    async def soft_delete_note(self, note_id: str, user_id: str) -> bool:
        """Soft delete a note and trigger background cleanup."""
        success = self._write_note_lifecycle_event("note.soft_deleted", note_id, user_id, notes.delete)
        return success

    async def restore_note(self, note_id: str, user_id: str) -> bool:
        """Restore a soft-deleted note and trigger background re-indexing."""
        success = self._write_note_lifecycle_event("note.restored", note_id, user_id, notes.restore)
        return success

    async def hard_delete_note(self, note_id: str, user_id: str) -> bool:
        """Permanently delete a note and trigger background cleanup."""
        success = self._write_note_lifecycle_event("note.hard_deleted", note_id, user_id, notes.hard_delete)
        return success

    async def delete_directory(self, dir_id: str, user_id: str) -> bool:
        """Permanently delete a directory and all notes inside it."""
        notes_in_dir = directories.get_notes_in_subtree(dir_id, user_id)
        for note in notes_in_dir:
            await self.hard_delete_note(note["id"], user_id)
            
        return directories.delete(dir_id, user_id)

    def _write_note_lifecycle_event(self, topic: str, note_id: str, user_id: str, writer) -> bool:
        payload = {"note_id": note_id, "user_id": user_id}
        conn = get_connection()
        try:
            success = writer(note_id, user_id, conn)
            if success:
                _enqueue_or_defer(topic, payload, _event_key(topic, payload), conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        if success and not redis_enabled():
            self.event_bus.publish(topic, payload)
        return success


def _enqueue_or_defer(topic: str, payload: dict[str, Any], key: str, conn) -> None:
    if redis_enabled():
        event_outbox.enqueue(topic, topic, payload, key, conn)


def _event_key(topic: str, payload: dict[str, Any]) -> str:
    return f"{topic}:{json.dumps(payload, sort_keys=True, ensure_ascii=False)}"


_instance = None
def get_notes_service() -> NotesService:
    global _instance
    if _instance is None:
        _instance = NotesService()
    return _instance
