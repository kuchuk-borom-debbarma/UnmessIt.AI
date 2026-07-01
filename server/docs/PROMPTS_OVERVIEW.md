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
- split compound queries into at most four focused sub-queries

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

### Answer Generation

File: `server/src/services/rag/private/chains/query/__init__.py`

Purpose:

- answer from selected source chunks only
- cite source chunk ids only
- say what is missing when evidence is incomplete

Contract:

```json
{
  "answer": "string",
  "citation_ids": ["source_chunk_id"]
}
```

The backend drops citation ids that are not in the selected source chunks.
