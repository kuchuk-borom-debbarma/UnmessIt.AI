# Development Scripts

This folder contains developer-only scripts for running UnmessIt.AI from the
working tree. They are not the user installer; use `scripts/install.*` for that.

## Scripts

- `run.sh` / `run.ps1`: run the frontend and backend directly on your machine.
- `run-local.sh` / `run-local.ps1`: build and run the full Docker Compose stack from local source.

## Bare-Metal Development

Use this when you want fast frontend/backend reloads while editing code.

Prerequisites:
- Node.js dependencies installed in `web`.
- Python dependencies installed in `server`.
- Docker available if you want Redis-backed events/SSE locally.

**Mac/Linux:**

```bash
./scripts/dev/run.sh
```

**Windows:**

```powershell
.\scripts\dev\run.ps1
```

These scripts will:
- Start the Vite web client on `http://localhost:2831`.
- Start the Uvicorn backend on `http://localhost:2317`.
- Start a local Redis container for Redis Streams/SSE when Docker is available.
- Display all backend logs directly in your terminal.
- Stop both services cleanly when you press `Ctrl+C`.

If `REDIS_URL` is already set, the scripts use it. Otherwise Redis starts on
`redis://localhost:6381/0`. Override the port with `UNMESSIT_DEV_REDIS_PORT`.
If Docker is unavailable, the backend falls back to in-memory events/SSE.

Example:

```bash
UNMESSIT_DEV_REDIS_PORT=6382 ./scripts/dev/run.sh
```

## Local Docker Development

Use this when you want the local app to behave like the published Docker
install, but with images built from your current checkout.

**Mac/Linux:**

```bash
./scripts/dev/run-local.sh
```

**Windows:**

```powershell
.\scripts\dev\run-local.ps1
```

These scripts will:
- Automatically detect any existing `.env` files and use them.
- Build the `unmessit-ai` images from your local `Dockerfile`s.
- Start the web, server, and Redis containers in the background using Docker Compose.

To stop the local Docker containers, run:

```bash
docker compose down
```

## Which One Should I Use?

Use `run.sh` / `run.ps1` for normal development. Use `run-local.sh` /
`run-local.ps1` when you are testing Dockerfiles, compose wiring, installer
behavior, or production-like networking.
