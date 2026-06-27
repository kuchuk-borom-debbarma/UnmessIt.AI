# Current State

This file is a plain snapshot of what the project has today: system shape, tech stack, strengths, weaknesses, and known limits.

## System
- UnmessIt.AI is a local-first knowledge ingestion and retrieval app.
- The app is an evolving ingestion system: users can keep adding new inputs over time, so indexing and retrieval must work across an accumulated, changing knowledge base rather than a one-time upload.
- The server lives in `server/src` and exposes FastAPI routes.
- The UI lives in `web/src` and calls the server routes.
- Active ingestion is SEAI: raw input -> source windows -> episodes -> atoms -> SQLite save -> Chroma index.
- Active retrieval is SEAI-aware: normalized query -> planner -> vector search plus lexical sweep -> reranker -> quote bank -> strict cited answer.
- Raw source text remains the truth. Episodes and atoms point back to exact raw spans.
- The app keeps old `memory_items` table support only for DB/wipe compatibility; current ingest writes SEAI tables.

## Core Retrieval Challenge
- The main unsolved product problem is broad-topic recall over an evolving user knowledge base.
- Users may ask about a broad topic, person, place, project, idea, or pattern that appears across many separate inputs, chunks, points, and references.
- A correct answer may require linking multiple stored pieces together before forming a useful answer or resolution.
- Example: if a user has added many notes about the same project over several days, a question like "what is going on with this project?" should gather the relevant notes, connect repeated themes and open issues, and answer from the combined evidence rather than only the nearest few matches.
- Narrow questions can usually be answered from a small number of matching facts. Broad questions need coverage, grouping, and synthesis across the stored record.

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
- `GET /dev/raw_inputs/{input_id}` returns one raw source document.
- `DELETE /dev/facts` wipes raw inputs, episodes, atoms, legacy memory items, and Chroma.

## Architecture
- `src/ports/` owns shared ports such as `JsonLLM` and `EventBus`.
- `src/infra/` owns external technology: LangChain setup, Chroma, SQLite connection, event bus adapters, settings, logging, and UUID generation.
- `src/repositories/` owns SQLite query/write repositories.
- `src/services/` owns use-case orchestration and domain flow.
- `src/routes/` is HTTP delivery only.
- `src/infra/di/bootstrap.py` is the composition root.
- SEAI ingest chain order is defined in `services/ingest_engine/domain/seai/ingestor.py`.
- Retrieval substeps are split into planner, evidence cards, reranker, quote-bank packing, answer generation, and citation validation.

## Strengths
- Source-bound by design: answers and UI evidence can trace back to raw text spans.
- Multi-span episodes handle messy notes where one topic appears in multiple places.
- Atoms are meant to be standalone claims, which improves retrieval precision.
- Quote-bank retrieval keeps final answer context smaller than passing whole documents.
- LLM/provider setup is mostly isolated behind infra and ports.
- Ingest chains are simple `run(...)` units, so the SEAI flow is easy to reorder or replace.
- Dev UI/API can inspect raw inputs, episodes, atoms, spans, and retrieval traces.
- Local model support exists through LM Studio/Ollama/OpenAI-compatible endpoints.

## Weaknesses
- Ingest is LLM-heavy: splitting, summarizing, extraction, episode verification, and atom verification can be slow or brittle on small local models.
- Retrieval still depends on LLM planner/reranker/answer quality; bad JSON or weak reasoning can cause fallback behavior.
- Broad questions are better than before but still not true global synthesis or contradiction resolution.
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
- No graph traversal.
- No atom links.
- No global rolling summary.
- No contradiction resolution.
- No durable job queue.
- No migration system.
- No production auth/multi-user isolation.
- No LangGraph retrieval workflow is active, even though the dependency exists.

## Docs
- Architecture rules: `server/docs/rules/codebase_rules.md`.
- Indexing design: `server/docs/SEAI_INDEXING_FLOW.md`.
- Retrieval design: `server/docs/SEAI_RETRIEVAL_FLOW.md`.
