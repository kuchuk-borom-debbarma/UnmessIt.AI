# User Configuration System

## Overview

UnmessIt.AI splits per-user AI configuration into two parts:

- **Processing settings**: stable ingest/retrieval behavior. These include embedding batch size, chunk size, chunk overlap, and ingest retry backoff.
- **Config presets**: complete model/API setups. These include OpenAI-compatible API keys, base URLs, language model names, embedding model names, generation limits, retries, and rate limits.

LLM and embedding runtime selection are independent. Each lane can use one active preset or rotate across its own ordered preset list. Rotation is per job/request only. The system does not persist a "last good" pointer. Each job/query starts at the first saved lane item and tries the next item only if the current item fails.

## Resolution Flow

1. `user_processing_settings` supplies stable processing settings.
2. `user_rotation_config` supplies LLM lane mode, embedding lane mode, active preset IDs, and ordered rotation IDs.
3. `user_config_presets` stores config presets. The legacy `is_active` flag remains for compatibility, while lane active IDs decide the current LLM and embedding singles.
4. `src.infra.settings.get_user_llm_setting_candidates(user_id)` returns ordered LLM `Settings` objects.
5. `src.infra.settings.get_user_embedding_setting_candidates(user_id)` returns ordered embedding `Settings` objects.

The LRU caches clear when processing settings, presets, or rotation order change.

## Hard Rules

- Only the `openai` provider is supported.
- Chunk size, chunk overlap, embedding batch size, and ingest retry backoff do not rotate mid-job.
- LLM and embedding lanes can be single/rotation independently.
- LLM and embedding model names belong to config presets and can differ between presets.
- API keys are never returned by `/configs` responses and never stored in snapshots.
- SSE progress is display-only. Durable checkpoints and saved artifact metadata are the persistent record.

## Snapshots

Saved chunks, recall keys/links, and vector metadata include non-secret configuration snapshots where useful:

- `processing_settings`: chunking, batch size, and retry backoff.
- `llm_rotation_preset`: the non-secret lane snapshot for LLM-produced artifacts.
- `embedding_rotation_preset`: the non-secret lane snapshot attached to vector metadata.

## API

- `GET /configs/processing` - Fetch stable processing settings.
- `PUT /configs/processing` - Save stable processing settings.
- `GET /configs/rotation` - Fetch LLM and embedding lane mode, active IDs, and ordered rotation IDs.
- `PUT /configs/rotation` - Save LLM and embedding lane mode, active IDs, and ordered rotation IDs.
- `POST /configs/test` - Test an unsaved or edit-mode LLM/embedding API config and return HTTP 200 on success. When `preset_id` is supplied, blank API key fields reuse the saved secret for that preset.
- `GET /configs/presets` - List config presets without API keys.
- `POST /configs/presets` - Create a config preset.
- `PUT /configs/presets/{preset_id}` - Update a config preset while preserving omitted keys.
- `PUT /configs/presets/{preset_id}/activate?lane=llm|embedding|both` - Switch one lane or both lanes to one specific config and disable that lane's rotation.
- `DELETE /configs/presets/{preset_id}` - Delete a config preset.
- `GET /configs/active` - Compatibility endpoint returning the first effective settings candidate.

## Retry Backoff

`ingest_retry_backoff_seconds` lives in processing settings as a comma-separated list such as `5,15,30,60,120`. Invalid entries are ignored, values over one hour are dropped, and an empty result falls back to the default list.

## Testing Rule

When testing chains, repositories, or infra that touch AI configuration, pass `user_id`. Global AI provider secrets are not supported.
