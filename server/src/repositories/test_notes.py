import pytest
import os
import json
from src.repositories import notes
from src.infra.sqlite import get_connection

@pytest.fixture(autouse=True)
def setup_db():
    conn = get_connection()
    conn.execute("DELETE FROM notes")
    conn.execute("DELETE FROM users")
    conn.execute("INSERT INTO users (id, identifier, password_hash) VALUES ('test_user', 'test', 'hash')")
    conn.commit()
    yield
    conn.execute("DELETE FROM notes")
    conn.execute("DELETE FROM users")
    conn.commit()

def test_note_metadata_create_and_get():
    user_id = "test_user"
    metadata = {"filename": "test.md", "extension": "md"}
    
    note_id = notes.create("Hello world", user_id, None, metadata)
    
    fetched_note = notes.get(note_id, user_id)
    assert fetched_note is not None
    assert fetched_note["metadata"] == metadata

def test_note_metadata_update():
    user_id = "test_user"
    
    note_id = notes.create("Initial", user_id)
    
    fetched_initial = notes.get(note_id, user_id)
    assert fetched_initial["metadata"] == {} # Default is empty dict
    
    new_metadata = {"filename": "updated.txt", "extension": "txt"}
    notes.update(note_id, "Updated", user_id, None, new_metadata)
    
    fetched_updated = notes.get(note_id, user_id)
    assert fetched_updated["metadata"] == new_metadata
