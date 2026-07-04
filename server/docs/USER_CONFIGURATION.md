# User Configuration System

## Overview

UnmessIt.AI splits per-user AI configuration into two parts:

- **Processing settings**: stable ingest/retrieval behavior. These include embedding batch size, chunk size, chunk overlap, and ingest retry backoff.
- **AI Profiles**: completely independent `LLM configs` and `Embedding configs`. These include OpenAI-compatible API keys, base URLs, language model names, embedding model names, generation limits, retries, and rate limits.

LLM and embedding runtime selection are independent and configured on a **per-stage** basis. For example, "Ingest Summarization" and "Retrieval Answer" can use completely different LLMs. Each stage can use one active config or rotate across its own ordered fallback list. Rotation is per job/request only. The system does not persist a "last good" pointer. Each job/query starts at the first saved lane item and tries the next item only if the current item fails.

## Resolution Flow

1. `user_processing_settings` supplies stable processing settings.
2. `user_stage_config` maps each distinct pipeline stage to a specific active config or fallback rotation list.
3. `user_llm_configs` and `user_embedding_configs` store the credentials and models.
4. `src.infra.settings.get_user_llm_setting_candidates(user_id, stage)` returns ordered LLM `Settings` objects for that stage.
5. `src.infra.settings.get_user_embedding_setting_candidates(user_id, stage)` returns ordered embedding `Settings` objects for that stage.

The LRU caches clear when processing settings, presets, or rotation order change.

## Hard Rules

- Only the `openai` provider is supported.
- Chunk size, chunk overlap, embedding batch size, and ingest retry backoff do not rotate mid-job.
- LLM and embedding configurations are strictly separated.
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
- `GET /configs/stages` - Fetch current stage assignments and active configs.
- `PUT /configs/stages/{stage}` - Update the routing for a specific stage.
- `GET /configs/llm` - List LLM configs without API keys.
- `POST /configs/llm` - Create an LLM config.
- `PUT /configs/llm/{config_id}` - Update an LLM config.
- `DELETE /configs/llm/{config_id}` - Delete an LLM config.
- `GET /configs/embedding` - List embedding configs without API keys.
- `POST /configs/embedding` - Create an embedding config.
- `PUT /configs/embedding/{config_id}` - Update an embedding config.
- `DELETE /configs/embedding/{config_id}` - Delete an embedding config.
- `POST /configs/test` - Test an unsaved or edit-mode LLM/embedding API config and return HTTP 200 on success.

## Retry Backoff

`ingest_retry_backoff_seconds` lives in processing settings as a comma-separated list such as `5,15,30,60,120`. Invalid entries are ignored, values over one hour are dropped, and an empty result falls back to the default list.

## Testing Rule

When testing chains, repositories, or infra that touch AI configuration, pass `user_id` and the required `stage`. Global AI provider secrets are not supported.
