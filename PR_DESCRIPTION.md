## What was done

This PR introduces comprehensive tag filtering to the RAG retrieval pipeline and fundamentally optimizes the directory filtering architecture for massive scale.

### 1. Tag Filtering (ANY / ALL Support)
- **Backend API Updates:** The `/tags/search` endpoint is now paginated for performance.
- **Frontend Integration:** Added a new `TagSearchSelect.tsx` component that allows users to filter the AI search context by tags. It supports both `ANY` and `ALL` logical operators.
- **RAG Pipeline:** Plumbed `within_tags`, `excluding_tags`, and `within_tags_condition` through `AskView.tsx` -> `RAGService` -> `QueryState` -> `_search.py` -> `ChromaDB` / `SQLite` / `Recall`.

### 2. O(1) Directory Lineage Search Optimization
Previously, directory filtering required an expensive string prefix query in SQLite to resolve all nested child directories before vector search, which was hard-capped at 1000 paths and degraded linearly with depth.

- **Index-time Lineage Materialization:** During ingestion, the background listener now splits the note's directory materialized path (`/A/B/C/`) and injects a boolean flag for **every parent in its lineage** directly into ChromaDB metadata (`dir_A: True`, `dir_B: True`, `dir_C: True`).
- **O(1) Vector Filtering:** The SQLite path resolution has been entirely removed from the vector search path! We now leverage native ChromaDB `$or` and `$ne` boolean logic during vector retrieval, enabling lightning-fast subtree inclusion and exclusion regardless of depth or scale.
- **Dynamic Re-indexing:** Updated the RAG event listener `_handle_note_moved` to automatically drop and re-index a note's source chunks in Chroma whenever it is moved, ensuring there are no orphaned or stale boolean lineage flags.

### 3. Infinite Scroll Pagination
- Updated both `DirectorySearchSelect.tsx` and `TagSearchSelect.tsx` to use `IntersectionObserver` for seamless infinite scrolling on massive tag and directory datasets.

### Testing
- Wrote an integration test script mocking Chroma chunks and metadata to rigorously verify the native tag operators (ANY/ALL) and the directory lineage boolean flags. All filters successfully execute in $O(1)$ directly inside the Vector DB.
