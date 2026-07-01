from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

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
    monkeypatch.setattr(notes_route.notes, "list_notes", lambda user_id, directory_id=None, include_all=False, page=1, limit=20: {"data": [{"id": "note-1", "text": "hello"}], "total": 1})
    monkeypatch.setattr(notes_route.tags, "get_for_note", lambda note_id: [{"id": "tag-1", "name": "test"}])

    response = asyncio.run(notes_route.list_notes(None, False, 1, 20, "user-1"))

    assert response["data"][0]["tags"][0]["name"] == "test"


def test_directories_route_lists_all_directories(monkeypatch):
    monkeypatch.setattr(directories_route.directories, "list_children", lambda user_id, parent_id=None: [{"id": "root", "name": "Root"}])
    monkeypatch.setattr(directories_route.directories, "list_subtree", lambda directory_id, user_id: [{"id": "child", "name": "Child"}])
    monkeypatch.setattr(directories_route.directories, "list_all", lambda user_id, page, limit: {"data": [{"id": "root", "name": "Root"}, {"id": "child", "name": "Child"}], "total": 2})

    response = asyncio.run(directories_route.list_directories(all=True, user_id="user-1"))

    assert [item["id"] for item in response["data"]] == ["root", "child"]


def test_directories_route_search_directories(monkeypatch):
    calls = []
    monkeypatch.setattr(directories_route.directories, "search_by_name", lambda query, user_id, limit, cursor: calls.append((query, user_id, limit, cursor)) or [{"id": "dir-1", "name": "FoundDir"}])

    response = asyncio.run(directories_route.search_directories(q="Found", limit=10, cursor=3, user_id="user-1"))

    assert response["data"][0]["name"] == "FoundDir"
    assert calls == [("Found", "user-1", 10, 3)]


def test_retrieval_route_returns_current_query_shape(monkeypatch):
    calls = []

    class FakeRag:
        async def query(self, data: str, user_id: str, reporter=None, within_directories=None, excluding_directories=None, within_tags=None, excluding_tags=None, within_tags_condition="any") -> dict:
            calls.append((data, user_id, reporter, within_directories, excluding_directories, within_tags, excluding_tags, within_tags_condition))
            return {"answer": "Retrieval rewrite pending.", "citations": [], "source_chunks": [], "retrieval_trace": {"query": data}}

    monkeypatch.setattr(retrieval_route, "get_rag_service", lambda: FakeRag())

    response = asyncio.run(retrieval_route.query_endpoint(retrieval_route.QueryRequest(
        query="hello",
        within_directories=["dir-1"],
        excluding_directories=["dir-2"],
        within_tags=["tag-1"],
        excluding_tags=["tag-2"],
        within_tags_condition="all",
    ), "user-1"))

    assert response["answer"] == "Retrieval rewrite pending."
    assert response["source_chunks"] == []
    assert calls == [("hello", "user-1", None, ["dir-1/"], ["dir-2/"], ["tag-1"], ["tag-2"], "all")]


def test_retrieval_route_accepts_legacy_tag_names(monkeypatch):
    monkeypatch.setattr(retrieval_route.tags, "get_by_name", lambda value, user_id: {"id": "tag-id-1"} if value == "Tag One" else None)

    assert retrieval_route._tag_ids(["Tag One", "tag-id-2"], "user-1") == ["tag-id-1", "tag-id-2"]


def test_dev_routes_read_repositories(monkeypatch):
    class FakeRag:
        def list_ingest_jobs(self, user_id: str | None = None, page: int = 1, limit: int = 20) -> dict:
            return {"total_jobs": 1, "data": [{"id": "job-1"}]}

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


def test_advanced_note_recall_endpoints_use_repository(monkeypatch):
    monkeypatch.setattr(advanced_route.recall_repo, "get_paginated_keys_for_note", lambda note_id, user_id, page, limit: {"keys": [{"id": "key-1"}], "total": 1})
    monkeypatch.setattr(advanced_route.recall_repo, "get_paginated_links_for_note", lambda note_id, user_id, page, limit: {"links": [{"id": "link-1"}], "total": 1})

    keys = asyncio.run(advanced_route.get_note_recall_keys("note-1", user_id="user-1"))
    links = asyncio.run(advanced_route.get_note_recall_links("note-1", user_id="user-1"))

    assert keys["keys"] == [{"id": "key-1"}]
    assert links["links"] == [{"id": "link-1"}]


def test_advanced_hard_delete_uses_user_scoped_vectors(monkeypatch):
    calls = []
    monkeypatch.setattr(advanced_route.raw_inputs, "get", lambda input_id: {"id": input_id, "user_id": "user-1"})
    monkeypatch.setattr(advanced_route.source_chunks, "get_by_raw_input_id", lambda input_id: [{"id": "chunk-1"}])
    monkeypatch.setattr(advanced_route.source_chunk_vectors, "delete", lambda chunk_ids, user_id: calls.append((chunk_ids, user_id)))
    monkeypatch.setattr(advanced_route.raw_inputs, "hard_delete", lambda input_id: None)

    response = asyncio.run(advanced_route.hard_delete_raw_input("raw-1", "user-1"))

    assert response["status"] == "success"
    assert calls == [(["chunk-1"], "user-1")]


def test_advanced_ingest_job_events_requires_auth(monkeypatch):
    class FakeAuth:
        def verify_token(self, token: str):
            return None

    request = SimpleNamespace(headers={}, is_disconnected=lambda: False)
    monkeypatch.setattr(advanced_route, "get_auth_service", lambda: FakeAuth())

    with pytest.raises(HTTPException):
        asyncio.run(advanced_route.ingest_job_events(request))
