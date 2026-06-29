# SEAI Retrieval Flow

Retrieval runs as an **Agentic AI** (`QueryAgentChain`) driven by a LangGraph ReAct tool-calling loop. This allows the system to answer both structural questions (about notes and directories) and semantic questions (RAG).

```txt
query
→ Agentic Tool Loop: LLM decides which tools to call
    ├─ list_directories (lists folder structure)
    ├─ list_notes_in_directory (lists notes metadata)
    ├─ read_note (fetches raw text of a specific note)
    └─ search_knowledge_base (runs the RAG Semantic Pipeline)
        → breakdown: LLM decomposes query into ≤4 focused sub-queries
        → search (per sub-query):
            → source chunk vector search
            → source chunk lexical search
            → recall key search
            → linked source chunk expansion
        → merge + dedup all sub-query evidence
        → re-rank merged chunks against original query
        → context-pack focused snippets
→ Agent gathers evidence from tools
→ Agent calls submit_final_answer to terminate the loop and output structured JSON
```

The semantic search (`QueryEvidenceChain`) is now a tool available to the agent. Its breakdown step is a no-op pass-through for simple queries, only fanning out when the LLM detects a multi-hop or compound question.

Context engineering: instead of sending whole chunk text to the answer model, each chunk is reduced to its summary plus the most query-relevant passages (≤3 snippets × ≤420 chars each). This keeps token usage low and protects local model context windows.

## Rules

- The `QueryAgentChain` uses a ReAct loop but forces a clean exit via a `StopAgentException` inside the `submit_final_answer` tool. This preserves structured output without serialization loss.
- Source chunks are the only citable evidence for semantic facts.
- Recall keys and recall links are navigation hints, not factual authority.
- The semantic search pipeline caps evidence before returning it to the agent (`MAX_EVIDENCE_CHUNKS = 12` after merge).
- The API returns full source chunks, directory metadata, and note metadata so the UI can render rich citations and links.
- If semantic search generation fails or yields nothing, the agent can fall back to directly reading a note if it knows the ID.

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
    "mode": "agentic",
    "query": "...",
    "tool_traces": [
      {
        "mode": "source_chunks_with_recall_expansion",
        "sub_queries": ["original", "sub-query 1"],
        "sub_query_count": 2,
        "sub_query_traces": [{"sub_query": "...", "recall_key_count": 0}],
        "ranked_source_chunk_ids": [],
        "context_chars_saved": 0
      }
    ]
  }
}
```

`citations` point to raw input ids and source chunk spans so the UI can open the original source text. `directories` and `notes` point to organizational UUIDs.

## Current Limits

This agent currently uses simple zero-shot tool usage. It is not a graph traversal engine, or temporal ordering engine.

The next temporal step should be:

```txt
detect timeline-style query
→ sort selected evidence by event_time, time_label, source span, and source order
→ pass timeline_order into the answer prompt
```

## Future Improvements (Cross-Domain "Smart" Queries)

Currently, the structural tools (`list_directories`, `list_notes_in_directory`) and the semantic tool (`search_knowledge_base`) are isolated. The agent cannot answer questions like *"In which folders are my love letters?"* because it requires intersecting semantic search with structural metadata.

To support these "smart" cross-domain questions in the future:
1. **Metadata-Aware Vectors:** Inject `directory_id` and tags into ChromaDB vectors during ingestion. This will allow the agent to issue metadata-filtered semantic searches (e.g., `where={"directory_id": "uuid"}`).
2. **Contextual Chunks:** Ensure that `search_knowledge_base` returns the parent `note_id` and `directory_id` alongside the chunk text so the agent can trace text back to its location.
3. **Text-to-SQL Tool:** Provide a read-only SQL tool so the agent can execute complex aggregations (e.g., *"Count notes by directory where..."*) directly against the SQLite database.
