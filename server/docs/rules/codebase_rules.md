# UnmessIt.AI Codebase Rules

Keep the server boring, small, and easy to read.

## 1. Server Shape
- `src/main.py` creates the FastAPI app, initializes SQLite, configures logging, and includes routes.
- `src/routes/` is HTTP delivery only: validate input, call a getter/function, return a response.
- `src/infra/` owns low-level technology setup: LangChain JSON, SQLite connection/init, Chroma, settings, logging.
- Redis setup, Redis Streams dispatch, and Redis-backed SSE live under `src/infra/`; SQLite outbox persistence lives in repositories.
- `src/repositories/` owns plain SQLite/Chroma function modules. Do not add repository classes unless state is unavoidable.
- `src/services/rag/` owns the product flow: public retrieval service, private chains, durable ingestion pipeline, and job controls.

## 2. No DI Container
- Do not use `kink`, `di[...]`, or a composition root.
- Public service getters compose stable internals once and cache them.
- Routes call `get_rag_service()` or repository functions directly.
- Infra modules may cache low-level clients with `functools.lru_cache`.

## 3. RAG Service
- `rag_service.py` exposes `RagService` and `get_rag_service()`.
- `private/pipeline/ingest.py` delegates ingestion to `private/durability/`; durability owns the LangGraph ingest workflow, jobs, checkpoints, retry, pause, stop, and resume.
- Recall indexing may use a nested LangGraph subgraph for candidate/draft/normalize/retry visibility; keep storage and checkpoint behavior in durability/repositories.
- Chains expose `run(...)`.
- If a chain becomes complex, put it in a small directory with local helpers.
- Raw input is saved before LLM work that produces citable spans.
- Durable unit keys must be deterministic and content-bound so completed work is not repeated.
- Missing raw source truth must abort the job instead of retrying forever.

## 4. Repositories
- Use module functions such as `save(...)`, `save_many(...)`, `find_candidate_keys(...)`, `index(...)`, and `reset(...)`.
- SQLite-specific code stays in SQLite repository modules.
- Chroma-specific indexing/search stays in Chroma repository modules.
- Wipe behavior must clear raw inputs, source chunks, recall keys/links, ingest jobs/checkpoints, and Chroma vectors.
- Recall-key candidate lookup must stay bounded before the LLM sees it.

## 5. LLM And Chroma
- LangChain imports belong only in `src/infra/`.
- Chains use the JSON client passed by `get_rag_service()`.
- Do not log API keys, full prompts, full model responses, or full raw source text.
- Chroma is a rebuildable index; SQLite source rows are the source of truth.
- Redis is a delivery/cache layer. SQLite remains the source of truth for jobs, events, and idempotency.
- Embedding cache belongs in `src/infra/`, may use in-memory plus Redis layers, and must stay disposable; never make Redis the source of truth for vectors.

## 6. Routes
- Keep these URLs stable: `POST /ingest/`, `POST /api/retrieval/query`, `GET /notes/`, `POST /notes/`, `GET /directories/`, `GET /tags/`, `GET /configs/presets`, `GET /configs/processing`, `PUT /configs/processing`, `GET /configs/rotation`, `PUT /configs/rotation`.
- Authenticated memory/job inspection lives under `/api/advanced/*`, including `/api/advanced/memory`, `/api/advanced/recall`, and `/api/advanced/ingest_jobs`.
- Development-only inspection/reset routes live under `/dev/*` and must stay gated by `ENABLE_DEV_ROUTES`.
- `POST /ingest/` returns after durable job submission; the private scheduler does the background work.
- Retrieval returns `{ answer, citations, source_chunks, retrieval_trace }` from source chunks, with recall keys/links used only for expansion.
- Timeline behavior must build on source chunks, recall links, `event_time`, `time_label`, and spans. Do not add a separate temporal model until the simple ordered-evidence path fails real examples.

## 7. Comments
- Comments explain why a non-obvious choice exists. Do not narrate obvious code.
- Add short comments for pipeline order, fallbacks, source-of-truth choices, and intentional no-op behavior.
- Use `ponytail:` comments for deliberate shortcuts and name the upgrade path.

## 8. Cleanup
- Delete inactive experiments instead of wrapping them.
- Do not add ports/adapters folder splits, factories, listeners, or interfaces for imaginary future implementations.
- Add one focused test for non-trivial logic or an architecture boundary.
