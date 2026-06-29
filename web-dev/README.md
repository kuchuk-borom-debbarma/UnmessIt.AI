# UnmessIt.AI Web Dev

React/Vite development frontend for the UnmessIt.AI memory app.

## Screens

- **Ingest Journal** posts text to `POST /ingest/` and shows the queued durable job id.
- **Memory Explorer** reads `/dev/seai`, `/dev/recall`, and `/dev/ingest_jobs` to inspect saved source chunks, recall links, and job state.
- **Ask AI** posts to `POST /api/retrieval/query` and displays the answer, citations, full source chunks, and retrieval trace.
- **Database** calls `DELETE /dev/facts` to wipe local memory, durability rows, lookup indexes, and vectors.

## Backend Assumption

The UI currently points at:

```txt
http://localhost:8000
```

Run the FastAPI server before using the UI.

## Commands

```bash
npm run dev
npm run build
npm run lint
```
