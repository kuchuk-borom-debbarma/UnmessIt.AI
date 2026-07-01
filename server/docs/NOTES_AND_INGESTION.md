# Notes And Ingestion

Notes are the user-facing source. RAG is the background index.

## Boundaries

Notes, directories, and tags own organization:

- `notes`
- `directories`
- `tags`
- `note_tags`

RAG owns retrieval artifacts:

- `raw_inputs`
- `source_chunks`
- `recall_keys`
- `recall_links`
- Chroma vectors
- durable ingest jobs and checkpoints

Notes code does not call LLMs or write vectors directly. It saves user data and emits events. The RAG listener submits durable ingest jobs from those events.

## Create Flow

```txt
POST /notes/
-> save note, tags, directory id
-> publish note.created
-> RAG listener submits durable ingest with job_id=note_id
-> API response returns before indexing finishes
```

`POST /ingest/` still exists for direct raw ingestion. Note-created ingestion uses the same durable pipeline.

## Updates

`PUT /notes/{id}` emits `note.updated`. If text changed, stale raw inputs, source chunks, vectors, checkpoints, and job rows for that note are removed before a new durable job is queued with the same note id.

If only the directory changes, the listener updates `directory_path` metadata for saved source chunks and vectors without re-running LLM work.

## Deletes

- Soft delete marks the note as deleted, masks the raw input, and removes active vectors.
- Restore clears deletion state and re-indexes existing chunks into Chroma.
- Hard delete removes the note and cascades removal of raw inputs, chunks, recall links, vectors, and job state.

Recall keys can outlive a deleted note when other chunks still link to them.

## Directories

Directories use a materialized path:

- `parent_id`: immediate parent
- `path`: full UUID breadcrumb, such as `/parent/child/`

Subtree lookup is a bounded SQLite query over `path`, then retrieval passes matching directory paths into Chroma metadata filters.
