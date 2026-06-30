<div align="center">
  <img src="./resources/logo.svg" alt="UnmessIt.AI Logo" width="120" />
</div>

# UnmessIt.AI

UnmessIt.AI is your Personal RAG AI. It turns your messy, scattered notes into a reliable knowledge engine. 

Stop digging through folders to find what you wrote weeks ago. Just dump your notes, organize them how you like, and ask natural-language questions. UnmessIt uses Retrieval-Augmented Generation (RAG) to instantly synthesize exact answers directly from your notes. You can restrict the AI's search to specific directories, or ask across everything—fully backed by citations you can trust.

## Major Features

- **Multi-Hop Reasoning**: Ask complex questions. The engine traverses your cross-linked notes to piece together facts scattered across multiple documents.
- **Verifiable Truth**: No AI hallucinations. Every answer includes the exact source chunks and a full retrieval trace so you know exactly where the information came from.
- **Cross-Domain Filtering**: Granular control to filter your AI searches by specific directories. Query within or exclude entire subtrees, perfectly matching your organizational hierarchy.
- **Always Up to Date**: Live, event-driven ingest means new notes are indexed as soon as you save them. No waiting for batch jobs to run.
- **Flexible Organization**: Structure your knowledge your way. We don't force a new system—use unlimited nested directories and flexible tags to keep things organized.

## Minor Features

- **AI Presets**: Configure distinct presets with custom LLMs, embedding models, and chunking strategies per workspace/project.
- **Transparent Indexing**: Track the indexing progress of every note in real-time. See exactly when jobs are queued, running, or failed.
- **Durable Execution**: Long-running indexing jobs are checkpointed in SQLite, so they can gracefully pause and resume if an API provider times out.
- **Memory Inspection**: View exact source chunks and recall links generated from your notes to understand how the AI sees your data.

## Next

- **Tag Filtering**: Apply granular filtering to your AI searches using specific tags across your entire workspace.

## Later Down the Line

- **Cloud Platform**: A fully hosted cloud version of UnmessIt.AI for zero-setup, ubiquitous access to your knowledge base.

---

## Fast Start (Local Run)

Docker is the easiest way to get started:

```bash
docker compose up --build
```

Open your browser to:
```txt
http://localhost:2831
```

1. Sign up for a local account.
2. Open **Settings** and add an OpenAI API key preset.
3. Create a note.
4. Wait for it to index.
5. Filter the AI search scope to specific directories (optional).
6. Ask a question!

### Custom Configuration

*(Optional)* You can customize the server and web ports by setting the `SERVER_PORT` and `WEB_PORT` environment variables. They work out of the box and automatically configure CORS and API URLs:
```bash
SERVER_PORT=8080 WEB_PORT=3000 docker compose up --build
```
*(If you changed `WEB_PORT`, go to `http://localhost:<WEB_PORT>` instead)*

If you are deploying to a specific domain or need advanced networking configuration, you can also manually override `VITE_API_BASE_URL` and `CORS_ORIGINS` directly:
```bash
CORS_ORIGINS="https://my-frontend.com" VITE_API_BASE_URL="https://api.my-backend.com" docker compose up --build
```
## Manual Development

Backend (FastAPI):
```bash
cd server
cp .env.example .env
uv sync
uv run python -m src.main
```

Frontend (React/Vite):
```bash
cd web
npm install
npm run dev -- --host 127.0.0.1
```

For detailed API documentation and runtime configuration, refer to the [Current State](./current-state.md) and technical docs in `server/docs/`.
