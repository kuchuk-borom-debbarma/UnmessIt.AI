# User Configuration System

## Overview

UnmessIt.AI splits per-user AI configuration into two parts:

- **Processing settings**: stable ingest/retrieval behavior. These include embedding batch size, chunk size, chunk overlap, and ingest retry backoff.
- **Config presets**: complete model/API setups. These include OpenAI-compatible API keys, base URLs, language model names, embedding model names, generation limits, retries, and rate limits.

Rotation is per job/request only. The system does not persist a "last good" pointer. Each job/query starts at the first saved rotation lane and tries the next lane only if the current lane fails.

## Resolution Flow

1. `user_processing_settings` supplies stable processing settings.
2. `user_rotation_config` supplies whether rotation is enabled and the ordered preset IDs.
3. `user_config_presets` stores config presets. The `is_active` flag is the specific config used when rotation is disabled.
4. `src.infra.settings.get_user_setting_candidates(user_id)` returns ordered `Settings` objects combining stable processing with either the active preset or rotation presets.

The LRU caches clear when processing settings, presets, or rotation order change.

## Hard Rules

- Only the `openai` provider is supported.
- Chunk size, chunk overlap, embedding batch size, and ingest retry backoff do not rotate mid-job.
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
- `GET /configs/rotation` - Fetch rotation enabled state and ordered lane IDs.
- `PUT /configs/rotation` - Save rotation enabled state and ordered lane IDs.
- `GET /configs/presets` - List config presets without API keys.
- `POST /configs/presets` - Create a config preset.
- `PUT /configs/presets/{preset_id}` - Update a config preset while preserving omitted keys.
- `PUT /configs/presets/{preset_id}/activate` - Switch to one specific config and disable rotation.
- `DELETE /configs/presets/{preset_id}` - Delete a config preset.
- `GET /configs/active` - Compatibility endpoint returning the first effective settings candidate.

## Retry Backoff

`ingest_retry_backoff_seconds` lives in processing settings as a comma-separated list such as `5,15,30,60,120`. Invalid entries are ignored, values over one hour are dropped, and an empty result falls back to the default list.

## Testing Rule

When testing chains, repositories, or infra that touch AI configuration, pass `user_id`. Global AI provider secrets are not supported.
