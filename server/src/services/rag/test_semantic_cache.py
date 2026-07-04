import pytest
from unittest.mock import AsyncMock, patch

from src.services.rag.private.chains.query._semantic_verifier import SemanticCacheVerifierChain
from src.services.rag.private.rag_service_impl import RagServiceImpl

@pytest.fixture
def mock_json_client():
    client = AsyncMock()
    # Default to returning safe
    client.async_invoke_json.return_value = {"is_safe": True, "reason": "Perfect match"}
    return client

@pytest.fixture
def mock_retrieval_cache():
    with patch("src.services.rag.private.rag_service_impl.retrieval_cache") as mock_cache:
        # Default to cache miss
        mock_cache.get_semantic_query_result = AsyncMock(return_value=None)
        mock_cache.set_semantic_query_result = AsyncMock()
        yield mock_cache

@pytest.mark.asyncio
async def test_semantic_verifier_chain_safe(mock_json_client):
    verifier = SemanticCacheVerifierChain(mock_json_client)
    is_safe = await verifier.run("today", "today", "schedule", "user-1")
    assert is_safe is True
    mock_json_client.async_invoke_json.assert_called_once()
    assert "retrieval.semantic_cache_verifier" in mock_json_client.async_invoke_json.call_args.kwargs["stage"]

@pytest.mark.asyncio
async def test_semantic_verifier_chain_unsafe(mock_json_client):
    mock_json_client.async_invoke_json.return_value = {"is_safe": False, "reason": "different time"}
    verifier = SemanticCacheVerifierChain(mock_json_client)
    is_safe = await verifier.run("tomorrow", "today", "schedule", "user-1")
    assert is_safe is False

@pytest.mark.asyncio
async def test_rag_service_semantic_cache_hit(mock_json_client, mock_retrieval_cache):
    # Mock a cache hit
    cached_payload = {"answer": "Cached answer", "citations": [], "retrieval_trace": {}}
    mock_retrieval_cache.get_semantic_query_result.return_value = (cached_payload, "Old query", 0.01)
    
    service = RagServiceImpl(mock_json_client)
    
    # Run the query
    result = await service.query("New query", "user-1")
    
    # Should return the cached payload without running evidence chain
    assert result == cached_payload
    mock_retrieval_cache.get_semantic_query_result.assert_called_once()
    mock_json_client.async_invoke_json.assert_called_once() # The verifier

@pytest.mark.asyncio
async def test_rag_service_semantic_cache_hit_but_unsafe(mock_json_client, mock_retrieval_cache):
    # Mock a cache hit
    cached_payload = {"answer": "Cached answer", "citations": [], "retrieval_trace": {}}
    mock_retrieval_cache.get_semantic_query_result.return_value = (cached_payload, "Old query", 0.01)
    
    # Mock verifier to reject it
    mock_json_client.async_invoke_json.return_value = {"is_safe": False, "reason": "Different"}
    
    service = RagServiceImpl(mock_json_client)
    
    # We must mock the evidence/verifier/answer chains since they will now be called
    service.query_evidence.run = AsyncMock(return_value=([], {"cache_events": []}))
    service.query_verifier.run = AsyncMock(return_value={"status": "sufficient", "on_topic_ids": []})
    service.query_answer.run = AsyncMock(return_value={"answer": "New answer", "citations": []})
    
    # Run the query
    result = await service.query("New query", "user-1")
    
    # Should NOT return the cached payload
    assert result["answer"] == "New answer"
    mock_retrieval_cache.get_semantic_query_result.assert_called_once()
    mock_retrieval_cache.set_semantic_query_result.assert_called_once() # Should cache the NEW result
