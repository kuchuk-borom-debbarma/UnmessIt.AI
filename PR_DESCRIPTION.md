# PR: Rebuild RAG Memory Engine Around Source Chunks, Recall Links, And Durable Ingestion

## Summary

This branch started as temporal memory work, but the implementation shifted after exploring the existing ingestion and retrieval code. The old atom/episode/memory-subject pipeline was too complex, too scattered, and too lossy to support reliable temporal reasoning.

Instead, this PR rebuilds the memory engine around a smaller source-backed RAG model:

```txt
raw input
-> source chunks
-> recall keys
-> recall links
-> vector indexes
-> source-backed retrieval
```

Temporal memory is not abandoned. This PR lays the foundation for it by preserving source spans, adding recall links with optional `event_time` and `time_label`, making ingestion durable, and making retrieval inspectable. Dedicated temporal ordering can now be added as a smaller follow-up.

## Why This Changed From Temporal Memory

The original goal was temporal memory, but temporal reasoning needs trustworthy evidence first.

The previous architecture had several blockers:

- ingestion and retrieval were split across too many abstractions
- source text could become lossy during extraction
- old atom/episode/memory-subject paths made behavior hard to inspect
- duplicate or drifting subjects were likely as new data arrived
- failed ingestion work was hard to resume safely
- retrieval did not expose enough trace data to debug broad answers

This PR intentionally resets the foundation before adding more temporal behavior.

## Major Changes

### Simple RAG Service

- Replaces the old split ingest/retrieval engines with `server/src/services/rag`.
- Removes the DI container and uses cached service getters instead.
- Keeps routes stable:
  - `POST /ingest/`
  - `POST /api/retrieval/query`
  - `GET /dev/seai`
  - `GET /dev/recall`
  - `GET /dev/raw_inputs/{input_id}`
  - `GET /dev/ingest_jobs`
  - `POST /dev/ingest_jobs/{job_id}/resume`
  - `DELETE /dev/facts`

### Source-Backed Memory Model

- Uses active tables:
  - `raw_inputs`
  - `source_chunks`
  - `recall_keys`
  - `recall_key_terms`
  - `recall_keys_fts`
  - `recall_links`
  - `ingest_jobs`
  - `ingest_checkpoints`
- Moves schema to `server/resources/schema.sql`.
- Keeps raw input as the source of truth.
- Saves source chunks losslessly with source spans.
- Uses LLM summaries as hints only, not as citable truth.

### Recall Keys And Links

- Adds bounded candidate lookup before recall LLM calls:
  - exact name/alias lookup
  - SQLite FTS keyword lookup
  - Chroma recall-key vector lookup
  - top-20 candidate cap
- Allows reused recall keys to evolve cautiously:
  - keep existing canonical name
  - merge conservative aliases
  - update broad orientation summary
  - update `kind_label` when clearer
  - update coarse `kind` only when existing is `other`
- Keeps duplicate link prevention in SQLite with a unique link constraint.
- Uses a small LangGraph recall subgraph for candidate lookup, draft, normalize, and one validation retry.

### Durable Ingestion

- Adds private durability under `services/rag/private/durability`.
- Adds durable jobs and unit checkpoints in SQLite.
- Uses a LangGraph stage runner:

```txt
load raw input
-> source chunks
-> recall
-> recall-key vectors
-> source-chunk vectors
-> complete
```

- Saves or reuses raw input by exact preprocessed text hash.
- Processes source chunks, recall links, and vectors by deterministic unit keys.
- Skips completed units on retry/resume.
- Retries failed units with bounded backoff.
- Aborts corrupt jobs when source truth is missing instead of retrying forever.
- Resumes queued/running/due retry jobs on FastAPI lifespan startup.

### Retrieval

- Implements source-backed retrieval:

```txt
query
-> source chunk vector search
-> source chunk lexical search
-> recall key search
-> linked source chunk expansion
-> rank chunks
-> context-pack focused snippets
-> one JSON answer call
```

- Treats recall keys and recall links as navigation only.
- Sends source chunk summaries plus focused snippets to the answer prompt.
- Returns full source chunks to the API/UI for inspection.
- Returns detailed retrieval trace:
  - vector hit ids
  - lexical hit ids
  - linked chunk ids
  - ranked source chunk ids
  - context chars before/after packing
  - selected snippet counts
  - score reasons

### Frontend

- Updates Memory Explorer to show:
  - raw inputs
  - source chunks
  - recall keys
  - recall links
  - durable ingest jobs
- Adds resume action for failed/waiting retry jobs.
- Updates Ask AI to show:
  - answer
  - citations
  - source chunks
  - retrieval trace
  - context packing stats
- Updates Database screen copy to match current wipe behavior.

### Docs

- Rewrites README around the product direction.
- Updates `current-state.md` as the engineering snapshot.
- Updates indexing, retrieval, durability, codebase, and prompt rules.
- Replaces the default Vite frontend README with app-specific frontend docs.

## What This Does Not Solve Yet

- Dedicated temporal ordering is not implemented yet.
- Timeline answers depend on recall-link quality, source order, and existing time hints.
- No broad raw-input/document summary exists yet.
- No agentic retrieval loop or graph traversal is included.
- No production multi-user storage or distributed job queue is included.
- Old local data is not migrated; wipe and reingest to rebuild with the new model.

## Follow-Up Work

Recommended next step:

```txt
timeline query detection
-> temporal evidence ordering
-> pass timeline_order into answer prompt
```

Use existing fields first:

- `recall_links.event_time`
- `recall_links.time_label`
- `source_chunks.source_time`
- source span start/end
- raw input/source order

After that, evaluate whether broad raw-input summaries are needed.

## Verification

Already run during branch work:

- Python compile checks
- frontend production build
- frontend lint
- focused backend tests during development

Commands used recently:

```bash
rtk proxy .venv/bin/python -m compileall -q src
rtk npm run build
rtk npm run lint
```

Full backend pytest was intentionally avoided while the dev server was running, per local workflow.

## Review Notes

This is a large squash because it intentionally replaces the active memory architecture. The key review path is:

1. `server/src/services/rag/private/rag_service_impl.py`
2. `server/src/services/rag/private/durability/runner.py`
3. `server/src/services/rag/private/chains/recall/index.py`
4. `server/src/services/rag/private/chains/query.py`
5. `server/resources/schema.sql`
6. `web/src/views/ExplorerView.jsx`
7. `web/src/views/RetrievalView.jsx`

The main behavioral invariant: **source chunks are the only citable evidence; recall structures are navigation metadata.**
