from __future__ import annotations

import hashlib
import inspect
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.repositories import config_presets, dev, notes, raw_inputs, recall, recall_key_vectors, retrieval_index, source_chunk_vectors, source_chunks, tags
from src.services.rag.private.chains.recall.candidates import RecallCandidateChain
from src.services.rag.private.chains.recall.index import RecallIndexChain
from src.services.rag.private.chains.recall.normalizer import RecallNormalizerChain
from src.services.rag.private.chains.query import QueryAnswerChain, QueryEvidenceChain, QueryVerifierChain
from src.services.rag.private.chains.query import _breakdown as breakdown_mod
from src.services.rag.private.chains.query import _search as search_mod
from src.services.rag.private.chains.query import _subjects as subjects_mod
from src.services.rag.private.chains.query._breakdown import _decompose
from src.services.rag.private.chains.query._search import _rank_chunks, _snippets
from src.services.rag.private.chains.source_chunk_assembler import SourceChunkAssemblerChain
from src.services.rag.private.chains.source_chunk_drafts import SourceChunkDraftChain
from src.services.rag.private.chains.source_windows import SourceWindowChain
from src.services.rag.private.durability import DurableIngest
from src.services.rag.private.durability import events as durability_events
from src.services.rag.private.durability import repository as durability_repo
from src.services.rag.private.durability.models import STAGE_SOURCE_CHUNKS, STATUS_ABORTED, STATUS_FAILED, STATUS_QUEUED, STATUS_WAITING_RETRY
from src.services.rag.private.durability.runner import DurableIngestRunner
from src.services.rag.private.pipeline.ingest import submit_ingest_job, get_durable_ingest
from src.services.rag.private.rag_service_impl import RagServiceImpl
from src.infra import retrieval_cache


def test_ingest_progress_payload_defaults_and_structured_refs():
    assert durability_events._progress_payload("legacy message") == {
        "message": "legacy message",
        "depth": 0,
        "ref": "message:a943e689213a",
    }

    assert durability_events._progress_payload({
        "message": "Drafting",
        "depth": 3,
        "ref": "source_chunks:unit-1:draft",
        "parent_ref": "source_chunks:unit-1",
    }) == {
        "message": "Drafting",
        "depth": 3,
        "ref": "source_chunks:unit-1:draft",
        "parent_ref": "source_chunks:unit-1",
    }


class FakeJson:
    def __init__(self, fail_recall: bool = False) -> None:
        self.fail_recall = fail_recall

    def invoke_json(self, system: str, human: str) -> dict:
        if "Summarize one source chunk" in system:
            return {"summary": "summary", "source_time": None, "metadata": {}}
        if self.fail_recall:
            raise RuntimeError("bad recall")
        return {
            "recall_keys": [{"ref": "k1", "name": "Grisha", "kind": "entity", "aliases": [], "summary": ""}],
            "recall_links": [{"recall_key_ref": "k1", "source_chunk_id": "chunk-1", "relation": "about", "confidence": 1}],
        }

    async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
        return self.invoke_json(system, human)


async def test_query_verifier_filters_off_scope_chunks_and_requests_retry():
    class FakeVerifierJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            assert "without mixing unrelated contexts" in system
            return {
                "status": "needs_retry",
                "reason": "The requested scope is missing one focused subject.",
                "on_topic_ids": ["chunk-cp"],
                "off_topic_ids": ["chunk-aot"],
                "retry_query": "David Cyberpunk focused evidence",
            }

    chunks = [
        {"id": "chunk-cp", "summary": "David in one context", "_snippets": ["David details"]},
        {"id": "chunk-aot", "summary": "A different same-word context", "_snippets": ["Attack Titan details"]},
    ]

    result = await QueryVerifierChain(FakeVerifierJson()).run("compare David and Eren", chunks, "user-1")

    assert result["status"] == "needs_retry"
    assert result["on_topic_ids"] == ["chunk-cp"]
    assert result["off_topic_ids"] == ["chunk-aot"]
    assert result["retry_query"] == "David Cyberpunk focused evidence"


async def test_query_verifier_keeps_partial_on_topic_evidence():
    class PartialVerifierJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            assert "partial answer" in system
            return {
                "status": "insufficient",
                "reason": "Only one requested part is present.",
                "on_topic_ids": ["chunk-supported"],
                "off_topic_ids": [],
                "retry_query": "",
            }

    chunks = [
        {"id": "chunk-supported", "summary": "One requested part", "_snippets": ["Supported detail"]},
        {"id": "chunk-other", "summary": "Unrelated", "_snippets": ["Other detail"]},
    ]

    result = await QueryVerifierChain(PartialVerifierJson()).run("explain several related causes", chunks, "user-1")

    assert result["status"] == "sufficient"
    assert result["on_topic_ids"] == ["chunk-supported"]


async def test_ingest_submits_durable_job(monkeypatch):
    async def _fake_submit(data, user_id, job_id):
        return {"id": job_id, "status": "queued", "raw_input_id": "raw-1", "stage": "source_chunks", "attempt_count": 0, "metadata": {}}

    class FakeDurability:
        async def submit(self, data, user_id, job_id):
            return await _fake_submit(data, user_id, job_id)

    monkeypatch.setattr("src.services.rag.private.pipeline.ingest.get_durable_ingest", lambda: FakeDurability())

    result = await submit_ingest_job("  Grisha inherited the Attack Titan.  ", user_id="user-1", job_id="job-1")

    assert result["job_id"] == "job-1"
    assert result["status"] == "queued"
    assert result["raw_input_id"] == "raw-1"


async def test_source_chunk_steps_preserve_source_bound_spans():
    raw_text = "Before the walls, Grisha inherited the Attack Titan. Kruger watched."
    windows = SourceWindowChain().run(raw_text)
    drafts = await SourceChunkDraftChain(FakeJson()).run(windows[0], "user-1")
    chunks = await SourceChunkAssemblerChain().run("raw-1", raw_text, "user-1", drafts)

    assert chunks[0]["text"] == raw_text
    assert chunks[0]["spans"] == [{"start": 0, "end": len(raw_text)}]


async def test_source_chunk_llm_failure_is_retryable():
    class BrokenJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            raise RuntimeError("provider forbidden")

    with pytest.raises(RuntimeError, match="provider forbidden"):
        await SourceChunkDraftChain(BrokenJson()).run({"text": "hello", "start": 0, "end": 5}, "user-1")


def test_source_chunk_vector_metadata_move_refreshes_directory_flags(monkeypatch):
    updated = {}

    class FakeCollection:
        def get(self, ids, include):
            assert ids == ["chunk-1:source_chunk"]
            assert include == ["metadatas"]
            return {
                "ids": ids,
                "metadatas": [{
                    "object_type": "source_chunk",
                    "directory_path": "/old/",
                    "dir_old": True,
                    "tag_keep": True,
                }],
            }

        def update(self, ids, metadatas):
            updated["ids"] = ids
            updated["metadatas"] = metadatas

    monkeypatch.setattr(source_chunk_vectors.chroma, "collection", lambda user_id: FakeCollection())

    source_chunk_vectors.update_metadata(["chunk-1"], {"directory_path": "/dir-2/nested/"}, "user-1")

    assert updated == {
        "ids": ["chunk-1:source_chunk"],
        "metadatas": [{
            "object_type": "source_chunk",
            "directory_path": "/dir-2/nested/",
            "tag_keep": True,
            "dir_dir-2": True,
            "dir_nested": True,
            source_chunk_vectors._dir_path_key("/dir-2/"): True,
            source_chunk_vectors._dir_path_key("/dir-2/nested/"): True,
        }],
    }


def test_source_chunk_vector_directory_filters_use_path_prefix_keys(monkeypatch):
    captured = {}

    def fake_search(query, user_id, top_k=8, where=None):
        captured["where"] = where
        return []

    monkeypatch.setattr(source_chunk_vectors.chroma, "search", fake_search)

    source_chunk_vectors.search("hello", "user-1", within_directories=["/parent/"], excluding_directories=["/blocked/"])

    assert {source_chunk_vectors._dir_path_key("/parent/"): True} in captured["where"]["$and"][2]["$or"]
    assert {source_chunk_vectors._dir_path_key("/blocked/"): {"$ne": True}} in captured["where"]["$and"]


async def test_recall_index_chain_retries_once_after_invalid_output(monkeypatch):
    class RetryJson:
        def __init__(self) -> None:
            self.calls = 0
            self.prompts = []
            self.systems = []

        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            self.calls += 1
            self.systems.append(system)
            self.prompts.append(human)
            if self.calls == 1:
                return {"recall_keys": [{"ref": "k1", "name": "Grisha", "kind": "entity"}], "recall_links": []}
            return {
                "recall_keys": [{"ref": "k1", "name": "Grisha", "kind": "entity"}],
                "recall_links": [{"recall_key_ref": "k1", "source_chunk_id": "chunk-1", "relation": "about"}],
            }

    monkeypatch.setattr(recall, "find_candidate_keys", lambda terms, user_id, limit=20: [])
    monkeypatch.setattr(recall, "find_exact_term_matches", lambda terms, user_id, limit=3: [])
    monkeypatch.setattr(recall_key_vectors, "search", lambda text, user_id, top_k=20: [])

    json_client = RetryJson()
    index = await RecallIndexChain(json_client).run("Grisha inherited the Attack Titan.", "user-1", [_source_chunk("chunk-1", "Grisha inherited the Attack Titan.")])

    assert json_client.calls == 2
    assert "previous response failed validation" in json_client.prompts[1]
    assert "recall_key_ref" in json_client.prompts[0]
    assert "source_chunk_id" in json_client.prompts[0]
    assert "stable merged orientation" in json_client.systems[0]
    assert "Avoid tiny phrase-specific topic keys" in json_client.systems[0]
    assert index["analysis"]["validation_errors"] == 0
    assert index["recall_links"][0]["source_chunk_id"] == "chunk-1"


async def test_candidate_lookup_merges_ranks_filters_and_caps(monkeypatch):
    source_chunks_data = [_source_chunk("chunk-1", "Grisha inherited the Attack Titan.")]
    sqlite_candidates = [
        _candidate("exact-1", "Grisha Yeager", "exact"),
        _candidate("keyword-1", "Attack Titan", "keyword"),
    ]
    vector_keys = [_candidate("vector-1", "Founding Titan", "vector"), _candidate("keyword-1", "Attack Titan", "vector")]
    extra = [_candidate(f"extra-{index}", f"Extra {index}", "keyword") for index in range(25)]

    monkeypatch.setattr(recall, "find_candidate_keys", lambda terms, user_id, limit=20: [*sqlite_candidates, *extra])
    monkeypatch.setattr(recall_key_vectors, "search", lambda text, user_id, top_k=20: [
        {"object_id": "vector-1", "object_type": "recall_key", "distance": 0.2},
        {"object_id": "ignored-source", "object_type": "source_chunk", "distance": 0.1},
        {"object_id": "keyword-1", "object_type": "recall_key", "distance": 0.3},
    ])
    monkeypatch.setattr(recall, "find_keys_by_ids", lambda ids, user_id: [key for key in vector_keys if key["id"] in ids])

    candidates = await RecallCandidateChain().run("Grisha and the Founding Titan", "user-1", source_chunks_data)

    assert len(candidates) == 20
    assert [candidate["id"] for candidate in candidates[:3]] == ["exact-1", "keyword-1", "extra-0"]
    assert "ignored-source" not in {candidate["id"] for candidate in candidates}
    assert "semantic vector match" in " ".join(candidates[1]["match_notes"])


async def test_query_uses_source_search_and_recall_expansion(monkeypatch):
    chunk_1 = {**_source_chunk("chunk-1", "Grisha inherited the Attack Titan. Unrelated training details continue for a while."), "summary": "Grisha Titan evidence"}
    chunk_2 = {**_source_chunk("chunk-2", "Eren later used inherited Titan powers. Unrelated tail should not be sent."), "summary": "Eren Titan evidence"}

    class FakeQueryEvidenceChain:
        def __init__(self, json_client) -> None:
            pass

        async def run(self, query: str, user_id: str, reporter=None, within_directories=None, excluding_directories=None, within_tags=None, excluding_tags=None, within_tags_condition="any"):
            return [chunk_1, chunk_2], {"mode": "source_chunks_with_recall_expansion", "sub_query_traces": [{"recall_key_count": 1}], "context_chars_saved": 10}

    class FakeQueryAnswerChain:
        def __init__(self, json_client) -> None:
            pass

        async def run(self, query: str, chunks: list[dict], user_id: str, reporter=None):
            return {"answer": "Grisha's power later connects to Eren.", "citation_ids": ["chunk-2"]}

    monkeypatch.setattr("src.services.rag.private.rag_service_impl.QueryEvidenceChain", FakeQueryEvidenceChain)
    monkeypatch.setattr("src.services.rag.private.rag_service_impl.QueryAnswerChain", FakeQueryAnswerChain)

    result = await RagServiceImpl(FakeJson()).query("Grisha to Eren", user_id="user-1")

    assert result["answer"] == "Grisha's power later connects to Eren."
    assert [chunk["id"] for chunk in result["source_chunks"]] == ["chunk-1", "chunk-2"]
    assert result["citations"][0]["source_chunk_id"] == "chunk-2"
    sub_trace = result["retrieval_trace"]["sub_query_traces"][0]
    assert sub_trace["recall_key_count"] == 1
    assert result["retrieval_trace"]["context_chars_saved"] > 0
    assert result["source_chunks"][1]["text"] == chunk_2["text"]


async def test_query_context_packer_ranks_and_falls_back(monkeypatch):
    vector = {**_source_chunk("vector", "Attack Titan matters here. A different sentence."), "summary": "vector summary"}
    lexical = {**_source_chunk("lexical", "No direct overlap in text."), "summary": "fallback summary"}
    linked = {**_source_chunk("linked", "Attack Titan is also linked through recall."), "summary": "linked summary"}

    monkeypatch.setattr(source_chunk_vectors, "search", lambda query, user_id, top_k=8, within_directories=None, excluding_directories=None, within_tags=None, excluding_tags=None, within_tags_condition="any": [{"object_id": "vector", "object_type": "source_chunk"}])
    monkeypatch.setattr(source_chunks, "get_by_ids", lambda ids, user_id: [chunk for chunk in [vector, lexical, linked] if chunk["id"] in ids])
    monkeypatch.setattr(source_chunks, "search", lambda query, user_id, limit=8, within_directories=None, excluding_directories=None, within_tags=None, excluding_tags=None, within_tags_condition="any": [lexical])
    monkeypatch.setattr(recall, "find_candidate_keys", lambda terms, user_id, limit=8: [_candidate("key-1", "Attack Titan", "keyword")])
    monkeypatch.setattr(recall, "linked_source_chunk_ids", lambda key_ids, user_id, limit=12, within_directories=None, excluding_directories=None, within_tags=None, excluding_tags=None, within_tags_condition="any": ["linked"])

    class PassthroughBreakdownJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            if "Decompose the user query" in system:
                return {"sub_queries": ["Attack Titan"]}
            return {"answer": "ok", "citation_ids": []}

    chain = QueryEvidenceChain(PassthroughBreakdownJson())
    chunks, trace = await chain.run("Attack Titan", user_id="user-1")

    assert {chunk["id"] for chunk in chunks} == {"vector", "lexical", "linked"}
    assert trace["selected_snippet_counts"].keys() == {"vector", "lexical", "linked"}
    # lexical chunk has no query-term overlap so it falls back to its summary snippet
    lexical_chunk = next(c for c in chunks if c["id"] == "lexical")
    assert lexical_chunk["_snippets"][0] == "fallback summary"
    assert trace["context_chars_saved"] >= 0


async def test_evidence_cache_hit_skips_second_search(monkeypatch):
    retrieval_cache.get_memory_json_cache.cache_clear()
    conn = _patch_memory_db(monkeypatch)
    monkeypatch.setattr(retrieval_index, "get_connection", lambda: conn)
    monkeypatch.setattr(search_mod, "_embedding_settings_signature", lambda user_id: "embedding:v1")
    monkeypatch.setattr(retrieval_cache.redis, "get_json", _raise_async)
    monkeypatch.setattr(retrieval_cache.redis, "set_json", _raise_async)
    calls = []

    async def fake_evidence(*args, **kwargs):
        calls.append(args[0])
        return [_source_chunk("chunk-1", "Attack Titan evidence")], {"sub_query": args[0], "baseline_lengths": {"chunk-1": 21}}

    monkeypatch.setattr(search_mod, "_evidence_for", fake_evidence)
    state = _search_state()

    first = await search_mod.search_node(state)
    second = await search_mod.search_node(state)

    assert calls == ["Attack Titan"]
    assert first == second


async def test_evidence_cache_key_changes_for_filters_user_version_and_embedding(monkeypatch):
    retrieval_cache.get_memory_json_cache.cache_clear()
    conn = _patch_memory_db(monkeypatch)
    monkeypatch.setattr(retrieval_index, "get_connection", lambda: conn)
    signature = {"value": "embedding:v1"}
    monkeypatch.setattr(search_mod, "_embedding_settings_signature", lambda user_id: signature["value"])
    calls = []

    async def fake_evidence(*args, **kwargs):
        calls.append(args[0])
        return [_source_chunk(f"chunk-{len(calls)}", "Attack Titan evidence")], {"sub_query": args[0], "baseline_lengths": {}}

    monkeypatch.setattr(search_mod, "_evidence_for", fake_evidence)

    await search_mod.search_node(_search_state())
    await search_mod.search_node(_search_state(within_tags=["tag-1"]))
    await search_mod.search_node(_search_state(within_directories=["/dir/"]))
    await search_mod.search_node(_search_state(user_id="user-2"))
    retrieval_index.bump("user-1")
    await search_mod.search_node(_search_state())
    signature["value"] = "embedding:v2"
    await search_mod.search_node(_search_state())

    assert len(calls) == 6


async def test_evidence_cache_ignores_corrupt_redis_payload(monkeypatch):
    retrieval_cache.get_memory_json_cache.cache_clear()
    conn = _patch_memory_db(monkeypatch)
    monkeypatch.setattr(retrieval_index, "get_connection", lambda: conn)
    monkeypatch.setattr(search_mod, "_embedding_settings_signature", lambda user_id: "embedding:v1")
    monkeypatch.setattr(retrieval_cache.redis, "get_json", lambda key: _async_value({"chunks": "bad", "trace_parts": []}))
    calls = []

    async def fake_evidence(*args, **kwargs):
        calls.append(args[0])
        return [_source_chunk("chunk-1", "Attack Titan evidence")], {"sub_query": args[0], "baseline_lengths": {}}

    monkeypatch.setattr(search_mod, "_evidence_for", fake_evidence)

    result = await search_mod.search_node(_search_state())

    assert calls == ["Attack Titan"]
    assert result["chunks"][0]["id"] == "chunk-1"


def test_query_snippets_expand_physical_terms():
    text = "The subject likes quiet mornings.\n\nThey have two moles near the neck and a small scar."

    assert "moles" in _snippets("physical stuff", text, "")[0]


def test_query_snippets_keep_numbered_list_items_together():
    text = "Intro sentence. Physical Details\nAmy has:\n1. Six moles on her face\n2. Three moles near her ears\n3. One mole on her neck\nSensitive Physical Notes\nAmy may feel insecure about hair."

    snippet = _snippets("Amy physical infos", text, "")[0]

    assert "Six moles on her face" in snippet
    assert "Three moles near her ears" in snippet
    assert "One mole on her neck" in snippet


def test_source_chunk_lexical_search_expands_physical_terms(monkeypatch):
    conn = _memory_db()
    monkeypatch.setattr(source_chunks, "get_connection", lambda: conn)
    conn.execute("INSERT INTO raw_inputs (id, job_id, content, user_id) VALUES ('raw-1', 'note-1', 'text', 'user-1')")
    conn.execute(
        "INSERT INTO source_chunks (id, raw_input_id, text, summary, spans, metadata, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("chunk-1", "raw-1", "She has two moles near her neck.", "summary", "[]", "{}", "user-1"),
    )

    rows = source_chunks.search("physical stuff", "user-1", limit=5)

    assert [row["id"] for row in rows] == ["chunk-1"]


def test_query_rank_chunks_uses_expanded_physical_terms():
    generic = _source_chunk("generic", "Subject Alpha likes quiet mornings and old songs.")
    mole_detail = _source_chunk("mole-detail", "Subject Alpha has two moles near the neck and a small scar.")

    ranked, reasons = _rank_chunks("physical stuff about Subject Alpha", [generic, mole_detail])

    assert ranked[0]["id"] == "mole-detail"
    assert "query_terms:" in " ".join(reasons["mole-detail"])


async def test_query_answer_accepts_inline_citation_markers():
    class MarkerJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            return {"answer": "Subject Alpha has two moles. [[cite:chunk-1]]", "citation_ids": []}

    result = await QueryAnswerChain(MarkerJson()).run(
        "physical stuff about Subject Alpha",
        [_source_chunk("chunk-1", "They have two moles near the neck.")],
        user_id="user-1",
    )

    assert result["citation_ids"] == ["chunk-1"]


async def test_query_answer_sanitizes_invalid_and_malformed_citation_markers():
    class MarkerJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            return {
                "answer": "Supported [[cite:chunk-1]], malformed [[cite:chunk-2], invalid [[cite:not-real]].",
                "citation_ids": [],
            }

    result = await QueryAnswerChain(MarkerJson()).run(
        "compare Subject Alpha and Subject Beta",
        [
            _source_chunk("chunk-1", "Subject Alpha has one detail."),
            _source_chunk("chunk-2", "Subject Beta has another detail."),
        ],
        user_id="user-1",
    )

    assert result["citation_ids"] == ["chunk-1", "chunk-2"]
    assert "[[cite:chunk-2]]" in result["answer"]
    assert "not-real" not in result["answer"]


async def test_query_answer_prompt_allows_cross_context_comparison():
    class CaptureJson:
        def __init__(self) -> None:
            self.system = ""

        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            self.system = system
            return {"answer": "ok", "citation_ids": []}

    json_client = CaptureJson()
    await QueryAnswerChain(json_client).run(
        "compare Subject Alpha and Subject Beta",
        [
            _source_chunk("chunk-1", "Subject Alpha has one detail."),
            _source_chunk("chunk-2", "Subject Beta has another detail."),
        ],
        user_id="user-1",
    )

    assert "different contexts or sources" in json_client.system


async def test_query_breakdown_expands_physical_attribute_queries_when_llm_underplans():
    class OriginalOnlyJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            return {"sub_queries": ["Tell me physical stuff about Subject Alpha"]}

    result = await _decompose(OriginalOnlyJson(), "Tell me physical stuff about Subject Alpha", "user-1")

    assert result[0] == "Tell me physical stuff about Subject Alpha"
    assert any("Subject Alpha appearance physical details" in query and "counts" in query for query in result)


async def test_query_breakdown_expands_comparison_queries_when_llm_underplans():
    class OriginalOnlyJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            return {"sub_queries": ["How similar are Subject Alpha and Subject Beta?"]}

    result = await _decompose(OriginalOnlyJson(), "How similar are Subject Alpha and Subject Beta?", "user-1")

    assert result[0] == "How similar are Subject Alpha and Subject Beta?"
    assert any(query.startswith("Subject Alpha attributes context") for query in result)
    assert any(query.startswith("Subject Beta attributes context") for query in result)
    assert any("Subject Alpha Subject Beta similarities differences" in query and "attributes" in query for query in result)


async def test_query_breakdown_expands_reasoning_queries_when_llm_underplans():
    class OriginalOnlyJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            return {"sub_queries": ["Why did Subject Alpha change?"]}

    result = await _decompose(OriginalOnlyJson(), "Why did Subject Alpha change?", "user-1")

    assert result[0] == "Why did Subject Alpha change?"
    assert any("Subject Alpha evidence context causes effects" in query for query in result)


async def test_query_breakdown_splits_broad_multi_part_queries_when_llm_underplans():
    class OriginalOnlyJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            return {"sub_queries": ["How did one factor, another factor, and a later result connect over time?"]}

    query = "How did one factor, another factor, a third factor, and a later result connect over time?"
    result = await _decompose(OriginalOnlyJson(), query, "user-1")

    assert result[0] == query
    assert any("another factor evidence context" == item for item in result)
    assert any("a third factor evidence context" == item for item in result)


async def test_query_breakdown_falls_back_to_original_query_on_llm_failure():
    """Breakdown must not block retrieval when the LLM call fails."""
    class FailJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            raise RuntimeError("provider unavailable")

    result = await _decompose(FailJson(), "what happened to the project", "user-1")

    assert result == ["what happened to the project"]


async def test_query_breakdown_caps_and_deduplicates_sub_queries():
    """Breakdown must cap at 6, always lead with original, and dedup."""
    class OverflowJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            return {"sub_queries": [
                "original",
                "sub-query 1",
                "sub-query 2",
                "sub-query 1",  # duplicate
                "sub-query 3",
                "sub-query 4",
                "sub-query 5",
                "sub-query 6",  # 8th item, 7th unique — should be cut
            ]}

    result = await _decompose(OverflowJson(), "original", "user-1")

    assert result[0] == "original"
    assert len(result) == 6
    assert len(set(result)) == 6  # no duplicates
    assert "sub-query 6" not in result


def test_query_breakdown_prompt_requests_embedding_friendly_deterministic_phrases():
    system = breakdown_mod._breakdown_system_prompt()

    assert "deterministic embedding-friendly search phrases" in system
    assert "stable nouns and qualifiers" in system
    assert "avoid pronouns" in system


async def test_query_breakdown_cache_skips_second_llm_call(monkeypatch):
    retrieval_cache.get_memory_json_cache.cache_clear()
    calls = []

    class CountingJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            calls.append(human)
            return {"sub_queries": ["original", "cached expansion"]}

    monkeypatch.setattr(retrieval_cache, "llm_settings_signature", lambda user_id: "settings-a")

    first = await breakdown_mod._decompose(CountingJson(), "original", "user-1")
    second = await breakdown_mod._decompose(CountingJson(), "original", "user-1")

    assert first == ["original", "cached expansion"]
    assert second == first
    assert len(calls) == 1


async def test_query_breakdown_cache_misses_when_settings_change(monkeypatch):
    retrieval_cache.get_memory_json_cache.cache_clear()
    calls = []
    signatures = iter(["settings-a", "settings-b"])

    class CountingJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            calls.append(human)
            return {"sub_queries": ["original", f"call {len(calls)}"]}

    monkeypatch.setattr(retrieval_cache, "llm_settings_signature", lambda user_id: next(signatures))

    first = await breakdown_mod._decompose(CountingJson(), "original", "user-1")
    second = await breakdown_mod._decompose(CountingJson(), "original", "user-1")

    assert first == ["original", "call 1"]
    assert second == ["original", "call 2"]
    assert len(calls) == 2


async def test_query_subjects_exact_cache_skips_second_llm_call(monkeypatch):
    retrieval_cache.get_memory_json_cache.cache_clear()
    calls = []

    class CountingJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            calls.append(human)
            return {"subjects": ["Subject Alpha"]}

    monkeypatch.setattr(retrieval_cache, "llm_settings_signature", lambda user_id: "llm-a")
    monkeypatch.setattr(subjects_mod, "_subjects_semantic_cache_key", lambda *args: None)

    first = await subjects_mod._identify_subjects(CountingJson(), "query", ["query"], "user-1")
    second = await subjects_mod._identify_subjects(CountingJson(), "query", ["query"], "user-1")

    assert first == ["Subject Alpha"]
    assert second == first
    assert len(calls) == 1


async def test_query_subjects_exact_cache_stores_empty_subjects(monkeypatch):
    retrieval_cache.get_memory_json_cache.cache_clear()
    calls = []

    class EmptyJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            calls.append(human)
            return {"subjects": []}

    monkeypatch.setattr(retrieval_cache, "llm_settings_signature", lambda user_id: "llm-a")
    monkeypatch.setattr(subjects_mod, "_subjects_semantic_cache_key", lambda *args: None)

    assert await subjects_mod._identify_subjects(EmptyJson(), "query", ["query"], "user-1") == []
    assert await subjects_mod._identify_subjects(EmptyJson(), "query", ["query"], "user-1") == []
    assert len(calls) == 1


async def test_query_subjects_failure_fallback_is_not_cached(monkeypatch):
    retrieval_cache.get_memory_json_cache.cache_clear()
    calls = []

    class FailThenOkJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            calls.append(human)
            if len(calls) == 1:
                raise RuntimeError("down")
            return {"subjects": ["Subject Alpha"]}

    monkeypatch.setattr(retrieval_cache, "llm_settings_signature", lambda user_id: "llm-a")
    monkeypatch.setattr(subjects_mod, "_subjects_semantic_cache_key", lambda *args: None)

    assert await subjects_mod._identify_subjects(FailThenOkJson(), "query", ["query"], "user-1") == []
    assert await subjects_mod._identify_subjects(FailThenOkJson(), "query", ["query"], "user-1") == ["Subject Alpha"]
    assert len(calls) == 2


async def test_query_subjects_semantic_cache_hit_skips_llm(monkeypatch):
    retrieval_cache.get_memory_json_cache.cache_clear()

    class FailJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            raise AssertionError("LLM should not be called")

    monkeypatch.setattr(subjects_mod, "_subjects_exact_cache_key", lambda *args: None)
    monkeypatch.setattr(subjects_mod, "_subjects_semantic_cache_key", lambda *args: ("ns", "normalized query"))
    monkeypatch.setattr(retrieval_cache, "get_semantic_json", lambda *args, **kwargs: {"subjects": ["Subject Alpha"]})

    assert await subjects_mod._identify_subjects(FailJson(), "query", ["query"], "user-1") == ["Subject Alpha"]


async def test_query_subjects_semantic_miss_calls_llm(monkeypatch):
    retrieval_cache.get_memory_json_cache.cache_clear()
    calls = []

    class CountingJson:
        async def async_invoke_json(self, system: str, human: str, **kwargs) -> dict:
            calls.append(human)
            return {"subjects": ["Subject Alpha"]}

    monkeypatch.setattr(subjects_mod, "_subjects_exact_cache_key", lambda *args: None)
    monkeypatch.setattr(subjects_mod, "_subjects_semantic_cache_key", lambda *args: ("ns", "normalized query"))
    monkeypatch.setattr(retrieval_cache, "get_semantic_json", lambda *args, **kwargs: None)
    monkeypatch.setattr(retrieval_cache, "set_semantic_json", lambda *args, **kwargs: None)

    assert await subjects_mod._identify_subjects(CountingJson(), "query", ["query"], "user-1") == ["Subject Alpha"]
    assert len(calls) == 1


def test_query_subjects_semantic_cache_key_changes_with_signatures(monkeypatch):
    monkeypatch.setattr(retrieval_cache, "llm_settings_signature", lambda user_id: "llm-a")
    monkeypatch.setattr(subjects_mod, "_embedding_settings_signature", lambda user_id: "embed-a")
    first = subjects_mod._subjects_semantic_cache_key("query", ["sub"], "user-1", "system")

    monkeypatch.setattr(retrieval_cache, "llm_settings_signature", lambda user_id: "llm-b")
    second = subjects_mod._subjects_semantic_cache_key("query", ["sub"], "user-1", "system")

    monkeypatch.setattr(retrieval_cache, "llm_settings_signature", lambda user_id: "llm-a")
    monkeypatch.setattr(subjects_mod, "_embedding_settings_signature", lambda user_id: "embed-b")
    third = subjects_mod._subjects_semantic_cache_key("query", ["sub"], "user-1", "system")

    assert first is not None and second is not None and third is not None
    assert first[0] != second[0]
    assert first[0] != third[0]


def test_evidence_cache_comment_sits_before_verifier_boundary():
    source = inspect.getsource(RagServiceImpl.query)

    assert "Evidence-search exact cache is inside QueryEvidenceChain, before verifier." in source
    assert source.index("Evidence-search exact cache") < source.index("self.query_verifier.run")


async def test_normalizer_reuses_single_exact_name_or_alias_match(monkeypatch):
    existing = _candidate("key-1", "Grisha Yeager", "exact")
    monkeypatch.setattr(recall, "find_exact_term_matches", lambda terms, user_id, limit=3: [existing])

    index, errors = await RecallNormalizerChain().run(
        {
            "recall_keys": [{"ref": "k1", "name": "Grisha", "kind": "entity", "aliases": ["Grisha Yeager"]}],
            "recall_links": [{"recall_key_ref": "k1", "source_chunk_id": "chunk-1", "relation": "about"}],
        },
        [_source_chunk("chunk-1", "Grisha inherited the Attack Titan.")],
        "user-1",
        [],
    )

    assert errors == []
    assert index["recall_keys"][0]["id"] == "key-1"
    assert index["recall_links"][0]["recall_key_id"] == "key-1"


async def test_normalizer_reused_candidate_preserves_identity_and_merges_aliases():
    existing = {
        **_candidate("key-1", "Eren Yeager", "exact"),
        "kind": "entity",
        "kind_label": "character",
        "aliases": ["Eren"],
        "summary": "Broad protagonist summary",
        "metadata": {"old": True},
    }

    index, errors = await RecallNormalizerChain().run(
        {
            "recall_keys": [{
                "ref": "k1",
                "existing_recall_key_id": "key-1",
                "name": "Eren Rumbling Arc",
                "kind": "topic",
                "kind_label": "main character",
                "aliases": ["Attack Titan holder"],
                "summary": "Broad protagonist summary updated with later evidence",
                "metadata": {"new": True},
            }],
            "recall_links": [{"recall_key_ref": "k1", "source_chunk_id": "chunk-1", "relation": "about"}],
        },
        [_source_chunk("chunk-1", "Eren activates the Rumbling.")],
        "user-1",
        [existing],
    )

    key = index["recall_keys"][0]
    assert errors == []
    assert key["id"] == "key-1"
    assert key["name"] == "Eren Yeager"
    assert key["kind"] == "entity"
    assert key["kind_label"] == "main character"
    assert key["aliases"] == ["Eren", "Attack Titan holder"]
    assert key["summary"] == "Broad protagonist summary updated with later evidence"
    assert key["metadata"] == {"old": True, "new": True}


async def test_normalizer_does_not_auto_merge_ambiguous_exact_match(monkeypatch):
    monkeypatch.setattr(recall, "find_exact_term_matches", lambda terms, user_id, limit=5: [
        _candidate("key-1", "Alex Smith", "exact"),
        _candidate("key-2", "Alex Doe", "exact"),
    ])

    index, errors = await RecallNormalizerChain().run(
        {
            "recall_keys": [{"ref": "k1", "name": "Alex", "kind": "entity", "aliases": []}],
            "recall_links": [{"recall_key_ref": "k1", "source_chunk_id": "chunk-1", "relation": "mentions"}],
        },
        [_source_chunk("chunk-1", "Alex joined the project.")],
        "user-1",
        [],
    )

    assert "new recall key exact match is ambiguous" in errors
    assert index["recall_keys"][0]["id"] not in {"key-1", "key-2"}


def test_recall_repository_terms_fts_and_duplicate_links(monkeypatch):
    conn = _memory_db()
    monkeypatch.setattr(recall, "get_connection", lambda: conn)
    conn.execute("INSERT INTO raw_inputs (id, job_id, content, user_id) VALUES ('raw-1', 'job-1', 'text', 'user-1')")
    conn.execute(
        "INSERT INTO source_chunks (id, raw_input_id, text, summary, spans, metadata, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("chunk-1", "raw-1", "Grisha text", "summary", "[]", "{}", "user-1"),
    )

    index = {
        "recall_keys": [{
            "id": "key-1",
            "name": "Grisha Yeager",
            "kind": "entity",
            "kind_label": "person",
            "aliases": ["Grisha"],
            "summary": "Attack Titan inheritor",
            "metadata": {},
        }],
        "recall_links": [{
            "id": "link-1",
            "recall_key_id": "key-1",
            "source_chunk_id": "chunk-1",
            "relation": "about",
            "relation_label": "",
            "confidence": 1,
            "reason": "mentioned",
            "metadata": {},
        }],
        "analysis": {},
    }

    assert recall.save_index(index, "user-1") == 1
    index["recall_links"][0]["id"] = "link-2"
    assert recall.save_index(index, "user-1") == 0
    assert recall.find_exact_term_matches(["grisha"], "user-1")[0]["id"] == "key-1"
    assert recall.find_fts_matches(["Attack Titan"], "user-1")[0]["id"] == "key-1"
    assert recall.linked_source_chunk_ids(["key-1"], "user-1") == ["chunk-1"]
    link = recall.get_view()["data"][0]["links"][0]
    assert link["raw_input_id"] == "raw-1"
    assert link["source_chunk_text"] == "Grisha text"
    assert link["source_chunk_spans"] == []


def test_source_chunk_lexical_search_handles_punctuation(monkeypatch):
    conn = _memory_db()
    monkeypatch.setattr(source_chunks, "get_connection", lambda: conn)
    conn.execute("INSERT INTO raw_inputs (id, job_id, content, user_id) VALUES ('raw-1', 'job-1', 'text', 'user-1')")
    conn.execute(
        "INSERT INTO source_chunks (id, raw_input_id, text, summary, spans, metadata, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("chunk-1", "raw-1", "Grisha inherited the Attack Titan.", "summary", "[]", "{}", "user-1"),
    )

    rows = source_chunks.search("Grisha's Titan?", "user-1", limit=5)

    assert [row["id"] for row in rows] == ["chunk-1"]


def test_source_chunk_lexical_search_filters_directories_and_tag_ids(monkeypatch):
    conn = _memory_db()
    monkeypatch.setattr(source_chunks, "get_connection", lambda: conn)
    conn.execute("INSERT INTO notes (id, text, user_id, directory_id) VALUES ('note-1', 'text', 'user-1', NULL)")
    conn.execute("INSERT INTO notes (id, text, user_id, directory_id) VALUES ('note-2', 'text', 'user-1', NULL)")
    conn.execute("INSERT INTO tags (id, name, user_id) VALUES ('tag-1', 'Tag One', 'user-1')")
    conn.execute("INSERT INTO tags (id, name, user_id) VALUES ('tag-2', 'Tag Two', 'user-1')")
    conn.execute("INSERT INTO note_tags (note_id, tag_id) VALUES ('note-1', 'tag-1')")
    conn.execute("INSERT INTO note_tags (note_id, tag_id) VALUES ('note-2', 'tag-2')")
    conn.execute("INSERT INTO raw_inputs (id, job_id, content, user_id) VALUES ('raw-1', 'note-1', 'text', 'user-1')")
    conn.execute("INSERT INTO raw_inputs (id, job_id, content, user_id) VALUES ('raw-2', 'note-2', 'text', 'user-1')")
    conn.execute(
        "INSERT INTO source_chunks (id, raw_input_id, text, summary, spans, metadata, user_id, directory_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("chunk-1", "raw-1", "needle text", "summary", "[]", "{}", "user-1", "/parent/child/")
    )
    conn.execute(
        "INSERT INTO source_chunks (id, raw_input_id, text, summary, spans, metadata, user_id, directory_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("chunk-2", "raw-2", "needle text", "summary", "[]", "{}", "user-1", "/other/")
    )

    rows = source_chunks.search("needle", "user-1", within_directories=["/parent/"], within_tags=["tag-1"], excluding_tags=["tag-2"])

    assert [row["id"] for row in rows] == ["chunk-1"]


def test_retrieval_index_version_bumps_for_source_and_recall_changes(monkeypatch):
    conn = _patch_memory_db(monkeypatch)
    monkeypatch.setattr(retrieval_index, "get_connection", lambda: conn)
    conn.execute("INSERT INTO raw_inputs (id, job_id, content, user_id) VALUES ('raw-1', 'note-1', 'text', 'user-1')")

    assert retrieval_index.get_version("user-1") == 0
    source_chunks.save_many([_source_chunk("chunk-1", "Grisha text")])
    assert retrieval_index.get_version("user-1") == 1
    assert source_chunks.update_directory_path("raw-1", "/dir/") is True
    assert retrieval_index.get_version("user-1") == 2

    recall.save_index({
        "recall_keys": [{"id": "key-1", "name": "Grisha", "kind": "entity", "kind_label": None, "aliases": [], "summary": "", "metadata": {}}],
        "recall_links": [{"id": "link-1", "recall_key_id": "key-1", "source_chunk_id": "chunk-1", "relation": "about", "relation_label": "", "confidence": 1, "reason": "", "metadata": {}}],
        "analysis": {},
    }, "user-1")

    assert retrieval_index.get_version("user-1") == 3


def test_retrieval_index_version_bumps_for_filters_and_lifecycle(monkeypatch):
    conn = _memory_db()
    for module in (notes, tags, raw_inputs, retrieval_index):
        monkeypatch.setattr(module, "get_connection", lambda conn=conn: conn)

    note_id = notes.create("text", "user-1")
    tag_id = tags.create("Important", "user-1")
    version = retrieval_index.get_version("user-1")

    tags.add_to_note(note_id, tag_id)
    notes.update(note_id, "text", "user-1", directory_id=None)
    notes.delete(note_id, "user-1")
    notes.restore(note_id, "user-1")
    raw_id = raw_inputs.save("note-1", "text", "user-1")
    raw_inputs.soft_delete(raw_id)
    raw_inputs.restore(raw_id)

    assert retrieval_index.get_version("user-1") == version + 6


def test_recall_repository_reused_key_preserves_name_and_updates_summary(monkeypatch):
    conn = _memory_db()
    monkeypatch.setattr(recall, "get_connection", lambda: conn)
    conn.execute("INSERT INTO raw_inputs (id, job_id, content, user_id) VALUES ('raw-1', 'job-1', 'text', 'user-1')")
    conn.execute(
        "INSERT INTO source_chunks (id, raw_input_id, text, summary, spans, metadata, user_id) VALUES ('chunk-1', 'raw-1', 'Eren text', 'summary', '[]', '{}', 'user-1')"
    )

    recall.save_index({
        "recall_keys": [{"id": "key-1", "name": "Eren Yeager", "kind": "entity", "kind_label": "character", "aliases": ["Eren"], "summary": "Broad protagonist summary", "metadata": {"old": True}}],
        "recall_links": [],
        "analysis": {},
    }, "user-1")
    recall.save_index({
        "recall_keys": [{"id": "key-1", "name": "Eren Rumbling Arc", "kind": "topic", "kind_label": "main character", "aliases": ["Attack Titan holder"], "summary": "Broad protagonist summary updated with later evidence", "metadata": {"old": True, "new": True}, "user_id": "user-1"}],
        "recall_links": [{"id": "link-1", "recall_key_id": "key-1", "source_chunk_id": "chunk-1", "relation": "about", "relation_label": "", "confidence": 1, "reason": "test", "metadata": {}}],
        "analysis": {},
    }, "user-1")

    key = recall.find_keys_by_ids(["key-1"], "user-1")[0]
    assert key["name"] == "Eren Yeager"
    assert key["kind"] == "entity"
    assert key["kind_label"] == "main character"
    assert key["summary"] == "Broad protagonist summary updated with later evidence"
    assert key["metadata"] == {"old": True, "new": True}


def test_recall_repository_reused_key_keeps_summary_when_new_summary_empty(monkeypatch):
    conn = _memory_db()
    monkeypatch.setattr(recall, "get_connection", lambda: conn)

    recall.save_index({
        "recall_keys": [{"id": "key-1", "name": "Eren Yeager", "kind": "other", "kind_label": None, "aliases": [], "summary": "Existing broad summary", "metadata": {}}],
        "recall_links": [],
        "analysis": {},
    }, "user-1")
    recall.save_index({
        "recall_keys": [{"id": "key-1", "name": "Eren", "kind": "entity", "kind_label": None, "aliases": [], "summary": "", "metadata": {}, "user_id": "user-1"}],
        "recall_links": [],
        "analysis": {},
    }, "user-1")

    key = recall.find_keys_by_ids(["key-1"], "user-1")[0]
    assert key["name"] == "Eren Yeager"
    assert key["kind"] == "entity"
    assert key["summary"] == "Existing broad summary"


def test_dev_wipe_clears_durability_sqlite_lookup_and_vectors(monkeypatch):
    conn = _patch_memory_db(monkeypatch)
    monkeypatch.setattr(dev, "get_connection", lambda: conn)
    monkeypatch.setattr(source_chunk_vectors, "reset", lambda user_id: conn.execute("CREATE TABLE IF NOT EXISTS vector_reset_called (ok INTEGER)"))
    conn.execute("INSERT INTO raw_inputs (id, job_id, content, user_id) VALUES ('raw-1', 'job-1', 'text', 'user-1')")
    conn.execute("INSERT INTO ingest_jobs (id, content_hash, raw_input_id, status, stage) VALUES ('job-1', 'hash-1', 'raw-1', 'queued', 'raw_input')")
    conn.execute("INSERT INTO ingest_checkpoints (job_id, stage, unit_key, status) VALUES ('job-1', 'raw_input', 'raw_input:raw-1', 'complete')")
    conn.execute("INSERT INTO source_chunks (id, raw_input_id, text, summary, spans, metadata, user_id) VALUES ('chunk-1', 'raw-1', 'Grisha text', 'summary', '[]', '{}', 'user-1')")
    recall.save_index({
        "recall_keys": [{"id": "key-1", "name": "Grisha", "kind": "entity", "kind_label": None, "aliases": ["Grisha Yeager"], "summary": "", "metadata": {}}],
        "recall_links": [{"id": "link-1", "recall_key_id": "key-1", "source_chunk_id": "chunk-1", "relation": "about", "relation_label": "", "confidence": 1, "reason": "", "metadata": {}}],
        "analysis": {},
    }, "user-1")

    dev.wipe_all()

    assert retrieval_index.get_version("user-1") == 2
    for table in ("ingest_checkpoints", "ingest_jobs", "recall_links", "recall_key_terms", "recall_keys_fts", "recall_keys", "source_chunks", "raw_inputs"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    assert conn.execute("SELECT name FROM sqlite_master WHERE name = 'vector_reset_called'").fetchone()


async def test_durable_submit_reuses_same_text_job(monkeypatch):
    _patch_memory_db(monkeypatch)

    durable = DurableIngest(NoopPreprocess(), FakeWindows(), FakeDrafts(), SourceChunkAssemblerChain(), FakeRecallIndex())

    async def _noop_schedule(job_id): pass
    durable.scheduler.schedule = _noop_schedule  # type: ignore[method-assign]

    first = await durable.submit("same text", "user-1", "job-1")
    second = await durable.submit("same text", "user-1", "job-2")

    assert first["id"] == "job-1"
    assert second["id"] == "job-1"
    assert len(durability_repo.list_jobs()["data"]) == 1



async def test_durable_submit_requeues_aborted_same_text_job(monkeypatch):
    _patch_memory_db(monkeypatch)

    content_hash = hashlib.sha256("user-1\0same text".encode("utf-8")).hexdigest()
    raw_id = raw_inputs.save_or_reuse("job-1", "same text", "user-1", content_hash)
    durability_repo.create_or_reuse_job("job-1", content_hash, raw_id)
    durability_repo.abort("job-1", "raw input missing")

    durable = DurableIngest(NoopPreprocess(), FakeWindows(), FakeDrafts(), SourceChunkAssemblerChain(), FakeRecallIndex())

    async def _noop_schedule(job_id): pass
    durable.scheduler.schedule = _noop_schedule  # type: ignore[method-assign]
    job = await durable.submit("same text", "user-1", "job-2")

    assert job["id"] == "job-1"
    assert job["status"] == STATUS_QUEUED
    assert job["error"] is None


async def test_durable_runner_aborts_job_missing_raw_input(monkeypatch):
    conn = _patch_memory_db(monkeypatch)
    conn.execute(
        "INSERT INTO ingest_jobs (id, content_hash, raw_input_id, status, stage) VALUES ('job-1', 'hash-1', NULL, 'queued', 'raw_input')"
    )
    durability_repo.complete_checkpoint("job-1", STAGE_SOURCE_CHUNKS, "source_piece:done", "chunk-1")
    runner = DurableIngestRunner(FakeWindows(), FakeDrafts(), SourceChunkAssemblerChain(), FakeRecallIndex())

    await runner.run_once("job-1")

    job = durability_repo.get("job-1")
    assert job["status"] == STATUS_ABORTED
    assert job["stage"] == STATUS_ABORTED
    assert "raw input missing" in job["error"]
    assert conn.execute("SELECT COUNT(*) FROM ingest_checkpoints WHERE job_id = 'job-1'").fetchone()[0] == 0


async def test_durable_source_chunks_resume_from_next_unfinished_piece(monkeypatch):
    _patch_memory_db(monkeypatch)
    monkeypatch.setattr(recall_key_vectors, "exists", lambda key_id, user_id: True)
    monkeypatch.setattr(source_chunk_vectors, "exists", lambda chunk_id, user_id: True)

    raw_id = raw_inputs.save_or_reuse("job-1", "one two", "user-1", "hash-1")
    job = durability_repo.create_or_reuse_job("job-1", "hash-1", raw_id)
    drafts = FakeDrafts(fail_on="two")
    runner = DurableIngestRunner(FakeWindows(), drafts, SourceChunkAssemblerChain(), FakeRecallIndex())

    with pytest.raises(RuntimeError):
        await runner.run_once(job["id"])
    assert durability_repo.get(job["id"])["status"] == STATUS_WAITING_RETRY
    assert drafts.calls == ["one", "two"]

    drafts.fail_on = None
    await runner.run_once(job["id"])

    assert drafts.calls == ["one", "two", "two"]
    completed = durability_repo.get(job["id"])
    assert completed["status"] == "complete"
    assert completed["metadata"] == {
        "raw_input_id": raw_id,
        "input_chars": 7,
        "directory_path": "",
        "source_window_count": 2,
        "source_chunk_count": 2,
        "recall_chunk_count": 2,
        "recall_key_count": 2,
        "recall_link_count": 2,
        "recall_vector_count": 2,
        "source_vector_count": 2,
        "source_chunks": 2,
        "recall_keys": 2,
    }
    assert len(source_chunks.get_by_raw_input_id(raw_id)) == 2


async def test_durable_runner_batches_vector_embeddings(monkeypatch):
    conn = _patch_memory_db(monkeypatch)
    calls = {"recall": [], "source": []}
    monkeypatch.setattr("src.services.rag.private.durability.runner.get_user_settings", lambda user_id: type("Settings", (), {"embedding_batch_size": 100})())
    monkeypatch.setattr(recall_key_vectors, "exists", lambda key_id, user_id: False)
    monkeypatch.setattr(source_chunk_vectors, "exists", lambda chunk_id, user_id: False)
    monkeypatch.setattr(recall_key_vectors, "index", lambda keys: calls["recall"].append(len(keys)))
    monkeypatch.setattr(source_chunk_vectors, "index", lambda chunks: calls["source"].append(len(chunks)))

    raw_id = raw_inputs.save_or_reuse("job-1", "one two", "user-1", "hash-1")
    job = durability_repo.create_or_reuse_job("job-1", "hash-1", raw_id)
    runner = DurableIngestRunner(FakeWindows(), FakeDrafts(), SourceChunkAssemblerChain(), FakeRecallIndex())

    await runner.run_once(job["id"])

    assert calls == {"recall": [2], "source": [2]}
    assert conn.execute("SELECT COUNT(*) FROM ingest_checkpoints WHERE stage = 'recall_vectors' AND status = 'complete'").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM ingest_checkpoints WHERE stage = 'source_vectors' AND status = 'complete'").fetchone()[0] == 2


async def test_durable_runner_pause_stops_after_current_unit(monkeypatch):
    _patch_memory_db(monkeypatch)

    raw_id = raw_inputs.save_or_reuse("job-1", "one two", "user-1", "hash-1")
    job = durability_repo.create_or_reuse_job("job-1", "hash-1", raw_id)

    class PausingDrafts(FakeDrafts):
        async def run(self, window: dict, user_id: str) -> list[dict]:
            result = await super().run(window, user_id)
            if window["text"] == "one":
                durability_repo.pause(job["id"])
            return result

    drafts = PausingDrafts()
    runner = DurableIngestRunner(FakeWindows(), drafts, SourceChunkAssemblerChain(), FakeRecallIndex())

    await runner.run_once(job["id"])

    assert durability_repo.get(job["id"])["status"] == "paused"
    assert drafts.calls == ["one"]
    assert len(source_chunks.get_by_raw_input_id(raw_id)) == 1


def test_durable_retry_cap_marks_job_failed(monkeypatch):
    _patch_memory_db(monkeypatch)
    raw_id = raw_inputs.save_or_reuse("job-1", "text", "user-1", "hash-1")
    durability_repo.create_or_reuse_job("job-1", "hash-1", raw_id)

    for _ in range(5):
        job = durability_repo.schedule_retry("job-1", STAGE_SOURCE_CHUNKS, "source_piece:1", "model down")

    assert job["status"] == STATUS_FAILED
    assert job["attempt_count"] == 5


def test_durable_retry_uses_configured_backoff(monkeypatch):
    _patch_memory_db(monkeypatch)
    raw_id = raw_inputs.save_or_reuse("job-1", "text", "user-1", "hash-1")
    durability_repo.create_or_reuse_job("job-1", "hash-1", raw_id)

    before = datetime.now(timezone.utc)
    job = durability_repo.schedule_retry("job-1", STAGE_SOURCE_CHUNKS, "source_piece:1", "model down", [1])
    delay = (datetime.fromisoformat(job["next_run_at"]) - before).total_seconds()

    assert job["status"] == STATUS_WAITING_RETRY
    assert 0 <= delay <= 2


def test_manual_resume_keeps_completed_checkpoints(monkeypatch):
    _patch_memory_db(monkeypatch)
    raw_id = raw_inputs.save_or_reuse("job-1", "text", "user-1", "hash-1")
    durability_repo.create_or_reuse_job("job-1", "hash-1", raw_id)
    durability_repo.complete_checkpoint("job-1", STAGE_SOURCE_CHUNKS, "source_piece:done", "chunk-1")
    durability_repo.schedule_retry("job-1", STAGE_SOURCE_CHUNKS, "source_piece:todo", "bad")

    durability_repo.resume("job-1")

    assert durability_repo.get("job-1")["status"] == STATUS_QUEUED
    assert durability_repo.checkpoint_complete("job-1", STAGE_SOURCE_CHUNKS, "source_piece:done") is True


# ── helpers ──────────────────────────────────────────────────────────────────


def _source_chunk(chunk_id: str, text: str) -> dict:
    return {
        "id": chunk_id,
        "raw_input_id": "raw-1",
        "text": text,
        "summary": "test chunk summary",
        "user_id": "user-1",
        "spans": [{"start": 0, "end": len(text)}],
        "source_time": None,
        "metadata": {"salient_entities": ["Test Entity"]},
    }


def _candidate(key_id: str, name: str, source: str) -> dict:
    return {
        "id": key_id,
        "name": name,
        "kind": "entity",
        "kind_label": None,
        "aliases": [],
        "user_id": "user-1",
        "summary": "",
        "metadata": {},
        "created_at": None,
        "updated_at": None,
        "match_source": source,
        "match_notes": [source],
    }


def _search_state(**overrides) -> dict:
    state = {
        "query": "Attack Titan",
        "sub_queries": ["Attack Titan"],
        "extracted_subjects": ["Grisha"],
        "user_id": "user-1",
        "reporter": None,
        "within_directories": [],
        "excluding_directories": [],
        "within_tags": [],
        "excluding_tags": [],
        "within_tags_condition": "any",
        "chunks": [],
        "trace_parts": [],
    }
    state.update(overrides)
    return state


async def _raise_async(*args, **kwargs):
    raise RuntimeError("redis disabled")


async def _async_value(value):
    return value


def _memory_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(Path(__file__).resolve().parents[3].joinpath("resources/schema.sql").read_text())
    conn.execute("INSERT INTO users (id, identifier, password_hash) VALUES ('user-1', 'test_user', 'hash')")
    return conn


def _patch_memory_db(monkeypatch):
    conn = _memory_db()
    for module in (raw_inputs, source_chunks, recall, retrieval_index, durability_repo, config_presets):
        monkeypatch.setattr(module, "get_connection", lambda conn=conn: conn)
    config_presets.save({"name": "test"}, "user-1")
    return conn


class NoopPreprocess:
    def run(self, text: str) -> str:
        return text.strip()


class FakeWindows:
    def run(self, raw_text: str, user_id: str | None = None) -> list[dict]:
        return [{"text": "one", "start": 0, "end": 3}, {"text": "two", "start": 4, "end": 7}]


class FakeDrafts:
    def __init__(self, fail_on: str | None = None) -> None:
        self.fail_on = fail_on
        self.calls = []

    async def run(self, window: dict, user_id: str) -> list[dict]:
        self.calls.append(window["text"])
        if window["text"] == self.fail_on:
            raise RuntimeError("draft failed")
        return [{"window": window, "summary": window["text"], "source_time": None, "metadata": {"salient_entities": ["Test Entity"]}}]


class FakeRecallIndex:
    async def run(self, raw_text: str, user_id: str, chunks: list[dict], on_progress=None) -> dict:
        chunk = chunks[0]
        key_id = f"key-{chunk['id']}"
        return {
            "recall_keys": [{"id": key_id, "name": f"Thing {chunk['id']}", "kind": "entity", "kind_label": None, "aliases": [], "summary": "", "metadata": {}, "user_id": user_id}],
            "recall_links": [{
                "id": f"link-{chunk['id']}",
                "recall_key_id": key_id,
                "source_chunk_id": chunk["id"],
                "relation": "about",
                "relation_label": "",
                "confidence": 1,
                "reason": "test",
                "metadata": {},
            }],
            "analysis": {},
        }


async def test_listener_note_moved_updates_directory_path(monkeypatch):
    from src.services.rag.private.listener.listener import _handle_note_moved
    from src.repositories import directories
    
    conn = _patch_memory_db(monkeypatch)
    monkeypatch.setattr(directories, "get_connection", lambda: conn)
    
    conn.execute("INSERT INTO raw_inputs (id, job_id, content, user_id) VALUES ('raw-1', 'note-1', 'text', 'user-1')")
    conn.execute("INSERT INTO source_chunks (id, raw_input_id, text, summary, spans, metadata, user_id, directory_path) VALUES ('chunk-1', 'raw-1', 'text', 'summary', '[]', '{}', 'user-1', '/old/')")
    conn.execute("INSERT INTO directories (id, name, parent_id, path, user_id) VALUES ('dir-2', 'NewDir', NULL, '/dir-2/', 'user-1')")
    
    calls = []
    monkeypatch.setattr(source_chunk_vectors, "update_metadata", lambda chunk_ids, updates, user_id: calls.append((chunk_ids, updates, user_id)))

    await _handle_note_moved({
        "note_id": "note-1",
        "new_directory_id": "dir-2",
        "user_id": "user-1"
    })

    # Check SQLite
    row = conn.execute("SELECT directory_path FROM source_chunks WHERE id = 'chunk-1'").fetchone()
    assert row["directory_path"] == "/dir-2/"
    
    # Check Chroma calls
    assert calls == [(["chunk-1"], {"directory_path": "/dir-2/"}, "user-1")]
