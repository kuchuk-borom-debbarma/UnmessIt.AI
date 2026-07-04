# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-03

### Added
- Added sub-query semantic caching with a fast LLM verifier to safely bypass retrieval processing for repeated semantic concepts at the sub-query level.
- Rebuilt the Retrieval Analysis UI into a Server-Driven UI timeline, perfectly tracking latencies, models, token usage, and cache hits precisely per execution step.
- Added background cron job to periodically clean up stale semantic cache values with random jitter.
- Fixed note creation to support choosing between Markdown and Plain Text formats.
- Enhanced Note UI to reliably use ResizeObserver for smooth content expansion and shrinking.
- Updated Answer generation to format results in Markdown and improved the popover UI for better readability.
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
- Recall candidate lookup during ingest now uses exact memory/Redis caching to skip repeated SQLite and vector candidate searches before the recall-draft LLM.
- Retrieval analysis now reports source-context engineering as raw-to-engineered prompt compression, including zero context when verifier and answer both hit cache.
- AI configuration is now split into named LLM configs and named embedding configs with per-stage single or fallback-rotation routing.
- Ingestion now runs independent source chunk and recall units with bounded parallelism while preserving durable per-unit checkpoints.

### Changed
- Refactored Server-Sent Events (SSE) progress reporting to use a centralized context variable (`_active_parent_ref`) for cleaner nested UI representations.
- Simplified internal log messaging in query chains and cache modules to plain, user-friendly language.
