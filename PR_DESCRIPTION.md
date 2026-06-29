# Pull Request Description

**Branch:** `feature/auth`
**Target:** `staging`

## Overview
This PR introduces a massive architectural upgrade to the system, transforming a raw single-user RAG script into a multi-tenant, event-driven, agentic note-taking backend. It implements full user authentication and data isolation, extracts a dedicated user-facing Notes/Organization bounded context, completely decouples RAG ingestion via an event bus, and upgrades the query pipeline into a dynamic LangGraph ReAct agent.

## Major Changes

### 1. Multi-Tenant Auth & Strict Data Isolation
- **User IDs Everywhere:** Added `user_id` to all core tables (`raw_inputs`, `source_chunks`, `recall_keys`, `recall_links`, etc.) in `schema.sql`.
- **Repository Enforcement:** Every single repository and RAG pipeline method now explicitly requires and filters by `user_id`, guaranteeing cross-tenant data isolation.
- **Auth State Machine:** Unified the authentication service state machine and decoupled notifications. Migrated old data to a default user automatically.
- **Route Protection:** FastApi routes are now protected via JWT authentication (`Depends(get_current_user_id)`).

### 2. New "Notes" Bounded Context & Organization
- **Dedicated Service:** Replaced the raw RAG `POST /ingest` endpoint with a proper `NotesService` for user-facing CRUD operations on notes, tags, and directories.
- **Materialized Path Directories:** Implemented a hierarchical folder structure using the Materialized Path pattern (`/parent-uuid/child-uuid/`), allowing extremely fast sub-tree SQL lookups without recursive queries.
- **Tags Integration:** Added robust Tag management and `note_tags` associations.

### 3. Event-Driven Async Ingestion
- **Domain Decoupling:** The RAG backend is completely decoupled from the Notes API. 
- **EventBus Architecture:** Creating or updating a note instantly returns success to the user and fires a `note.created` event via an internal `EventBus`. 
- **Background Processing:** A dedicated `RagListener` catches these events and quietly handles the heavy LLM summarization, chunking, and vector embedding asynchronously as a background task.

### 4. Agentic Query Pipeline (Tool-Calling ReAct Agent)
- **Agent Orchestration:** Upgraded the static retrieval chain to a dynamic LangGraph ReAct tool-calling agent (`QueryAgentChain`).
- **New Tools:** The LLM now has explicit tools to browse directories (`list_directories`), list note metadata (`list_notes_in_directory`), read full note content (`read_note`), and run semantic RAG pipelines (`search_knowledge_base`).
- **Structured Outputs via Exceptions:** Used a `StopAgentException` inside a `submit_final_answer` tool to instantly short-circuit the LangGraph loop. This cleanly returns a heavily structured payload (directories, notes, citations, and markdown answers) directly to the UI without error-prone LLM string parsing.

### 5. Documentation & Developer Experience
- **Architecture Docs:** Created `server/docs/NOTES_AND_INGESTION.md` and thoroughly updated `SEAI_RETRIEVAL_FLOW.md` and `SEAI_INDEXING_FLOW.md` to reflect the agentic, event-driven architecture.
- **Future Planning:** Documented the blueprint for "Smart Cross-Domain Queries" (intersecting semantic search with structural metadata via SQL tools and vector filtering) directly in the retrieval docs.

## Verification
- Fully tested in the staging environment.
- All 23 Pytest unit, integration, and architecture tests pass flawlessly.
- Verified the local SQLite database migrations and materialized path directory tree lookups operate at expected speeds.
