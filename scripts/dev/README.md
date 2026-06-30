# Development Scripts

This folder contains scripts intended for use by developers working on UnmessIt.AI.

## Quick Start (Run Bare-Metal)

If you have already installed the dependencies for the web client (Node.js) and the server (Python), you can start both the web client and the server simultaneously using the bare-metal run scripts. This is the fastest way to develop because you get immediate hot-reloading for both the frontend and the backend.

**Mac/Linux:**
```bash
./scripts/dev/run.sh
```

**Windows:**
```powershell
.\scripts\dev\run.ps1
```
These scripts will:
- Start the Vite web client in the background.
- Start the Uvicorn Python backend in the foreground.
- Display all backend logs directly in your terminal.
- Stop both services cleanly when you press `Ctrl+C`.

---

## Local Docker Development

If you prefer to run the application within Docker (to ensure your environment matches production exactly) without relying on published images, you can use the `run-local` scripts. These scripts build the Docker images directly from your local source code.

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
- Start the containers in the background using `docker compose`.

To stop the local Docker containers, run:
```bash
docker compose down
```
