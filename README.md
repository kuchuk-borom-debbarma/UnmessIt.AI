# UnmessIt.AI

UnmessIt.AI is an AI knowledge base for information that keeps growing.

Add notes, documents, research, logs, plans, decisions, story material, or messy thoughts over time. Later, ask AI questions and get answers grounded in what you saved.

## Why It Exists

Most knowledge tools treat information like a static folder of files. Real work is messier: ideas change, new details arrive, decisions evolve, and related notes may be spread across many inputs.

UnmessIt.AI is built for that kind of living knowledge base.

## What You Can Do

- Save text whenever you want.
- Ask questions about saved information.
- Get answers with source-backed citations.
- Inspect the original source behind an answer.
- Browse saved memory, related topics, and ingestion jobs.
- Use local or hosted AI model providers.

## App Screens

- **Ingest Journal**: paste text into the knowledge base.
- **Memory Explorer**: browse saved sources and related memory links.
- **Ask AI**: ask questions and inspect citations.
- **Database**: clear local development data when needed.

## Source-Grounded Answers

The app keeps your original input as the source of truth. AI-generated summaries and links help find relevant information, but answers are grounded in saved source text.

That means you can inspect where an answer came from instead of trusting a disconnected response.

## Model Providers

UnmessIt.AI can work with local or hosted model endpoints. Provider settings are currently configured through environment variables.

User-facing provider configuration is planned for a future version.

## Project Status

This is an active early-stage project. The current version focuses on reliable ingestion, source-backed retrieval, and inspection tools.

For engineering details, see:

- `current-state.md`
- `server/docs/`
