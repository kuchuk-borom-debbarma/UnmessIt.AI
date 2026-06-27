# UnmessIt.AI

UnmessIt.AI is a local-first app for turning messy user input into a searchable, source-backed knowledge base.

Users can keep adding notes, ideas, research, logs, character analysis, project context, or any other text over time. The app preserves the original input, structures it into smaller useful pieces, and answers later questions using evidence from what the user has stored.

## What It Does

- Saves raw user input as the source of truth.
- Breaks long or messy text into smaller connected pieces.
- Extracts useful points from those pieces.
- Lets users ask questions over everything they have added.
- Returns answers with citations back to the stored source text.

## Why It Exists

Most search works well when the question is narrow:

> What did I say about the deadline?

But real user knowledge often builds up slowly across many separate inputs. A broad question may need many pieces to be connected first:

> What is going on with this project?

For that kind of question, the app should gather related notes from different times, connect repeated themes, include open issues, and answer from the combined evidence instead of only the closest few matches.

## Core Challenge

UnmessIt.AI is not built around one fixed topic or one-time upload. It is an evolving knowledge base.

The main challenge is broad-topic recall: users may ask about a person, place, project, idea, pattern, or situation that appears across many separate chunks and references. A good answer must find enough of those pieces, group them, and form a useful response without losing the link back to the original text.

## Current Status

The app currently has:

- A backend server for ingestion and retrieval.
- A frontend for entering text and asking questions.
- Local storage for raw inputs and extracted knowledge.
- Vector search for finding semantically related material.
- Source-backed answer generation with citations.
- Developer views for inspecting stored inputs, extracted pieces, and retrieval traces.

The next major product problem is improving broad questions so the app can reliably answer from the whole relevant stored record, not just a small slice of it.

