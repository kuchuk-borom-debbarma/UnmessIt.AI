# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.4] - 2026-07-02

### Added
- Indexing jobs now sort by actionability: running jobs first, then queued/retry, failed/paused/stopped work, and completed jobs last.
- The app shell now shows the current signed-in user and a direct release history entry point.
- Release history now has a cleaner version timeline in the frontend modal.

## [0.0.2] - 2026-07-02

### Added
- Added a staging release gate for PRs into `staging`.
- The gate requires `web/package.json` to increment beyond `origin/staging`.
- The gate requires `CHANGELOG.md` changes and release notes for the new version.
- CI regenerates `web/public/version.json` from `web/package.json` and `CHANGELOG.md`.
- `web/public/version.json` is now generated in CI/build instead of being manually maintained.
- Release history now includes changelog entries for every version in the frontend metadata.
- Documented the GitHub branch protection settings needed to block direct commits to `staging`.

## [0.0.1] - 2026-07-01

Welcome to the first version of **UnmessIt.AI**! This initial release brings a comprehensive suite of features designed to help you store messy text and get answers grounded in your exact saved sources.

### User Authentication & Accounts
- **Local Auth System**: Secure username/password authentication using JWT bearer tokens.
- **Data Isolation**: Total privacy—your notes, tags, and AI processing settings are strictly isolated to your account.

### Notes & Organization
- **Robust Notes Management**: Create, edit, and manage your text-based notes easily.
- **Directory Structures**: Organize your knowledge base using hierarchical folders.
- **Tagging System**: Tag your notes for flexible categorization.
- **Trash & Recovery**: Soft-delete notes into a Trash bin, with the ability to restore them or permanently delete them. Vectors are instantly synced (moved out of AI context when trashed, and back in when restored).

### AI Ingestion & Processing
- **Automated Processing**: Saving a note automatically kicks off background ingestion that extracts chunks, summarizes them, and generates reusable "Recall Keys" (topics, entities, events, etc.).
- **Durable Jobs System**: Background jobs are persistent. You can monitor their progress, pause, stop, or resume them directly from the **Jobs UI**.
- **Lossless Source Chunks**: We don't overwrite your data. AI chunks map exactly back to the spans of text you wrote.
- **Note Insights**: Dive into any note to see exactly what "Recall Keys" the AI generated for it.

### Ask AI (Retrieval)
- **Source-Backed Answers**: Ask questions and get answers explicitly grounded in your notes.
- **Citations & Transparency**: Every answer includes clickable citations linking to the exact chunk of your note it pulled from.
- **Retrieval Analysis Trace**: Expand the trace to see exactly how the AI broke down your query, searched the vector database, and ranked the results.
- **Cross-Domain Filtering**: Focus your query! Tell the AI to *only* search within specific folders or tags, or strictly exclude them.

### AI Settings & Configuration
- **Bring Your Own AI**: Connect directly to OpenAI by adding your own API key and model names.
- **Fallback Rotation**: Configure multiple AI presets. If one fails during a job, UnmessIt automatically rolls over to the next one.
- **Advanced Knobs**: Tech-savvy users can fine-tune chunk sizes, overlap, and retry backoffs.

### User Interface
- **Built-in Versioning**: A sleek global update banner and this very Release History modal to keep you in the loop.
- **Dark Mode Aesthetic**: A highly polished, responsive design utilizing framer-motion animations and debounced loading states.

### Infrastructure Reliability
- **Redis Runtime For Docker**: Docker installs now include Redis and set `REDIS_URL=redis://redis:6379/0` automatically. Manual backend runs can leave `REDIS_URL` unset and keep the old in-memory event/SSE behavior.
- **Transactional Event Outbox**: Note lifecycle changes and ingest job updates write durable SQLite outbox rows alongside the state changes that caused them. If Redis is down, events stay pending and retry when the dispatcher recovers.
- **At-Least-Once Domain Events**: Cross-process domain events are delivered through Redis Streams with the `unmessit:server` consumer group. Consumers acknowledge messages only after handlers succeed.
- **Persistent Idempotency**: Event handlers record completed `(event_id, handler_name)` pairs in SQLite, so Redis redelivery or duplicate stream entries do not repeat completed handler work.
- **Redis SSE Fanout**: Server-Sent Events now scale across multiple API processes with Redis Pub/Sub. Live SSE sockets stay process-local, while each instance forwards Redis topic events only to local subscribers.
- **SSE Connection Presence**: Redis stores short-lived connection presence records with instance id, connection id, topic, and last-seen timestamp. This supports observability and future routing without trying to move live HTTP connections between processes.
- **Docker And Installer Updates**: Compose files, Bash installer, and PowerShell installer were updated to start Redis, preserve `REDIS_URL`, and keep data in persistent Docker volumes.
- **Redis Documentation**: Added dedicated Redis event/SSE documentation plus updated durability, SSE, runtime config, README, and codebase rules docs.
- **Repository Cleanup**: Removed stale root patch scripts and generated log files from the tracked repository, and ignored future `*.log` and generated codebase-memory artifacts.
