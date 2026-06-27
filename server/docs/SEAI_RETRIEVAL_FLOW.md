# SEAI Retrieval Flow

SEAI retrieval answers questions from source-backed evidence created by `SEAI_INDEXING_FLOW.md`. Temporal memory subjects add a subject-first path for broad accumulated-context questions while keeping final answers cited to raw source spans.

Retrieval flow:

```txt
query
-> broad/narrow detection
-> subject resolution when useful
-> linked evidence fetch
-> vector and lexical search
-> evidence cards
-> rerank
-> quote bank
-> cited answer
-> citation validation
```

## Retrieval Modes

Narrow questions can usually be answered from direct vector or lexical matches over atoms and episodes.

Broad questions may need evidence that is distributed across many inputs. For these, retrieval should first try to resolve likely memory subjects, then fetch a capped set of linked evidence before merging that with normal search results.

Examples of broad intent include:

- Asking what is happening with a recurring subject.
- Asking for development, status, patterns, or open questions.
- Asking about a subject that appears across several inputs.
- Asking for a timeline or current state.

## Broad Retrieval

Broad Retrieval is the subject-aware path for accumulated-context questions. It can use subject resolution, linked evidence fetch, vector search, and lexical/entity sweep before reranking evidence into the quote bank.

## Subject Resolution

Subject resolution maps a query to likely memory subjects by using subject names, aliases, summaries, recent activity, and existing search terms. It is a retrieval aid, not evidence.

If no useful subject is found, retrieval falls back to the normal SEAI path:

```txt
query -> planner -> vector/lexical search -> rerank -> quote bank -> cited answer
```

If subjects are found, retrieval fetches linked episodes and atoms for those subjects, then ranks and caps them before answer generation.

## Query Planner JSON

The query planner still returns structured JSON for search intent, answer style, search queries, must-find items, and constraints. Planner output guides subject resolution, vector search, lexical/entity sweep, and follow-up search. It is not evidence.

## Linked Evidence Fetch

Subject links narrow the search space. They must not cause retrieval to load every memory attached to a subject.

For each resolved subject, fetch a limited set of evidence using:

- recent links by `created_at`
- clear `event_time` matches when the query asks about a time period
- high-confidence links
- useful relation labels such as `decision`, `problem`, `status`, `event`, `question`, or `change`
- older milestone links when they give important context

The default broad-answer shape is recent state plus important milestones. Strict chronological output should be used when the query asks for a timeline or history.

## Evidence Cards

Retrieval uses compact evidence cards for atoms and episodes.

Atom cards carry:

- atom id
- episode id
- raw input id
- atom role
- annotations
- source evidence text
- spans
- optional subject-link metadata

Episode cards carry:

- episode id
- raw input id
- neutral summary
- source span snippets
- optional subject-link metadata

Subject summaries may be included only as non-citable hints. They are never enough to support a final factual claim.

## Reranker JSON

The reranker receives the question, planner output, and evidence cards. It returns selected evidence ids, scores, missing aspects, optional follow-up queries, and whether there is enough evidence. Unknown or duplicate evidence ids are ignored.

## Ranking And Context Budget

The final answer context must stay compact. Retrieval should combine subject-linked evidence with vector and lexical candidates, dedupe them, rerank them, and pack only the strongest quote-bank evidence.

Ranking should prefer:

- direct relevance to the query
- source-backed atoms over broad summaries
- recent evidence for current-state questions
- milestone evidence for broad status questions
- relation atoms for why/how questions
- diverse raw inputs when a subject has many repeated links

## Quote Bank

The answer generator receives a quote bank, not the whole database.

Quote-bank rules:

- Every citable block must come from an atom evidence span or episode span.
- Subject names, aliases, summaries, and link reasons are hints only.
- The answer model must cite quote ids and copy exact quote text.
- Context should fit the configured budget instead of expanding with subject size.

## Citation Validation

The answer response keeps the public shape:

```json
{
  "answer": "...",
  "citations": [],
  "retrieval_trace": {}
}
```

Every citation must validate against raw source text through the selected atom or episode spans. If validation fails, retrieval may retry with stricter quote-bank context. If citations still fail, the system should return no sourced answer rather than invent support.

## Trace Expectations

`retrieval_trace` should make broad retrieval inspectable without exposing full raw prompts or full source text. Useful trace fields include:

- normalized query
- broad query flag
- resolved subject ids
- subject evidence counts
- selected evidence ids
- quote bank ids
- context character count
- answer retry flag

## Scale Behavior

Memory subjects are indexes, not answer context. A subject with many links should be searched and sampled, not fully loaded.

The scale rule is:

```txt
find likely subjects -> fetch capped linked evidence -> rerank -> cite raw spans
```

This keeps broad retrieval useful as the knowledge base grows.

## Partial Or Conflicting Evidence

Retrieval should answer only what the cited evidence supports. If evidence is incomplete, stale, or conflicting, the answer should say so plainly. This enhancement does not require global contradiction resolution.

## Not Implemented

The current system does not include full graph traversal, rolling summaries, autonomous tool routing, durable retrieval workflows, or a contradiction engine.
