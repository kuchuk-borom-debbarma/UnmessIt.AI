# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.4] - 2026-07-02

### Added
- A redesigned landing page with an animated RAG demo flow for append-friendly indexing, source-grounded reasoning, inline citations, and cited-line navigation.
- Inline Ask AI citation chips that open cited-line popovers directly inside the answer and link into the matching source note span.
- Domain-neutral retrieval fan-out for attribute, comparison, and reasoning questions, including expanded recall-key lookup, lexical search, reranking, and snippet packing.
- A domain-neutral evidence verifier that filters off-scope chunks and can trigger one focused retry before answer generation.
- Depth-aware retrieval SSE progress events so Ask AI can show nested planning, search, verifier, retry, and answer steps.
- Independent LLM and embedding runtime lanes, each with its own single-config or rotation mode.
- Settings test buttons for LLM and embedding API configs, with frontend-visible API/provider error messages.
- Shared page hero, stat-card, toolbar, and segmented-tab patterns across the app's internal pages.
- Redis-backed runtime support for Docker installs, with manual backend runs still able to use in-memory events/SSE when `REDIS_URL` is unset.
- Transactional SQLite event outbox rows for note lifecycle and ingest job events, with Redis Streams delivery through the `unmessit:server` consumer group.
- Persistent handler idempotency rows so redelivered stream events skip completed handler work.
- Redis Pub/Sub SSE fanout and Redis-backed SSE connection presence records for future horizontal scaling.
- Docker Compose, installer, runtime configuration, and Redis/outbox/SSE documentation updates for the new Redis runtime path.
- Indexing jobs now sort by actionability: running jobs first, then queued/retry, failed/paused/stopped work, and completed jobs last.
- The app shell now shows the current signed-in user and a direct release history entry point.
- Release history now has a cleaner version timeline in the frontend modal.
- Note detail expand/collapse now reveals 400px per step instead of 200px.

### Changed
- Refreshed Notes, Jobs, Settings, Trash, Note Detail, and Note Insights with the same polished visual system as Ask AI while keeping layouts dense and operational.
- Rebalanced internal pages into compact glassmorphism surfaces with the Ask AI-style soft blurred background and less visual noise.
- Changed the retrieval flow to plan focused sub-queries, gather packed context, verify the context against the original query, optionally retry once, then answer from verified evidence.
- Changed broad multi-part retrieval to add generic clause-level sub-queries and preserve partial on-topic evidence instead of refusing the whole question.
- Changed Settings so LLM answer calls and embedding/indexing calls can use different active presets or different rotation orders.
- Improved retrieval prompts so answers can synthesize comparisons and reasoning from separate sourced facts without requiring the source to already contain the comparison.
- Improved lexical retrieval scoring and focused snippets so exact small details rank and cite better than generic matches.
- Expanded retrieval and prompt documentation for inline citations, source-backed synthesis, and deterministic query fan-out.
- Reworked the app shell and notes grid for a calmer, more stable UI with fewer persistent visual layers and less layout shifting.
- Reduced Notes view refresh work by separating full-directory loading from paginated note/folder loading and memoizing derived directory lookups.
- Cleaned repository-generated artifacts out of the tracked tree and ignored future local logs/codebase-memory outputs.

### Fixed
- Ask AI now handles broad comparison/reasoning questions when each side has separate supporting evidence.
- Ask AI now answers supported parts of an incomplete multi-part query and briefly names missing evidence instead of treating the whole query as unanswerable.
- Ask AI no longer rejects user-requested comparisons only because the subjects come from different contexts or sources.
- Ask AI now drops same-word but wrong-scope evidence before answering while still allowing cross-context reasoning when the query asks for it.
- Ask AI progress no longer renders raw details JSON in the terminal; it shows compact indented retrieval steps instead.
- Ask AI prompts no longer leak retrieval-internal labels such as `SOURCE_CHUNKS` into user-facing prose.
- Frontend API failures now distinguish provider/API failures, backend connection failures, and internal server errors.
- Settings API tests now reuse the saved secret when an edit-mode API key field is left blank.
- Ask AI now strips invalid or unavailable inline citation markers instead of showing raw `[[cite:...]]` text in answers.
- Inline citation popovers now layer above the answer area cleanly instead of hiding behind the Ask input or progress UI.
- Attribute-style questions now retrieve small exact details such as counts, labels, descriptors, and qualifiers more reliably.
- Focused snippets now keep numbered list evidence together so cited lines do not stop at markers such as `1.`.
- Cited note links now expand the source note enough to reveal the highlighted span and scroll gently for smaller screens.
- Jobs note links now open the note id associated with the ingest job instead of treating the job id as a note id.
- Corrected release history so each version only describes changes introduced in that version.
- Removed the misleading in-app update/reload button; update detection now points users to the GitHub repository instead of pretending to install updates.
- Hardened `scripts/dev/run.sh` so it checks ports, starts/waits for Redis, captures frontend logs, and cleans up child processes when either service exits.
- Redis stream workers now back off quietly while Redis is unavailable and keep outbox events pending instead of marking them failed for connection errors.

## [0.0.3] - 2026-07-02

### Changed
- Clarified README install guidance for the current local install path, self-hosting with server/frontend/Redis, and future cloud hosting.
- Documented the developer scripts and when to use bare-metal development versus local Docker development.

### Fixed
- Hardened Bash and PowerShell installers so updates preserve existing environment values, including `REDIS_URL`.
- Moved dev Redis to a dedicated default port to avoid conflicts with common local Redis installs.
- Quieted Redis idle polling in development so normal blocking reads do not look like failures.

## [0.0.2] - 2026-07-02

### Added
- Added a staging release gate for PRs into `staging`.
- The gate requires `web/package.json` to increment beyond `origin/staging`.
- The gate requires `CHANGELOG.md` changes and release notes for the new version.
- CI regenerates `web/public/version.json` from `web/package.json` and `CHANGELOG.md`.
- `web/public/version.json` is now generated in CI/build instead of being manually maintained.
- Release history now includes changelog entries for every version in the frontend metadata.
- Documented the GitHub branch protection settings needed to block direct commits to `staging`.

## [0.0.1] - 2026-07-01

Welcome to the first version of **UnmessIt.AI**! This initial release brings a comprehensive suite of features designed to help you store messy text and get answers grounded in your exact saved sources.

### User Authentication & Accounts
- **Local Auth System**: Secure username/password authentication using JWT bearer tokens.
- **Data Isolation**: Total privacy—your notes, tags, and AI processing settings are strictly isolated to your account.

### Notes & Organization
- **Robust Notes Management**: Create, edit, and manage your text-based notes easily.
- **Directory Structures**: Organize your knowledge base using hierarchical folders.
- **Tagging System**: Tag your notes for flexible categorization.
- **Trash & Recovery**: Soft-delete notes into a Trash bin, with the ability to restore them or permanently delete them. Vectors are instantly synced (moved out of AI context when trashed, and back in when restored).

### AI Ingestion & Processing
- **Automated Processing**: Saving a note automatically kicks off background ingestion that extracts chunks, summarizes them, and generates reusable "Recall Keys" (topics, entities, events, etc.).
- **Durable Jobs System**: Background jobs are persistent. You can monitor their progress, pause, stop, or resume them directly from the **Jobs UI**.
- **Lossless Source Chunks**: We don't overwrite your data. AI chunks map exactly back to the spans of text you wrote.
- **Note Insights**: Dive into any note to see exactly what "Recall Keys" the AI generated for it.

### Ask AI (Retrieval)
- **Source-Backed Answers**: Ask questions and get answers explicitly grounded in your notes.
- **Citations & Transparency**: Every answer includes clickable citations linking to the exact chunk of your note it pulled from.
- **Retrieval Analysis Trace**: Expand the trace to see exactly how the AI broke down your query, searched the vector database, and ranked the results.
- **Cross-Domain Filtering**: Focus your query! Tell the AI to *only* search within specific folders or tags, or strictly exclude them.

### AI Settings & Configuration
- **Bring Your Own AI**: Connect directly to OpenAI by adding your own API key and model names.
- **Fallback Rotation**: Configure multiple AI presets. If one fails during a job, UnmessIt automatically rolls over to the next one.
- **Advanced Knobs**: Tech-savvy users can fine-tune chunk sizes, overlap, and retry backoffs.

### User Interface
- **Built-in Versioning**: A sleek global update banner and this very Release History modal to keep you in the loop.
- **Dark Mode Aesthetic**: A highly polished, responsive design utilizing framer-motion animations and debounced loading states.
