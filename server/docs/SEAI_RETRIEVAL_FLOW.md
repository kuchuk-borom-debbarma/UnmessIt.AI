# SEAI Retrieval Flow

Retrieval is deliberately small:

```txt
query
-> source chunk vector search
-> source chunk lexical search
-> recall key search
-> linked source chunk expansion
-> rank source chunks
-> context-pack focused snippets
-> one JSON answer prompt over focused snippets
```

## Rules

- Source chunks are the only citable evidence.
- Recall keys and recall links are navigation hints, not factual authority.
- Retrieval caps evidence before prompting the LLM.
- The answer prompt gets source chunk summaries plus focused snippets, not whole chunk text.
- The API still returns full source chunks so the UI can inspect the evidence.
- If vector search fails, lexical source chunk search can still return evidence.
- If answer generation fails, the API still returns found source chunks.

## Response Shape

`POST /api/retrieval/query` returns:

```json
{
  "answer": "string",
  "citations": [],
  "source_chunks": [],
  "retrieval_trace": {
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

This is not a planner, reranker, graph traversal engine, or multi-step agent. Add those only if this simple path cannot answer real broad questions well enough.
