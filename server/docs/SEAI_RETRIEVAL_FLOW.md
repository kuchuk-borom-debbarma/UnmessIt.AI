# SEAI Retrieval Flow

Retrieval is source-backed. It selects source chunks, expands through recall links, packs focused snippets, and answers from source chunks only.

```txt
query
-> breakdown into at most 4 focused sub-queries
-> per-sub-query search:
   -> source chunk vector search
   -> source chunk lexical search
   -> recall key search
   -> linked source chunk expansion
-> merge and dedupe evidence
-> rerank against original query
-> pack focused snippets
-> answer from selected source chunks
```

The breakdown step passes simple queries through unchanged and fans out only for compound questions.

Each chunk is reduced to its summary plus the most query-relevant passages before answer generation. This keeps token use low for local and cloud models.

## Rules

- Source chunks are the only citable evidence for semantic facts.
- Recall keys and recall links are navigation hints, not factual authority.
- Evidence is capped before returning to the answer step.
- If search finds no source chunks, the answer says no relevant source chunks were found.
- The current retrieval path does not run a tool-calling note-browsing agent.

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
    "ranked_source_chunk_ids": []
  }
}
```

`citations` point to raw input ids and source chunk spans. `directories` and `notes` point to organizational UUIDs for UI links.

## Directory Filtering

Semantic retrieval can be scoped with `within_directories` and `excluding_directories`.

The backend resolves requested root directory ids into descendant paths with SQLite materialized paths, then passes those paths into Chroma metadata filters.

## Limits

Retrieval is not a full graph traversal engine or temporal ordering engine. Add timeline ordering only when real questions need ordered evidence from `event_time`, `time_label`, source spans, and source order.

Add a read-only SQL/tool layer only if real questions need aggregation such as counting notes by directory.
