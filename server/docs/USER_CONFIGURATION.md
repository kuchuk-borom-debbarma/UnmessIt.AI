# User Configuration System

## Overview
UnmessIt.AI uses a **per-user preset system** for AI configuration. Each user manages their own OpenAI model names, API keys, optional OpenAI-compatible base URLs, chunk sizes, and generation limits without colliding with other users on the same instance.

This design explicitly serves the application's multi-tenant capabilities by treating each user as an isolated domain of configuration and persistence.

## Configuration Resolution
Configuration for any given user request is resolved in the following sequence:

1. **In-Memory Cache (LRU)**
   The most recent configurations are cached in an `lru_cache` within the application memory to minimize database read overhead. This cache clears automatically when a preset is activated or modified.

2. **Database (SQLite `user_config_presets` Table)**
   If not cached, the application reads the currently active preset for the `user_id` from the SQLite database. Presets contain OpenAI text model names, embedding model names, API keys, optional base URLs, and chunk settings.

3. **Application Defaults**
   If a user has no active preset, AI work raises `NoActivePresetError` and the API returns `428` with code `no_active_preset`. Provider secrets and model endpoints are never loaded from `.env`; users define those values in Settings.

## Provider Rule

Only the `openai` provider is supported. The `/configs` route validates both `llm_provider` and `embedding_provider` and rejects anything else.

Optional base URLs remain available for endpoints that follow OpenAI-compatible request and response behavior. There is no Ollama/local-provider branch in active code.

## Late-Binding Architecture (LangChain & Embeddings)
Because configuration is dynamic, we do not initialize global AI text or embedding clients on application startup. Instead, we use a **late-binding** approach.

Components like `JsonLLMClient` and `get_embedding_function` are instantiated per-request. By passing `user_id` down the entire call stack (from the API route, through the LangGraph chains, down to the clients), the system fetches the user's specific `Settings` from the LRU cache just milliseconds before making the provider API call.

## RAG Isolation Strategy

Because API keys and configuration define context windows and embedding models, we must strictly isolate user data across the entire RAG pipeline:

* **ChromaDB Collections**: Chroma collections are dynamically named using the convention `statements_{user_id}` instead of a single shared `statements` collection. This enforces rigid data separation at the persistence layer.

> [!WARNING]
> **Cloud Infra Limitations**
> Scoping Chroma collections by user ID (`statements_{user_id}`) is acceptable for the current beta storage layer. A larger cloud multi-tenant deployment should use either a dedicated multi-tenant vector database with namespaces/tenants or a single shared collection with rigid metadata filtering (`{"user_id": {"$eq": user_id}}`) enforced at the proxy layer.

* **Vector Migrations**: Because each user manages their own embedding model, vector dimensions may change. The application does not migrate existing vectors automatically; the user must rebuild their knowledge base if they swap embedding representations.

## Using the API

The `/configs` router provides CRUD operations for managing these presets:
* `GET /configs/presets` - List all presets for the authenticated user.
* `POST /configs/presets` - Create a new preset.
* `PUT /configs/presets/{preset_id}` - Update an existing preset while preserving saved API keys when omitted.
* `GET /configs/active` - Fetch the currently active preset.
* `PUT /configs/presets/{preset_id}/activate` - Set a preset as the active context for the user.
* `DELETE /configs/presets/{preset_id}` - Delete a preset.

## Testing Rules Addendum

When writing integration tests or unit tests for components across the stack (Chains, Repositories, Infra), **always pass a `user_id` parameter** to the mock functions and pipeline steps. Global AI configuration is not supported; tests that omit `user_id` will fail configuration and persistence lookups.
