This PR introduces the highly requested Cross-Domain Directory Filtering feature and synchronizes RAG vectors with the Trash system.

## Changes Included
- **Materialized-Path Directory Filtering**: AI searches can now be restricted to (or explicitly exclude) entire directory subtrees without expensive recursive database CTEs.
- **Dynamic Retrieval Operators**: Cross-links SQLite domain hierarchy with ChromaDB `$in` and `$nin` metadata querying to enforce strict organizational scopes.
- **RAG Soft Delete Sync**: Trash management is now fully synchronized. Moving a note to the trash emits a `note.soft_deleted` event that instantly evicts vector bounds from ChromaDB.
- **Instant Restore**: Emitting `note.restored` instantly re-pushes existing `source_chunks` back into ChromaDB without queuing an LLM job.
- **Cascading Move Support**: Moving notes automatically ripples through to patch ChromaDB metadata paths.
- **UI Enhancements**: Added an interactive `DirectorySearchSelect` component in the Ask UI allowing users to granularly scope their query.

## Testing
- E2E tests have been authored and verified across deep directory structures (100+ nested limits), verifying semantic `$in` matching and async EventBus synchronization.
- Frontend builds passing strict TypeScript rules.
