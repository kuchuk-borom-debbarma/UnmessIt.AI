# SEAI_RETRIEVAL_FLOW

SEAI retrieval turns a user question into a compact, cited answer using the source-bound index created by `SEAI_INDEXING_FLOW.md`.

Indexing stays source-bound and local: raw input, episodes, atoms. Retrieval is allowed to be multi-pass because query needs vary. A "why" question may need relation atoms, a "what happened" question may need episode context, and a broad question may need several related memories.

## V1 Loop

```txt
question
-> normalize query
-> query planner
-> vector search atoms + episodes
-> broad query lexical sweep when needed
-> evidence cards
-> LLM reranker
-> optional follow-up search
-> quote-bank final context
-> cited answer
-> citation validation
```

The loop is capped at 3 rounds. It stops early when the reranker says the evidence is enough and no aspects are missing, when there are no new follow-up queries, or when no new evidence appears.

Incoming UI numbering is stripped before retrieval, so `21. What caused the outage?` is searched as `What caused the outage?`.

## Query Planner JSON

The planner reads the user question and returns:

```json
{
  "intent": "why_question",
  "answer_style": "concise",
  "search_queries": ["why Amy punched the man", "Amy man behaved badly"],
  "must_find": ["cause of Amy punching the man"],
  "constraints": ["use only source evidence"]
}
```

Planner output is not trusted as evidence. It only guides search.

Planner JSON is normalized before validation. If a local model returns a string or object where V1 expects a list, the server coerces it into list strings instead of discarding the whole plan.

## Broad Retrieval

Some questions are broad even when they look simple. Examples: worldview, development, relationship, overall, explain, tell me, or what was. For these, vector search alone can be too narrow.

Broad retrieval adds a cheap lexical/entity sweep over SEAI episodes and atoms using important query terms and planner terms. This is not evidence synthesis; it only adds candidate evidence cards. The reranker still chooses, and the answer still cites raw spans.

This keeps V1 deterministic and avoids LangGraph for now. LangGraph becomes useful later if retrieval needs real tool routing such as `vector_search`, `sql_entity_sweep`, `fetch_neighbors`, `compress_quotes`, and `answer_retry`.

## Evidence Cards

Retrieval searches both atoms and episodes. Results become compact evidence cards.

Atom card:

```json
{
  "evidence_id": "atom:<atom_id>",
  "object_type": "atom",
  "atom_role": "relation",
  "content": "The man's bad behavior caused Amy to punch him.",
  "episode_summary": "Amy punched a man because he behaved badly.",
  "evidence": "Amy punched a man because he behaved badly",
  "spans": [{"start": 0, "end": 42}]
}
```

Episode card:

```json
{
  "evidence_id": "episode:<episode_id>",
  "object_type": "episode",
  "summary": "Amy punched a man because he behaved badly.",
  "source_span_snippets": "SPAN 0-43:\nAmy punched a man because he behaved badly."
}
```

Atoms are used for precise statements. Relation atoms are boosted by the reranker for why/how questions. Episodes provide story context and broad recall.

## Reranker JSON

The LLM reranker receives the question, planner output, and evidence cards. It returns:

```json
{
  "selected_evidence_ids": ["atom:abc", "episode:def"],
  "scores": [
    {"evidence_id": "atom:abc", "score": 0.93, "reason": "directly explains cause"}
  ],
  "missing_aspects": [],
  "follow_up_queries": [],
  "enough_evidence": true
}
```

Unknown evidence IDs are ignored. Duplicate selections are deduped.

## Quote Bank And Context Budget

The final answer context is capped around 9000 characters.

Rules:

- Start with reranker-selected evidence.
- For broad questions or missing aspects, add only query-matching nearby/broad episode evidence before answering.
- Pack final context as a quote bank: evidence id, object type, non-citable hint, exact citable quote.
- Prefer exact atom evidence quotes over full episodes.
- For huge episodes, include only selected source span snippets.
- Episode summaries are allowed as hints but are marked non-citable.
- Citable text must come from atom evidence spans or episode source spans.

## Citation Validation

The answer model must return JSON with:

```json
{
  "answer_text": "...",
  "citations": [
    {
      "statement_id": "<atom_or_episode_uuid>",
      "source_input_id": "<raw_input_uuid>",
      "start_char": 0,
      "end_char": 43,
      "exact_quote": "Amy punched a man because he behaved badly."
    }
  ]
}
```

The server validates every citation against raw source spans. If citation validation fails, the answer step retries once with quote-bank-only strict context. If it still fails, the system returns no sourced answer.

## Partial Or Conflicting Evidence

SEAI retrieval should answer what the evidence supports and name gaps or uncertainty. It should not invent missing facts, resolve contradictions globally, or infer personality patterns.

## Example

Question:

```txt
Why did Amy punch the man?
```

Likely selected evidence:

```txt
[ATOM relation]
CONTENT (not citable): The man's bad behavior caused Amy to punch him.
EVIDENCE:
Amy punched a man because he behaved badly.
```

Answer:

```txt
Amy punched the man because he behaved badly.
```

Citation quote:

```txt
Amy punched a man because he behaved badly.
```

## Not In V1

V1 retrieval does not do graph traversal, atom links, global memory synthesis, contradiction resolution, rolling summaries, or long-term personality inference.
