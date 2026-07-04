# SEAI Retrieval Flow

Retrieval is source-backed. It selects source chunks, expands through recall links, packs focused snippets, and answers from source chunks only.

```txt
query
-> exact full-result cache lookup
-> semantic full-result cache lookup
   -> strict verifier must approve similar cached answers before reuse
-> breakdown into at most 6 focused sub-queries
   -> deterministic fan-out for broad multi-part, attribute, comparison, and reasoning questions
-> per-sub-query search:
   -> source chunk vector search
   -> source chunk lexical search
   -> recall key search
   -> linked source chunk expansion
-> merge and dedupe evidence
-> rerank against original query
-> pack focused snippets
-> verify evidence against the original query scope
   -> filter off-topic chunks
   -> optionally run one focused retry query
-> answer from verified source chunks with optional inline citation markers
```

The breakdown step passes simple queries through unchanged. For broad multi-part, attribute, comparison, or reasoning questions, it combines LLM decomposition with deterministic fan-out so retrieval searches for the facts needed to answer, not only the exact words the user typed. Broad enumerations can add clause-level searches without assuming any domain.

Each chunk is reduced to its summary plus the most query-relevant passages before answer generation. This keeps token use low for local and cloud models.

The full-result semantic cache is a shortcut before retrieval. It is allowed to reuse a prior answer only when the cached query is close enough and a strict verifier says the old answer fully covers the new query. Verifier and answer caches remain exact because their prompts include the requested wording and selected evidence.

Before answer generation, the verifier judges the packed chunk payload against the original query. It keeps chunks that match the requested subject, scope, qualifiers, and sense of ambiguous terms, drops off-topic same-word matches, and can ask retrieval to retry once with a more focused query. Explicit comparison or relationship questions may keep evidence from multiple contexts when those contexts are part of the user request. If selected evidence supports only part of a multi-part query, the verifier keeps that partial evidence instead of discarding it as insufficient.

Attribute, comparison, and reasoning-style queries get deterministic query-term expansion before recall-key lookup, lexical search, reranking, and snippet packing. Attribute questions add neutral detail terms such as labels, counts, features, and measurements, with appearance terms only when the query asks for them. Comparison questions generate per-subject searches plus shared dimension searches for attributes, context, changes, goals, and outcomes. Reasoning/change questions add neutral cause, effect, context, sequence, and outcome terms.

## Rules

- Source chunks are the only citable evidence for semantic facts.
- Recall keys and recall links are navigation hints, not factual authority.
- The answer model may synthesize user-requested comparisons from sourced facts; the source does not need to contain an explicit comparison or a shared context.
- Evidence verification keeps cross-context evidence only when the query asks for cross-context reasoning or when the chunks match the same requested scope.
- Partial on-topic evidence should still reach answer generation; the answer should cover supported parts first and briefly name missing parts.
- Inline answer references use `[[cite:source_chunk_id]]` markers. The UI renders these as source popups and links to the cited note span.
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
    "ranked_source_chunk_ids": [],
    "verification": {
      "status": "sufficient",
      "reason": "...",
      "on_topic_ids": [],
      "off_topic_ids": [],
      "retry_query": ""
    },
    "verified_source_chunk_ids": []
  }
}
```

`citations` point to raw input ids and source chunk spans. `answer` may also contain inline citation markers that reference those source chunk ids. `directories` and `notes` point to organizational UUIDs for UI links.

## Directory Filtering

Semantic retrieval can be scoped with `within_directories` and `excluding_directories`.

The backend resolves requested root directory ids into descendant paths with SQLite materialized paths, then passes those paths into Chroma metadata filters.

## Limits

Retrieval is not a full graph traversal engine or temporal ordering engine. Add timeline ordering only when real questions need ordered evidence from `event_time`, `time_label`, source spans, and source order.

Add a read-only SQL/tool layer only if real questions need aggregation such as counting notes by directory.
