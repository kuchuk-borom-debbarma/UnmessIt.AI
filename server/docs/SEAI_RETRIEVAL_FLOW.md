# SEAI Retrieval Flow

Retrieval runs as a small LangGraph state graph (`QueryEvidenceChain`):

```txt
query
→ breakdown: LLM decomposes query into ≤4 focused sub-queries
→ search (per sub-query):
    → source chunk vector search
    → source chunk lexical search
    → recall key search
    → linked source chunk expansion
→ merge + dedup all sub-query evidence
→ re-rank merged chunks against original query
→ context-pack focused snippets (budget per pass, then global cap)
→ one JSON answer prompt over focused snippets
```

The breakdown step is a no-op pass-through for simple queries (returns `[original_query]`).
It only fans out to multiple sub-queries when the LLM detects a multi-hop or compound question.
If the breakdown LLM call fails, retrieval falls back silently to a single pass with the original query.

Context engineering: instead of sending whole chunk text to the answer model, each chunk
is reduced to its summary plus the most query-relevant passages (≤3 snippets × ≤420 chars each).
This keeps token usage low and protects local model context windows across multi-sub-query passes.

## Rules

- Source chunks are the only citable evidence.
- Recall keys and recall links are navigation hints, not factual authority.
- Retrieval caps evidence before prompting the LLM (`MAX_EVIDENCE_CHUNKS = 12` after merge).
- The answer prompt gets source chunk summaries plus focused snippets, not whole chunk text.
- The API still returns full source chunks so the UI can inspect the evidence.
- If vector search fails, lexical source chunk search can still return evidence.
- If answer generation fails, the API still returns found source chunks.
- Recall `event_time` and `time_label` are hints. Retrieval must not treat them as stronger than source text.

## Response Shape

`POST /api/retrieval/query` returns:

```json
{
  "answer": "string",
  "citations": [],
  "source_chunks": [],
  "retrieval_trace": {
    "sub_queries": ["original", "sub-query 1"],
    "sub_query_count": 2,
    "sub_query_traces": [{"sub_query": "...", "recall_key_count": 0}],
    "ranked_source_chunk_ids": [],
    "selected_snippet_counts": {},
    "context_chars_before_packing": 0,
    "context_chars_after_packing": 0,
    "context_chars_saved": 0,
    "chunk_score_reasons": {}
  }
}
```

`citations` point to raw input ids and source chunk spans so the UI can open the original source text.

## Current Limits

This is not a planner, reranker, graph traversal engine, or temporal ordering engine.
Add those only if this simple path cannot answer real broad or timeline questions well enough.

The next temporal step should be:

```txt
detect timeline-style query
→ sort selected evidence by event_time, time_label, source span, and source order
→ pass timeline_order into the answer prompt
```

