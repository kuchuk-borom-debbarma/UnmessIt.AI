from __future__ import annotations

import asyncio

from src.routes import dev as dev_route
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
