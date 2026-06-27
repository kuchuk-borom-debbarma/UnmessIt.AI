# SEAI_INDEXING_FLOW

SEAI means **Source-bound Episode Atom Indexing**. It is the V1 indexing flow for UnmessIt.AI:

```txt
raw input -> episode -> atom
```

Raw input is the source of truth. The original text is stored unchanged before any LLM step. Episodes and atoms only point back to source spans; they never replace the raw text.

## Objects

**Raw input** is the exact user submission.

**Episode** is one meaningful topic, event, scene, thought, or note inside the raw input. Most short inputs create one episode. Messy inputs may create many episodes. One episode can have multiple source spans when the user starts a topic, changes topic, then returns to it later.

**Atom** is the smallest useful standalone memory statement inside an episode. V1 supports only:

- `direct`: directly expressed facts, events, states, preferences, plans, claims, or uncertainty.
- `relation`: local relationships inside the same episode, such as cause, contrast, sequence, dependency, example, or result.

Relation atoms replace atom links in V1. Instead of storing `atom A caused atom B`, SEAI stores a source-bound relation atom such as `The man's bad behavior explains why Amy punched him.`

Atoms should be complete standalone claims, not short labels. For example, prefer `The team believes the outage was caused by the database migration and plans to roll it back.` over `Database migration issue.`

Atom annotations should include useful generic retrieval themes when supported by the source, such as `topic`, `entity`, `time`, `place`, `event`, `action`, `belief`, `preference`, `goal`, `motivation`, `cause`, `consequence`, `contrast`, `relationship`, `status`, `uncertainty`, `plan`, `problem`, `decision`, and `evidence`.

## What V1 Does Not Add

SEAI V1 intentionally avoids atom links, entity tables, rolling summaries, contradiction tracking, global graph traversal, timeline indexes, and personality inference. These are useful later, but they make the first durable memory flow too complex.

Late chunking is not a good fit here. It can work for fixed documents, but UnmessIt.AI often receives small facts or messy incremental notes. Rechunking or re-embedding a larger document around every tiny insert would repeat expensive work.

Graph-only indexing is also not enough. Graphs get messy and expensive, and many memories are not naturally graph-shaped. Some are feelings, partial beliefs, notes, or source-grounded explanations.

A full hybrid system is attractive but too complex for V1. SEAI is the current balance: episode embeddings for broad context, atom embeddings for precise facts, relation atoms for local reasoning, and raw spans for evidence.

Future context engineering can reduce prompt size for huge episodes by passing only relevant spans and atoms to retrieval-time reasoning.

## Indexing Flow

1. Receive raw text.
2. Save raw input unchanged.
3. Split into source-bound episodes. Episodes may contain multiple raw spans.
4. Summarize each episode neutrally.
5. Extract direct and relation atoms from each episode.
6. Run an LLM verifier to reject unsupported, over-broad, uncertainty-dropping, or personality-inference atoms.
7. Run code checks: valid role, confidence threshold, complete standalone content, and exact evidence quote found in episode spans.
8. Save episodes and atoms.
9. Embed episodes and atoms.

## Retrieval Expectations

Retrieval embeds the question, searches atom and episode vectors, fetches matched atoms with their episodes and raw source spans, then asks the answer LLM to cite exact source quotes. Summaries help retrieval but are not citable evidence.

The full retrieval loop is documented in `SEAI_RETRIEVAL_FLOW.md`.

## Example

Input:

```txt
Amy punched a man because he was being an asshole. Later she apologized and left quietly.
```

Expected episode:

```txt
Text:
Amy punched a man because he was being an asshole. Later she apologized and left quietly.

Summary:
Amy punched a man after he behaved badly, then apologized and left quietly.
```

Expected atoms:

```txt
1. Amy punched a man.
   role: direct
   evidence: Amy punched a man
   annotations: event, action

2. The man behaved badly.
   role: direct
   evidence: he was being an asshole
   annotations: behavior, claim

3. The man's bad behavior explains why Amy punched him.
   role: relation
   evidence: because he was being an asshole
   annotations: cause, explanation

4. Amy apologized later.
   role: direct
   evidence: Later she apologized
   annotations: event, action

5. Amy left quietly.
   role: direct
   evidence: left quietly
   annotations: event, action
```

Do not create unsupported global/personality inferences:

```txt
Amy is violent.
Amy has anger issues.
Amy is protective.
Amy always reacts aggressively.
```
