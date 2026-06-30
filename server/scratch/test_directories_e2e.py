import asyncio
import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from src.infra.events import get_event_bus
from src.infra import sqlite, chroma, settings
from src.repositories import directories, notes, source_chunks, source_chunk_vectors, raw_inputs
from src.services.rag.private.rag_service_impl import RagServiceImpl
from src.services.rag.private.listener.listener import register_rag_listeners

def setup_mocks():
    # 1. Mock Settings to avoid preset errors
    mock_settings = MagicMock()
    mock_settings.embedding_provider = "openai"
    mock_settings.embedding_api_key = "dummy"
    mock_settings.embedding_base_url = "dummy"
    mock_settings.embedding_model = "dummy"
    mock_settings.embedding_rate_limit_per_minute = 0
    settings.get_user_settings = lambda user_id: mock_settings
    chroma.get_user_settings = lambda user_id: mock_settings
    
    # 2. Mock Chroma Embedding Function (so it doesn't make real LLM network calls)
    class MockEmbeddingFunction:
        def __call__(self, input):
            return [[0.1] * 1536 for _ in input]
        def embed_query(self, input):
            return self.__call__(input)
        def embed_documents(self, input):
            return self.__call__(input)
        def name(self):
            return "mock"
    chroma._embedding_function = lambda user_id: MockEmbeddingFunction()
    
    # 3. Setup SQLite
    sqlite.init_db()

async def run_e2e():
    setup_mocks()
    
    user_id = "e2e-user"
    bus = get_event_bus()
    register_rag_listeners()
    
    # Clean up DB
    conn = sqlite.get_connection()
    conn.execute("INSERT OR IGNORE INTO users (id, identifier, password_hash) VALUES (?, ?, ?)", (user_id, "test@example.com", "hash"))
    conn.execute("DELETE FROM directories")
    conn.execute("DELETE FROM notes")
    conn.execute("DELETE FROM source_chunks")
    conn.execute("DELETE FROM raw_inputs")
    conn.commit()
    chroma.reset(user_id)
    
    print("--- 1. Testing Nested Directory Limit (Edge Case) ---")
    current_parent = None
    # 100 nested directories should succeed, 101st should fail
    for i in range(100):
        name = f"nested-{i}"
        dir_id = directories.create(name, user_id, parent_id=current_parent)
        current_parent = dir_id
        
    print("Successfully created 100 nested directories.")
    
    try:
        directories.create("nested-101", user_id, parent_id=current_parent)
        assert False, "Should have failed to create 101 nested directories!"
    except Exception as e:
        assert "Max directory depth" in str(e)
        print(f"Correctly caught nested limit error: {e}")
        
    print("\n--- 2. Setting up Directory Structure ---")
    # Clean up for main test
    conn.execute("DELETE FROM directories")
    conn.commit()
    
    root_work = directories.create("Work", user_id)
    work_alpha = directories.create("Alpha", user_id, parent_id=root_work)
    work_beta = directories.create("Beta", user_id, parent_id=root_work)
    root_personal = directories.create("Personal", user_id)
    
    # Fetch paths to verify Materialized Path works
    w = directories.get(root_work, user_id)
    w_a = directories.get(work_alpha, user_id)
    print(f"Work path: {w['path']}")
    print(f"Work Alpha path: {w_a['path']}")
    assert w_a["path"] == f"/{root_work}/{work_alpha}/"
    
    print("\n--- 3. Creating Notes and Ingesting ---")
    
    # Manually create notes (NotesService usually does this)
    note1 = notes.create("Meeting notes for Alpha project.", user_id, work_alpha)
    note2 = notes.create("Beta launch checklist.", user_id, work_beta)
    note3 = notes.create("Grocery list.", user_id, root_personal)
    
    # Create raw inputs and chunks manually to bypass the LLM summary step for this test
    # (Because the durable ingestion runner calls the LLM, we just manually inject to vector DB)
    
    r1 = raw_inputs.save(note1, "Meeting notes for Alpha project.", user_id, "hash1")
    r2 = raw_inputs.save(note2, "Beta launch checklist.", user_id, "hash2")
    r3 = raw_inputs.save(note3, "Grocery list.", user_id, "hash3")
    
    c1 = str(uuid4())
    c2 = str(uuid4())
    c3 = str(uuid4())
    
    source_chunks.save_many([
        {"id": c1, "raw_input_id": r1, "text": "Meeting notes for Alpha project.", "summary": "Alpha Meeting", "spans": [{"start": 0, "end": 10}], "user_id": user_id, "directory_path": w_a["path"], "metadata": {}},
        {"id": c2, "raw_input_id": r2, "text": "Beta launch checklist.", "summary": "Beta Checklist", "spans": [{"start": 0, "end": 10}], "user_id": user_id, "directory_path": directories.get(work_beta, user_id)["path"], "metadata": {}},
        {"id": c3, "raw_input_id": r3, "text": "Grocery list.", "summary": "Groceries", "spans": [{"start": 0, "end": 10}], "user_id": user_id, "directory_path": directories.get(root_personal, user_id)["path"], "metadata": {}}
    ])
    
    # Index them in Chroma
    source_chunk_vectors.index([source_chunks.get_by_ids([c1], user_id)[0], source_chunks.get_by_ids([c2], user_id)[0], source_chunks.get_by_ids([c3], user_id)[0]])
    print("Indexed 3 chunks to Chroma.")
    
    print("\n--- 4. Testing Directory Search (list_subtree & $in resolution) ---")
    
    # Search within 'Work' (should return Alpha and Beta notes)
    hits = source_chunk_vectors.search("test", user_id, top_k=10, within_directories=[root_work])
    print(f"Search 'Work' hits: {len(hits)}")
    assert len(hits) == 2
    
    # Search within 'Alpha' (should return only Alpha note)
    hits = source_chunk_vectors.search("test", user_id, top_k=10, within_directories=[work_alpha])
    print(f"Search 'Alpha' hits: {len(hits)}")
    assert len(hits) == 1
    assert hits[0]["object_id"] == c1
    
    # Search excluding 'Beta' from 'Work' (should return only Alpha)
    hits = source_chunk_vectors.search("test", user_id, top_k=10, within_directories=[root_work], excluding_directories=[work_beta])
    print(f"Search 'Work' excluding 'Beta' hits: {len(hits)}")
    assert len(hits) == 1
    assert hits[0]["object_id"] == c1
    
    print("\n--- 5. Testing Note Move (Event Cascade to SQLite & Chroma) ---")
    
    # Move note1 from work_alpha to root_personal
    notes.update(note1, "Meeting notes for Alpha project.", user_id, root_personal)
    
    # Manually fire the event that NotesService would fire
    bus.publish("note.moved", {"note_id": note1, "new_directory_id": root_personal, "user_id": user_id})
    await asyncio.sleep(0.5) # Wait for async listener to finish Chroma update
    
    p_path = directories.get(root_personal, user_id)["path"]
    
    # Verify SQLite was updated
    chk = source_chunks.get_by_ids([c1], user_id)[0]
    print(f"Chunk 1 directory_path in SQLite: {chk['directory_path']}")
    assert chk["directory_path"] == p_path
    
    # Verify Chroma was updated (Search in 'Work' should no longer yield Alpha note)
    hits = source_chunk_vectors.search("test", user_id, top_k=10, within_directories=[root_work])
    print(f"Search 'Work' hits after move: {len(hits)}")
    assert len(hits) == 1 # Only Beta remains
    
    # Search in 'Personal' should now yield both grocery list and the moved note
    hits = source_chunk_vectors.search("test", user_id, top_k=10, within_directories=[root_personal])
    print(f"Search 'Personal' hits after move: {len(hits)}")
    assert len(hits) == 2
    
    print("\n✅ All Edge Cases and E2E Scenarios PASSED!")

if __name__ == "__main__":
    asyncio.run(run_e2e())
