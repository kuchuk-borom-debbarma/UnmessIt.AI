from __future__ import annotations

import asyncio

from src.routes import dev as dev_route
from src.routes import ingest as ingest_route
from src.routes import retrieval as retrieval_route


def test_ingest_route_returns_processing_and_schedules(monkeypatch):
    calls = []

    class FakeRag:
        async def ingest(self, text: str, job_id: str) -> dict:
            calls.append((text, job_id))
            return {"job_id": "durable-job-1"}

    monkeypatch.setattr(ingest_route, "get_rag_service", lambda: FakeRag())

    response = asyncio.run(ingest_route.process_text(ingest_route.IngestRequest(text="hello")))

    assert response["status"] == "processing"
    assert response["job_id"] == "durable-job-1"
    assert calls[0][0] == "hello"


def test_retrieval_route_returns_current_query_shape(monkeypatch):
    class FakeRag:
        async def query(self, data: str, reporter=None) -> dict:
            return {"answer": "Retrieval rewrite pending.", "citations": [], "source_chunks": [], "retrieval_trace": {"query": data}}

    monkeypatch.setattr(retrieval_route, "get_rag_service", lambda: FakeRag())

    response = asyncio.run(retrieval_route.query_endpoint(retrieval_route.QueryRequest(query="hello")))

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
