# Current State

Engineering snapshot as of 2026-07-05.

## Product Direction

UnmessIt.AI is a source-backed personal unstructured knowledge engine. The product goal is simple: users store messy text, then ask questions later and get answers grounded in the exact saved sources.

The system uses a highly localized version of Graph RAG via "Recall Keys" to connect topics across isolated notes without the massive indexing overhead of a rigid graph database.

## Current App Shape

- `/` is a public landing page.
- `/login` and `/signup` are product-aware auth pages.
- Logged-out navigation shows brand, sign in, sign up, and theme toggle.
- Logged-in navigation shows notes, ask AI, jobs, trash, settings, theme, and logout.
- Protected app routes redirect guests to `/login`.

## Implemented Features (The UnmessIt Architecture)

- **Durable LangGraph Ingestion**: Notes are ingested via a durable LangGraph workflow with strict SQLite checkpoints (`load_raw_input` -> `source_chunks` -> `recall` -> `recall_vectors` -> `source_vectors` -> `complete`).
- **Transactional Outbox & Redis Streams**: Decouples API requests from AI background jobs, ensuring at-least-once guaranteed delivery of `note.created` events.
- **4-Layer Deduplication Guard**: Uses LLM pre-fetching, in-memory batch merging, exact-match DB lookups, and SQLite unique constraints to prevent Graph sprawl.
- **Deterministic Fan-out Querying**: Complex user queries are broken down by an LLM into multiple targeted sub-queries.
- **Multi-Strategy Parallel Search**: Vector Search (dense), Lexical Search (sparse), and Recall Link Expansion execute concurrently via `asyncio.gather`.
- **Top-Level Multi-Cache System**: Fast-paths identical queries via Exact Memory Cache (1ms) and Semantic ChromaDB Cache (skips LLM entirely if distance < `0.02`).
- **Semantic Verifier Trap**: Evaluates edge-case cache hits (0.02 < dist < 0.05) to ensure missing negative constraints or antonyms do not trigger hallucinations.
- **SSE Fanout Architecture**: Background workers stream real-time UI updates via Redis Pub/Sub to specific frontend websocket connections, using a 30s TTL presence heartbeat.
- **Backend-Driven Tracing**: The UI is fully backend-driven, parsing `retrieval_trace.ui` contracts to render token usage, cache savings, and search pathways visually.

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
- `POST /api/retrieval/query`
- `GET /api/retrieval/events/{client_id}`
- `GET /configs/processing`
- `PUT /configs/processing`

Advanced authenticated inspection:
- `GET /api/advanced/ingest_jobs`
- `POST /api/advanced/ingest_jobs/{job_id}/resume`
- `DELETE /api/advanced/ingest_jobs/{job_id}`

## Tech Stack

- **Backend**: Python 3.12, FastAPI, LangChain, LangGraph, ChromaDB, SQLite, Redis.
- **Frontend**: React 19, Vite, Tailwind CSS 4, Framer Motion.
- **Deployment**: Docker Compose, multi-stage builds.

## What Is Good Now

- **Strict Source Truth**: LLMs can extract Recall Keys and Summaries, but the original text chunks are always preserved and cited.
- **Durable Resumption**: API crashes or token limits simply pause jobs, which can be resumed from exact SQLite checkpoints.
- **Parallel Query Speed**: Queries execute vastly faster by breaking down and searching concurrently, bypassing Naive RAG limitations.
- **Documentation is Pristine**: The engineering architecture is deeply documented and centralized into a single canonical source of truth.

## Likely Next Steps (Future Roadmap)

- **Conversational AI with History**: Add multi-turn chat memory so the AI can maintain context and references across sequential follow-up questions from the user. 
*(No other roadmap items are planned at this time).*

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

The documentation has been consolidated into a clean, categorized structure in `server/docs/`:

- **Architecture**
  - `server/docs/architecture/ARCHITECTURE_DEEP_DIVE.md` (The canonical engineering novel)
  - `server/docs/architecture/raw-architecture-doc.md` (Core design philosophy)
- **Deployment**
  - `server/docs/deployment/BETA_DEPLOY.md`
  - `server/docs/deployment/DOCKER_NETWORKING.md`
- **Operations**
  - `server/docs/operations/USER_CONFIGURATION.md`
  - `server/docs/operations/AUTH_INFRASTRUCTURE.md`
- **Reference**
  - `server/docs/reference/CACHE_EVALUATION_NOTES.md`
  - `server/docs/reference/PROMPTS_OVERVIEW.md`
- **Rules**
  - `server/docs/rules/codebase_rules.md`
  - `server/docs/rules/prompt_rules.md`
