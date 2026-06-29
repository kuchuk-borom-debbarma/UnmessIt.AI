# User Configuration System

## Overview
UnmessIt.AI has transitioned from a global `.env` based configuration model to a **per-user preset system**. This allows individual users to maintain isolated settings for LLM providers (e.g., API keys, models, base URLs) without colliding with other users on the same instance. 

This design explicitly serves the application's multi-tenant capabilities by treating each user as an isolated domain of configuration and persistence.

## Configuration Resolution
Configuration for any given user request is resolved in the following sequence:

1. **In-Memory Cache (LRU)**
   The most recent configurations are cached in an `lru_cache` within the application memory to minimize database read overhead. This cache clears automatically when a preset is activated or modified.

2. **Database (SQLite `user_config_presets` Table)**
   If not cached, the application reads the currently active preset for the `user_id` from the SQLite database. Presets contain JSON fields for standard LLM settings (OpenAI API key, Anthropic API key, Ollama URL, etc.).

3. **Fallback (`.env`)**
   If a user has no active preset defined in the database (e.g., a newly created user), the system falls back to the global `.env` definitions to ensure immediate usability out-of-the-box.

## RAG Isolation Strategy

Because API keys and configuration define the context window and the embedding models, we must strictly isolate user data across the entire RAG pipeline:

* **ChromaDB Collections**: Chroma collections are now dynamically named using the convention `statements_{user_id}` instead of a single shared `statements` collection. This enforces rigid data separation at the persistence layer.

> [!WARNING]
> **Cloud Infra Limitations**
> Scoping Chroma collections by user ID (`statements_{user_id}`) is perfectly viable and **good enough for local desktop usage**, as it maps directly to individual sqlite files or isolated namespaces within local Chroma. However, **this pattern does not scale to cloud infrastructure**. A true cloud multi-tenant deployment would require either a dedicated multi-tenant Vector DB (like Pinecone namespaces, Qdrant tenants) or a single shared collection with rigid metadata filtering (`{"user_id": {"$eq": user_id}}`) enforced at the proxy layer.

* **Vector Migrations**: Because each user manages their own configuration and potentially their own vector dimensions (based on their configured embedding model), **we migrate on our own**. The application does not handle global migrations of vectors if an embedding model changes; the user is responsible for rebuilding their knowledge base if they swap vector representations.

## Using the API

The `/configs` router provides CRUD operations for managing these presets:
* `GET /configs` - List all presets for the authenticated user.
* `POST /configs` - Create a new preset.
* `GET /configs/active` - Fetch the currently active preset.
* `POST /configs/{preset_id}/activate` - Set a preset as the active context for the user.
* `DELETE /configs/{preset_id}` - Delete a preset.

## Testing Rules Addendum

When writing integration tests or unit tests for components across the stack (Chains, Repositories, Infra), **always pass a `user_id` parameter** to the mock functions and pipeline steps. Global configuration is no longer guaranteed, and tests that omit `user_id` will fail configuration and persistence lookups.
