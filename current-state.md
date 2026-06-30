# Current State

Engineering snapshot as of 2026-06-30.

## Product Direction

UnmessIt.AI is a source-backed personal RAG app for evolving user notes. The product goal is simple: users store messy text, then ask questions later and get answers grounded in the exact saved sources.

The current implementation is OpenAI-standard only. Users configure OpenAI text and embedding presets in the app Settings screen. Server environment variables are for runtime concerns such as JWT, CORS, dev routes, and logging.

## Current App Shape

- `/` is a public landing page.
- `/login` and `/signup` are product-aware auth pages.
- Logged-out navigation shows brand, sign in, sign up, and theme toggle.
- Logged-in navigation shows notes, ask AI, jobs, trash, settings, theme, and logout.
- Protected app routes redirect guests to `/login`.

## Implemented Features

- Local username/password auth with JWT bearer tokens.
- Per-user data isolation across notes, directories, tags, raw inputs, source chunks, recall keys, recall links, vectors, and presets.
- Notes CRUD with directory structures, tag organization, pagination, and a soft/hard delete Trash system.
- Materialized-path directories for efficient subtree queries and strict 100-nested depth limits.
- Soft-delete vector synchronization (moving notes to trash masks raw inputs and evicts Chroma vectors; restoring re-indexes instantly).
- Cross-Domain Directory Filtering for AI queries (restrict RAG search strictly to, or explicitly exclude, entire directory trees).
- Event-driven note ingestion through the in-memory event bus.
- Raw input storage as source truth.
- Durable ingestion jobs with SQLite checkpoints, bounded retry/backoff, pause, and stop controls.
- Lossless source chunks chosen by source position, not by LLM importance.
- LLM summaries for chunks without replacing source text.
- Recall keys and recall links for entities, topics, tasks, events, questions, and other reusable handles.
- Chroma vector indexes for source chunks and recall keys (ChromaDB client acts as a global singleton to prevent SQLite locking).
- Retrieval with query breakdown, vector search, lexical search, recall-key search, linked-chunk expansion, dedupe, rerank, and Context Engineering (context packing/distillation).
- Source-backed answer generation with citations to specific `note_id`s, source chunks, and an expandable Retrieval Analysis Trace.
- Settings UI for OpenAI presets, API keys, model names, base URLs, max tokens, retries, chunk size, chunk overlap, and rate limits.
- Jobs UI for durable ingest job status, stage tracking, pause, stop, resume, and delete.
- Paginated Note Insights UI for inspecting recall keys and links per note (replaced global memory UI).

## Active Ingestion Shape

```txt
note create/update
-> notes service saves user-facing note
-> event bus emits note.created or note.updated
-> RAG listener submits durable ingest job
-> raw input saved/reused
-> source windows
-> source chunks
-> recall keys and recall links
-> recall-key vectors
-> source-chunk vectors
```

Source chunks save full citable text and point back to raw spans. LLM output can summarize and link, but it cannot decide what source text survives.

## Active Retrieval Shape

```txt
query
-> breakdown into focused sub-queries
-> parallel source vector, lexical, and recall search
-> linked source chunk expansion
-> merge, dedupe, rerank
-> context-pack focused snippets
-> answer from selected source chunks
```

Recall keys and links are navigation hints. Final answers cite source chunks.

## Active API

Public/auth:

- `POST /api/auth/sign_up`
- `POST /api/auth/sign_in`
- `GET /api/auth/me`
- `POST /api/auth/logout`

Product:

- `GET /notes/`
- `POST /notes/`
- `PUT /notes/{note_id}`
- `DELETE /notes/{note_id}`
- `GET /directories/`
- `POST /directories/`
- `GET /tags/`
- `POST /ingest/`
- `POST /api/retrieval/query`
- `GET /api/retrieval/events/{client_id}`
- `GET /configs/presets`
- `POST /configs/presets`
- `PUT /configs/presets/{preset_id}/activate`
- `DELETE /configs/presets/{preset_id}`
- `GET /configs/active`

Advanced authenticated inspection:

- `GET /api/advanced/memory`
- `GET /api/advanced/recall`
- `GET /api/advanced/raw_inputs/{input_id}`
- `DELETE /api/advanced/raw_inputs/{input_id}/hard`
- `GET /api/advanced/ingest_jobs`
- `POST /api/advanced/ingest_jobs/{job_id}/resume`
- `DELETE /api/advanced/ingest_jobs/{job_id}`

Development-only routes:

- `/dev/*` routes exist for local inspection/reset and are gated by `ENABLE_DEV_ROUTES`.

## Tech Stack

- Backend: Python 3.12, FastAPI, Uvicorn, Pydantic, SQLite.
- RAG: LangChain, LangGraph, Chroma, OpenAI chat/embedding APIs.
- Frontend: React 19, Vite, React Router 7, Tailwind CSS 4, Framer Motion, lucide-react.
- Deployment: Fully dockerized multi-stage builds (Server + Nginx).
- Testing: pytest, pytest-asyncio, TypeScript build, oxlint.

## What Is Good Now

- Public landing and auth are separated from protected app routes.
- Source truth is preserved before any LLM work.
- Durable ingest skips completed units on resume, and supports pause/stop.
- Corrupt jobs abort when source truth is missing instead of retrying forever.
- Recall indexing has candidate lookup, draft, normalization, and one validation retry.
- Retrieval searches broadly but answers narrowly from selected source chunks.
- Context Engineering optimization stats are transparent to the user in Ask View.
- UI is highly polished with debounced spinners, query state preservation, and animated traces.
- ChromaDB SQLite locking is resolved via a global singleton.
- Route prefixes between frontend and backend are currently aligned.
- OpenAI-only provider rules are enforced in the config route and reflected in the UI.

## Current Limits

- Background ingest workers are in-process threads, not a distributed queue.
- SQLite and Chroma are still beta storage choices, not a production multi-region data layer.
- Chroma collection names are per user, but vector rebuild/migration is manual if embedding dimensions change.
- Timeline answers use source order, spans, `source_time`, `event_time`, and `time_label` hints; there is no dedicated temporal ordering layer yet.
- Recall quality controls broad reasoning quality.
- There is no LLM response cache table.
- There is no dead-letter/archive table for failed jobs.
- `/dev/*` routes should stay disabled outside local debugging.

## Likely Next Steps

- **Durable Pub/Sub**: Implement durable pub/sub using idempotency and a transactional outbox pattern to guarantee event delivery between the Notes and RAG domains.
- **Tag Filtering**: Granular control to filter AI searches by specific tags during querying.
- **Custom Knowledge Connections**: Give users the ability to manually teach the AI connections by wiring explicit recall links between concepts or notes.
- Add explicit timeline ordering for timeline-style questions if real examples need it.
- Add a rebuild-vector-index command for embedding model changes.
- Add small evaluations for multi-note, broad-recall, and citation correctness.
- Replace in-process jobs with a real queue/lease only when multi-process deployment needs it.
- Add route contract tests for frontend-used endpoints.

## Far Far in the Future

- **Cloud Platform**: A fully hosted cloud version of UnmessIt.AI for zero-setup, ubiquitous access to user knowledge bases.

## Useful Checks

Backend:

```bash
cd server
uv run pytest src
```

Frontend:

```bash
cd web
npm run lint
npm run build
```

## Docs

- Code rules: `server/docs/rules/codebase_rules.md`
- Prompt rules: `server/docs/rules/prompt_rules.md`
- Auth: `server/docs/AUTH_INFRASTRUCTURE.md`
- User config: `server/docs/USER_CONFIGURATION.md`
- Notes and ingestion: `server/docs/NOTES_AND_INGESTION.md`
- Indexing: `server/docs/SEAI_INDEXING_FLOW.md`
- Retrieval: `server/docs/SEAI_RETRIEVAL_FLOW.md`
- Durability: `server/docs/RAG_DURABILITY.md`
- SSE: `server/docs/SSE_INFRASTRUCTURE.md`
- Beta deploy: `server/docs/BETA_DEPLOY.md`
