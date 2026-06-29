# UnmessIt.AI

UnmessIt.AI turns your notes into an AI-searchable knowledge base.

Save messy thoughts, research, decisions, logs, plans, or project notes. The app indexes them, connects related ideas, and lets you ask questions with answers grounded in the sources you saved.

## What You Can Do

- Write and organize notes.
- Put notes into directories and tags.
- Configure your AI model from the app.
- Ask AI questions about your saved knowledge.
- See citations and source chunks behind each answer.
- Check indexing status so you know when new notes are ready.
- Inspect the memory the app built from your notes.

## Fast Start

The easiest way to run UnmessIt.AI is Docker.

```bash
docker compose up --build
```

Open:

```txt
http://localhost:5173
```

Then:

1. Create an account.
2. Open **Settings** and add your AI model preset.
3. Create a note.
4. Wait for indexing to finish.
5. Ask AI a question.

That is the main flow.

## Configure AI

AI settings live inside the app.

Go to **Settings** and create a preset with:

- provider
- text model
- embedding model
- provider URL
- API key
- chunk and retry settings

Each user can have their own presets. Server environment files are only for server runtime settings like auth secret and CORS.

## Using The App

**Notes**
Write the information you want the AI to remember. Add tags and directories when it helps.

**Ask AI**
Ask a question in natural language. The answer includes source-backed evidence so you can check where it came from.

**Memory**
Browse indexed source text, chunks, and recall keys.

**Indexing**
See whether notes are queued, running, finished, or failed.

**Settings**
Manage AI presets for your account.

## Stop Or Reset

Stop Docker:

```bash
docker compose down
```

Remove Docker data:

```bash
docker compose down -v
```

## Manual Setup

Use this if you are developing the project without Docker.

Backend:

```bash
cd server
cp .env.example .env
uv sync
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd web
npm install
npm run dev -- --host 127.0.0.1
```

Open:

```txt
http://127.0.0.1:5173
```

## Developer Notes

Main folders:

```txt
server/   backend API, auth, notes, indexing, retrieval
web/      main React frontend
web-dev/  old development UI kept for reference
```

Useful checks:

```bash
cd server && uv run pytest
cd web && npm run build
```

More technical docs live in `server/docs/`.
