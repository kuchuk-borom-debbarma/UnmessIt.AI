# Prompt Rules

These rules apply to every prompt in the codebase. They are intentionally general because user input can be any kind of text: notes, logs, fiction, research, conversations, tasks, records, plans, observations, pasted documents, or mixed fragments.

Prompts should be boring, standard, explicit, and portable across domains. A good prompt defines the task, the allowed inputs, the output contract, and the grounding rules without smuggling in assumptions about what the user data is.

## 1. General Standard

- One prompt should do one job.
- State the task in plain language.
- State what the model may use as evidence.
- State what the model must not infer.
- State the exact output format when code depends on it.
- Keep prompts domain-neutral unless the source or feature is explicitly domain-specific.
- Prefer short, direct instructions over long explanation.
- Avoid clever prompt tricks, hidden roleplay, or fragile phrasing.
- Do not ask for chain-of-thought or hidden reasoning.

## 2. Domain Neutrality

- Assume the input may be any genre, topic, or structure.
- Do not assume the input is a project, journal, meeting, research note, character analysis, code log, or personal memory.
- Do not privilege one subject type such as people, projects, places, stories, tasks, or research topics.
- Use general words: source, input, item, subject, evidence, claim, relation, time, context.
- Use broad labels and allow `other` when a source does not fit cleanly.
- Do not normalize messy input into a cleaner domain model than the source supports.
- Examples in production prompts should be avoided unless they are generic and necessary to explain the output shape.

## 3. Prompt Structure

- Put durable behavior rules in the system message.
- Put task data, source text, candidate lists, and schemas in the user/human message.
- Keep schemas small and stable.
- Use explicit field names that match downstream code.
- Separate instructions from data with clear labels.
- Mark whether each data block is source evidence, metadata, context, hint, or candidate data.
- Do not mix prose instructions into JSON data blobs.

## 4. Output Contracts

- If code expects JSON, the prompt must say `Return only valid JSON`.
- If markdown would break parsing, say `No markdown`.
- Required keys must be named explicitly.
- Optional fields should use `null` when the downstream schema expects the key.
- Cap outputs that can grow: queries, subjects, links, evidence ids, citations, bullets, or extracted claims.
- Do not ask for prose and machine-readable JSON in the same response.
- Do not rely on the model to enforce validity alone; code must still validate and normalize.

## 5. Grounding

- Prompts must define what counts as evidence.
- Extraction prompts must require exact source text, source ids, or another verifiable pointer.
- Answer prompts must distinguish citable evidence from hints or metadata.
- The model must preserve uncertainty from the source.
- The model must not invent missing facts, hidden motives, long-term patterns, or global conclusions.
- If the source is incomplete, the output should stay partial instead of filling gaps.
- If the source conflicts, the output should name the conflict rather than resolve it without evidence.

## 6. Scope Control

- Prompts must respect the user's scope qualifiers.
- Time qualifiers such as `early`, `initial`, `before`, `after`, `recent`, `current`, `timeline`, and `over time` must constrain selection and synthesis.
- Subject qualifiers must constrain selection and synthesis.
- If out-of-scope evidence is useful only for contrast, the model should treat it as contrast, not as the main answer.
- Broad questions need coverage across relevant evidence, not a dump of everything.
- Narrow questions should prefer direct evidence over broad background.

## 7. Concision And Context Budget Safety

- Prompts must stay small enough for configured OpenAI context windows.
- Do not pass full raw inputs when compact summaries, ids, or selected snippets are enough.
- Trim candidate lists before prompting.
- Cap generated objects before increasing model limits.
- Avoid large embedded examples.
- Prefer deterministic code validation over longer prompt explanations.
- When a prompt repeatedly hits context or output limits, reduce input/output size first.

## 8. Robustness

- Prompt failures should have deterministic fallback behavior when possible.
- Never let a derived prompt step destroy or block already-saved source data unless the feature explicitly requires it.
- Prompts should work with weaker JSON-following models.
- Avoid instructions that depend on subtle wording or model-specific behavior.
- Keep prompt changes covered by small tests when they protect an important contract.

## 9. Logging And Safety

- Do not log full prompts, full source text, full model responses, secrets, tokens, or API keys.
- Logs may include ids, counts, short previews, span ranges, and error categories.
- If a prompt handles sensitive or arbitrary user text, assume logs may be inspected later and keep them minimal.

## 10. Applying These Rules Here

- Source chunks, recall keys, recall links, retrieval plans, rerank decisions, and cited answers must follow the general rules above.
- Raw input is source evidence.
- Source chunk summaries, recall key summaries, aliases, link reasons, and retrieval hints are metadata or hints, not factual authority.
- Final answers must cite citable source spans, not metadata.
- Recall keys are general recall structures for reusable user-specific things, not a domain-specific model.
- Retrieval prompts should select evidence that matches the user's subject and time scope before broader context.

## 11. Test Expectations

- Test behavior or contract-critical phrases, not entire prompt snapshots.
- Add a small test when a prompt rule prevents a known failure mode.
- Prefer testing normalized output and fallback behavior over brittle wording checks.
