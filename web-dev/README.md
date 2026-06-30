# UnmessIt.AI Web Dev

Legacy React/Vite development UI kept for reference.

The current product frontend lives in `web/`. Use this directory only when you need the older dev-only screens that talk directly to local inspection routes.

## Old Screens

- **Ingest Journal** posts text to `POST /ingest/`.
- **Memory Explorer** reads `/dev/seai`, `/dev/recall`, and `/dev/ingest_jobs`.
- **Ask AI** posts to `POST /api/retrieval/query`.
- **Database** calls `DELETE /dev/facts`.

## Backend Assumption

This UI points at:

```txt
http://localhost:2317
```

It requires `ENABLE_DEV_ROUTES=1` for the `/dev/*` screens.

## Commands

```bash
npm run dev
npm run build
npm run lint
```
