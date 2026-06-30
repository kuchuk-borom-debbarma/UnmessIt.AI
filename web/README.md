# UnmessIt.AI Web

Current React/Vite frontend for UnmessIt.AI.

## Routes

- `/` public landing page.
- `/login` sign-in page.
- `/signup` sign-up page.
- `/notes` authenticated note capture and organization.
- `/ask` authenticated AI search.
- `/memory` authenticated source chunk and recall-key inspection.
- `/jobs` authenticated durable ingest job monitor.
- `/settings` authenticated OpenAI preset management.

Logged-out users can see the landing page and auth pages. Protected routes redirect to `/login`.

## Commands

```bash
npm install
npm run dev -- --host 127.0.0.1
npm run lint
npm run build
```

Default backend:

```txt
http://localhost:8000
```

Override:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1
```

## API Notes

The frontend currently uses:

- `/api/auth/*`
- `/notes/`
- `/directories/`
- `/tags/`
- `/api/retrieval/query`
- `/api/advanced/memory`
- `/api/advanced/recall`
- `/api/advanced/ingest_jobs`
- `/configs/*`

Settings exposes OpenAI-only presets with model names, API keys, optional OpenAI-compatible base URLs, chunk size, and chunk overlap.
