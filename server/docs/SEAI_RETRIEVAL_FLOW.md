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

This is the retrieval foundation for the temporal-memory goal. It can answer timeline-style questions only when the right chunks are found and the stored evidence already carries useful source order or time hints. A dedicated temporal ordering pass is future work.

## Rules

- Source chunks are the only citable evidence.
- Recall keys and recall links are navigation hints, not factual authority.
- Retrieval caps evidence before prompting the LLM.
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

This is not a planner, reranker, graph traversal engine, multi-step agent, or temporal ordering engine. Add those only if this simple path cannot answer real broad or timeline questions well enough.

The next temporal step should be:

```txt
detect timeline-style query
-> sort selected evidence by event_time, time_label, source span, and source order
-> pass timeline_order into the answer prompt
```
