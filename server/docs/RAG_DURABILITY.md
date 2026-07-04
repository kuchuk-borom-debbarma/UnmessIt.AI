# RAG Durability

Durable ingestion is private to `server/src/services/rag`. Routes call the public RAG service; durability owns job rows, checkpoints, retries, pause/resume/stop, and the LangGraph ingest workflow.

## Flow

```txt
POST /ingest/
-> get_rag_service().submit_ingest_job(...)
-> save or reuse raw input by content hash
-> create or reuse ingest job
-> schedule background work
-> run missing checkpoint units
-> mark job complete
```

`POST /ingest/` returns after job submission. LLM calls and vector writes happen in the private scheduler.

On startup, `server/src/main.py` calls:

```python
get_rag_service().resume_pending_jobs()
```

This resumes `queued`, `running`, and due `waiting_retry` jobs. `paused`, `failed`, `complete`, and `aborted` jobs stay still until an explicit action applies.

## Files

- `server/src/services/rag/private/durability/`
- `server/src/services/rag/private/rag_service_impl.py`
- `server/resources/schema.sql`

## Stored State

- `raw_inputs.content_hash`: SHA-256 of preprocessed text; exact idempotency key.
- `ingest_jobs`: one row per submitted job.
- `ingest_checkpoints`: one row per deterministic unit inside a job.

> [!NOTE]
> All LLM-backed cache keys include a hashed `llm_settings_signature`. This guarantees that if a user changes their AI provider, model, or generation settings, the cache is safely partitioned and old answers are never incorrectly served for a new configuration.

Job statuses:

- `queued`
- `running`
- `waiting_retry`
- `paused`
- `complete`
- `failed`
- `aborted`

Checkpoint primary key is `(job_id, stage, unit_key)`. Completed units are skipped on retry or manual resume.

## Runner Stages

```txt
load job and raw input
abort if source truth is missing
checkpoint raw_input
build or reuse source chunks
build or reuse recall links
index or reuse recall-key vectors
index or reuse source-chunk vectors
mark job complete
```

Unit keys are deterministic and content-bound where source text is involved, for example:

```txt
source_piece:{raw_input_id}:{start}:{end}:{sha256(piece_text)}
recall_chunk:{source_chunk_id}
recall_key_vector:{recall_key_id}
source_vector:{source_chunk_id}
```

SQLite source rows are the source of truth. Chroma vectors are rebuildable indexes.

## Event Delivery

Docker runs Redis for cross-process delivery. State changes write SQLite outbox rows, the dispatcher publishes them to Redis Streams, and each server process consumes through the `unmessit:server` consumer group.

Handlers record `event_handler_runs` before work and skip completed event/handler pairs on redelivery. This gives at-least-once delivery with persistent duplicate suppression. Manual backend runs can leave `REDIS_URL` unset and use the in-memory event bus.

See `server/docs/REDIS_EVENTS.md` for Redis Streams, outbox, and SSE delivery details.

## Retry And Resume

Retries are bounded. Default retry backoff is:

```txt
5,15,30,60,120
```

The list is configurable in per-user processing settings. Invalid entries are ignored and values over one hour are dropped.

When a unit fails, the runner marks the unit failed, increments the job attempt count, records the failing unit, and either schedules `waiting_retry` or marks the job `failed`. A successful unit resets attempts, so retries apply to the currently failing unit.

Manual controls:

```txt
GET    /api/advanced/ingest_jobs
POST   /api/advanced/ingest_jobs/{job_id}/resume
POST   /api/advanced/ingest_jobs/{job_id}/pause
POST   /api/advanced/ingest_jobs/{job_id}/stop
DELETE /api/advanced/ingest_jobs/{job_id}
```

Development mirrors live under `/dev/*` when `ENABLE_DEV_ROUTES=1`.

Manual resume sets a job back to `queued`, clears retry state, keeps completed checkpoints, and schedules only missing or failed work. `aborted` jobs are terminal because missing source text cannot be reconstructed safely.

## Limits

- The scheduler is in-process, not a distributed queue.
- There is no cross-process job lease.
- A crashed process may leave a checkpoint marked `running`; the next run can overwrite it when that unit is reached.
- Aborted jobs stay in `ingest_jobs` with the reason in `error`.
- Recall returning zero links is currently retryable.

Run one worker process per SQLite database unless a real queue or lease is added.
