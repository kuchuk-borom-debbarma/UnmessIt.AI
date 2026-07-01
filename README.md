# UnmessIt.AI

UnmessIt.AI is a RAG notes app that runs locally for now. Save messy notes, organize them with directories and tags, and ask questions backed by source chunks and citations.

## What It Does

- Stores notes, nested directories, tags, user config, and durable ingest state in SQLite.
- Builds source chunks, recall keys, recall links, and Chroma vectors from saved notes.
- Answers questions from source chunks only, with citations and retrieval traces.
- Lets retrieval include or exclude directory subtrees.
- Runs ingest as durable background jobs that can retry, pause, resume, and survive restarts.
- Uses Redis in Docker for cross-process events and SSE fanout.
- Supports ordered OpenAI-compatible config presets for per-job/request failover.

## Local Install

For now, the supported install path is a local Docker install on your machine.
The installer runs the web app, API server, Redis, SQLite data, and vector data
locally.

**Mac / Linux**

```bash
bash <(curl -s https://raw.githubusercontent.com/kuchuk-borom-debbarma/UnmessIt.AI/staging/scripts/install.sh)
```

**Windows PowerShell**

```powershell
iwr -useb https://raw.githubusercontent.com/kuchuk-borom-debbarma/UnmessIt.AI/staging/scripts/install.ps1 | iex
```

Open `http://localhost:2831`.

First run:

1. Sign up for a local account.
2. Create an OpenAI-compatible config preset in Settings.
3. Create notes.
4. Wait for indexing to finish.
5. Ask a question.

Your data lives in the install folder's `data` directory. Re-running the
installer updates images and restarts containers without deleting notes,
vectors, or config as long as that folder remains.

Docker installs run Redis for event delivery and SSE fanout. Manual backend runs can leave `REDIS_URL` unset to use in-memory delivery.

If the UI looks stale after an update, hard refresh the browser (`Cmd+Shift+R` on macOS, `Ctrl+F5` on Windows/Linux). New commits may also take a few minutes to publish as Docker images.

## Self-Hosting

You can self-host the same stack anywhere Docker Compose runs. The stack has
three runtime services:

- `web`: React frontend served by Nginx.
- `server`: FastAPI backend with SQLite-backed app data and ingest state.
- `redis`: Redis Streams for durable event delivery and Redis Pub/Sub for SSE fanout.

Use the production compose file:

```bash
curl -fsSLO https://raw.githubusercontent.com/kuchuk-borom-debbarma/UnmessIt.AI/staging/docker-compose.prod.yml
mkdir -p data
docker compose -f docker-compose.prod.yml up -d --pull always
```

Set a real secret before exposing the server:

```bash
JWT_SECRET="$(openssl rand -hex 32)" docker compose -f docker-compose.prod.yml up -d
```

Use a custom data directory:

```bash
UNMESSIT_DATA_DIR="$HOME/unmessit-ai/data" docker compose -f docker-compose.prod.yml up -d
```

Use custom ports:

```bash
SERVER_PORT=8080 WEB_PORT=3000 docker compose -f docker-compose.prod.yml up -d
```

The Docker web container proxies `/api` to the server, so remote browsers can use `http://<host-ip>:<WEB_PORT>` without a baked-in localhost API URL.

For host-local model servers such as LM Studio, Docker rewrites loopback preset URLs like `http://127.0.0.1:1234/v1` to `http://host.docker.internal:1234/v1`. See [Docker Networking](./server/docs/DOCKER_NETWORKING.md).

For custom domains, set the API and CORS values directly:

```bash
CORS_ORIGINS="https://my-frontend.com" VITE_API_BASE_URL="https://api.my-backend.com" docker compose -f docker-compose.prod.yml up -d
```

Keep Redis reachable by the server as `REDIS_URL=redis://redis:6379/0` when
using the bundled compose network. If you run Redis separately, point
`REDIS_URL` at that instance.

## Cloud

Managed cloud hosting is future work. Today, use the local installer or
self-host the Docker Compose stack.

## Development

Backend:

```bash
cd server
cp .env.example .env
uv sync
uv run python -m src.main
```

Set `REDIS_URL=redis://localhost:6379/0` for manual multi-process event/SSE testing. Leave it unset for simple local development.

Frontend:

```bash
cd web
npm install
npm run dev -- --host 127.0.0.1
```

Build local Docker images:

```bash
git pull origin staging
docker compose build
docker compose up -d
```

## Docs

- [Current State](./current-state.md)
- [Server docs](./server/docs/)
- [Codebase rules](./server/docs/rules/codebase_rules.md)
