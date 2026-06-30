# RAG Durability

This document explains how durable ingestion works right now.

The short version:

```txt
POST /ingest/
-> RagService.ingest(...)
-> DurableIngest.submit(...)
-> save or reuse raw input
-> create or reuse ingest job
-> background scheduler runs the job
-> LangGraph runner moves through ingest stages
-> completed checkpoints are skipped and only missing units run
```

Durability is private to `services/rag`. Routes still talk only to the public
RAG service. Chains still transform data. Repositories still save data. The
durability layer only owns the LangGraph stage workflow, job records,
checkpoints, retries, and resume.

## Lifespan

`lifespan` is FastAPI's startup/shutdown hook.

In this app it lives in `server/src/main.py`. When the API process starts,
FastAPI enters the lifespan context and runs:

```python
get_rag_service().resume_pending_jobs()
```

That means unfinished durable ingest jobs are picked up when the server starts
again. The `yield` inside the lifespan function marks the time while the API is
serving requests. Code before `yield` runs at startup; code after `yield` would
run at shutdown.

We use `lifespan` because this installed FastAPI version supports it and does
not expose `app.add_event_handler(...)`.

## Files

Durability code lives here:

- `server/src/services/rag/private/durability/__init__.py`
- `server/src/services/rag/private/durability/models.py`
- `server/src/services/rag/private/durability/repository.py`
- `server/src/services/rag/private/durability/runner.py`
- `server/src/services/rag/private/durability/scheduler.py`

The active service entrypoint is:

- `server/src/services/rag/private/rag_service_impl.py`

The tables are declared in:

- `server/resources/schema.sql`

## Stored State

Durability uses two tables plus one raw input hash column.

### `raw_inputs.content_hash`

`content_hash` is the SHA-256 hash of the preprocessed text.

It gives ingestion an exact idempotency key. If the same normalized text is
submitted again, the app can reuse the existing raw input and durable job
instead of starting over.

### `ingest_jobs`

One row tracks the whole ingest job.

Important fields:

- `id`: public job id returned by `/ingest/`.
- `content_hash`: exact preprocessed text hash.
- `raw_input_id`: saved source text row.
- `status`: current job state.
- `stage`: current broad stage.
- `attempt_count`: retry count for the current failing work.
- `next_run_at`: when a waiting retry may run again.
- `error`: last error, trimmed for inspection.
- `metadata`: final counts or failure context.

Statuses:

- `queued`: ready to run.
- `running`: currently being worked.
- `waiting_retry`: failed, but retry is scheduled.
- `paused`: active job was manually paused and will wait for resume.
- `complete`: finished successfully.
- `failed`: retry cap reached; manual resume is required.
- `aborted`: terminal corrupt-job state, used when required source truth is missing.

### `ingest_checkpoints`

One row tracks one deterministic unit of work inside a job.

Important fields:

- `job_id`: parent ingest job.
- `stage`: broad stage name.
- `unit_key`: deterministic unit key.
- `status`: `running`, `complete`, or `failed`.
- `output_ref`: saved object id or comma-separated ids.
- `error`: last unit error.
- `metadata`: small details needed for inspection or skip behavior.

The primary key is `(job_id, stage, unit_key)`. That lets the runner retry the
same unit safely without creating duplicate checkpoint rows.

## Submit Flow

`POST /ingest/` calls `get_rag_service().ingest(...)` and immediately returns:

```json
{ "status": "processing", "job_id": "..." }
```

The request does not wait for LLM calls or vector indexing.

Inside `RagServiceImpl.ingest(...)`:

1. A job id is created if the route did not pass one.
2. `DurableIngest.submit(...)` is called.
3. The returned job row is converted to the ingest response shape.

Inside `DurableIngest.submit(...)`:

1. The preprocessor runs.
2. A SHA-256 `content_hash` is computed from the preprocessed text.
3. `raw_inputs.save_or_reuse(...)` saves or reuses the exact source text.
4. `repository.create_or_reuse_job(...)` saves or reuses the durable job.
5. The job is scheduled in the in-process background scheduler.
6. The latest job row is returned.

Same text means same `content_hash`. Because `ingest_jobs.content_hash` is
unique, normal repeated submits reuse the same job.

## Startup Resume Flow

When the server starts, FastAPI lifespan calls:

```txt
RagServiceImpl.resume_pending_jobs()
-> DurableIngest.resume_pending()
-> DurableScheduler.resume_pending()
```

The scheduler asks the durability repository for resumable jobs.

Resumable jobs are:

- `queued`
- `running`
- `waiting_retry` with no `next_run_at`
- `waiting_retry` where `next_run_at` is due
- *Note: `paused` jobs are intentionally skipped on startup.*

Each resumable job is scheduled once in the current process.

## Scheduler

`DurableScheduler` is intentionally small.

It keeps an in-memory `_running` set guarded by a `threading.Lock`. That prevents
two background threads in the same Python process from running the same job id
at the same time.

For each scheduled job it starts one daemon thread. The thread loops until the
job becomes `complete`, becomes `failed`, disappears, or finishes all work.

If a job is `waiting_retry`, the thread sleeps until `next_run_at` before trying
again.

This is local-process durability, not a distributed queue. If multiple server
processes run against the same SQLite file, this scheduler does not coordinate
between processes.

## LangGraph Runner

`DurableIngestRunner.run_once(job_id)` invokes a fixed LangGraph workflow from
durable state. LangGraph owns stage order; SQLite checkpoints still own
idempotency and retry decisions.

The workflow is:

```txt
load job and raw input
abort if source truth is missing
checkpoint raw_input
build or reuse source chunks
build or reuse recall links through the recall subgraph
index or reuse recall-key vectors
index or reuse source-chunk vectors
mark job complete
```

If one unit fails, the graph node records the failed checkpoint, schedules retry
on the job, and stops. The next run invokes the same workflow again and skips
work already marked complete.

If the job is corrupt because its raw input reference is missing or the raw
input row was deleted, the graph branches to `abort`. Abort is terminal and
does not retry, because source truth cannot be reconstructed safely.

## Stage 1: Raw Input

The raw input is saved during submit before any LLM work starts.

If the job no longer points to a raw input, or the raw input row is gone, the
runner marks the job `aborted`, clears its checkpoints, and deletes source
chunks for the raw input when that id is still known.

The runner still writes a `raw_input` checkpoint:

```txt
raw_input:{raw_input_id}
```

This checkpoint records that the saved source text exists and can be used by
later stages.

Why this is safe:

- raw input is immutable source text
- every source chunk span points back to this row
- there is no LLM output to repeat

## Stage 2: Source Chunks

Source chunking processes one text piece at a time.

First, `SourceWindowChain` splits long input into bounded pieces. A "source
window" is just a smaller slice of the original raw text with `start` and `end`
character offsets.

For each source window, the runner builds a deterministic unit key:

```txt
source_piece:{raw_input_id}:{start}:{end}:{sha256(piece_text)}
```

That key includes:

- the raw input id
- the source piece start offset
- the source piece end offset
- a hash of the exact piece text

This makes the checkpoint content-bound. If the same piece was completed before
a crash, resume skips it. If the text or offsets change, it becomes a different
unit.

For each unfinished source piece:

1. `SourceChunkDraftChain` asks the LLM for a short summary only.
2. `SourceChunkAssemblerChain` saves the whole source piece as one citable span.
3. The runner replaces temporary chunk ids with stable SHA-based ids.
4. `source_chunks.save_many(...)` inserts chunks with `ON CONFLICT(id) DO NOTHING`.
5. The checkpoint is marked complete with created source chunk ids.

Code, not the LLM, decides which raw text is preserved. This keeps source chunks
lossless; recall keys and links can be rebuilt from those chunks later.

If the LLM provider call fails, the source piece fails and the durable retry
policy handles it. The chain does not save guessed chunks for provider/auth
outages, because that would make a failed LLM call look like successful ingest.

The stable chunk ids are important. If the server crashes after saving chunks
but before marking the checkpoint complete, retrying the same unit produces the
same ids and the database ignores duplicate inserts.

There is also a compatibility reuse path: if source chunks already exist for a
raw input and the job has no source chunk checkpoints yet, the runner reuses
those chunks instead of calling the LLM again.

## Stage 3: Recall

Recall indexing processes one saved source chunk at a time.

Inside the recall stage, `RecallIndexChain` uses a nested LangGraph subgraph:

```txt
find_candidates -> draft -> normalize -> retry_or_done
```

That subgraph gives visibility to the recall-specific branch: if normalization
finds validation errors, the draft node runs one more time with those errors.

For each source chunk, the unit key is:

```txt
recall_chunk:{source_chunk_id}
```

Before calling the LLM, the runner checks two things:

1. Is the recall checkpoint already complete?
2. Does the source chunk already have recall links?

If either is true, the runner marks/reuses the checkpoint and skips the LLM.

For unfinished chunks:

1. `RecallIndexChain` runs for exactly one source chunk.
2. It finds candidate existing recall keys.
3. It asks the LLM to reuse candidate keys or propose new ones.
4. It normalizes keys and links.
5. `recall.save_index(...)` saves keys and appends links.

`recall_links` has a database unique constraint on:

```txt
(recall_key_id, source_chunk_id, relation, relation_label)
```

That is the final duplicate guard. Even if a retry proposes the same evidence
link again, SQLite ignores the duplicate.

Right now, if recall indexing returns zero links for a chunk, the runner treats
that as a failure and retries the unit.

## Stage 4: Recall-Key Vectors

After recall links are saved, the runner loads recall keys connected to the
current source chunks.

For each recall key, the unit key is:

```txt
recall_key_vector:{recall_key_id}
```

Before embedding, the runner checks:

1. Is the checkpoint complete?
2. Does Chroma already have a vector for this recall key id?

If either is true, it marks/reuses the checkpoint and skips embedding.

Recall-key vectors are only an index. They can be rebuilt from SQLite recall
keys if Chroma is wiped.

## Stage 5: Source-Chunk Vectors

For each source chunk, the unit key is:

```txt
source_vector:{source_chunk_id}
```

Before embedding, the runner checks:

1. Is the checkpoint complete?
2. Does Chroma already have a vector for this source chunk id?

If either is true, it marks/reuses the checkpoint and skips embedding.

Source chunk vectors are also rebuildable. The durable source of truth remains
SQLite raw inputs and source chunks.

## Completion

When all stages finish, the runner marks the job complete and stores counts in
`ingest_jobs.metadata`:

```json
{
  "raw_input_id": "...",
  "source_chunks": 3,
  "recall_keys": 8
}
```

The job status becomes `complete`, the stage becomes `complete`, retry state is
cleared, and the completion is logged.

## Retry Behavior

Retries are bounded.

Current constants:

- retry limit: `5`
- backoff seconds: `30`, `120`, `300`, `900`, `1800`

When a unit fails:

1. The unit checkpoint is marked `failed`.
2. The job `attempt_count` increases.
3. The failing `unit_key` is stored in job metadata.
4. If attempts are below the cap, the job becomes `waiting_retry`.
5. `next_run_at` is set from the backoff table.
6. If attempts reach the cap, the job becomes `failed`.

A successful unit calls `reset_attempts(...)`. This means retries are counted
against the currently failing unit, not permanently against the whole job.

## Manual Resume

Manual resume and pause are exposed through authenticated beta UI routes:

```txt
POST /api/advanced/ingest_jobs/{job_id}/resume
POST /api/advanced/ingest_jobs/{job_id}/pause
DELETE /api/advanced/ingest_jobs/{job_id}
GET /api/advanced/ingest_jobs
```

Development-only mirrors also exist when `ENABLE_DEV_ROUTES=1`:

```txt
GET /dev/ingest_jobs
POST /dev/ingest_jobs/{job_id}/resume
DELETE /dev/ingest_jobs/{job_id}
```

Resume calls:

```txt
RagServiceImpl.resume_ingest_job(...)
-> DurableIngest.resume_job(...)
-> DurableScheduler.resume_job(...)
```

Manual resume:

- loads the job
- sets it back to `queued`
- clears retry count, error, and `next_run_at`
- keeps completed checkpoints
- schedules it again

Completed checkpoints are not deleted. That is the key point: manual resume
retries missing or failed units without redoing completed work.

Aborted jobs are terminal. Manual resume returns the aborted job row without
rescheduling it, because the missing source text cannot be recreated safely.

## Dev Visibility

Authenticated advanced routes:

- `GET /api/advanced/ingest_jobs`: list jobs for the current user.
- `POST /api/advanced/ingest_jobs/{job_id}/resume`: manually resume a current-user job.
- `DELETE /api/advanced/ingest_jobs/{job_id}`: delete a current-user job record.

Dev routes, when enabled:

- `GET /dev/ingest_jobs`: list jobs newest first.
- `POST /dev/ingest_jobs/{job_id}/resume`: manually resume a job.
- `DELETE /dev/ingest_jobs/{job_id}`: delete a job record.
- `DELETE /dev/facts`: wipe active memory, vectors, jobs, and checkpoints.

The wipe route clears durability rows, raw inputs, source chunks, recall keys,
recall links, recall exact/FTS lookup rows, and the shared Chroma collection
that contains both source-chunk and recall-key vectors.

Logs are emitted at info level for:

- job submit
- startup resume
- manual resume
- unit start
- unit complete
- unit reuse
- retry scheduling
- job complete

Recall adds more detailed diagnostic logs because that stage depends on LLM
JSON shape and ID references:

- `recall_candidates`: candidate source counts before the LLM.
- `recall_draft_request`: chunk/candidate counts and whether this is a retry.
- `recall_draft_response`: top-level JSON keys plus draft key/link counts.
- `recall_normalizer_input`: compact key refs and link refs from the LLM.
- `recall_normalizer_result`: normalized key/link counts and validation errors.
- `recall_index_retry`: validation errors passed into the one retry prompt.
- `recall_index_complete`: final normalized counts after retry.
- `ingest_recall_index_result`: recall output seen by the durable runner.
- `ingest_recall_saved`: number of links SQLite accepted.

The logs intentionally identify job ids, stages, and unit keys. They do not log
the full raw input text.

## Idempotency Summary

Idempotency is layered.

Raw input:

- exact preprocessed text hash
- `raw_inputs.save_or_reuse(...)`
- one durable job per `content_hash`

Source chunks:

- deterministic source piece keys
- stable source chunk ids on retry
- `ON CONFLICT(id) DO NOTHING`

Recall:

- one recall unit per source chunk id
- skip chunks that already have recall links
- unique link constraint prevents duplicate evidence links

Vectors:

- one vector unit per object id
- skip if checkpoint exists
- skip if Chroma already has the object id
- skip semantic recall-key candidate search until at least one recall key exists

Jobs:

- scheduler prevents duplicate in-process workers for the same job id
- startup resumes queued/running/due retry jobs
- failed jobs require manual resume

## What This Does Not Do Yet

The current system is deliberately simple.

Known limits:

- The scheduler is in-process and thread-based.
- There is no distributed lock across multiple server processes.
- There is no LLM response cache table yet.
- There is no archive/dead-letter table yet; aborted jobs stay in `ingest_jobs`
  with the abort reason in `error`.
- A crashed process may leave a checkpoint marked `running`; the next run can
  overwrite it when that unit is reached again.
- Chroma orphan cleanup for corrupt jobs is deferred to a future rebuild/reset
  index command.
- Recall returning zero links is treated as retryable failure.
- Retrieval uses a small LangGraph flow for query breakdown and parallel search,
  then deterministic merge, dedupe, rerank, and context packing. It is not a
  full planner or graph traversal engine.

These limits are acceptable for the current development setup. A production
multi-process deployment would need a real job lease or queue before running
multiple workers against the same database.
