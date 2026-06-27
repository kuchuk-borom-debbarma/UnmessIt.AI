# SEAI Indexing Flow

SEAI means **Source-bound Episode Atom Indexing**. It turns evolving user input into source-backed retrieval material while preserving the original text as the authority.

SEAI includes a derived temporal memory subject layer:

```txt
raw input
-> source windows
-> episodes
-> atoms
-> memory subjects and temporal links
-> vector index
```

Raw input remains the source of truth. Episodes, atoms, memory subjects, and links are indexes over that source. They help retrieval find and organize evidence; they do not replace the original text.

## Objects

**Raw input** is the exact user submission. It is saved before LLM work so all later spans point back to durable source text.

**Source window** is a bounded slice of raw input used to keep episode splitting practical for local and cloud models.

**Episode** is one meaningful unit inside a raw input. It can describe any kind of user-provided material: a fact, event, question, plan, observation, scene, concern, preference, or partial thought. One episode may point to multiple raw spans when the same subject appears in separate parts of one input.

**Atom** is a small standalone claim extracted from an episode. Atoms must stay source-supported and understandable without rereading the whole episode.

Atom roles:

- `direct`: directly expressed facts, events, states, preferences, plans, claims, or uncertainty.
- `relation`: local relationships inside the same episode, such as cause, contrast, sequence, dependency, example, or result.

**Memory subject** is a lightweight derived node for a recurring thing the knowledge base needs to remember. A subject can be a concept, person, place, project, theme, question, decision, problem, event, story, research topic, or another user-specific subject. Subjects are domain-neutral by design.

**Memory subject link** connects a subject to source-backed evidence: an episode and, when useful, a specific atom. Links may carry relation and time metadata so retrieval can build a useful view without loading every linked memory.

## Temporal Links

Every subject link has `created_at`, the reliable time when the evidence was ingested.

Links may also have:

- `event_time`: a normalized time from the source text when the text clearly mentions one.
- `time_label`: the original time phrase when useful, such as `next month`, `June 2026`, or `yesterday`.

Mentioned times are best-effort metadata. Ingest time is always available and should be used as the fallback timeline order.

## Indexing Flow

1. Receive raw text.
2. Save raw input unchanged.
3. Split the input into source windows.
4. Split windows into source-bound episodes.
5. Summarize each episode neutrally.
6. Extract direct and relation atoms from each episode.
7. Verify atoms against episode text.
8. Run code checks for valid role, confidence threshold, standalone content, and exact evidence spans.
9. Save episodes and atoms.
10. Extract or match memory subjects for the new evidence.
11. Save subject links with relation and temporal metadata.
12. Embed episodes and atoms for vector search.

Subject extraction is a derived-index step. If it fails, the raw input, episodes, atoms, and vector index should still remain usable.

## Subject Matching

Subject matching should prefer reuse when a new note clearly refers to an existing subject by name, alias, summary, or recent linked evidence. If no appropriate subject exists and the concept is central to the input, create a new subject.

V1 should use moderate granularity:

- Create subjects for central or recurring concepts.
- Do not create a subject for every noun.
- Keep subject kinds broad and neutral.
- Update only simple subject metadata such as aliases, summary, and `updated_at`.

Subject summaries are orientation hints, not citable evidence.

## Source-Bound Rules

- Raw input is the authority.
- Episodes and atoms must point to raw spans.
- Atoms must preserve uncertainty from the source.
- Relation atoms describe local relationships only.
- Memory subjects and subject summaries must not introduce unsupported facts.
- Final answers cite raw episode or atom evidence, not subject metadata.

## Relationship To Retrieval

Broad Retrieval can use subjects to narrow the search space before evidence ranking. For example, a broad query may resolve to a small set of likely subjects, fetch a capped set of linked atoms and episodes, then combine that evidence with vector and lexical search.

The retrieval path may still use a lexical/entity sweep and a quote bank. The indexing job is to create complete standalone claims and source-bound episode evidence so retrieval can stay compact and cited.

The full retrieval design is documented in `SEAI_RETRIEVAL_FLOW.md`.

## Not In This Enhancement

This design does not require full graph traversal, contradiction resolution, durable job queues, production multi-user storage, or global summary engines. Those can be added later if the subject-link layer proves insufficient.
