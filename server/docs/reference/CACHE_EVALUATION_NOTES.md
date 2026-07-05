# Cache Evaluation Notes

This document tracks verification steps for evaluating the effectiveness and safety of semantic caches across different RAG pipeline layers.

## Top-Level Semantic Cache
- [ ] Test exact match hits correctly and displays LLM resources saved.
- [ ] Test semantically equivalent questions (e.g., "What did John say about apples?" vs "John's statements on apples") to ensure cache hits.
- [ ] Test identical queries with different constraints (e.g., "today" vs "yesterday", "differences" vs "similarities") to ensure the Verifier REJECTS the cache and runs a full search.
- [ ] Verify the UI updates correctly with "skip" statuses for downstream stages when a top-level semantic hit occurs.

## Sub-Query Semantic Cache
- [ ] Ask a complex query to generate fresh sub-queries and populate the Sub-Query Semantic Cache.
- [ ] Ask a slightly reworded complex query that generates similar sub-queries.
- [ ] Verify that the Sub-Query Semantic Cache hits, the Fast Verifier approves the match, and the heavy Context Compactor is completely skipped for that sub-query.
- [ ] Check logs to ensure the Context Compactor exact match cache hits when two different top-level queries generate the exact same sub-query text.
