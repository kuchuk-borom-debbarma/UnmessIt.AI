# SEAI Indexing Flow

SEAI now means **Source Evidence And Indexing** for this codebase. The active memory ingestion flow is deliberately small:

```txt
raw input
-> source windows
-> source chunks
-> recall keys and recall links
-> vector index
```

Raw input remains the source of truth. Source chunks, recall keys, and recall links are indexes over that source. They help retrieval find and organize evidence; they do not replace the original text.

## Objects

**Raw input** is the exact user submission. It is saved before LLM work so all later spans point back to durable source text.

**Source window** is a bounded slice of raw input used to keep source chunk splitting practical for local and cloud models.

**Source chunk** is one citable unit inside a raw input. Code chooses it by source position so ingestion preserves every part of the input; the LLM summarizes the chunk but does not choose what text survives.

**Recall key** is a lightweight derived handle for something the knowledge base may need to recall. It can be an entity, topic, event, task, question, or another user-specific thing.

**Recall link** connects a recall key to a source chunk. A link can carry relation and time metadata so retrieval can build useful views without loading everything.

This branch originally targeted temporal memory. The active indexing work became the smaller foundation temporal memory needs: source-backed chunks, recall links, and optional time hints. Dedicated temporal ordering is not implemented in this document yet.

## Recall Key Fields

Recall keys use coarse normalized fields plus source-grounded hints:

- `kind`: `entity`, `topic`, `event`, `task`, `question`, or `other`.
- `kind_label`: optional natural label from the source.
- `aliases`: conservative alternate names only.
- `summary`: short orientation hint, not citable evidence.
- `metadata`: small source-grounded extras.

Unknown LLM kinds normalize to `other`; the original value is preserved in metadata.

## Recall Link Fields

Recall links use:

- `relation`: `mentions`, `about`, `updates`, `contradicts`, `supports`, or `other`.
- `relation_label`: optional natural source-grounded phrase.
- `event_time`: optional normalized time from source text.
- `time_label`: optional original time phrase.
- `metadata`: small source-grounded extras.

Unknown LLM relations normalize to `other`; the original value is preserved in metadata.

Temporal fields are hints, not truth:

- `event_time` should be a normalized date, year, or comparable value only when the source clearly supports it.
- `time_label` should preserve source phrases such as "before the time skip", "later", or "after the decision".
- Missing time fields are acceptable. The system should prefer partial temporal evidence over invented precision.

## Indexing Flow

1. Receive raw text.
2. Preprocess text if configured.
3. Save raw input unchanged.
4. Split input into source windows.
5. Save each source window as a source chunk.
6. Summarize each source chunk neutrally.
7. Extract or match recall keys for the new chunks.
8. Save recall keys and append recall links.
9. Embed source chunks and recall keys for vector search.

If recall indexing fails, raw input, source chunks, and vector index should still remain usable.

The implementation lives under `server/src/services/rag/`. The public ingest route submits a durable job through `RagService.ingest(...)` and returns immediately.

Durable job details live in `server/docs/RAG_DURABILITY.md`.

## Recall Matching

Recall matching should prefer reuse when a new chunk clearly refers to an existing key by name, alias, summary, or candidate match.

Recall indexing is coordinated by a small LangGraph subgraph:

```txt
find_candidates
-> draft
-> normalize
   -> retry once if validation failed
   -> done
```

The subgraph is only orchestration. Existing chains still do candidate lookup,
LLM drafting, and code normalization.

Candidate lookup is bounded before the LLM sees it:

1. Exact saved name/alias matches.
2. SQLite FTS keyword matches over saved recall keys.
3. Chroma semantic recall-key matches, only when at least one recall key exists.
4. Merge and cap candidates before prompting the LLM.

The semantic lookup is skipped when there are no saved recall keys yet. That avoids embedding calls during first-ingest recall retries where there is nothing to semantically match.

Safe recall key updates:

- Merge conservative aliases.
- Update summary as a broad merged orientation hint when new evidence improves it.
- Update `kind_label` when clearer.
- Update coarse `kind` only when the existing value is `other`.
- Shallow-merge safe metadata.
- Update `updated_at`.

Existing recall key names stay stable. New source chunks may enrich the key's
summary, aliases, label, or metadata, but they should not narrow the key to only
the latest chunk.

Normal ingest appends links. It does not delete old links or rewrite old chunks.

## Source-Bound Rules

- Raw input is the authority.
- Source chunks must point to raw spans and should not be lossy.
- Recall keys and summaries must not introduce unsupported facts.
- Labels, reasons, and metadata are hints, not citable evidence.
- Final answers should cite source chunk spans, not recall metadata.

## Not In This Enhancement

This design does not include atom extraction, full graph traversal, contradiction resolution, production multi-user storage, recursive summary engines, or dedicated temporal ordering. Temporal retrieval should build on `event_time`, `time_label`, source spans, and recall links in a later pass.
