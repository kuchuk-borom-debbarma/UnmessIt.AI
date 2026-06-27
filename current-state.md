# Current State

This file is a plain snapshot of the project today: implemented behavior, system shape, strengths, weaknesses, and known limits.

## Implemented System

- UnmessIt.AI is a local-first knowledge ingestion and retrieval app.
- The server lives in `server/src` and exposes FastAPI routes.
- The UI lives in `web/src` and calls the server routes.
- Raw user input is saved unchanged as the source of truth.
- Active ingestion is SEAI: raw input -> source windows -> episodes -> atoms -> SQLite save -> temporal memory subjects/links -> Chroma index.
- Active retrieval is SEAI-aware: normalized query -> planner -> subject-linked evidence for broad queries -> vector search plus lexical sweep -> reranker -> quote bank -> strict cited answer.
- Episodes and atoms point back to exact raw spans.
- Memory subjects are a derived recall index over episodes and atoms; they are not source truth.
- The app keeps old `memory_items` table support only for old DB and wipe compatibility.

## Temporal Memory Subjects

Implemented shape:

```txt
raw input
-> source windows
-> episodes
-> atoms
-> memory subjects and temporal links
-> vector index
```

A memory subject is a lightweight derived node for a recurring thing in the user's accumulated input. It can represent any useful concept, person, place, project, theme, question, decision, problem, event, story, research topic, or user-specific subject.

Memory subjects link to source-backed episodes and atoms. Links can carry relation labels and time metadata:

- `created_at`: reliable ingest time.
- `event_time`: optional normalized time mentioned in source text.
- `time_label`: optional original time phrase from the text.

Subjects and links are retrieval indexes. They are not factual authority. Final answers must still cite raw episode or atom spans.

## Core Retrieval Challenge

The main unsolved product problem is broad-topic recall over an evolving user knowledge base.

Users may ask about a broad subject that appears across many separate inputs, chunks, points, and references. A correct answer may require finding the recurring subject, gathering relevant evidence across time, and synthesizing only what the cited record supports.

Narrow questions can usually be answered from a small number of matching facts. Broad questions need subject resolution, coverage, temporal awareness, grouping, and compact synthesis.

## Tech Stack

- Backend: Python 3.12, FastAPI, Uvicorn, Pydantic.
- Frontend: React, Vite, React Router, Axios, lucide-react.
- Dependency injection: `kink`.
- LLM client layer: LangChain with OpenAI-compatible and Ollama-compatible providers.
- Embeddings/vector search: Chroma.
- Relational storage: SQLite.
- Eventing: in-memory async `EventBus` adapter.
- Optional coreference: `fastcoref`, with fallback to raw text.
- Testing: pytest.

## Active API

- `POST /ingest/` publishes an ingest job to the in-memory event bus.
- `POST /api/retrieval/query` returns `{ answer, citations, retrieval_trace }`.
- `GET /dev/seai` returns raw inputs with nested episodes and atoms.
- `GET /dev/subjects` returns memory subjects with temporal evidence links.
- `GET /dev/raw_inputs/{input_id}` returns one raw source document.
- `DELETE /dev/facts` wipes raw inputs, episodes, atoms, memory subjects, legacy memory items, and Chroma.

## Architecture Rules

- `src/routes/` is HTTP delivery only.
- `src/services/` owns use-case orchestration and domain flow.
- `src/repositories/` owns SQLite query/write classes and repository ports.
- `src/infra/` owns external technology such as LangChain, Chroma, SQLite connection, settings, logging, UUIDs, and event bus adapters.
- `src/infra/di/bootstrap.py` is the composition root.
- LLM-backed chains use the `JsonLLM` port and do not import LangChain directly.
- Retrieval keeps the public response shape `{ answer, citations, retrieval_trace }`.

Full rules live in `server/docs/rules/codebase_rules.md`.

## Strengths

- Source-bound by design: answers and UI evidence can trace back to raw text spans.
- Multi-span episodes handle messy notes where one subject appears in multiple places.
- Atoms are complete standalone claims, which improves retrieval precision.
- Quote-bank retrieval keeps final answer context smaller than passing whole documents.
- LLM/provider setup is mostly isolated behind infra and ports.
- Ingest chains are simple `run(...)` units, so the SEAI flow is easy to reorder or replace.
- Dev UI/API can inspect raw inputs, episodes, atoms, spans, and retrieval traces.
- Local model support exists through LM Studio/Ollama/OpenAI-compatible endpoints.

## Weaknesses

- Ingest is LLM-heavy: splitting, summarizing, extraction, episode verification, and atom verification can be slow or brittle on small local models.
- Retrieval still depends on LLM planner/reranker/answer quality; bad JSON or weak reasoning can cause fallback behavior.
- Broad questions have subject-linked recall, but synthesis is still limited by extracted links, capped evidence, and LLM reranking quality.
- The event bus is in-memory, so jobs are not durable across process restarts.
- SQLite and Chroma are good for local/dev use but not yet a production multi-user storage story.
- Retrieval repository/vector ports are not fully normalized into shared top-level port locations yet.
- Dev routes still resolve the dev repository directly because they are intentionally simple.
- Fastcoref is optional and can fail or be too heavy locally.

## Local Model Constraints

- LM Studio/OpenAI-compatible JSON behavior varies by model and server.
- Some reasoning models may return JSON in hidden/reasoning fields instead of normal content.
- 8B-class local models can hit memory or compute errors on long prompts.
- Smaller chunks and compact quote banks help, but do not remove local hardware limits.
- Cloud LLMs are usually more reliable for JSON-heavy SEAI steps.

## Not Solved Yet

- No backfill for memory subjects over existing pre-feature data.
- No durable job queue.
- No migration system.
- No production auth/multi-user isolation.
- No contradiction resolution.
- No global rolling summary.
- No full graph traversal.

## Docs

- Architecture rules: `server/docs/rules/codebase_rules.md`.
- Indexing design: `server/docs/SEAI_INDEXING_FLOW.md`.
- Retrieval design: `server/docs/SEAI_RETRIEVAL_FLOW.md`.
