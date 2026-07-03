# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-03

### Added
- Provider-native prompt caching now activates automatically for official OpenAI LLM presets by sending a stable, non-secret prompt cache key.
- Prompt rules now document cache-friendly structure: durable instructions first, reusable schemas/examples next, and dynamic user/source data last.
- Embeddings are now cached in memory and Redis when available, reducing repeated provider calls for identical text/model inputs.
- Query breakdown now uses an exact memory/Redis cache so repeated retrieval queries can skip the planning LLM call.
- Subject extraction now uses exact memory/Redis caching for repeated query-planning inputs.
- Subject extraction can reuse strict semantic cache hits when prompt, LLM, and embedding settings match.
- Evidence search now uses an exact memory/Redis cache invalidated by a durable SQLite retrieval index version.
- Evidence search now uses strict semantic candidate caching to boost similar sub-query retrieval without skipping normal search or verification.
- Evidence verification now uses an exact memory/Redis cache for repeated verifier decisions over the same query and compact evidence payload.
- Answer generation now uses an exact memory/Redis cache for repeated final answers over the same query and compact verified evidence payload.
- Document ingestion now uses exact memory/Redis caching for `SourceChunkDraftChain` (summaries) and `RecallDraftChain` (entities) to skip re-running expensive LLM calls on identical text blocks.

### Changed
- Refactored Server-Sent Events (SSE) progress reporting to use a centralized context variable (`_active_parent_ref`) for cleaner nested UI representations.
- Simplified internal log messaging in query chains and cache modules to plain, user-friendly language.
