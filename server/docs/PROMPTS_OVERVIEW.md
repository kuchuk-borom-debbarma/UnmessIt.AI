# Prompts Overview

This document outlines the core LLM prompts used within UnmessIt.AI. All prompts strictly adhere to the guidelines set forth in `server/docs/rules/prompt_rules.md`, maintaining domain-neutrality, precise JSON output contracts, and strict grounding requirements.

## 1. Source Chunk Summarization (`source_chunk_drafts.py`)

**Purpose**: Summarizes a single bounded text chunk and extracts salient entities (people, places, topics) to aid downstream retrieval.
**Type**: Ingestion
**System Prompt**:
```text
Summarize one source chunk and extract its main subjects. Return only JSON.
```
**Human Prompt**:
```text
Return JSON: {"summary":"short neutral summary","source_time":null,"metadata":{"salient_entities":["Subject 1","Subject 2"]}}
Do not omit details because the full SOURCE_TEXT is saved as the citable chunk.
Extract 2-8 of the most important people, places, topics, or events into salient_entities to aid later retrieval.

SOURCE_TEXT:
{window['text']}
```
**Rule Adherence**: 
- **Grounding**: Extracts metadata neutrally without overriding the actual `SOURCE_TEXT` which remains the only citable truth.
- **Output Contract**: Defines an exact JSON schema.
- **Domain Neutrality**: Uses general terms ("people, places, topics, or events").

---

## 2. Recall Key & Link Drafting (`recall/drafts.py`)

**Purpose**: Extracts structured knowledge relationships by identifying canonical entities/topics and linking them to specific source chunks. 
**Type**: Ingestion
**System Prompt**:
```text
Create recall keys and recall links for source chunks. Return only valid JSON. No markdown.
Use SOURCE_CHUNKS as source evidence. EXISTING_CANDIDATES are reuse hints, not source evidence.
Reuse existing_recall_key_id only when the candidate clearly matches. Create a new key only when no candidate clearly matches.
For reused keys, keep the candidate's identity broad: write summary as a stable merged orientation using the old candidate summary plus this new source evidence.
If the old summary is already good, repeat it instead of narrowing it to the latest chunk.
Canonical names must be clean, human-readable, and language-consistent; avoid mixed-script names unless the source itself uses them.
Prefer reusable keys a user may ask about later. Avoid tiny phrase-specific topic keys when a broader candidate fits.
Aim for 1-5 important recall keys per source chunk.
```
**Human Prompt**:
```text
Return exactly this JSON shape, with no markdown:
{
  "recall_keys": [
    {"ref":"k1","name":"canonical name","kind":"entity|topic|event|task|question|other","kind_label":"optional specific label","aliases":["alternate name"],"summary":"short hint"}
  ],
  "recall_links": [
    {"recall_key_ref":"k1","source_chunk_id":"exact id from SOURCE_CHUNKS","relation":"mentions|about|updates|contradicts|supports|other","relation_label":"optional specific relation","confidence":0.8,"reason":"short source-grounded reason"}
  ]
}
Every recall key must have a non-empty ref like k1, k2, k3.
Every recall link must use recall_key_ref that matches one recall key ref.
Every source_chunk_id must be copied exactly from SOURCE_CHUNKS.
Allowed kind: entity, topic, event, task, question, other.
Allowed relation: mentions, about, updates, contradicts, supports, other.

EXISTING_CANDIDATES:
{candidates}

SOURCE_CHUNKS:
{source_chunks}
```
**Rule Adherence**:
- **Output Contract**: Strictly defines allowed categories (entity, topic, event, etc.) and enforces `ref` mapping to ensure valid DAG construction.
- **Grounding**: Emphasizes that `EXISTING_CANDIDATES` are hints, not evidence, ensuring links are grounded only in the provided `SOURCE_CHUNKS`.
- **Scope Control**: Caps processing at `1-5 important recall keys`.

---

## 3. Query Decomposition (`query/_breakdown.py`)

**Purpose**: Breaks down a complex user query into smaller, focused sub-queries for parallel evidence retrieval.
**Type**: Retrieval (Graph Node)
**System Prompt**:
```text
Decompose the user query into focused sub-queries for evidence retrieval. Return only valid JSON. No markdown. Each sub-query must be self-contained and searchable on its own. Include the original query as the first item. Return at most 4 sub-queries. If the query is already simple and focused, return only the original query.
```
**Human Prompt**:
```text
QUERY:
{query}

Return JSON: {"sub_queries":["original query","sub-query 1","sub-query 2"]}
```
**Rule Adherence**:
- **Robustness**: The application is resilient; if the LLM fails to output valid JSON, it defaults back to `[query]`.
- **Concision**: Returns at most 4 sub-queries, preventing runaway retrieval budgets.

---

## 4. Implicit Subject Extraction (`query/_subjects.py`)

**Purpose**: Identifies subjects (entities, characters, places) that are implied by description (e.g., "the young officer") rather than named explicitly, allowing direct recall-key FTS lookups to succeed.
**Type**: Retrieval (Graph Node)
**System Prompt**:
```text
Identify the specific named entities (people, characters, places, items, concepts) that the query refers to by description rather than by explicit name. Use your general knowledge to resolve the descriptions into specific proper names whenever possible. If the query describes a subject (e.g., 'the man who...', 'the young officer', 'the company'), figure out who or what it is and return their exact name. Return only valid JSON. No markdown. Return at most 8 subjects. If every subject is already stated by explicit proper name in the query, return [].
```
**Human Prompt**:
```text
QUERY:
{query}

SUB_QUERIES:
{sub_queries}

Return JSON: {"subjects": ["subject name 1", "subject name 2"]}
```
**Rule Adherence**:
- **Domain Neutrality**: Mentions general groupings rather than project-specific nouns. 
- **Scope Control**: Caps subjects at 8.

---

## 5. Answer Generation & Citation (`query/__init__.py`)

**Purpose**: Synthesizes a final answer for the user strictly based on the provided source chunks, generating exact citations.
**Type**: Retrieval (Final Node)
**System Prompt**:
```text
Answer the user query using only SOURCE_CHUNKS. Return only valid JSON. No markdown. SOURCE_CHUNKS are the only evidence; recall metadata is not evidence. Each source chunk contains a summary and focused snippets from saved text. If the evidence is incomplete, say what is missing. For broad or timeline questions, combine relevant chunks in source/time order. Citations must be source_chunk ids from SOURCE_CHUNKS.
```
**Human Prompt**:
```text
QUERY:
{query}

SOURCE_CHUNKS:
{source_chunks}

Return JSON with keys: {"answer":"string","citation_ids":["source_chunk_id"]}
```
**Rule Adherence**:
- **Grounding**: Explicitly states `SOURCE_CHUNKS are the only evidence; recall metadata is not evidence` and enforces that the model must state what is missing if evidence is incomplete.
- **Output Contract**: Enforces JSON output with explicit fields.
- **Robustness**: The backend code silently filters out hallucinated citation IDs, keeping only valid ones.
