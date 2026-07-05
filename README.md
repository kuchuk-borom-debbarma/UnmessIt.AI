# UnmessIt.AI
 
UnmessIt.AI is an AI-powered notes application. It helps you save messy, unstructured thoughts and query them later. You write the notes, and the AI connects the dots to answer your questions with precise citations.
 
## What You Can Do
 
- **Save Messy Notes**: Write in Markdown or Plain Text. Don't worry about structuring everything perfectly; just get your thoughts down.
- **Organize Your Way**: Group notes using nested directories and tags.
- **Ask AI Questions**: Ask questions across your entire knowledge base. The AI will read your notes and generate a comprehensive answer backed by actual citations.
- **Filter Your Search**: Tell the AI to only look inside specific folders or ignore certain tags when answering a question.
- **Use Any Model**: Configure UnmessIt.AI to work with self-hosted models via LM Studio, or point it to any OpenAI-compatible API.
 
## Quick Install
 
 The easiest way to get started is using the automated installer. It spins up the web app, API server, Redis, SQLite, and vector database automatically via Docker.
 
 **Mac / Linux**
 
 ```bash
 bash <(curl -s https://raw.githubusercontent.com/kuchuk-borom-debbarma/UnmessIt.AI/staging/scripts/install.sh)
 ```
 
 **Windows PowerShell**
 
 ```powershell
 iwr -useb https://raw.githubusercontent.com/kuchuk-borom-debbarma/UnmessIt.AI/staging/scripts/install.ps1 | iex
 ```
 
 Open `http://localhost:2831` (or your server's IP address).
 
 First run:
 
 1. Sign up for an account.
 2. Create an OpenAI-compatible config preset in Settings.
 3. Create notes.
 4. Wait for indexing to finish.
 5. Ask a question.
 
 Your data lives in the install folder's `data` directory. Re-running the
 installer updates images and restarts containers without deleting your notes,
 vectors, or configs.
 
 If the UI looks stale after an update, hard refresh the browser (`Cmd+Shift+R` on macOS, `Ctrl+F5` on Windows/Linux).
 
## Features

UnmessIt.AI goes beyond a simple chat interface, combining a robust application platform with a highly-optimized, heavily engineered AI backend.

### User-Facing Features
- **Complete Data Privacy**: Fully self-hosted Docker deployment ensures your personal notes and queries never leave your infrastructure unless you choose a public API.
- **Secure Multi-User Support**: Includes built-in JWT authentication so you can host the application on a server and create isolated accounts for your team or family.
- **Flexible Organization**: A materialized-path directory structure allows for infinitely nested folders, alongside a robust tagging system for quick filtering.
- **AI Config Rotation**: Setup multiple AI providers (e.g. OpenAI, LM Studio, Groq). If one fails or hits a rate limit during a heavy job, the system automatically falls back to your backup provider.

### Internal Engineering (Under the Hood)
- **Event-Driven Architecture (EDA)**: The application decouples fast UI interactions from heavy AI workloads using Redis Streams and background worker processes.
- **Transactional Outbox**: Guarantees that every note you save is queued for processing by wrapping the database insert and the event emission in a single, atomic SQLite transaction. Data is never lost.
- **Strict Idempotency**: Prevents the system from processing the same event twice. Even if a background worker crashes or restarts mid-job, your notes will never be double-indexed.
- **SSE Fanout Architecture**: Uses Redis Pub/Sub and a TTL heartbeat to instantly stream background progress (like indexing percentages) directly to your specific browser window, no matter which server instance you are connected to.
- **The RAG (Retrieval-Augmented Generation) Engine**:
  - **Recall Keys**: Instead of building a massive, rigid graph database, the system extracts lightweight "Recall Keys" (entities and topics) from your text. This implicitly links related notes together, bypassing the immense overhead of standard Graph RAG.
  - **Resilient LangGraph Processing**: Indexing happens via a durable state-machine in the background. If you close the app or hit an API limit, the system safely checkpoints its progress and resumes exactly where it left off.
  - **Multi-Strategy Querying**: When you ask a complex question, the AI breaks it down into sub-queries and executes Vector Search (dense meaning), Lexical Search (exact words), and Recall Key expansion simultaneously to gather the best evidence.
  - **Aggressive Caching**: UnmessIt.AI utilizes exact memory caches and semantic vector caches. If you ask a question that is semantically similar to a previous one, an internal verifier ensures it's safe to reuse, then instantly returns the cached answer to save time and API costs.
 
## Other Ways to Use UnmessIt.AI
 
### Self-Hosting (Docker Compose)
 
 You can manually self-host the stack anywhere Docker Compose runs using the production compose file:
 
 ```bash
 curl -fsSLO https://raw.githubusercontent.com/kuchuk-borom-debbarma/UnmessIt.AI/staging/docker-compose.prod.yml
 mkdir -p data
 ```
 
 Set a real secret before exposing the server:
 
 ```bash
 JWT_SECRET="$(openssl rand -hex 32)" docker compose -f docker-compose.prod.yml up -d
 ```
 
 Use custom ports or data directories:
 
 ```bash
 UNMESSIT_DATA_DIR="$HOME/unmessit-ai/data" SERVER_PORT=8080 WEB_PORT=3000 docker compose -f docker-compose.prod.yml up -d
 ```
 
 For host-local model servers such as LM Studio, Docker rewrites loopback preset URLs like `http://127.0.0.1:1234/v1` to `http://host.docker.internal:1234/v1`. See [Docker Networking](./server/docs/deployment/DOCKER_NETWORKING.md).
 
### Development
 
 Backend:
 ```bash
 cd server
 cp .env.example .env
 uv sync
 uv run python -m src.main
 ```
 *(Set `REDIS_URL=redis://localhost:6379/0` for manual multi-process event/SSE testing. Leave it unset for simple local development).*
 
 Frontend:
 ```bash
 cd web
 npm install
 npm run dev -- --host 127.0.0.1
 ```
 
 Build Docker images locally:
 ```bash
 git pull origin staging
 docker compose build
 docker compose up -d
 ```

### Cloud
Managed cloud hosting is future work. Today, use the installer script or self-host the Docker Compose stack.
 
## Docs
 
 - **[Architecture Novel (The Deep Dive)](./server/docs/architecture/ARCHITECTURE_DEEP_DIVE.md)**
 - **[Current State](./current-state.md)**
 - [All Server docs](./server/docs/)
