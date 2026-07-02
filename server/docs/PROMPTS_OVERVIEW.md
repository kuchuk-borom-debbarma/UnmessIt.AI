# Prompts Overview

Prompts live near the chains that use them. Keep them domain-neutral, JSON-only, and source-grounded. See `server/docs/rules/prompt_rules.md`.

## Ingestion

### Source Chunk Summary

File: `server/src/services/rag/private/chains/source_chunks/source_chunk_drafts.py`

Purpose:

- summarize one bounded source window
- extract a few salient subjects for retrieval
- preserve the full source text as the citable chunk

Contract:

```json
{
  "summary": "short neutral summary",
  "source_time": null,
  "metadata": {
    "salient_entities": []
  }
}
```

### Recall Keys And Links

File: `server/src/services/rag/private/chains/recall/`

Purpose:

- create reusable recall keys
- link keys to exact source chunks
- reuse existing candidate keys when they clearly match

Contract:

```json
{
  "recall_keys": [
    {
      "ref": "k1",
      "name": "canonical name",
      "kind": "entity|topic|event|task|question|other",
      "kind_label": null,
      "aliases": [],
      "summary": "short hint"
    }
  ],
  "recall_links": [
    {
      "recall_key_ref": "k1",
      "source_chunk_id": "exact id",
      "relation": "mentions|about|updates|contradicts|supports|other",
      "relation_label": null,
      "confidence": 0.8,
      "reason": "short source-grounded reason"
    }
  ]
}
```

Existing candidates are reuse hints only. Source chunks are the evidence.

## Retrieval

### Query Breakdown

File: `server/src/services/rag/private/chains/query/_breakdown.py`

Purpose:

- keep simple queries unchanged
- split compound queries into at most six focused sub-queries
- add generic clause-level searches for broad enumerations
- add deterministic attribute, comparison, and reasoning fan-out when the model returns only the original query

Contract:

```json
{
  "sub_queries": ["original query"]
}
```

### Implicit Subjects

File: `server/src/services/rag/private/chains/query/_subjects.py`

Purpose:

- identify named subjects implied by a description
- improve recall-key lookup for queries that omit names

Contract:

```json
{
  "subjects": ["subject name"]
}
```

The result is capped and can be empty.

### Evidence Verification

File: `server/src/services/rag/private/chains/query/__init__.py`

Purpose:

- judge whether packed evidence matches the original query scope
- keep on-topic chunks and drop off-topic same-word matches
- keep partial on-topic evidence for incomplete multi-part questions
- allow cross-context evidence when the user explicitly asks to compare, connect, or contrast subjects
- request one focused retry when the current evidence is close but missing likely retrievable support
- avoid domain-specific assumptions and expose only a concise reason

Contract:

```json
{
  "status": "sufficient|needs_retry|insufficient",
  "reason": "short reason",
  "on_topic_ids": ["source_chunk_id"],
  "off_topic_ids": ["source_chunk_id"],
  "retry_query": "focused query or empty string"
}
```

The service filters chunks with this result before answer generation. If `needs_retry` includes a focused query, retrieval runs one more packed search and verifies the combined context again.

### Answer Generation

File: `server/src/services/rag/private/chains/query/__init__.py`

Purpose:

- answer from selected source chunks only
- cite source chunk ids only
- synthesize comparisons or similarities when the user asks and the selected chunks contain facts for each side, even if no source explicitly performs the comparison
- preserve exact counts, labels, descriptors, and qualifiers when available
- embed inline `[[cite:source_chunk_id]]` markers when useful for verification
- normalize or remove malformed/invalid inline citation markers before returning the answer
- answer supported parts first and briefly say what is missing when evidence is incomplete

Contract:

```json
{
  "answer": "string with optional [[cite:source_chunk_id]] markers",
  "citation_ids": ["source_chunk_id"]
}
```

The backend drops citation ids that are not in the selected source chunks.
