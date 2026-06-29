# Notes Service and Event-Driven Ingestion

The UnmessIt.AI architecture separates the organizational domain (Notes, Directories, Tags) from the intensive AI processing domain (RAG, Source Chunks, Vectors) using an event-driven flow.

## 1. Domain Separation

### The Notes Domain (`server/src/services/notes/`)
This is the user-facing organizational layer. It is responsible for:
- Storing the exact text content of what the user wrote (`notes` table).
- Categorizing notes flexibly (`tags` and `note_tags` tables).
- Organizing notes hierarchically using a Materialized Path pattern for fast subtree queries (`directories` table).

The Notes Service focuses strictly on CRUD operations and organization. It does not perform any LLM calls, chunking, or embedding.

### The RAG Domain (`server/src/services/rag/`)
This is the background AI processing layer. It is responsible for:
- Accepting raw text inputs (`raw_inputs`).
- Chunking, summarizing, and linking (`source_chunks`, `recall_keys`).
- Embedding text and metadata into the vector database.

## 2. Event-Driven Flow

To keep the Notes API responses fast and the bounded contexts decoupled, the two domains communicate via an asynchronous in-memory `EventBus`.

1. **User Action**: The client sends a request to `POST /notes` with text and optional tags/directory.
2. **Persistence**: The `NotesService` writes the data to the SQLite `notes` and `note_tags` tables.
3. **Event Emitted**: The `NotesService` publishes a `note.created` event to the `EventBus`, carrying the `note_id`, `text`, and `user_id`.
4. **Immediate Response**: The API responds with `200 OK` and the `note_id`.
5. **Background Listener**: The RAG listener (`server/src/services/rag/listener.py`), which subscribed to `note.created` on startup, catches the event.
6. **Async Ingestion**: The listener spawns an `asyncio.create_task()` background worker that calls `rag_service.ingest(text, user_id, job_id=note_id)`.
7. **Durable Processing**: The `rag_service` creates a durable ingestion job to process the raw text into source chunks and vectors. (See `RAG_DURABILITY.md` and `SEAI_INDEXING_FLOW.md` for details).

## 3. Directory Materialized Paths

To efficiently query entire folder subtrees without expensive recursive SQL queries (CTEs), the `directories` table implements a **Materialized Path** pattern.

- `parent_id`: Points to the immediate parent directory for simple direct-child lookups.
- `path`: Stores the full breadcrumb path of UUIDs (e.g., `/parent-uuid/child-uuid/`).

To list all descendants of a folder (including sub-folders of sub-folders), the query simply uses `LIKE`:
```sql
SELECT * FROM directories WHERE path LIKE '/parent-uuid/%'
```
This is heavily optimized by the `idx_directories_path` index.

## 4. Updates

When a note is updated (`PUT /notes/{id}`), a `note.updated` event is emitted. The RAG listener catches this and submits the new text to `rag_service.ingest()` using the same `note_id` as the `job_id`. Currently, this acts as a re-ingestion, maintaining the system's "append-only" philosophy for recall links, but allowing the source chunks to reflect the updated text.
