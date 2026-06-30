# SEAI Retrieval Flow

Retrieval runs as a source-backed semantic pipeline. It selects source chunks, expands through recall links, packs focused snippets, and generates an answer from source chunks only.

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
→ context-pack focused snippets
→ answer from selected source chunks
```

The breakdown step is a no-op pass-through for simple queries, only fanning out when the LLM detects a multi-hop or compound question.

Context engineering: instead of sending whole chunk text to the answer model, each chunk is reduced to its summary plus the most query-relevant passages (≤3 snippets × ≤420 chars each). This keeps token usage low and protects local model context windows.

## Rules

- Source chunks are the only citable evidence for semantic facts.
- Recall keys and recall links are navigation hints, not factual authority.
- The semantic search pipeline caps evidence before returning it to the agent (`MAX_EVIDENCE_CHUNKS = 12` after merge).
- The API returns full source chunks, directory metadata, and note metadata fields so the UI can render rich citations and links.
- If search finds no source chunks, the answer is an explicit "no relevant source chunks" response. The current retrieval path does not run a tool-calling note-browsing agent.

## Response Shape

`POST /api/retrieval/query` returns:

```json
{
  "answer": "string",
  "citations": [],
  "directories": [],
  "notes": [],
  "source_chunks": [],
  "retrieval_trace": {
    "mode": "source_chunks_with_recall_expansion",
    "query": "...",
    "sub_queries": ["original", "sub-query 1"],
    "sub_query_count": 2,
    "sub_query_traces": [{"sub_query": "...", "recall_key_count": 0}],
    "ranked_source_chunk_ids": [],
    "context_chars_saved": 0
  }
}
```

`citations` point to raw input ids and source chunk spans so the UI can open the original source text. `directories` and `notes` point to organizational UUIDs.

## Current Limits

Retrieval is not a graph traversal engine or temporal ordering engine.

The next temporal step should be:

```txt
detect timeline-style query
→ sort selected evidence by event_time, time_label, source span, and source order
→ pass timeline_order into the answer prompt
```

## Cross-Domain Filtering

Semantic retrieval queries can be scoped to specific directories using the `within_directories` and `excluding_directories` parameters. 

To achieve exact hierarchical filtering efficiently:
1. The backend translates the requested root `directory_id`s into a flat list of all descendant paths using SQLite's `list_subtree` (which leverages the Materialized Path).
2. The retrieval query passes these resolved paths into ChromaDB using the `$in` (or `$nin`) operator on the `directory_path` metadata field.
3. This combines structural bounds with semantic similarity without requiring the vector database to understand hierarchical trees natively.

## Future Improvements

1. **Contextual Chunks:** Return the parent `note_id` and `directory_id` alongside chunk text so the answer layer can better trace text back to its location.
2. **Optional SQL/Tool Layer:** Add a read-only SQL/tool layer only if real questions need cross-domain aggregation such as *"Count notes by directory where..."*.
