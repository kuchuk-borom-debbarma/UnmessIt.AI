from __future__ import annotations

from typing import Any

from src.infra.events import get_event_bus
from src.repositories import notes, tags, directories


class NotesService:
    def __init__(self) -> None:
        self.event_bus = get_event_bus()
        
    async def create_note(self, text: str, user_id: str, directory_id: str | None = None, tag_names: list[str] | None = None) -> str:
        """Create a note and publish event for ingestion."""
        note_id = notes.create(text, user_id, directory_id)
        
        if tag_names:
            for name in tag_names:
                tag = tags.get_by_name(name, user_id)
                if not tag:
                    tag_id = tags.create(name, user_id)
                else:
                    tag_id = tag["id"]
                tags.add_to_note(note_id, tag_id)
                
        self.event_bus.publish("note.created", {
            "note_id": note_id,
            "text": text,
            "user_id": user_id
        })
        
        return note_id

    async def update_note(
        self,
        note_id: str,
        text: str,
        user_id: str,
        directory_id: str | None = None,
        tag_names: list[str] | None = None,
    ) -> bool:
        """Update a note and publish event for ingestion."""
        old_note = notes.get(note_id, user_id)
        if not old_note:
            return False
            
        old_dir = old_note["directory_id"]
        
        success = notes.update(note_id, text, user_id, directory_id)
        if success:
            if tag_names is not None:
                for tag in tags.get_for_note(note_id):
                    tags.remove_from_note(note_id, tag["id"])
                for name in tag_names:
                    tag = tags.get_by_name(name, user_id)
                    tag_id = tag["id"] if tag else tags.create(name, user_id)
                    tags.add_to_note(note_id, tag_id)
            self.event_bus.publish("note.updated", {
                "note_id": note_id,
                "text": text,
                "user_id": user_id
            })
            
            if old_dir != directory_id:
                self.event_bus.publish("note.moved", {
                    "note_id": note_id,
                    "old_directory_id": old_dir,
                    "new_directory_id": directory_id,
                    "user_id": user_id
                })
        return success

    async def hard_delete_note(self, note_id: str, user_id: str) -> bool:
        """Permanently delete a note and trigger background cleanup."""
        success = notes.hard_delete(note_id, user_id)
        if success:
            self.event_bus.publish("note.hard_deleted", {
                "note_id": note_id,
                "user_id": user_id
            })
        return success

    async def delete_directory(self, dir_id: str, user_id: str) -> bool:
        """Permanently delete a directory and all notes inside it."""
        notes_in_dir = directories.get_notes_in_subtree(dir_id, user_id)
        for note in notes_in_dir:
            await self.hard_delete_note(note["id"], user_id)
            
        return directories.delete(dir_id, user_id)


_instance = None
def get_notes_service() -> NotesService:
    global _instance
    if _instance is None:
        _instance = NotesService()
    return _instance
