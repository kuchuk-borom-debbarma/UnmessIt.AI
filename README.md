# UnmessIt.AI

UnmessIt.AI is a local-first app for turning evolving user input into a searchable, source-backed knowledge memory.

Users can keep adding arbitrary text over time. The app preserves the original input, structures it into source-bound evidence, and answers later questions using citations back to what was actually stored.

## What It Does

- Saves raw user input as the source of truth.
- Splits messy input into source-bound episodes.
- Extracts small standalone atoms from episodes.
- Builds lightweight memory subjects for recurring concepts.
- Tracks temporal links between subjects and evidence.
- Lets users ask questions over accumulated input.
- Returns answers with citations back to stored source text.

## Why It Exists

Simple search works when the question is narrow:

> What did I say about the deadline?

Accumulated knowledge is harder. A useful answer may need to connect material added at different times, under different wording, and at different levels of detail.

> What is going on with this?

For that kind of question, the app should identify the recurring subject, gather relevant evidence across stored inputs, include recent and important earlier context, and answer only from cited source text.

## Core Idea

UnmessIt.AI treats raw input as the authority and builds indexes around it:

```txt
raw input
-> episodes
-> atoms
-> memory subjects and temporal links
-> retrieval with citations
```

Memory subjects are lightweight recall nodes for recurring things in the user's knowledge base. A subject may represent any useful recurring concept: a person, place, project, theme, question, decision, problem, event, story, research topic, or something else specific to the user's input.

Subjects are not factual authority. They help retrieval find relevant source-backed evidence. Final answers still cite raw episode or atom spans.

## Current Status

The app currently has:

- A FastAPI backend for ingestion and retrieval.
- A React frontend for entering text, asking questions, and inspecting stored evidence.
- SQLite storage for raw inputs, episodes, atoms, and legacy compatibility data.
- Chroma vector search over source-backed retrieval material.
- Source-backed answer generation with citation validation.
- Developer views for inspecting raw inputs, episodes, atoms, and retrieval traces.

Temporal memory subjects are implemented as a derived index that connects recurring subjects to evidence over time so broad questions can retrieve from the accumulated record without loading everything at once.

## Design Notes

- Raw source text remains the source of truth.
- Episodes and atoms provide citable evidence.
- Memory subjects organize recurring material.
- Temporal links help retrieval distinguish recent state, milestones, and historical context.
- Retrieval should fetch capped relevant evidence, not every memory attached to a subject.
