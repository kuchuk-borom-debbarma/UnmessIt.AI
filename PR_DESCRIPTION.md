# Pull Request Description

**Branch:** `enhancement/async-io`
**Target:** `staging`

## Overview
This PR started as a simple async migration but evolved into a comprehensive overhaul of the RAG ingestion, retrieval, and document lifecycle architectures. We've significantly improved how the system handles concurrency, resolves vague queries, deduplicates knowledge entities, and manages document deletion.

## Major Changes

### 1. Complete Async Overhaul & Concurrency Fixes
- Migrated the codebase to be fully asynchronous.
- **SQLite Concurrency:** Fixed a severe concurrency crash where parallel `asyncio.to_thread()` calls shared a single SQLite connection. Replaced the global connection with a thread-local proxy (`threading.local()`) so every thread safely manages its own connection.
- **Durable Runner Fix:** Resolved a `TypeError: object tuple can't be used in 'await' expression` crash in the `recall_vectors` stage of the ingestion background worker by properly converting the Chroma indexing functions to coroutines.

### 2. "Subject Extraction" Query Enhancement
- **New LangGraph Node:** Added a `subjects` node to the retrieval graph. For vague queries like "what did the man do?", the LLM extracts the implied subject names (e.g., "Prince Vasili") using the query and context.
- **FTS5 Diacritic Support:** Subject names are searched using SQLite FTS5 to safely handle diacritic variants (e.g., "Helene" matches "Hélène").
- **Search Re-Prioritization:** Explicit subject name matches are now forcefully injected at the front of the candidate list, preventing generic keyword hits (like "officer") from pushing critical entities out of the Top-K bounds.
- **Parallel Vector Expansion:** The retrieval graph now fires a secondary vector search explicitly against the extracted subject names concurrently with the main sub-query vector search.

### 3. Strict 4-Layer Knowledge Deduplication
Rewrote the ingestion deduplication pipeline to aggressively prevent "entity fragmentation" (e.g., creating 50 separate recall keys for "Prince Andrew"). 
- **Salient Entity Pre-Retrieval:** Instead of basic regex matching, chunks now instruct the LLM to output `salient_entities`. These are used to retrieve existing candidates *before* new extractions happen.
- **In-Memory Batch Dedup:** Collapses identical names within a single LLM batch to prevent UUID duplication.
- **Exact Match Resolution:** Fallback SQLite check to forcefully override the LLM if it misses an exact existing name.
- **Structural Database Lock:** Added a `UNIQUE` constraint on `recall_key_terms(normalized_term)` for `term_type='name'`. Concurrent race conditions now cleanly abort and auto-retry via the durable worker, safely reusing the winner's key.

### 4. Trash Bin / Document Lifecycle (Soft & Hard Delete)
- Added a `deleted_at` column to `raw_inputs`.
- **Query Isolation:** All RAG retrieval queries now enforce a strict SQL `JOIN` filter (`deleted_at IS NULL`). This guarantees soft-deleted knowledge is instantly invisible to the LLM.
- **ChromaDB Synchronization:** Moving a document to the Trash instantly deletes its chunks from ChromaDB, preventing the vector store from wasting its Top-K slots on deleted evidence. Restoring the document re-indexes them.
- **Cross-Document Stability:** Deleting a document safely orphans its recall links without destroying the global recall key, ensuring knowledge continuity for other documents that mention the same entities.
- **Frontend Upgrades:** `ExplorerView.jsx` now features a dedicated **Trash** tab with options to Restore or Permanently Hard Delete documents.

### 5. Dev UI & Documentation
- **Job Management:** Added the ability to manually delete stuck durable ingest jobs from the Memory Explorer UI.
- **Docs Update:** Rewrote `server/docs/SEAI_INDEXING_FLOW.md` to document the new 4-Layer Deduplication pipeline and the Document Lifecycle / Trash Bin rules. 
- **Clean up:** Removed redundant `has_keys` logic and optimized SQL joins under the "ponytail" rule.

## Verification
- Staging environment tested. All 30 Pytest unit and architecture tests pass cleanly. 
- Verified that local SQLite database migrations (adding `deleted_at`) ran successfully without corrupting existing RAG indexes.
