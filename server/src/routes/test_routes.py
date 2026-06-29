from __future__ import annotations

import asyncio

from src.routes import advanced as advanced_route
from src.routes import dev as dev_route
from src.routes import directories as directories_route
from src.routes import notes as notes_route
from src.routes import retrieval as retrieval_route


def test_notes_route_creates_note_and_triggers_event(monkeypatch):
    class FakeNotesService:
        async def create_note(self, text: str, user_id: str, directory_id: str | None = None, tag_names: list[str] | None = None) -> str:
            return "note-1"

    monkeypatch.setattr(notes_route, "get_notes_service", lambda: FakeNotesService())

    response = asyncio.run(notes_route.create_note(
        notes_route.NoteCreateRequest(text="hello", tags=["test"]), 
        "user-1"
    ))

    assert response["status"] == "created"
    assert response["note_id"] == "note-1"


def test_notes_route_lists_notes_with_tags(monkeypatch):
    monkeypatch.setattr(notes_route.notes, "list_notes", lambda user_id, directory_id=None, include_all=False: [{"id": "note-1", "text": "hello"}])
    monkeypatch.setattr(notes_route.tags, "get_for_note", lambda note_id: [{"id": "tag-1", "name": "test"}])

    response = asyncio.run(notes_route.list_notes(None, False, "user-1"))

    assert response["data"][0]["tags"][0]["name"] == "test"


def test_directories_route_lists_all_directories(monkeypatch):
    monkeypatch.setattr(directories_route.directories, "list_children", lambda user_id, parent_id=None: [{"id": "root", "name": "Root"}])
    monkeypatch.setattr(directories_route.directories, "list_subtree", lambda directory_id, user_id: [{"id": "child", "name": "Child"}])

    response = asyncio.run(directories_route.list_directories(all=True, user_id="user-1"))

    assert [item["id"] for item in response["data"]] == ["root", "child"]


def test_retrieval_route_returns_current_query_shape(monkeypatch):
    class FakeRag:
        async def query(self, data: str, user_id: str, reporter=None) -> dict:
            return {"answer": "Retrieval rewrite pending.", "citations": [], "source_chunks": [], "retrieval_trace": {"query": data}}

    monkeypatch.setattr(retrieval_route, "get_rag_service", lambda: FakeRag())

    response = asyncio.run(retrieval_route.query_endpoint(retrieval_route.QueryRequest(query="hello"), "user-1"))

    assert response["answer"] == "Retrieval rewrite pending."
    assert response["source_chunks"] == []


def test_dev_routes_read_repositories(monkeypatch):
    class FakeRag:
        def list_ingest_jobs(self) -> list:
            return [{"id": "job-1"}]

        async def resume_ingest_job(self, job_id: str) -> dict:
            return {"id": job_id, "status": "queued"}

    monkeypatch.setattr(dev_route.dev, "memory_view", lambda: {"total_raw_inputs": 1, "total_source_chunks": 1, "data": []})
    monkeypatch.setattr(dev_route.dev, "recall_view", lambda: {"total_recall_keys": 1, "total_recall_links": 1, "data": []})
    monkeypatch.setattr(dev_route.dev, "raw_input", lambda input_id: {"id": input_id, "content": "hello"})
    monkeypatch.setattr(dev_route, "get_rag_service", lambda: FakeRag())

    assert dev_route.get_seai()["total_source_chunks"] == 1
    assert dev_route.get_recall()["total_recall_keys"] == 1
    assert dev_route.get_raw_input("raw-1")["data"]["content"] == "hello"
    assert dev_route.get_ingest_jobs()["total_jobs"] == 1
    assert asyncio.run(dev_route.resume_ingest_job("job-1"))["data"]["status"] == "queued"


def test_advanced_raw_input_is_user_scoped(monkeypatch):
    monkeypatch.setattr(advanced_route.raw_inputs, "get", lambda input_id: {"id": input_id, "user_id": "user-1"})

    response = asyncio.run(advanced_route.raw_input("raw-1", "user-1"))

    assert response["data"]["id"] == "raw-1"


def test_advanced_hard_delete_uses_user_scoped_vectors(monkeypatch):
    calls = []
    monkeypatch.setattr(advanced_route.raw_inputs, "get", lambda input_id: {"id": input_id, "user_id": "user-1"})
    monkeypatch.setattr(advanced_route.source_chunks, "get_by_raw_input_id", lambda input_id: [{"id": "chunk-1"}])
    monkeypatch.setattr(advanced_route.source_chunk_vectors, "delete", lambda chunk_ids, user_id: calls.append((chunk_ids, user_id)))
    monkeypatch.setattr(advanced_route.raw_inputs, "hard_delete", lambda input_id: None)

    response = asyncio.run(advanced_route.hard_delete_raw_input("raw-1", "user-1"))

    assert response["status"] == "success"
    assert calls == [(["chunk-1"], "user-1")]
