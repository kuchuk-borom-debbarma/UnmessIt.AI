# Current State

This file is the engineering snapshot: what exists, what is rough, and what should improve next.

## Product Direction

UnmessIt.AI is an AI RAG-powered knowledge base for evolving user input. Users add their own data over time, then ask AI about it later.

The product is not local-only. It should support configurable model providers, API keys, base URLs, and local or hosted model endpoints. The current code already reads provider settings from environment variables.

## Branch Direction

This branch started as temporal memory work, but the implementation shifted after the old ingestion/retrieval code proved too noisy and too lossy for temporal reasoning.

The current branch is now a memory-engine reset:

- replace atom/episode/memory-subject storage with source chunks and recall links
- make ingestion durable and resumable
- keep source text lossless
- make retrieval source-backed and inspectable
- leave temporal ordering as the next layer, using existing `event_time`, `time_label`, source spans, and recall links

## Implemented Features

- React UI for ingesting text, asking questions, browsing stored memory, and wiping dev data.
- FastAPI backend with stable ingest, retrieval, dev, and health routes.
- Raw input storage as the source of truth.
- Lossless source chunks chosen by source position, not by LLM importance.
- LLM-written source chunk summaries.
- Recall keys for reusable entities, topics, events, tasks, questions, and other user-specific things.
- Recall indexing uses a nested LangGraph subgraph for candidate lookup, LLM draft, normalization, and one validation retry.
- Recall links connecting recall keys back to source chunks with relation and optional time metadata.
- Durable ingest jobs orchestrated with LangGraph and checkpointed in SQLite for source pieces, recall chunks, recall-key vectors, and source-chunk vectors.
- Corrupt ingest jobs abort when their raw source row is missing instead of retrying forever.
- Startup/manual resume for queued, retryable, or failed ingest jobs.
- Chroma vector indexes for both source chunks and recall keys.
- Retrieval from ranked source chunks with recall expansion, context-packed snippets, and cited answers.

## Active Ingestion Shape

```txt
raw input
-> source windows
-> lossless source chunks
-> source chunk summaries
-> recall keys and recall links
-> source chunk and recall key vector indexes
```

Source chunks save the full text piece and point back to exact raw spans. The LLM can summarize a chunk, but it cannot decide which source text survives.

Recall keys evolve cautiously as new evidence arrives. Existing names stay stable, aliases merge conservatively, and summaries can become broader orientation hints.

## Active Retrieval Shape

```txt
query
-> source chunk vector search
-> source chunk lexical search
-> recall key search
-> linked source chunk expansion
-> rank and context-pack source chunks
-> one JSON answer prompt over focused snippets
```

Retrieval treats recall keys and recall links as navigation only. The final answer prompt receives source chunks as citable evidence.
The prompt uses summaries plus focused snippets to save context, while the API still returns full source chunks for inspection.

This supports:

- Basic fact questions through direct source chunk search.
- Broader questions through recall-key and linked-chunk expansion.
- Connection-style questions when related chunks share recall keys.
- Timeline-style questions when relevant chunks contain source order or time labels.

## Active API

- `POST /ingest/` schedules a durable ingest job and returns immediately.
- `POST /api/retrieval/query` returns `{ answer, citations, source_chunks, retrieval_trace }`.
- `GET /dev/seai` returns raw inputs with nested source chunks.
- `GET /dev/recall` returns recall keys with recall links.
- `GET /dev/raw_inputs/{input_id}` returns one raw source document.
- `GET /dev/ingest_jobs` lists durable ingest jobs.
- `POST /dev/ingest_jobs/{job_id}/resume` manually resumes a waiting or failed job.
- `DELETE /dev/facts` wipes active ingestion tables and Chroma vectors.

## Tech Stack

- Backend: Python 3.12, FastAPI, Uvicorn, Pydantic.
- Frontend: React, Vite, React Router, Axios, lucide-react.
- LLM client layer: LangChain with OpenAI-compatible and Ollama-compatible providers.
- Embeddings/vector search: Chroma.
- Relational storage: SQLite.
- Testing: pytest and frontend lint/build.

## What Is Good Now

- The memory model is small: raw inputs, source chunks, recall keys, recall links.
- Source chunks are no longer lossy.
- Ingest uses a LangGraph stage workflow with durable, idempotent unit checkpoints.
- Missing source truth is now a terminal abort path, so bad jobs stop cleanly.
- Recall indexing has its own small LangGraph subgraph, so the retry/validation branch is visible.
- Recall-key lookup is bounded before LLM calls.
- Recall keys can be reused and updated instead of creating obvious duplicates every time.
- Retrieval now uses both direct source search and recall-link expansion.
- The UI is wired to show answers, citations, source chunks, retrieval trace, and durable ingest jobs.

## Current Limits

- Retrieval is intentionally simple: deterministic ranking/context packing, no planner, graph traversal, or agentic tool loop yet.
- Broad answers depend on recall-link quality and source chunk quality.
- No broad raw-input summary exists yet.
- Timeline answers use available source order and stored time hints, but there is no dedicated temporal ordering layer yet.
- Existing old lossy local data is not migrated; wipe and reingest to rebuild with current source chunk behavior.
- Background ingest workers are in-process, not a distributed queue.
- Corrupt-job cleanup is minimal: aborted jobs clear checkpoints and known SQLite source chunks, but Chroma orphan cleanup is deferred.
- SQLite and Chroma are fine for current development but not yet a production multi-user storage plan.
- Provider configuration exists through environment settings, but the product UI for managing user API keys/provider URLs is not built yet.

## Likely Next Steps

- Add temporal retrieval support: detect timeline questions, sort evidence by `event_time`, `time_label`, source span, and source order, then pass explicit timeline order to the answer prompt.
- Strengthen recall prompts for temporal hints without inventing dates.
- Add a broad raw-input summary only if broad answers still lose too much context.
- Add provider/API-key configuration in the UI later.
- Add evaluations using real multi-input knowledge-base questions.

## Docs

- Architecture rules: `server/docs/rules/codebase_rules.md`.
- Indexing design: `server/docs/SEAI_INDEXING_FLOW.md`.
- Durable ingest: `server/docs/RAG_DURABILITY.md`.
- Retrieval design: `server/docs/SEAI_RETRIEVAL_FLOW.md`.
