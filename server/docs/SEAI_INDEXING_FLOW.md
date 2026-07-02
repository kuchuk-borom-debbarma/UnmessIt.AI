# SEAI Indexing Flow

SEAI means **Source Evidence And Indexing** here. The active ingestion flow is small:

```txt
raw input
-> source windows
-> source chunks
-> recall keys and recall links
-> vector index
```

Raw input remains the source of truth. Source chunks, recall keys, recall links, and vectors are indexes over that source.

## Objects

**Raw input** is the exact user submission. It is saved before LLM work so later spans point back to durable source text.

**Source window** is a bounded slice of raw input used to keep chunk splitting practical.

**Source chunk** is one citable unit inside a raw input. Code chooses it by source position; the LLM summarizes it but does not decide what text survives.

**Recall key** is a lightweight handle for something worth finding later: an entity, topic, event, task, question, or other user-specific thing.

**Recall link** connects a recall key to a source chunk. Links can carry relation and time metadata, but they are hints, not citable truth.

## Fields

Recall keys:

- `kind`: `entity`, `topic`, `event`, `task`, `question`, or `other`
- `kind_label`
- `aliases`
- `summary`
- `metadata`

Recall links:

- `relation`: `mentions`, `about`, `updates`, `contradicts`, `supports`, or `other`
- `relation_label`
- `event_time`
- `time_label`
- `metadata`

Unknown LLM kinds or relations normalize to `other`; the original value is preserved in metadata. Temporal fields are optional and must stay source-grounded.

## Flow

1. Receive raw text.
2. Preprocess text if configured.
3. Save raw input unchanged.
4. Split input into source windows.
5. Save each source window as a source chunk.
6. Summarize each source chunk neutrally.
7. Extract or match recall keys for new chunks.
8. Save recall keys and append recall links.
9. Embed source chunks and recall keys for vector search.

Implementation lives under `server/src/services/rag/`. Note events submit durable jobs through `submit_ingest_job(...)`.

See `server/docs/NOTES_AND_INGESTION.md` and `server/docs/RAG_DURABILITY.md`.

## Document Lifecycle

- Soft delete masks the raw input and removes active source-chunk vectors.
- Queries filter deleted chunks out of source evidence.
- Restore re-indexes saved chunks without rerunning the LLM.
- Hard delete removes raw input, source chunks, recall links, vectors, and job state.
- Recall keys can stay when other chunks still use them.

## Recall Deduplication

Recall indexing uses four duplicate guards:

- Candidate retrieval before the LLM, capped before prompting.
- In-memory batch dedupe by normalized name.
- Exact-match repository lookup before creating a new key.
- SQLite unique constraint on normalized name terms.

Safe recall key updates:

- Merge conservative aliases.
- Update summary as a broad merged orientation hint when new evidence improves it.
- Update `kind_label` when clearer.
- Update coarse `kind` only when the existing value is `other`.
- Shallow-merge safe metadata.
- Update `updated_at`.

Existing recall key names stay stable. New source chunks may enrich a key, but normal ingest appends links instead of rewriting old chunks.

## Source Rules

- Raw input is the authority.
- Source chunks point to raw spans and should not be lossy.
- Recall keys and summaries must not introduce unsupported facts.
- Labels, reasons, and metadata are hints, not citable evidence.
- Final answers cite source chunk spans, not recall metadata.

## Limits

This design does not include atom extraction, full graph traversal, contradiction resolution, recursive summary engines, or dedicated temporal ordering. Temporal retrieval should build on `event_time`, `time_label`, source spans, and recall links only when real examples need it.
