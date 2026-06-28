# UnmessIt.AI

UnmessIt.AI is an AI RAG-powered knowledge base for information that keeps growing.

People can type or paste their own notes, stories, research, logs, plans, decisions, or messy thoughts into the app. Later, they can ask AI about that knowledge base and get answers grounded in the stored source text.

Traditional RAG usually assumes a mostly static document set: upload files, index them, ask questions. UnmessIt.AI is built for evolving input. Users keep adding new data over time, and the system updates its searchable memory as that data arrives.

## What Users Can Do

- Add arbitrary text whenever they want.
- Keep the original input as the source of truth.
- Ask simple factual questions about stored information.
- Ask broader questions that need multiple source chunks.
- Ask timeline or connection-style questions where the answer needs related evidence.
- Inspect the stored source chunks and recall links behind an answer.
- Use configurable model providers, API keys, base URLs, and local or hosted model endpoints.

## How It Works

The app stores user input as source-backed memory:

```txt
user input
-> source chunks
-> recall keys
-> recall links
-> vector indexes
```

Source chunks are citable slices of the original input. Recall keys are reusable handles for things the user may ask about later: people, topics, events, tasks, questions, places, projects, or anything else in the user's data. Recall links connect those keys back to the source chunks that mention, update, support, or otherwise relate to them.

When a user asks a question, retrieval searches source chunks directly, searches recall keys, expands through linked source chunks, and answers from the source chunks.

```txt
question
-> source chunk search
-> recall key search
-> linked source chunk expansion
-> cited answer
```

This makes basic questions possible through direct source search, while broader questions can use the recall structure to pull together related pieces of evidence.

## Why The Index Matters

UnmessIt.AI does not treat recall keys or summaries as truth. They are navigation structures.

The source text remains the authority. Recall keys and recall links help the system find the right source chunks for questions like:

- "What did I decide about this project?"
- "How did this idea change over time?"
- "Write the timeline from this person's beginning to their ending."
- "What connects these two topics?"
- "What do I know about this thing so far?"

Broad answers work because the index connects related chunks instead of relying only on one nearest vector match.

## Current Product Shape

The current app has:

- A React UI for ingesting text, asking questions, and inspecting saved memory.
- A FastAPI backend for ingestion, retrieval, and dev inspection routes.
- Durable ingestion so partially completed jobs can resume.
- SQLite storage for raw inputs, source chunks, recall keys, and recall links.
- Chroma vector indexes for source chunks and recall keys.
- Configurable LLM and embedding providers through environment settings.

Future iteration: add one broad raw-input summary for large inputs before considering recursive summary trees.
