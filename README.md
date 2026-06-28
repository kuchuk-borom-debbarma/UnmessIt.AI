# UnmessIt.AI

UnmessIt.AI is an AI RAG-powered knowledge base for information that keeps growing.

Users can paste notes, stories, research, logs, plans, decisions, or messy thoughts into the app over time. Later, they can ask AI about that evolving knowledge base and get answers grounded in the original stored source text.

Traditional RAG is usually built around a mostly static document set. This project is aimed at **living data**: new inputs keep arriving, old topics get updated, and the app needs to connect related evidence across multiple ingests.

## What Users Can Do

- Add arbitrary text whenever they want.
- Keep the original input as the source of truth.
- Ask factual questions about saved information.
- Ask broader questions that need multiple source chunks.
- Ask connection-style or timeline-style questions where related evidence matters.
- Inspect the source chunks, recall keys, recall links, citations, retrieval trace, and ingest jobs behind the answer.
- Use local or hosted model endpoints through environment configuration.

## Current Product Shape

The app has four main screens:

- **Ingest Notes**: submit text and receive a durable background job id.
- **Memory Explorer**: inspect raw inputs, source chunks, recall keys, recall links, and durable ingest jobs.
- **Ask AI**: query saved knowledge and inspect citations, source chunks, and retrieval trace.
- **Database Controls**: wipe local SQLite memory, durability rows, lookup indexes, and Chroma vectors.

## How Memory Works

The active memory model is intentionally small:

```txt
raw input
-> source chunks
-> recall keys
-> recall links
-> vector indexes
```

**Raw input** is the exact user submission and remains the authority.

**Source chunks** are citable slices of that original input. They preserve full source text and raw spans, while the LLM only writes summaries.

**Recall keys** are reusable handles for things the user may ask about later: people, topics, events, tasks, questions, projects, places, or anything else in the user's data.

**Recall links** connect recall keys back to source chunks and may include relation and time hints.

Recall keys, summaries, aliases, and link reasons are navigation metadata. Final answers must be grounded in source chunks.

## How Retrieval Works

When a user asks a question, retrieval uses several small search paths:

```txt
query
-> source chunk vector search
-> source chunk lexical search
-> recall key search
-> linked source chunk expansion
-> rank source chunks
-> context-pack focused snippets
-> cited answer
```

The answer prompt receives source chunk summaries plus focused snippets to save context. The API still returns full source chunks so the UI can inspect the evidence.

## Why This Branch Changed Direction

This branch started as temporal memory work. While exploring the codebase, the larger problem became clear: the previous ingest/retrieval split was too complex and too lossy for reliable temporal reasoning.

The branch now lays the foundation temporal memory needs:

- source chunks are lossless and span-backed
- recall links can store `event_time` and `time_label`
- retrieval can combine direct source search with recall-link expansion
- durable jobs make long ingestion resumable
- dev UI exposes the saved evidence and job state

Dedicated temporal ordering is still future work. The current branch builds the simpler source-backed memory engine that temporal reasoning should sit on top of.

## Tech Stack

- Backend: Python, FastAPI, SQLite, LangChain, LangGraph, Chroma.
- Frontend: React, Vite, React Router, Axios, lucide-react.
- Models: OpenAI-compatible or Ollama-compatible chat and embedding providers through environment variables.

## Key Docs

- Current engineering state: `current-state.md`
- Indexing flow: `server/docs/SEAI_INDEXING_FLOW.md`
- Retrieval flow: `server/docs/SEAI_RETRIEVAL_FLOW.md`
- Durable ingestion: `server/docs/RAG_DURABILITY.md`
- Server rules: `server/docs/rules/codebase_rules.md`
- Prompt rules: `server/docs/rules/prompt_rules.md`
