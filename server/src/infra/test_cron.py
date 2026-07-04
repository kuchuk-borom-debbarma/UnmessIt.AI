import time
import pytest
from unittest.mock import patch, MagicMock

from src.infra.embedding_cache import MemoryEmbeddingCache
from src.infra.retrieval_cache import MemoryJsonCache
from src.infra.chroma import semantic_cache_collection, cleanup_stale_semantic_collections, _get_client

def test_memory_embedding_cache_cleanup():
    cache = MemoryEmbeddingCache()
    cache.set("key1", [0.1, 0.2])
    
    with patch("time.time", return_value=time.time() + 3600 + 10):
        # Now key1 should be stale
        cache.set("key2", [0.3, 0.4]) # Fresh key
        count = cache.cleanup_stale(3600)
        assert count == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == [0.3, 0.4]


def test_memory_json_cache_cleanup():
    cache = MemoryJsonCache()
    cache.set("key1", {"data": 1})
    
    with patch("time.time", return_value=time.time() + 3600 + 10):
        cache.set("key2", {"data": 2})
        count = cache.cleanup_stale(3600)
        assert count == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == {"data": 2}


def test_chroma_semantic_cache_cleanup():
    # Setup two collections, one stale, one fresh
    client = _get_client()
    
    # Clean any existing
    for c in client.list_collections():
        if getattr(c, "name", str(c)).startswith("retrieval_cache_"):
            client.delete_collection(getattr(c, "name", str(c)))
            
    # Fresh collection
    semantic_cache_collection("user1", "fresh")
    
    # Stale collection (we can mock time.time when creating it to make it stale)
    with patch("time.time", return_value=time.time() - 86400 - 10):
        semantic_cache_collection("user1", "stale")
        
    cols_before = [getattr(c, "name", str(c)) for c in client.list_collections() if getattr(c, "name", str(c)).startswith("retrieval_cache_")]
    assert len(cols_before) == 2
    
    count = cleanup_stale_semantic_collections(86400)
    assert count == 1
    
    cols_after = [getattr(c, "name", str(c)) for c in client.list_collections() if getattr(c, "name", str(c)).startswith("retrieval_cache_")]
    assert len(cols_after) == 1
